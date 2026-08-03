"""Safety contracts for research utilities that are not yet wired into runtime."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from eros.allocation.conflicts import resolve_conflict
from eros.allocation.waiting import compare_waiting
from eros.app.state import Catalyst
from eros.mechanisms.registry import EvidenceStatus, MechanismEdge
from eros.ontology.entities import Entity, EntityType
from eros.ontology.graph import EconomicGraph
from eros.opportunity.ev import CostBreakdown, ExpectedValueInput, ExpectedValueResult
from eros.portfolio.exposures import PositionExposure
from eros.portfolio.scenarios import Scenario
from eros.registries.schemas import RecordMetadata
from eros.research.experiments import ExperimentResult
from eros.thesis.discovery import ThesisCandidate


def test_waiting_and_conflict_reject_nonfinite_boolean_or_out_of_domain_inputs() -> None:
    with pytest.raises(ValueError):
        compare_waiting(float("nan"), 0.1, 0.0, 0.02)
    with pytest.raises(ValueError):
        compare_waiting(True, 0.1, 0.0, 0.02)
    with pytest.raises(ValueError):
        resolve_conflict({"macro": 2})
    with pytest.raises(ValueError):
        resolve_conflict({"macro": True})


def test_exposure_scenario_and_thesis_reject_boolean_or_nonfinite_numbers() -> None:
    with pytest.raises(ValueError):
        PositionExposure(instrument="SPY", weight=True, factors={"growth": 1.0})
    with pytest.raises(ValueError):
        PositionExposure(instrument="SPY", weight=1.0, factors={"growth": float("inf")})
    with pytest.raises(ValueError):
        PositionExposure(instrument="SPY", weight=1.0, factors={"growth": True})
    with pytest.raises(ValueError):
        Scenario(
            scenario_id="SCENARIO-1",
            name="Shock",
            probability=True,
            triggers=["release"],
            factor_shocks={"growth": -0.1},
        )
    with pytest.raises(ValueError):
        Scenario(
            scenario_id="SCENARIO-1",
            name="Shock",
            probability=0.5,
            triggers=["release"],
            factor_shocks={"growth": True},
        )
    with pytest.raises(ValueError):
        ThesisCandidate(
            thesis_id="TH-1",
            thesis_type="null",
            claim="No effect",
            distinct_prediction="No response",
            prior_probability=True,
        )


def test_ontology_rejects_blank_entity_and_edges_without_registered_endpoints() -> None:
    with pytest.raises(ValueError):
        Entity(entity_id=" ", name="Blank", entity_type=EntityType.ACTOR)

    graph = EconomicGraph()
    graph.add_entity(Entity(entity_id="ENTITY-1", name="Source", entity_type=EntityType.ACTOR))
    edge = MechanismEdge(
        source_entity="ENTITY-1",
        target_entity="ENTITY-MISSING",
        relationship_type="affects",
        mechanism_id="MECH-1",
        evidence_status=EvidenceStatus.CANDIDATE,
    )
    with pytest.raises(ValueError, match="endpoint"):
        graph.add_mechanism_edge(edge)


def test_registry_chronology_and_experiment_metrics_fail_closed() -> None:
    with pytest.raises(ValueError):
        RecordMetadata(
            created_at=datetime(2026, 8, 3, tzinfo=UTC),
            effective_at=datetime(2026, 8, 2, tzinfo=UTC),
            available_at=datetime(2026, 8, 1, tzinfo=UTC),
            version="1",
            source_id="SOURCE-1",
            code_hash="a" * 64,
            lineage_id="LINEAGE-1",
        )
    with pytest.raises(ValueError):
        ExperimentResult(
            experiment_id="EXP-1",
            metrics={"sharpe": float("nan")},
            limitations=[],
            verdict="FAIL",
            replication_status="NOT_RUN",
        )
    with pytest.raises(ValueError):
        ExperimentResult(
            experiment_id="EXP-1",
            metrics={"sharpe": True},
            limitations=[],
            verdict="FAIL",
            replication_status="NOT_RUN",
        )
    with pytest.raises(ValidationError):
        Catalyst(date="2026-99-99", event="Release", decision="Wait", status="PENDING")


def test_expected_value_contracts_reject_boolean_and_nonfinite_values() -> None:
    with pytest.raises(ValueError):
        CostBreakdown(transaction=True)
    with pytest.raises(ValueError):
        ExpectedValueInput(
            probability_win=True,
            expected_win=0.2,
            expected_loss=-0.1,
            costs=CostBreakdown(),
        )
    with pytest.raises(ValueError):
        ExpectedValueResult(
            gross_ev=float("nan"),
            total_cost=0.0,
            net_ev=0.0,
            conservative_ev=0.0,
        )


def test_validated_mechanism_rejects_boolean_sign_and_nonfinite_estimates() -> None:
    with pytest.raises(ValueError):
        MechanismEdge(
            source_entity="ENTITY-1",
            target_entity="ENTITY-2",
            relationship_type="affects",
            mechanism_id="MECH-1",
            sign=True,
            evidence_status=EvidenceStatus.CANDIDATE,
        )
    with pytest.raises(ValueError):
        MechanismEdge(
            source_entity="ENTITY-1",
            target_entity="ENTITY-2",
            relationship_type="affects",
            mechanism_id="MECH-1",
            elasticity_estimate=float("inf"),
            evidence_status=EvidenceStatus.CANDIDATE,
        )
    with pytest.raises(ValueError):
        MechanismEdge(
            source_entity="ENTITY-1",
            target_entity="ENTITY-2",
            relationship_type="affects",
            mechanism_id="MECH-1",
            elasticity_estimate=True,
            evidence_status=EvidenceStatus.CANDIDATE,
        )
    with pytest.raises(ValueError):
        MechanismEdge(
            source_entity="ENTITY-1",
            target_entity="ENTITY-2",
            relationship_type="affects",
            mechanism_id="MECH-1",
            expected_lag_distribution={"1d": True},
            evidence_status=EvidenceStatus.CANDIDATE,
        )
    with pytest.raises(ValueError):
        MechanismEdge(
            source_entity="ENTITY-1",
            target_entity="ENTITY-2",
            relationship_type="affects",
            mechanism_id="MECH-1",
            confidence_interval=(False, 1.0),
            evidence_status=EvidenceStatus.CANDIDATE,
        )
