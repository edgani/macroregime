from datetime import UTC, datetime, timedelta

from eros.data.quality.health import FeedStatus, evaluate_feed_health


def test_stale_feed_fails_closed() -> None:
    now = datetime(2026, 8, 2, 12, tzinfo=UTC)
    health = evaluate_feed_health(now - timedelta(days=4), timedelta(days=1), now)
    assert health.status is FeedStatus.STALE and health.downstream_enabled is False


def test_missing_feed_is_unknown_not_neutral() -> None:
    health = evaluate_feed_health(None, timedelta(days=1), datetime(2026, 8, 2, tzinfo=UTC))
    assert health.status is FeedStatus.NO_DATA and health.value is None
