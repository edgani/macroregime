"""Resilient market-data layer for War Room OS v6.

Goals
-----
* Real data only: never synthesize decision-bearing market observations.
* Multi-provider cascade: yfinance -> direct Yahoo chart -> Binance/Stooq where applicable.
* Persistent last-known-good (LKG) cache with atomic writes.
* Per-ticker and per-market isolation: one failure never blanks the whole desk.
* Explicit freshness metadata. Cached/stale data is labelled, never presented as live.

This module is intended for research and monitoring. Yahoo/yfinance data may be delayed and is
not an exchange-grade execution feed. Binance public market-data endpoints are used only for
crypto prices and require no trading key.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
CACHE_ROOT = ROOT / ".cache" / "market_v7"
DAILY_DIR = CACHE_ROOT / "daily"
QUOTE_DIR = CACHE_ROOT / "quotes"
HEALTH_PATH = CACHE_ROOT / "feed_health.json"
for _p in (DAILY_DIR, QUOTE_DIR):
    _p.mkdir(parents=True, exist_ok=True)

DAILY_REFRESH_MINUTES = int(os.environ.get("WARROOM_DAILY_REFRESH_MINUTES", "30"))
QUOTE_REFRESH_SECONDS = int(os.environ.get("WARROOM_QUOTE_REFRESH_SECONDS", "180"))
REQUEST_TIMEOUT = float(os.environ.get("WARROOM_REQUEST_TIMEOUT", "5"))
YFINANCE_TIMEOUT = float(os.environ.get("WARROOM_YFINANCE_TIMEOUT", "8"))
RETRY_TOTAL = int(os.environ.get("WARROOM_RETRY_TOTAL", "1"))
MAX_WORKERS = int(os.environ.get("WARROOM_FEED_WORKERS", "12"))
MIN_BARS = 60

BINANCE_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]
YAHOO_CHART_BASES = [
    "https://query1.finance.yahoo.com/v8/finance/chart",
    "https://query2.finance.yahoo.com/v8/finance/chart",
]

STOOQ_COMMODITY_MAP = {
    "CL=F": "cl.f", "BZ=F": "co.f", "GC=F": "gc.f", "SI=F": "si.f",
    "HG=F": "hg.f", "NG=F": "ng.f",
}
CRYPTO_ALIASES = {
    "UNI7083": "UNI", "COMP5692": "COMP", "TON11419": "TON", "TAO22974": "TAO",
    "TIA22861": "TIA", "SUI20947": "SUI", "GRT6719": "GRT", "PEPE24478": "PEPE",
    "RENDER": "RENDER", "RNDR": "RENDER",
}


@dataclass
class TickerHealth:
    ticker: str
    market: str
    status: str
    provider: str
    fetched_at_utc: Optional[str]
    as_of: Optional[str]
    cache_age_hours: Optional[float]
    bars: int
    errors: list[str]


@dataclass
class MarketBundle:
    market: str
    frames: dict[str, pd.DataFrame]
    health: dict[str, TickerHealth]
    provider_counts: dict[str, int]
    live_count: int
    cache_fresh_count: int
    cache_stale_count: int
    missing_count: int
    requested_count: int
    generated_at_utc: str

    @property
    def source_summary(self) -> str:
        parts = []
        for key in ("yfinance", "yahoo_chart", "binance", "stooq", "cache_fresh", "cache_stale"):
            count = int(self.provider_counts.get(key, 0))
            if count:
                parts.append(f"{key}:{count}")
        return "resilient_v6 · " + (" · ".join(parts) if parts else "no data")

    @property
    def status(self) -> str:
        if self.live_count == self.requested_count and self.requested_count:
            return "LIVE_REFRESHED"
        if self.live_count or self.cache_fresh_count:
            return "READY_PARTIAL" if self.missing_count else "READY"
        if self.cache_stale_count:
            return "STALE_CACHE"
        return "MISSING"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z") if dt else None


def _safe_name(ticker: str) -> str:
    digest = hashlib.sha1(ticker.encode("utf-8")).hexdigest()[:12]
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", ticker)[:40]
    return f"{stem}__{digest}"


def _daily_paths(ticker: str) -> tuple[Path, Path]:
    stem = _safe_name(ticker)
    return DAILY_DIR / f"{stem}.pkl", DAILY_DIR / f"{stem}.json"


def _quote_path(ticker: str) -> Path:
    return QUOTE_DIR / f"{_safe_name(ticker)}.json"


def _atomic_bytes(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_bytes(path, json.dumps(payload, indent=2, sort_keys=True, default=str).encode("utf-8"))


def _save_frame(ticker: str, frame: pd.DataFrame, provider: str) -> None:
    if frame is None or frame.empty:
        return
    frame = _normalize_frame(frame)
    if frame.empty:
        return
    data_path, meta_path = _daily_paths(ticker)
    tmp = data_path.with_suffix(".pkl.tmp")
    frame.to_pickle(tmp)
    os.replace(tmp, data_path)
    _atomic_json(meta_path, {
        "ticker": ticker,
        "provider": provider,
        "fetched_at_utc": _iso(_utcnow()),
        "as_of": _iso(pd.Timestamp(frame.index.max()).to_pydatetime().replace(tzinfo=timezone.utc) if pd.Timestamp(frame.index.max()).tzinfo is None else pd.Timestamp(frame.index.max()).to_pydatetime()),
        "bars": int(len(frame)),
    })


def _load_frame_cache(ticker: str) -> tuple[Optional[pd.DataFrame], dict[str, Any]]:
    data_path, meta_path = _daily_paths(ticker)
    if not data_path.exists():
        return None, {}
    try:
        frame = _normalize_frame(pd.read_pickle(data_path))
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        return (frame if not frame.empty else None), meta
    except Exception:
        return None, {}


def _cache_age_hours(meta: dict[str, Any]) -> Optional[float]:
    try:
        fetched = pd.Timestamp(meta.get("fetched_at_utc"))
        if fetched.tzinfo is None:
            fetched = fetched.tz_localize("UTC")
        return max(0.0, float((_utcnow() - fetched.to_pydatetime()).total_seconds() / 3600.0))
    except Exception:
        return None


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    out = frame.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [c[0] if isinstance(c, tuple) else c for c in out.columns]
    ren = {str(c).strip().lower(): str(c) for c in out.columns}
    cols = {}
    for wanted in ("open", "high", "low", "close", "volume"):
        if wanted in ren:
            cols[ren[wanted]] = wanted.capitalize()
    out = out.rename(columns=cols)
    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col not in out.columns:
            out[col] = np.nan if col != "Volume" else 0.0
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out.index = pd.to_datetime(out.index, errors="coerce", utc=True).tz_convert(None)
    out = out[~out.index.isna()].sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out = out[["Open", "High", "Low", "Close", "Volume"]]
    out = out.dropna(subset=["Close"])
    for col in ("Open", "High", "Low"):
        out[col] = out[col].fillna(out["Close"])
    out["Volume"] = out["Volume"].fillna(0.0)
    return out


def _session() -> requests.Session:
    retry = Retry(
        total=RETRY_TOTAL, connect=RETRY_TOTAL, read=RETRY_TOTAL, status=RETRY_TOTAL,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WarRoomOS/5.0 research",
        "Accept": "application/json,text/csv,*/*",
    })
    session.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=16))
    return session


def _adjust_ohlc(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    if "Adj Close" in frame.columns and "Close" in frame.columns:
        raw = pd.to_numeric(frame["Close"], errors="coerce")
        adj = pd.to_numeric(frame["Adj Close"], errors="coerce")
        ratio = (adj / raw.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(1.0)
        for col in ("Open", "High", "Low", "Close"):
            if col in frame.columns:
                frame[col] = pd.to_numeric(frame[col], errors="coerce") * ratio
    return _normalize_frame(frame)


def _parse_yfinance_download(raw: pd.DataFrame, tickers: list[str]) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    if raw is None or raw.empty:
        return out
    if isinstance(raw.columns, pd.MultiIndex):
        lvl0 = set(map(str, raw.columns.get_level_values(0)))
        lvl1 = set(map(str, raw.columns.get_level_values(1)))
        if any(t in lvl0 for t in tickers):
            for ticker in tickers:
                if ticker in lvl0:
                    frame = _adjust_ohlc(raw[ticker].dropna(how="all"))
                    if len(frame) >= MIN_BARS:
                        out[ticker] = frame
        elif any(t in lvl1 for t in tickers):
            for ticker in tickers:
                if ticker in lvl1:
                    frame = _adjust_ohlc(raw.xs(ticker, axis=1, level=1).dropna(how="all"))
                    if len(frame) >= MIN_BARS:
                        out[ticker] = frame
    elif len(tickers) == 1:
        frame = _adjust_ohlc(raw)
        if len(frame) >= MIN_BARS:
            out[tickers[0]] = frame
    return out


def _fetch_yfinance_batch(tickers: list[str], days: int) -> tuple[dict[str, pd.DataFrame], list[str]]:
    errors: list[str] = []
    try:
        import yfinance as yf
        start = (_utcnow() - timedelta(days=max(days * 2, 1200))).date().isoformat()
        raw = yf.download(
            tickers=tickers,
            start=start,
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            repair=True,
            actions=False,
            threads=min(16, max(1, len(tickers))),
            progress=False,
            timeout=YFINANCE_TIMEOUT,
            multi_level_index=True,
        )
        return _parse_yfinance_download(raw, tickers), errors
    except Exception as exc:
        errors.append(f"yfinance:{type(exc).__name__}:{exc}")
        return {}, errors


def _fetch_yahoo_chart(ticker: str, days: int, interval: str = "1d") -> pd.DataFrame:
    session = _session()
    period2 = int(time.time()) + 60
    history_days = max(days * 3, 1200) if interval == "1d" else max(2, min(days, 7))
    period1 = period2 - history_days * 86400
    last_error = None
    for base in YAHOO_CHART_BASES:
        url = f"{base}/{quote(ticker, safe='')}"
        try:
            response = session.get(url, params={
                "period1": period1,
                "period2": period2,
                "interval": interval,
                "events": "div,splits",
                "includeAdjustedClose": "true",
            }, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            result = ((response.json().get("chart") or {}).get("result") or [None])[0]
            if not result:
                raise ValueError("empty chart result")
            timestamps = result.get("timestamp") or []
            quote_data = (((result.get("indicators") or {}).get("quote") or [{}])[0])
            adj_data = (((result.get("indicators") or {}).get("adjclose") or [{}])[0]).get("adjclose") or []
            if not timestamps:
                raise ValueError("no timestamps")
            frame = pd.DataFrame({
                "Open": quote_data.get("open", []),
                "High": quote_data.get("high", []),
                "Low": quote_data.get("low", []),
                "Close": quote_data.get("close", []),
                "Volume": quote_data.get("volume", []),
            }, index=pd.to_datetime(timestamps, unit="s", utc=True))
            if adj_data and len(adj_data) == len(frame):
                frame["Adj Close"] = adj_data
            frame = _adjust_ohlc(frame)
            if len(frame) < (2 if interval != "1d" else MIN_BARS):
                raise ValueError(f"insufficient bars:{len(frame)}")
            return frame
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Yahoo chart failed for {ticker}: {last_error}")


def _crypto_binance_symbol(ticker: str) -> Optional[str]:
    if not ticker.endswith("-USD"):
        return None
    base = ticker[:-4].upper()
    base = CRYPTO_ALIASES.get(base, base)
    base = re.sub(r"\d+$", "", base)
    if not re.fullmatch(r"[A-Z0-9]{2,15}", base):
        return None
    return base + "USDT"


def _fetch_binance_daily(ticker: str, days: int) -> pd.DataFrame:
    symbol = _crypto_binance_symbol(ticker)
    if not symbol:
        raise ValueError("not a Binance-mappable symbol")
    session = _session()
    last_error = None
    limit = min(1000, max(MIN_BARS, days))
    for base in BINANCE_BASES:
        try:
            response = session.get(f"{base}/api/v3/klines", params={
                "symbol": symbol, "interval": "1d", "limit": limit,
            }, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            rows = response.json()
            if not isinstance(rows, list) or len(rows) < MIN_BARS:
                raise ValueError(f"insufficient klines:{len(rows) if isinstance(rows,list) else 0}")
            frame = pd.DataFrame(rows, columns=[
                "open_time", "Open", "High", "Low", "Close", "Volume", "close_time",
                "quote_volume", "trades", "taker_base", "taker_quote", "ignore",
            ])
            frame.index = pd.to_datetime(frame["open_time"], unit="ms", utc=True)
            return _normalize_frame(frame[["Open", "High", "Low", "Close", "Volume"]])
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Binance failed for {ticker}: {last_error}")


def _stooq_symbol(ticker: str, market: str) -> Optional[str]:
    if market == "us" and re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", ticker):
        return ticker.lower().replace("-", ".") + ".us"
    if market == "fx" and ticker.endswith("=X"):
        return ticker[:-2].lower()
    if market == "fx" and ticker == "DX-Y.NYB":
        return "dx.f"
    if market == "commodity":
        return STOOQ_COMMODITY_MAP.get(ticker)
    return None


def _fetch_stooq(ticker: str, market: str, days: int) -> pd.DataFrame:
    symbol = _stooq_symbol(ticker, market)
    if not symbol:
        raise ValueError("no Stooq mapping")
    session = _session()
    end = _utcnow().date()
    start = end - timedelta(days=max(days * 3, 1200))
    url = "https://stooq.com/q/d/l/"
    response = session.get(url, params={
        "s": symbol, "d1": start.strftime("%Y%m%d"), "d2": end.strftime("%Y%m%d"), "i": "d",
    }, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    from io import StringIO
    frame = pd.read_csv(StringIO(response.text))
    if frame.empty or "Date" not in frame.columns:
        raise ValueError("empty Stooq response")
    frame.index = pd.to_datetime(frame.pop("Date"), utc=True)
    frame = _normalize_frame(frame)
    if len(frame) < MIN_BARS:
        raise ValueError(f"insufficient Stooq bars:{len(frame)}")
    return frame


def _merge_cache(old: Optional[pd.DataFrame], new: pd.DataFrame) -> pd.DataFrame:
    if old is None or old.empty:
        return _normalize_frame(new)
    merged = pd.concat([old, new]).sort_index()
    return _normalize_frame(merged[~merged.index.duplicated(keep="last")])


def _provider_fallback(ticker: str, market: str, days: int) -> tuple[Optional[pd.DataFrame], str, list[str]]:
    errors: list[str] = []
    providers = []
    if market == "crypto":
        providers.append(("binance", lambda: _fetch_binance_daily(ticker, days)))
    providers.append(("yahoo_chart", lambda: _fetch_yahoo_chart(ticker, days, "1d")))
    if market in {"us", "fx", "commodity"}:
        providers.append(("stooq", lambda: _fetch_stooq(ticker, market, days)))
    for name, fn in providers:
        try:
            frame = fn()
            return frame, name, errors
        except Exception as exc:
            errors.append(f"{name}:{type(exc).__name__}:{exc}")
    return None, "", errors


def load_market_bundle(
    tickers: Iterable[str],
    market: str,
    days: int = 756,
    force_refresh: bool = False,
) -> MarketBundle:
    tickers = list(dict.fromkeys(str(t).strip() for t in tickers if str(t).strip()))
    generated = _iso(_utcnow()) or ""
    frames: dict[str, pd.DataFrame] = {}
    health: dict[str, TickerHealth] = {}
    provider_counts: dict[str, int] = {}
    cached: dict[str, tuple[Optional[pd.DataFrame], dict[str, Any]]] = {t: _load_frame_cache(t) for t in tickers}

    fetch_list = []
    for ticker in tickers:
        frame, meta = cached[ticker]
        age = _cache_age_hours(meta)
        if force_refresh or frame is None or age is None or age * 60 >= DAILY_REFRESH_MINUTES:
            fetch_list.append(ticker)

    live_frames: dict[str, pd.DataFrame] = {}
    live_provider: dict[str, str] = {}
    errors_map: dict[str, list[str]] = {t: [] for t in tickers}

    # Primary provider in chunks to limit throttling and isolate failures.
    for i in range(0, len(fetch_list), 24):
        chunk = fetch_list[i:i + 24]
        if not chunk:
            continue
        batch, batch_errors = _fetch_yfinance_batch(chunk, days)
        for ticker, frame in batch.items():
            live_frames[ticker] = frame
            live_provider[ticker] = "yfinance"
        for ticker in chunk:
            errors_map[ticker].extend(batch_errors)
        if i + 24 < len(fetch_list):
            time.sleep(0.25 + random.random() * 0.2)

    missing_after_batch = [t for t in fetch_list if t not in live_frames]
    if missing_after_batch:
        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(missing_after_batch))) as pool:
            futures = {pool.submit(_provider_fallback, t, market, days): t for t in missing_after_batch}
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    frame, provider, errs = future.result()
                    errors_map[ticker].extend(errs)
                    if frame is not None and not frame.empty:
                        live_frames[ticker] = frame
                        live_provider[ticker] = provider
                except Exception as exc:
                    errors_map[ticker].append(f"fallback:{type(exc).__name__}:{exc}")

    # Persist live results and choose live/cache per ticker.
    for ticker in tickers:
        old_frame, old_meta = cached[ticker]
        if ticker in live_frames:
            merged = _merge_cache(old_frame, live_frames[ticker])
            provider = live_provider[ticker]
            _save_frame(ticker, merged, provider)
            frames[ticker] = merged.tail(max(days, MIN_BARS))
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
            health[ticker] = TickerHealth(
                ticker=ticker, market=market, status="LIVE_REFRESHED", provider=provider,
                fetched_at_utc=generated,
                as_of=_iso(pd.Timestamp(merged.index.max()).to_pydatetime().replace(tzinfo=timezone.utc)),
                cache_age_hours=0.0, bars=len(merged), errors=errors_map[ticker][-5:],
            )
            continue
        if old_frame is not None and not old_frame.empty:
            age = _cache_age_hours(old_meta)
            fresh_hours = 12 if market == "crypto" else 96
            status = "CACHE_FRESH" if age is not None and age <= fresh_hours else "CACHE_STALE"
            key = "cache_fresh" if status == "CACHE_FRESH" else "cache_stale"
            provider_counts[key] = provider_counts.get(key, 0) + 1
            frames[ticker] = old_frame.tail(max(days, MIN_BARS))
            health[ticker] = TickerHealth(
                ticker=ticker, market=market, status=status,
                provider=str(old_meta.get("provider") or "cache"),
                fetched_at_utc=old_meta.get("fetched_at_utc"),
                as_of=old_meta.get("as_of"), cache_age_hours=age,
                bars=len(old_frame), errors=errors_map[ticker][-5:],
            )
        else:
            health[ticker] = TickerHealth(
                ticker=ticker, market=market, status="MISSING", provider="none",
                fetched_at_utc=None, as_of=None, cache_age_hours=None, bars=0,
                errors=errors_map[ticker][-5:],
            )

    live_count = sum(h.status == "LIVE_REFRESHED" for h in health.values())
    cache_fresh_count = sum(h.status == "CACHE_FRESH" for h in health.values())
    cache_stale_count = sum(h.status == "CACHE_STALE" for h in health.values())
    missing_count = sum(h.status == "MISSING" for h in health.values())
    bundle = MarketBundle(
        market=market, frames=frames, health=health, provider_counts=provider_counts,
        live_count=live_count, cache_fresh_count=cache_fresh_count,
        cache_stale_count=cache_stale_count, missing_count=missing_count,
        requested_count=len(tickers), generated_at_utc=generated,
    )
    return bundle


def _load_quote_cache(ticker: str) -> Optional[dict[str, Any]]:
    path = _quote_path(ticker)
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except Exception:
        return None


def _save_quote_cache(ticker: str, payload: dict[str, Any]) -> None:
    _atomic_json(_quote_path(ticker), payload)


def _quote_age_seconds(payload: Optional[dict[str, Any]]) -> Optional[float]:
    if not payload:
        return None
    try:
        ts = pd.Timestamp(payload.get("fetched_at_utc"))
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        return max(0.0, (_utcnow() - ts.to_pydatetime()).total_seconds())
    except Exception:
        return None


def _fetch_binance_all_quotes(tickers: list[str]) -> dict[str, dict[str, Any]]:
    wanted = {t: _crypto_binance_symbol(t) for t in tickers}
    reverse = {v: k for k, v in wanted.items() if v}
    if not reverse:
        return {}
    session = _session()
    last_error = None
    for base in BINANCE_BASES:
        try:
            response = session.get(f"{base}/api/v3/ticker/price", timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            rows = response.json()
            now = _iso(_utcnow())
            out = {}
            for row in rows if isinstance(rows, list) else []:
                ticker = reverse.get(row.get("symbol"))
                if ticker:
                    out[ticker] = {
                        "ticker": ticker, "price": float(row["price"]), "as_of": now,
                        "fetched_at_utc": now, "provider": "binance", "status": "INTRADAY_FRESH",
                    }
            return out
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Binance quote endpoint failed: {last_error}")


def _fetch_yfinance_intraday(tickers: list[str]) -> dict[str, dict[str, Any]]:
    import yfinance as yf
    raw = yf.download(
        tickers=tickers, period="1d", interval="1m", prepost=True,
        auto_adjust=False, repair=True, progress=False, threads=min(16, max(1, len(tickers))),
        timeout=12, group_by="ticker", multi_level_index=True,
    )
    frames = _parse_yfinance_download(raw, tickers)
    # _parse_yfinance_download enforces MIN_BARS, not appropriate intraday. Parse manually if absent.
    out: dict[str, dict[str, Any]] = {}
    if raw is None or raw.empty:
        return out
    def consume(ticker: str, frame: pd.DataFrame):
        frame = _normalize_frame(frame)
        if frame.empty:
            return
        row = frame.iloc[-1]
        ts = pd.Timestamp(frame.index[-1])
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        now = _iso(_utcnow())
        out[ticker] = {
            "ticker": ticker, "price": float(row["Close"]), "as_of": _iso(ts.to_pydatetime()),
            "fetched_at_utc": now, "provider": "yfinance_intraday", "status": "INTRADAY_FRESH",
        }
    if isinstance(raw.columns, pd.MultiIndex):
        lvl0 = set(map(str, raw.columns.get_level_values(0)))
        lvl1 = set(map(str, raw.columns.get_level_values(1)))
        for ticker in tickers:
            try:
                if ticker in lvl0:
                    consume(ticker, raw[ticker])
                elif ticker in lvl1:
                    consume(ticker, raw.xs(ticker, axis=1, level=1))
            except Exception:
                continue
    elif len(tickers) == 1:
        consume(tickers[0], raw)
    return out


def _fetch_yahoo_quote(ticker: str) -> dict[str, Any]:
    frame = _fetch_yahoo_chart(ticker, days=2, interval="1m")
    row = frame.iloc[-1]
    ts = pd.Timestamp(frame.index[-1])
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    now = _iso(_utcnow())
    return {
        "ticker": ticker, "price": float(row["Close"]), "as_of": _iso(ts.to_pydatetime()),
        "fetched_at_utc": now, "provider": "yahoo_chart_intraday", "status": "INTRADAY_FRESH",
    }


def load_quotes(tickers: Iterable[str], market: str, force_refresh: bool = False) -> dict[str, dict[str, Any]]:
    tickers = list(dict.fromkeys(str(t) for t in tickers if t))
    out: dict[str, dict[str, Any]] = {}
    to_fetch = []
    for ticker in tickers:
        cached = _load_quote_cache(ticker)
        age = _quote_age_seconds(cached)
        if cached and not force_refresh and age is not None and age <= QUOTE_REFRESH_SECONDS:
            cached = dict(cached)
            cached["status"] = "INTRADAY_CACHE_FRESH"
            out[ticker] = cached
        else:
            to_fetch.append(ticker)

    fetched: dict[str, dict[str, Any]] = {}
    if to_fetch:
        if market == "crypto":
            try:
                fetched.update(_fetch_binance_all_quotes(to_fetch))
            except Exception:
                pass
        remaining = [t for t in to_fetch if t not in fetched]
        for i in range(0, len(remaining), 24):
            chunk = remaining[i:i + 24]
            try:
                fetched.update(_fetch_yfinance_intraday(chunk))
            except Exception:
                pass
        remaining = [t for t in to_fetch if t not in fetched]
        if remaining:
            with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(remaining))) as pool:
                futures = {pool.submit(_fetch_yahoo_quote, t): t for t in remaining}
                for future in as_completed(futures):
                    ticker = futures[future]
                    try:
                        fetched[ticker] = future.result()
                    except Exception:
                        continue

    for ticker, payload in fetched.items():
        _save_quote_cache(ticker, payload)
        out[ticker] = payload
    for ticker in tickers:
        if ticker in out:
            continue
        cached = _load_quote_cache(ticker)
        if cached:
            age = _quote_age_seconds(cached)
            cached = dict(cached)
            cached["status"] = "INTRADAY_CACHE_STALE"
            cached["cache_age_seconds"] = age
            out[ticker] = cached
    return out


def attach_quotes_to_desk(desk: dict[str, Any], force_refresh: bool = False) -> dict[str, Any]:
    market_alias = {"ihsg": "idx", "commod": "commodity"}
    total = fresh = stale = 0
    quote_sources: dict[str, int] = {}
    priority: dict[str, list[str]] = {}
    for ui_market, payload in (desk.get("markets") or {}).items():
        market = market_alias.get(ui_market, ui_market)
        tickers = [row.get("tk") for row in (payload.get("setups") or []) if row.get("tk") and row.get("valid")]
        priority[market] = tickers
        quotes = load_quotes(tickers, market, force_refresh=force_refresh) if tickers else {}
        for row in payload.get("setups") or []:
            q = quotes.get(row.get("tk"))
            if not q:
                row["quote_status"] = "MISSING"
                continue
            total += 1
            status = str(q.get("status") or "")
            if status in {"INTRADAY_FRESH", "INTRADAY_CACHE_FRESH"}:
                fresh += 1
            else:
                stale += 1
            provider = str(q.get("provider") or "unknown")
            quote_sources[provider] = quote_sources.get(provider, 0) + 1
            row["current_quote"] = q.get("price")
            row["quote_as_of"] = q.get("as_of")
            row["quote_provider"] = provider
            row["quote_status"] = status
    try:
        _atomic_json(CACHE_ROOT / "priority_tickers.json", priority)
    except Exception:
        pass
    meta = desk.setdefault("meta", {})
    meta["quote_total"] = total
    meta["quote_fresh"] = fresh
    meta["quote_stale"] = stale
    meta["quote_sources"] = quote_sources
    if fresh:
        meta["data_mode"] = "INTRADAY_QUOTE_PLUS_DAILY_MODEL" if fresh == total else "PARTIAL_INTRADAY_PLUS_DAILY_MODEL"
    elif stale:
        meta["data_mode"] = "STALE_INTRADAY_CACHE_PLUS_DAILY_MODEL"
    else:
        meta["data_mode"] = "DAILY_MODEL_ONLY"
    return desk


def write_health(bundles: dict[str, MarketBundle], extra: Optional[dict[str, Any]] = None) -> None:
    payload = {
        "generated_at_utc": _iso(_utcnow()),
        "markets": {
            market: {
                "status": bundle.status,
                "source_summary": bundle.source_summary,
                "requested": bundle.requested_count,
                "live": bundle.live_count,
                "cache_fresh": bundle.cache_fresh_count,
                "cache_stale": bundle.cache_stale_count,
                "missing": bundle.missing_count,
                "provider_counts": bundle.provider_counts,
                "tickers": {t: asdict(h) for t, h in bundle.health.items()},
            }
            for market, bundle in bundles.items()
        },
        "extra": extra or {},
    }
    _atomic_json(HEALTH_PATH, payload)


def read_health() -> dict[str, Any]:
    try:
        return json.loads(HEALTH_PATH.read_text(encoding="utf-8")) if HEALTH_PATH.exists() else {}
    except Exception:
        return {}
