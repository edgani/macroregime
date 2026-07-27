"""Fail-closed dual-source monthly S&P 500 loader for the V7.9 trading core.

Production instructions require agreement between two independently distributed live feeds:
FRED's SP500 daily-close series and Yahoo's ^GSPC daily-close history. The still-open
calendar month is excluded. A missing source, stale source, date mismatch, or material
close mismatch produces ``UNAVAILABLE_FAIL_CLOSED`` and no executable order.

Bundled research CSVs are never used for a current decision.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from io import StringIO
from typing import Any
import hashlib
import json
import time

import pandas as pd

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC"


@dataclass(frozen=True)
class MonthlyFeedResult:
    status: str
    provider: str
    symbol: str
    fetched_at_utc: str
    observations: list[dict[str, Any]]
    latest_completed_month: str | None
    latest_close: float | None
    payload_sha256: str | None
    source_count: int
    source_details: list[dict[str, Any]]
    consensus_status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_date(value: str | date | datetime | None) -> date:
    if value is None:
        return _utc_now().date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()


def _completed_monthly(daily: pd.DataFrame, *, as_of: str | date | datetime | None = None) -> list[dict[str, Any]]:
    if daily.empty or "Date" not in daily or "Close" not in daily:
        raise ValueError("daily price frame requires Date and Close")
    d = daily[["Date", "Close"]].copy()
    d["Date"] = pd.to_datetime(d["Date"], utc=True, errors="coerce")
    d["Close"] = pd.to_numeric(d["Close"], errors="coerce")
    d = d.dropna().sort_values("Date")
    d = d[d["Close"].gt(0)]
    d = d.drop_duplicates(subset=["Date"], keep="last")
    if d.empty:
        raise ValueError("no positive closes")
    cutoff = _as_date(as_of)
    current_month_start = pd.Timestamp(date(cutoff.year, cutoff.month, 1), tz="UTC")
    d = d[d["Date"] < current_month_start]
    if d.empty:
        raise ValueError("no completed-month observations")
    monthly = d.set_index("Date")["Close"].resample("ME").last().dropna()
    rows = [
        {"observed_month": ts.date().replace(day=1).isoformat(), "close": float(value)}
        for ts, value in monthly.items()
    ]
    if len(rows) < 10:
        raise ValueError("fewer than 10 completed months")
    return rows


def _parse_fred_csv(text: str, *, as_of: str | date | datetime | None = None) -> list[dict[str, Any]]:
    frame = pd.read_csv(StringIO(text))
    if frame.empty or len(frame.columns) < 2:
        raise ValueError("FRED CSV has no usable rows")
    date_col = "observation_date" if "observation_date" in frame.columns else frame.columns[0]
    value_col = "SP500" if "SP500" in frame.columns else frame.columns[-1]
    frame = frame.rename(columns={date_col: "Date", value_col: "Close"})
    frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
    return _completed_monthly(frame, as_of=as_of)


def _parse_yahoo_payload(payload: dict[str, Any], *, as_of: str | date | datetime | None = None) -> list[dict[str, Any]]:
    result = (((payload.get("chart") or {}).get("result") or [None])[0])
    if not isinstance(result, dict):
        error = (payload.get("chart") or {}).get("error")
        raise ValueError(f"Yahoo chart returned no result: {error}")
    timestamps = result.get("timestamp") or []
    quote = (((result.get("indicators") or {}).get("quote") or [{}])[0])
    closes = quote.get("close") or []
    if len(timestamps) != len(closes) or not timestamps:
        raise ValueError("Yahoo timestamp/close payload mismatch")
    frame = pd.DataFrame({
        "Date": pd.to_datetime(timestamps, unit="s", utc=True),
        "Close": closes,
    })
    return _completed_monthly(frame, as_of=as_of)


def _fetch_fred_http(*, as_of: str | date | datetime | None, timeout: float) -> tuple[list[dict[str, Any]], str]:
    import requests

    response = requests.get(
        FRED_CSV,
        headers={"User-Agent": "Mozilla/5.0 WarRoomOS/7.9"},
        timeout=timeout,
    )
    response.raise_for_status()
    return _parse_fred_csv(response.text, as_of=as_of), "FRED SP500 (S&P DJI source)"


def _fetch_yahoo_http(*, as_of: str | date | datetime | None, timeout: float) -> tuple[list[dict[str, Any]], str]:
    import requests

    end = int(time.time()) + 86400
    start = end - 5 * 366 * 86400
    response = requests.get(
        YAHOO_CHART,
        params={
            "period1": start,
            "period2": end,
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true",
        },
        headers={"User-Agent": "Mozilla/5.0 WarRoomOS/7.9"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    return _parse_yahoo_payload(payload, as_of=as_of), "Yahoo Finance chart (^GSPC)"


def _fetch_yfinance(*, as_of: str | date | datetime | None) -> tuple[list[dict[str, Any]], str]:
    import yfinance as yf

    frame = yf.download(
        "^GSPC",
        period="5y",
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
        timeout=8,
    )
    if frame is None or frame.empty:
        raise ValueError("yfinance returned no ^GSPC rows")
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = [str(x[0]) for x in frame.columns]
    frame = frame.reset_index()
    return _completed_monthly(frame, as_of=as_of), "yfinance/Yahoo (^GSPC)"


def _fetch_yahoo_family(*, as_of: str | date | datetime | None, timeout: float) -> tuple[list[dict[str, Any]], str]:
    try:
        return _fetch_yahoo_http(as_of=as_of, timeout=timeout)
    except Exception as first:
        try:
            return _fetch_yfinance(as_of=as_of)
        except Exception as second:
            raise RuntimeError(f"Yahoo chart failed ({first}); yfinance fallback failed ({second})") from second


def _consensus(
    fred_rows: list[dict[str, Any]],
    yahoo_rows: list[dict[str, Any]],
    *,
    months: int = 10,
    tolerance_bps: float = 2.0,
    absolute_tolerance: float = 1.0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Require identical month keys and materially identical closes over the signal window."""
    f = {str(r["observed_month"]): float(r["close"]) for r in fred_rows}
    y = {str(r["observed_month"]): float(r["close"]) for r in yahoo_rows}
    shared = sorted(set(f) & set(y))
    if len(shared) < months:
        raise ValueError(f"only {len(shared)} shared completed months")
    keys = shared[-months:]
    if keys[-1] != fred_rows[-1]["observed_month"] or keys[-1] != yahoo_rows[-1]["observed_month"]:
        raise ValueError("latest completed-month mismatch across providers")
    comparisons = []
    for key in keys:
        fv, yv = f[key], y[key]
        tolerance = max(absolute_tolerance, abs(fv) * tolerance_bps / 10000.0)
        diff = abs(fv - yv)
        comparisons.append({"observed_month": key, "fred_close": fv, "yahoo_close": yv, "absolute_difference": diff, "tolerance": tolerance})
        if diff > tolerance:
            raise ValueError(f"provider close mismatch at {key}: FRED={fv}, Yahoo={yv}, tolerance={tolerance}")
    # FRED is retained as the canonical execution series after agreement.
    return fred_rows, {
        "months_compared": months,
        "tolerance_bps": tolerance_bps,
        "absolute_tolerance": absolute_tolerance,
        "latest_comparison": comparisons[-1],
        "max_absolute_difference": max(x["absolute_difference"] for x in comparisons),
    }


def fetch_completed_monthly_closes(
    *,
    as_of: str | date | datetime | None = None,
    timeout: float = 6.0,
) -> MonthlyFeedResult:
    fetched = _utc_now().isoformat()
    details: list[dict[str, Any]] = []
    outputs: dict[str, tuple[list[dict[str, Any]], str]] = {}
    for source_id, fetcher in (
        ("fred", lambda: _fetch_fred_http(as_of=as_of, timeout=timeout)),
        ("yahoo", lambda: _fetch_yahoo_family(as_of=as_of, timeout=timeout)),
    ):
        try:
            rows, provider = fetcher()
            outputs[source_id] = (rows, provider)
            details.append({
                "source_id": source_id,
                "provider": provider,
                "status": "LIVE",
                "latest_completed_month": rows[-1]["observed_month"],
                "latest_close": float(rows[-1]["close"]),
                "observation_count": len(rows),
            })
        except Exception as exc:
            details.append({"source_id": source_id, "provider": source_id, "status": "ERROR", "reason": f"{type(exc).__name__}: {exc}"})

    if set(outputs) != {"fred", "yahoo"}:
        return MonthlyFeedResult(
            status="UNAVAILABLE_FAIL_CLOSED",
            provider="dual-source required",
            symbol="^GSPC / FRED SP500",
            fetched_at_utc=fetched,
            observations=[],
            latest_completed_month=None,
            latest_close=None,
            payload_sha256=None,
            source_count=len(outputs),
            source_details=details,
            consensus_status="NOT_CONFIRMED",
            reason="Both FRED and Yahoo-distributed completed-month data are required; at least one source failed.",
        )

    try:
        canonical_rows, consensus = _consensus(outputs["fred"][0], outputs["yahoo"][0])
    except Exception as exc:
        return MonthlyFeedResult(
            status="UNAVAILABLE_FAIL_CLOSED",
            provider="FRED + Yahoo",
            symbol="^GSPC / FRED SP500",
            fetched_at_utc=fetched,
            observations=[],
            latest_completed_month=None,
            latest_close=None,
            payload_sha256=None,
            source_count=2,
            source_details=details,
            consensus_status="MISMATCH",
            reason=f"Dual-source consensus failed: {type(exc).__name__}: {exc}",
        )

    rows = canonical_rows[-24:]
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    details.append({"source_id": "consensus", "status": "PASS", **consensus})
    return MonthlyFeedResult(
        status="LIVE_DUAL_SOURCE_CONFIRMED",
        provider="FRED + Yahoo consensus",
        symbol="^GSPC / FRED SP500",
        fetched_at_utc=fetched,
        observations=rows,
        latest_completed_month=rows[-1]["observed_month"],
        latest_close=float(rows[-1]["close"]),
        payload_sha256=hashlib.sha256(canonical).hexdigest(),
        source_count=2,
        source_details=details,
        consensus_status="PASS",
        reason="Two live distributors agree across the trailing 10 completed months; the open calendar month is excluded.",
    )


__all__ = [
    "MonthlyFeedResult",
    "fetch_completed_monthly_closes",
    "_completed_monthly",
    "_parse_fred_csv",
    "_parse_yahoo_payload",
    "_consensus",
]
