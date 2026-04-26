"""engines/price_cluster_engine.py v1 — Auto-Discover Themes from Price Action

Detects clusters of tickers that are outperforming together with high correlation.
These clusters = emergent narratives BEFORE media covers them.
"""
from __future__ import annotations
import math
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from collections import Counter, defaultdict

class PriceClusterEngine:
    """
    L1 Signal Detection: discover emergent themes purely from price action.
    Steps:
      1. Filter outperformers (RS vs benchmark > threshold)
      2. Compute correlation matrix of returns
      3. DBSCAN clustering on correlation + momentum features
      4. Auto-label clusters by dominant sector / market
      5. Return emergent themes with confidence
    """

    def __init__(self, sector_map: Dict[str,str], market_map: Dict[str,str]):
        self.sector_map = sector_map
        self.market_map = market_map

    def run(
        self,
        prices: Dict[str, pd.Series],
        benchmark: str = "SPY",
        lookback: int = 63,
        rs_threshold: float = 0.02,      # min 2% outperformance vs bench
        corr_threshold: float = 0.65,    # min pairwise correlation
        min_cluster_size: int = 3,
    ) -> Dict[str, object]:

        bench = prices.get(benchmark)
        if bench is None or len(bench) < lookback + 5:
            return {"clusters": [], "meta": {"error": "benchmark missing"}}

        # ── 1. Compute returns & RS ─────────────────────────────────────
        tickers = [t for t in prices if t != benchmark]
        rets = {}
        rs_scores = {}
        bench_ret = self._ret(bench, lookback) or 0.0

        for t in tickers:
            s = prices.get(t)
            if s is None or len(s) < lookback + 5:
                continue
            r = self._ret(s, lookback)
            if r is None:
                continue
            rets[t] = r
            # RS = ticker return - benchmark return
            rs_scores[t] = r - bench_ret

        # Filter outperformers
        outperformers = {t: rs for t, rs in rs_scores.items() if rs >= rs_threshold}
        if len(outperformers) < min_cluster_size:
            return {"clusters": [], "meta": {"outperformers": len(outperformers)}}

        symbols = list(outperformers.keys())
        n = len(symbols)

        # ── 2. Build daily return matrix for correlation ──────────────
        daily_rets = {}
        for t in symbols:
            s = pd.to_numeric(prices[t], errors="coerce").dropna().tail(lookback)
            dr = s.pct_change().dropna().values
            if len(dr) >= 20:
                daily_rets[t] = dr

        # Intersect length
        min_len = min(len(v) for v in daily_rets.values())
        if min_len < 15:
            return {"clusters": [], "meta": {"error": "insufficient daily data"}}

        # Align lengths
        aligned = {t: v[-min_len:] for t, v in daily_rets.items()}
        sym_list = list(aligned.keys())
        m = len(sym_list)

        # Correlation matrix
        corr_mat = np.zeros((m, m))
        for i, ti in enumerate(sym_list):
            for j, tj in enumerate(sym_list):
                if i == j:
                    corr_mat[i, j] = 1.0
                else:
                    c = np.corrcoef(aligned[ti], aligned[tj])[0, 1]
                    corr_mat[i, j] = c if math.isfinite(c) else 0.0

        # ── 3. Feature matrix for DBSCAN: [avg_corr, momentum, volatility] ─
        features = []
        for i, t in enumerate(sym_list):
            avg_corr = float(np.mean([corr_mat[i, j] for j in range(m) if j != i]))
            mom = outperformers.get(t, 0.0)
            vol = float(np.std(aligned[t]))
            features.append([avg_corr, mom, vol])

        X = np.array(features)
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)

        # DBSCAN: eps tuned for correlation space
        clustering = DBSCAN(eps=0.8, min_samples=min_cluster_size).fit(Xs)
        labels = clustering.labels_

        # ── 4. Build clusters ───────────────────────────────────────────
        clusters = defaultdict(list)
        for idx, lbl in enumerate(labels):
            if lbl == -1:  # noise
                continue
            clusters[lbl].append(sym_list[idx])

        results = []
        for cid, members in clusters.items():
            if len(members) < min_cluster_size:
                continue

            # Auto-label by dominant sector
            sectors = [self.sector_map.get(t, "unknown") for t in members]
            sector_ctr = Counter(sectors)
            dom_sector, dom_count = sector_ctr.most_common(1)[0]
            sector_pct = dom_count / len(members)

            # Auto-label by dominant market
            markets = [self.market_map.get(t, "us_equity") for t in members]
            market_ctr = Counter(markets)
            dom_market = market_ctr.most_common(1)[0][0]

            # Cluster stats
            cluster_rs = [outperformers[t] for t in members]
            avg_rs = float(np.mean(cluster_rs))
            max_rs = float(np.max(cluster_rs))

            # Correlation strength
            idxs = [sym_list.index(t) for t in members]
            sub_corr = corr_mat[np.ix_(idxs, idxs)]
            avg_pairwise = float(np.mean(sub_corr[np.triu_indices_from(sub_corr, k=1)]))

            # Detect if this is a NEW theme (not matching existing sectors well)
            is_novel = sector_pct < 0.6  # mixed sectors = potential new cross-sector theme

            results.append({
                "cluster_id": int(cid),
                "members": members,
                "member_count": len(members),
                "dominant_sector": dom_sector,
                "sector_concentration": round(sector_pct, 2),
                "dominant_market": dom_market,
                "avg_rs_3m": round(avg_rs, 4),
                "max_rs_3m": round(max_rs, 4),
                "avg_correlation": round(avg_pairwise, 3),
                "is_novel_theme": is_novel,
                "theme_hypothesis": self._hypothesize_theme(members, dom_sector, is_novel),
                "confidence": round(min(avg_pairwise * 1.2, 1.0), 3),
            })

        # Sort by confidence
        results.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "clusters": results,
            "outlier_tickers": [sym_list[i] for i, lbl in enumerate(labels) if lbl == -1 and sym_list[i] in outperformers],
            "meta": {
                "universe_scanned": len(tickers),
                "outperformers": len(outperformers),
                "clusters_found": len(results),
                "benchmark": benchmark,
                "lookback": lookback,
            }
        }

    def _ret(self, s, n):
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < n + 1:
            return None
        try:
            r = float(s.iloc[-1] / s.iloc[-n - 1] - 1)
            return r if math.isfinite(r) else None
        except:
            return None

    def _hypothesize_theme(self, members, dom_sector, is_novel):
        if is_novel:
            return f"Cross-sector emergent theme: {', '.join(members[:3])} and {len(members)-3} others moving together despite different sectors"
        # Map sector to likely narrative
        sector_narrative = {
            "ai_optics": "AI photonics / CPO supply chain surge",
            "ai_power": "AI power / SiC-GaN demand acceleration",
            "ai_power_infra": "AI data center power infrastructure buildout",
            "transformer_infra": "Electrical grid / transformer shortage",
            "defense": "Defense spending / geopolitical reshoring",
            "precious_metals": "Gold / de-dollarization bid",
            "energy_infra": "Energy / oil services cycle",
            "coal": "Coal demand / energy security",
            "osv_hulu": "Offshore support vessel day rate surge",
            "dry_bulk_shipping": "Dry bulk shipping / BDI cycle",
        }
        return sector_narrative.get(dom_sector, f"{dom_sector} sector momentum cluster")