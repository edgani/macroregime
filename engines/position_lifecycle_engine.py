"""position_lifecycle_engine.py

Converts regime + conviction + vol state → concrete position sizing guidance.
Answers the question every trader actually has: "OK I'm convinced, berapa dan gimana masuknya?"

Includes:
- Kelly-fraction based sizing (regime-adjusted)
- Entry zone logic (scale in vs. all-in)
- Stop-loss guidance per regime
- Exit trigger conditions
- Risk-reward estimation
- Hold horizon per regime

This is the bridge between "macro intelligence" and "actual trade execution".
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

from utils.math_utils import clamp01


@dataclass
class PositionGuidance:
    # Sizing
    base_size_pct: float               # recommended position size (% of portfolio)
    max_size_pct: float                # absolute maximum
    kelly_fraction: float              # raw Kelly output
    kelly_adjusted: float              # half-Kelly (more practical)
    sizing_rationale: str

    # Entry
    entry_strategy: str                # all_in | scale_3 | scale_5 | wait_pullback | avoid
    entry_triggers: List[str]          # specific conditions to enter
    entry_zone_note: str

    # Risk management
    stop_loss_pct: float               # recommended stop from entry
    stop_loss_rationale: str
    risk_reward_estimate: float        # estimated R:R ratio
    max_holding_weeks: int

    # Exit
    exit_triggers: List[str]          # conditions that should trigger full exit
    partial_exit_triggers: List[str]  # conditions for 50% trim

    # Context
    regime_sizing_modifier: float     # multiplier from regime (Q3 = 0.5x, Q1 = 1.2x)
    vol_sizing_modifier: float        # multiplier from VIX bucket
    conviction_modifier: float        # multiplier from conviction score


# Regime-specific base parameters
_REGIME_PARAMS: Dict[str, Dict] = {
    "Q1": {
        "base_size": 0.08,       # 8% per position base
        "max_size": 0.15,        # 15% max
        "regime_mult": 1.20,     # risk-on = larger size
        "stop_pct": 0.07,        # 7% stop (tighter in risk-on — more conviction)
        "hold_weeks": 12,
        "entry": "scale_3",      # scale in 3 tranches as regime confirms
        "rr_estimate": 2.5,
    },
    "Q2": {
        "base_size": 0.07,
        "max_size": 0.12,
        "regime_mult": 1.10,
        "stop_pct": 0.08,
        "hold_weeks": 10,
        "entry": "scale_3",
        "rr_estimate": 2.2,
    },
    "Q3": {
        "base_size": 0.04,       # smaller — stagflation = high uncertainty
        "max_size": 0.08,
        "regime_mult": 0.55,     # significantly reduced sizing in Q3
        "stop_pct": 0.06,        # tighter stops — moves are fast
        "hold_weeks": 6,
        "entry": "scale_5",      # scale in more slowly — more uncertainty
        "rr_estimate": 1.8,
    },
    "Q4": {
        "base_size": 0.05,
        "max_size": 0.10,
        "regime_mult": 0.70,
        "stop_pct": 0.09,        # wider stop — Q4 has big whipsaws
        "hold_weeks": 8,
        "entry": "wait_pullback",
        "rr_estimate": 2.0,
    },
}

_VIX_MULT: Dict[str, float] = {
    "goldilocks": 1.10,
    "normal": 1.00,
    "elevated": 0.70,
    "stress": 0.40,
    "crisis": 0.15,
}

_ENTRY_DESCRIPTIONS: Dict[str, str] = {
    "all_in":       "Enter full position at once — high conviction + confirmed regime",
    "scale_3":      "Enter in 3 tranches: 40% → 35% → 25% over 2-4 weeks",
    "scale_5":      "Enter in 5 tranches of 20% each — high uncertainty, build slowly",
    "wait_pullback": "Wait for 3-5% pullback from recent high before entering",
    "avoid":        "Do not enter — risk/reward unfavorable in current regime",
}


class PositionLifecycleEngine:
    """
    Given current regime, conviction score, VIX bucket, and trade direction,
    returns complete position lifecycle guidance.
    """

    def run(
        self,
        quad: str,
        conviction: float,           # 0-1
        vix_bucket: str,
        trade_direction: str,        # long | short
        front_run: bool = False,     # True = pre-confirmation entry → smaller initial
        news_state: str = "quiet",
        narrative_stage: str = "",   # early | building | mature | exhausted
    ) -> PositionGuidance:
        quad = quad if quad in _REGIME_PARAMS else "Q3"  # default to conservative
        params = _REGIME_PARAMS[quad]

        regime_mult = params["regime_mult"]
        vol_mult = _VIX_MULT.get(vix_bucket, 0.70)
        conviction_mult = clamp01(0.40 + 0.80 * conviction)  # 0.40 min, scales with conviction

        # Front-run penalty: reduce initial size since not confirmed yet
        front_run_mult = 0.60 if front_run else 1.00

        # Narrative stage modifier
        stage_mult = {
            "early": 0.65,     # early stage = smaller position, wait for building
            "building": 0.85,
            "mature": 1.00,
            "exhausted": 0.30,  # don't enter exhausted narratives
        }.get(narrative_stage, 0.90)

        # News state modifier
        news_mult = {
            "war_oil": 0.80 if trade_direction == "long" else 1.20,  # oil shock = tighter longs
            "credit_stress": 0.60,
            "deescalation_confirmed": 1.10 if trade_direction == "long" else 0.70,
            "quiet": 1.00,
        }.get(news_state, 1.00)

        # Raw Kelly calculation
        # Kelly = (p * b - q) / b where p=win_prob, q=loss_prob, b=reward/loss
        # Use conviction as proxy for win probability (with adjustment)
        p_win = clamp01(0.45 + 0.30 * conviction)  # 45% at zero conviction, 75% at full
        b_reward = params["rr_estimate"]
        kelly_raw = (p_win * b_reward - (1 - p_win)) / b_reward
        kelly_raw = max(0.0, kelly_raw)
        kelly_adj = kelly_raw * 0.50  # half-Kelly is standard practice

        # Final position size
        base = params["base_size"] * regime_mult * vol_mult * conviction_mult * front_run_mult * stage_mult * news_mult
        base_pct = clamp01(base) * 100
        max_pct = clamp01(params["max_size"] * regime_mult * vol_mult) * 100

        # Adjust entry strategy based on conditions
        if conviction >= 0.70 and not front_run and narrative_stage == "mature":
            entry = "all_in"
        elif front_run or narrative_stage == "early":
            entry = "scale_5"
        elif vix_bucket in ("stress", "crisis"):
            entry = "wait_pullback"
        else:
            entry = params["entry"]

        # Stop loss — adjust for direction and regime
        stop = params["stop_pct"]
        if vix_bucket in ("stress", "crisis"):
            stop = stop * 0.75  # tighter stop in high vol (get out fast)
        if trade_direction == "short":
            stop = stop * 1.20  # shorts are harder to hold, wider stop
        if front_run:
            stop = stop * 0.80  # front-run: tighter stop, smaller loss if wrong

        # R:R estimate
        rr = params["rr_estimate"] * (0.80 + 0.40 * conviction)

        # Entry triggers
        entry_triggers = _build_entry_triggers(quad, trade_direction, front_run, narrative_stage)
        exit_triggers = _build_exit_triggers(quad, trade_direction)
        partial_exit_triggers = _build_partial_exit_triggers(quad, trade_direction)

        # Sizing rationale
        rationale_parts = []
        if front_run:
            rationale_parts.append("pre-confirmation front-run → reduced initial size")
        if vix_bucket in ("elevated", "stress", "crisis"):
            rationale_parts.append(f"VIX {vix_bucket} → {int(vol_mult*100)}% size reduction")
        if regime_mult < 0.80:
            rationale_parts.append(f"{quad} regime → conservative sizing ({int(regime_mult*100)}%)")
        if narrative_stage == "early":
            rationale_parts.append("early narrative → staged entry")
        rationale = "; ".join(rationale_parts) if rationale_parts else f"{quad} base sizing, standard conditions"

        return PositionGuidance(
            base_size_pct=round(base_pct, 1),
            max_size_pct=round(max_pct, 1),
            kelly_fraction=round(kelly_raw, 3),
            kelly_adjusted=round(kelly_adj, 3),
            sizing_rationale=rationale,
            entry_strategy=entry,
            entry_triggers=entry_triggers,
            entry_zone_note=_ENTRY_DESCRIPTIONS.get(entry, "Standard entry"),
            stop_loss_pct=round(stop * 100, 1),
            stop_loss_rationale=f"Regime {quad} typical stop; {'tightened for vol' if vix_bucket in ('stress','crisis') else 'standard'}",
            risk_reward_estimate=round(rr, 1),
            max_holding_weeks=params["hold_weeks"],
            exit_triggers=exit_triggers,
            partial_exit_triggers=partial_exit_triggers,
            regime_sizing_modifier=round(regime_mult, 2),
            vol_sizing_modifier=round(vol_mult, 2),
            conviction_modifier=round(conviction_mult, 2),
        )


def _build_entry_triggers(quad: str, direction: str, front_run: bool, stage: str) -> List[str]:
    base = {
        "Q1": ["ISM prints above 50", "Claims trend turns down", "IWM/RSP relative strength improving"],
        "Q2": ["Oil bid above 3% 1m move", "Breakevens rising", "XLE/XLB sector leadership confirmed"],
        "Q3": ["ISM sub-50 confirmed", "Oil still above 8% 3m", "Breadth remains narrow"],
        "Q4": ["ISM deteriorating 3+ months", "Claims rising trend", "Inflation momentum negative"],
    }.get(quad, ["Regime confirmed by breadth and credit"])

    if front_run:
        base.insert(0, "⚡ FRONT-RUN: Enter partial on early warning signals firing (50-70%)")
    if stage == "early":
        base.insert(0, "Initial tranche only — wait for building stage before full size")
    if direction == "short":
        base = [t.replace("improving", "deteriorating") for t in base]

    return base[:4]


def _build_exit_triggers(quad: str, direction: str) -> List[str]:
    return {
        "Q1": ["ISM drops below 49 for 2 months", "Claims trend reverses up", "growth_momentum turns negative", "Inflation re-accelerates above 4%"],
        "Q2": ["ISM drops below 50 — growth side of Q2 failing", "Oil reverses >12% from peak", "Breadth collapses (Q2→Q3 risk)"],
        "Q3": ["Oil drops >10% fast — supply shock fading", "ISM bounces above 52 — growth stabilizing", "Fed signals pivot"],
        "Q4": ["Fed pivot confirmed + leading indicators turning", "ISM prints >50 on sustained basis", "Inflation clearly decelerated below 3%"],
    }.get(quad, ["Regime changes materially", "Cross-asset confirmation reverses"])


def _build_partial_exit_triggers(quad: str, direction: str) -> List[str]:
    return {
        "Q1": ["Position +25% from entry — trim 30-40%", "VIX spikes above 22 — uncertainty increases", "Monthly quad diverges to Q2"],
        "Q2": ["Oil >+30% from entry — trim energy names", "ISM 3m trend turns negative", "Breakevens start rolling over"],
        "Q3": ["Any confirmed de-escalation headline + market confirmation", "Gold drops >8% — narrative fading", "Credit spreads tighten"],
        "Q4": ["TLT +15% from entry — trim duration", "Growth data surprises to upside", "Sentiment becomes very bearish (contrarian buy signal)"],
    }.get(quad, ["Position +20% → trim 25-35%", "Regime probability drops below 50%"])
