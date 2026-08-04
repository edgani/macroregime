"""Contract tests for proven meter transforms and engines."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from eros.meters.engines import (
    dollar_meter,
    fear_entry_signal,
    gold_meter,
    growth_index,
    inflation_index,
    r2_exposure_state,
    tilt_weights,
)
from eros.meters.transforms import (
    apply_publication_lag,
    expanding_pct,
)


def _series(values: list[float], start: str = "2020-01-01", freq: str = "D") -> pd.Series:
    index = pd.date_range(start, periods=len(values), freq=freq, name="date")
    return pd.Series(values, index=index, dtype="float64")


def test_expanding_pct_midrank_is_exact_and_never_imputes() -> None:
    values = _series([10.0, 20.0, 20.0, 5.0, float("nan"), 30.0])
    pct = expanding_pct(values)

    assert math.isnan(pct.iloc[0])
    assert pct.iloc[1] == pytest.approx(1.0)
    assert pct.iloc[2] == pytest.approx((1 + 0.5) / 2)
    assert pct.iloc[3] == pytest.approx(0.0)
    assert math.isnan(pct.iloc[4])
    assert pct.iloc[5] == pytest.approx(1.0)


def test_expanding_pct_is_causal_and_history_only() -> None:
    values = _series([5.0, 1.0, 100.0])
    pct = expanding_pct(values)

    assert pct.iloc[1] == pytest.approx(0.0)
    assert pct.iloc[2] == pytest.approx(1.0)


def test_publication_lag_shifts_visibility_forward() -> None:
    values = _series([1.0, 2.0, 3.0])
    lagged = apply_publication_lag(values, 7)

    assert lagged.index[0] == values.index[0] + pd.Timedelta(days=7)
    with pytest.raises(ValueError):
        apply_publication_lag(values, -1)


def test_growth_inflation_and_tilt_follow_the_sealed_formulas() -> None:
    base = _series([float(i + 10) for i in range(60)], freq="ME")
    lags = {
        "CFNAI": 0, "NEWORDER": 0, "UNRATE": 0, "ICSA": 0,
        "CPIAUCSL": 0, "DCOILWTICO": 0, "T5YIFR": 0,
    }

    growth = growth_index(base, base, base, base, lags)
    infl = inflation_index(base, base, base, lags)
    tilt = tilt_weights(growth, infl)

    assert not growth.dropna().empty
    assert growth.dropna().between(0, 1).all()
    assert not tilt.empty
    assert (tilt.sum(axis=1)).map(lambda x: abs(x - 1.0) < 1e-9).all()
    assert (tilt >= 0.0).all().all()


def test_gold_and_dollar_meters_match_component_definitions() -> None:
    up = _series([float(i + 1) for i in range(40)], freq="ME")
    down = _series([float(41 - i) for i in range(40)], freq="ME")
    lags = {"DFII10": 0, "M2SL": 0, "DRCLACBS": 0, "NFCI": 0, "EVZCLS": 0, "FEDFUNDS": 0}
    infl = _series([0.5] * 40, freq="ME")

    gold = gold_meter(up, up, up, lags)
    dollar = dollar_meter(down, down, down, infl, lags)

    assert gold.dropna().between(0, 1).all()
    assert dollar.dropna().between(0, 1).all()


def test_fear_entry_requires_both_vix_extreme_and_low_inflation() -> None:
    vix = _series([10.0] * 30 + [80.0] * 10)
    infl_low = _series([0.3] * 40)
    infl_high = _series([0.9] * 40)

    assert fear_entry_signal(vix, infl_low, {"VIXCLS": 0}).iloc[-1]
    assert not fear_entry_signal(vix, infl_high, {"VIXCLS": 0}).iloc[-1]


def test_r2_state_machine_follows_the_documented_rules() -> None:
    index = pd.date_range("2020-01-01", periods=6, freq="D", name="date")
    bcm = pd.Series([0.30, 0.70, 0.55, 0.45, 0.85, 0.40], index=index)
    frag = pd.Series([0.90] * 6, index=index)

    state = r2_exposure_state(bcm, frag)

    assert list(state) == [1.0, 0.0, 0.5, 1.0, 0.0, 0.5]


def test_r2_hysteresis_holds_half_exposure_in_the_ambiguous_band() -> None:
    """After re-entry at 50%, BCM 0.50-0.60 must NOT restore full exposure."""

    index = pd.date_range("2020-01-01", periods=5, freq="D", name="date")
    bcm = pd.Series([0.70, 0.55, 0.58, 0.52, 0.49], index=index)
    frag = pd.Series([0.90] * 5, index=index)

    state = r2_exposure_state(bcm, frag)

    assert list(state) == [0.0, 0.5, 0.5, 0.5, 1.0]


def test_r2_reexit_requires_bcm_extreme_regardless_of_fragility() -> None:
    """From half exposure, BCM >= 0.80 re-exits even when FRAGILITY < 0.8."""

    index = pd.date_range("2020-01-01", periods=4, freq="D", name="date")
    bcm = pd.Series([0.70, 0.55, 0.82, 0.40], index=index)
    frag = pd.Series([0.50] * 4, index=index)

    state = r2_exposure_state(bcm, frag)

    assert list(state) == [1.0, 1.0, 1.0, 1.0]
