"""narrative_discovery_engine.py"""
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


@dataclass
class NarrativeCase:
    name: str
    category: str
    stage: str
    conviction: float
    regime_multiplier: float
    regime_adjusted_conviction: float
    pump_risk: float
    net_news_score: float
    primary_beneficiaries: List[str]
    secondary_beneficiaries: List[str]
    what_fades: List[str]
    claude_insight: str
    confirmation_signals: List[str]
    catalyst_type: str
    action_summary: str
    invalidators: List[str]
    headlines: List[Dict]


@dataclass
class NarrativeDiscoveryOutput:
    active_narratives: List[NarrativeCase]
    top_conviction: NarrativeCase | None
    early_stage_alerts: List[NarrativeCase]
    regime_aligned: List[NarrativeCase]
    cross_market_plays: List[NarrativeCase]
    summary: str


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
    headline_text = "\n".join(f"- {h['title']}" for h in headlines[:8])
    prompt = f"""You are a macro analyst and narrative-driven trader. Analyze this live market narrative.

NARRATIVE: {narrative_name}
DESCRIPTION: {description}
CURRENT MACRO REGIME: {current_quad}
REGIME AMPLIFICATION: {regime_multiplier:.2f}x
PUMP RISK BASELINE: {pump_risk:.0%}

CURRENT HEADLINES:
{headline_text}

Analyze and respond ONLY with valid JSON (no markdown):
{{
 "stage": "early|building|mature|exhausted|invalid",
 "catalyst_type": "competitor_admission|government_contract|earnings_beat|regulatory_change|product_launch|partnership|research_breakthrough|other",
 "narrative_strength": 0.0,
 "is_legitimate_thesis": true,
 "institutional_discovery_phase": "pre|early|mid|late",
 "action_summary": "1-2 sentence specific actionable insight with ticker names",
 "primary_catalyst_detail": "what specifically triggered this narrative",
 "key_risk": "most important thing that would kill this trade",
 "front_run_opportunity": true,
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
                "model": "claude-3-haiku-20240307",
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


class NarrativeDiscoveryEngine:
    def run(
        self,
        narrative_signals: Dict,
        current_quad: str,
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

            if net_score <= 0 and not is_live:
                continue

            regime_mult = float(narrative_tmpl.regime_alignment.get(current_quad, 1.0))
            monthly_mult = float(narrative_tmpl.regime_alignment.get(monthly_quad, 1.0))
            effective_mult = clamp01((0.65 * regime_mult + 0.35 * monthly_mult) / 1.5)

            signal_strength = clamp01(net_score / 8.0)
            base_conviction = clamp01(
                signal_strength * 0.50
                + (0.30 if is_live else 0.0)
                + 0.20 * min(1.0, act_score / 5.0)
            )
            conviction = clamp01(
                base_conviction * (1.0 - 0.50 * narrative_tmpl.pump_risk)
            )
            conviction = min(conviction, narrative_tmpl.conviction_ceiling)
            regime_adjusted = clamp01(conviction * (0.60 + 0.40 * effective_mult))

            if name == "Iran-Hormuz Oil Supply Shock":
                war_h = float(scenario_features.get("war_oil_hazard", 0.0))
                conviction = clamp01(conviction + 0.25 * war_h)
                regime_adjusted = clamp01(regime_adjusted + 0.25 * war_h)
            elif "Indonesia Coal" in name:
                petro = float(scenario_features.get("petrodollar_shock", 0.0))
                conviction = clamp01(conviction + 0.20 * petro)
            elif "Fed Pivot" in name:
                pol_h = float(scenario_features.get("policy_pressure_hazard", 0.0))
                conviction = clamp01(conviction - 0.20 * pol_h)

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

            if claude_data.get("action_summary"):
                action_summary = str(claude_data["action_summary"])
            else:
                bens = narrative_tmpl.beneficiaries
                primary = next(iter(bens.values()), [])[:3] if bens else []
                action_summary = (
                    f"Narrative active — watch {', '.join(primary[:2])} for entry. "
                    f"Confirm via: {narrative_tmpl.confirmation_signals[0] if narrative_tmpl.confirmation_signals else 'market data'}"
                )

            if claude_data.get("primary_catalyst_detail") and claude_data.get(
                "front_run_opportunity"
            ) is not None:
                fr = (
                    "FRONT-RUN OPPORTUNITY"
                    if claude_data.get("front_run_opportunity")
                    else ""
                )
                timing = claude_data.get("timing_note", "")
                claude_insight = f"{fr} [{timing}] — {claude_data.get('primary_catalyst_detail', '')} | Key risk: {claude_data.get('key_risk', 'unknown')}"
            else:
                phase = claude_data.get("institutional_discovery_phase", "")
                claude_insight = (
                    f"Institutional discovery: {phase} phase" if phase else "Analysis pending"
                )

            catalyst_type = str(
                claude_data.get(
                    "catalyst_type",
                    narrative_tmpl.catalyst_types[0]
                    if narrative_tmpl.catalyst_types
                    else "unknown",
                )
            )

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

            invalidators = (
                [claude_data.get("key_risk", "")]
                if claude_data.get("key_risk")
                else []
            )
            invalidators += narrative_tmpl.invalidation_keywords[:3]

            cases.append(
                NarrativeCase(
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
                )
            )

        cases.sort(key=lambda c: c.regime_adjusted_conviction, reverse=True)

        top_conviction = cases[0] if cases else None
        early_stage_alerts = [
            c for c in cases if c.stage == "early" and c.conviction >= 0.25
        ]
        regime_aligned = [c for c in cases if c.regime_multiplier >= 0.75]
        cross_market = [
            c
            for c in cases
            if len(
                [
                    m
                    for m in c.primary_beneficiaries
                    if any(m.endswith(x) for x in [".JK", "-USD", "=X", "=F"])
                ]
            )
            >= 2
        ]

        if top_conviction:
            summary = (
                f"Top narrative: {top_conviction.name} ({int(top_conviction.regime_adjusted_conviction * 100)}% regime-adjusted conviction, "
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
