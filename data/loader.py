"""Fast Yahoo market loader used by War Room OS.

One network download now returns both Close and OHLCV. The previous implementation downloaded
one ticker at a time twice (once for prices and once for OHLCV), which was the main reason a
Streamlit rerun could take minutes for large universes.

Production behavior remains honest: failed symbols stay missing; no synthetic fallback is emitted.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, Tuple
import os
import pickle
import time

import pandas as pd
import yfinance as yf

_HERE = Path(__file__).resolve().parents[1]
_CACHE_PATH = _HERE / ".cache" / "price_cache.pkl"
_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Yahoo changed/uses non-intuitive canonical symbols for several instruments. Keep the
# War Room display key stable while querying the provider with its canonical symbol.
YAHOO_ALIASES = {
    "USDJPY=X": "JPY=X",
    "USDIDR=X": "IDR=X",
    "UNI7083-USD": "UNI-USD",
    "COMP5692-USD": "COMP-USD",
    "TON11419-USD": "TON-USD",
    "TAO22974-USD": "TAO-USD",
}

_MEM: dict[tuple, tuple[float, dict[str, pd.DataFrame]]] = {}
_LOCK = Lock()
_MEM_TTL = int(os.getenv("WARROOM_PRICE_MEMORY_TTL", "55"))
_BATCH_SIZE = max(5, int(os.getenv("WARROOM_YF_BATCH_SIZE", "40")))
_DISK_TTL = max(60, int(os.getenv("WARROOM_PRICE_DISK_TTL", "300")))
_DISK_CACHE: dict[str, tuple[float, pd.DataFrame]] | None = None


def _clean_tickers(tickers: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in tickers or []:
        ticker = str(value or "").strip()
        if ticker and ticker not in seen:
            seen.add(ticker)
            out.append(ticker)
    return out


def _period(days: int) -> str:
    # yfinance's named periods are more reliable than arbitrary "756d" on some endpoints.
    if days <= 90:
        return "3mo"
    if days <= 190:
        return "6mo"
    if days <= 380:
        return "1y"
    if days <= 760:
        return "3y"
    if days <= 1300:
        return "5y"
    return "10y"


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame | None:
    if frame is None or frame.empty:
        return None
    out = frame.copy()
    if isinstance(out.columns, pd.MultiIndex):
        # This helper receives one ticker slice, so collapse any remaining singleton level.
        out.columns = [c[0] if isinstance(c, tuple) else c for c in out.columns]
    wanted = ["Open", "High", "Low", "Close", "Volume"]
    if not all(c in out.columns for c in wanted):
        return None
    out = out[wanted].apply(pd.to_numeric, errors="coerce").dropna(how="all")
    if len(out) < 50:
        return None
    return out


def _extract_batch(raw: pd.DataFrame, tickers: list[str]) -> dict[str, pd.DataFrame]:
    result: dict[str, pd.DataFrame] = {}
    if raw is None or raw.empty:
        return result
    if len(tickers) == 1:
        frame = _normalize_frame(raw)
        if frame is not None:
            result[tickers[0]] = frame
        return result

    if not isinstance(raw.columns, pd.MultiIndex):
        return result

    level0 = set(map(str, raw.columns.get_level_values(0)))
    level1 = set(map(str, raw.columns.get_level_values(1)))
    fields = {"Open", "High", "Low", "Close", "Volume"}
    ticker_first = bool(set(tickers) & level0)
    field_first = bool(fields & level0)
    for ticker in tickers:
        try:
            if ticker_first:
                frame = raw[ticker]
            elif field_first and ticker in level1:
                frame = raw.xs(ticker, axis=1, level=1)
            else:
                continue
            frame = _normalize_frame(frame)
            if frame is not None:
                result[ticker] = frame
        except Exception:
            continue
    return result


def _download_chunk(tickers: list[str], days: int) -> dict[str, pd.DataFrame]:
    if not tickers:
        return {}
    try:
        raw = yf.download(
            tickers=tickers,
            period=_period(days),
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
            group_by="ticker",
            timeout=max(3, int(os.getenv("WARROOM_YF_TIMEOUT", "10"))),
        )
        out = _extract_batch(raw, tickers)
    except Exception:
        out = {}

    # Retry only unresolved symbols. This preserves batch speed while handling Yahoo partial failures.
    missing = [ticker for ticker in tickers if ticker not in out]
    # A large unresolved universe used to trigger dozens of serial retries and stall Streamlit.
    # Retry a bounded number; the remaining symbols are reported missing and retried next cycle.
    retry_cap = max(0, int(os.getenv("WARROOM_YF_RETRY_CAP", "2")))
    for ticker in missing[:retry_cap]:
        try:
            raw = yf.download(
                tickers=ticker,
                period=_period(days),
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
                timeout=max(3, int(os.getenv("WARROOM_YF_TIMEOUT", "10"))),
            )
            frame = _normalize_frame(raw)
            if frame is not None:
                out[ticker] = frame
        except Exception:
            continue
    return out


def _load_disk_cache() -> dict[str, tuple[float, pd.DataFrame]]:
    global _DISK_CACHE
    if _DISK_CACHE is not None:
        return _DISK_CACHE
    try:
        if _CACHE_PATH.exists():
            raw = pickle.loads(_CACHE_PATH.read_bytes())
            if isinstance(raw, dict):
                _DISK_CACHE = raw
            else:
                _DISK_CACHE = {}
        else:
            _DISK_CACHE = {}
    except Exception:
        _DISK_CACHE = {}
    return _DISK_CACHE


def _save_disk_cache(cache: dict[str, tuple[float, pd.DataFrame]]) -> None:
    try:
        tmp = _CACHE_PATH.with_suffix('.tmp')
        tmp.write_bytes(pickle.dumps(cache, protocol=pickle.HIGHEST_PROTOCOL))
        tmp.replace(_CACHE_PATH)
    except Exception:
        pass


def load_bundle(tickers: Iterable[str], days: int = 756, progress_cb=None) -> dict[str, pd.DataFrame]:
    names = _clean_tickers(tickers)
    key = (tuple(names), int(days))
    now = time.time()
    with _LOCK:
        cached = _MEM.get(key)
        if cached and now - cached[0] <= _MEM_TTL:
            return {ticker: frame.copy(deep=False) for ticker, frame in cached[1].items()}

    # Resolve provider aliases but preserve the requested/display symbol in returned data.
    requested_to_provider = {name: YAHOO_ALIASES.get(name, name) for name in names}
    provider_to_requested: dict[str, list[str]] = {}
    for requested, provider in requested_to_provider.items():
        provider_to_requested.setdefault(provider, []).append(requested)

    disk = _load_disk_cache()
    provider_frames: dict[str, pd.DataFrame] = {}
    stale_or_missing: list[str] = []
    for provider in provider_to_requested:
        item = disk.get(provider)
        if item and now - float(item[0]) <= _DISK_TTL and isinstance(item[1], pd.DataFrame):
            provider_frames[provider] = item[1]
        else:
            stale_or_missing.append(provider)

    total = max(1, len(stale_or_missing))
    for start in range(0, len(stale_or_missing), _BATCH_SIZE):
        chunk = stale_or_missing[start : start + _BATCH_SIZE]
        if progress_cb and chunk:
            progress_cb(f"Fetching {chunk[0]}…{chunk[-1]}", 0.1 + 0.8 * start / total)
        fetched = _download_chunk(chunk, days)
        provider_frames.update(fetched)
        for provider, frame in fetched.items():
            disk[provider] = (now, frame)
    if stale_or_missing:
        _save_disk_cache(disk)

    combined: dict[str, pd.DataFrame] = {}
    for provider, requested_names in provider_to_requested.items():
        frame = provider_frames.get(provider)
        if frame is None:
            continue
        for requested in requested_names:
            combined[requested] = frame

    with _LOCK:
        _MEM[key] = (now, combined)
    return {ticker: frame.copy(deep=False) for ticker, frame in combined.items()}


def load_prices(tickers, days=756, max_age_hours=12.0, progress_cb=None):
    bundle = load_bundle(tickers, days=days, progress_cb=progress_cb)
    return {ticker: frame["Close"].dropna() for ticker, frame in bundle.items() if "Close" in frame}


def load_ohlcv(tickers, days=756):
    return load_bundle(tickers, days=days)


def load_snapshot(max_age_hours=12.0):
    legacy_path = _HERE / ".cache" / "legacy_snapshot.pkl"
    if not legacy_path.exists():
        return None
    try:
        age_hours = (datetime.now().timestamp() - legacy_path.stat().st_mtime) / 3600
        if age_hours > max_age_hours:
            return None
        with legacy_path.open("rb") as handle:
            return pickle.load(handle)
    except Exception:
        return None


def save_snapshot(obj):
    try:
        legacy_path = _HERE / ".cache" / "legacy_snapshot.pkl"
        with legacy_path.open("wb") as handle:
            pickle.dump(obj, handle)
    except Exception:
        pass


def snapshot_age_str():
    legacy_path = _HERE / ".cache" / "legacy_snapshot.pkl"
    if not legacy_path.exists():
        return "no cache"
    try:
        age = datetime.now().timestamp() - legacy_path.stat().st_mtime
        if age < 60:
            return f"{int(age)}s ago"
        if age < 3600:
            return f"{int(age / 60)}m ago"
        return f"{int(age / 3600)}h ago"
    except Exception:
        return "unknown"
