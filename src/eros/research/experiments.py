"""Pre-registered experiment contracts."""

from pydantic import BaseModel, Field


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
