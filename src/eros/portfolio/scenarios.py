"""Scenario and counterfactual portfolio stress contracts."""

import math

from pydantic import BaseModel, Field, field_validator, model_validator


class Scenario(BaseModel):
    scenario_id: str
    name: str
    probability: float = Field(ge=0.0, le=1.0)
    triggers: list[str]
    factor_shocks: dict[str, float]

    @field_validator("probability", mode="before")
    @classmethod
    def reject_boolean_probability(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("scenario probability cannot be boolean")
        return value

    @field_validator("factor_shocks", mode="before")
    @classmethod
    def reject_boolean_shocks(cls, value: object) -> object:
        if isinstance(value, dict) and any(
            isinstance(shock, bool) for shock in value.values()
        ):
            raise ValueError("scenario factor shocks cannot be boolean")
        return value

    @model_validator(mode="after")
    def validate_scenario(self) -> "Scenario":
        if not self.scenario_id.strip() or not self.name.strip():
            raise ValueError("scenario identity fields must be nonblank")
        if not self.triggers or any(not trigger.strip() for trigger in self.triggers):
            raise ValueError("scenario requires nonblank triggers")
        if not self.factor_shocks or any(
            not factor.strip() or not math.isfinite(shock)
            for factor, shock in self.factor_shocks.items()
        ):
            raise ValueError("scenario factor shocks must be nonblank and finite")
        return self


def scenario_impact(exposures: dict[str, float], scenario: Scenario) -> float:
    return sum(
        exposures.get(factor, 0.0) * shock for factor, shock in scenario.factor_shocks.items()
    )
