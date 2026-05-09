"""orchestrator.py — MacroRegime Pro Orchestrator
Single entry point: build_snapshot() → returns full macro snapshot dict.
"""
from __future__ import annotations
import os, sys, json, math, logging, time
from typing import Dict, List, Optional
from datetime import datetime, timezone
import pandas as pd
import numpy as np

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------
from config.settings import (
    MACRO_PROXIES, US_SECTORS, BONDS, COMMODITIES, CRYPTO, FOREX_PAIRS,
    TICKER_SECTOR, MAG7, US_BUCKETS,
)

try:
    from config.autonomy_settings import AUTONOMY_LEVEL
except Exception:
    AUTONOMY_LEVEL = "semi"

# ------------------------------------------------------------------
# Engines
# ------------------------------------------------------------------
from data.loader import load_prices, load_fred_macro
from engines.gip_engine import GIPEngine
from engines.quad_engine import QuadEngine
from engines.market_health_engine import MarketHealthEngine
from engines.hurst_risk_ranges import HurstRiskRangeEngine
from engines.cme_cot import CMECOTProxy
from engines.cme_oi import CMEOpenInterestProxy
from engines.defillama_helper import DeFiLlamaHelper
from engines.auto_discovery_engine_v3 import AutoDiscoveryEngineV3

# ------------------------------------------------------------------
# QUAD_MAP fallback — if engines.quad_engine doesn't export it
# ------------------------------------------------------------------
try:
    from engines.quad_engine import QUAD_MAP
except Exception:
    # Fallback QUAD_MAP matching Hedgeye framework
    QUAD_MAP = {
        "Q1": {"name": "Goldilocks", "assets": ["XLK", "XLY", "XLI", "IWM", "QQQ", "RSP", "SLV", "GLD", "IBIT"], "bias": "bullish"},
        "Q2": {"name": "Reflation / Knife Fights", "assets": ["XLE", "OIH", "XLI", "XLB", "SLV", "GLD", "GDX", "ITB", "TLT", "IBIT"], "bias": "bullish"},
        "Q3": {"name": "Stagflation", "assets": ["SLV", "GLD", "PPLT", "GDX", "GDXJ", "XLV", "XLP", "XLU", "TLT", "ITA"], "bias": "bearish"},
        "Q4": {"name": "Deflation", "assets": ["TLT", "IEF", "GLD", "SLV", "XLV", "XLP", "XLU", "UUP", "BTAL"], "bias": "bearish"},
    }
    logger.info("Using fallback QUAD_MAP (engines.quad_engine.QUAD_MAP not exported)")

# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------
class Orchestrator:
    def __init__(self, lookback: int = 252):
        self.lookback = lookback
        self.gip = GIPEngine()
        self.quad = QuadEngine()
        self.health = MarketHealthEngine()
        self.risk = HurstRiskRangeEngine()
        self.cot_proxy = CMECOTProxy()
        self.oi_proxy = CMEOpenInterestProxy()
        self.defi = DeFiLlamaHelper()
        self.discovery = AutoDiscoveryEngineV3()

    # ── helpers ──────────────────────────────────────────────────────
    def _safe_ret(self, s: Optional[pd.Series], n: int) -> Optional[float]:
        if s is None or s.empty:
            return None
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < n + 1:
            return None
        try:
            r = float(s.iloc[-1] / s.iloc[-n - 1] - 1)
            return r if math.isfinite(r) else None
        except Exception:
            return None

    def _last_price(self, s: Optional[pd.Series]) -> Optional[float]:
        if s is None or s.empty:
            return None
        try:
            v = float(pd.to_numeric(s, errors="coerce").dropna().iloc[-1])
            return v if math.isfinite(v) else None
        except Exception:
            return None

    def _build_macro_summary(self, gip_features: Dict, quad: str) -> Dict:
        g = gip_features.get("growth_momentum", 0)
        i = gip_features.get("inflation_momentum", 0)
        p = gip_features.get("policy_score", 0)
        q3 = gip_features.get("q3_modifier", 0)

        growth_label = "Accelerating 📈" if g > 0.08 else "Decelerating 📉" if g < -0.08 else "Stable ➡️"
        inflation_label = "Rising 🔥" if i > 0.05 else "Falling ❄️" if i < -0.05 else "Stable ➡️"
        policy_label = "Hawkish 🦅" if p < -0.3 else "Dovish 🕊️" if p > 0.3 else "Neutral ⚖️"

        regime = QUAD_MAP.get(quad, {"name": "Unknown", "assets": [], "bias": "neutral"})
        bias = regime.get("bias", "neutral")
        assets = regime.get("assets", [])

        summary = {
            "quad": quad,
            "regime_name": regime.get("name", "Unknown"),
            "bias": bias,
            "recommended_assets": assets,
            "growth": {"momentum": round(g, 4), "label": growth_label},
            "inflation": {"momentum": round(i, 4), "label": inflation_label},
            "policy": {"score": round(p, 4), "label": policy_label},
            "q3_modifier": round(q3, 4),
            "note": (
                f"Regime {regime.get('name', 'Unknown')} ({quad}). "
                f"Growth {growth_label}, Inflation {inflation_label}, Policy {policy_label}. "
                f"Focus: {', '.join(assets[:4]) if assets else 'TBD'}."
            ),
        }
        return summary

    def _build_sector_table(self, prices: Dict[str, pd.Series]) -> List[Dict]:
        rows = []
        for name, tickers in US_SECTORS.items():
            rets = [self._safe_ret(prices.get(t), 21) for t in tickers if prices.get(t) is not None]
            valid = [r for r in rets if r is not None]
            if not valid:
                continue
            avg_ret = float(np.mean(valid))
            med_ret = float(np.median(valid))
            rows.append({
                "sector": name,
                "avg_1m": round(avg_ret, 4),
                "median_1m": round(med_ret, 4),
                "breadth": f"{sum(1 for r in valid if r > 0)}/{len(valid)}",
                "tone": "good" if avg_ret > 0.03 else "warn" if avg_ret > -0.03 else "bad",
            })
        rows.sort(key=lambda x: x["avg_1m"], reverse=True)
        return rows

    def _build_narrative(self, gip_features: Dict, quad: str, health: Dict) -> str:
        g = gip_features.get("growth_momentum", 0)
        i = gip_features.get("inflation_momentum", 0)
        p = gip_features.get("policy_score", 0)
        q3 = gip_features.get("q3_modifier", 0)
        regime = QUAD_MAP.get(quad, {"name": "Unknown"})
        vix = health.get("vix_bucket", {}).get("vix_last", 18)
        crash = health.get("crash", {}).get("state", "calm")

        parts = []
        parts.append(f"🌍 MacroRegime: **{regime.get('name', 'Unknown')}** ({quad})")
        parts.append(f"📊 Growth {g:+.2%} | Inflation {i:+.2%} | Policy {p:+.2f} | Q3 {q3:+.2f}")
        if vix > 25:
            parts.append(f"⚠️ VIX {vix:.0f} — defensive posture")
        if crash in ("elevated", "watch"):
            parts.append(f"🚨 Crash meter: {crash.upper()}")
        if q3 > 0.3:
            parts.append("🔥 Q3 modifier positive — risk-on tailwind")
        elif q3 < -0.3:
            parts.append("❄️ Q3 modifier negative — risk-off headwind")

        return "\n".join(parts)

    def _build_alpha_ideas(self, prices: Dict, health: Dict, gip: Dict, quad: str) -> List[Dict]:
        ideas = []
        regime = QUAD_MAP.get(quad, {})
        bias = regime.get("bias", "neutral")
        assets = regime.get("assets", [])

        for asset in assets[:6]:
            ticker = None
            for t, s in TICKER_SECTOR.items():
                if s == asset:
                    ticker = t
                    break
            if ticker is None:
                continue
            p = self._last_price(prices.get(ticker))
            r1m = self._safe_ret(prices.get(ticker), 21)
            if p is None or r1m is None:
                continue
            direction = "Long" if bias in ("bullish", "risk_on") else "Short" if bias == "bearish" else "Neutral"
            ideas.append({
                "ticker": ticker,
                "theme": asset.replace("_", " ").title(),
                "direction": direction,
                "price": round(p, 2),
                "momentum_1m": round(r1m, 4),
                "setup": f"{direction} {ticker} @ {p:.2f} — {asset.replace('_', ' ').title()} theme in {regime.get('name', 'Unknown')}",
            })
        return ideas

    def _build_bottlenecks(self, prices: Dict, health: Dict, gip: Dict) -> List[Dict]:
        b = []
        vix = health.get("vix_bucket", {}).get("vix_last", 18)
        crash = health.get("crash", {}).get("state", "calm")
        crash_score = health.get("crash", {}).get("score", 0)
        risk_off = health.get("risk_off", {}).get("state", "risk_on")
        g = gip.get("growth_momentum", 0)
        i = gip.get("inflation_momentum", 0)

        if vix > 25:
            b.append({"type": "volatility", "severity": "high" if vix > 30 else "medium", "description": f"VIX {vix:.0f} — elevated volatility regime"})
        if crash == "elevated":
            b.append({"type": "crash_risk", "severity": "high", "description": f"Crash score {crash_score:.2f} — multiple stress signals active"})
        elif crash == "watch":
            b.append({"type": "crash_risk", "severity": "medium", "description": f"Crash score {crash_score:.2f} — watch mode"})
        if risk_off == "risk_off":
            b.append({"type": "risk_off", "severity": "high", "description": "Risk-off regime — reduce beta, increase cash/Treasuries"})
        elif risk_off == "caution":
            b.append({"type": "risk_off", "severity": "medium", "description": "Risk-off caution — tighten stops, reduce sizing"})
        if g < -0.05:
            b.append({"type": "growth", "severity": "high" if g < -0.10 else "medium", "description": f"Growth decelerating ({g:+.2%}) — earnings risk"})
        if i > 0.04:
            b.append({"type": "inflation", "severity": "high" if i > 0.06 else "medium", "description": f"Inflation persistent ({i:+.2%}) — Fed hawkish risk"})

        # Check MAG7 concentration as bottleneck
        mag7_rets = [self._safe_ret(prices.get(t), 21) for t in MAG7 if prices.get(t) is not None]
        mag7_valid = [r for r in mag7_rets if r is not None]
        spy_ret = self._safe_ret(prices.get("SPY"), 21)
        if mag7_valid and spy_ret is not None:
            mag7_avg = float(np.mean(mag7_valid))
            if mag7_avg > spy_ret + 0.03:
                b.append({"type": "concentration", "severity": "medium", "description": "MAG7 outperforming SPY by >3% — narrow leadership bottleneck"})

        return b

    def _build_risk_ranges(self, prices: Dict) -> Dict[str, Dict]:
        """Build TRR/LRR for all tracked tickers."""
        rr_tickers = (
            list(MACRO_PROXIES.keys()) + list(US_SECTORS.keys()) +
            list(BONDS.keys()) + list(COMMODITIES.keys())[:15] +
            list(FOREX_PAIRS.keys()) +  # <-- FIX: added FOREX_PAIRS
            (list(CRYPTO.keys())[:6] if True else []) +
            ["DX-Y.NYB","EIDO","^JKSE"] +
            [t for t in TICKER_SECTOR if TICKER_SECTOR.get(t) in (
                "ai_optics","ai_power","ai_power_infra","precious_metals","precious_metals_miners",
                "defense","oil_services","housing","steel","infrastructure"
            )][:25]
        )

        asset_ranges: Dict[str, Dict] = {}
        for t in rr_tickers:
            s = prices.get(t)
            if s is None or s.empty:
                continue
            try:
                rr = self.risk.analyze(s)
                if rr and rr.get("ok"):
                    asset_ranges[t] = rr
            except Exception as e:
                logger.debug(f"Risk range error for {t}: {e}")
                continue

        return asset_ranges

    def _build_cot_oi(self, prices: Dict) -> Dict[str, Dict]:
        """Build COT + OI proxy for CME futures."""
        cot_results: Dict[str, Dict] = {}
        oi_results: Dict[str, Dict] = {}

        # CME futures tickers that have COT data
        cme_tickers = list(COMMODITIES.keys())[:10] + ["DX-Y.NYB"] + list(FOREX_PAIRS.keys())[:6]
        vix_last = self._last_price(prices.get("^VIX")) or 18.0

        for t in cme_tickers:
            try:
                cot = self.cot_proxy.analyze(t, prices, vix=vix_last)
                if cot and cot.get("ok"):
                    cot_results[t] = cot
            except Exception as e:
                logger.debug(f"COT error for {t}: {e}")

            try:
                oi = self.oi_proxy.analyze(t, prices)
                if oi and oi.get("ok"):
                    oi_results[t] = oi
            except Exception as e:
                logger.debug(f"OI error for {t}: {e}")

        return {"cot": cot_results, "oi": oi_results}

    def _build_crypto_onchain(self) -> Dict:
        """Fetch DeFiLlama on-chain metrics."""
        try:
            tvl = self.defi.get_tvl()
            stable = self.defi.get_stablecoin_mcap()
            dex = self.defi.get_dex_volume_24h()
            return {
                "tvl_b": round(tvl, 2) if tvl else None,
                "stable_mcap_b": round(stable, 2) if stable else None,
                "dex_vol_24h_b": round(dex, 2) if dex else None,
                "source": "defillama",
            }
        except Exception as e:
            logger.warning(f"DeFiLlama error: {e}")
            return {"tvl_b": None, "stable_mcap_b": None, "dex_vol_24h_b": None, "source": "defillama", "error": str(e)}

    # ── main build ─────────────────────────────────────────────────
    def build_snapshot(self, include_crypto: bool = True) -> Dict:
        t0 = time.time()
        logger.info("Building macro snapshot...")

        # 1. Load data
        prices = load_prices(lookback=self.lookback)
        fred_data = load_fred_macro()

        # 2. GIP + Quad
        gip_features = self.gip.analyze(fred_data)
        quad = self.quad.classify(gip_features)

        # 3. Market Health
        health = self.health.run(prices, gip_features, quad)

        # 4. Risk Ranges
        asset_ranges = self._build_risk_ranges(prices)

        # 5. COT + OI
        cot_oi = self._build_cot_oi(prices)

        # 6. Crypto on-chain
        crypto_onchain = self._build_crypto_onchain() if include_crypto else {}

        # 7. Discovery
        discovery = self.discovery.run(prices, gip_features, quad)

        # 8. Macro summary
        macro_summary = self._build_macro_summary(gip_features, quad)

        # 9. Narrative
        narrative = self._build_narrative(gip_features, quad, health)

        # 10. Alpha ideas
        alpha_ideas = self._build_alpha_ideas(prices, health, gip_features, quad)

        # 11. Bottlenecks
        bottlenecks = self._build_bottlenecks(prices, health, gip_features)

        # 12. Sector table
        sector_table = self._build_sector_table(prices)

        # 13. Timestamp
        timestamp = datetime.now(timezone.utc).isoformat()

        snapshot = {
            "timestamp": timestamp,
            "macro_summary": macro_summary,
            "gip_features": gip_features,
            "quad": quad,
            "market_health": health,
            "asset_ranges": asset_ranges,
            "cot_oi": cot_oi,
            "crypto_onchain": crypto_onchain,
            "discovery": discovery,
            "narrative": narrative,
            "alpha_ideas": alpha_ideas,
            "bottlenecks": bottlenecks,
            "sector_table": sector_table,
            "prices_loaded": len(prices),
            "assets_in_snapshot": len(asset_ranges),
            "build_time_sec": round(time.time() - t0, 1),
        }

        logger.info(f"Snapshot built in {snapshot['build_time_sec']}s | "
                    f"Prices: {snapshot['prices_loaded']} | "
                    f"Ranges: {snapshot['assets_in_snapshot']}")
        return snapshot


# ------------------------------------------------------------------
# CLI / direct run
# ------------------------------------------------------------------
if __name__ == "__main__":
    orch = Orchestrator()
    snap = orch.build_snapshot(include_crypto=True)
    print(json.dumps(snap["macro_summary"], indent=2))
    print(f"\nBuilt in {snap['build_time_sec']}s")
