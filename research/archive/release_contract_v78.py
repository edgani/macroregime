"""War Room OS V7.8 proof-expansion checkpoint contract.

V7.8 deliberately removes the misleading word "final" from the release identity.  It adds
confirmatory negative results, a point-in-time data contract, a historical-membership guard,
and a stricter prospective ledger.  It inherits only the already-confirmed V6.6 US monthly
SMA10 exposure-cap permission.
"""
from __future__ import annotations
from typing import Any
from release_contract_v77 import release_contract as release_contract_v77, validate_runtime_desk as validate_runtime_v77

RELEASE_ID = "WAR_ROOM_OS_V78_PROOF_EXPANSION_CHECKPOINT"
RELEASE_LABEL = "War Room OS V7.8 Proof Expansion Checkpoint"
RELEASE_DATE = "2026-07-26"


def release_contract() -> dict[str, Any]:
    inherited = release_contract_v77()
    return {
        "schema": "warroom.release_contract.v78",
        "release_id": RELEASE_ID,
        "release_label": RELEASE_LABEL,
        "release_date": RELEASE_DATE,
        "status": "PROOF_EXPANSION_CHECKPOINT_NOT_FINAL_TRADING_SYSTEM",
        "final_trading_system": False,
        "proof_boundary_inherited_from": inherited.get("release_id"),
        "inherited_scoped_decision_components": inherited.get("scoped_decision_components", []),
        "inherited_scoped_risk_permission": inherited.get("scoped_risk_permission", "NO_PERMISSION_FAIL_CLOSED"),
        "new_decision_active_components": 0,
        "decision_active_ticker_or_directional_components": 0,
        "global_ticker_capital_permission": "BLOCKED",
        "new_confirmatory_families": {
            "cross_market_tsmom": "NOT_PROMOTED_POST_PUBLICATION_LOCKBOX",
            "cross_market_sma10_gold_oil_dxy": "0_OF_3_PROMOTED",
            "us_equity_vol12_risk_cap": "NOT_PROMOTED",
        },
        "proof_infrastructure_added": [
            "US point-in-time survivor-bias-free data contract",
            "historical S&P 500 membership interval research guard",
            "three-candidate frozen stock-level option/information proof protocol",
            "non-backfillable forecast and separate outcome hash chains",
        ],
        "next_hard_blocker": (
            "Lawful survivor-bias-free US security master, delistings, corporate actions, historical membership, "
            "point-in-time option surfaces, estimates and borrow/cost data for an untouched 2019-2024 ticker lockbox."
        ),
        "claim_boundary": (
            "V7.8 is evidence and infrastructure progress, not a final proven trading system. The only inherited "
            "capital-usable component remains the V6.6 broad-US-equity monthly SMA10 exposure cap."
        ),
        "inherited_v77": inherited,
    }


def validate_runtime_desk(desk: dict[str, Any]) -> dict[str, Any]:
    base = validate_runtime_v77(desk)
    failures = list(base.get("failures") or [])
    contract = desk.get("release_contract_v78") or release_contract()
    if contract.get("status") != "PROOF_EXPANSION_CHECKPOINT_NOT_FINAL_TRADING_SYSTEM":
        failures.append("V7.8 checkpoint status mismatch")
    if contract.get("final_trading_system") is not False:
        failures.append("V7.8 must not claim final trading-system status")
    if contract.get("new_decision_active_components") != 0:
        failures.append("unproven V7.8 component became decision-active")
    if contract.get("global_ticker_capital_permission") != "BLOCKED":
        failures.append("ticker capital permission escaped the proof gate")
    return {
        "schema": "warroom.runtime_validation.v78",
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "inherited_v77_status": base.get("status"),
        "final_trading_system": False,
        "ticker_capital_permission": "BLOCKED",
    }
