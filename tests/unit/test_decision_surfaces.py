"""Behavioral tests for state-derived decision surfaces."""

from eros.app.command_center import _command_center_qualified_packets
from eros.app.opportunity_engine import _decision_contract_rows, _horizon_rows
from eros.app.portfolio import _scenario_rows, _tripwire_rows
from eros.app.state import ExecutionState, load_dashboard_state


def test_opportunity_rows_follow_qualified_packet_and_execution_state() -> None:
    base = load_dashboard_state()
    empty_rows = _horizon_rows(base)
    assert {row["Permission"] for row in empty_rows} == {"WAIT / RESEARCH ONLY"}

    qualified = base.model_copy(
        update={
            "qualified_opportunities": [
                {
                    "decision": "ENTER",
                    "sizing": "2% NAV",
                    "holding_horizon": "1-3 months",
                    "entry_trigger": "Verified trigger",
                    "invalidation": "Verified invalidation",
                    "valuation_basis": "Point-in-time fundamental target",
                    "alternative_action": "Hold cash",
                }
            ],
            "execution": ExecutionState(
                permission="HUMAN_REVIEW",
                human_approval_required=True,
                reason="Qualified packet awaits approval.",
            ),
        }
    )

    horizon_rows = _horizon_rows(qualified)
    assert {row["Permission"] for row in horizon_rows} == {"HUMAN_REVIEW"}
    assert all("qualified packet exists" in str(row["Reason"]).lower() for row in horizon_rows)
    contract = {row["Field"]: row["Current value"] for row in _decision_contract_rows(qualified)}
    assert contract["Decision"] == "ENTER"
    assert contract["Sizing"] == "2% NAV"
    assert contract["Holding horizon"] == "1-3 months"
    assert contract["Valuation / target basis"] == "Point-in-time fundamental target"


def test_portfolio_tripwires_follow_positions_scenarios_and_permission() -> None:
    base = load_dashboard_state()
    empty = {row["Tripwire"]: row["Status"] for row in _tripwire_rows(base)}
    assert empty["Private holdings loaded"] == "FAIL"
    assert empty["Qualified opportunity packet"] == "FAIL"
    assert empty["Execution permission"] == "LOCKED"

    ready = base.model_copy(
        update={
            "portfolio_positions": [
                {
                    "instrument": "TEST",
                    "quantity": 1,
                    "cost_basis": 100,
                    "currency": "USD",
                    "asset_class": "equities",
                    "country": "United States",
                    "account": "taxable",
                    "tax_treatment": "configured",
                    "days_to_exit": 1,
                }
            ],
            "qualified_opportunities": [
                {
                    "decision": "ENTER",
                    "sizing": "2% NAV",
                    "holding_horizon": "1-3 months",
                    "entry_trigger": "Verified trigger",
                    "invalidation": "Verified invalidation",
                    "valuation_basis": "Point-in-time target",
                    "alternative_action": "Hold cash",
                }
            ],
            "scenarios": [
                {"scenario": "Base", "probability": "0.50", "portfolio_impact": "-1%"}
            ],
            "execution": ExecutionState(
                permission="APPROVED",
                human_approval_required=False,
                reason="Approved test state.",
            ),
        }
    )
    tripwires = {row["Tripwire"]: row["Status"] for row in _tripwire_rows(ready)}

    assert tripwires["Private holdings loaded"] == "PASS"
    assert tripwires["Qualified opportunity packet"] == "PASS"
    assert tripwires["Scenario mechanism validated"] == "PASS"
    assert tripwires["Liquidity, tax, and access complete"] == "PASS"
    assert tripwires["Execution permission"] == "APPROVED"
    assert tripwires["Human approval"] == "NOT_REQUIRED"
    assert {row["Permission"] for row in _scenario_rows(ready)} == {
        "APPROVED FOR EXPLICIT REVIEW"
    }


def test_malformed_decision_state_never_promotes_permissions() -> None:
    base = load_dashboard_state()
    malformed = base.model_copy(
        update={
            "portfolio_positions": [
                {
                    "instrument": " ",
                    "quantity": True,
                    "cost_basis": float("nan"),
                    "currency": "",
                    "asset_class": "equities",
                    "country": "United States",
                    "account": "taxable",
                    "tax_treatment": "configured",
                    "days_to_exit": -1,
                }
            ],
            "qualified_opportunities": [{}],
            "scenarios": [
                {"scenario": "Base", "probability": "", "portfolio_impact": "not numeric"}
            ],
            "execution": ExecutionState(
                permission="APPROVED",
                human_approval_required=False,
                reason="Malformed test state.",
            ),
        }
    )

    horizons = _horizon_rows(malformed)
    assert {row["Permission"] for row in horizons} == {"WAIT / RESEARCH ONLY"}
    assert {row["Qualified packets"] for row in horizons} == {0}
    decision = {
        row["Field"]: row["Current value"]
        for row in _decision_contract_rows(malformed)
    }
    assert decision["Decision"] == "WAIT / RESEARCH ONLY"
    tripwires = {row["Tripwire"]: row["Status"] for row in _tripwire_rows(malformed)}
    assert tripwires["Private holdings loaded"] == "FAIL"
    assert tripwires["Qualified opportunity packet"] == "FAIL"
    assert tripwires["Scenario mechanism validated"] == "FAIL"
    assert tripwires["Liquidity, tax, and access complete"] == "FAIL"
    assert {row["Permission"] for row in _scenario_rows(malformed)} == {"NO REBALANCE"}
    assert _command_center_qualified_packets(malformed) == []


def test_boolean_scenario_probability_never_promotes_permissions() -> None:
    base = load_dashboard_state()
    malformed = base.model_copy(
        update={
            "portfolio_positions": [
                {
                    "instrument": "TEST",
                    "quantity": 1,
                    "cost_basis": 100,
                    "currency": "USD",
                    "asset_class": "equities",
                    "country": "United States",
                    "account": "taxable",
                    "tax_treatment": "configured",
                    "days_to_exit": 1,
                }
            ],
            "qualified_opportunities": [
                {
                    "decision": "ENTER",
                    "sizing": "2% NAV",
                    "holding_horizon": "1-3 months",
                    "entry_trigger": "Verified trigger",
                    "invalidation": "Verified invalidation",
                    "valuation_basis": "Point-in-time target",
                    "alternative_action": "Hold cash",
                }
            ],
            "scenarios": [
                {"scenario": "Base", "probability": True, "portfolio_impact": "-1%"}
            ],
            "execution": ExecutionState(
                permission="APPROVED",
                human_approval_required=False,
                reason="Malformed scenario test.",
            ),
        }
    )

    tripwires = {row["Tripwire"]: row["Status"] for row in _tripwire_rows(malformed)}
    assert tripwires["Scenario mechanism validated"] == "FAIL"
    assert {row["Permission"] for row in _scenario_rows(malformed)} == {"NO REBALANCE"}


def test_missing_or_wrong_type_scenario_fields_fail_closed_without_exception() -> None:
    base = load_dashboard_state()
    malformed = base.model_copy(
        update={
            "scenarios": [
                {},
                {"scenario": "Bad", "probability": "0.5", "portfolio_impact": True},
            ]
        }
    )

    rows = _scenario_rows(malformed)

    assert rows
    assert {row["Permission"] for row in rows} == {"NO REBALANCE"}
    assert any(row["Scenario"] == "UNKNOWN" for row in rows)
    assert any(row["Portfolio impact"] == "UNKNOWN" for row in rows)
