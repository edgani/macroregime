"""War Room OS V7.6 final production boundary.

This contract makes the release usable without converting research context into trade permission.
The only decision-active market component is the previously confirmed broad-US-equity monthly
risk cap. All ticker, directional, target, timing, short, leverage and cross-market claims remain
fail-closed until an exact-scope signed proof receipt exists.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
RELEASE_ID = "WAR_ROOM_OS_V76_FINAL_SAFE_KERNEL"
RELEASE_LABEL = "War Room OS V7.6 Final Safe Kernel"
RELEASE_DATE = "2026-07-26"

SCOPED_DECISION_COMPONENTS = ("US_SMA10_MONTHLY_RISK_CAP",)
DIRECTIONAL_OR_TICKER_COMPONENTS_ACTIVE = 0
GLOBAL_TICKER_CAPITAL_PERMISSION = "BLOCKED"
SCOPED_RISK_PERMISSION = "CONDITIONAL_RISK_CAP_ONLY_FOR_US_BROAD_EQUITY_REDUCTION"

NEGATIVE_RESEARCH_RESULTS = {
    "V73_CUSP_STRUCTURAL_FRAGILITY_HISTORICAL": ROOT / "research_v57/results/V73_CUSP_HISTORICAL_RESULTS.json",
    "V74_BREADTH_CUSP_VOLATILITY_TRANSITION": ROOT / "research_v57/results/V74_BREADTH_CUSP_RESULTS.json",
    "V75_PRE1973_CUSP_REGIME_DEPENDENCE": ROOT / "research_v57/results/V75_PRE1973_CUSP_RESULTS.json",
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def release_contract() -> dict[str, Any]:
    from research_evidence_v66 import load_research_evidence_v66

    v66 = load_research_evidence_v66()
    v72 = _read_json(ROOT / "V72_DATA_ACQUISITION_STATUS.json")
    negative = []
    for study_id, path in NEGATIVE_RESEARCH_RESULTS.items():
        result = _read_json(path)
        negative.append({
            "study_id": study_id,
            "file": str(path.relative_to(ROOT)),
            "verdict": result.get("verdict", "UNAVAILABLE_FAIL_CLOSED"),
            "live_decision_weight": float(result.get("live_decision_weight") or 0.0),
            "capital_permission": result.get("capital_permission", "BLOCKED"),
            "promoted": bool(result.get("promoted_live") or result.get("promoted_current")),
        })

    risk_controls = v66.get("decision_active_risk_controls") or []
    exact_control = next((x for x in risk_controls if x.get("component_id") == SCOPED_DECISION_COMPONENTS[0]), None)
    negative_safe = all(
        row["verdict"] == "NOT_PROVEN"
        and row["live_decision_weight"] == 0.0
        and row["capital_permission"] == "BLOCKED"
        and not row["promoted"]
        for row in negative
    )
    scoped_control_safe = bool(
        exact_control
        and exact_control.get("ticker_permission") is False
        and exact_control.get("short_permission") is False
        and exact_control.get("leverage_permission") is False
        and exact_control.get("cross_market_permission") is False
        and exact_control.get("capital_creation_permission") is False
    )

    status = "FINAL_FOR_EXACT_US_RISK_CAP_SCOPE" if negative_safe and scoped_control_safe else "FAIL_CLOSED_REVIEW_REQUIRED"
    return {
        "schema": "warroom.release_contract.v76",
        "release_id": RELEASE_ID,
        "release_label": RELEASE_LABEL,
        "release_date": RELEASE_DATE,
        "status": status,
        "final_for_current_usable_scope": status == "FINAL_FOR_EXACT_US_RISK_CAP_SCOPE",
        "universal_cross_market_alpha_proven": False,
        "scoped_decision_components": list(SCOPED_DECISION_COMPONENTS),
        "decision_active_scoped_risk_controls": 1 if scoped_control_safe else 0,
        "decision_active_ticker_or_directional_components": DIRECTIONAL_OR_TICKER_COMPONENTS_ACTIVE,
        "global_ticker_capital_permission": GLOBAL_TICKER_CAPITAL_PERMISSION,
        "scoped_risk_permission": SCOPED_RISK_PERMISSION if scoped_control_safe else "NO_PERMISSION_FAIL_CLOSED",
        "v66_scoped_control": exact_control or {},
        "v72_data_acquisition": {
            "status": v72.get("status", "UNAVAILABLE_FAIL_CLOSED"),
            "licensed_files_present": int(v72.get("licensed_files_present") or 0),
            "predictive_components_promoted": int(v72.get("predictive_components_promoted") or 0),
            "capital_permission": v72.get("capital_permission", "BLOCKED"),
        },
        "negative_research_results": negative,
        "claim_boundary": (
            "Final and usable for one exact completed-month broad-US-equity exposure-cap scope. "
            "All ticker selection, long/short direction, target, timing, leverage, crash prediction, "
            "and cross-market capital remain blocked. Descriptive lifecycle states are observations, not alpha proof."
        ),
    }


def validate_runtime_desk(desk: dict[str, Any]) -> dict[str, Any]:
    """Fail if a normal dashboard snapshot leaks unproven capital or predictive semantics."""
    failures: list[str] = []
    alpha = desk.get("alpha") if isinstance(desk.get("alpha"), list) else []
    for idx, row in enumerate(alpha):
        if not isinstance(row, dict):
            failures.append(f"alpha[{idx}] is not an object")
            continue
        if str(row.get("capital_permission") or "BLOCKED").upper() != "BLOCKED":
            failures.append(f"alpha[{idx}] capital permission is not BLOCKED")
        if row.get("upside") is not None or row.get("base_rate") is not None or row.get("asymmetry") is not None:
            failures.append(f"alpha[{idx}] contains unproven numeric alpha fields")
        if str(row.get("proof_state") or "").upper() in {"PROVEN", "PRODUCTION", "PROMOTED"}:
            failures.append(f"alpha[{idx}] has promoted proof state")

    picks = ((desk.get("desk_picks") or {}).get("picks") or []) if isinstance(desk.get("desk_picks"), dict) else []
    if picks:
        failures.append("desk_picks must be empty while ticker capital is blocked")

    markets = desk.get("markets") if isinstance(desk.get("markets"), dict) else {}
    for market_id, market in markets.items():
        if not isinstance(market, dict):
            continue
        if str(market.get("directional_selector_permission") or "BLOCKED").upper() != "BLOCKED":
            failures.append(f"market {market_id} directional selector is not BLOCKED")

    contract = desk.get("release_contract_v76") or release_contract()
    if contract.get("status") != "FINAL_FOR_EXACT_US_RISK_CAP_SCOPE":
        failures.append("V7.6 release contract is not final for its exact scope")

    return {
        "schema": "warroom.runtime_validation.v76",
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "alpha_rows_checked": len(alpha),
        "market_rows_checked": len(markets),
        "ticker_capital_permission": "BLOCKED",
    }
