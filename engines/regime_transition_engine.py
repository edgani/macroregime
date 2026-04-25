"""engines/regime_transition_engine.py
Ported from v9_fixed. Timing + front-run window + early warning checklist.
Tells you WHEN the next quad is coming and what signals to watch.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np

def _safe_eval(fn, macro): 
    try: return bool(fn(macro))
    except: return False

def clamp01(x): return float(max(0.0, min(1.0, x)))

@dataclass
class TransitionPath:
    from_quad: str; to_quad: str; probability: float
    timeframe_weeks: int; early_warning_score: float
    confirmation_needed: List[str]; invalidators: List[str]
    asset_implications: Dict[str,str]; confidence: float

@dataclass
class RegimeTransitionOutput:
    current_quad: str; current_monthly_quad: str; most_likely_next: str
    transition_paths: List[TransitionPath]
    early_warning_signals: Dict[str, float]
    leading_composite: float
    front_run_window: str   # "now" | "1-2w" | "3-6w" | "not yet"
    front_run_rationale: str

_TRANSITION_LIBRARY: Dict[str, Dict] = {
    "Q1→Q2": {
        "trigger_logic": "Growth cycle matures, commodity demand builds, inflation re-accelerates while growth still robust.",
        "early_warning_thresholds": {
            "inflation_momentum_rising":   lambda m: m.get("inflation_momentum", 0.0) > 0.15,
            "breakeven_widening":          lambda m: m.get("breakeven_1m_delta", 0.0) > 0.05,
            "oil_bid":                     lambda m: m.get("oil_3m", 0.0) > 0.08,
            "gold_bid":                    lambda m: m.get("gold_3m", 0.0) > 0.06,
            "ism_above_50":                lambda m: m.get("ism_norm", 0.0) > 0.0,
            "growth_level_positive":       lambda m: m.get("growth_level", 0.0) > 0.10,
        },
        "confirmation_needed": ["CPI/PCE beats for 2+ consecutive months", "Breakevens rise above 2.5% and hold", "ISM stays above 52 while oil bid"],
        "invalidators": ["Oil reverses >10%", "ISM drops below 50", "Breakevens fall back below 2.2%"],
        "base_probability": 0.15, "typical_timeframe_weeks": 8,
        "asset_implications": {"us_equities":"selective — energy/materials/cyclicals","ihsg":"coal exporters up, importers flat","commodities":"bullish energy and base metals","fx":"commodity FX (AUD/CAD/NOK) outperform","bonds":"bearish duration","crypto":"selective — BTC may hold"},
    },
    "Q1→Q4": {
        "trigger_logic": "Late-cycle growth fatigue. ISM peaks and rolls over. Inflation stays contained — deflationary risk.",
        "early_warning_thresholds": {
            "growth_momentum_falling":     lambda m: m.get("growth_momentum", 0.0) < -0.10,
            "ism_deteriorating":           lambda m: m.get("ism_delta", 0.0) < -0.02,
            "claims_rising":               lambda m: m.get("claims_delta", 0.0) > 0.0,
            "housing_rolling_over":        lambda m: m.get("housing_yoy", 0.0) < 0.0,
            "inflation_contained":         lambda m: m.get("inflation_momentum", 0.0) < 0.10,
        },
        "confirmation_needed": ["ISM sub-50 for 2 consecutive months", "Payrolls decelerate 3+ months", "Inflation stays below 3%"],
        "invalidators": ["ISM rebounds above 52", "Fiscal stimulus revives demand", "Oil spike → routes to Q2/Q3"],
        "base_probability": 0.12, "typical_timeframe_weeks": 10,
        "asset_implications": {"us_equities":"defensive rotation — quality/dividend/low-vol","ihsg":"bearish","commodities":"bearish","fx":"USD safe haven, EM under pressure","bonds":"bullish duration","crypto":"bearish"},
    },
    "Q2→Q3": {
        "trigger_logic": "Growth peaks and rolls over while inflation stays hot. Policy overtightening or supply shock.",
        "early_warning_thresholds": {
            "growth_momentum_falling":     lambda m: m.get("growth_momentum", 0.0) < -0.05,
            "ism_rolling_over":            lambda m: m.get("ism_delta", 0.0) < -0.015,
            "inflation_sticky":            lambda m: m.get("inflation_level", 0.0) > 0.20,
            "oil_shock_active":            lambda m: m.get("oil_3m", 0.0) > 0.12,
            "smallcap_lagging":            lambda m: m.get("growth_momentum", 0.0) < -0.03,
        },
        "confirmation_needed": ["ISM drops below 50 while CPI stays above 4%", "Claims rise 2+ months", "Fed stays hawkish despite slowing"],
        "invalidators": ["Oil drops sharply", "Fed signals pivot", "Growth data surprises upside"],
        "base_probability": 0.10, "typical_timeframe_weeks": 8,
        "asset_implications": {"us_equities":"bearish broad — energy/commodities only safe harbor","ihsg":"split — coal up, rupiah fragile","commodities":"bullish energy/gold, bearish base metals","fx":"USD strong, EM importers fragile","bonds":"bearish duration worst of all worlds","crypto":"bearish"},
    },
    "Q3→Q4": {
        "trigger_logic": "Supply shock fades or policy succeeds in crushing inflation. Growth still weak but inflation decelerating.",
        "early_warning_thresholds": {
            "inflation_momentum_falling":  lambda m: m.get("inflation_momentum", 0.0) < 0.0,
            "oil_retreating":              lambda m: m.get("oil_3m", 0.0) < 0.0,
            "breakevens_falling":          lambda m: m.get("breakeven_1m_delta", 0.0) < -0.05,
            "growth_still_weak":           lambda m: m.get("growth_momentum", 0.0) < -0.10,
            "q3_modifier_low":             lambda m: m.get("q3_modifier", 0.5) < 0.15,
        },
        "confirmation_needed": ["CPI decelerates 3+ months in a row", "Oil breaks below 3M moving average", "Breakevens fall below 2.0%"],
        "invalidators": ["Oil reverses bid", "New supply shock (Iran/Hormuz)", "Fiscal spending re-ignites demand"],
        "base_probability": 0.20, "typical_timeframe_weeks": 10,
        "asset_implications": {"us_equities":"XLV/XLP/XLU defensive", "ihsg":"bearish — commodity demand collapse","commodities":"bearish except gold","fx":"USD strengthens (deflation fear)","bonds":"very bullish — max long TLT","crypto":"bearish"},
    },
    "Q3→Q2": {
        "trigger_logic": "Inflation stays hot AND growth appears to stabilize (fiscal boost or commodity-led). Often a head-fake.",
        "early_warning_thresholds": {
            "growth_stabilizing":          lambda m: m.get("growth_momentum", 0.0) > -0.05,
            "inflation_still_hot":         lambda m: m.get("inflation_momentum", 0.0) > 0.10,
            "oil_still_bid":               lambda m: m.get("oil_3m", 0.0) > 0.05,
            "policy_still_tight":          lambda m: m.get("policy_score", 0.0) < 0.0,
        },
        "confirmation_needed": ["ISM holds above 51 for 3+ months", "Payrolls stay robust >200k/month while inflation stays above 3%"],
        "invalidators": ["ISM falls back below 50", "Credit spreads widen", "Fiscal impulse fades"],
        "base_probability": 0.08, "typical_timeframe_weeks": 6,
        "asset_implications": {"us_equities":"short-lived risk rally; energy/materials lead","ihsg":"cautious bounce — exporters up","commodities":"still bullish if sustained","fx":"commodity currencies bounce","bonds":"still bearish duration","crypto":"selective risk-on possible"},
    },
    "Q3→Q1": {
        "trigger_logic": "The cleanest recovery. Both growth re-accelerates AND inflation cools simultaneously. Rare but powerful.",
        "early_warning_thresholds": {
            "growth_reaccelerating":       lambda m: m.get("growth_momentum", 0.0) > 0.05,
            "inflation_cooling":           lambda m: m.get("inflation_momentum", 0.0) < -0.05,
            "oil_cooling":                 lambda m: m.get("oil_3m", 0.0) < 0.03,
            "breakevens_normalizing":      lambda m: m.get("breakeven_1m_delta", 0.0) < 0.0,
            "policy_becoming_supportive":  lambda m: m.get("policy_score", 0.0) > 0.05,
        },
        "confirmation_needed": ["CPI decelerates 50bps", "ISM > 52 and rising", "Fed signals cuts", "Oil 3M return < -10%"],
        "invalidators": ["Inflation re-accelerates", "Growth disappointment", "Geopolitical supply shock"],
        "base_probability": 0.12, "typical_timeframe_weeks": 12,
        "asset_implications": {"us_equities":"selective recovery — quality growth first","ihsg":"EIDO/INDA recovery begins","commodities":"gold holds, cyclicals recover","fx":"USD weakens, EM FX recovers","bonds":"neutral — rates settle","crypto":"bullish"},
    },
    "Q4→Q1": {
        "trigger_logic": "THE canonical recovery. Deflation fears peak, Fed eases, liquidity returns. Maximum conviction long.",
        "early_warning_thresholds": {
            "growth_reaccelerating":       lambda m: m.get("growth_momentum", 0.0) > 0.05,
            "inflation_normalized":        lambda m: abs(m.get("inflation_momentum", 0.0)) < 0.15,
            "policy_easing":               lambda m: m.get("policy_score", 0.0) > 0.10,
            "credit_normalizing":          lambda m: m.get("q3_credit_stress", 0.0) < 0.10,
            "leading_composite_rising":    lambda m: m.get("leading_indicator_composite", 0.0) > 0.0,
        },
        "confirmation_needed": ["Fed cuts ≥25bps", "ISM breaks back above 50", "Payrolls re-accelerate", "Credit spreads tighten 50bps+"],
        "invalidators": ["Credit event", "Inflation re-ignites before growth firms", "Dollar crisis"],
        "base_probability": 0.25, "typical_timeframe_weeks": 8,
        "asset_implications": {"us_equities":"MAXIMUM LONG — broadest participation","ihsg":"MAX EM RECOVERY — EIDO, banks, property","commodities":"base metals bid, gold steady","fx":"USD weakens, EM FX surges","bonds":"neutral (yields stabilize as growth returns)","crypto":"bullish — risk appetite and liquidity both improving"},
    },
    "Q4→Q3": {
        "trigger_logic": "Supply shock or fiscal stimulus re-ignites inflation before growth firms. Rare but brutal.",
        "early_warning_thresholds": {
            "oil_spiking":                 lambda m: m.get("oil_3m", 0.0) > 0.15,
            "inflation_re_accelerating":   lambda m: m.get("inflation_momentum", 0.0) > 0.15,
            "growth_still_weak":           lambda m: m.get("growth_momentum", 0.0) < -0.05,
        },
        "confirmation_needed": ["Oil spike persists >2 months", "CPI re-accelerates while GDP still negative"],
        "invalidators": ["Oil reverses", "Growth picks up alongside inflation → routes to Q2"],
        "base_probability": 0.05, "typical_timeframe_weeks": 6,
        "asset_implications": {"us_equities":"gold/defense/energy only","ihsg":"exporters only","commodities":"energy/gold bullish","fx":"USD up + petrocurrencies","bonds":"bearish","crypto":"bearish"},
    },
}


class RegimeTransitionEngine:
    def run(self, macro: Dict[str, float], market: Dict[str, float], gip_result, news_state: Dict = None, shock_strength: float = 0.0) -> RegimeTransitionOutput:
        news_state = news_state or {}
        current_quad = getattr(gip_result, "structural_quad", "Q3")
        monthly_quad = getattr(gip_result, "monthly_quad", current_quad)
        flip_hazard = float(getattr(gip_result, "flip_hazard", 0.30))
        macro_enriched = {**macro, **market, **getattr(gip_result, "features", {})}

        relevant_paths = [k for k in _TRANSITION_LIBRARY if k.startswith(f"{current_quad}→")]
        if monthly_quad != current_quad:
            cross = f"{current_quad}→{monthly_quad}"
            if cross not in relevant_paths and cross in _TRANSITION_LIBRARY:
                relevant_paths.append(cross)

        paths: List[TransitionPath] = []
        for path_key in relevant_paths:
            template = _TRANSITION_LIBRARY[path_key]
            _, to_q = path_key.split("→")
            thresholds = template.get("early_warning_thresholds", {})
            firing = sum(1.0 for fn in thresholds.values() if _safe_eval(fn, macro_enriched))
            ew_score = clamp01(firing / len(thresholds)) if thresholds else 0.0

            base = template.get("base_probability", 0.10)
            monthly_confirm = 0.08 if monthly_quad == to_q else 0.0
            prob = clamp01(base + 0.30*ew_score + monthly_confirm + 0.05*flip_hazard + (0.08*shock_strength if to_q in ("Q3","Q4") else 0.0))

            timeframe = template.get("typical_timeframe_weeks", 8)
            if ew_score >= 0.70: timeframe = max(2, int(timeframe*0.60))
            elif ew_score >= 0.50: timeframe = max(3, int(timeframe*0.75))

            paths.append(TransitionPath(
                from_quad=current_quad, to_quad=to_q, probability=prob,
                timeframe_weeks=timeframe, early_warning_score=ew_score,
                confirmation_needed=template.get("confirmation_needed",[]),
                invalidators=template.get("invalidators",[]),
                asset_implications=template.get("asset_implications",{}),
                confidence=clamp01(0.30 + 0.40*ew_score + 0.30*prob),
            ))

        paths.sort(key=lambda p: p.probability, reverse=True)
        most_likely_next = paths[0].to_quad if paths else current_quad

        # Early warning signals
        ew_signals = {}
        for path_key, template in _TRANSITION_LIBRARY.items():
            if not path_key.startswith(f"{current_quad}→"): continue
            for sig, fn in template.get("early_warning_thresholds",{}).items():
                if sig not in ew_signals:
                    ew_signals[sig] = 1.0 if _safe_eval(fn, macro_enriched) else 0.0

        top2_ew = [p.early_warning_score for p in paths[:2]]
        leading_composite = float(np.mean(top2_ew)) if top2_ew else 0.0

        top = paths[0] if paths else None
        if top and top.early_warning_score >= 0.70 and top.probability >= 0.30:
            fw = "now"
            fr = f"HIGH CONVICTION {top.from_quad}→{top.to_quad}. {int(top.early_warning_score*100)}% early warning conditions active. Estimated {top.timeframe_weeks}w window. FRONT-RUN NOW."
        elif top and top.early_warning_score >= 0.50 and top.probability >= 0.22:
            fw = "1-2w"
            conf_1 = top.confirmation_needed[0] if top.confirmation_needed else "additional data"
            fr = f"MODERATE {top.from_quad}→{top.to_quad} probability. Watch for: {conf_1}"
        elif top and top.early_warning_score >= 0.30:
            fw = "3-6w"
            conf_1 = top.confirmation_needed[0] if top.confirmation_needed else "confirmation"
            fr = f"EARLY WARNING building for {top.from_quad}→{top.to_quad}. Not actionable yet — watch for {conf_1}."
        else:
            fw = "not yet"
            fr = f"Current {current_quad} shows no clear transition signals. Stay positioned for regime continuation."

        return RegimeTransitionOutput(
            current_quad=current_quad, current_monthly_quad=monthly_quad,
            most_likely_next=most_likely_next, transition_paths=paths,
            early_warning_signals=ew_signals, leading_composite=leading_composite,
            front_run_window=fw, front_run_rationale=fr,
        )
