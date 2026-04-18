from __future__ import annotations
from typing import Dict
from utils.math_utils import clamp01


class NewsEventEngine:
    """Translates raw news signals (keyword + Claude analysis) into structured
    market-state hazard scores and forward-looking regime shift signals.

    Consumes both the keyword counts AND Claude semantic analysis when available.
    Claude analysis takes priority on dominant state when confidence > 0.4.
    """

    def run(
        self,
        news: Dict[str, object],
        market: Dict[str, float],
        macro: Dict[str, float],
    ) -> Dict[str, object]:
        counts = (news or {}).get("counts", {}) or {}
        raw_state = str((news or {}).get("state", "quiet"))
        claude_analysis = (news or {}).get("claude_analysis") or {}

        # Raw keyword counts
        escalation = float(counts.get("escalation", 0.0))
        relief     = float(counts.get("relief", 0.0))
        oil_news   = float(counts.get("oil", 0.0))
        rates_news = float(counts.get("rates", 0.0))
        usd_news   = float(counts.get("usd", 0.0))
        china_news = float(counts.get("china", 0.0))
        credit_news = float(counts.get("credit", 0.0))

        # Market confirmations
        oil_move       = float(macro.get("oil_3m", 0.0) or 0.0)
        usd_move       = float(market.get("dxy_1m", 0.0) or 0.0)
        breadth_rel    = float(market.get("rsp_rel_1m", 0.0) or 0.0)
        smallcap_rel   = float(market.get("iwm_rel_1m", 0.0) or 0.0)
        vix_move       = float(market.get("vix_1m", 0.0) or 0.0)
        long_end       = max(0.0, -float(market.get("tlt_1m", 0.0) or 0.0))

        oil_up           = max(0.0, oil_move)
        oil_down         = max(0.0, -oil_move)
        usd_up           = max(0.0, usd_move)
        usd_down         = max(0.0, -usd_move)
        breadth_stress   = max(0.0, -breadth_rel)
        smallcap_stress  = max(0.0, -smallcap_rel)
        breadth_relief   = max(0.0, breadth_rel)
        smallcap_relief  = max(0.0, smallcap_rel)
        vol_stress       = max(0.0, vix_move)

        # ------------------------------------------------------------------
        # Claude analysis boosts (when available and confident)
        # ------------------------------------------------------------------
        claude_confidence = 0.0
        claude_oil_shock   = 0.0
        claude_war_esc     = 0.0
        claude_relief      = 0.0
        claude_policy_piv  = 0.0
        claude_credit      = 0.0
        claude_toward_q    = ""
        claude_q_prob      = 0.0
        claude_action_win  = 7
        claude_what_watch  = ""
        claude_summary     = ""

        if isinstance(claude_analysis, dict) and claude_analysis:
            frs = claude_analysis.get("front_run_signal") or {}
            claude_confidence   = float(frs.get("confidence", 0.0))
            claude_action_win   = int(frs.get("action_window_days", 7))
            claude_what_watch   = str(frs.get("what_to_watch", ""))
            claude_summary      = str(claude_analysis.get("summary", ""))

            ev = claude_analysis.get("event_specific") or {}
            if isinstance(ev, dict):
                claude_oil_shock  = 1.0 if ev.get("oil_shock_active") else 0.0
                claude_war_esc    = 1.0 if ev.get("war_escalation") else 0.0
                claude_relief     = 1.0 if ev.get("ceasefire_or_relief") else 0.0
                claude_policy_piv = 1.0 if ev.get("policy_pivot") else 0.0
                claude_credit     = 1.0 if ev.get("credit_stress") else 0.0

            qsr = claude_analysis.get("quad_shift_risk") or {}
            if isinstance(qsr, dict):
                claude_toward_q = str(qsr.get("toward", "none"))
                claude_q_prob   = float(qsr.get("probability", 0.0))

        # ------------------------------------------------------------------
        # Hazard scores (keyword baseline + Claude boost)
        # ------------------------------------------------------------------
        war_oil_hazard = clamp01(
            0.12 * escalation
            + 0.08 * oil_news
            + 0.22 * clamp01(0.5 + oil_up / 0.12)
            + 0.10 * clamp01(0.5 + usd_up / 0.04)
            + 0.12 * clamp01(0.5 + breadth_stress / 0.03)
            + 0.08 * clamp01(0.5 + vol_stress / 0.12)
            + 0.18 * claude_oil_shock * claude_confidence
            + 0.10 * claude_war_esc * claude_confidence
        )
        policy_pressure_hazard = clamp01(
            0.08 * escalation
            + 0.12 * rates_news
            + 0.22 * clamp01(0.5 + long_end / 0.05)
            + 0.14 * clamp01(0.5 + smallcap_stress / 0.04)
            + 0.10 * clamp01(0.5 + usd_up / 0.04)
            + 0.06 * usd_news
            + 0.18 * claude_policy_piv * claude_confidence
        )
        credit_stress_hazard = clamp01(
            0.15 * credit_news
            + 0.20 * clamp01(0.5 + breadth_stress / 0.03)
            + 0.20 * clamp01(0.5 + smallcap_stress / 0.04)
            + 0.15 * clamp01(0.5 + vol_stress / 0.12)
            + 0.10 * long_end
            + 0.20 * claude_credit * claude_confidence
        )
        relief_hazard = clamp01(
            0.20 * relief
            + 0.16 * clamp01(0.5 + oil_down / 0.12)
            + 0.10 * clamp01(0.5 + usd_down / 0.04)
            + 0.10 * clamp01(0.5 + breadth_relief / 0.03)
            + 0.08 * clamp01(0.5 + smallcap_relief / 0.04)
            + 0.20 * claude_relief * claude_confidence
            + 0.08 * china_news
        )

        deescalation_watch = clamp01(
            0.55 * relief_hazard
            + 0.15 * relief
            + 0.15 * clamp01(0.5 + oil_down / 0.10)
            + 0.15 * clamp01(0.5 + usd_down / 0.04)
        )
        deescalation_confirmed = clamp01(
            0.35 * deescalation_watch
            + 0.25 * (1.0 if oil_move <= -0.04 else 0.0)
            + 0.15 * (1.0 if breadth_rel >= 0.01 else 0.0)
            + 0.15 * (1.0 if smallcap_rel >= 0.01 else 0.0)
            + 0.10 * (1.0 if usd_move <= 0.00 else 0.0)
        )
        oil_shock_live = clamp01(
            0.40 * war_oil_hazard
            + 0.20 * (1.0 if oil_move >= 0.08 else 0.0)
            + 0.15 * (1.0 if usd_move >= 0.01 else 0.0)
            + 0.10 * (1.0 if breadth_stress >= 0.02 else 0.0)
            + 0.10 * (1.0 if vix_move >= 0.10 else 0.0)
            + 0.05 * claude_oil_shock * claude_confidence
        )
        oil_shock_fading = clamp01(
            0.40 * war_oil_hazard
            + 0.30 * (1.0 if oil_move <= 0.02 else 0.0)
            + 0.15 * (1.0 if usd_move <= 0.01 else 0.0)
            + 0.15 * (1.0 if breadth_rel >= 0.00 else 0.0)
        )

        # ------------------------------------------------------------------
        # Dominant state classification (Claude takes priority if confident)
        # ------------------------------------------------------------------
        dominant = "quiet"
        if raw_state in {"war_oil", "deescalation_confirmed", "deescalation_watch", "oil_shock_fading", "policy_pressure", "credit_stress"} and claude_confidence >= 0.50:
            # Claude's analysis is confident — use its classified state directly
            dominant = raw_state
        elif oil_shock_live >= max(policy_pressure_hazard, credit_stress_hazard, deescalation_confirmed, deescalation_watch, 0.44):
            dominant = "war_oil"
        elif credit_stress_hazard >= max(oil_shock_live, policy_pressure_hazard, deescalation_confirmed, 0.40):
            dominant = "credit_stress"
        elif policy_pressure_hazard >= max(oil_shock_live, credit_stress_hazard, deescalation_confirmed, deescalation_watch, 0.38):
            dominant = "policy_pressure"
        elif deescalation_confirmed >= max(oil_shock_live, policy_pressure_hazard, credit_stress_hazard, 0.42):
            dominant = "deescalation_confirmed"
        elif deescalation_watch >= max(oil_shock_live, policy_pressure_hazard, credit_stress_hazard, 0.30):
            dominant = "deescalation_watch"
        elif oil_shock_fading >= max(policy_pressure_hazard, credit_stress_hazard, 0.34):
            dominant = "oil_shock_fading"
        elif raw_state in {"active", "escalating", "de_escalating"}:
            dominant = raw_state

        display = {
            "war_oil":                 "War / oil shock",
            "policy_pressure":         "Policy pressure",
            "credit_stress":           "Credit stress",
            "deescalation_watch":      "De-escalation watch",
            "deescalation_confirmed":  "De-escalation confirmed",
            "oil_shock_fading":        "Oil shock fading",
            "relief":                  "Relief",
            "active":                  "Active",
            "escalating":              "Escalating",
            "de_escalating":           "De-escalating",
            "quiet":                   "Quiet",
        }.get(dominant, "Quiet")

        # ------------------------------------------------------------------
        # Forward-looking regime shift signal
        # Combines Claude's quad shift probability with market confirmation
        # ------------------------------------------------------------------
        regime_shift_probability = 0.0
        regime_shift_toward = "none"
        regime_shift_timeframe_weeks = 4
        if claude_toward_q not in ("none", "", None):
            regime_shift_probability = clamp01(
                claude_q_prob
                + 0.10 * min(1.0, (war_oil_hazard + policy_pressure_hazard + credit_stress_hazard) / 1.5)
            )
            regime_shift_toward = claude_toward_q
            qsr = claude_analysis.get("quad_shift_risk") or {}
            regime_shift_timeframe_weeks = int(qsr.get("timeframe_weeks", 4)) if isinstance(qsr, dict) else 4

        # ------------------------------------------------------------------
        # Market confirmation flags
        # ------------------------------------------------------------------
        confirmation = {
            "oil_confirms":           oil_move > 0.08,
            "oil_relief_confirms":    oil_move < -0.04,
            "usd_confirms":           usd_move > 0.01,
            "usd_relief_confirms":    usd_move <= 0.00,
            "breadth_confirms_stress": breadth_stress > 0.02 or smallcap_stress > 0.03,
            "breadth_confirms_relief": breadth_rel >= 0.01 or smallcap_relief >= 0.01,
            "rates_confirms_pressure": long_end > 0.03,
            "credit_confirms_stress":  credit_stress_hazard > 0.45,
        }

        # ------------------------------------------------------------------
        # Summary text
        # ------------------------------------------------------------------
        if claude_summary and claude_confidence >= 0.40:
            summary = claude_summary
        elif display == "Quiet":
            summary = "No major news impulse detected."
        elif dominant == "deescalation_confirmed":
            summary = "De-escalation path has both headline and market confirmation."
        elif dominant == "deescalation_watch":
            summary = "Relief headlines building, but full market confirmation not yet complete."
        elif dominant == "oil_shock_fading":
            summary = "Prior oil/geopolitical shock is fading but not fully cleared."
        elif dominant == "credit_stress":
            summary = "Credit stress signals active — watch HY spreads and small cap breadth."
        else:
            summary = f"{display} bias with market confirmation check active."

        # Front-run signal (populated by Claude analysis)
        front_run = {}
        if claude_confidence >= 0.40:
            front_run = {
                "action_window_days": claude_action_win,
                "confidence": claude_confidence,
                "what_to_watch": claude_what_watch,
                "toward_quad": regime_shift_toward,
                "shift_probability": regime_shift_probability,
                "shift_timeframe_weeks": regime_shift_timeframe_weeks,
            }

        return {
            "state": dominant,
            "display_state": display,
            "summary": summary,
            "war_oil_hazard":          war_oil_hazard,
            "policy_pressure_hazard":  policy_pressure_hazard,
            "credit_stress_hazard":    credit_stress_hazard,
            "relief_hazard":           relief_hazard,
            "deescalation_watch":      deescalation_watch,
            "deescalation_confirmed":  deescalation_confirmed,
            "oil_shock_live":          oil_shock_live,
            "oil_shock_fading":        oil_shock_fading,
            "confirmation":            confirmation,
            "front_run":               front_run,
            "regime_shift_probability":      regime_shift_probability,
            "regime_shift_toward":           regime_shift_toward,
            "regime_shift_timeframe_weeks":  regime_shift_timeframe_weeks,
            "headlines": (news or {}).get("top_headlines", []),
            "claude_analysis": claude_analysis if claude_analysis else None,
        }
