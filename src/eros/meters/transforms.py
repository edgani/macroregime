"""Deterministic point-in-time transforms for EROS meters.

All meters speak one language: a real-time expanding midrank percentile of the
source series against its own history up to the observation date. No rolling
windows, no fitted parameters, no look-ahead.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import pandas as pd


def expanding_pct(values: pd.Series) -> pd.Series:
    """Real-time expanding midrank percentile of each observation.

    pct(x_t) = (count(x_i < x_t) + 0.5 * count(x_i == x_t)) / n for i < t.
    The first finite observation is NaN (no history to rank against).
    Non-finite values propagate as NaN and are never imputed.
    O(n log n) via a sorted history with bisection.
    """

    import bisect

    if not isinstance(values, pd.Series):
        raise TypeError("expanding_pct expects a pandas Series")
    numeric = pd.to_numeric(values, errors="coerce")
    out = pd.Series(float("nan"), index=values.index, dtype="float64")
    history: list[float] = []
    for position, (_idx, value) in enumerate(numeric.items()):
        if value is None or not math.isfinite(float(value)):
            out.iloc[position] = float("nan")
            continue
        current = float(value)
        if history:
            less = bisect.bisect_left(history, current)
            equal = bisect.bisect_right(history, current) - less
            out.iloc[position] = (less + 0.5 * equal) / len(history)
        bisect.insort(history, current)
    return out


def pct_change_n(values: pd.Series, periods: int) -> pd.Series:
    """Percent change over ``periods`` observations, NaN-safe."""

    if periods < 1:
        raise ValueError("periods must be positive")
    numeric = pd.to_numeric(values, errors="coerce")
    changed = numeric.pct_change(periods=periods)
    return changed.where(changed.map(math.isfinite))


def delta_n(values: pd.Series, periods: int) -> pd.Series:
    """First difference over ``periods`` observations, NaN-safe."""

    if periods < 1:
        raise ValueError("periods must be positive")
    numeric = pd.to_numeric(values, errors="coerce")
    diff = numeric.diff(periods=periods)
    return diff.where(diff.map(math.isfinite))


def apply_publication_lag(values: pd.Series, lag_days: int) -> pd.Series:
    """Shift a series forward by its publication lag (point-in-time alignment).

    A value published ``lag_days`` after its reference date must not be visible
    to the engine before that date.
    """

    if lag_days < 0:
        raise ValueError("lag_days cannot be negative")
    if lag_days == 0:
        return values
    if not isinstance(values.index, pd.DatetimeIndex):
        raise TypeError("publication lag requires a DatetimeIndex")
    shifted = values.copy()
    shifted.index = shifted.index + pd.Timedelta(days=lag_days)
    return shifted


def realized_vol(returns: pd.Series, window: int = 21, annualization: int = 252) -> pd.Series:
    """Annualized realized volatility (percent) from log returns."""

    if window < 2:
        raise ValueError("window must be at least two")
    numeric = pd.to_numeric(returns, errors="coerce")
    vol = numeric.rolling(window, min_periods=window).std() * math.sqrt(annualization) * 100.0
    return vol.where(vol.map(math.isfinite))


def combine_mean(components: Sequence[pd.Series]) -> pd.Series:
    """Equal-weight mean of components; NaN only where every component is NaN.

    A component missing at a date reduces the effective weight instead of being
    silently treated as neutral — callers must inspect component coverage.
    """

    if not components:
        raise ValueError("combine_mean requires at least one component")
    frame = pd.concat(components, axis=1)
    return frame.mean(axis=1, skipna=True)
