"""Exact-scope proof and promotion registry.

The JSON registry is configuration only.  Boolean fields in it are never treated as evidence.
Predictive promotion requires a valid Ed25519-signed proof receipt bound to the exact component,
scope, code/data/spec/trial hashes, expiry, revocation state, prospective evidence, and human approval.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from proof_receipts import find_receipt, verify_receipt

HERE = Path(__file__).resolve().parent
REGISTRY_PATH = HERE / "component_registry_v42.json"

PROMOTION_LADDER = [
    "DESIGN_ONLY",
    "DATA_CONTRACT_VERIFIED",
    "DESCRIPTIVE_CONTROL",
    "OOS_CANDIDATE",
    "LOCKBOX_PASS",
    "PROSPECTIVE_WATCH",
    "LIMITED_PRODUCTION_ELIGIBLE",
    "HUMAN_APPROVED_LIMITED_PRODUCTION",
]
PRODUCTION_STATES = {"LIMITED_PRODUCTION_ELIGIBLE", "HUMAN_APPROVED_LIMITED_PRODUCTION"}


_COMPONENTS = {
    "generic_price_context": ("ALL_MARKETS_DESCRIPTIVE", "DESCRIPTIVE_CONTROL"),
    "us_directional_selector": ("US_EQUITIES_DAILY", "DESIGN_ONLY"),
    "ihsg_long_selector": ("IHSG_LONG_ONLY_DAILY", "DESIGN_ONLY"),
    "crypto_directional_selector": ("CRYPTO_PER_ASSET_PER_VENUE", "DESIGN_ONLY"),
    "commodity_directional_selector": ("FUTURES_PER_CONTRACT", "DESIGN_ONLY"),
    "fx_pair_selector": ("FX_PAIR_SPECIFIC", "DESIGN_ONLY"),
    "wasserstein_hmm": ("CROSS_ASSET_DAILY_ALLOCATION_CHALLENGER", "DESIGN_ONLY"),
    "simple_hmm": ("CROSS_ASSET_DAILY_CONTEXT_CHALLENGER", "DESIGN_ONLY"),
    "volatility_risk_premium": ("OPTIONS_PER_INSTRUMENT", "DESIGN_ONLY"),
    "dealer_greeks": ("OPTIONS_PER_INSTRUMENT", "DESCRIPTIVE_CONTROL"),
    "order_flow_imbalance": ("VENUE_SPECIFIC_EXECUTION", "DESIGN_ONLY"),
    "failed_breakout": ("MARKET_SPECIFIC_EXECUTION_PATTERN", "DESIGN_ONLY"),
    "merton_structural_credit": ("COMPANY_SPECIFIC_CREDIT_CONTEXT", "DESIGN_ONLY"),
    "alpha_scenario_valuation": ("COMPANY_OR_TOKEN_SPECIFIC", "DESIGN_ONLY"),
    "equity_scenario_probability_calibration": ("COMPANY_SPECIFIC_SCENARIO_PROBABILITY", "DESIGN_ONLY"),
    "token_scenario_probability_calibration": ("TOKEN_SPECIFIC_SCENARIO_PROBABILITY", "DESIGN_ONLY"),
    "portfolio_allocator": ("VALIDATED_RETURN_STREAMS_ONLY", "DESIGN_ONLY"),
    "position_lifecycle_v59": ("MARKET_SPECIFIC_POSITION_BUILD_SURGE_TOP_CONTEXT", "DESCRIPTIVE_CONTROL"),
    "mechanical_flow_driver_v60": ("ALL_MARKETS_MARKET_SPECIFIC_INPUT_CONTRACTS", "DESCRIPTIVE_CONTROL"),
    "early_move_driver_research_v60": ("CROSS_MARKET_ORIGIN_VULNERABILITY_TRIGGER_TRANSMISSION", "DESIGN_ONLY"),
    "price_derived_network_diffusion_v61": ("US_FIXED_PANEL_PRICE_DERIVED_NETWORK", "DESIGN_ONLY"),
    "discrete_event_origin_proxy_v62": ("US_FIXED_PANEL_GAP_VOLUME_EVENT_PROXY", "DESIGN_ONLY"),
    "sec_point_in_time_fundamentals_v62": ("US_SEC_XBRL_POINT_IN_TIME_PIPELINE", "DESIGN_ONLY"),
}


def default_registry() -> dict[str, Any]:
    components: dict[str, dict[str, Any]] = {}
    for name, (scope, state) in _COMPONENTS.items():
        components[name] = {
            "scope": scope,
            "state": state,
            "receipt_id": None,
            "proof_receipt_valid": False,
            "predictive_promoted": False,
            "capital_permission": "BLOCKED",
        }
    return {
        "version": "6.3",
        "claim_ceiling": "RESEARCH_ONLY_UNTIL_SIGNED_EXACT_SCOPE_GATES_PASS",
        "promotion_ladder": PROMOTION_LADDER,
        "registry_semantics": "CONFIGURATION_ONLY_NOT_EVIDENCE",
        "components": components,
    }


def load_registry() -> dict[str, Any]:
    """Load only non-evidentiary configuration fields from the editable registry."""
    base = default_registry()
    if not REGISTRY_PATH.exists():
        return base
    try:
        raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return base
    for key, row in (raw.get("components") or {}).items():
        if key not in base["components"] or not isinstance(row, dict):
            continue
        # Only a receipt pointer and free-text note are accepted from editable JSON.  All pass flags,
        # states and permissions are intentionally ignored.
        if row.get("receipt_id"):
            base["components"][key]["receipt_id"] = str(row["receipt_id"])
        if row.get("note"):
            base["components"][key]["note"] = str(row["note"])
        ignored = sorted(set(row) - {"receipt_id", "note"})
        if ignored:
            base["components"][key]["untrusted_fields_ignored"] = ignored
    return base


def component_status(name: str) -> dict[str, Any]:
    reg = load_registry()
    row = dict((reg.get("components") or {}).get(name) or {})
    if not row:
        return {"state": "UNKNOWN_COMPONENT", "predictive_promoted": False, "capital_permission": "BLOCKED"}

    # Descriptive controls never become trade permission merely because they are useful in the UI.
    if row.get("state") == "DESCRIPTIVE_CONTROL":
        row.update({
            "proof_receipt_valid": False,
            "predictive_promoted": False,
            "capital_permission": "BLOCKED",
            "promotion_reason": "descriptive component; no predictive/capital semantics",
        })
        return row

    receipt_path = find_receipt(row.get("receipt_id"))
    proof = verify_receipt(
        receipt_path,
        component=name,
        scope=str(row.get("scope") or ""),
        claim_type="CAPITAL_PERMISSION",
    )
    row["proof_receipt"] = proof
    row["proof_receipt_valid"] = bool(proof.get("valid"))
    row["predictive_promoted"] = bool(proof.get("valid"))
    row["state"] = "HUMAN_APPROVED_LIMITED_PRODUCTION" if proof.get("valid") else "DESIGN_ONLY"
    row["capital_permission"] = "HUMAN_APPROVED_LIMITED_PRODUCTION" if proof.get("valid") else "BLOCKED"
    return row


def attach_proof_registry(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    reg = load_registry()
    statuses = {name: component_status(name) for name in reg.get("components") or {}}
    promoted = [name for name, row in statuses.items() if row.get("predictive_promoted")]
    capital = [name for name, row in statuses.items() if row.get("capital_permission") != "BLOCKED"]
    desk["proof_registry"] = {**reg, "components": statuses}
    desk["proof_status"] = {
        "predictive_components_promoted": len(promoted),
        "promoted_components": promoted,
        "capital_authorized_components": capital,
        "capital_permission": "HUMAN_APPROVED_LIMITED_PRODUCTION" if capital else "BLOCKED",
        "software_is_not_alpha": True,
        "claim_ceiling": reg.get("claim_ceiling"),
        "editable_boolean_flags_are_evidence": False,
    }
    return desk
