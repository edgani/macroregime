"""warroom/research/vol_proxy.py — options-free volatility layer (R10.1).

Origin: the operator's reverse-engineering mandate includes an options/vol
layer (expected move, extreme move band, volatility pressure, squeeze risk)
but the War Room currently has NO options chain data source. Per the mandate
itself: "If options data does not exist, build a proxy model and clearly
label it as a proxy, not truth."

This module is that proxy. Every output carries source=PROXY and an explicit
list of what is NOT measurable without options data (implied vol, skew, term
structure, gamma exposure, dealer positioning, pinning).

Design constraint (operator rule): no technical indicators. Everything here
is a statistical estimator over return distributions (realized volatility,
EWMA variance, vol-cone percentiles), not chart-pattern signals. No moving
average crossovers, no RSI, no MACD, no bands built for entries.

This is a measurement layer, not a trading signal. If it ever feeds a policy
change, that change is a new trial and must be registered in
warroom/research/trial_counter.py BEFORE evaluation (fail-closed gate).
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "warroom.vol_proxy.v1"
PROXY_LABEL = "PROXY_REALIZED_VOL_NO_OPTIONS_DATA"
NOT_MEASURABLE = [
    "implied_volatility",
    "skew",
    "term_structure",
    "gamma_exposure",
    "dealer_positioning",
    "pinning_risk",
    "vanna_charm",
]

MIN_OBS = 30  # below this, dispersion estimates are noise: refuse honestly


def _log_returns(closes: Sequence[float]) -> list[float]:
    return [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0 and closes[i] > 0]


def _std(xs: Sequence[float]) -> float:
    if len(xs) < 2:
        return 0.0
    mean = sum(xs) / len(xs)
    return math.sqrt(sum((x - mean) ** 2 for x in xs) / (len(xs) - 1))


def realized_vol_annualized(closes: Sequence[float], window: int) -> float | None:
    """Close-to-close realized volatility, annualized (sqrt(252) scaling)."""
    rets = _log_returns(closes)
    if len(rets) < window:
        return None
    return _std(rets[-window:]) * math.sqrt(252.0)


def ewma_vol_annualized(closes: Sequence[float], lam: float = 0.94) -> float | None:
    """RiskMetrics EWMA variance estimator (lambda=0.94), annualized."""
    rets = _log_returns(closes)
    if len(rets) < 10:
        return None
    var = rets[0] ** 2
    for r in rets[1:]:
        var = lam * var + (1.0 - lam) * r * r
    return math.sqrt(var) * math.sqrt(252.0)


def _rolling_realized_vols(closes: Sequence[float], window: int) -> list[float]:
    rets = _log_returns(closes)
    return [_std(rets[i - window:i]) * math.sqrt(252.0) for i in range(window, len(rets) + 1)]


def vol_cone_percentile(closes: Sequence[float], window: int) -> float | None:
    """Percentile rank (0-100) of the latest realized vol inside its own history."""
    vols = _rolling_realized_vols(closes, window)
    if len(vols) < 5:
        return None
    current = vols[-1]
    below = sum(1 for v in vols if v < current)
    return 100.0 * below / len(vols)


def expected_move(price: float, sigma_annual: float, horizon_days: int) -> float:
    """1-sigma expected move over the horizon: S * sigma * sqrt(T/252)."""
    return price * sigma_annual * math.sqrt(horizon_days / 252.0)


def _regime(percentile: float) -> str:
    if percentile < 20.0:
        return "COMPRESSED"
    if percentile > 80.0:
        return "EXPANDED"
    return "NORMAL"


def assess(
    security_id: str,
    closes: Sequence[float],
    *,
    price: float | None = None,
    window: int = 20,
    horizon_days: int = 30,
) -> dict[str, Any]:
    """Volatility-layer assessment for one security. Honest on thin data."""
    closes = [float(c) for c in closes if c and float(c) > 0]
    price = float(price) if price else (closes[-1] if closes else None)
    base: dict[str, Any] = {
        "schema": SCHEMA,
        "security_id": security_id,
        "source": PROXY_LABEL,
        "not_measurable_without_options_data": NOT_MEASURABLE,
        "window": window,
        "horizon_days": horizon_days,
    }
    if price is None or len(closes) < MIN_OBS:
        base.update(
            status="INSUFFICIENT_DATA",
            note=f"need >= {MIN_OBS} closes for dispersion estimates; got {len(closes)}",
        )
        return base

    sigma_cc = realized_vol_annualized(closes, window)
    sigma_ewma = ewma_vol_annualized(closes)
    percentile = vol_cone_percentile(closes, window)
    sigma = sigma_ewma if sigma_ewma is not None else sigma_cc
    em = expected_move(price, sigma, horizon_days)

    base.update(
        status="OK",
        price=price,
        realized_vol_annualized=round(sigma_cc, 6) if sigma_cc is not None else None,
        ewma_vol_annualized=round(sigma_ewma, 6) if sigma_ewma is not None else None,
        vol_cone_percentile=round(percentile, 2) if percentile is not None else None,
        vol_regime=_regime(percentile) if percentile is not None else "UNKNOWN",
        squeeze_expansion_risk=bool(percentile is not None and percentile < 15.0),
        expected_move_1sigma=round(em, 6),
        expected_move_band=[round(price - em, 6), round(price + em, 6)],
        extreme_move_band_2sigma=[round(price - 2 * em, 6), round(price + 2 * em, 6)],
        note="Proxy over realized returns. No implied vol, skew, gamma, or dealer data.",
    )
    return base


def assess_many(series: Mapping[str, Iterable[float]], **kwargs) -> dict[str, dict[str, Any]]:
    """Batch assessment: {security_id: closes} -> {security_id: assessment}."""
    return {sid: assess(sid, list(closes), **kwargs) for sid, closes in series.items()}
