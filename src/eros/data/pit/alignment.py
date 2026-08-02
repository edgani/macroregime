"""Point-in-time availability alignment."""
from datetime import datetime
from pydantic import BaseModel


class PointInTimeObservation(BaseModel):
    series_id: str
    effective_at: datetime
    available_at: datetime
    value: float
    vintage: str = "original"


def available_as_of(observations: list[PointInTimeObservation], decision_at: datetime, latest_vintage: bool = False) -> list[PointInTimeObservation]:
    eligible = [row for row in observations if row.available_at <= decision_at]
    if not latest_vintage:
        return sorted(eligible, key=lambda row: (row.series_id, row.effective_at, row.available_at))
    selected: dict[tuple[str, datetime], PointInTimeObservation] = {}
    for row in eligible:
        key = (row.series_id, row.effective_at)
        if key not in selected or row.available_at > selected[key].available_at:
            selected[key] = row
    return sorted(selected.values(), key=lambda row: (row.series_id, row.effective_at))
