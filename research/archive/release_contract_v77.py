"""War Room OS V7.7 human-readable release contract.

V7.7 does not expand predictive permission. It inherits the exact V7.6 proof boundary,
fixes state-semantics classification (notably RISK_ON versus RISK_OFF), and adds a default
plain-language board so non-specialists can read the system without interpreting raw codes.
"""
from __future__ import annotations
from typing import Any
from release_contract_v76 import release_contract as release_contract_v76, validate_runtime_desk as validate_runtime_v76

RELEASE_ID = "WAR_ROOM_OS_V77_HUMAN_READABLE_FINAL"
RELEASE_LABEL = "War Room OS V7.7 Human-Readable Final"
RELEASE_DATE = "2026-07-26"


def release_contract() -> dict[str, Any]:
    inherited = release_contract_v76()
    inherited_ok = inherited.get("status") == "FINAL_FOR_EXACT_US_RISK_CAP_SCOPE"
    return {
        "schema": "warroom.release_contract.v77",
        "release_id": RELEASE_ID,
        "release_label": RELEASE_LABEL,
        "release_date": RELEASE_DATE,
        "status": "FINAL_HUMAN_READABLE_FOR_INHERITED_EXACT_SCOPE" if inherited_ok else "FAIL_CLOSED_REVIEW_REQUIRED",
        "final_for_current_usable_scope": bool(inherited_ok),
        "proof_boundary_inherited_from": inherited.get("release_id"),
        "scoped_decision_components": inherited.get("scoped_decision_components", []),
        "decision_active_ticker_or_directional_components": inherited.get("decision_active_ticker_or_directional_components", 0),
        "global_ticker_capital_permission": inherited.get("global_ticker_capital_permission", "BLOCKED"),
        "scoped_risk_permission": inherited.get("scoped_risk_permission", "NO_PERMISSION_FAIL_CLOSED"),
        "ux_contract": {
            "default_layout": "PLAIN_LANGUAGE_BOARD",
            "technical_detail": "COLLAPSED_BY_DEFAULT",
            "state_semantics": {
                "RISK_ON": "CONSTRUCTIVE",
                "RISK_OFF": "DESTRUCTIVE",
                "RESEARCH_BAND": "WATCH_NOT_PROBABILITY",
            },
            "capital_and_context_visually_separated": True,
            "layperson_legend_required": True,
        },
        "claim_boundary": (
            "V7.7 changes presentation and corrects state-label semantics only. It does not add ticker alpha, "
            "directional, target, timing, leverage, crash-prediction, or cross-market capital permission."
        ),
        "inherited_v76": inherited,
    }


def validate_runtime_desk(desk: dict[str, Any]) -> dict[str, Any]:
    base = validate_runtime_v76(desk)
    failures = list(base.get("failures") or [])
    contract = desk.get("release_contract_v77") or release_contract()
    if contract.get("status") != "FINAL_HUMAN_READABLE_FOR_INHERITED_EXACT_SCOPE":
        failures.append("V7.7 release contract is not final for inherited exact scope")
    ux = contract.get("ux_contract") or {}
    if ux.get("state_semantics", {}).get("RISK_ON") != "CONSTRUCTIVE":
        failures.append("RISK_ON semantic contract is not constructive")
    if ux.get("state_semantics", {}).get("RISK_OFF") != "DESTRUCTIVE":
        failures.append("RISK_OFF semantic contract is not destructive")
    return {
        "schema": "warroom.runtime_validation.v77",
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "inherited_v76_status": base.get("status"),
        "ticker_capital_permission": "BLOCKED",
    }
