"""War Room OS V7.9 exact-scope final trading-system contract."""
from __future__ import annotations
from typing import Any

from release_contract_v78 import release_contract as release_contract_v78

RELEASE_ID = "WAR_ROOM_OS_V79_FINAL_PROVEN_CORE"
RELEASE_LABEL = "War Room OS V7.9 Final Proven Core"
RELEASE_DATE = "2026-07-26"
SYSTEM_ID = "US_BROAD_EQUITY_SMA10_LONG_CASH_V79"


def release_contract() -> dict[str, Any]:
    inherited = release_contract_v78()
    return {
        "schema": "warroom.release_contract.v79",
        "release_id": RELEASE_ID,
        "release_label": RELEASE_LABEL,
        "release_date": RELEASE_DATE,
        "status": "FINAL_PROVEN_READY_TO_TRADE_EXACT_SCOPE",
        "final_trading_system": True,
        "final_scope": "One dedicated broad-US-equity long/cash sleeve, evaluated only at completed monthly rebalances.",
        "system_id": SYSTEM_ID,
        "decision_active_systems": [SYSTEM_ID],
        "decision_active_ticker_selectors": 0,
        "decision_active_cross_market_directional_components": 0,
        "allowed_execution_instruments": ["SPY", "VOO", "IVV"],
        "defensive_instrument": "CASH",
        "leverage_permission": False,
        "short_permission": False,
        "intramonth_override_permission": False,
        "other_market_permission": "NO_TRADE_RESEARCH_ONLY",
        "proof_claim": "Historically confirmed reduction of broad-US-equity drawdown and left-tail severity under the frozen monthly long/cash rule and tested cost assumptions.",
        "not_proven": [
            "future profitability guarantee",
            "advance crash-date prediction",
            "individual ticker selection",
            "entry target or stop forecasting",
            "IHSG, FX, commodity or crypto direction",
            "accumulation or topping prediction as a capital signal",
        ],
        "live_data_policy": "Completed-month S&P 500 closes require live FRED + Yahoo-distributed agreement. Bundled or manual data is audit-only. Any missing, stale, or mismatched source produces NO TRADE.",
        "user_authorization_policy": "The user must explicitly authorize and size the dedicated strategy sleeve before the system may create broad-equity exposure.",
        "inherited_checkpoint": inherited.get("release_id"),
    }


def validate_runtime_desk(desk: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    contract = desk.get("release_contract_v79") or release_contract()
    evidence = desk.get("research_evidence_v79") or {}
    if contract.get("status") != "FINAL_PROVEN_READY_TO_TRADE_EXACT_SCOPE":
        failures.append("V7.9 final exact-scope status mismatch")
    if contract.get("final_trading_system") is not True:
        failures.append("V7.9 final trading-system flag missing")
    if contract.get("decision_active_systems") != [SYSTEM_ID]:
        failures.append("unexpected decision-active system set")
    if contract.get("decision_active_ticker_selectors") != 0:
        failures.append("ticker selector escaped the proof boundary")
    if contract.get("decision_active_cross_market_directional_components") != 0:
        failures.append("cross-market directional component escaped the proof boundary")
    if evidence and evidence.get("system_id") != SYSTEM_ID:
        failures.append("runtime evidence system id mismatch")
    instruction = (evidence.get("current_instruction") or {}) if isinstance(evidence, dict) else {}
    if instruction:
        if instruction.get("ticker_selection_permission") is not False:
            failures.append("ticker-selection permission escaped")
        if instruction.get("short_permission") is not False:
            failures.append("short permission escaped")
        if instruction.get("leverage_permission") is not False:
            failures.append("leverage permission escaped")
    return {
        "schema": "warroom.runtime_validation.v79",
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "final_trading_system": True,
        "scope": contract.get("final_scope"),
        "system_id": SYSTEM_ID,
    }
