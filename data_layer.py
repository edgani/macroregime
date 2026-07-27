"""War Room OS v8.8 data adapter — nontechnical evidence only.

The adapter intentionally excludes chart transformations and price-derived signals. Current-vintage
FRED observations are collected only as descriptive context. They are never point-in-time eligible
until vintage/release timestamps are reconstructed. Market prices are not collected by this research
runtime; a future approved execution service may fetch a current quote solely after a capital receipt
exists.
"""
from __future__ import annotations

import io
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd

MARKETS = ("us", "idx", "crypto", "commodity", "fx")

# Economic and liquidity context. These are raw public series, not technical indicators.
FRED_SERIES = {
    "INDPRO": "Industrial production",
    "PAYEMS": "Nonfarm payrolls",
    "CPIAUCSL": "Consumer price index",
    "PCEPI": "PCE price index",
    "WALCL": "Federal Reserve balance sheet",
    "RRPONTSYD": "Overnight reverse repo",
    "WTREGEN": "Treasury General Account",
    "DFII10": "10-year real yield",
    "T10YIE": "10-year breakeven inflation",
    "BAMLH0A0HYM2": "US high-yield option-adjusted spread",
    "DFF": "Effective federal funds rate",
    "DGS2": "2-year Treasury yield",
    "DGS10": "10-year Treasury yield",
    "DTWEXBGS": "Trade-weighted US dollar index",
}


def _fetch_fred_series(series_id: str, timeout: float) -> tuple[str, pd.Series | None, str | None]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "WarRoomOS/8.8 research-only"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            frame = pd.read_csv(io.BytesIO(response.read()))
        if frame.shape[1] < 2:
            return series_id, None, "malformed response"
        frame = frame.iloc[:, :2].copy()
        frame.columns = ["date", "value"]
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        series = frame.dropna().set_index("date")["value"].sort_index()
        if series.empty:
            return series_id, None, "empty response"
        return series_id, series, None
    except Exception as exc:
        return series_id, None, f"{type(exc).__name__}: {exc}"


def load_fred_current_context(*, allow_live: bool = True, timeout: float = 8.0) -> tuple[dict[str, pd.Series], str, dict[str, str]]:
    if not allow_live or os.getenv("WARROOM_NETWORK_MODE", "live").lower() in {"offline", "disabled", "0", "false"}:
        return {}, "NO_DATA", {"_mode": "network disabled"}
    observations: dict[str, pd.Series] = {}
    status: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch_fred_series, sid, timeout): sid for sid in FRED_SERIES}
        for future in as_completed(futures):
            sid, series, error = future.result()
            if series is not None:
                observations[sid] = series
                status[sid] = "CURRENT_VINTAGE_OBSERVED"
            else:
                status[sid] = f"NO_DATA · {error}"
    source = "LIVE_CURRENT_VINTAGE_FRED" if observations else "NO_DATA"
    return observations, source, status


def load_all(
    markets: list[str] | tuple[str, ...] | None = None,
    start: str | None = None,
    allow_live: bool = True,
    fetch_live_feeds: bool = False,
    allow_synthetic: bool = False,
    fast_core: bool = True,
    skip_slow_context: bool = False,
    bootstrap_core: bool = False,
) -> dict[str, Any]:
    """Return a fail-closed research payload.

    Compatibility parameters are accepted so the surrounding runtime remains stable. Synthetic data
    and price-derived signal feeds are always disabled. `start`, `fetch_live_feeds`, `fast_core`,
    `skip_slow_context`, and `bootstrap_core` do not relax the proof policy.
    """
    del start, fetch_live_feeds, fast_core, skip_slow_context, bootstrap_core
    if allow_synthetic:
        raise ValueError("Synthetic evidence is forbidden in the V8.8 proof runtime")
    selected = [m for m in (markets or MARKETS) if m in MARKETS]
    fred, fred_source, fred_status = load_fred_current_context(allow_live=allow_live)
    sources = {market: "NO_EXECUTION_REFERENCE_LOADED" for market in selected}
    sources["macro"] = fred_source
    return {
        "markets": selected,
        "prices": {market: {} for market in selected},
        "ohlcv": {market: {} for market in selected},
        "fred": fred,
        "fred_source": fred_source,
        "feeds": {"_status": {"fred": fred_status, "_policy": "NONTECHNICAL_RESEARCH_ONLY"}},
        "sources": sources,
        "overall_source": "CURRENT_CONTEXT_RESEARCH_ONLY" if fred else "NO_DATA",
        "policy": {
            "technical_features": "FORBIDDEN",
            "synthetic_data": "FORBIDDEN",
            "price_collection": "DISABLED_UNTIL_EXECUTION_APPROVAL",
            "capital_permission": "BLOCKED",
        },
    }
