"""Narrative-to-evidence permission firewall."""
from enum import StrEnum
from pydantic import BaseModel, Field


class SourceType(StrEnum):
    OBSERVED_OPERATION = "observed_operation"
    OFFICIAL_PRIMARY = "official_primary"
    EXCHANGE_OR_FILING = "exchange_or_filing"
    NAMED_WIRE = "named_wire"
    PEER_REVIEWED = "peer_reviewed"
    RESEARCH_NOTE = "research_note"
    JOURNALIST_INTERPRETATION = "journalist_interpretation"
    SOCIAL_MEDIA = "social_media"
    ANONYMOUS = "anonymous"


class ClaimClass(StrEnum):
    FACT = "fact"
    CAUSAL = "causal"
    FORECAST = "forecast"
    ATTRIBUTION = "attribution"
    CONSPIRACY = "conspiracy"
    OPINION = "opinion"


class Claim(BaseModel):
    claim_id: str
    source_id: str
    source_type: SourceType
    claim_text: str
    claim_class: ClaimClass
    original_source_chain: list[str] = Field(default_factory=list)
    testable_predictions: list[str] = Field(default_factory=list)


class ClaimAssessment(BaseModel):
    verification_status: str
    decision_permission: str
    material_probability_update_allowed: bool
    rationale: str


def assess_claim(claim: Claim) -> ClaimAssessment:
    if not claim.testable_predictions:
        return ClaimAssessment(verification_status="UNTESTABLE_ARCHIVE", decision_permission="blocked", material_probability_update_allowed=False, rationale="No falsifiable prediction.")
    if claim.source_type in {SourceType.SOCIAL_MEDIA, SourceType.ANONYMOUS}:
        return ClaimAssessment(verification_status="RESEARCH_TICKET", decision_permission="research_only", material_probability_update_allowed=False, rationale="Narrative source requires independent primary evidence.")
    if claim.source_type in {SourceType.JOURNALIST_INTERPRETATION, SourceType.RESEARCH_NOTE}:
        return ClaimAssessment(verification_status="CONTEXT_PENDING", decision_permission="context_only", material_probability_update_allowed=False, rationale="Interpretation may guide research but not allocation.")
    return ClaimAssessment(verification_status="VERIFICATION_REQUIRED", decision_permission="eligible", material_probability_update_allowed=True, rationale="Primary-class source is eligible after verification and independence checks.")
