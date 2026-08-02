"""Hidden-factor exposure decomposition."""

from pydantic import BaseModel, Field


class PositionExposure(BaseModel):
    instrument: str
    weight: float
    factors: dict[str, float] = Field(default_factory=dict)


def aggregate_exposures(positions: list[PositionExposure]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for position in positions:
        for factor, loading in position.factors.items():
            totals[factor] = totals.get(factor, 0.0) + position.weight * loading
    return totals
