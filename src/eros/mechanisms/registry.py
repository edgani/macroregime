"""Economic mechanism registry contracts."""

import math
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


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

    @field_validator("sign", mode="before")
    @classmethod
    def reject_boolean_sign(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("mechanism sign cannot be boolean")
        return value

    @field_validator("elasticity_estimate", mode="before")
    @classmethod
    def reject_boolean_elasticity(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("mechanism elasticity cannot be boolean")
        return value

    @field_validator("expected_lag_distribution", mode="before")
    @classmethod
    def reject_boolean_lags(cls, value: object) -> object:
        if isinstance(value, dict) and any(
            isinstance(lag, bool) for lag in value.values()
        ):
            raise ValueError("mechanism lag values cannot be boolean")
        return value

    @field_validator("confidence_interval", mode="before")
    @classmethod
    def reject_boolean_interval(cls, value: object) -> object:
        if isinstance(value, (tuple, list)) and any(
            isinstance(bound, bool) for bound in value
        ):
            raise ValueError("mechanism confidence bounds cannot be boolean")
        return value

    @model_validator(mode="after")
    def require_lineage_for_validated_edge(self) -> "MechanismEdge":
        if any(
            not value.strip()
            for value in (
                self.source_entity,
                self.target_entity,
                self.relationship_type,
                self.mechanism_id,
            )
        ):
            raise ValueError("mechanism identity fields must be nonblank")
        numeric_values = [*self.expected_lag_distribution.values()]
        if self.elasticity_estimate is not None:
            numeric_values.append(self.elasticity_estimate)
        if self.confidence_interval is not None:
            numeric_values.extend(self.confidence_interval)
        if any(not math.isfinite(value) for value in numeric_values):
            raise ValueError("mechanism numeric estimates must be finite")
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
