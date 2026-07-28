"""War Room OS V9.9 actual bundled-data + nontechnical current-context adapter.

Current quotes are execution references only. Public-source snapshots and current-vintage macro data
remain research context until their exact release/availability lineage passes the point-in-time gate.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd

from public_snapshot_reader_v98 import summarize_public_sources, universe_summary
from bundled_research_reader_v99 import all_context as load_bundled_context

HERE = Path(__file__).resolve().parent
MARKETS = ("us", "idx", "crypto", "commodity", "fx")
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


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _fetch_fred_series(series_id: str, timeout: float) -> tuple[str, pd.Series | None, str | None]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "WarRoomOS/9.9 current-context-only"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            frame = pd.read_csv(io.BytesIO(response.read()))
        if frame.shape[1] < 2:
            return series_id, None, "malformed response"
        frame = frame.iloc[:, :2].copy(); frame.columns = ["date", "value"]
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
    observations: dict[str, pd.Series] = {}; status: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch_fred_series, sid, timeout): sid for sid in FRED_SERIES}
        for future in as_completed(futures):
            sid, series, error = future.result()
            if series is not None:
                observations[sid] = series; status[sid] = "CURRENT_VINTAGE_OBSERVED"
            else:
                status[sid] = f"NO_DATA · {error}"
    return observations, "LIVE_CURRENT_VINTAGE_FRED" if observations else "NO_DATA", status


def load_execution_quotes() -> dict[str, Any]:
    path = HERE / "runtime" / "v99_trading" / "execution_quotes.json"
    # V9.9 never imports an older release's quote cache implicitly.  A previous release may have
    # different universe/schema semantics and must not silently affect current execution state.
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("quote root must be object")
        expected = str(payload.get("manifest_hash") or "")
        actual = hashlib.sha256(_canonical({k: v for k, v in payload.items() if k != "manifest_hash"})).hexdigest()
        payload["manifest_valid"] = len(expected) == 64 and expected == actual
        payload["loaded_from"] = path.relative_to(HERE).as_posix()
        if not payload["manifest_valid"]:
            payload["markets"] = {m: {} for m in MARKETS}
            payload["quote_count"] = 0; payload["markets_with_quote"] = 0
        return payload
    except Exception as exc:
        return {
            "schema": "warroom.v99.execution_quotes.v1", "markets": {m: {} for m in MARKETS},
            "quote_count": 0, "markets_with_quote": 0, "manifest_valid": False,
            "failures": [{"error": f"{type(exc).__name__}: {exc}"}],
        }


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
    del start, fetch_live_feeds, fast_core, skip_slow_context, bootstrap_core
    if allow_synthetic:
        raise ValueError("Synthetic evidence is forbidden in the V9.9 runtime")
    selected = [m for m in (markets or MARKETS) if m in MARKETS]
    fred, fred_source, fred_status = load_fred_current_context(allow_live=allow_live)
    quotes = load_execution_quotes()
    public_sources = summarize_public_sources()
    universes = universe_summary()
    bundled = load_bundled_context()
    coverage = bundled.get("market_coverage") or {}
    sources = {}
    for m in selected:
        public_state = (public_sources.get("markets") or {}).get(m, {}).get("state", "ROUTE_ONLY")
        bundled_state = (coverage.get(m) or {}).get("state", "NO_DATA")
        sources[m] = {"bundled_research": bundled_state, "official_current_snapshot": public_state}
    sources["macro"] = {"current_fred": fred_source, "bundled_macro": (bundled.get("macro") or {}).get("macro_panel_state", "MISSING")}
    quote_markets = quotes.get("markets") if isinstance(quotes.get("markets"), dict) else {}
    bundled_present = int(((bundled.get("inventory") or {}).get("datasets_present") or 0))
    current_available = bool(fred or any(bool((quote_markets.get(m) or {})) for m in selected) or public_sources.get("markets_with_real_snapshot"))
    return {
        "markets": selected,
        "fred": fred,
        "fred_source": fred_source,
        "feeds": {
            "public_sources": public_sources,
            "execution_quotes": quotes,
            "bundled_research": bundled,
            "_status": {"fred": fred_status, "public_sources": {m: sources[m]["official_current_snapshot"] for m in selected}, "bundled_datasets_present": bundled_present, "_policy": "NONTECHNICAL_RESEARCH_AND_EXECUTION_REFERENCE_ONLY"},
        },
        "quotes": quotes,
        "public_sources": public_sources,
        "bundled_research": bundled,
        "universe_summary": universes,
        "sources": sources,
        "overall_source": "BUNDLED_RESEARCH_PLUS_CURRENT_CONTEXT" if current_available and bundled_present else "BUNDLED_RESEARCH_AVAILABLE" if bundled_present else "ROUTES_ONLY",
        "policy": {
            "technical_features": "FORBIDDEN",
            "synthetic_data": "FORBIDDEN",
            "price_role": "HISTORICAL_OUTCOME_OR_CURRENT_EXECUTION_REFERENCE_ONLY",
            "capital_permission": "BLOCKED_UNTIL_EXACT_PROOF_AND_HUMAN_APPROVAL",
            "research_data_and_capital_permission_are_separate": True,
        },
    }
