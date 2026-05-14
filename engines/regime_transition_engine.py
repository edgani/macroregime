"""engines/regime_transition_engine.py — Regime Transition Engine v1.0
Predicts probability of regime shift using momentum, macro, and options flow.
"""
import logging, math
from typing import Dict, List
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

QUAD_ORDER = ["Q1", "Q2", "Q3", "Q4"]

class RegimeTransitionEngine:
    """Predicts regime transition probabilities with time horizon."""

    def __init__(self):
        pass

    def _momentum_score(self, prices: Dict, fred: Dict) -> Dict:
        """Score momentum direction for each quad."""
        scores = {}
        # Q1 proxy: SPY + QQQ momentum
        for q, tickers in {
            "Q1": ["SPY", "QQQ", "IWM"],
            "Q2": ["EEM", "VWO", "FXI", "XLE"],
            "Q3": ["GC=F", "GLD", "TLT", "XLU", "XLP"],
            "Q4": ["UUP", "DX-Y.NYB", "SHY", "XLU"],
        }.items():
            rets = []
            for t in tickers:
                s = prices.get(t)
                if s is not None and len(s) >= 22:
                    try:
                        s = pd.to_numeric(s, errors="coerce").dropna()
                        if len(s) >= 22:
                            rets.append(float(s.iloc[-1] / s.iloc[-22] - 1))
                    except Exception:
                        pass
            scores[q] = sum(rets) / len(rets) if rets else 0.0
        return scores

    def _macro_score(self, fred: Dict, current_quad: str) -> Dict:
        """Score macro conditions favoring each quad."""
        scores = {}
        # Inflation proxy
        cpi = fred.get("CPI")
        core = fred.get("CORECPI")
        inf_rate = 0.03
        if cpi is not None and len(cpi) >= 2:
            try:
                inf_rate = float(cpi.iloc[-1] / cpi.iloc[-2] - 1)
            except Exception:
                pass
        # Growth proxy
        indpro = fred.get("INDPRO")
        growth = 0.02
        if indpro is not None and len(indpro) >= 4:
            try:
                growth = float(indpro.iloc[-1] / indpro.iloc[-4] - 1)
            except Exception:
                pass
        # Rates
        dgs10 = fred.get("DGS10")
        rate = 4.5
        if dgs10 is not None and len(dgs10) > 0:
            try:
                rate = float(dgs10.iloc[-1])
            except Exception:
                pass
        # Yield curve
        dgs2 = fred.get("DGS2")
        spread = 0
        if dgs10 is not None and dgs2 is not None:
            try:
                spread = float(dgs10.iloc[-1]) - float(dgs2.iloc[-1])
            except Exception:
                pass
        # Unemployment
        unrate = fred.get("UNRATE")
        unemp = 4.0
        if unrate is not None and len(unrate) > 0:
            try:
                unemp = float(unrate.iloc[-1])
            except Exception:
                pass
        # Score each quad
        scores["Q1"] = 0.3 + growth * 5 - unemp * 0.05  # Goldilocks: growth up, unemp low
        scores["Q2"] = 0.2 + inf_rate * 10 + growth * 3  # Reflation: inflation up
        scores["Q3"] = 0.3 + inf_rate * 5 - growth * 3 + (0.1 if spread < 0 else 0)  # Stagflation: inflation up, growth down
        scores["Q4"] = 0.2 - growth * 5 + (0.2 if unemp > 4.5 else 0) + (0.1 if rate > 5 else 0)  # Deflation: growth down, unemp up
        return scores

    def _options_flow_score(self, prices: Dict) -> Dict:
        """Score based on options skew and VIX."""
        scores = {}
        vix = prices.get("^VIX")
        vix_val = float(vix.iloc[-1]) if vix is not None and len(vix) > 0 else 20.0
        vvix = prices.get("VVIX")
        vvix_val = float(vvix.iloc[-1]) if vvix is not None and len(vvix) > 0 else vix_val * 1.2
        # High VIX + high VVIX = Q3/Q4 risk
        scores["Q1"] = 0.3 - (vix_val - 15) * 0.01
        scores["Q2"] = 0.2 - (vix_val - 20) * 0.005
        scores["Q3"] = 0.2 + (vix_val - 20) * 0.01 + (vvix_val - vix_val) * 0.005
        scores["Q4"] = 0.2 + (vix_val - 25) * 0.01 + (vvix_val - vix_val) * 0.01
        return scores

    def run(self, prices: Dict, fred: Dict, current_quad: str = "Q3", current_probs: Dict = None) -> Dict:
        """Main entry: predict transition probabilities."""
        import pandas as pd
        mom = self._momentum_score(prices, fred)
        macro = self._macro_score(fred, current_quad)
        opt = self._options_flow_score(prices)
        # Combine scores
        combined = {}
        for q in QUAD_ORDER:
            combined[q] = mom.get(q, 0) * 0.35 + macro.get(q, 0) * 0.45 + opt.get(q, 0) * 0.20
        # Normalize
        total = sum(max(0, v) for v in combined.values())
        if total > 0:
            combined = {k: max(0, v) / total for k, v in combined.items()}
        # Transition matrix: probability of moving from current to target
        transitions = {}
        for target in QUAD_ORDER:
            if target == current_quad:
                # Stay probability: higher if current quad score is highest
                stay_boost = 0.3 if combined.get(target, 0) == max(combined.values()) else 0.1
                transitions[target] = {
                    "30d": round(min(0.8, combined.get(target, 0.25) + stay_boost), 3),
                    "60d": round(min(0.7, combined.get(target, 0.20) + stay_boost * 0.8), 3),
                    "90d": round(min(0.6, combined.get(target, 0.15) + stay_boost * 0.6), 3),
                }
            else:
                # Shift probability
                base = combined.get(target, 0)
                # Adjacent quads have higher transition probability
                curr_idx = QUAD_ORDER.index(current_quad)
                target_idx = QUAD_ORDER.index(target)
                adjacency_boost = 0.1 if abs(curr_idx - target_idx) == 1 else 0.0
                transitions[target] = {
                    "30d": round(min(0.5, base * 0.6 + adjacency_boost), 3),
                    "60d": round(min(0.6, base * 0.8 + adjacency_boost * 1.2), 3),
                    "90d": round(min(0.7, base + adjacency_boost * 1.5), 3),
                }
        # Find most likely transition
        best_target = max(transitions.keys(), key=lambda k: transitions[k]["60d"])
        return {
            "current_quad": current_quad,
            "momentum_scores": {k: round(v, 3) for k, v in mom.items()},
            "macro_scores": {k: round(v, 3) for k, v in macro.items()},
            "options_scores": {k: round(v, 3) for k, v in opt.items()},
            "combined_scores": {k: round(v, 3) for k, v in combined.items()},
            "transitions": transitions,
            "most_likely_60d": best_target,
            "most_likely_prob_60d": transitions[best_target]["60d"],
            "summary": f"{current_quad} → {best_target} in 60d: {transitions[best_target]['60d']:.0%} prob",
        }


def run_regime_transition(prices: Dict, fred: Dict, current_quad: str = "Q3", current_probs: Dict = None) -> Dict:
    engine = RegimeTransitionEngine()
    return engine.run(prices, fred, current_quad, current_probs)
