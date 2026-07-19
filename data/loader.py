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
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import os
import pickle
import time

import numpy as np
import pandas as pd
import requests

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

_HTTP_TIMEOUT = max(2, int(os.getenv("WARROOM_PRICE_HTTP_TIMEOUT", "5")))
_HTTP_WORKERS = max(4, int(os.getenv("WARROOM_PRICE_HTTP_WORKERS", "16")))
_HTTP_HEADERS = {
    "User-Agent": os.getenv("WARROOM_PUBLIC_USER_AGENT", "Mozilla/5.0 WarRoomOS/2.7"),
    "Accept": "application/json,text/plain,*/*",
}


def _frame_from_yahoo_payload(payload: dict) -> pd.DataFrame | None:
    try:
        result = ((payload or {}).get("chart") or {}).get("result") or []
        if not result:
            return None
        item = result[0]
        timestamps = item.get("timestamp") or []
        quote = (((item.get("indicators") or {}).get("quote") or [{}])[0])
        adjusted = (((item.get("indicators") or {}).get("adjclose") or [{}])[0]).get("adjclose") or []
        if not timestamps or not quote:
            return None
        index = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None)
        frame = pd.DataFrame({
            "Open": quote.get("open"), "High": quote.get("high"), "Low": quote.get("low"),
            "Close": quote.get("close"), "Volume": quote.get("volume"),
        }, index=index)
        frame = frame.apply(pd.to_numeric, errors="coerce")
        if adjusted and len(adjusted) == len(frame):
            adj = pd.Series(pd.to_numeric(adjusted, errors="coerce"), index=frame.index)
            raw_close = frame["Close"].replace(0, np.nan)
            factor = (adj / raw_close).replace([np.inf, -np.inf], np.nan)
            for col in ("Open", "High", "Low", "Close"):
                frame[col] = frame[col] * factor
        return _normalize_frame(frame)
    except Exception:
        return None


def _stooq_symbol(provider: str) -> str | None:
    p = str(provider or "").upper()
    if p.endswith("-USD"):
        return None
    if p.endswith(".JK"):
        # Stooq coverage for Indonesia is incomplete but this is a harmless fallback.
        return p[:-3].lower() + ".id"
    if p == "^JKSE":
        return "^jkse"
    commodity = {
        "CL=F": "cl.f", "BZ=F": "co.f", "GC=F": "gc.f",
        "SI=F": "si.f", "HG=F": "hg.f", "NG=F": "ng.f",
        "DX-Y.NYB": "dx.f",
    }
    if p in commodity:
        return commodity[p]
    fx = {
        "EURUSD=X": "eurusd", "JPY=X": "usdjpy", "GBPUSD=X": "gbpusd",
        "AUDUSD=X": "audusd", "IDR=X": "usdidr",
    }
    if p in fx:
        return fx[p]
    if p.startswith("^") or any(ch in p for ch in "=/-"):
        return None
    return p.lower() + ".us"


def _download_stooq(provider: str) -> pd.DataFrame | None:
    symbol = _stooq_symbol(provider)
    if not symbol:
        return None
    try:
        url = "https://stooq.com/q/d/l/"
        response = requests.get(
            url, params={"s": symbol, "i": "d"}, headers=_HTTP_HEADERS,
            timeout=(2, max(3, _HTTP_TIMEOUT)),
        )
        if response.status_code != 200 or len(response.content) < 64:
            return None
        frame = pd.read_csv(io.BytesIO(response.content))
        if "Date" not in frame.columns:
            return None
        frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
        frame = frame.dropna(subset=["Date"]).set_index("Date")
        if "Volume" not in frame.columns:
            frame["Volume"] = 0.0
        return _normalize_frame(frame)
    except Exception:
        return None


def _download_crypto_public(provider: str, days: int) -> pd.DataFrame | None:
    if not str(provider).upper().endswith("-USD"):
        return None
    base = str(provider).upper()[:-4]
    limit = min(1000, max(120, int(days)))
    # Binance is fast when available; OKX is an independent no-key fallback.
    try:
        response = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": f"{base}USDT", "interval": "1d", "limit": limit},
            headers=_HTTP_HEADERS, timeout=(2, max(3, _HTTP_TIMEOUT)),
        )
        if response.status_code == 200:
            rows = response.json()
            if isinstance(rows, list) and len(rows) >= 50:
                frame = pd.DataFrame(rows, columns=[
                    "ts", "Open", "High", "Low", "Close", "Volume", "close_ts",
                    "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
                ])
                frame.index = pd.to_datetime(frame.pop("ts"), unit="ms", utc=True).tz_convert(None)
                return _normalize_frame(frame[["Open", "High", "Low", "Close", "Volume"]])
    except Exception:
        pass
    try:
        response = requests.get(
            "https://www.okx.com/api/v5/market/history-candles",
            params={"instId": f"{base}-USDT", "bar": "1D", "limit": min(300, limit)},
            headers=_HTTP_HEADERS, timeout=(2, max(3, _HTTP_TIMEOUT)),
        )
        if response.status_code == 200:
            rows = (response.json() or {}).get("data") or []
            if isinstance(rows, list) and len(rows) >= 50:
                frame = pd.DataFrame(rows, columns=[
                    "ts", "Open", "High", "Low", "Close", "Volume", "volCcy", "volQuote", "confirm",
                ])
                frame.index = pd.to_datetime(frame.pop("ts"), unit="ms", utc=True).tz_convert(None)
                frame = frame.sort_index()
                return _normalize_frame(frame[["Open", "High", "Low", "Close", "Volume"]])
    except Exception:
        pass
    return None


def _download_symbol_http(provider: str, days: int) -> pd.DataFrame | None:
    """Fetch one daily history from independent public endpoints with bounded timeouts.

    Provider order is asset-aware. Crypto uses exchange-native public APIs first. Other assets use
    Yahoo chart hosts and then Stooq as an independent fallback. Missing data stays missing.
    """
    provider = str(provider or "").strip()
    bootstrap = os.getenv("WARROOM_BOOTSTRAP_CORE", "0").strip().lower() in {"1", "true", "yes"}
    if provider.upper().endswith("-USD"):
        crypto = _download_crypto_public(provider, days)
        if crypto is not None:
            return crypto
        if bootstrap:
            return None

    period2 = int(time.time()) + 86400
    period1 = period2 - max(120, int(days) + 30) * 86400
    params = {
        "period1": period1, "period2": period2, "interval": "1d",
        "events": "history", "includeAdjustedClose": "true",
    }
    yahoo_hosts = ("query1.finance.yahoo.com",) if bootstrap else ("query1.finance.yahoo.com", "query2.finance.yahoo.com")
    for host in yahoo_hosts:
        try:
            response = requests.get(
                f"https://{host}/v8/finance/chart/{provider}", params=params,
                headers=_HTTP_HEADERS, timeout=(2, max(3, _HTTP_TIMEOUT)),
            )
            if response.status_code == 200:
                frame = _frame_from_yahoo_payload(response.json())
                if frame is not None:
                    return frame
        except Exception:
            continue
    return _download_stooq(provider)


def _download_many_http(providers: list[str], days: int) -> dict[str, pd.DataFrame]:
    result: dict[str, pd.DataFrame] = {}
    if not providers:
        return result
    with ThreadPoolExecutor(max_workers=min(_HTTP_WORKERS, len(providers))) as pool:
        futures = {pool.submit(_download_symbol_http, provider, days): provider for provider in providers}
        for future in as_completed(futures):
            provider = futures[future]
            try:
                frame = future.result()
            except Exception:
                frame = None
            if frame is not None:
                result[provider] = frame
    return result


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
        import yfinance as yf
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
        tmp = _CACHE_PATH.with_name(f"{_CACHE_PATH.name}.{os.getpid()}.tmp")
        payload = pickle.dumps(cache, protocol=pickle.HIGHEST_PROTOCOL)
        with open(tmp, "wb") as handle:
            handle.write(payload)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(tmp, _CACHE_PATH)
    except Exception:
        try:
            tmp.unlink()
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
    backend = os.getenv("WARROOM_PRICE_BACKEND", "http" if os.getenv("WARROOM_HOSTED_MODE") == "1" else "hybrid").strip().lower()
    unresolved = list(stale_or_missing)
    if backend in {"http", "hybrid"} and unresolved:
        if progress_cb:
            progress_cb(f"Fetching {len(unresolved)} symbols with bounded HTTP", 0.15)
        fetched = _download_many_http(unresolved, days)
        provider_frames.update(fetched)
        for provider, frame in fetched.items():
            disk[provider] = (now, frame)
        unresolved = [provider for provider in unresolved if provider not in fetched]

    enable_yf = os.getenv("WARROOM_ENABLE_YFINANCE_FALLBACK", "1" if backend != "http" else "0").strip().lower() in {"1", "true", "yes"}
    if enable_yf:
        for start in range(0, len(unresolved), _BATCH_SIZE):
            chunk = unresolved[start : start + _BATCH_SIZE]
            if progress_cb and chunk:
                progress_cb(f"Yahoo fallback {chunk[0]}…{chunk[-1]}", 0.45 + 0.45 * start / total)
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
