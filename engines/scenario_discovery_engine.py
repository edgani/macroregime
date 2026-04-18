from __future__ import annotations
from typing import Dict, List

from domain.types import ScenarioCase
from utils.math_utils import normalize_dict


class ScenarioDiscoveryEngine:
    """Adaptive scenario discovery engine.

    FIX: Original generated the same static scenarios regardless of what news said.
    Now: Claude's semantic analysis directly modifies scenario probabilities and can
    inject entirely new scenario branches (e.g., specific Iran war branch) based on
    current news. This makes it adaptive to events in real-time.
    """

    def run(
        self,
        structural: Dict[str, float],
        tactical: Dict[str, float],
        shock: Dict[str, float],
        scenario_flags: Dict[str, float] | None,
        playbooks: List[Dict[str, object]],
        analogs: List[Dict[str, object]] | None = None,
        news_state: Dict[str, object] | None = None,
        transition_output=None,  # Optional RegimeTransitionOutput for forward-looking paths
    ) -> Dict[str, ScenarioCase]:
        structural_quad = structural.get("structural_quad", structural.get("current_quad", "Q?"))
        structural_next = structural.get("structural_next_quad", structural.get("next_quad", structural_quad))
        monthly_quad = structural.get("monthly_quad", structural_quad)
        monthly_next = structural.get("monthly_next_quad", monthly_quad)
        divergence = structural.get("divergence_state", "aligned" if structural_quad == monthly_quad else "divergent")
        operating = structural.get("operating_regime", f"Monthly {monthly_quad} inside Structural {structural_quad}" if divergence != "aligned" else f"Aligned {structural_quad}")

        weather = tactical.get("weather_bias", "mixed")
        hazard = float(structural.get("flip_hazard", 0.5))
        tactical_score = float(tactical.get("score", 0.5))
        confirm = float(tactical.get("cross_asset_confirm", 0.5))
        shock_strength = float(shock.get("override_strength", 0.0))
        shock_state = str(shock.get("state", "normal"))
        news = news_state or {}
        flags = scenario_flags or {}

        # Extract hazard scores from the upgraded news_event_engine
        war_h   = float(news.get("war_oil_hazard", 0.0))
        pol_h   = float(news.get("policy_pressure_hazard", 0.0))
        rel_h   = float(news.get("relief_hazard", 0.0))
        crd_h   = float(news.get("credit_stress_hazard", 0.0))

        # Claude semantic signals (from upgraded news_event_engine)
        front_run = news.get("front_run") or {}
        news_regime_shift_prob   = float(front_run.get("shift_probability", 0.0)) if isinstance(front_run, dict) else 0.0
        news_regime_shift_toward = str(front_run.get("toward_quad", "none")) if isinstance(front_run, dict) else "none"
        news_confidence          = float(front_run.get("confidence", 0.0)) if isinstance(front_run, dict) else 0.0
        news_what_to_watch       = str(front_run.get("what_to_watch", "")) if isinstance(front_run, dict) else ""

        # Transition engine signals (for forward-looking scenarios)
        transition_paths = []
        front_run_window = "not yet"
        if transition_output is not None:
            try:
                transition_paths = getattr(transition_output, "transition_paths", [])
                front_run_window = getattr(transition_output, "front_run_window", "not yet")
            except Exception:
                pass

        # ------------------------------------------------------------------
        # Base scenario set (regime-conditional)
        # ------------------------------------------------------------------
        raw: Dict[str, float] = {}

        if divergence == "aligned":
            raw[f"Base: aligned {structural_quad} continuation"] = (
                0.34 + 0.18 * float(structural.get("structural_confidence", structural.get("confidence", 0.5)))
                - 0.08 * hazard   # high flip hazard reduces base continuation probability
            )
            raw[f"Alt: tactical move toward {structural_next}"] = (
                0.18 + 0.18 * hazard + 0.10 * confirm + 0.08 * rel_h
            )
            raw["Family: shock branch"] = (
                0.12 + 0.22 * shock_strength + 0.08 * war_h + 0.06 * crd_h
            )
            raw["Family: broadening leadership"] = (
                0.12 + 0.15 * confirm + 0.06 * rel_h
            )
            raw["Family: false relief"] = (
                0.10 + 0.12 * max(0.0, hazard - confirm)
            )
        else:
            raw[f"Base: Monthly {monthly_quad} inside Structural {structural_quad}"] = (
                0.28 + 0.16 * tactical_score + 0.10 * confirm
            )
            raw[f"Alt: Monthly {monthly_quad} fades back to Structural {structural_quad}"] = (
                0.18 + 0.16 * max(0.0, 0.55 - confirm) + 0.10 * hazard
            )
            raw[f"Transition: Monthly {monthly_quad} broadens into Structural {monthly_next}"] = (
                0.12 + 0.14 * confirm + 0.10 * rel_h + 0.08 * max(0.0, tactical_score - 0.52)
            )
            raw["Family: divergence resolves via signal confirmation"] = (
                0.10 + 0.14 * tactical_score + 0.08 * confirm
            )
            raw["Family: policy / rates override branch"] = (
                0.08 + 0.12 * pol_h + 0.08 * hazard
            )
            raw["Family: shock branch"] = (
                0.10 + 0.20 * shock_strength + 0.08 * war_h + 0.06 * crd_h
            )

        # ------------------------------------------------------------------
        # Out-of-box scenario flags (scenario_features-driven)
        # ------------------------------------------------------------------
        if float(flags.get("petrodollar_shock", 0.0)) >= 0.60:
            raw["Out-of-box: Petrodollar tightening shock"] = (
                0.12 + 0.20 * float(flags.get("petrodollar_shock", 0.0))
                + 0.06 * float(flags.get("em_importer_pain", 0.0))
                + 0.10 * war_h   # geopolitical news amplifies this
            )
        if float(flags.get("em_importer_pain", 0.0)) >= 0.58:
            raw["Out-of-box: EM importer pain / exporter split"] = (
                0.10 + 0.16 * float(flags.get("em_importer_pain", 0.0))
            )
        if float(flags.get("carry_unwind", 0.0)) >= 0.58:
            raw["Out-of-box: Carry unwind / dollar squeeze"] = (
                0.10 + 0.16 * float(flags.get("carry_unwind", 0.0)) + 0.08 * crd_h
            )
        if float(flags.get("china_false_dawn", 0.0)) >= 0.56:
            raw["Out-of-box: China reflation false dawn"] = (
                0.08 + 0.14 * float(flags.get("china_false_dawn", 0.0))
            )
        if float(flags.get("historical_repeat_score", 0.0)) >= 0.58:
            raw["Out-of-box: Historical repeat / stagflation echo"] = (
                0.08 + 0.16 * float(flags.get("historical_repeat_score", 0.0))
            )
        if crd_h >= 0.45:
            raw["Out-of-box: Credit stress / deleveraging"] = (
                0.08 + 0.18 * crd_h
            )

        # ------------------------------------------------------------------
        # NEWS-ADAPTIVE SCENARIOS (NEW)
        # These inject dynamically from what the news actually says.
        # Claude's semantic analysis determines if these are active and how strong.
        # ------------------------------------------------------------------
        claude_analysis = news.get("claude_analysis") or {}
        if isinstance(claude_analysis, dict) and claude_analysis:
            ev = claude_analysis.get("event_specific") or {}

            # Iran war / Hormuz strait closure scenario
            if (isinstance(ev, dict) and ev.get("war_escalation")) or war_h >= 0.50:
                raw["News-adaptive: Iran/Mideast war escalation — oil supply shock"] = (
                    0.06 + 0.35 * war_h + 0.20 * news_confidence
                    + 0.10 * float(flags.get("petrodollar_shock", 0.0))
                )

            # Ceasefire / rapid de-escalation
            if (isinstance(ev, dict) and ev.get("ceasefire_or_relief")) or rel_h >= 0.45:
                raw["News-adaptive: Ceasefire / rapid de-escalation — relief squeeze"] = (
                    0.06 + 0.35 * rel_h + 0.15 * news_confidence
                )

            # Policy pivot (Fed cut signal, dovish surprise)
            if isinstance(ev, dict) and ev.get("policy_pivot"):
                raw["News-adaptive: Fed policy pivot / dovish surprise"] = (
                    0.06 + 0.30 * pol_h + 0.20 * news_confidence + 0.10 * rel_h
                )

            # Tariff escalation / trade war restart
            if isinstance(ev, dict) and ev.get("tariff_escalation"):
                raw["News-adaptive: Tariff escalation — global trade disruption"] = (
                    0.06 + 0.25 * pol_h + 0.15 * news_confidence
                    + 0.08 * float(flags.get("em_importer_pain", 0.0))
                )

            # Credit crisis / financial accident
            if isinstance(ev, dict) and ev.get("credit_stress"):
                raw["News-adaptive: Credit stress / financial accident risk"] = (
                    0.06 + 0.30 * crd_h + 0.20 * news_confidence
                )

            # Claude-identified regime shift toward a specific quad
            if news_regime_shift_toward not in ("none", "", None) and news_regime_shift_prob >= 0.20:
                label = f"News-adaptive: Claude-identified {structural_quad}→{news_regime_shift_toward} transition"
                raw[label] = (
                    0.05 + 0.40 * news_regime_shift_prob * news_confidence
                )

        # ------------------------------------------------------------------
        # TRANSITION-ENGINE FORWARD PATHS (from RegimeTransitionEngine)
        # ------------------------------------------------------------------
        for tpath in transition_paths[:2]:  # top 2 most probable transitions
            if tpath.probability >= 0.20:
                label = f"Forward-path: {tpath.from_quad}→{tpath.to_quad} (EW: {int(tpath.early_warning_score*100)}%)"
                # Don't duplicate if already in raw
                if label not in raw:
                    raw[label] = max(raw.get(label, 0.0), tpath.probability * 0.65)

        # ------------------------------------------------------------------
        # Historical analogs
        # ------------------------------------------------------------------
        if analogs:
            top_analog = max(analogs, key=lambda x: float(x.get("similarity", 0.0)))
            label = top_analog.get("label", "Historical analog repeat")
            raw[f"Analog: {label}"] = max(
                raw.get(f"Analog: {label}", 0.0),
                0.08 + 0.18 * float(top_analog.get("similarity", 0.0))
            )

        # ------------------------------------------------------------------
        # Playbooks
        # ------------------------------------------------------------------
        if playbooks:
            top_playbook = max(playbooks, key=lambda x: float(x.get("hypothesis_score", 0.0)))
            raw[f"Playbook: {top_playbook['name']}"] = max(
                raw.get(f"Playbook: {top_playbook['name']}", 0.0),
                0.08 + 0.25 * float(top_playbook.get("hypothesis_score", 0.0))
            )

        # ------------------------------------------------------------------
        # Normalize and build ScenarioCase objects
        # ------------------------------------------------------------------
        probs = normalize_dict(raw)
        cases: Dict[str, ScenarioCase] = {}

        for name, p in probs.items():
            winners, losers, invalidators = _infer_scenario_playbook(
                name=name,
                flags=flags,
                shock_state=shock_state,
                war_h=war_h,
                rel_h=rel_h,
                pol_h=pol_h,
                crd_h=crd_h,
                news_what_to_watch=news_what_to_watch,
                structural_quad=structural_quad,
                monthly_quad=monthly_quad,
                transition_paths=transition_paths,
            )

            desc = (
                f"{name} under structural {structural_quad}, monthly {monthly_quad}, "
                f"operating regime {operating}, weather {weather}, shock {shock_state}, "
                f"news-state {str(news.get('state', 'quiet'))}"
            )
            if news_what_to_watch and "News-adaptive" in name:
                desc += f". WATCH: {news_what_to_watch}"

            cases[name] = ScenarioCase(
                name=name,
                probability=p,
                description=desc,
                invalidators=invalidators,
                winners=winners,
                losers=losers,
            )

        return dict(sorted(cases.items(), key=lambda kv: kv[1].probability, reverse=True))


def _infer_scenario_playbook(
    name: str,
    flags: Dict[str, float],
    shock_state: str,
    war_h: float,
    rel_h: float,
    pol_h: float,
    crd_h: float,
    news_what_to_watch: str,
    structural_quad: str,
    monthly_quad: str,
    transition_paths: list,
) -> tuple[list, list, list]:
    lower = name.lower()

    # -- Geopolitical / war / oil scenarios --
    if any(x in lower for x in ["petrodollar", "war", "iran", "mideast", "oil shock", "hormuz", "escalat"]):
        winners = ["Energy / hard assets", "Gold / selective defensives", "Petro-exporters (NOK, CAD)", "IDR coal exporters"]
        losers  = ["Oil importers / EM current account deficits", "Weak small caps", "Broad cyclical beta", "IDR if oil stays bid"]
        inv     = ["Oil impulse fades >10% from peak", "USD and rates both calm materially", "Ceasefire confirmation pulls rug", "OPEC supply response"]

    # -- Ceasefire / relief / de-escalation --
    elif any(x in lower for x in ["ceasefire", "de-escal", "relief", "truce", "peace"]):
        winners = ["Equal-weight / broad market relief", "EM catch-up (IDR, INR beneficiaries)", "Prior beaten-down cyclicals", "Risk parity restoration"]
        losers  = ["Gold as safe haven bid collapses", "Energy outperformers give back gains", "Crowded defensives"]
        inv     = ["Escalation resumes within weeks", "Oil fails to fall despite ceasefire", "Structural regime (Q3/Q4) reasserts quickly"]

    # -- Credit stress --
    elif any(x in lower for x in ["credit stress", "financial accident", "deleverag"]):
        winners = ["Cash / T-bills", "IG over HY", "Gold / safe haven", "JPY / CHF"]
        losers  = ["HY / leveraged loans", "Crowded carry trades", "High beta small caps", "Crypto"]
        inv     = ["HY spreads re-tighten quickly on Fed backstop", "Credit event contained to one sector"]

    # -- Carry unwind / dollar squeeze --
    elif any(x in lower for x in ["carry unwind", "dollar squeeze"]):
        winners = ["USD cash", "Funding-safe majors (JPY, CHF)", "IG bonds"]
        losers  = ["Crowded carry", "Fragile EM FX", "High beta crypto"]
        inv     = ["Dollar fails to extend", "Rates calm and carry re-bid returns", "Vol compresses fast"]

    # -- Policy pivot --
    elif any(x in lower for x in ["fed policy", "policy pivot", "dovish"]):
        winners = ["Duration (TLT)", "EM FX", "Growth/tech names", "Crypto if risk-on confirmed"]
        losers  = ["Banks (NIM compression)", "Overcrowded defensive yield plays"]
        inv     = ["Inflation re-accelerates forcing Fed to reverse", "Long end sells off on policy credibility concerns"]

    # -- Tariff / trade war --
    elif any(x in lower for x in ["tariff", "trade war", "trade disruption"]):
        winners = ["Domestic-facing US companies", "Beneficiaries of reshoring", "Gold"]
        losers  = ["Global trade-exposed cyclicals", "EM exporters", "Tech supply chain"]
        inv     = ["Trade deal signed / tariffs rolled back", "WTO resolution", "Election change in US policy direction"]

    # -- Forward-path transition scenarios --
    elif "forward-path" in lower:
        toward = ""
        for tpath in transition_paths:
            if tpath.to_quad in lower or f"→{tpath.to_quad}" in name:
                toward = tpath.to_quad
                break
        if toward == "Q1":
            winners = ["Small caps / equal-weight", "EM risk-on", "Broad cyclical recovery"]
            losers  = ["Defensives / gold", "Short duration"]
            inv     = ["ISM fails to recover above 50", "Inflation re-accelerates before growth returns"]
        elif toward == "Q2":
            winners = ["Energy / materials / commodities", "Cyclicals", "IHSG coal names"]
            losers  = ["Bonds / duration", "Defensives"]
            inv     = ["Oil reverses sharply", "Growth rolls over before inflation peaks"]
        elif toward == "Q3":
            winners = ["Energy", "Gold / hard assets", "Cash"]
            losers  = ["Equities broadly", "Duration bonds", "EM growth stories"]
            inv     = ["Inflation breaks faster than expected", "Fed turns more dovish"]
        elif toward == "Q4":
            winners = ["Duration / TLT", "Quality defensives", "Gold"]
            losers  = ["Small caps", "Cyclicals", "EM growth stories"]
            inv     = ["Growth doesn't decelerate fast enough", "Inflation stays elevated"]
        else:
            winners = ["Selective regime-aligned names"]
            losers  = ["Consensus mismatched expressions"]
            inv     = ["Transition signal reverses"]

    # -- Historical analog --
    elif any(x in lower for x in ["historical repeat", "analog"]):
        winners = ["Names aligned with analog path", "Selective hard assets / defensives"]
        losers  = ["Crowded late-cycle beta", "Consensus laggards if analog fails"]
        inv     = ["Cross-asset path diverges from analog quickly", "Breadth expands against analog script"]

    # -- Broadening / leadership --
    elif any(x in lower for x in ["broadens", "leadership", "signal confirmation", "broadening"]):
        winners = ["Equal-weight / selective beta", "EM catch-up routes", "Quality laggards if breadth confirms"]
        losers  = ["Consensus hedges", "Ultra-defensive late trades"]
        inv     = ["Equal-weight and small caps fail to confirm", "USD re-accelerates"]

    # -- Default --
    else:
        winners = ["Selective winners with scenario fit"]
        losers  = ["Crowded mismatched expressions"]
        inv     = ["Cross-asset confirmation flips materially", "Shock state fades or intensifies against the branch"]

    if shock_state == "shock":
        inv.append("Vol and credit calm faster than the branch assumes")
    if news_what_to_watch:
        inv.append(f"Watch: {news_what_to_watch}")

    return winners, losers, inv
