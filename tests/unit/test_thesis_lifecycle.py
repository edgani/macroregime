import pytest

from eros.thesis.resolution import ThesisStatus, transition_thesis


def test_allowed_transition_is_audited() -> None:
    change = transition_thesis(
        "TH-20260802-0001",
        ThesisStatus.OBSERVATION,
        ThesisStatus.PLAUSIBLE,
        "Distinct predictions documented.",
        "EV-1",
    )
    assert (change.before, change.after, change.evidence_id) == (
        ThesisStatus.OBSERVATION,
        ThesisStatus.PLAUSIBLE,
        "EV-1",
    )


def test_universal_proven_status_does_not_exist() -> None:
    with pytest.raises(ValueError):
        ThesisStatus("PROVEN_UNIVERSAL")


def test_skipping_validation_stages_fails_closed() -> None:
    with pytest.raises(ValueError, match="invalid thesis transition"):
        transition_thesis(
            "TH-1", ThesisStatus.PLAUSIBLE, ThesisStatus.PROVEN_SCOPE_LIMITED, "Unsupported", "EV-2"
        )
