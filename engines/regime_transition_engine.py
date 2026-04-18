from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

from utils.math_utils import clamp01


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TransitionPath:
    from_quad: str
    to_quad: str
    probability: float                  # 0-1: probability this transition occurs in timeframe
    timeframe_weeks: int               # estimated weeks to transition
    early_warning_score: float         # 0-1: how many early warning signals are firing
    confirmation_needed: List[str]     # what needs to happen to CONFIRM the transition
    invalidators: List[str]            # what would KILL this transition thesis
    asset_implications: Dict[str, str] # {asset_class: "bullish|bearish|neutral|selective"}
    confidence: float                  # 0-1: confidence in the probability estimate


@dataclass
class RegimeTransitionOutput:
    current_quad: str
    current_monthly_quad: str
    most_likely_next: str
    transition_paths: List[TransitionPath]  # sorted by probability desc
    early_warning_signals: Dict[str, float]  # named signals and their current scores
    leading_composite: float                 # overall forward-looking score
    front_run_window: str                    # "now" | "1-2w" | "3-6w" | "not yet"
    front_run_rationale: str


# ---------------------------------------------------------------------------
# Transition condition library
# Each entry defines the economic logic for a quad-to-quad transition
# ---------------------------------------------------------------------------

_TRANSITION_LIBRARY: Dict[str, Dict] = {
    # ---- Q1 → Q2 (growth stays up, inflation starts accelerating) ----
    "Q1→Q2": {
        "trigger_logic": "Growth cycle matures, commodity/energy demand builds, inflation starts re-accelerating while growth still robust.",
        "early_warning_thresholds": {
            "inflation_momentum_rising":   lambda m: m.get("inflation_momentum", 0.0) > 0.15,
            "breakeven_widening":          lambda m: m.get("breakeven_1m_delta", 0.0) > 0.05,
            "oil_bid":                     lambda m: m.get("oil_3m", 0.0) > 0.08,
            "gold_bid":                    lambda m: m.get("gold_3m", 0.0) > 0.06,
            "ism_still_above_50":          lambda m: m.get("ism_last", 50.0) > 50.0,
            "growth_level_positive":       lambda m: m.get("growth_level", 0.0) > 0.10,
        },
        "confirmation_needed": [
            "CPI or PCE prints higher than consensus for 2+ consecutive months",
            "Breakeven inflation rises above 2.5% and holds",
            "ISM stays above 52 while oil holds bid",
        ],
        "invalidators": [
            "Oil reverses sharply (>10%) — removes the inflation push",
            "ISM drops below 50 — growth side of Q2 collapses",
            "Breakevens fall back below 2.2%",
        ],
        "base_probability": 0.15,
        "typical_timeframe_weeks": 8,
        "asset_implications": {
            "us_equities": "selective — energy/materials/cyclicals outperform; bonds underperform",
            "ihsg": "neutral to bearish — commodity exporters (coal) up, importers down",
            "commodities": "bullish — energy, base metals bid",
            "fx": "commodity currencies (AUD, CAD, petro-FX) outperform; USD mixed",
            "bonds": "bearish duration — yields rise as inflation re-accelerates",
            "crypto": "selective — BTC may hold, alts vulnerable if rates bite",
        },
    },

    # ---- Q1 → Q4 (growth starts fading, inflation stays well-behaved) ----
    "Q1→Q4": {
        "trigger_logic": "Late-cycle growth fatigue. ISM peaks and rolls over. Hiring slows. But inflation stays contained — deflationary risk, not stagflation.",
        "early_warning_thresholds": {
            "growth_momentum_falling":     lambda m: m.get("growth_momentum", 0.0) < -0.10,
            "ism_deteriorating":           lambda m: m.get("ism_3m_delta", 0.0) < -2.0,
            "claims_rising":               lambda m: m.get("claims_13w_delta", 0.0) > 0.0,
            "housing_rolling_over":        lambda m: m.get("housing_yoy", 0.0) < 0.0,
            "inflation_still_contained":   lambda m: m.get("inflation_momentum", 0.0) < 0.10,
            "leading_indicator_fading":    lambda m: m.get("leading_indicator_composite", 0.0) < -0.05,
        },
        "confirmation_needed": [
            "ISM prints sub-50 for 2 consecutive months",
            "Payrolls growth rate decelerates for 3+ months",
            "Inflation stays below 3% — no reacceleration",
        ],
        "invalidators": [
            "ISM rebounds above 52 on new order improvement",
            "Fiscal stimulus lands and revives demand",
            "Oil spike triggers inflation reaccel → routes to Q2/Q3 instead",
        ],
        "base_probability": 0.12,
        "typical_timeframe_weeks": 10,
        "asset_implications": {
            "us_equities": "defensive rotation — quality, dividend, low-vol outperform",
            "ihsg": "bearish — growth scare hurts commodity demand and export outlook",
            "commodities": "bearish — demand destruction narrative",
            "fx": "USD safe haven; EM under pressure",
            "bonds": "bullish duration — yields fall as growth fears dominate",
            "crypto": "bearish — risk-off dominates",
        },
    },

    # ---- Q2 → Q3 (growth decelerates but inflation stays hot — stagflation) ----
    "Q2→Q3": {
        "trigger_logic": "Growth peaks and rolls over while inflation remains hot or re-accelerates. Policy overtightening or supply shock. Most dangerous regime for asset prices.",
        "early_warning_thresholds": {
            "growth_momentum_falling":     lambda m: m.get("growth_momentum", 0.0) < -0.05,
            "ism_rolling_over":            lambda m: m.get("ism_3m_delta", 0.0) < -1.5,
            "inflation_sticky":            lambda m: m.get("inflation_level", 0.0) > 0.20,
            "oil_shock_active":            lambda m: m.get("oil_3m", 0.0) > 0.12,
            "claims_rising":               lambda m: m.get("claims_13w_delta", 0.0) > 0.0,
            "smallcap_rolling_over":       lambda m: m.get("slowdown_flags", 0.0) >= 0.50,
        },
        "confirmation_needed": [
            "ISM drops below 50 while CPI stays above 4%",
            "Claims rise for 2+ consecutive months",
            "Fed stays hawkish despite slowing growth",
        ],
        "invalidators": [
            "Oil drops sharply — removes stagflation fuel",
            "Fed signals pause/pivot — relieves supply-side pressure",
            "Growth data surprises to the upside (ISM re-accelerates)",
        ],
        "base_probability": 0.10,
        "typical_timeframe_weeks": 8,
        "asset_implications": {
            "us_equities": "bearish broad tape — energy/commodities only safe harbor",
            "ihsg": "split — coal exporters still OK, rupiah and importers under severe pressure",
            "commodities": "bullish energy/gold, bearish base metals (demand destruction)",
            "fx": "USD strong; EM commodity importers (IDR, INR) extremely fragile",
            "bonds": "extremely bearish duration — worst of all worlds",
            "crypto": "bearish — liquidity removal AND growth scare",
        },
    },

    # ---- Q3 → Q4 (inflation finally breaks down, growth still weak) ----
    "Q3→Q4": {
        "trigger_logic": "Supply shock fades or policy succeeds in crushing inflation. Growth still weak but inflation is finally decelerating. Market re-rates toward deflation risk.",
        "early_warning_thresholds": {
            "inflation_momentum_falling":  lambda m: m.get("inflation_momentum", 0.0) < 0.0,
            "oil_retreating":              lambda m: m.get("oil_3m", 0.0) < 0.0,
            "breakevens_falling":          lambda m: m.get("breakeven_1m_delta", 0.0) < -0.05,
            "growth_still_weak":           lambda m: m.get("growth_momentum", 0.0) < -0.10,
            "inflation_shock_fading":      lambda m: m.get("inflation_shock", 0.0) < 0.10,
            "cpi_deceleration":            lambda m: m.get("cpi_roc_3m", 0.0) < 0.0,
        },
        "confirmation_needed": [
            "CPI prints sub-expectations for 2+ consecutive months",
            "Breakevens fall below 2.3% and hold",
            "Oil retreats >10% from peak — supply shock officially dissipating",
        ],
        "invalidators": [
            "Oil re-spikes — supply disruption resumes",
            "Wage spiral takes over even as energy prices fall",
            "Fed keeps hiking aggressively causing financial accident instead",
        ],
        "base_probability": 0.12,
        "typical_timeframe_weeks": 8,
        "asset_implications": {
            "us_equities": "still defensive but quality bonds start working again",
            "ihsg": "remains bearish — growth still weak, relief only if commodity pain eases",
            "commodities": "bearish — de-inflation narrative kills the commodity bid",
            "fx": "USD begins to fade; emerging market FX starts to breathe",
            "bonds": "bullish duration begins — duration starts working as inflation falls",
            "crypto": "still bearish — growth weak, liquidity not yet restored",
        },
    },

    # ---- Q4 → Q1 (the full-cycle transition — Fed pivots, growth recovers) ----
    "Q4→Q1": {
        "trigger_logic": "Policy easing lands. Leading indicators begin turning. Growth starts re-accelerating while inflation stays contained. Best risk-on setup in the cycle.",
        "early_warning_thresholds": {
            "growth_momentum_turning":     lambda m: m.get("growth_momentum", 0.0) > 0.0,
            "leading_indicator_turning":   lambda m: m.get("leading_indicator_composite", 0.0) > 0.0,
            "ism_recovering":              lambda m: m.get("ism_3m_delta", 0.0) > 0.0,
            "claims_improving":            lambda m: m.get("claims_13w_delta", 0.0) < 0.0,
            "policy_easing":               lambda m: m.get("policy_score", 0.0) > 0.10,
            "inflation_still_contained":   lambda m: m.get("inflation_momentum", 0.0) < 0.15,
        },
        "confirmation_needed": [
            "ISM prints above 50 for 2 consecutive months",
            "Claims trend turns down for 3+ consecutive weeks",
            "Payrolls growth stabilizes above 150k/month",
            "Inflation stays below 3% — no reaccel from policy ease",
        ],
        "invalidators": [
            "Inflation re-accelerates above 4% as policy eases",
            "ISM recovery stalls — demand not responding to easing",
            "Credit event disrupts the recovery path",
        ],
        "base_probability": 0.10,
        "typical_timeframe_weeks": 12,
        "asset_implications": {
            "us_equities": "bullish broad — growth recovery; small caps, equal-weight outperform",
            "ihsg": "bullish — EM inflows return; domestic demand recovers",
            "commodities": "selective bullish — base metals bid, energy depends on supply",
            "fx": "USD weakens; EM FX recovers broadly",
            "bonds": "neutral to mildly bearish duration — yields stabilize as growth returns",
            "crypto": "bullish — risk appetite and liquidity both improving",
        },
    },

    # ---- Q3 → Q2 (false dawn — growth doesn't recover, market tests transition) ----
    "Q3→Q2": {
        "trigger_logic": "Inflation stays hot and growth appears to stabilize (fiscal boost or commodity-led demand). Market briefly prices Q2 but structural growth weak — often a head-fake.",
        "early_warning_thresholds": {
            "growth_stabilizing":          lambda m: m.get("growth_momentum", 0.0) > -0.05,
            "inflation_still_hot":         lambda m: m.get("inflation_momentum", 0.0) > 0.10,
            "oil_still_bid":               lambda m: m.get("oil_3m", 0.0) > 0.05,
            "policy_still_tight":          lambda m: m.get("policy_score", 0.0) < 0.0,
        },
        "confirmation_needed": [
            "ISM actually holds above 51 for 3+ months (not just one bounce)",
            "Payrolls stay robust (>200k/month) while inflation stays above 3%",
        ],
        "invalidators": [
            "ISM falls back below 50 — growth bounce was a head-fake",
            "Credit spreads widen — real economy stress showing",
            "Fiscal impulse fades — no structural demand driver",
        ],
        "base_probability": 0.08,
        "typical_timeframe_weeks": 6,
        "asset_implications": {
            "us_equities": "short-lived risk rally; energy/materials still lead",
            "ihsg": "cautious bounce — exporters up, but IDR fragile if USD stays bid",
            "commodities": "still bullish if sustained",
            "fx": "commodity currencies bounce; USD mildly pressured",
            "bonds": "still bearish duration",
            "crypto": "selective risk-on trade possible if growth narrative sticks",
        },
    },
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class RegimeTransitionEngine:
    """Forward-looking regime transition detection.

    Computes probability-weighted transition paths from the current regime,
    using early warning signals from macro data, market prices, and news.

    This is what enables FRONT-RUNNING: identifying regime changes 4-12 weeks
    before the market fully prices them.
    """

    def _compute_early_warning_score(
        self,
        path_key: str,
        macro: Dict[str, float],
    ) -> float:
        """Count what fraction of early warning signals are firing for this path."""
        template = _TRANSITION_LIBRARY.get(path_key, {})
        thresholds = template.get("early_warning_thresholds", {})
        if not thresholds:
            return 0.0

        firing = sum(
            1.0 for _, condition_fn in thresholds.items()
            if _safe_eval(condition_fn, macro)
        )
        return clamp01(firing / len(thresholds))

    def _compute_transition_probability(
        self,
        path_key: str,
        macro: Dict[str, float],
        news_state: Dict[str, object],
        shock_strength: float,
        flip_hazard: float,
        monthly_quad: str,
    ) -> float:
        template = _TRANSITION_LIBRARY.get(path_key, {})
        base = template.get("base_probability", 0.10)
        ew_score = self._compute_early_warning_score(path_key, macro)
        from_q, to_q = path_key.split("→")

        # Monthly quad already pointing toward target = confirmation boost
        monthly_confirm = 0.08 if monthly_quad == to_q else 0.0

        # Flip hazard = general instability → boosts all non-base transitions slightly
        hazard_boost = 0.05 * flip_hazard

        # Shock state can accelerate transitions toward Q3 or Q4
        shock_boost = 0.0
        if shock_strength > 0.55:
            if to_q in ("Q3", "Q4"):
                shock_boost = 0.08 * shock_strength

        # News regime_shift_probability for matching target quad
        news_boost = 0.0
        front_run = news_state.get("front_run") or {}
        if isinstance(front_run, dict):
            if front_run.get("toward_quad") == to_q:
                news_boost = 0.10 * float(front_run.get("shift_probability", 0.0))

        prob = base + 0.30 * ew_score + monthly_confirm + hazard_boost + shock_boost + news_boost
        return clamp01(prob)

    def run(
        self,
        macro: Dict[str, float],
        market: Dict[str, float],
        regime_posterior,     # RegimePosterior dataclass
        news_state: Dict[str, object] | None = None,
        shock_strength: float = 0.0,
    ) -> RegimeTransitionOutput:
        news_state = news_state or {}
        current_quad = getattr(regime_posterior, "structural_quad", "Q?")
        monthly_quad = getattr(regime_posterior, "monthly_quad", current_quad)
        flip_hazard = float(getattr(regime_posterior, "flip_hazard", 0.30))

        # Relevant paths from current quad (all possible transitions)
        relevant_paths = [k for k in _TRANSITION_LIBRARY if k.startswith(f"{current_quad}→")]

        # Also include cross-path if monthly quad already shows a different quadrant
        # (monthly divergence = structural is being pulled toward a transition)
        if monthly_quad != current_quad:
            cross_path = f"{current_quad}→{monthly_quad}"
            if cross_path not in relevant_paths and cross_path in _TRANSITION_LIBRARY:
                relevant_paths.append(cross_path)

        paths: List[TransitionPath] = []
        for path_key in relevant_paths:
            template = _TRANSITION_LIBRARY[path_key]
            _, to_q = path_key.split("→")
            prob = self._compute_transition_probability(
                path_key, macro, news_state, shock_strength, flip_hazard, monthly_quad
            )
            ew_score = self._compute_early_warning_score(path_key, macro)
            timeframe = template.get("typical_timeframe_weeks", 8)

            # Shorten timeframe if many early warnings are firing
            if ew_score >= 0.70:
                timeframe = max(2, int(timeframe * 0.60))
            elif ew_score >= 0.50:
                timeframe = max(3, int(timeframe * 0.75))

            confidence = clamp01(0.30 + 0.40 * ew_score + 0.30 * prob)

            paths.append(TransitionPath(
                from_quad=current_quad,
                to_quad=to_q,
                probability=prob,
                timeframe_weeks=timeframe,
                early_warning_score=ew_score,
                confirmation_needed=template.get("confirmation_needed", []),
                invalidators=template.get("invalidators", []),
                asset_implications=template.get("asset_implications", {}),
                confidence=confidence,
            ))

        # Sort by probability descending
        paths.sort(key=lambda p: p.probability, reverse=True)

        # Most likely next quad
        most_likely_next = paths[0].to_quad if paths else getattr(regime_posterior, "structural_next_quad", "Q?")

        # Named early warning signals (cross-path composite)
        ew_signals = {}
        macro_enriched = {**macro, **market}
        for path_key, template in _TRANSITION_LIBRARY.items():
            if not path_key.startswith(f"{current_quad}→"):
                continue
            for signal_name, fn in template.get("early_warning_thresholds", {}).items():
                if signal_name not in ew_signals:
                    ew_signals[signal_name] = 1.0 if _safe_eval(fn, macro_enriched) else 0.0

        # Overall leading composite: average of top-2 path early warning scores
        if paths:
            top2_ew = [p.early_warning_score for p in paths[:2]]
            leading_composite = sum(top2_ew) / len(top2_ew)
        else:
            leading_composite = float(macro.get("leading_indicator_composite", 0.0))

        # Front-run window determination
        top_path = paths[0] if paths else None
        if top_path and top_path.early_warning_score >= 0.70 and top_path.probability >= 0.30:
            front_run_window = "now"
            front_run_rationale = (
                f"High conviction {top_path.from_quad}→{top_path.to_quad} transition signal. "
                f"{int(top_path.early_warning_score * 100)}% of early warning conditions active. "
                f"Estimated {top_path.timeframe_weeks}w window."
            )
        elif top_path and top_path.early_warning_score >= 0.50 and top_path.probability >= 0.22:
            front_run_window = "1-2w"
            front_run_rationale = (
                f"Moderate {top_path.from_quad}→{top_path.to_quad} transition probability. "
                f"Watch for confirmation: {top_path.confirmation_needed[0] if top_path.confirmation_needed else 'additional data'}"
            )
        elif top_path and top_path.early_warning_score >= 0.30:
            front_run_window = "3-6w"
            front_run_rationale = (
                f"Early warning signals beginning for {top_path.from_quad}→{top_path.to_quad}. "
                f"Not actionable yet — watch for {top_path.confirmation_needed[0] if top_path.confirmation_needed else 'confirmation'}."
            )
        else:
            front_run_window = "not yet"
            front_run_rationale = f"Current {current_quad} regime shows no early transition signals. Stay positioned for regime continuation."

        return RegimeTransitionOutput(
            current_quad=current_quad,
            current_monthly_quad=monthly_quad,
            most_likely_next=most_likely_next,
            transition_paths=paths,
            early_warning_signals=ew_signals,
            leading_composite=leading_composite,
            front_run_window=front_run_window,
            front_run_rationale=front_run_rationale,
        )


def _safe_eval(fn, macro: dict) -> bool:
    try:
        return bool(fn(macro))
    except Exception:
        return False
