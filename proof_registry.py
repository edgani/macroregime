"""Exact-scope proof and promotion registry.

Software tests and historical research diagnostics are deliberately separated from predictive
promotion.  Missing evidence always leaves the component blocked.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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


def default_registry() -> dict[str, Any]:
    components = {
        "generic_price_context": {"scope": "ALL_MARKETS_DESCRIPTIVE", "state": "DESCRIPTIVE_CONTROL"},
        "us_directional_selector": {"scope": "US_EQUITIES_DAILY", "state": "DESIGN_ONLY"},
        "ihsg_long_selector": {"scope": "IHSG_LONG_ONLY_DAILY", "state": "DESIGN_ONLY"},
        "crypto_directional_selector": {"scope": "CRYPTO_PER_ASSET_PER_VENUE", "state": "DESIGN_ONLY"},
        "commodity_directional_selector": {"scope": "FUTURES_PER_CONTRACT", "state": "DESIGN_ONLY"},
        "fx_pair_selector": {"scope": "FX_PAIR_SPECIFIC", "state": "DESIGN_ONLY"},
        "wasserstein_hmm": {"scope": "CROSS_ASSET_DAILY_ALLOCATION_CHALLENGER", "state": "DESIGN_ONLY"},
        "simple_hmm": {"scope": "CROSS_ASSET_DAILY_CONTEXT_CHALLENGER", "state": "DESIGN_ONLY"},
        "volatility_risk_premium": {"scope": "OPTIONS_PER_INSTRUMENT", "state": "DESIGN_ONLY"},
        "dealer_greeks": {"scope": "OPTIONS_PER_INSTRUMENT", "state": "DESCRIPTIVE_CONTROL"},
        "order_flow_imbalance": {"scope": "VENUE_SPECIFIC_EXECUTION", "state": "DESIGN_ONLY"},
        "failed_breakout": {"scope": "MARKET_SPECIFIC_EXECUTION_PATTERN", "state": "DESIGN_ONLY"},
        "merton_structural_credit": {"scope": "COMPANY_SPECIFIC_CREDIT_CONTEXT", "state": "DESIGN_ONLY"},
        "alpha_scenario_valuation": {"scope": "COMPANY_OR_TOKEN_SPECIFIC", "state": "DESIGN_ONLY"},
        "portfolio_allocator": {"scope": "VALIDATED_RETURN_STREAMS_ONLY", "state": "DESIGN_ONLY"},
    }
    for row in components.values():
        row.update({
            "wfa_pass": False,
            "lockbox_pass": False,
            "prospective_pass": False,
            "cost_model_pass": False,
            "multiple_testing_pass": False,
            "human_signoff": False,
            "capital_permission": "BLOCKED",
        })
    return {
        "version": "4.2",
        "claim_ceiling": "RESEARCH_ONLY_UNTIL_EXACT_SCOPE_GATES_PASS",
        "promotion_ladder": PROMOTION_LADDER,
        "components": components,
    }


def load_registry() -> dict[str, Any]:
    base = default_registry()
    if not REGISTRY_PATH.exists():
        return base
    try:
        raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return base
    for key, row in (raw.get("components") or {}).items():
        if key in base["components"] and isinstance(row, dict):
            base["components"][key].update(row)
    return base


def component_status(name: str) -> dict[str, Any]:
    reg = load_registry()
    row = dict((reg.get("components") or {}).get(name) or {})
    state = str(row.get("state") or "DESIGN_ONLY").upper()
    gate = all(bool(row.get(k)) for k in ("wfa_pass", "lockbox_pass", "prospective_pass", "cost_model_pass", "multiple_testing_pass"))
    human = bool(row.get("human_signoff"))
    eligible = state in PRODUCTION_STATES and gate
    row["predictive_promoted"] = bool(eligible)
    row["capital_permission"] = "HUMAN_APPROVED_LIMITED_PRODUCTION" if eligible and human else "BLOCKED"
    return row


def attach_proof_registry(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    reg = load_registry()
    components = reg.get("components") or {}
    promoted = [k for k in components if component_status(k).get("predictive_promoted")]
    desk["proof_registry"] = reg
    desk["proof_status"] = {
        "predictive_components_promoted": len(promoted),
        "promoted_components": promoted,
        "capital_permission": "BLOCKED",
        "software_is_not_alpha": True,
        "claim_ceiling": reg.get("claim_ceiling"),
    }
    return desk
