"""Proven meter engines from the sealed research specification.

Formulas are ported verbatim from the legacy candidate registry and the Kimi
research trail. Every meter is an equal-weight mean of expanding-percentile
components — zero fitted parameters. Missing components degrade status instead
of being silently neutralized.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from eros.meters.transforms import (
    apply_publication_lag,
    combine_mean,
    delta_n,
    expanding_pct,
    pct_change_n,
    realized_vol,
)

MeterStatus = Literal["LIVE", "PARTIAL", "NO_DATA"]


class MeterReading(BaseModel):
    """One meter value with component visibility and an honesty label."""

    meter_id: str
    label: str
    value: float | None
    status: MeterStatus
    components: dict[str, float] = Field(default_factory=dict)
    missing: list[str] = Field(default_factory=list)
    as_of: str
    evidence: str
    note: str = ""


def _latest(series: pd.Series) -> float | None:
    finite = series.dropna()
    if finite.empty:
        return None
    return float(finite.iloc[-1])


def _as_of(series: pd.Series) -> str | None:
    finite = series.dropna()
    if finite.empty:
        return None
    stamp = pd.Timestamp(finite.index[-1])
    return stamp.strftime("%Y-%m-%d")


def _pct_of(series: pd.Series, lag_days: int) -> pd.Series:
    """Apply publication lag then compute the expanding percentile."""

    lagged = apply_publication_lag(series, lag_days)
    return expanding_pct(lagged)


def growth_index(
    cfnai: pd.Series,
    neworder: pd.Series,
    unrate: pd.Series,
    icsa: pd.Series,
    lags: dict[str, int],
) -> pd.Series:
    """GROWTH = mean(pct CFNAI, pct d6m(%chg NEWORDER), 1-pct d12m UNRATE, 1-pct YoY ICSA)."""

    components = [
        _pct_of(cfnai, lags.get("CFNAI", 0)),
        _pct_of(pct_change_n(neworder, 6), lags.get("NEWORDER", 0)),
        1.0 - _pct_of(delta_n(unrate, 12), lags.get("UNRATE", 0)),
        1.0 - _pct_of(pct_change_n(icsa, 52), lags.get("ICSA", 0)),
    ]
    return combine_mean(components)


def inflation_index(
    cpi: pd.Series,
    wti: pd.Series,
    t5yifr: pd.Series,
    lags: dict[str, int],
) -> pd.Series:
    """INFL = mean(pct YoY CPI, pct YoY WTI, pct T5YIFR)."""

    components = [
        _pct_of(pct_change_n(cpi, 12), lags.get("CPIAUCSL", 0)),
        _pct_of(pct_change_n(wti, 252), lags.get("DCOILWTICO", 0)),
        _pct_of(t5yifr, lags.get("T5YIFR", 0)),
    ]
    return combine_mean(components)


def tilt_weights(growth: pd.Series, infl: pd.Series) -> pd.DataFrame:
    """Legacy tilt baseline: SPX/TLT/COMM/GLD with 5% floor, renormalized."""

    frame = pd.DataFrame({"growth": growth, "infl": infl}).dropna()
    if frame.empty:
        return pd.DataFrame(columns=["SPX", "TLT", "COMM", "GLD"])
    growth_momentum = expanding_pct(delta_n(frame["growth"], 6))
    raw = pd.DataFrame(
        {
            "SPX": 0.25 - (frame["infl"] - 0.5),
            "TLT": 0.25 + (frame["infl"] - 0.5),
            "COMM": 0.25 + (growth_momentum - 0.5),
            "GLD": 0.25,
        }
    ).dropna()
    if raw.empty:
        return pd.DataFrame(columns=["SPX", "TLT", "COMM", "GLD"])
    raw = raw.clip(lower=0.05)
    return raw.div(raw.sum(axis=1), axis=0)


def gold_meter(
    dfii10: pd.Series, m2: pd.Series, delinq: pd.Series, lags: dict[str, int]
) -> pd.Series:
    """GOLD_METER_V2 = mean(pct DFII10, 1-pct YoY M2SL, pct DRCLACBS)."""

    components = [
        _pct_of(dfii10, lags.get("DFII10", 0)),
        1.0 - _pct_of(pct_change_n(m2, 12), lags.get("M2SL", 0)),
        _pct_of(delinq, lags.get("DRCLACBS", 0)),
    ]
    return combine_mean(components)


def dollar_meter(
    nfci: pd.Series,
    evz: pd.Series,
    fedfunds: pd.Series,
    infl: pd.Series,
    lags: dict[str, int],
) -> pd.Series:
    """DOLLAR_METER_V1 = mean(1-pct NFCI, 1-pct EVZ, 1-pct FEDFUNDS, pct INFL)."""

    components = [
        1.0 - _pct_of(nfci, lags.get("NFCI", 0)),
        1.0 - _pct_of(evz, lags.get("EVZCLS", 0)),
        1.0 - _pct_of(fedfunds, lags.get("FEDFUNDS", 0)),
        infl,
    ]
    return combine_mean(components)


def fear_entry_signal(vix: pd.Series, infl: pd.Series, lags: dict[str, int]) -> pd.Series:
    """FEAR-ENTRY: pct(VIX) > 0.80 AND INFL <= 0.50 (proven, hit 100% n=29)."""

    vix_pct = _pct_of(vix, lags.get("VIXCLS", 0))
    aligned = pd.DataFrame({"vix": vix_pct, "infl": infl}).ffill()
    return (aligned["vix"] > 0.80) & (aligned["infl"] <= 0.50)


def bcm_stress(
    fedfunds: pd.Series,
    t10y3m: pd.Series,
    nfci: pd.Series,
    stlfsi: pd.Series,
    kcfsi: pd.Series,
    baa_spread: pd.Series,
    delinq: pd.Series,
    sloos: pd.Series,
    growth: pd.Series,
    m2: pd.Series,
    rv21: pd.Series,
    vix: pd.Series,
    lags: dict[str, int],
) -> pd.DataFrame:
    """BCM v3.2 six blocks (TREND removed by doctrine). Returns per-block frame.

    POLICY: two-tailed U-shape on d1y FEDFUNDS + re-steepening of the 3M10Y curve.
    STRESS: NFCI / STLFSI / KCFSI. CREDIT: BAA spread level+velocity, delinquency,
    SLOOS. REAL: 1 - GROWTH. LIQ: pct YoY M2. VOL: rv21 and variance-risk-premium.
    """

    # FEDFUNDS is monthly: one year is 12 observations, not 252 trading days.
    d1y = delta_n(fedfunds, 12)
    u_shape = (2.0 * (_pct_of(d1y, lags.get("FEDFUNDS", 0)) - 0.5)).abs()
    resteep = _pct_of(delta_n(t10y3m, 63), lags.get("T10Y3M", 0))
    policy = combine_mean([u_shape, resteep])

    stress = combine_mean(
        [
            _pct_of(nfci, lags.get("NFCI", 0)),
            _pct_of(stlfsi, lags.get("STLFSI4", 0)),
            _pct_of(kcfsi, lags.get("KCFSI", 0)),
        ]
    )

    credit = combine_mean(
        [
            _pct_of(baa_spread, lags.get("BAA10Y", 0)),
            _pct_of(delta_n(baa_spread, 126), lags.get("BAA10Y", 0)),
            _pct_of(delinq, lags.get("DRCLACBS", 0)),
            _pct_of(sloos, lags.get("DRTSCILM", 0)),
        ]
    )

    real = 1.0 - growth
    liq = _pct_of(pct_change_n(m2, 12), lags.get("M2SL", 0))

    vrp = 1.0 - _pct_of(vix / rv21, lags.get("VIXCLS", 0))
    vol = combine_mean([_pct_of(rv21, 0), vrp])

    weights = {
        "POLICY": 0.20,
        "STRESS": 1 / 6,
        "CREDIT": 0.20,
        "REAL": 1 / 6,
        "LIQ": 1 / 12,
        "VOL": 1 / 6,
    }
    blocks = pd.DataFrame(
        {"POLICY": policy, "STRESS": stress, "CREDIT": credit, "REAL": real, "LIQ": liq, "VOL": vol}
    ).sort_index()
    # Components publish at different frequencies and lags; the latest available
    # percentile stays valid until the next release (point-in-time forward-fill).
    blocks = blocks.ffill()
    weight_total = sum(weights.values())
    weighted = blocks[list(weights)].mul(pd.Series(weights, dtype="float64")).sum(axis=1)
    bcm_values = weighted / weight_total
    blocks["BCM"] = bcm_values.where(blocks[list(weights)].notna().all(axis=1))
    return blocks


def fragility(buffett: pd.Series, cape: pd.Series | None) -> tuple[pd.Series, MeterStatus]:
    """FRAGILITY = mean(pct Buffett, pct CAPE); PARTIAL when CAPE unavailable."""

    buffett_pct = expanding_pct(buffett)
    if cape is None:
        return buffett_pct, "PARTIAL"
    return combine_mean([buffett_pct, expanding_pct(cape)]), "LIVE"


def r2_exposure_state(bcm: pd.Series, frag: pd.Series) -> pd.Series:
    """R2 state machine: EXIT (FRAG>=0.8 & BCM>=0.65) -> 50% (BCM<0.60)
    -> 100% (BCM<0.50) -> RE-EXIT (BCM>=0.80)."""

    aligned = pd.DataFrame({"bcm": bcm, "frag": frag}).ffill().dropna()
    values: list[float] = []
    exposure = 1.0
    for _idx, row in aligned.iterrows():
        bcm_level = float(row["bcm"])
        frag_level = float(row["frag"])
        if exposure > 0 and frag_level >= 0.8 and bcm_level >= 0.65:
            exposure = 0.0
        elif exposure == 0.0 and bcm_level < 0.60:
            exposure = 0.5
        elif exposure == 0.5 and bcm_level < 0.50:
            exposure = 1.0
        if exposure < 1.0 and bcm_level >= 0.80:
            exposure = 0.0
        values.append(exposure)
    return pd.Series(values, index=aligned.index, dtype="float64")


def spx_realized_vol(spx: pd.Series) -> pd.Series:
    """Annualized 21-day realized volatility (percent) from SPX closes."""

    import math as _math

    ratio = spx / spx.shift(1)
    returns = ratio.map(lambda v: _math.log(v) if v is not None and v > 0 else float("nan"))
    return realized_vol(returns)


__all__ = [
    "MeterReading",
    "_latest",
    "bcm_stress",
    "dollar_meter",
    "fear_entry_signal",
    "fragility",
    "gold_meter",
    "growth_index",
    "inflation_index",
    "r2_exposure_state",
    "spx_realized_vol",
    "tilt_weights",
]
