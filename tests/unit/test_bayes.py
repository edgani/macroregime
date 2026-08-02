from eros.thesis.bayes import EvidenceUpdate, update_probability


def test_correlated_evidence_is_cluster_discounted() -> None:
    correlated = update_probability(
        0.40,
        [EvidenceUpdate("E1", 2.0, 1.0, 1.0, "wire"), EvidenceUpdate("E2", 2.0, 1.0, 1.0, "wire")],
    )
    independent = update_probability(
        0.40,
        [
            EvidenceUpdate("E1", 2.0, 1.0, 1.0, "wire-a"),
            EvidenceUpdate("E2", 2.0, 1.0, 1.0, "wire-b"),
        ],
    )
    assert 0.40 < correlated.posterior_probability < independent.posterior_probability
    assert correlated.cluster_count == 1


def test_missing_evidence_penalty_reduces_posterior() -> None:
    assert (
        update_probability(0.5, [], 0.3).posterior_probability
        < update_probability(0.5, [], 0.0).posterior_probability
    )
