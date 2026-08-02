import pytest

from eros.mechanisms.registry import EvidenceStatus, MechanismEdge


def test_validated_edge_requires_experiment_lineage() -> None:
    with pytest.raises(ValueError, match="experiment lineage"):
        MechanismEdge(
            source_entity="oil supply",
            target_entity="freight rates",
            relationship_type="raises",
            mechanism_id="MECH-1",
            evidence_status=EvidenceStatus.PROVEN_SCOPE_LIMITED,
        )


def test_candidate_edge_is_dashed() -> None:
    edge = MechanismEdge(
        source_entity="oil supply",
        target_entity="freight rates",
        relationship_type="raises",
        mechanism_id="MECH-1",
        evidence_status=EvidenceStatus.CANDIDATE,
    )
    assert edge.visual_style == "dashed"
