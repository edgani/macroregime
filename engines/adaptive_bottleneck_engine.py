"""engines/adaptive_bottleneck_engine.py
Dynamic bottleneck discovery — no hardcoded tickers.
Scans all available price data, clusters by momentum, detects leaders,
traces supply chain via lead-lag correlation, identifies cross-market plays.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set
from collections import defaultdict
import numpy as np
from utils.math_utils import clamp01


@dataclass
class AdaptiveBottleneckOutput:
    active_sectors: List[Dict]
    leader_tickers: List[Dict]
    supply_chain_chains: List[Dict]
    front_run_basket: List[Dict]
    cross_market_opportunities: List[Dict]
    summary: str
    discovery_method: str


class AdaptiveBottleneckEngine:
    """
    Scans ALL tickers in price data. No hardcoded library.
    Detects bottleneck sectors via momentum clustering + volume confirmation.
    """

    def __init__(self, prices: Dict[str, any], volumes: Dict[str, any] = None, vix: float = 20.0):
        self.prices = prices
        self.volumes = volumes or {}
        self.vix = vix
        self._momentum_cache = {}
        self._volatility_cache = {}
        self._volume_cache = {}

    def _ret_n(self, s, n: int) -> float:
        if s is None or len(s) < n + 1:
            return float("nan")
        return float(s.iloc[-1] / s.iloc[-(n + 1)] - 1.0)

    def _volatility(self, s, n: int) -> float:
        if s is None or len(s) < n + 1:
            return float("nan")
        returns = s.iloc[-n:].pct_change().dropna()
        return float(returns.std()) if len(returns) > 5 else float("nan")

    def _volume_zscore(self, ticker: str) -> float:
        v = self.volumes.get(ticker)
        if v is None or len(v) < 21:
            return 0.0
        avg_20 = float(v.iloc[-21:-1].mean())
        if avg_20 == 0:
            return 0.0
        return (float(v.iloc[-1]) - avg_20) / avg_20

    def _compute_momentum_regime(self, ticker: str, s) -> Dict:
        """Classify ticker into momentum regime."""
        if s is None or len(s) < 63:
            return {"regime": "insufficient_data", "score": 0.0}

        r1w = self._ret_n(s, 5)
        r1m = self._ret_n(s, 21)
        r3m = self._ret_n(s, 63)
        vol = self._volatility(s, 21)
        vol_z = self._volume_zscore(ticker)

        # Composite momentum score
        score = (
            0.20 * (r1w / 0.03 if np.isfinite(r1w) else 0)
            + 0.30 * (r1m / 0.08 if np.isfinite(r1m) else 0)
            + 0.35 * (r3m / 0.15 if np.isfinite(r3m) else 0)
            + 0.10 * (vol_z if np.isfinite(vol_z) else 0)
            + 0.05 * (1.0 - min(vol / 0.05, 1.0) if np.isfinite(vol) else 0)
        )
        score = clamp01(score)

        if score > 0.70 and r3m > 0.15:
            regime = "strong_up"
        elif score > 0.45 and r3m > 0.05:
            regime = "building_up"
        elif score > 0.20 and r1m > 0:
            regime = "early_up"
        elif score < -0.70 and r3m < -0.15:
            regime = "strong_down"
        elif score < -0.45 and r3m < -0.05:
            regime = "building_down"
        elif abs(score) < 0.20:
            regime = "chop"
        else:
            regime = "mixed"

        return {
            "ticker": ticker,
            "regime": regime,
            "score": round(score, 3),
            "r1w": round(r1w, 3) if np.isfinite(r1w) else None,
            "r1m": round(r1m, 3) if np.isfinite(r1m) else None,
            "r3m": round(r3m, 3) if np.isfinite(r3m) else None,
            "volatility": round(vol, 4) if np.isfinite(vol) else None,
            "volume_zscore": round(vol_z, 3) if np.isfinite(vol_z) else None,
        }

    def _detect_market(self, ticker: str) -> str:
        if ticker.endswith(".JK"):
            return "IHSG"
        if ticker.endswith(("-USD", "=X", "=F", ".F")):
            return "FX/Commodity"
        if ticker in ("BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"):
            return "Crypto"
        return "US"

    def _cluster_by_momentum(self) -> Dict[str, List[Dict]]:
        """Cluster ALL tickers by momentum regime."""
        clusters = defaultdict(list)
        for ticker, s in self.prices.items():
            if s is None or getattr(s, "empty", True):
                continue
            regime = self._compute_momentum_regime(ticker, s)
            clusters[regime["regime"]].append(regime)
        return dict(clusters)

    def _find_sector_leaders(self, strong_up: List[Dict]) -> List[Dict]:
        """Find top momentum leaders per market."""
        by_market = defaultdict(list)
        for t in strong_up:
            by_market[self._detect_market(t["ticker"])].append(t)

        leaders = []
        for market, tickers in by_market.items():
            tickers.sort(key=lambda x: x["score"], reverse=True)
            for t in tickers[:5]:  # top 5 per market
                t["market"] = market
                t["leader_type"] = "momentum"
                leaders.append(t)
        return leaders

    def _detect_bottleneck_sectors(self, clusters: Dict) -> List[Dict]:
        """
        Detect bottleneck = sector with multiple tickers in strong_up/building_up
        + low correlation to SPY + volume confirmation.
        """
        spy = self.prices.get("SPY")
        spy_returns = spy.pct_change().dropna().iloc[-63:] if spy is not None and len(spy) >= 63 else None

        strong = clusters.get("strong_up", []) + clusters.get("building_up", [])
        if len(strong) < 3:
            return []

        # Group by inferred sector (simplified: correlation clustering)
        sector_groups = self._correlation_cluster(strong, spy_returns)

        sectors = []
        for sector_name, tickers in sector_groups.items():
            if len(tickers) < 2:
                continue
            avg_score = np.mean([t["score"] for t in tickers])
            avg_vol_z = np.mean([t.get("volume_zscore", 0) or 0 for t in tickers])
            avg_r3m = np.mean([t.get("r3m", 0) or 0 for t in tickers])

            # Correlation to SPY (bottleneck = low correlation = idiosyncratic move)
            correlations = []
            for t in tickers:
                s = self.prices.get(t["ticker"])
                if s is not None and len(s) >= 63 and spy_returns is not None:
                    t_returns = s.pct_change().dropna().iloc[-63:]
                    if len(t_returns) == len(spy_returns):
                        correlations.append(np.corrcoef(t_returns, spy_returns)[0, 1])
            avg_corr = np.mean(correlations) if correlations else 0.5

            # Bottleneck score: high momentum + low SPY correlation + volume spike
            bottleneck_score = clamp01(
                0.40 * avg_score
                + 0.30 * (1.0 - abs(avg_corr))
                + 0.20 * min(max(avg_vol_z, 0), 2.0) / 2.0
                + 0.10 * (avg_r3m / 0.20 if avg_r3m > 0 else 0)
            )

            if bottleneck_score > 0.45:
                sectors.append({
                    "sector_name": sector_name,
                    "tickers": [t["ticker"] for t in tickers],
                    "markets": list(set(self._detect_market(t["ticker"]) for t in tickers)),
                    "bottleneck_score": round(bottleneck_score, 3),
                    "avg_momentum": round(avg_score, 3),
                    "spy_correlation": round(avg_corr, 3),
                    "avg_volume_zscore": round(avg_vol_z, 3),
                    "stage": "mature" if bottleneck_score > 0.70 else "building" if bottleneck_score > 0.55 else "early",
                    "leader": tickers[0]["ticker"],  # highest score
                })

        sectors.sort(key=lambda x: x["bottleneck_score"], reverse=True)
        return sectors

    def _correlation_cluster(self, tickers: List[Dict], spy_returns) -> Dict[str, List[Dict]]:
        """Simple correlation-based sector clustering."""
        if len(tickers) < 2:
            return {"mixed": tickers}

        # Compute pairwise correlations
        returns_map = {}
        for t in tickers:
            s = self.prices.get(t["ticker"])
            if s is not None and len(s) >= 21:
                returns_map[t["ticker"]] = s.pct_change().dropna().iloc[-21:]

        # Greedy clustering: start with highest momentum ticker, add correlated ones
        unassigned = set(t["ticker"] for t in tickers)
        clusters = {}
        cluster_idx = 0

        while unassigned:
            seed = max((t for t in tickers if t["ticker"] in unassigned), key=lambda x: x["score"])
            unassigned.remove(seed["ticker"])
            cluster_members = [seed]

            for t in list(unassigned):
                if t not in returns_map or seed["ticker"] not in returns_map:
                    continue
                r1 = returns_map[seed["ticker"]]
                r2 = returns_map[t]
                min_len = min(len(r1), len(r2))
                if min_len < 10:
                    continue
                corr = np.corrcoef(r1.iloc[-min_len:], r2.iloc[-min_len:])[0, 1]
                if np.isfinite(corr) and abs(corr) > 0.60:
                    cluster_members.append(next(x for x in tickers if x["ticker"] == t))
                    unassigned.remove(t)

            clusters[f"Sector_{cluster_idx}"] = cluster_members
            cluster_idx += 1

        return clusters

    def _trace_supply_chain(self, sectors: List[Dict]) -> List[Dict]:
        """
        Trace supply chain via lead-lag correlation.
        If ticker A leads ticker B by 1-3 days consistently, A is upstream of B.
        """
        chains = []
        for sector in sectors[:3]:  # top 3 sectors
            tickers = sector["tickers"][:6]  # limit for performance
            if len(tickers) < 2:
                continue

            # Find lead-lag relationships
            leads = []
            for i, t1 in enumerate(tickers):
                s1 = self.prices.get(t1)
                if s1 is None or len(s1) < 21:
                    continue
                r1 = s1.pct_change().dropna().iloc[-21:]
                for t2 in tickers[i+1:]:
                    s2 = self.prices.get(t2)
                    if s2 is None or len(s2) < 21:
                        continue
                    r2 = s2.pct_change().dropna().iloc[-21:]
                    min_len = min(len(r1), len(r2))
                    if min_len < 10:
                        continue

                    # Test lag 1-3
                    best_lag = 0
                    best_corr = 0
                    for lag in range(1, 4):
                        if min_len <= lag:
                            continue
                        c = np.corrcoef(r1.iloc[-min_len+lag:], r2.iloc[-min_len:-lag])[0, 1]
                        if np.isfinite(c) and abs(c) > abs(best_corr):
                            best_corr = c
                            best_lag = lag

                    if best_corr > 0.50:
                        leads.append({
                            "upstream": t1,
                            "downstream": t2,
                            "lag_days": best_lag,
                            "correlation": round(best_corr, 3),
                        })

            if leads:
                chains.append({
                    "sector": sector["sector_name"],
                    "lead_lag_relationships": sorted(leads, key=lambda x: x["correlation"], reverse=True)[:5],
                })
        return chains

    def _detect_cross_market(self, leaders: List[Dict], sectors: List[Dict]) -> List[Dict]:
        """Detect same-theme plays across markets."""
        opportunities = []
        for sector in sectors[:3]:
            markets = sector["markets"]
            if len(markets) < 2:
                continue
            opportunities.append({
                "theme": sector["sector_name"],
                "markets": markets,
                "tickers_by_market": {
                    m: [t for t in sector["tickers"] if self._detect_market(t) == m][:3]
                    for m in markets
                },
                "bottleneck_score": sector["bottleneck_score"],
                "rationale": f"{sector['sector_name']} active across {len(markets)} markets — arbitrage or amplify",
            })
        return opportunities

    def _build_front_run_basket(self, sectors: List[Dict], leaders: List[Dict]) -> List[Dict]:
        """Build actionable basket from detected sectors + leaders."""
        basket = []
        vix_scale = 1.0 if self.vix < 19 else 0.85 if self.vix < 29 else 0.50

        # From sectors
        for sector in sectors[:4]:
            for ticker in sector["tickers"][:3]:
                s = self.prices.get(ticker)
                if s is None:
                    continue
                regime = self._compute_momentum_regime(ticker, s)
                adj_score = regime["score"] * vix_scale

                if adj_score > 0.40:
                    basket.append({
                        "ticker": ticker,
                        "market": self._detect_market(ticker),
                        "sector": sector["sector_name"],
                        "conviction": round(adj_score, 3),
                        "stage": sector["stage"],
                        "r1m": regime.get("r1m"),
                        "r3m": regime.get("r3m"),
                        "volume_zscore": regime.get("volume_zscore"),
                        "source": "adaptive_sector",
                        "position_size": "full" if adj_score > 0.70 else "half" if adj_score > 0.55 else "quarter",
                    })

        # From leaders (ensure no duplicates)
        existing = {b["ticker"] for b in basket}
        for leader in leaders[:5]:
            if leader["ticker"] in existing:
                continue
            adj_score = leader["score"] * vix_scale
            if adj_score > 0.40:
                basket.append({
                    "ticker": leader["ticker"],
                    "market": leader["market"],
                    "sector": "momentum_leader",
                    "conviction": round(adj_score, 3),
                    "stage": "building" if leader["regime"] == "building_up" else "early",
                    "r1m": leader.get("r1m"),
                    "r3m": leader.get("r3m"),
                    "volume_zscore": leader.get("volume_zscore"),
                    "source": "momentum_scan",
                    "position_size": "half" if adj_score > 0.55 else "quarter",
                })

        basket.sort(key=lambda x: x["conviction"], reverse=True)
        return basket[:15]

    def run(self, current_quad: str = "Q?") -> AdaptiveBottleneckOutput:
        clusters = self._cluster_by_momentum()
        strong_up = clusters.get("strong_up", [])
        building_up = clusters.get("building_up", [])

        leaders = self._find_sector_leaders(strong_up + building_up)
        sectors = self._detect_bottleneck_sectors(clusters)
        chains = self._trace_supply_chain(sectors)
        cross_market = self._detect_cross_market(leaders, sectors)
        basket = self._build_front_run_basket(sectors, leaders)

        if sectors:
            top = sectors[0]
            summary = (
                f"Adaptive scan: {len(clusters)} regimes detected. "
                f"Top sector: {top['sector_name']} (score {top['bottleneck_score']:.2f}, "
                f"SPY corr {top['spy_correlation']:.2f}). "
                f"{len(basket)} front-run candidates. "
                f"VIX {self.vix:.1f} → conviction scaled {1.0 if self.vix < 19 else 0.85 if self.vix < 29 else 0.50:.0%}"
            )
        else:
            summary = f"Adaptive scan: {len(clusters)} regimes, no bottleneck sectors detected. VIX {self.vix:.1f}."

        return AdaptiveBottleneckOutput(
            active_sectors=sectors,
            leader_tickers=leaders,
            supply_chain_chains=chains,
            front_run_basket=basket,
            cross_market_opportunities=cross_market,
            summary=summary,
            discovery_method="adaptive_momentum_clustering",
        )
