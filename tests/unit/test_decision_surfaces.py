"""Behavioral tests for state-derived decision surfaces."""

from datetime import UTC, datetime

import pytest
from packet_factory import qualified_packet as _qualified_packet

from eros.app import state as state_module
from eros.app.command_center import _command_center_qualified_packets
from eros.app.opportunity_engine import (
    _decision_contract_rows,
    _horizon_rows,
    _qualification_root_cause_rows,
)
from eros.app.portfolio import _scenario_rows, _tripwire_rows
from eros.app.state import ExecutionState, load_dashboard_state
from eros.opportunity.packet import validate_qualified_packet


def _complete_position() -> dict[str, object]:
    return {
        "instrument": "TEST",
        "quantity": 1.0,
        "cost_basis": 95.0,
        "current_price": 100.0,
        "market_value": 100.0,
        "currency": "USD",
        "asset_class": "equities",
        "country": "United States",
        "account": "taxable",
        "tax_treatment": "configured",
        "tax_rate_pct": 15.0,
        "days_to_exit": 1.0,
        "spread_bps": 5.0,
        "estimated_slippage_bps": 3.0,
        "broker_access": True,
        "settlement_days": 2,
        "capacity_usd": 10_000.0,
        "factor_exposures": {"growth": 1.0},
        "position_snapshot_id": "POSITION-SNAPSHOT-TEST-1",
        "valuation_source_id": "VALUATION-SOURCE-TEST-1",
        "liquidity_source_id": "LIQUIDITY-SOURCE-TEST-1",
        "risk_model_id": "RISK-MODEL-TEST-1",
        "decision_snapshot_id": "DEC-TEST-1",
        "price_observed_at": "2026-08-03T05:00:00Z",
        "borrow_available": False,
        "borrow_rate_pct": 0.0,
    }


def _validated_scenario(probability: object = 0.50) -> dict[str, object]:
    return {
        "scenario_id": "SCENARIO-TEST-1",
        "scenario": "Growth shock",
        "probability": probability,
        "portfolio_impact_pct": -1.0,
        "mechanism_id": "MECH-TEST-1",
        "evidence_status": "REPLICATED_OOS",
        "triggers": ["Official growth release crosses the validated threshold"],
        "factor_shocks": {"growth": -0.01},
        "decision_snapshot_id": "DEC-TEST-1",
    }


def _approved_execution(reason: str) -> ExecutionState:
    return ExecutionState(
        permission="APPROVED",
        human_approval_required=False,
        reason=reason,
        approval_id="APPROVAL-TEST-1",
        approved_by="test-human-reviewer",
        approved_at=datetime(2026, 8, 3, 10, 5, tzinfo=UTC),
        approval_method="SIGNED_ATTESTATION",
        approval_evidence_checksum="a" * 64,
    )


def test_approved_execution_requires_auditable_human_approval() -> None:
    with pytest.raises(ValueError, match="approval"):
        ExecutionState(
            permission="APPROVED",
            human_approval_required=False,
            reason="Unaudited approval.",
        )


def test_execution_enabled_requires_human_approval_to_be_cleared() -> None:
    base = load_dashboard_state()
    inconsistent = base.model_copy(
        update={
            "execution": ExecutionState.model_construct(
                permission="APPROVED",
                human_approval_required=True,
                reason="Approval flag remains open.",
            )
        }
    )

    assert inconsistent.execution_enabled is False


def test_execution_enabled_requires_anti_contamination_policy_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = load_dashboard_state()
    approved_but_contaminated = base.model_copy(
        update={"execution": _approved_execution("Human approved the exact snapshot.")}
    )

    assert approved_but_contaminated.execution_enabled is False

    monkeypatch.setattr(state_module, "_contamination_policy_ready", lambda: True)

    assert approved_but_contaminated.execution_enabled is True


def test_ui_complete_packet_without_research_lineage_is_not_qualified() -> None:
    base = load_dashboard_state()
    presentation_only = base.model_copy(
        update={
            "qualified_opportunities": [
                {
                    "decision": "ENTER",
                    "sizing": "2% NAV",
                    "holding_horizon": "1-3 months",
                    "entry_trigger": "Price crossed a watched level",
                    "invalidation": "Price crossed back",
                    "valuation_basis": "Unverified target",
                    "alternative_action": "Hold cash",
                }
            ]
        }
    )

    assert _command_center_qualified_packets(presentation_only) == []
    assert {row["Qualified packets"] for row in _horizon_rows(presentation_only)} == {0}


def test_qualified_packet_requires_full_lineage_and_recomputed_ev() -> None:
    for missing_field in (
        "model_id",
        "experiment_id",
        "data_snapshot_id",
        "evidence_ids",
    ):
        packet = _qualified_packet()
        packet.pop(missing_field)
        with pytest.raises(ValueError):
            validate_qualified_packet(packet)

    tampered = _qualified_packet()
    expected_value = tampered["expected_value"]
    assert isinstance(expected_value, dict)
    expected_value["gross_ev"] = 0.09
    with pytest.raises(ValueError, match="deterministic recomputation"):
        validate_qualified_packet(tampered)


def test_zero_qualified_root_cause_ledger_names_unbuilt_runtime_components() -> None:
    rows = {
        row["Component"]: row for row in _qualification_root_cause_rows(load_dashboard_state())
    }

    assert rows["Point-in-time causal feature panel"]["Status"] == "NOT_IMPLEMENTED"
    assert rows["Global candidate generator"]["Status"] == "NOT_IMPLEMENTED"
    assert rows["Global conservative-EV ranker"]["Status"] == "NOT_RUN"
    assert rows["Candidate admission"]["Status"] == "0 QUALIFIED"
    assert rows["Private portfolio contract"]["Status"] == "MISSING"
    assert rows["Execution approval verifier"]["Status"] == "SCHEMA_ONLY"


def test_opportunity_rows_follow_qualified_packet_and_execution_state() -> None:
    base = load_dashboard_state()
    empty_rows = _horizon_rows(base)
    assert {row["Permission"] for row in empty_rows} == {"WAIT / RESEARCH ONLY"}

    qualified = base.model_copy(
        update={
            "qualified_opportunities": [_qualified_packet()],
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


def test_formatted_portfolio_inputs_without_lineage_do_not_pass_readiness() -> None:
    base = load_dashboard_state()
    presentation_only = base.model_copy(
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
            "qualified_opportunities": [_qualified_packet()],
            "scenarios": [
                {"scenario": "Base", "probability": "0.50", "portfolio_impact": "-1%"}
            ],
            "execution": _approved_execution("Presentation-only test state."),
        }
    )

    tripwires = {
        row["Tripwire"]: row["Status"] for row in _tripwire_rows(presentation_only)
    }
    assert tripwires["Private holdings loaded"] == "PASS"
    assert tripwires["Scenario mechanism validated"] == "FAIL"
    assert tripwires["Liquidity, tax, and access complete"] == "FAIL"
    assert {row["Permission"] for row in _scenario_rows(presentation_only)} == {
        "NO REBALANCE"
    }


def test_future_or_missing_position_source_lineage_blocks_portfolio() -> None:
    base = load_dashboard_state()
    future_position = _complete_position()
    future_position["price_observed_at"] = "2999-01-01T00:00:00Z"
    future_position.pop("risk_model_id")
    state = base.model_copy(update={"portfolio_positions": [future_position]})

    tripwires = {row["Tripwire"]: row["Status"] for row in _tripwire_rows(state)}

    assert tripwires["Liquidity, tax, and access complete"] == "FAIL"


def test_portfolio_tripwires_follow_positions_scenarios_and_permission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = load_dashboard_state()
    empty = {row["Tripwire"]: row["Status"] for row in _tripwire_rows(base)}
    assert empty["Private holdings loaded"] == "FAIL"
    assert empty["Qualified opportunity packet"] == "FAIL"
    assert empty["Execution permission"] == "LOCKED"

    ready = base.model_copy(
        update={
            "portfolio_positions": [_complete_position()],
            "qualified_opportunities": [_qualified_packet()],
            "scenarios": [_validated_scenario()],
            "execution": _approved_execution("Approved test state."),
        }
    )
    monkeypatch.setattr(state_module, "_contamination_policy_ready", lambda: True)
    tripwires = {row["Tripwire"]: row["Status"] for row in _tripwire_rows(ready)}

    assert tripwires["Private holdings loaded"] == "PASS"
    assert tripwires["Qualified opportunity packet"] == "PASS"
    assert tripwires["Scenario mechanism validated"] == "PASS"
    assert tripwires["Liquidity, tax, and access complete"] == "PASS"
    assert tripwires["Execution permission"] == "APPROVED"
    assert tripwires["Anti-contamination policy"] == "PASS"
    assert tripwires["Human approval"] == "NOT_REQUIRED"
    assert {row["Permission"] for row in _scenario_rows(ready)} == {
        "APPROVED FOR EXPLICIT REVIEW"
    }


def test_approved_metadata_stays_locked_when_contamination_policy_blocks() -> None:
    base = load_dashboard_state()
    blocked = base.model_copy(
        update={
            "portfolio_positions": [_complete_position()],
            "qualified_opportunities": [_qualified_packet()],
            "scenarios": [_validated_scenario()],
            "execution": _approved_execution("Policy-blocked state."),
        }
    )

    tripwires = {row["Tripwire"]: row["Status"] for row in _tripwire_rows(blocked)}

    assert tripwires["Execution permission"] == "LOCKED"
    assert tripwires["Anti-contamination policy"] == "FAIL"
    assert {row["Permission"] for row in _scenario_rows(blocked)} == {"NO REBALANCE"}
    assert {row["Permission"] for row in _horizon_rows(blocked)} == {
        "WAIT / RESEARCH ONLY"
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
            "execution": _approved_execution("Malformed test state."),
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
            "portfolio_positions": [_complete_position()],
            "qualified_opportunities": [_qualified_packet()],
            "scenarios": [_validated_scenario(probability=True)],
            "execution": _approved_execution("Malformed scenario test."),
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
