"""narrative_discovery_engine.py

The core of the "more dewa than Hedgeye" system.

Takes raw narrative signals (keyword scores from narrative_news_loader) and:
1. Scores each narrative's strength and regime alignment
2. Uses Claude to DEEPLY analyze the top narratives for:
   - Catalyst classification (what type of event triggered this)
   - Stage assessment (early / building / mature / exhausted)
   - Beneficiary ranking (primary vs secondary vs tertiary winners)
   - Risk classification (fundamental thesis vs pure momentum)
   - Specific actionable insight ("Google quantum admission validates photonic QC
     — buy IONQ/QUBT before institutional discovery phase")
3. Returns ranked NarrativeCase objects with full conviction scoring

The XNDU pattern this detects:
  - Dominant company admits limit → challenger's thesis validated
  - Government/institutional partner list = legitimacy signal
  - Social momentum building (pre-institutional) = early stage
  - Regime alignment = Q1/Q2 amplifies tech narratives
  - Action: Buy IONQ/QUBT before institutions discover this
"""
from __future__ import annotations
import json
import os
import requests
from dataclasses import dataclass, field
from typing import Dict, List

from utils.math_utils import clamp01
from utils.streamlit_compat import st
from config.narrative_universe import _NARRATIVE_LIBRARY, NARRATIVE_BY_NAME
from config.settings import NEWS_CACHE_TTL_SECONDS


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

@dataclass
class NarrativeCase:
    name: str
    category: str
    stage: str                          # early | building | mature | exhausted | invalid
    conviction: float                   # 0-1: overall actionability
    regime_multiplier: float            # how much current regime amplifies this
    regime_adjusted_conviction: float   # conviction × regime_multiplier
    pump_risk: float                    # 0=pure thesis, 1=pure pump
    net_news_score: float               # activation - invalidation score
    primary_beneficiaries: List[str]    # highest priority tickers to buy
    secondary_beneficiaries: List[str]  # secondary tickers
    what_fades: List[str]              # tickers that lose from this narrative
    claude_insight: str                 # Claude's specific analytical take
    confirmation_signals: List[str]     # what market data to watch to confirm
    catalyst_type: str                  # what kind of event activated this
    action_summary: str                 # "Buy X before Y happens because Z"
    invalidators: List[str]            # what would kill this trade
    headlines: List[Dict]              # supporting headlines


@dataclass
class NarrativeDiscoveryOutput:
    active_narratives: List[NarrativeCase]      # all live narratives sorted by conviction
    top_conviction: NarrativeCase | None        # highest conviction play
    early_stage_alerts: List[NarrativeCase]     # stage == "early" — front-run these
    regime_aligned: List[NarrativeCase]         # regime_multiplier > 1.10
    cross_market_plays: List[NarrativeCase]     # beneficiaries span multiple markets
    summary: str                                 # plain language portfolio implication


# ---------------------------------------------------------------------------
# Claude analysis helper
# ---------------------------------------------------------------------------

def _get_api_key() -> str | None:
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    try:
        return st.secrets.get("ANTHROPIC_API_KEY", "").strip() or None
    except Exception:
        return None


def _analyze_narrative_with_claude(
    narrative_name: str,
    description: str,
    headlines: List[Dict],
    current_quad: str,
    regime_multiplier: float,
    pump_risk: float,
    api_key: str,
) -> Dict:
    """
    Use Claude to deeply analyze a specific live narrative.
    Returns structured insight: stage, catalyst_type, action_summary, key_risk.
    """
    headline_text = "\n".join(f"- {h['title']}" for h in headlines[:8])
    prompt = f"""You are a macro analyst and narrative-driven trader. Analyze this live market narrative.

NARRATIVE: {narrative_name}
DESCRIPTION: {description}
CURRENT MACRO REGIME: {current_quad}
REGIME AMPLIFICATION: {regime_multiplier:.2f}x (>1.0 means regime supports this narrative)
PUMP RISK BASELINE: {pump_risk:.0%} (0%=pure thesis, 100%=pure pump/momentum)

CURRENT HEADLINES:
{headline_text}

Analyze this narrative and respond ONLY with valid JSON (no markdown):
{{
  "stage": "early|building|mature|exhausted|invalid",
  "catalyst_type": "competitor_admission|government_contract|earnings_beat|regulatory_change|product_launch|partnership|research_breakthrough|other",
  "narrative_strength": 0.0-1.0,
  "is_legitimate_thesis": true|false,
  "institutional_discovery_phase": "pre|early|mid|late",
  "action_summary": "1-2 sentence specific actionable insight with ticker names",
  "primary_catalyst_detail": "what specifically triggered this narrative",
  "key_risk": "most important thing that would kill this trade",
  "front_run_opportunity": true|false,
  "timing_note": "now|wait_for_pullback|too_late|accumulate_on_dips"
}}"""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=10,
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"].strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class NarrativeDiscoveryEngine:
    """
    Converts raw narrative signals into ranked, regime-adjusted narrative cases
    with Claude-powered depth analysis for the top signals.
    """

    def run(
        self,
        narrative_signals: Dict,        # from load_narrative_signals()
        current_quad: str,              # structural quad
        monthly_quad: str,
        scenario_features: Dict | None = None,
        use_claude: bool = True,
    ) -> NarrativeDiscoveryOutput:
        scenario_features = scenario_features or {}
        all_items = narrative_signals.get("narratives", {})
        api_key = _get_api_key() if use_claude else None

        cases: List[NarrativeCase] = []

        for narrative_tmpl in _NARRATIVE_LIBRARY:
            name = narrative_tmpl.name
            signal_data = all_items.get(name, {})

            net_score = float(signal_data.get("net_score", 0.0))
            act_score = float(signal_data.get("activation_score", 0.0))
            is_live = bool(signal_data.get("is_live", False))
            headlines = signal_data.get("items", [])

            # Skip if no signal at all
            if net_score <= 0 and not is_live:
                continue

            # Regime multiplier (how much current quad amplifies this narrative)
            regime_mult = float(narrative_tmpl.regime_alignment.get(current_quad, 1.0))
            # Monthly quad adds a partial boost
            monthly_mult = float(narrative_tmpl.regime_alignment.get(monthly_quad, 1.0))
            effective_mult = clamp01((0.65 * regime_mult + 0.35 * monthly_mult) / 1.5)

            # Base conviction from news signal strength
            signal_strength = clamp01(net_score / 8.0)  # normalize 0-8+ → 0-1
            base_conviction = clamp01(
                signal_strength * 0.50
                + (0.30 if is_live else 0.0)
                + 0.20 * min(1.0, act_score / 5.0)
            )
            # Apply pump risk penalty
            conviction = clamp01(base_conviction * (1.0 - 0.50 * narrative_tmpl.pump_risk))
            conviction = min(conviction, narrative_tmpl.conviction_ceiling)
            regime_adjusted = clamp01(conviction * (0.60 + 0.40 * effective_mult))

            # Scenario feature boosts
            if name == "Iran-Hormuz Oil Supply Shock":
                war_h = float(scenario_features.get("war_oil_hazard", 0.0))
                conviction = clamp01(conviction + 0.25 * war_h)
                regime_adjusted = clamp01(regime_adjusted + 0.25 * war_h)
            elif "Indonesia Coal" in name:
                em_pain = float(scenario_features.get("em_importer_pain", 0.0))
                petro = float(scenario_features.get("petrodollar_shock", 0.0))
                # Coal exporters benefit from petrodollar shock
                conviction = clamp01(conviction + 0.20 * petro)
            elif "Fed Pivot" in name:
                pol_h = float(scenario_features.get("policy_pressure_hazard", 0.0))
                conviction = clamp01(conviction - 0.20 * pol_h)  # policy pressure = pivot less likely

            # Claude deep analysis for top narratives (top 4 by conviction)
            claude_data: Dict = {}
            if api_key and conviction >= 0.30 and headlines:
                claude_data = _analyze_narrative_with_claude(
                    narrative_name=name,
                    description=narrative_tmpl.description,
                    headlines=headlines,
                    current_quad=current_quad,
                    regime_multiplier=regime_mult,
                    pump_risk=narrative_tmpl.pump_risk,
                    api_key=api_key,
                )

            # Stage determination
            if claude_data.get("stage"):
                stage = str(claude_data["stage"])
            elif net_score >= 6:
                stage = "building"
            elif net_score >= 3:
                stage = "early"
            elif net_score >= 1:
                stage = "early"
            else:
                stage = "watching"

            # Action summary
            if claude_data.get("action_summary"):
                action_summary = str(claude_data["action_summary"])
            else:
                bens = narrative_tmpl.beneficiaries
                primary = next(iter(bens.values()), [])[:3] if bens else []
                action_summary = (
                    f"Narrative active — watch {', '.join(primary[:2])} for entry. "
                    f"Confirm via: {narrative_tmpl.confirmation_signals[0] if narrative_tmpl.confirmation_signals else 'market data'}"
                )

            # Claude insight
            if claude_data.get("primary_catalyst_detail") and claude_data.get("front_run_opportunity") is not None:
                fr = "FRONT-RUN OPPORTUNITY" if claude_data.get("front_run_opportunity") else ""
                timing = claude_data.get("timing_note", "")
                claude_insight = f"{fr} [{timing}] — {claude_data.get('primary_catalyst_detail', '')} | Key risk: {claude_data.get('key_risk', 'unknown')}"
            else:
                phase = claude_data.get("institutional_discovery_phase", "")
                claude_insight = f"Institutional discovery: {phase} phase" if phase else "Analysis pending"

            catalyst_type = str(claude_data.get("catalyst_type", narrative_tmpl.catalyst_types[0] if narrative_tmpl.catalyst_types else "unknown"))

            # Flatten beneficiaries into primary and secondary
            all_bens = []
            for market, tickers in narrative_tmpl.beneficiaries.items():
                for t in tickers:
                    if t not in all_bens:
                        all_bens.append(t)
            primary_bens = all_bens[:5]
            secondary_bens = all_bens[5:10]

            all_fades = []
            for market, tickers in narrative_tmpl.fades.items():
                all_fades.extend(tickers)

            invalidators = [claude_data.get("key_risk", "")] if claude_data.get("key_risk") else []
            invalidators += narrative_tmpl.invalidation_keywords[:3]

            cases.append(NarrativeCase(
                name=name,
                category=narrative_tmpl.category,
                stage=stage,
                conviction=conviction,
                regime_multiplier=effective_mult,
                regime_adjusted_conviction=regime_adjusted,
                pump_risk=narrative_tmpl.pump_risk,
                net_news_score=net_score,
                primary_beneficiaries=primary_bens,
                secondary_beneficiaries=secondary_bens,
                what_fades=all_fades[:5],
                claude_insight=claude_insight,
                confirmation_signals=narrative_tmpl.confirmation_signals[:3],
                catalyst_type=catalyst_type,
                action_summary=action_summary,
                invalidators=invalidators[:3],
                headlines=headlines[:3],
            ))

        # Sort by regime-adjusted conviction
        cases.sort(key=lambda c: c.regime_adjusted_conviction, reverse=True)

        top_conviction = cases[0] if cases else None
        early_stage_alerts = [c for c in cases if c.stage == "early" and c.conviction >= 0.25]
        regime_aligned = [c for c in cases if c.regime_multiplier >= 0.75]
        cross_market = [c for c in cases if len([
            m for m in c.primary_beneficiaries if any(m.endswith(x) for x in [".JK", "-USD", "=X", "=F"])
        ]) >= 2]

        if top_conviction:
            summary = (
                f"Top narrative: {top_conviction.name} ({int(top_conviction.regime_adjusted_conviction*100)}% regime-adjusted conviction, "
                f"{top_conviction.stage} stage). {top_conviction.action_summary}"
            )
        else:
            summary = "No dominant narrative detected. Stay in regime-driven positions."

        return NarrativeDiscoveryOutput(
            active_narratives=cases,
            top_conviction=top_conviction,
            early_stage_alerts=early_stage_alerts,
            regime_aligned=regime_aligned,
            cross_market_plays=cross_market,
            summary=summary,
        )
