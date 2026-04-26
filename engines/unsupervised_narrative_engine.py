"""engines/unsupervised_narrative_engine.py — Auto-Discover NEW Narratives & Bottlenecks

NO HARDCODED NARRATIVES. NO ANCHORED SECTOR BUCKETS.
Uses HDBSCAN clustering + correlation graph analysis to detect EMERGING patterns
that don't exist in any pre-defined taxonomy.

Input: price history of full universe
Output: auto-detected clusters → candidate narrative labels → spillover predictions
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple, Set
import numpy as np
import pandas as pd
from dataclasses import dataclass, field

try:
    from hdbscan import HDBSCAN
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False


@dataclass
class EmergingCluster:
    cluster_id: int
    tickers: List[str]
    markets: List[str]
    avg_correlation: float
    momentum_score: float
    narrative_label: str          # auto-generated from sector composition
    is_new: bool                # not matching any known narrative
    spillover_candidates: List[Tuple[str, float]] = field(default_factory=list)
    confidence: float = 0.0


class UnsupervisedNarrativeEngine:
    """Zero hardcode. Zero anchor. Pure pattern detection from price data."""

    def __init__(self, settings_module=None):
        self.cfg = settings_module
        self.sector_map = getattr(settings_module, "TICKER_SECTOR", {}) if settings_module else {}
        self.market_map = getattr(settings_module, "MARKET_CLASSIFICATION", {}) if settings_module else {}
        self.known_sectors: Set[str] = set(self.sector_map.values()) if self.sector_map else set()

    def _build_correlation_matrix(
        self,
        prices: Dict[str, pd.Series],
        lookback: int = 63,
        min_obs: int = 30,
    ) -> Tuple[pd.DataFrame, List[str]]:
        """Build return correlation matrix from price data."""
        returns = {}
        valid_tickers = []

        for ticker, close in prices.items():
            close = pd.to_numeric(close, errors="coerce").dropna().tail(lookback)
            if len(close) < min_obs:
                continue
            ret = close.pct_change().dropna().values
            if len(ret) >= min_obs // 2:
                returns[ticker] = ret[-min_obs:]
                valid_tickers.append(ticker)

        if len(valid_tickers) < 5:
            return pd.DataFrame(), []

        # Align lengths
        min_len = min(len(v) for v in returns.values())
        aligned = {k: v[-min_len:] for k, v in returns.items()}

        # Correlation matrix
        df = pd.DataFrame(aligned)
        corr = df.corr().fillna(0)
        return corr, valid_tickers

    def _distance_from_correlation(self, corr: pd.DataFrame) -> np.ndarray:
        """Convert correlation to distance: d = sqrt(2 * (1 - rho))"""
        dist = np.sqrt(2 * (1 - np.clip(corr.values, -1, 1)))
        np.fill_diagonal(dist, 0)
        return dist

    def detect_emerging_clusters(
        self,
        prices: Dict[str, pd.Series],
        lookback: int = 63,
        min_cluster_size: int = 3,
        min_samples: int = 2,
        correlation_threshold: float = 0.40,
    ) -> List[EmergingCluster]:
        """HDBSCAN clustering on correlation distance matrix."""
        corr, tickers = self._build_correlation_matrix(prices, lookback)
        if len(tickers) < 5:
            return []

        dist = self._distance_from_correlation(corr)

        if HDBSCAN_AVAILABLE:
            clusterer = HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
                metric="precomputed",
                cluster_selection_method="eom",
            )
            labels = clusterer.fit_predict(dist)
        else:
            # Fallback: simple correlation threshold clustering
            labels = self._fallback_clustering(corr.values, tickers, correlation_threshold)

        clusters: Dict[int, List[str]] = {}
        noise = []
        for i, label in enumerate(labels):
            if label == -1:
                noise.append(tickers[i])
            else:
                clusters.setdefault(label, []).append(tickers[i])

        results = []
        for cid, members in clusters.items():
            if len(members) < min_cluster_size:
                continue

            # Compute cluster stats
            sub_corr = corr.loc[members, members]
            avg_corr = float(sub_corr.values[np.triu_indices_from(sub_corr.values, k=1)].mean())

            # Momentum: average 21d return
            mom_scores = []
            for t in members:
                close = pd.to_numeric(prices.get(t), errors="coerce").dropna()
                if len(close) > 22:
                    mom_scores.append(float(close.iloc[-1] / close.iloc[-22] - 1))
            avg_mom = np.mean(mom_scores) if mom_scores else 0.0

            # Markets represented
            markets = list({self.market_map.get(t, "unknown") for t in members})

            # Auto-label from sector composition
            sectors = [self.sector_map.get(t, "unknown") for t in members]
            sector_counts = {}
            for s in sectors:
                sector_counts[s] = sector_counts.get(s, 0) + 1
            top_sector = max(sector_counts, key=sector_counts.get) if sector_counts else "mixed"
            label = f"emerging_{top_sector}_{cid}"

            # Is this NEW? (not matching known narratives)
            known_sector_ratio = sum(1 for s in sectors if s in self.known_sectors) / max(len(sectors), 1)
            is_new = known_sector_ratio < 0.5  # majority unknown = new narrative

            # Spillover: find tickers highly correlated with cluster but NOT in cluster
            spillover = []
            for t in tickers:
                if t in members:
                    continue
                t_corr = corr.loc[t, members].mean() if t in corr.index else 0
                if t_corr > 0.35 and t_corr < 0.80:  # correlated but not identical
                    spillover.append((t, round(float(t_corr), 3)))
            spillover.sort(key=lambda x: x[1], reverse=True)

            results.append(EmergingCluster(
                cluster_id=cid,
                tickers=members,
                markets=markets,
                avg_correlation=round(avg_corr, 3),
                momentum_score=round(avg_mom, 3),
                narrative_label=label,
                is_new=is_new,
                spillover_candidates=spillover[:10],
                confidence=round(min(avg_corr * 2.0, 1.0), 3),
            ))

        # Sort by momentum × correlation
        results.sort(key=lambda x: abs(x.momentum_score) * x.avg_correlation, reverse=True)
        return results

    def _fallback_clustering(
        self,
        corr_matrix: np.ndarray,
        tickers: List[str],
        threshold: float = 0.40,
    ) -> np.ndarray:
        """Simple agglomerative clustering when HDBSCAN not available."""
        n = len(tickers)
        labels = np.full(n, -1)
        visited = set()
        cluster_id = 0

        for i in range(n):
            if i in visited:
                continue
            cluster = [i]
            visited.add(i)
            for j in range(n):
                if j in visited:
                    continue
                if corr_matrix[i, j] > threshold:
                    cluster.append(j)
                    visited.add(j)
            if len(cluster) >= 3:
                for idx in cluster:
                    labels[idx] = cluster_id
                cluster_id += 1

        return labels

    def detect_bottleneck_candidates(
        self,
        prices: Dict[str, pd.Series],
        clusters: List[EmergingCluster],
        quad_str: str = "Q3",
    ) -> List[Dict]:
        """From emerging clusters, identify which ones look like bottleneck patterns."""
        candidates = []

        for c in clusters:
            # Bottleneck signature: high correlation + accelerating momentum + not at ATH
            ath_distances = []
            acc_scores = []
            for t in c.tickers:
                close = pd.to_numeric(prices.get(t), errors="coerce").dropna()
                if len(close) < 30:
                    continue
                hi52 = float(close.tail(252).max()) if len(close) >= 252 else float(close.max())
                px = float(close.iloc[-1])
                ath_distances.append((px - hi52) / max(hi52, 1e-9))

                # Accumulation score
                v = close.pct_change().dropna().tail(63).values
                if len(v) > 20:
                    up = v > 0
                    uv = float(np.mean(v[up])) if up.any() else float(np.mean(v))
                    dv = float(np.mean(v[~up])) if (~up).any() else float(np.mean(v))
                    acc_scores.append(float(np.clip(0.5 * (uv / (abs(dv) + 1e-10)), 0.0, 1.0)))

            avg_ath_dist = np.mean(ath_distances) if ath_distances else 0
            avg_acc = np.mean(acc_scores) if acc_scores else 0.5

            # Bottleneck brewing score
            brewing = 0.0
            if c.avg_correlation > 0.50:
                brewing += 0.25
            if avg_acc > 0.55:
                brewing += 0.20
            if avg_ath_dist < -0.05:
                brewing += 0.20  # room to run
            if abs(c.momentum_score) > 0.03:
                brewing += 0.15
            if c.is_new:
                brewing += 0.10  # new = early = alpha

            if brewing >= 0.50:
                candidates.append({
                    "cluster_id": c.cluster_id,
                    "narrative_label": c.narrative_label,
                    "tickers": c.tickers,
                    "markets": c.markets,
                    "avg_correlation": c.avg_correlation,
                    "momentum_score": c.momentum_score,
                    "avg_ath_distance": round(avg_ath_dist, 3),
                    "accumulation": round(avg_acc, 2),
                    "brewing_score": round(brewing, 3),
                    "is_new_narrative": c.is_new,
                    "spillover_candidates": c.spillover_candidates,
                    "confidence": c.confidence,
                    "verdict": "bottleneck_brewing" if brewing >= 0.70 else "watch",
                })

        candidates.sort(key=lambda x: x["brewing_score"], reverse=True)
        return candidates

    def run(
        self,
        prices: Dict[str, pd.Series],
        quad_str: str = "Q3",
        lookback: int = 63,
    ) -> Dict:
        """Full pipeline: detect clusters → identify bottleneck candidates."""
        clusters = self.detect_emerging_clusters(prices, lookback)
        bottleneck_candidates = self.detect_bottleneck_candidates(prices, clusters, quad_str)

        # Separate new vs known
        new_narratives = [c for c in clusters if c.is_new]
        known_narratives = [c for c in clusters if not c.is_new]

        return {
            "emerging_clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "label": c.narrative_label,
                    "tickers": c.tickers,
                    "markets": c.markets,
                    "avg_correlation": c.avg_correlation,
                    "momentum": c.momentum_score,
                    "is_new": c.is_new,
                    "confidence": c.confidence,
                }
                for c in clusters
            ],
            "new_narratives_detected": [
                {
                    "cluster_id": c.cluster_id,
                    "label": c.narrative_label,
                    "tickers": c.tickers,
                    "markets": c.markets,
                    "avg_correlation": c.avg_correlation,
                    "momentum": c.momentum_score,
                    "spillover": c.spillover_candidates[:5],
                }
                for c in new_narratives
            ],
            "bottleneck_candidates": bottleneck_candidates,
            "meta": {
                "total_clusters": len(clusters),
                "new_narratives": len(new_narratives),
                "known_patterns": len(known_narratives),
                "bottleneck_brewing": len([b for b in bottleneck_candidates if b["verdict"] == "bottleneck_brewing"]),
                "universe_scanned": len(prices),
                "hdbscan_used": HDBSCAN_AVAILABLE,
            },
        }