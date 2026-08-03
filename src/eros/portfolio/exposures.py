"""Hidden-factor exposure decomposition."""

import math

from pydantic import BaseModel, Field, field_validator, model_validator


class PositionExposure(BaseModel):
    instrument: str
    weight: float
    factors: dict[str, float] = Field(default_factory=dict)

    @field_validator("weight", mode="before")
    @classmethod
    def reject_boolean_weight(cls, value: object) -> object:
        if isinstance(value, bool):
            raise ValueError("position weight cannot be boolean")
        return value

    @field_validator("factors", mode="before")
    @classmethod
    def reject_boolean_factors(cls, value: object) -> object:
        if isinstance(value, dict) and any(
            isinstance(loading, bool) for loading in value.values()
        ):
            raise ValueError("factor loadings cannot be boolean")
        return value

    @model_validator(mode="after")
    def validate_exposure(self) -> "PositionExposure":
        if not self.instrument.strip():
            raise ValueError("instrument must be nonblank")
        if not math.isfinite(self.weight):
            raise ValueError("position weight must be finite")
        if any(
            not factor.strip() or not math.isfinite(loading)
            for factor, loading in self.factors.items()
        ):
            raise ValueError("factor names must be nonblank and loadings finite")
        return self


def aggregate_exposures(positions: list[PositionExposure]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for position in positions:
        for factor, loading in position.factors.items():
            totals[factor] = totals.get(factor, 0.0) + position.weight * loading
    return totals
