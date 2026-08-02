"""Evidence conflict resolver."""

from pydantic import BaseModel


class ConflictResolution(BaseModel):
    status: str
    confidence_multiplier: float
    rationale: str


def resolve_conflict(family_directions: dict[str, int]) -> ConflictResolution:
    directions = {value for value in family_directions.values() if value != 0}
    if len(directions) > 1:
        return ConflictResolution(
            status="UNRESOLVED_CONFLICT",
            confidence_multiplier=0.5,
            rationale="Independent evidence families disagree; tier must be downgraded.",
        )
    if not directions:
        return ConflictResolution(
            status="UNKNOWN",
            confidence_multiplier=0.0,
            rationale="No directional evidence is available.",
        )
    return ConflictResolution(
        status="COHERENT",
        confidence_multiplier=1.0,
        rationale="Independent evidence families agree.",
    )
