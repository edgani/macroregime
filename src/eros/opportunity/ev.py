"""Conservative net expected-value calculations."""

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator

_COST_FIELDS = ("transaction", "funding", "borrow", "tax", "fx", "liquidity_impact")
_INPUT_FIELDS = (
    "probability_win",
    "expected_win",
    "expected_loss",
    "lower_confidence_adjustment",
    "tail_risk_penalty",
    "model_uncertainty_penalty",
)
_RESULT_FIELDS = ("gross_ev", "total_cost", "net_ev", "conservative_ev")


class CostBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction: FiniteFloat = Field(default=0.0, ge=0.0)
    funding: FiniteFloat = Field(default=0.0, ge=0.0)
    borrow: FiniteFloat = Field(default=0.0, ge=0.0)
    tax: FiniteFloat = Field(default=0.0, ge=0.0)
    fx: FiniteFloat = Field(default=0.0, ge=0.0)
    liquidity_impact: FiniteFloat = Field(default=0.0, ge=0.0)

    @field_validator(*_COST_FIELDS, mode="before")
    @classmethod
    def reject_boolean_cost(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("cost values cannot be boolean")
        return value

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
    model_config = ConfigDict(extra="forbid")

    probability_win: FiniteFloat = Field(ge=0.0, le=1.0)
    expected_win: FiniteFloat = Field(gt=0.0)
    expected_loss: FiniteFloat = Field(lt=0.0)
    costs: CostBreakdown
    lower_confidence_adjustment: FiniteFloat = Field(default=0.0, ge=0.0)
    tail_risk_penalty: FiniteFloat = Field(default=0.0, ge=0.0)
    model_uncertainty_penalty: FiniteFloat = Field(default=0.0, ge=0.0)

    @field_validator(*_INPUT_FIELDS, mode="before")
    @classmethod
    def reject_boolean_input(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("expected-value inputs cannot be boolean")
        return value


class ExpectedValueResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gross_ev: FiniteFloat
    total_cost: FiniteFloat
    net_ev: FiniteFloat
    conservative_ev: FiniteFloat

    @field_validator(*_RESULT_FIELDS, mode="before")
    @classmethod
    def reject_boolean_result(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("expected-value results cannot be boolean")
        return value


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
