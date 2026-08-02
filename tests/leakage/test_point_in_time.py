from datetime import UTC, datetime

from eros.data.pit.alignment import PointInTimeObservation, available_as_of


def test_future_release_is_excluded() -> None:
    rows = [
        PointInTimeObservation(
            "CPI", datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 7, 10, tzinfo=UTC), 2.7
        ),
        PointInTimeObservation(
            "CPI", datetime(2026, 7, 1, tzinfo=UTC), datetime(2026, 8, 12, tzinfo=UTC), 2.5
        ),
    ]
    assert [row.value for row in available_as_of(rows, datetime(2026, 8, 2, tzinfo=UTC))] == [2.7]


def test_latest_available_vintage_wins_without_overwrite() -> None:
    rows = [
        PointInTimeObservation(
            "GDP",
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 4, 1, tzinfo=UTC),
            1.0,
            "advance",
        ),
        PointInTimeObservation(
            "GDP", datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 5, 1, tzinfo=UTC), 1.2, "second"
        ),
    ]
    result = available_as_of(rows, datetime(2026, 6, 1, tzinfo=UTC), latest_vintage=True)
    assert len(result) == 1 and result[0].value == 1.2 and result[0].vintage == "second"
