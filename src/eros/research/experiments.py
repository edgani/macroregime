"""Pre-registered experiment contracts."""

import math

from pydantic import BaseModel, Field, field_validator, model_validator


class ExperimentPlan(BaseModel):
    experiment_id: str
    hypothesis_id: str
    pre_registered_plan: str
    code_hash: str
    data_snapshot: str
    variants_tested: int = Field(ge=1)
    train_periods: list[str]
    test_periods: list[str]
    multiple_testing_adjustment: str
    holdout_sealed: bool = True


class ExperimentResult(BaseModel):
    experiment_id: str
    metrics: dict[str, float | None]
    limitations: list[str]
    verdict: str
    replication_status: str

    @field_validator("metrics", mode="before")
    @classmethod
    def reject_boolean_metrics(cls, value: object) -> object:
        if isinstance(value, dict) and any(
            isinstance(metric, bool) for metric in value.values()
        ):
            raise ValueError("experiment metrics cannot be boolean")
        return value

    @model_validator(mode="after")
    def validate_result(self) -> "ExperimentResult":
        if (
            not self.experiment_id.strip()
            or not self.verdict.strip()
            or not self.replication_status.strip()
        ):
            raise ValueError("experiment result identity fields must be nonblank")
        if any(value is not None and not math.isfinite(value) for value in self.metrics.values()):
            raise ValueError("experiment metrics must be finite when present")
        return self
