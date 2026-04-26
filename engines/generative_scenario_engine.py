"""engines/generative_scenario_engine.py — Generative Scenario Discovery

Generates NOVEL scenarios not in historical transition matrix.
Combines macro events combinatorially → Monte Carlo probability scoring.

NO hardcoded scenarios. Only hardcoded event library + combination rules.
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass, field


@dataclass
class MacroEvent:
    name: str
    category: str          # "policy", "geopolitical", "supply_chain", "market_structure"
    growth_impact: float   # -1 to +1
    inflation_impact: float
    probability_base: float
    duration_weeks: int
    triggers: List[str]    # what events can co-occur
    inhibitors: List[str]  # what events block this


class GenerativeScenarioEngine:
    """Generate synthetic scenarios from event combinatorics."""

    def __init__(self, settings_module=None):
        self.cfg = settings_module
        # Event library: base building blocks (this IS hardcoded, but it's primitives, not scenarios)
        self.event_library: Dict[str, MacroEvent] = {
            "fed_cut_50bp": MacroEvent(
                name="Fed Cut 50bp", category="policy",
                growth_impact=0.40, inflation_impact=0.10,
                probability_base=0.15, duration_weeks=8,
                triggers=["credit_stress", "unemployment_spike"],
                inhibitors=["fed_hike", "inflation_reacceleration"],
            ),
            "fed_hike_25bp": MacroEvent(
                name="Fed Hike 25bp", category="policy",
                growth_impact=-0.30, inflation_impact=-0.20,
                probability_base=0.10, duration_weeks=12,
                triggers=["inflation_reacceleration", "wage_spiral"],
                inhibitors=["fed_cut_50bp", "recession_signs"],
            ),
            "china_stimulus_1t": MacroEvent(
                name="China Stimulus $1T", category="policy",
                growth_impact=0.50, inflation_impact=0.30,
                probability_base=0.20, duration_weeks=16,
                triggers=["property_crisis", "export_slowdown"],
                inhibitors=["trade_war_escalation"],
            ),
            "taiwan_blockade": MacroEvent(
                name="Taiwan Strait Blockade", category="geopolitical",
                growth_impact=-0.80, inflation_impact=0.60,
                probability_base=0.05, duration_weeks=24,
                triggers=["us_china_tension", "military_drill"],
                inhibitors=["diplomatic_breakthrough"],
            ),
            "ai_capex_surge": MacroEvent(
                name="AI Capex Surge $500B", category="supply_chain",
                growth_impact=0.60, inflation_impact=0.20,
                probability_base=0.35, duration_weeks=20,
                triggers=["nvda_beat", "hyperscaler_guidance_up"],
                inhibitors=["ai_bubble_burst", "regulatory_crackdown"],
            ),
            "ai_bubble_burst": MacroEvent(
                name="AI Bubble Burst", category="market_structure",
                growth_impact=-0.50, inflation_impact=-0.30,
                probability_base=0.10, duration_weeks=12,
                triggers=["nvda_miss", "valuation_extreme"],
                inhibitors=["ai_capex_surge"],
            ),
            "red_sea_closure": MacroEvent(
                name="Red Sea Full Closure", category="geopolitical",
                growth_impact=-0.30, inflation_impact=0.40,
                probability_base=0.08, duration_weeks=16,
                triggers=["houthi_escalation", "iran_tension"],
                inhibitors=["ceasefire"],
            ),
            "oil_shock_150": MacroEvent(
                name="Oil $150/bbl", category="supply_chain",
                growth_impact=-0.40, inflation_impact=0.70,
                probability_base=0.12, duration_weeks=12,
                triggers=["red_sea_closure", "opec_cut", "iran_blockade"],
                inhibitors=["recession_demand_destruction"],
            ),
            "dollar_crisis": MacroEvent(
                name="USD Crisis (DXY <95)", category="market_structure",
                growth_impact=0.20, inflation_impact=0.50,
                probability_base=0.10, duration_weeks=20,
                triggers=["fed_cut_50bp", "debt_ceiling_crisis", "brics_dedollarization"],
                inhibitors=["fed_hike_25bp", "safe_haven_flow"],
            ),
            "indonesia_nickel_ban": MacroEvent(
                name="Indonesia Nickel Export Ban", category="supply_chain",
                growth_impact=-0.10, inflation_impact=0.30,
                probability_base=0.15, duration_weeks=12,
                triggers=["resource_nationalism", "ev_demand_surge"],
                inhibitors=["wto_ruling", "trade_deal"],
            ),
        }

    def _score_event_compatibility(
        self,
        events: List[MacroEvent],
    ) -> float:
        """Score how compatible a set of events is (can they co-occur?)."""
        if len(events) < 2:
            return 1.0

        score = 1.0
        names = [e.name for e in events]

        for i, e1 in enumerate(events):
            for e2 in events[i+1:]:
                # Check inhibitors
                if e2.name in e1.inhibitors or e1.name in e2.inhibitors:
                    score *= 0.10  # Strongly incompatible
                # Check triggers
                elif e2.name in e1.triggers or e1.name in e2.triggers:
                    score *= 1.50  # Mutually reinforcing
                # Same category = moderate compatibility decay
                elif e1.category == e2.category:
                    score *= 0.80

        return float(np.clip(score, 0.01, 3.0))

    def _compute_scenario_quad(
        self,
        events: List[MacroEvent],
    ) -> Tuple[str, float, float, float]:
        """Aggregate event impacts into GIP coordinates."""
        total_g = sum(e.growth_impact * e.probability_base for e in events)
        total_i = sum(e.inflation_impact * e.probability_base for e in events)
        avg_prob = np.mean([e.probability_base for e in events])
        compat = self._score_event_compatibility(events)

        # Adjust by compatibility
        adjusted_g = total_g * compat
        adjusted_i = total_i * compat
        scenario_prob = avg_prob * compat * 0.5  # Joint probability dampening

        # Map to quad
        if adjusted_g > 0 and adjusted_i < 0:
            quad = "Q1"
        elif adjusted_g > 0 and adjusted_i > 0:
            quad = "Q2"
        elif adjusted_g < 0 and adjusted_i > 0:
            quad = "Q3"
        else:
            quad = "Q4"

        return quad, adjusted_g, adjusted_i, float(np.clip(scenario_prob, 0.001, 0.80))

    def generate_scenarios(
        self,
        max_events_per_scenario: int = 3,
        top_n: int = 10,
    ) -> List[Dict]:
        """Generate all valid event combinations → score → rank."""
        from itertools import combinations

        events = list(self.event_library.values())
        scenarios = []

        for r in range(1, max_events_per_scenario + 1):
            for combo in combinations(events, r):
                quad, g, i, prob = self._compute_scenario_quad(list(combo))

                if prob < 0.01:
                    continue

                scenario = {
                    "events": [e.name for e in combo],
                    "categories": list({e.category for e in combo}),
                    "predicted_quad": quad,
                    "growth_impact": round(g, 3),
                    "inflation_impact": round(i, 3),
                    "joint_probability": round(prob, 4),
                    "compatibility_score": round(self._score_event_compatibility(list(combo)), 3),
                    "duration_weeks": max(e.duration_weeks for e in combo),
                    "narrative_summary": " + ".join([e.name for e in combo]),
                }
                scenarios.append(scenario)

        # Sort by probability × impact magnitude
        scenarios.sort(
            key=lambda x: x["joint_probability"] * (abs(x["growth_impact"]) + abs(x["inflation_impact"])),
            reverse=True,
        )
        return scenarios[:top_n]

    def stress_test_portfolio(
        self,
        portfolio_tickers: List[str],
        prices: Dict[str, pd.Series],
        scenarios: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """Test portfolio against generated scenarios."""
        if scenarios is None:
            scenarios = self.generate_scenarios(top_n=5)

        results = []
        for sc in scenarios:
            portfolio_impacts = []
            for ticker in portfolio_tickers:
                close = pd.to_numeric(prices.get(ticker), errors="coerce").dropna()
                if len(close) < 30:
                    continue

                # Estimate sensitivity based on historical beta to macro proxies
                # Simplified: use volatility as proxy for sensitivity
                vol = float(close.pct_change().dropna().tail(63).std() * np.sqrt(252))
                sensitivity = min(vol * 2, 1.0)  # Cap at 100%

                # Direction based on sector + quad
                sector = "generic"
                if self.cfg:
                    sector = getattr(self.cfg, "TICKER_SECTOR", {}).get(ticker, "generic")

                # Quad playbook direction
                quad = sc["predicted_quad"]
                direction = 0
                if quad == "Q1":
                    direction = 1 if sector in {"ai_compute", "tech", "growth"} else 0
                elif quad == "Q3":
                    direction = -1 if sector in {"tech", "growth"} else 1 if sector in {"staples", "utilities", "gold"} else 0
                elif quad == "Q4":
                    direction = -1
                elif quad == "Q2":
                    direction = 1 if sector in {"commodity", "energy", "materials"} else 0

                expected_move = direction * sensitivity * (abs(sc["growth_impact"]) + abs(sc["inflation_impact"])) * 0.5
                portfolio_impacts.append({
                    "ticker": ticker,
                    "expected_move": round(expected_move, 3),
                    "sensitivity": round(sensitivity, 2),
                    "direction": direction,
                })

            if portfolio_impacts:
                avg_impact = np.mean([p["expected_move"] for p in portfolio_impacts])
                worst_impact = min(p["expected_move"] for p in portfolio_impacts)
                results.append({
                    "scenario": sc["narrative_summary"],
                    "quad": sc["predicted_quad"],
                    "probability": sc["joint_probability"],
                    "portfolio_avg_impact": round(avg_impact, 3),
                    "portfolio_worst_impact": round(worst_impact, 3),
                    "affected_tickers": [p for p in portfolio_impacts if abs(p["expected_move"]) > 0.02],
                })

        return results

    def run(
        self,
        portfolio_tickers: Optional[List[str]] = None,
        prices: Optional[Dict[str, pd.Series]] = None,
        top_n: int = 10,
    ) -> Dict:
        """Full generative scenario pipeline."""
        scenarios = self.generate_scenarios(top_n=top_n)

        stress_results = []
        if portfolio_tickers and prices:
            stress_results = self.stress_test_portfolio(portfolio_tickers, prices, scenarios[:5])

        return {
            "generated_scenarios": scenarios,
            "portfolio_stress_test": stress_results,
            "meta": {
                "event_library_size": len(self.event_library),
                "scenarios_generated": len(scenarios),
                "max_events_per_scenario": 3,
                "portfolio_tested": len(portfolio_tickers) if portfolio_tickers else 0,
            },
        }