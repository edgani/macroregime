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

_CACHE_PATH = Path(".price_cache.pkl")
_MEM: dict[tuple, tuple[float, dict[str, pd.DataFrame]]] = {}
_LOCK = Lock()
_MEM_TTL = int(os.getenv("WARROOM_PRICE_MEMORY_TTL", "55"))
_BATCH_SIZE = max(5, int(os.getenv("WARROOM_YF_BATCH_SIZE", "40")))


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
        )
        out = _extract_batch(raw, tickers)
    except Exception:
        out = {}

    # Retry only unresolved symbols. This preserves batch speed while handling Yahoo partial failures.
    missing = [ticker for ticker in tickers if ticker not in out]
    for ticker in missing[: max(8, len(tickers) // 4)]:
        try:
            raw = yf.download(
                tickers=ticker,
                period=_period(days),
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            frame = _normalize_frame(raw)
            if frame is not None:
                out[ticker] = frame
        except Exception:
            continue
    return out


def load_bundle(tickers: Iterable[str], days: int = 756, progress_cb=None) -> dict[str, pd.DataFrame]:
    names = _clean_tickers(tickers)
    key = (tuple(names), int(days))
    now = time.time()
    with _LOCK:
        cached = _MEM.get(key)
        if cached and now - cached[0] <= _MEM_TTL:
            return {ticker: frame.copy(deep=False) for ticker, frame in cached[1].items()}

    combined: dict[str, pd.DataFrame] = {}
    total = max(1, len(names))
    for start in range(0, len(names), _BATCH_SIZE):
        chunk = names[start : start + _BATCH_SIZE]
        if progress_cb:
            progress_cb(f"Fetching {chunk[0]}…{chunk[-1]}", 0.1 + 0.8 * start / total)
        combined.update(_download_chunk(chunk, days))

    with _LOCK:
        _MEM[key] = (now, combined)
    return {ticker: frame.copy(deep=False) for ticker, frame in combined.items()}


def load_prices(tickers, days=756, max_age_hours=12.0, progress_cb=None):
    bundle = load_bundle(tickers, days=days, progress_cb=progress_cb)
    return {ticker: frame["Close"].dropna() for ticker, frame in bundle.items() if "Close" in frame}


def load_ohlcv(tickers, days=756):
    return load_bundle(tickers, days=days)


def load_snapshot(max_age_hours=12.0):
    if not _CACHE_PATH.exists():
        return None
    try:
        age_hours = (datetime.now().timestamp() - _CACHE_PATH.stat().st_mtime) / 3600
        if age_hours > max_age_hours:
            return None
        with _CACHE_PATH.open("rb") as handle:
            return pickle.load(handle)
    except Exception:
        return None


def save_snapshot(obj):
    try:
        with _CACHE_PATH.open("wb") as handle:
            pickle.dump(obj, handle)
    except Exception:
        pass


def snapshot_age_str():
    if not _CACHE_PATH.exists():
        return "no cache"
    try:
        age = datetime.now().timestamp() - _CACHE_PATH.stat().st_mtime
        if age < 60:
            return f"{int(age)}s ago"
        if age < 3600:
            return f"{int(age / 60)}m ago"
        return f"{int(age / 3600)}h ago"
    except Exception:
        return "unknown"
