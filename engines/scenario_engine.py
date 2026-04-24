"""engines/scenario_engine.py

Adaptive Scenario Discovery Engine.

Rather than static hardcoded scenarios, this engine:
1. Reads current quad state + signal state
2. Computes all plausible near-term transitions (from transition probability matrix)
3. Scores each scenario by: base probability × signal confirmation × leading indicators
4. Returns ranked scenarios with investment implications

"Scenarios are not forecasts. They are probabilistic maps of what the data
requires to be TRUE for each path." — McCullough framework
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np


# ---------------------------------------------------------------------------
# Transition matrix (calibrated from Hedgeye 27yr back-test patterns)
# Verified: "Quads follow each other like seasons in a continuous loop"
# ---------------------------------------------------------------------------

BASE_TRANSITIONS: Dict[str, Dict[str, float]] = {
    "Q1": {"Q1": 0.28, "Q2": 0.38, "Q4": 0.22, "Q3": 0.12},
    "Q2": {"Q2": 0.22, "Q3": 0.38, "Q1": 0.24, "Q4": 0.16},
    "Q3": {"Q3": 0.22, "Q4": 0.38, "Q2": 0.20, "Q1": 0.20},
    "Q4": {"Q4": 0.18, "Q1": 0.48, "Q3": 0.20, "Q2": 0.14},
}

# Monthly → structural transition modifiers
# If monthly is AHEAD of structural, structural likely moves there
MONTHLY_STRUCTURAL_ALIGNMENT_BONUS: Dict[str, float] = {
    "Q1→Q1": 0.10, "Q2→Q2": 0.10, "Q3→Q3": 0.10, "Q4→Q4": 0.10,
    # Monthly ahead of structural = structural likely to follow
    "Q3→Q2": 0.05,  # Monthly Q2 inside Structural Q3 = structural may improve
    "Q3→Q4": 0.05,  # Or get worse
    "Q4→Q1": 0.15,  # Recovery setup = strongest conviction
    "Q2→Q3": 0.08,  # Heating up
}

# Investment implications per transition path
TRANSITION_IMPLICATIONS: Dict[str, dict] = {
    "Q3→Q4": {
        "headline": "Stagflation → Deflation: Growth collapses, inflation cools",
        "best":  ["TLT","IEF","GLD","XLV","XLP","XLU","USD"],
        "worst": ["XLK","XLE","IWM","HYG","EM Equities"],
        "catalyst": "GDP nowcast rolls over, payrolls miss, ISM <48, Fed signal pivot",
        "conviction": "HIGH if growth data continues to decelerate",
    },
    "Q3→Q2": {
        "headline": "Stagflation → Reflation: Growth rebounds, inflation stays elevated",
        "best":  ["XLE","XLB","XLI","Commodities","EM commodity exporters","EWW","NORW"],
        "worst": ["TLT","Defensive bonds","Low beta"],
        "catalyst": "ISM rebounds >52, retail sales surprise, PMI acceleration",
        "conviction": "MODERATE — monthly Q2 signal leads structural confirmation",
    },
    "Q3→Q3": {
        "headline": "Stagflation Persistence: Stay defensive",
        "best":  ["GLD","XLV","XLP","XLU","TLT (partial)"],
        "worst": ["XLK","XLY","IWM","Credit","EM ex-commodity"],
        "catalyst": "CPI re-accelerates, ISM stays <50, payrolls miss",
        "conviction": "HIGH if inflation data re-accelerates",
    },
    "Q3→Q1": {
        "headline": "Stagflation → Goldilocks: Growth rebounds, inflation cools",
        "best":  ["SPY","QQQ","XLK","XLY","IWM","Credit"],
        "worst": ["GLD","Commodities","Defensive"],
        "catalyst": "CPI reversal, growth acceleration, Fed easing cycle",
        "conviction": "LOW — rare direct transition, requires simultaneous G↑ and I↓",
    },
    "Q4→Q1": {
        "headline": "Deflation → Goldilocks: MAXIMUM CONVICTION LONG",
        "best":  ["SPY","QQQ","XLK","XLI","IWM","Credit","EM equities"],
        "worst": ["GLD","Commodities","Defensive","TLT (rotate out)"],
        "catalyst": "Growth data accelerates, Fed cuts, liquidity injected, credit spreads tighten",
        "conviction": "VERY HIGH — Q4→Q1 is McCullough's highest conviction long setup",
    },
    "Q2→Q3": {
        "headline": "Reflation → Stagflation: Inflation wins, growth fades",
        "best":  ["GLD","XLV","XLP","Commodities (selective)"],
        "worst": ["XLK","XLY","Discretionary","Credit"],
        "catalyst": "Payrolls miss, ISM <50, CPI sticky, Fed overtightened",
        "conviction": "HIGH — classic late-cycle setup",
    },
    "Q1→Q2": {
        "headline": "Goldilocks → Reflation: Growth matures, inflation picks up",
        "best":  ["XLE","XLB","XLI","Commodities","Value","Cyclicals"],
        "worst": ["TLT","Defensive bonds","Low Beta"],
        "catalyst": "Breakevens rise, oil bid, ISM >55, retail strong",
        "conviction": "MODERATE — watch inflation prints for confirmation",
    },
    "Q2→Q1": {
        "headline": "Reflation → Goldilocks: Inflation cools, growth holds",
        "best":  ["SPY","XLK","XLY","QQQ","Credit"],
        "worst": ["Commodities","XLE","XLB"],
        "catalyst": "CPI decelerates, energy rolls, Fed on hold/cutting",
        "conviction": "MODERATE",
    },
    "Q4→Q3": {
        "headline": "Deflation → Stagflation: Supply shock or fiscal stimulus re-ignites inflation",
        "best":  ["GLD","Commodities","Energy","Defensive Equities"],
        "worst": ["TLT","Bonds","Tech"],
        "catalyst": "Oil spike, tariff shock, fiscal easing while growth flat",
        "conviction": "LOW — unusual path, requires supply-side catalyst",
    },
}


# ---------------------------------------------------------------------------
# Scenario dataclass
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    name: str
    from_quad: str
    to_quad: str
    probability: float
    confirmation_score: float    # how much current data confirms this path
    timeframe_weeks: int
    best_assets: List[str]
    worst_assets: List[str]
    catalyst: str
    conviction: str
    headline: str
    confirmation_triggers: List[str] = field(default_factory=list)
    invalidators: List[str] = field(default_factory=list)

    @property
    def weighted_score(self) -> float:
        return self.probability * (0.60 + 0.40 * self.confirmation_score)


# ---------------------------------------------------------------------------
# Confirmation triggers per transition
# ---------------------------------------------------------------------------

CONFIRMATION_TRIGGERS: Dict[str, List[str]] = {
    "Q3→Q4": ["Non-farm payrolls miss 2+ months", "ISM Manufacturing < 48", "CPI decelerates 2+ months",
               "Initial claims > 250k weekly", "GDP nowcast below 1.0%"],
    "Q3→Q2": ["ISM rebounds above 52", "Retail sales beat 2+ months", "S&P 500 breaks above TREND TRR",
               "IWM leads SPY by > 3% over 4 weeks", "PMI composite > 52"],
    "Q3→Q1": ["CPI 3-month average decelerates 50bps", "ISM > 52 and rising", "Fed signals cuts",
               "Oil 3M return < -10%", "Breakevens fall below 2.2%"],
    "Q4→Q1": ["Fed cuts ≥ 25bps", "ISM breaks back above 50", "Payrolls re-accelerate",
               "Credit spreads tighten 50bps+", "IWM breakout above TREND TRR"],
    "Q2→Q3": ["ISM falls below 50", "Payrolls miss 3 consecutive months", "CPI stays above 3%",
               "GDP nowcast below 2%", "Yield curve flattens aggressively"],
}

INVALIDATORS: Dict[str, List[str]] = {
    "Q3→Q4": ["ISM rebounds > 52", "Payrolls surprise > +250k", "CPI re-accelerates"],
    "Q3→Q2": ["CPI re-accelerates > 0.5% monthly", "ISM fails to hold above 50", "Dollar spikes"],
    "Q4→Q1": ["Credit event / banking stress", "Inflation re-ignites before growth firms", "Dollar crisis"],
    "Q2→Q3": ["Payrolls surprise to upside", "ISM holds > 52", "CPI decelerates sharply"],
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ScenarioEngine:
    """
    Adaptive scenario discovery from current macro data.
    Scores scenarios by data confirmation, not opinion.
    """

    def run(
        self,
        structural_quad: str,
        monthly_quad: str,
        features: Dict[str, float],
        flip_hazard: float = 0.3,
        data_coverage: float = 0.75,
    ) -> Dict[str, object]:

        # 1. Base transition probabilities
        base_probs = dict(BASE_TRANSITIONS.get(structural_quad, {}))

        # 2. Monthly quad adjustment
        monthly_key = f"{structural_quad}→{monthly_quad}"
        bonus = MONTHLY_STRUCTURAL_ALIGNMENT_BONUS.get(monthly_key, 0.0)
        if monthly_quad in base_probs:
            base_probs[monthly_quad] = min(base_probs[monthly_quad] + bonus, 0.99)

        # 3. Feature-based confirmation for each transition
        g_mom   = float(features.get("growth_momentum",   0.0))
        i_mom   = float(features.get("inflation_momentum", 0.0))
        policy  = float(features.get("policy_score",       0.0))
        leading = float(features.get("leading_indicator_composite", features.get("growth_momentum", 0.0)))

        # Adjust probabilities based on current signals
        if g_mom < -0.10:   # growth deteriorating → more likely to worsen
            base_probs["Q4"] = base_probs.get("Q4", 0.0) + 0.08
            base_probs["Q3"] = base_probs.get("Q3", 0.0) - 0.04
        if g_mom > 0.10:    # growth improving → more likely to improve
            base_probs["Q2"] = base_probs.get("Q2", 0.0) + 0.08
            base_probs["Q1"] = base_probs.get("Q1", 0.0) + 0.04
        if i_mom < -0.10:   # inflation cooling → shift toward Q1/Q4
            base_probs["Q1"] = base_probs.get("Q1", 0.0) + 0.06
            base_probs["Q4"] = base_probs.get("Q4", 0.0) + 0.06
        if i_mom > 0.10:    # inflation hot → shift toward Q2/Q3
            base_probs["Q2"] = base_probs.get("Q2", 0.0) + 0.05
            base_probs["Q3"] = base_probs.get("Q3", 0.0) + 0.05
        if policy > 0.15:   # easing → boost Q1/Q4 outcomes
            base_probs["Q1"] = base_probs.get("Q1", 0.0) + 0.05
            base_probs["Q4"] = base_probs.get("Q4", 0.0) + 0.03

        # Normalise
        total = sum(base_probs.values())
        if total > 0:
            base_probs = {k: v/total for k,v in base_probs.items()}

        # 4. Build confirmation scores for each to_quad
        def _conf_score(to_quad: str) -> float:
            """How strongly does current data confirm transition to to_quad?"""
            if to_quad == "Q1":
                return float(np.clip(0.5 - 0.8*i_mom + 0.8*g_mom + 0.3*policy, 0.0, 1.0))
            elif to_quad == "Q2":
                return float(np.clip(0.5 + 0.6*i_mom + 0.6*g_mom, 0.0, 1.0))
            elif to_quad == "Q3":
                return float(np.clip(0.5 + 0.8*i_mom - 0.8*g_mom, 0.0, 1.0))
            elif to_quad == "Q4":
                return float(np.clip(0.5 - 0.8*i_mom - 0.8*g_mom + 0.4*policy, 0.0, 1.0))
            return 0.5

        # 5. Build scenario objects
        scenarios: List[Scenario] = []
        for to_quad, prob in sorted(base_probs.items(), key=lambda kv: kv[1], reverse=True):
            path_key = f"{structural_quad}→{to_quad}"
            impl = TRANSITION_IMPLICATIONS.get(path_key, {})
            conf_s = _conf_score(to_quad)

            # Timeframe estimate: stay in same quad = 4-12w, change = 6-16w
            tf = 6 if to_quad == structural_quad else 10

            scenarios.append(Scenario(
                name=f"{structural_quad}→{to_quad}",
                from_quad=structural_quad,
                to_quad=to_quad,
                probability=prob,
                confirmation_score=conf_s,
                timeframe_weeks=tf,
                best_assets=impl.get("best", []),
                worst_assets=impl.get("worst", []),
                catalyst=impl.get("catalyst", "Data-dependent"),
                conviction=impl.get("conviction", "MODERATE"),
                headline=impl.get("headline", f"{structural_quad} → {to_quad}"),
                confirmation_triggers=CONFIRMATION_TRIGGERS.get(path_key, []),
                invalidators=INVALIDATORS.get(path_key, []),
            ))

        # Sort by weighted score
        scenarios.sort(key=lambda s: s.weighted_score, reverse=True)

        # 6. Summary
        base_case = scenarios[0]
        alt_case  = scenarios[1] if len(scenarios) > 1 else None

        return dict(
            scenarios=scenarios,
            base_case=base_case,
            alt_case=alt_case,
            current_quad=structural_quad,
            monthly_quad=monthly_quad,
            flip_hazard=flip_hazard,
            regime_stability="stable" if base_case.probability > 0.40 else "unstable",
            inputs=dict(g_mom=g_mom, i_mom=i_mom, policy=policy, leading=leading),
        )
