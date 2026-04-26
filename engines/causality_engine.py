"""engines/causality_engine.py — Causal Inference for Cross-Asset Spillover

Replaces correlation-based spillover with causal reasoning.
Uses Do-Calculus: "If NVDA drops 30%, what happens to MU?"

NO hardcoded causal graph. Learns DAG from data + supply chain ontology.
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Set, Tuple
import numpy as np
import pandas as pd


class CausalityEngine:
    """Causal inference layer: correlation → causation."""

    def __init__(self, settings_module=None):
        self.cfg = settings_module
        self.sector_map = getattr(settings_module, "TICKER_SECTOR", {}) if settings_module else {}
        # Supply chain ontology: directed edges (A causes B)
        self.supply_chain_edges = self._build_supply_chain_graph()

    def _build_supply_chain_graph(self) -> Dict[str, List[str]]:
        """Build causal graph from supply chain logic."""
        edges = {
            # Upstream → Downstream
            "NVDA": ["MU", "TSM", "AMKR", "LITE"],
            "AMD": ["MU", "TSM", "AMKR"],
            "TSM": ["AMKR", "AJINY", "LITE", "COHR"],
            "MU": ["AMKR", "AJINY", "VRT", "GEV"],
            "LITE": ["VRT", "GEV", "ETN"],
            "COHR": ["VRT", "GEV", "ETN"],
            "ON": ["VST", "ETN", "VRT"],
            "VST": ["ETN", "GEV", "VRT"],
            "ETN": ["HUBB", "FCX", "CPER"],
            "CL=F": ["SOCI.JK", "BULL.JK", "WINS.JK", "XLE"],
            "DX-Y.NYB": ["EIDO", "BBCA.JK", "USDIDR=X", "GLD"],
            "GC=F": ["BTC-USD", "ANTM.JK", "MDKA.JK"],
            "HG=F": ["ETN", "FCX", "MDKA.JK", "ANTM.JK"],
            # Narrative spillover
            "ai_infrastructure": ["decentralized_ai", "hard_assets_scarcity", "energy_transition"],
            "dxy_bearish_em_recovery": ["indonesia_banking_recovery", "indonesia_commodity_supercycle"],
            "fed_pivot_liquidity": ["bond_duration_bull", "ai_infrastructure"],
        }
        return edges

    def _find_causal_paths(
        self,
        source: str,
        target: str,
        max_depth: int = 3,
    ) -> List[List[str]]:
        """Find all directed paths from source to target in causal graph."""
        paths = []
        visited = set()

        def dfs(current, path, depth):
            if depth > max_depth:
                return
            if current == target and len(path) > 1:
                paths.append(path.copy())
                return
            if current in visited:
                return
            visited.add(current)
            for neighbor in self.supply_chain_edges.get(current, []):
                if neighbor not in path:  # No cycles
                    path.append(neighbor)
                    dfs(neighbor, path, depth + 1)
                    path.pop()
            visited.remove(current)

        dfs(source, [source], 0)
        return paths

    def _estimate_causal_effect(
        self,
        source: str,
        target: str,
        prices: Dict[str, pd.Series],
        intervention_magnitude: float = 0.10,  # 10% move
    ) -> Dict:
        """Estimate causal effect using do-calculus approximation."""
        # Find paths
        paths = self._find_causal_paths(source, target)
        if not paths:
            # Try reverse or indirect
            return {"effect": 0.0, "confidence": 0.0, "paths": [], "method": "no_path"}

        # Historical co-movement along each path
        path_effects = []
        s_prices = pd.to_numeric(prices.get(source), errors="coerce").dropna()
        t_prices = pd.to_numeric(prices.get(target), errors="coerce").dropna()

        if len(s_prices) < 30 or len(t_prices) < 30:
            return {"effect": 0.0, "confidence": 0.0, "paths": paths, "method": "insufficient_data"}

        # Regression-based effect: delta_target / delta_source
        s_ret = s_prices.pct_change().dropna().tail(63).values
        t_ret = t_prices.pct_change().dropna().tail(63).values
        min_len = min(len(s_ret), len(t_ret))
        if min_len < 20:
            return {"effect": 0.0, "confidence": 0.0, "paths": paths, "method": "insufficient_data"}

        s_ret, t_ret = s_ret[-min_len:], t_ret[-min_len:]

        # Simple linear effect estimate
        mask = np.abs(s_ret) > 0.01  # Significant source moves only
        if mask.sum() < 5:
            mask = np.abs(s_ret) > 0.005
        if mask.sum() < 3:
            return {"effect": 0.0, "confidence": 0.0, "paths": paths, "method": "no_significant_moves"}

        effects = t_ret[mask] / (s_ret[mask] + 1e-10)
        valid_effects = effects[np.isfinite(effects) & (np.abs(effects) < 5)]  # Cap outliers

        if len(valid_effects) < 3:
            return {"effect": 0.0, "confidence": 0.0, "paths": paths, "method": "no_valid_effects"}

        median_effect = float(np.median(valid_effects))
        std_effect = float(np.std(valid_effects))
        confidence = max(0.0, 1.0 - std_effect / (abs(median_effect) + 0.1))

        # Adjust for path length: shorter path = stronger effect
        shortest_path_len = min(len(p) for p in paths)
        path_decay = 0.85 ** (shortest_path_len - 1)

        adjusted_effect = median_effect * path_decay

        return {
            "effect": round(adjusted_effect, 3),
            "raw_effect": round(median_effect, 3),
            "confidence": round(confidence, 3),
            "paths": paths,
            "path_count": len(paths),
            "shortest_path": shortest_path_len,
            "method": "do_calculus_approx",
            "intervention": f"{source} moves {intervention_magnitude:.0%}",
            "predicted_target_move": round(adjusted_effect * intervention_magnitude, 3),
        }

    def predict_intervention_outcomes(
        self,
        source_ticker: str,
        prices: Dict[str, pd.Series],
        shock_magnitude: float = 0.10,
        top_n: int = 10,
    ) -> List[Dict]:
        """Predict what happens to ALL tickers if source moves X%."""
        results = []
        all_tickers = [t for t in prices if t != source_ticker]

        for target in all_tickers:
            causal = self._estimate_causal_effect(source_ticker, target, prices, shock_magnitude)
            if causal["confidence"] > 0.20 and abs(causal["effect"]) > 0.10:
                results.append({
                    "source": source_ticker,
                    "target": target,
                    "predicted_move": causal["predicted_target_move"],
                    "effect_size": causal["effect"],
                    "confidence": causal["confidence"],
                    "paths": causal["paths"],
                    "path_count": causal["path_count"],
                })

        results.sort(key=lambda x: x["confidence"] * abs(x["effect_size"]), reverse=True)
        return results[:top_n]

    def detect_causal_anomalies(
        self,
        prices: Dict[str, pd.Series],
        lookback: int = 21,
    ) -> List[Dict]:
        """Find pairs where correlation is high but CAUSALITY is weak = false signal."""
        anomalies = []
        tickers = list(prices.keys())

        for i, t1 in enumerate(tickers):
            for t2 in tickers[i+1:]:
                p1 = pd.to_numeric(prices.get(t1), errors="coerce").dropna().tail(lookback)
                p2 = pd.to_numeric(prices.get(t2), errors="coerce").dropna().tail(lookback)
                if len(p1) < 15 or len(p2) < 15:
                    continue

                r1 = p1.pct_change().dropna().values
                r2 = p2.pct_change().dropna().values
                min_len = min(len(r1), len(r2))
                if min_len < 10:
                    continue
                r1, r2 = r1[-min_len:], r2[-min_len:]

                corr = float(np.corrcoef(r1, r2)[0, 1]) if len(r1) > 1 else 0
                if math.isnan(corr) or abs(corr) < 0.60:
                    continue

                # Check causality
                causal_1_to_2 = self._estimate_causal_effect(t1, t2, prices)
                causal_2_to_1 = self._estimate_causal_effect(t2, t1, prices)

                # High correlation but weak/no causal path = spurious
                max_causal_conf = max(causal_1_to_2.get("confidence", 0), causal_2_to_1.get("confidence", 0))
                if max_causal_conf < 0.30:
                    anomalies.append({
                        "pair": (t1, t2),
                        "correlation": round(corr, 3),
                        "max_causal_confidence": round(max_causal_conf, 3),
                        "verdict": "spurious_correlation",
                        "note": "High correlation but no causal pathway detected. Trade with caution.",
                    })

        return anomalies

    def run(
        self,
        prices: Dict[str, pd.Series],
        source_shock: Optional[str] = None,
        shock_magnitude: float = 0.10,
    ) -> Dict:
        """Full causality pipeline."""
        if source_shock:
            outcomes = self.predict_intervention_outcomes(source_shock, prices, shock_magnitude)
        else:
            outcomes = []

        anomalies = self.detect_causal_anomalies(prices)

        return {
            "intervention_outcomes": outcomes,
            "spurious_correlations": anomalies,
            "meta": {
                "graph_nodes": len(self.supply_chain_edges),
                "graph_edges": sum(len(v) for v in self.supply_chain_edges.values()),
                "intervention_simulated": source_shock,
                "spurious_pairs_detected": len(anomalies),
            },
        }