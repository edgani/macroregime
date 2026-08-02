"""Complete opportunity packet contract."""
from pydantic import BaseModel, Field
from eros.opportunity.ev import CostBreakdown, ExpectedValueResult


class OpportunityPacket(BaseModel):
    opportunity_id: str
    asset: str
    direction: str
    country: str
    currency: str
    mechanism_id: str
    thesis_id: str
    competing_thesis_probabilities: dict[str, float]
    probability_mechanism_true: float = Field(ge=0.0, le=1.0)
    probability_catalyst_within_horizon: float = Field(ge=0.0, le=1.0)
    probability_not_fully_priced: float = Field(ge=0.0, le=1.0)
    probability_trade_profitable_net: float = Field(ge=0.0, le=1.0)
    expected_value: ExpectedValueResult
    horizon: str
    evidence_families: list[str]
    missing_evidence: list[str]
    target_basis: str
    invalidation: list[str]
    instrument_mapping: list[str]
    costs: CostBreakdown
    evidence_label: str
    execution_permission: str = "human_approval_required"
