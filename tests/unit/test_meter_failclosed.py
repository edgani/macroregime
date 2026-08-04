"""Fail-closed contract for FRED fetching and BCM frequency handling."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pandas as pd
import pytest

from eros.meters.engines import bcm_stress
from eros.meters.fred import fetch_fred_series
from eros.meters.snapshot import checksum_verdict


def _cached_series_file(cache_dir, series_id: str, days_old: int) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        {"date": pd.date_range("2020-01-01", periods=5, freq="D"), series_id: [1.0] * 5}
    )
    path = cache_dir / f"{series_id}.csv"
    frame.to_csv(path, index=False)
    stale_time = datetime.now(UTC).timestamp() - days_old * 86400
    os.utime(path, (stale_time, stale_time))


def test_stale_cache_fails_closed_instead_of_rendering_live(tmp_path) -> None:
    """Reviewer finding: an arbitrarily old cache must never serve as LIVE data."""

    _cached_series_file(tmp_path, "UNRATE", days_old=30)

    def failing_request(url: str) -> bytes:
        raise ConnectionError("provider down")

    with pytest.raises(ValueError, match="failing closed"):
        fetch_fred_series(
            "UNRATE",
            request=failing_request,
            cache_dir=tmp_path,
            max_age_seconds=0,
        )


def test_fresh_cache_still_serves_when_provider_is_down(tmp_path) -> None:
    _cached_series_file(tmp_path, "UNRATE", days_old=1)

    def failing_request(url: str) -> bytes:
        raise ConnectionError("provider down")

    series = fetch_fred_series(
        "UNRATE",
        request=failing_request,
        cache_dir=tmp_path,
        max_age_seconds=0,
    )
    assert len(series) == 5


def test_policy_block_uses_twelve_months_not_252_monthly_observations() -> None:
    """Reviewer finding: d1y on a monthly series must span 12 observations."""

    index = pd.date_range("2015-01-01", periods=30, freq="ME", name="date")
    monthly = pd.Series([2.0] * 24 + [5.0] * 6, index=index, dtype="float64")
    daily_index = pd.date_range("2015-01-01", periods=600, freq="D", name="date")
    daily = pd.Series([0.5] * 600, index=daily_index, dtype="float64")
    weekly_index = pd.date_range("2015-01-01", periods=400, freq="W", name="date")
    weekly = pd.Series([0.5] * 400, index=weekly_index, dtype="float64")
    growth = pd.Series([0.5] * 30, index=index, dtype="float64")
    lags = {name: 0 for name in (
        "FEDFUNDS", "T10Y3M", "NFCI", "STLFSI4", "KCFSI", "BAA10Y",
        "DRCLACBS", "DRTSCILM", "M2SL", "VIXCLS",
    )}

    blocks = bcm_stress(
        monthly, daily, weekly, weekly, monthly, daily, monthly, monthly,
        growth, monthly, daily, daily, lags,
    )

    policy = blocks["POLICY"].dropna()
    assert not policy.empty
    # With only 30 monthly observations a 252-observation window would be all-NaN;
    # a 12-observation window produces real percentile values.
    assert policy.iloc[-1] > 0.0


def test_checksum_match_requires_unblocked_complete_bcm() -> None:
    status, note = checksum_verdict(0.4042, 0.9607, bcm_blocked=False)
    assert status == "MATCH"
    assert "0.4042" in note

    blocked_status, blocked_note = checksum_verdict(0.4042, 0.9607, bcm_blocked=True)
    assert blocked_status == "UNVERIFIED_PORT"
    assert "checksum not claimed" in blocked_note

    none_status, _ = checksum_verdict(None, 0.9607, bcm_blocked=False)
    assert none_status == "UNVERIFIED_PORT"

    _, none_gold_note = checksum_verdict(0.4042, None, bcm_blocked=False)
    assert "NO_DATA" in none_gold_note
    assert "None" not in none_gold_note

    differs_status, _ = checksum_verdict(0.75, 0.5, bcm_blocked=False)
    assert differs_status == "DIFFERS"
