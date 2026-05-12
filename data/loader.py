"""data/loader.py — Bulletproof YFinance Price Loader v3.1
Fixes v3.1:
 • Added KOL, JJN to blacklist (delisted / illiquid)
 • yfinance TzCache fix: env var + mkdir before import
 • Batch size 50, sleep 0.3s (preserved from v3.0)
 • Stale cache fallback preserved
"""
from __future__ import annotations
import os, time, json, logging, math
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# ── Cache directory (MUST be defined before any function uses it) ────────────
CACHE_DIR = Path(".cache/prices_v2")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── CRITICAL: Fix yfinance cache dir BEFORE importing yfinance ───────────────
os.environ["YFINANCE_CACHE_DIR"] = ".cache/yfinance"
Path(".cache/yfinance").mkdir(parents=True, exist_ok=True)

import yfinance as yf

# ── Known-bad tickers: skip entirely, never fetch ─────────────────────────────
KNOWN_BAD_TICKERS = {
    # Delisted / renamed / never existed on Yahoo Finance
    "VEX", "WDL", "VIX",           # VIX without caret → ^VIX
    "JPXN", "EIS", "TUR", "NORW",  # sometimes 404 depending on region
    "ZNC=F", "ALI=F",              # low-liquidity futures often 404
    "LBS=F",                       # Lumber futures delisted
    "KOL", "JJN",                  # v3.1: KOL=delisted Coal ETF, JJN=illiquid Nickel ETN
    # Renamed / illiquid crypto on Yahoo
    "BONK-USD", "FLOKI-USD", "PEPE24478-USD",
    "UNI7083-USD", "COMP5692-USD",
    "GRT6719-USD", "SUI20947-USD",
    "TAO22974-USD", "TIA22861-USD",
    "TON11419-USD",
}

# ── Retry Decorator ────────────────────────────────────────────────────────────
def _retry_call(func, *args, max_attempts=3, base_delay=2.0, **kwargs):
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            is_timeout = "timeout" in err_str or "timed out" in err_str
            is_rate = "too many requests" in err_str or "429" in err_str or "403" in err_str
            if not (is_timeout or is_rate or "failed" in err_str):
                raise
            delay = base_delay * (2 ** (attempt - 1)) + (hash(str(args)) % 100) / 100.0
            logger.warning(f"[Retry {attempt}/{max_attempts}] {e} — sleeping {delay:.1f}s")
            time.sleep(delay)
    raise last_err

# ── Cache Helpers ──────────────────────────────────────────────────────────────
def _cache_path(tickers_key: str, days: int) -> Path:
    return CACHE_DIR / f"px_{tickers_key}_{days}d.parquet"

def _meta_path(tickers_key: str, days: int) -> Path:
    return CACHE_DIR / f"px_{tickers_key}_{days}d_meta.json"

def _hash_tickers(tickers: List[str]) -> str:
    import hashlib
    s = ",".join(sorted(tickers))
    return hashlib.md5(s.encode()).hexdigest()[:12]

def _load_cache(tickers_key: str, days: int, max_age_hours: float = 12.0) -> Optional[Dict[str, pd.Series]]:
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
        out = {col: df[col].dropna() for col in df.columns if len(df[col].dropna()) > 0}
        logger.info(f"Cache HIT: {len(out)} series ({age_hours:.1f}h old)")
        return out
    except Exception as e:
        logger.warning(f"Cache load failed: {e}")
        return None

def _load_cache_stale(tickers_key: str, days: int) -> Optional[Dict[str, pd.Series]]:
    """Load cache regardless of age — fallback when live fetch fails."""
    cp = _cache_path(tickers_key, days)
    if not cp.exists():
        return None
    try:
        df = pd.read_parquet(cp)
        return {col: df[col].dropna() for col in df.columns if len(df[col].dropna()) > 0}
    except Exception:
        return None

def _save_cache(tickers_key: str, days: int, data: Dict[str, pd.Series]):
    cp = _cache_path(tickers_key, days)
    mp = _meta_path(tickers_key, days)
    try:
        df = pd.DataFrame(data)
        df.to_parquet(cp, compression="zstd")
        with open(mp, "w") as f:
            json.dump({"cached_at": datetime.now().isoformat(), "tickers": list(data.keys())}, f)
        logger.info(f"Cache saved: {len(data)} series → {cp}")
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")

# ── Core Fetch ─────────────────────────────────────────────────────────────────
def _fetch_yf_batch(tickers: List[str], days: int = 756) -> pd.DataFrame:
    period = "2y" if days <= 500 else "5y"
    df = _retry_call(
        yf.download,
        tickers=tickers,
        period=period,
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        prepost=False,
        threads=True,
        progress=False,
        max_attempts=3,
        base_delay=3.0,
    )
    return df

def _extract_close(df: pd.DataFrame, tickers: List[str]) -> Dict[str, pd.Series]:
    out = {}
    if len(tickers) == 1:
        t = tickers[0]
        for col in ("Close", "Adj Close"):
            if col in df.columns:
                s = df[col].dropna()
                if len(s) > 0:
                    out[t] = s
                    break
        return out
    for t in tickers:
        try:
            if (t, "Close") in df.columns:
                s = df[(t, "Close")].dropna()
            elif (t, "Adj Close") in df.columns:
                s = df[(t, "Adj Close")].dropna()
            else:
                continue
            if len(s) > 5:
                out[t] = s
        except Exception:
            continue
    return out

# ── Public API ─────────────────────────────────────────────────────────────────
def load_prices(tickers: List[str], days: int = 756,
        max_age_hours: float = 12.0,
        progress_cb=None) -> Dict[str, pd.Series]:
    """
    Robust price loader. Returns dict of Series keyed by ticker.
    v3.1: blacklist filter + faster batching + stale-cache fallback.
    """
    if not tickers:
        return {}

    # Filter known-bad tickers before any network call
    clean = [t for t in tickers if t not in KNOWN_BAD_TICKERS]
    skipped = [t for t in tickers if t in KNOWN_BAD_TICKERS]
    if skipped:
        logger.info(f"Skipping {len(skipped)} blacklisted tickers: {skipped[:10]}")

    tickers_key = _hash_tickers(clean)

    # 1. Try fresh cache
    cached = _load_cache(tickers_key, days, max_age_hours)
    if cached is not None:
        return cached

    # 2. Live fetch — larger batches, shorter sleep
    BATCH_SIZE = 50
    all_data: Dict[str, pd.Series] = {}
    total_batches = math.ceil(len(clean) / BATCH_SIZE)

    for i in range(total_batches):
        batch = clean[i * BATCH_SIZE:(i + 1) * BATCH_SIZE]
        if progress_cb:
            progress_cb(
                f"Fetching prices {i+1}/{total_batches} ({len(batch)} tickers)…",
                0.10 + 0.45 * (i / max(total_batches, 1))
            )
        try:
            df_batch = _fetch_yf_batch(batch, days)
            batch_data = _extract_close(df_batch, batch)
            all_data.update(batch_data)
            missing = [t for t in batch if t not in batch_data]
            if missing:
                logger.warning(f"Batch {i+1}: no data for {missing}")
            if i < total_batches - 1:
                time.sleep(0.3)
        except Exception as e:
            logger.error(f"Batch {i+1} failed: {e}")
            for t in batch:
                if t not in all_data:
                    try:
                        s = yf.Ticker(t).history(period="2y", interval="1d", progress=False)["Close"].dropna()
                        if len(s) > 5:
                            all_data[t] = s
                            time.sleep(0.4)
                    except Exception:
                        pass

    # 3. Save fresh data if we got enough
    if len(all_data) > max(len(clean) * 0.5, 5):
        _save_cache(tickers_key, days, all_data)
    elif len(all_data) == 0:
        stale = _load_cache_stale(tickers_key, days)
        if stale:
            logger.warning("Live fetch failed — using STALE cache")
            return stale

    loaded = len(all_data); total = len(clean)
    if loaded < total:
        logger.warning(f"Missing prices for {total-loaded} tickers")

    return all_data

# ── Snapshot persistence ───────────────────────────────────────────────────────
SNAP_PATH = Path(".cache/snapshot_v3.json")
SNAP_PATH.parent.mkdir(parents=True, exist_ok=True)

def save_snapshot(snap: dict):
    try:
        import pickle
        with open(SNAP_PATH.with_suffix(".pkl"), "wb") as f:
            pickle.dump(snap, f)
        with open(SNAP_PATH, "w") as f:
            json.dump({"saved_at": datetime.now().isoformat(), "ok": snap.get("ok", False)}, f)
    except Exception as e:
        logger.warning(f"Snapshot save failed: {e}")

def load_snapshot(max_age_hours: float = 12.0) -> Optional[dict]:
    try:
        import pickle
        mp = SNAP_PATH
        pkl = SNAP_PATH.with_suffix(".pkl")
        if not mp.exists() or not pkl.exists():
            return None
        with open(mp) as f:
            meta = json.load(f)
        saved_at = datetime.fromisoformat(meta["saved_at"])
        age = (datetime.now() - saved_at).total_seconds() / 3600
        if age > max_age_hours:
            logger.info(f"Snapshot stale ({age:.1f}h)")
            return None
        with open(pkl, "rb") as f:
            snap = pickle.load(f)
        logger.info(f"Snapshot HIT ({age:.1f}h old)")
        return snap
    except Exception as e:
        logger.warning(f"Snapshot load failed: {e}")
        return None

def snapshot_age_str() -> str:
    try:
        if not SNAP_PATH.exists():
            return "No snapshot"
        with open(SNAP_PATH) as f:
            meta = json.load(f)
        saved_at = datetime.fromisoformat(meta["saved_at"])
        age_min = (datetime.now() - saved_at).total_seconds() / 60
        if age_min < 60:
            return f"{age_min:.0f}m ago"
        return f"{age_min/60:.1f}h ago"
    except Exception:
        return "Unknown"
