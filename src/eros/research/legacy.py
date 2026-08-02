"""Exact, explicitly unverified legacy candidate formulas."""

from collections.abc import Sequence

import pandas as pd
from pydantic import BaseModel


class ValuationGapResult(BaseModel):
    ttm_fundamental: float
    multiple: float
    fair_value: float
    cheap_value: float
    danger_value: float
    gap: float


def legacy_tilt_baseline(
    inflation_percentile: float, growth_velocity_percentile: float
) -> dict[str, float]:
    raw = {
        "SPX": 0.25 - (inflation_percentile - 0.5),
        "TLT": 0.25 + (inflation_percentile - 0.5),
        "COMM": 0.25 + (growth_velocity_percentile - 0.5),
        "GLD": 0.25,
    }
    floored = {asset: max(0.05, value) for asset, value in raw.items()}
    total = sum(floored.values())
    return {asset: value / total for asset, value in floored.items()}


def valuation_gap(
    filings: pd.DataFrame,
    decision_at: pd.Timestamp,
    market_cap: float,
    shares: float,
    current_price: float,
    historical_multiples: Sequence[float],
) -> ValuationGapResult:
    available = filings.loc[filings["filed_at"] <= decision_at].sort_values("filed_at").tail(4)
    if len(available) < 4:
        raise ValueError("four point-in-time filed quarters are required")
    ttm = float(available["fundamental"].sum())
    series = pd.Series(historical_multiples, dtype=float)
    multiple = market_cap / ttm
    fair = float(series.median()) * ttm / shares
    cheap = float(series.quantile(0.15)) * ttm / shares
    danger = float(series.quantile(0.85)) * ttm / shares
    return ValuationGapResult(
        ttm_fundamental=ttm,
        multiple=multiple,
        fair_value=fair,
        cheap_value=cheap,
        danger_value=danger,
        gap=fair / current_price - 1.0,
    )
