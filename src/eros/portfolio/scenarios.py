"""Scenario and counterfactual portfolio stress contracts."""
from pydantic import BaseModel, Field


class Scenario(BaseModel):
    scenario_id: str
    name: str
    probability: float = Field(ge=0.0, le=1.0)
    triggers: list[str]
    factor_shocks: dict[str, float]


def scenario_impact(exposures: dict[str, float], scenario: Scenario) -> float:
    return sum(exposures.get(factor, 0.0) * shock for factor, shock in scenario.factor_shocks.items())
