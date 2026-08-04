"""FRED multi-series fetcher with disk cache and publication-lag metadata.

Every series carries its documented publication lag so the engine never sees a
data point before it was publicly available. Fetch failures fail closed per
series; nothing is interpolated silently.

Known honesty limit: fredgraph.csv serves the latest vintage of each series.
Revised history (e.g. GDP rewrites) cannot be removed without ALFRED vintage
endpoints; fixed calendar-day lags approximate release timing but do not remove
revision look-ahead. This constraint is accepted and documented, not hidden.
"""

from __future__ import annotations

import csv
import io
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

RequestBytes = Callable[[str], bytes]

FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[3] / "runtime" / "fred_cache"
CACHE_TTL_SECONDS = 12 * 3600
MAX_RESPONSE_BYTES = 20 * 1024 * 1024
# A failed fetch may reuse a cached series only while it is still plausibly
# current. Beyond this bound the series must fail closed (NO_DATA), never
# silently render LIVE from arbitrarily old data.
MAX_STALE_SECONDS = 7 * 24 * 3600

# Documented publication lags (days) from the research audit trail.
PUBLICATION_LAG_DAYS: dict[str, int] = {
    "CFNAI": 24,
    "NEWORDER": 26,
    "UNRATE": 24,
    "ICSA": 4,
    "CPIAUCSL": 13,
    "DCOILWTICO": 0,
    "T5YIFR": 0,
    "DFII10": 0,
    "M2SL": 14,
    "DRCLACBS": 45,
    "NFCI": 7,
    "EVZCLS": 0,
    "FEDFUNDS": 0,
    "VIXCLS": 0,
    "DGS10": 1,
    "DGS3MO": 1,
    "STLFSI4": 7,
    "KCFSI": 7,
    "BAA10Y": 1,
    "DRTSCILM": 35,
    "BOGZ1FL893064105Q": 75,
    "GDP": 28,
}


def _default_request(url: str) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EROS/3.0",
            "Accept": "text/csv,*/*",
        },
    )
    with urlopen(request, timeout=15) as response:
        data: bytes = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError("FRED response exceeds 20 MiB safety limit")
    return data


def _parse_fred_csv(series_id: str, payload: bytes) -> pd.Series:
    rows = [
        row
        for row in csv.DictReader(io.StringIO(payload.decode("utf-8", errors="replace")))
        if row.get(series_id) not in (None, "", ".")
    ]
    if not rows:
        raise ValueError(f"FRED {series_id} returned no usable observation")
    dates = pd.to_datetime([row["observation_date"] for row in rows], utc=False)
    values = pd.Series(
        [float(row[series_id]) for row in rows],
        index=pd.DatetimeIndex(dates, name="date"),
        name=series_id,
        dtype="float64",
    )
    return values.sort_index()


def fetch_fred_series(
    series_id: str,
    *,
    request: RequestBytes = _default_request,
    cache_dir: Path | None = DEFAULT_CACHE_DIR,
    now: datetime | None = None,
    max_age_seconds: int = CACHE_TTL_SECONDS,
    max_stale_seconds: int = MAX_STALE_SECONDS,
) -> pd.Series:
    """Fetch one FRED series with disk cache; cache falls back when fetch fails."""

    fetched_at = now or datetime.now(UTC)
    cache_path = cache_dir / f"{series_id}.csv" if cache_dir is not None else None
    if cache_path is not None and cache_path.exists():
        age = fetched_at.timestamp() - cache_path.stat().st_mtime
        if age <= max_age_seconds:
            return _read_cache(cache_path, series_id)
    try:
        payload = request(f"{FRED_BASE}{series_id}")
        series = _parse_fred_csv(series_id, payload)
    except Exception:
        if cache_path is not None and cache_path.exists():
            age = fetched_at.timestamp() - cache_path.stat().st_mtime
            if age > max_stale_seconds:
                raise ValueError(
                    f"FRED {series_id} fetch failed and cache is {age / 86400:.1f} days old "
                    f"(limit {max_stale_seconds / 86400:.0f}) — failing closed"
                ) from None
            return _read_cache(cache_path, series_id)
        raise
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        series.to_csv(cache_path, index_label="date", header=[series_id])
    return series


def _read_cache(cache_path: Path, series_id: str) -> pd.Series:
    frame = pd.read_csv(cache_path, parse_dates=["date"])
    series = pd.Series(
        frame[series_id].astype(float).to_numpy(),
        index=pd.DatetimeIndex(frame["date"], name="date"),
        name=series_id,
    )
    return series.sort_index()


def fetch_many(
    series_ids: list[str],
    *,
    request: RequestBytes = _default_request,
    cache_dir: Path | None = DEFAULT_CACHE_DIR,
    max_workers: int = 6,
) -> tuple[dict[str, pd.Series], dict[str, str]]:
    """Fetch many series concurrently; failures are reported, never hidden."""

    series: dict[str, pd.Series] = {}
    failures: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(fetch_fred_series, sid, request=request, cache_dir=cache_dir): sid
            for sid in series_ids
        }
        for future in as_completed(futures):
            sid = futures[future]
            try:
                series[sid] = future.result()
            except Exception as exc:
                failures[sid] = f"{type(exc).__name__}: {exc}"
    return series, failures


def wait_for_sources(seconds: float = 0.0) -> None:
    """Hook for tests to control pacing."""

    if seconds > 0:
        time.sleep(seconds)
