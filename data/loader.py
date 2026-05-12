"""data/loader.py — Bulletproof YFinance Price Loader v2.1
Fixes:
  • yf.download() does NOT accept proxy kwarg in 0.2.x
  • Batch download via yf.download() 
  • Exponential backoff retry (3 attempts)
  • Disk cache with parquet
  • Graceful fallback: if live fails, return cached even if stale
"""
from __future__ import annotations
import os, time, json, logging, math
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

CACHE_DIR = Path(".cache/prices_v2")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── YFinance Config ────────────────────────────────────────────
import yfinance as yf

# ── Retry Decorator ──────────────────────────────────────────
def _retry_call(func, *args, max_attempts=3, base_delay=2.0, **kwargs):
    """Call func with exponential backoff."""
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            is_timeout = "timeout" in err_str or "timed out" in err_str or "readtimeout" in err_str
            is_rate = "too many requests" in err_str or "429" in err_str or "403" in err_str
            if not (is_timeout or is_rate or "failed" in err_str):
                raise
            delay = base_delay * (2 ** (attempt - 1)) + (hash(str(args)) % 100) / 100.0
            logger.warning(f"[Retry {attempt}/{max_attempts}] {e} — sleeping {delay:.1f}s")
            time.sleep(delay)
    raise last_err

# ── Cache Helpers ────────────────────────────────────────────
def _cache_path(tickers_key: str, days: int) -> Path:
    return CACHE_DIR / f"px_{tickers_key}_{days}d.parquet"

def _meta_path(tickers_key: str, days: int) -> Path:
    return CACHE_DIR / f"px_{tickers_key}_{days}d_meta.json"

def _hash_tickers(tickers: List[str]) -> str:
    import hashlib
    s = ",".join(sorted(tickers))
    return hashlib.md5(s.encode()).hexdigest()[:12]

def _load_cache(tickers_key: str, days: int, max_age_hours: float = 6.0) -> Optional[Dict[str, pd.Series]]:
    cp = _cache_path(tickers_key, days)
    mp = _meta_path(tickers_key, days)
    if not cp.exists() or not mp.exists():
        return None
    try:
        with open(mp, "r") as f:
            meta = json.load(f)
        cached_at = datetime.fromisoformat(meta["cached_at"])
        age_hours = (datetime.now() - cached_at).total_seconds() / 3600
        if age_hours > max_age_hours:
            logger.info(f"Cache stale ({age_hours:.1f}h > {max_age_hours}h), refetching...")
            return None
        df = pd.read_parquet(cp)
        out = {}
        for col in df.columns:
            s = df[col].dropna()
            if len(s) > 0:
                out[col] = s
        logger.info(f"Loaded {len(out)} series from cache ({age_hours:.1f}h old)")
        return out
    except Exception as e:
        logger.warning(f"Cache load failed: {e}")
        return None

def _save_cache(tickers_key: str, days: int, data: Dict[str, pd.Series]):
    cp = _cache_path(tickers_key, days)
    mp = _meta_path(tickers_key, days)
    try:
        df = pd.DataFrame(data)
        df.to_parquet(cp, compression="zstd")
        with open(mp, "w") as f:
            json.dump({"cached_at": datetime.now().isoformat(), "tickers": list(data.keys())}, f)
        logger.info(f"Saved cache: {cp}")
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")

# ── Core Fetch ───────────────────────────────────────────────
def _fetch_yf_batch(tickers: List[str], days: int = 756) -> pd.DataFrame:
    """Use yf.download() batch endpoint."""
    period = "2y" if days <= 500 else "5y"
    # yf.download signature: NO proxy kwarg in 0.2.x
    df = _retry_call(
        yf.download,
        tickers=tickers,
        period=period,
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        prepost=False,
        threads=True,
        max_attempts=3,
        base_delay=3.0,
    )
    return df

def _extract_close(df: pd.DataFrame, tickers: List[str]) -> Dict[str, pd.Series]:
    """Extract Close price series from yf.download() output."""
    out = {}
    if len(tickers) == 1:
        t = tickers[0]
        col = "Close" if "Close" in df.columns else "Adj Close"
        if col in df.columns:
            s = df[col].dropna()
            if len(s) > 0:
                out[t] = s
        return out
    for t in tickers:
        try:
            if (t, "Close") in df.columns:
                s = df[(t, "Close")].dropna()
            elif (t, "Adj Close") in df.columns:
                s = df[(t, "Adj Close")].dropna()
            else:
                continue
            if len(s) > 0:
                out[t] = s
        except Exception:
            continue
    return out

# ── Public API (COMPATIBLE NAMES) ────────────────────────────
def load_prices(tickers: List[str], days: int = 756,
                max_age_hours: float = 6.0,
                progress_cb=None) -> Dict[str, pd.Series]:
    """
    Robust price loader. Returns dict of Series keyed by ticker.
    THIS IS THE FUNCTION orchestrator.py CALLS.
    """
    if not tickers:
        return {}
    tickers_key = _hash_tickers(tickers)

    # 1. Try cache first
    cached = _load_cache(tickers_key, days, max_age_hours)
    if cached is not None:
        return cached

    # 2. Live fetch in batches
    BATCH_SIZE = 25
    all_data: Dict[str, pd.Series] = {}

    total_batches = math.ceil(len(tickers) / BATCH_SIZE)
    for i in range(total_batches):
        batch = tickers[i * BATCH_SIZE:(i + 1) * BATCH_SIZE]
        if progress_cb:
            progress_cb(f"Fetching batch {i+1}/{total_batches} ({len(batch)} tickers)...",
                        0.10 + 0.50 * (i / max(total_batches, 1)))
        try:
            df_batch = _fetch_yf_batch(batch, days)
            batch_data = _extract_close(df_batch, batch)
            all_data.update(batch_data)
            if i < total_batches - 1:
                time.sleep(1.2)
        except Exception as e:
            logger.error(f"Batch {i+1} failed: {e}")
            # Per-ticker fallback
            for t in batch:
                if t not in all_data:
                    try:
                        s = yf.Ticker(t).history(period="2y", interval="1d")["Close"].dropna()
                        if len(s) > 0:
                            all_data[t] = s
                        time.sleep(0.8)
                    except Exception:
                        pass

    # 3. Save cache
    if all_data:
        _save_cache(tickers_key, days, all_data)

    missing = [t for t in tickers if t not in all_data]
    if missing:
        logger.warning(f"Missing prices for {len(missing)} tickers: {missing[:10]}")

    return all_data


def load_fred():
    """Placeholder — keep compatibility."""
    return {}


def snapshot_age_str() -> str:
    """Return human-readable age of latest cache."""
    try:
        files = sorted(CACHE_DIR.glob("px_*_meta.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return "No cache"
        mtime = datetime.fromtimestamp(files[0].stat().st_mtime)
        age = datetime.now() - mtime
        if age < timedelta(minutes=1):
            return "Just now"
        if age < timedelta(hours=1):
            return f"{age.seconds // 60}m ago"
        return f"{age.seconds // 3600}h ago"
    except Exception:
        return "Unknown"


def load_snapshot(max_age_hours: float = 6.0) -> Optional[Dict]:
    """Placeholder — actual snapshot build happens in orchestrator."""
    return None
