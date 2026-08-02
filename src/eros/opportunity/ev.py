"""Conservative net expected-value calculations."""

from pydantic import BaseModel, Field


class CostBreakdown(BaseModel):
    transaction: float = Field(default=0.0, ge=0.0)
    funding: float = Field(default=0.0, ge=0.0)
    borrow: float = Field(default=0.0, ge=0.0)
    tax: float = Field(default=0.0, ge=0.0)
    fx: float = Field(default=0.0, ge=0.0)
    liquidity_impact: float = Field(default=0.0, ge=0.0)

    @property
    def total(self) -> float:
        return (
            self.transaction
            + self.funding
            + self.borrow
            + self.tax
            + self.fx
            + self.liquidity_impact
        )


class ExpectedValueInput(BaseModel):
    probability_win: float = Field(ge=0.0, le=1.0)
    expected_win: float = Field(gt=0.0)
    expected_loss: float = Field(lt=0.0)
    costs: CostBreakdown
    lower_confidence_adjustment: float = Field(default=0.0, ge=0.0)
    tail_risk_penalty: float = Field(default=0.0, ge=0.0)
    model_uncertainty_penalty: float = Field(default=0.0, ge=0.0)


class ExpectedValueResult(BaseModel):
    gross_ev: float
    total_cost: float
    net_ev: float
    conservative_ev: float


def evaluate_expected_value(inputs: ExpectedValueInput) -> ExpectedValueResult:
    gross = (
        inputs.probability_win * inputs.expected_win
        + (1.0 - inputs.probability_win) * inputs.expected_loss
    )
    net = gross - inputs.costs.total
    conservative = (
        net
        - inputs.lower_confidence_adjustment
        - inputs.tail_risk_penalty
        - inputs.model_uncertainty_penalty
    )
    return ExpectedValueResult(
        gross_ev=round(gross, 12),
        total_cost=round(inputs.costs.total, 12),
        net_ev=round(net, 12),
        conservative_ev=round(conservative, 12),
    )
