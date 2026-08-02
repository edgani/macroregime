"""Fail-closed feed health evaluation."""
from datetime import datetime, timedelta
from enum import StrEnum
from pydantic import BaseModel


class FeedStatus(StrEnum):
    LIVE = "LIVE"
    PARTIAL = "PARTIAL"
    STALE = "STALE"
    NO_DATA = "NO_DATA"


class FeedHealth(BaseModel):
    status: FeedStatus
    last_observation: datetime | None
    downstream_enabled: bool
    value: float | None = None
    reason: str


def evaluate_feed_health(last_observation: datetime | None, expected_frequency: timedelta, now: datetime, value: float | None = None) -> FeedHealth:
    if last_observation is None:
        return FeedHealth(status=FeedStatus.NO_DATA, last_observation=None, downstream_enabled=False, value=None, reason="No observation is available.")
    if now - last_observation > expected_frequency * 2:
        return FeedHealth(status=FeedStatus.STALE, last_observation=last_observation, downstream_enabled=False, value=None, reason="Observation exceeded the freshness SLA.")
    return FeedHealth(status=FeedStatus.LIVE, last_observation=last_observation, downstream_enabled=True, value=value, reason="Observation is within the freshness SLA.")
