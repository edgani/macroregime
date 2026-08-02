"""Economic mechanism registry contracts."""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class EvidenceStatus(StrEnum):
    PROVEN_SCOPE_LIMITED = "PROVEN_SCOPE_LIMITED"
    REPLICATED_OOS = "REPLICATED_OOS"
    CONDITIONAL = "CONDITIONAL"
    CONTEXT = "CONTEXT"
    CANDIDATE = "CANDIDATE"
    WATCHLIST = "WATCHLIST"
    BUSTED_AS_TESTED = "BUSTED_AS_TESTED"
    DATA_DEBT = "DATA_DEBT"
    UNTESTED = "UNTESTED"


class MechanismEdge(BaseModel):
    source_entity: str
    target_entity: str
    relationship_type: str
    mechanism_id: str
    sign: int | None = Field(default=None, ge=-1, le=1)
    expected_lag_distribution: dict[str, float] = Field(default_factory=dict)
    elasticity_estimate: float | None = None
    regime_validity: list[str] = Field(default_factory=list)
    country_validity: list[str] = Field(default_factory=list)
    evidence_status: EvidenceStatus
    confidence_interval: tuple[float, float] | None = None
    experiment_ids: list[str] = Field(default_factory=list)
    counterexamples: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_lineage_for_validated_edge(self) -> "MechanismEdge":
        if (
            self.evidence_status
            in {EvidenceStatus.PROVEN_SCOPE_LIMITED, EvidenceStatus.REPLICATED_OOS}
            and not self.experiment_ids
        ):
            raise ValueError("validated edge requires experiment lineage")
        return self

    @property
    def visual_style(self) -> str:
        return {
            EvidenceStatus.PROVEN_SCOPE_LIMITED: "solid",
            EvidenceStatus.REPLICATED_OOS: "solid",
            EvidenceStatus.CANDIDATE: "dashed",
            EvidenceStatus.BUSTED_AS_TESTED: "red-crossed",
        }.get(self.evidence_status, "grey")
