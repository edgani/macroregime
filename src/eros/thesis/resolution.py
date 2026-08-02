"""Audited thesis lifecycle transitions."""

from enum import StrEnum

from pydantic import BaseModel


class ThesisStatus(StrEnum):
    IDEA = "IDEA"
    OBSERVATION = "OBSERVATION"
    PLAUSIBLE = "PLAUSIBLE"
    TESTABLE_THESIS = "TESTABLE_THESIS"
    HISTORICALLY_SUPPORTED = "HISTORICALLY_SUPPORTED"
    CONDITIONAL = "CONDITIONAL"
    PROSPECTIVE_PENDING = "PROSPECTIVE_PENDING"
    REPLICATED_OOS = "REPLICATED_OOS"
    PROVEN_SCOPE_LIMITED = "PROVEN_SCOPE_LIMITED"
    WEAKENING = "WEAKENING"
    BUSTED = "BUSTED"
    ARCHIVED = "ARCHIVED"


_FORWARD = {
    ThesisStatus.IDEA: {ThesisStatus.OBSERVATION, ThesisStatus.ARCHIVED},
    ThesisStatus.OBSERVATION: {ThesisStatus.PLAUSIBLE, ThesisStatus.BUSTED, ThesisStatus.ARCHIVED},
    ThesisStatus.PLAUSIBLE: {
        ThesisStatus.TESTABLE_THESIS,
        ThesisStatus.BUSTED,
        ThesisStatus.ARCHIVED,
    },
    ThesisStatus.TESTABLE_THESIS: {ThesisStatus.HISTORICALLY_SUPPORTED, ThesisStatus.BUSTED},
    ThesisStatus.HISTORICALLY_SUPPORTED: {ThesisStatus.CONDITIONAL, ThesisStatus.WEAKENING},
    ThesisStatus.CONDITIONAL: {ThesisStatus.PROSPECTIVE_PENDING, ThesisStatus.WEAKENING},
    ThesisStatus.PROSPECTIVE_PENDING: {ThesisStatus.REPLICATED_OOS, ThesisStatus.WEAKENING},
    ThesisStatus.REPLICATED_OOS: {ThesisStatus.PROVEN_SCOPE_LIMITED, ThesisStatus.WEAKENING},
    ThesisStatus.PROVEN_SCOPE_LIMITED: {ThesisStatus.WEAKENING},
    ThesisStatus.WEAKENING: {ThesisStatus.BUSTED, ThesisStatus.ARCHIVED},
    ThesisStatus.BUSTED: {ThesisStatus.ARCHIVED},
    ThesisStatus.ARCHIVED: set(),
}


class ThesisChange(BaseModel):
    thesis_id: str
    before: ThesisStatus
    after: ThesisStatus
    rationale: str
    evidence_id: str


def transition_thesis(
    thesis_id: str, current: ThesisStatus, target: ThesisStatus, rationale: str, evidence_id: str
) -> ThesisChange:
    if target not in _FORWARD[current]:
        raise ValueError(f"invalid thesis transition: {current} -> {target}")
    return ThesisChange(
        thesis_id=thesis_id,
        before=current,
        after=target,
        rationale=rationale,
        evidence_id=evidence_id,
    )
