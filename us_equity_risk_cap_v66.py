"""V6.6 scoped US broad-equity monthly risk-cap control.

This is deliberately not a crash predictor and not a ticker selector.  It implements the
only decision permission granted by the V6.6 confirmation result: at a completed monthly
observation, cap broad US equity exposure when the price is below its trailing 10-month
simple moving average.  Missing, stale, duplicated, non-monthly, or insufficient input
fails closed and never creates exposure.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Iterable, Mapping, Any
import hashlib
import json
import math

COMPONENT_ID = "US_SMA10_MONTHLY_RISK_CAP"
DECISION_PERMISSION = "REDUCE_US_BROAD_EQUITY_EXPOSURE_ONLY_AT_MONTHLY_REBALANCE"


@dataclass(frozen=True)
class MonthlyObservation:
    observed_month: str
    close: float


@dataclass(frozen=True)
class RiskCapDecision:
    component_id: str
    status: str
    observed_month: str | None
    close: float | None
    sma10: float | None
    max_broad_us_equity_multiplier: float
    decision_permission: str
    crash_prediction_permission: bool
    ticker_permission: bool
    short_permission: bool
    data_freshness_months: int | None
    input_sha256: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _month_start(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return date(value.year, value.month, 1)
    if isinstance(value, date):
        return date(value.year, value.month, 1)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return date(parsed.year, parsed.month, 1)


def _months_between(older: date, newer: date) -> int:
    return (newer.year - older.year) * 12 + newer.month - older.month


def _fail(reason: str, freshness: int | None = None) -> RiskCapDecision:
    return RiskCapDecision(
        component_id=COMPONENT_ID,
        status="NO_PERMISSION_FAIL_CLOSED",
        observed_month=None,
        close=None,
        sma10=None,
        max_broad_us_equity_multiplier=0.0,
        decision_permission=DECISION_PERMISSION,
        crash_prediction_permission=False,
        ticker_permission=False,
        short_permission=False,
        data_freshness_months=freshness,
        input_sha256=None,
        reason=reason,
    )


def evaluate_monthly_risk_cap(
    observations: Iterable[Mapping[str, Any] | MonthlyObservation],
    *,
    as_of: str | date | datetime | None = None,
    max_staleness_months: int = 1,
) -> RiskCapDecision:
    """Evaluate the frozen SMA10 rule from completed monthly observations.

    Input rows require ``observed_month`` and ``close``.  The function sorts months,
    rejects duplicates and gaps in the final 10-month window, and uses no future row.
    ``max_broad_us_equity_multiplier`` is a cap, never a target or leverage instruction.
    """
    rows: list[MonthlyObservation] = []
    for raw in observations:
        if isinstance(raw, MonthlyObservation):
            row = raw
        else:
            row = MonthlyObservation(str(raw.get("observed_month")), float(raw.get("close")))
        month = _month_start(row.observed_month)
        close = float(row.close)
        if not math.isfinite(close) or close <= 0:
            return _fail("non-positive or non-finite monthly close")
        rows.append(MonthlyObservation(month.isoformat(), close))
    if len(rows) < 10:
        return _fail("fewer than 10 completed monthly observations")
    rows.sort(key=lambda r: r.observed_month)
    months = [_month_start(r.observed_month) for r in rows]
    if len(set(months)) != len(months):
        return _fail("duplicate monthly observations")
    final = rows[-10:]
    final_months = [_month_start(r.observed_month) for r in final]
    for left, right in zip(final_months, final_months[1:]):
        if _months_between(left, right) != 1:
            return _fail("gap in trailing 10-month observation window")
    now = _month_start(as_of or datetime.now(timezone.utc))
    freshness = _months_between(final_months[-1], now)
    if freshness < 0:
        return _fail("future-dated observation", freshness)
    if freshness > max_staleness_months:
        return _fail("monthly observation is stale", freshness)
    closes = [r.close for r in final]
    sma10 = sum(closes) / 10.0
    close = closes[-1]
    payload = [{"observed_month": r.observed_month, "close": r.close} for r in final]
    input_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if close >= sma10:
        status = "BASELINE_CAP_ALLOWED"
        multiplier = 1.0
        reason = "completed monthly close is at or above trailing SMA10; the control does not force a reduction"
    else:
        status = "REDUCE_TO_CASH_CAP"
        multiplier = 0.0
        reason = "completed monthly close is below trailing SMA10; broad US equity exposure is capped at cash until a future completed monthly rebalance"
    return RiskCapDecision(
        component_id=COMPONENT_ID,
        status=status,
        observed_month=final[-1].observed_month,
        close=close,
        sma10=sma10,
        max_broad_us_equity_multiplier=multiplier,
        decision_permission=DECISION_PERMISSION,
        crash_prediction_permission=False,
        ticker_permission=False,
        short_permission=False,
        data_freshness_months=freshness,
        input_sha256=input_hash,
        reason=reason,
    )
