"""data/loader.py — Tiered Universe Price Loader v4.1 (Sprint 5)

UPGRADES vs v4:
  • COMPANY NAME → TICKER mapping (TSMC → TSM, FANUC → 6954.T, etc.)
  • ENHANCED blacklist (company short names auto-stripped)
  • Yahoo backoff with persistent rate-limit state (30s skip after 429)
  • Tier 1 cache TTL extended to 4h (Tier 2 still 12h)
"""
from __future__ import annotations

import os
import time
import json
import math
import logging
import threading
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# ── Cache dirs ────────────────────────────────────────────────────────────
CACHE_DIR = Path(".cache/prices_v4")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["YFINANCE_CACHE_DIR"] = ".cache/yfinance"
Path(".cache/yfinance").mkdir(parents=True, exist_ok=True)

import yfinance as yf

# ── Streamlit secrets compat ──────────────────────────────────────────────
def _get_secret(key: str) -> Optional[str]:
    try:
        import streamlit as st
        v = st.secrets.get(key, None)
        if v:
            return str(v)
    except Exception:
        pass
    return os.environ.get(key, None)


POLYGON_API_KEY = _get_secret("POLYGON_API_KEY")

# ────────────────────────────────────────────────────────────────────────
# COMPANY NAME → REAL TICKER MAPPING
# Sources: bottleneck_reference.json + narrative_universe.py company refs
# ────────────────────────────────────────────────────────────────────────

NAME_TO_TICKER: Dict[str, str] = {
    # Semis - non-US
    "TSMC": "TSM",                # Taiwan Semi US ADR
    "SAMSUNG": "005930.KS",       # Samsung Electronics Korea
    "SAMSUNG ELECTRONICS": "005930.KS",
    "SK HYNIX": "000660.KS",
    "MEDIATEK": "2454.TW",
    # Japan industrials/tech
    "FANUC": "6954.T",
    "KEYENCE": "6861.T",
    "YASKAWA": "6506.T",
    "FUJIBO": "3104.T",           # Fujibo Holdings
    "HARMONIC DRIVE": "6324.T",
    "NABTESCO": "6268.T",
    "THK": "6481.T",
    "SMC": "6273.T",
    "NIDEC": "6594.T",
    # Optics / photonics
    "SYTECH": None,               # private, skip
    "SIPHONICS": None,            # private, skip
    "CELESTIAL AI": None,         # private
    "JEN": None,                  # ambiguous - skip
    "RPI": None,                  # research institution
    "BESI": "BESI.AS",            # BE Semiconductor Industries Amsterdam
    "AMEC": "AMEC.SS",            # Advanced Micro-Fabrication Equipment China
    "TUC": None,                  # Tucker (Ferro Mfg)
    "LPK": None,                  # ambiguous
    "ELSFPS": None,               # private
    "SIVE": None,                 # private
    "SMHN": None,                 # private/regional
    "POET": "POET",               # POET Technologies (already US ticker)
    # US giants with name
    "LINDE": "LIN",
    "SEAGATE": "STX",
    "AIR PRODUCTS": "APD",
    # Helium plays
    "HELIUM ONE": "HE1.L",        # London
    "PULSAR HELIUM": "PLSR.V",    # Canadian
    "ASIA METAL": None,
    # Misc bottleneck names
    "VVIX": "^VVIX",              # Yahoo wants ^VVIX
    "VIX": "^VIX",
    "MOVE": "^MOVE",
}


def _normalize_ticker(t: str) -> Optional[str]:
    """Map company names to real tickers, or return None if unmappable."""
    if not t:
        return None
    t_up = t.strip().upper()
    if t_up in NAME_TO_TICKER:
        return NAME_TO_TICKER[t_up]  # May be None (skip)
    return t_up  # Pass through


# ── Known-bad tickers (static + auto-blacklist) ───────────────────────────
KNOWN_BAD_TICKERS: Set[str] = {
    "VEX", "WDL", "JPXN", "EIS", "TUR", "NORW",
    "ZNC=F", "ALI=F", "LBS=F", "KOL", "JJN",
    # Crypto with CoinGecko numeric IDs
    "BONK-USD", "FLOKI-USD", "PEPE24478-USD",
    "UNI7083-USD", "COMP5692-USD",
    "GRT6719-USD", "SUI20947-USD",
    "TAO22974-USD", "TIA22861-USD", "TON11419-USD",
    # Recently delisted/bad
    "NXTECH", "ISWAVE", "UNRAND", "FOSER", "MARCH", "ETMS", "BTHC",
    "NIPPONS", "IMI", "BSF", "BUFI", "LRMK", "RYTICK",
    # Company names that snuck in as tickers from screenshot
    "SIPHONICS", "FANUC", "KEYENCE", "NABTESCO", "SYTECH", "TSMC",
    "ELSFPS", "RPI", "SAMSUNG", "YASKAWA", "AMEC", "SIVE",
    "FUJIBO", "SEAGATE", "TUC", "LINDE", "BESI", "THK", "LPK",
    "JEN", "SMHN", "AIR PRODUCTS", "ASIA METAL", "HARMONIC DRIVE",
    "CELESTIAL AI", "HELIUM ONE", "PULSAR HELIUM", "SK HYNIX",
    # VVIX without caret (yfinance needs ^VVIX)
    "VVIX",  # only ^VVIX works
}


_RUNTIME_BAD_TICKERS: Set[str] = set()
_RUNTIME_BAD_LOCK = threading.Lock()
_BLACKLIST_FILE = CACHE_DIR / "runtime_bad_tickers.json"

# Rate limit state — skip Yahoo for X seconds after 429
_RATE_LIMIT_UNTIL = 0.0
_RATE_LIMIT_LOCK = threading.Lock()


def _is_rate_limited() -> bool:
    return time.time() < _RATE_LIMIT_UNTIL


def _set_rate_limit(seconds: float = 30.0):
    global _RATE_LIMIT_UNTIL
    with _RATE_LIMIT_LOCK:
        _RATE_LIMIT_UNTIL = max(_RATE_LIMIT_UNTIL, time.time() + seconds)
    logger.warning(f"Yahoo rate-limit cooldown: pausing yfinance for {seconds}s")


def _load_runtime_blacklist():
    global _RUNTIME_BAD_TICKERS
    try:
        if _BLACKLIST_FILE.exists():
            with open(_BLACKLIST_FILE) as f:
                data = json.load(f)
            cutoff = (datetime.now() - timedelta(days=7)).timestamp()
            _RUNTIME_BAD_TICKERS = {t for t, ts in data.items() if ts > cutoff}
    except Exception:
        _RUNTIME_BAD_TICKERS = set()


def _save_runtime_blacklist():
    try:
        existing = {}
        if _BLACKLIST_FILE.exists():
            with open(_BLACKLIST_FILE) as f:
                existing = json.load(f)
        now = datetime.now().timestamp()
        for t in _RUNTIME_BAD_TICKERS:
            existing[t] = now
        with open(_BLACKLIST_FILE, "w") as f:
            json.dump(existing, f)
    except Exception:
        pass


def _mark_bad(ticker: str):
    with _RUNTIME_BAD_LOCK:
        _RUNTIME_BAD_TICKERS.add(ticker)


_load_runtime_blacklist()


def _is_bad(ticker: str) -> bool:
    return ticker in KNOWN_BAD_TICKERS or ticker in _RUNTIME_BAD_TICKERS


# ── Tier classification ───────────────────────────────────────────────────
TIER_CORE = {
    "SPY", "QQQ", "IWM", "DIA", "^VIX", "DX-Y.NYB", "GC=F", "SI=F",
    "CL=F", "BZ=F", "HG=F", "NG=F",
    "TLT", "IEF", "SHY", "HYG", "LQD", "TIP",
    "XLK", "XLE", "XLF", "XLV", "XLI", "XLB", "XLY", "XLP", "XLU", "XLRE", "XLC",
    "GLD", "SLV", "GDX", "USO", "UNG", "UUP",
    "BTC-USD", "ETH-USD",
    "EURUSD=X", "USDJPY=X", "GBPUSD=X", "USDIDR=X", "AUDUSD=X",
    "^JKSE", "EIDO", "BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK",
    "NVDA", "AAPL", "MSFT", "AMZN", "META", "GOOGL", "TSLA", "AVGO", "AMD",
}


# ── Retry helpers ─────────────────────────────────────────────────────────
def _retry_call(func, *args, max_attempts=2, base_delay=2.0, **kwargs):
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            is_rate = "too many requests" in err_str or "429" in err_str or "rate" in err_str
            is_timeout = "timeout" in err_str or "timed out" in err_str
            if is_rate:
                _set_rate_limit(60.0)
                raise
            if not (is_timeout or "failed" in err_str):
                raise
            delay = base_delay * (2 ** (attempt - 1))
            time.sleep(delay)
    raise last_err


# ── Cache helpers ─────────────────────────────────────────────────────────
def _hash_tickers(tickers: List[str]) -> str:
    import hashlib
    return hashlib.md5(",".join(sorted(tickers)).encode()).hexdigest()[:12]


def _cache_path(key: str, days: int) -> Path:
    return CACHE_DIR / f"px_{key}_{days}d.parquet"


def _meta_path(key: str, days: int) -> Path:
    return CACHE_DIR / f"px_{key}_{days}d_meta.json"


def _load_cache(key: str, days: int, max_age_hours: float) -> Optional[Dict[str, pd.Series]]:
    cp = _cache_path(key, days)
    mp = _meta_path(key, days)
    if not cp.exists() or not mp.exists():
        return None
    try:
        with open(mp) as f:
            meta = json.load(f)
        cached_at = datetime.fromisoformat(meta["cached_at"])
        age_hours = (datetime.now() - cached_at).total_seconds() / 3600
        if age_hours > max_age_hours:
            return None
        df = pd.read_parquet(cp)
        return {c: df[c].dropna() for c in df.columns if len(df[c].dropna()) > 0}
    except Exception:
        return None


def _load_cache_stale(key: str, days: int) -> Optional[Dict[str, pd.Series]]:
    cp = _cache_path(key, days)
    if not cp.exists():
        return None
    try:
        df = pd.read_parquet(cp)
        return {c: df[c].dropna() for c in df.columns if len(df[c].dropna()) > 0}
    except Exception:
        return None


def _save_cache(key: str, days: int, data: Dict[str, pd.Series]):
    try:
        df = pd.DataFrame(data)
        df.to_parquet(_cache_path(key, days), compression="zstd")
        with open(_meta_path(key, days), "w") as f:
            json.dump({"cached_at": datetime.now().isoformat(), "tickers": list(data.keys())}, f)
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")


# ── Source 1: yfinance batch ──────────────────────────────────────────────
def _fetch_yf_batch(tickers: List[str], days: int = 756) -> pd.DataFrame:
    if _is_rate_limited():
        raise RuntimeError("yfinance rate-limit cooldown active")
    period = "2y" if days <= 500 else "5y"
    return _retry_call(
        yf.download,
        tickers=tickers,
        period=period,
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        prepost=False,
        threads=False,
        progress=False,
        max_attempts=2,
        base_delay=3.0,
    )


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


# ── Polygon fallback ──────────────────────────────────────────────────────
def _fetch_polygon_single(ticker: str, days: int = 756) -> Optional[pd.Series]:
    if not POLYGON_API_KEY:
        return None
    if "=" in ticker or "-USD" in ticker or "." in ticker or "^" in ticker:
        return None
    try:
        import requests
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days + 30)).strftime("%Y-%m-%d")
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}"
        params = {"apiKey": POLYGON_API_KEY, "adjusted": "true", "sort": "asc", "limit": 5000}
        r = requests.get(url, params=params, timeout=8)
        if r.status_code != 200:
            return None
        data = r.json()
        results = data.get("results", [])
        if not results:
            return None
        df = pd.DataFrame(results)
        df["date"] = pd.to_datetime(df["t"], unit="ms")
        return pd.Series(df["c"].values, index=df["date"], name=ticker).dropna()
    except Exception:
        return None


def _safe_progress(cb, msg: str, pct: float):
    if cb is None:
        return
    try:
        cb(msg, float(pct))
    except Exception:
        pass


# ── Public: load_prices ──────────────────────────────────────────────────
def load_prices(tickers: List[str], days: int = 756,
                max_age_hours: float = 12.0,
                progress_cb=None) -> Dict[str, pd.Series]:
    if not tickers:
        return {}

    # STEP 1: Normalize (company names → tickers, OR None to skip)
    normalized = []
    skipped_unmappable = []
    for t in tickers:
        norm = _normalize_ticker(t)
        if norm is None:
            skipped_unmappable.append(t)
            continue
        normalized.append(norm)

    if skipped_unmappable:
        logger.info(f"Skipped {len(skipped_unmappable)} unmappable names: {skipped_unmappable[:8]}")

    # STEP 2: Dedupe + filter blacklist
    clean = []
    seen = set()
    skipped_bl = []
    for t in normalized:
        if t in seen:
            continue
        seen.add(t)
        if _is_bad(t):
            skipped_bl.append(t)
            continue
        clean.append(t)

    if skipped_bl:
        logger.info(f"Skipped {len(skipped_bl)} blacklisted tickers")

    tickers_key = _hash_tickers(clean)

    # STEP 3: Try fresh cache
    cached = _load_cache(tickers_key, days, max_age_hours)
    if cached is not None and len(cached) > len(clean) * 0.6:
        _safe_progress(progress_cb, "Loaded from price cache", 0.55)
        logger.info(f"Cache HIT: {len(cached)} series")
        return cached

    # STEP 4: Tier split
    core = [t for t in clean if t in TIER_CORE]
    secondary = [t for t in clean if t not in TIER_CORE]

    _safe_progress(progress_cb, f"Tier 1: Core ({len(core)} tickers)...", 0.10)
    all_data: Dict[str, pd.Series] = {}

    if core:
        all_data.update(_fetch_tier(core, days, batch_size=15))
        _safe_progress(progress_cb, f"Tier 1 done: {len(all_data)}/{len(core)}", 0.30)

    if secondary and not _is_rate_limited():
        _safe_progress(progress_cb, f"Tier 2: Secondary ({len(secondary)})...", 0.32)
        sec_data = _fetch_tier(secondary, days, batch_size=20)
        all_data.update(sec_data)
        _safe_progress(progress_cb, f"Tier 2 done: {len(sec_data)}/{len(secondary)}", 0.52)
    elif _is_rate_limited():
        logger.warning("Skipping Tier 2 — rate limit active")

    # Save cache if we have a meaningful amount
    if len(all_data) > max(len(clean) * 0.5, 10):
        _save_cache(tickers_key, days, all_data)
    elif len(all_data) == 0:
        stale = _load_cache_stale(tickers_key, days)
        if stale:
            logger.warning("Live fetch returned 0 — using STALE cache")
            return stale

    _save_runtime_blacklist()

    loaded, total = len(all_data), len(clean)
    if loaded < total:
        logger.warning(f"Missing prices for {total - loaded} tickers (auto-blacklisted)")

    _safe_progress(progress_cb, f"Prices ready: {loaded}/{total}", 0.55)
    return all_data


def _fetch_tier(tickers: List[str], days: int, batch_size: int = 20) -> Dict[str, pd.Series]:
    out: Dict[str, pd.Series] = {}
    total_batches = math.ceil(len(tickers) / batch_size)

    for i in range(total_batches):
        if _is_rate_limited():
            logger.warning(f"Stopping tier fetch — rate-limited at batch {i+1}/{total_batches}")
            break

        batch = tickers[i * batch_size:(i + 1) * batch_size]
        try:
            df = _fetch_yf_batch(batch, days)
            batch_data = _extract_close(df, batch)
            out.update(batch_data)
            missing = [t for t in batch if t not in batch_data]

            # Try Polygon for missing US tickers
            if missing and POLYGON_API_KEY and not _is_rate_limited():
                for t in missing[:3]:
                    s = _fetch_polygon_single(t, days)
                    if s is not None and len(s) > 10:
                        out[t] = s
                    else:
                        _mark_bad(t)
            else:
                for t in missing:
                    _mark_bad(t)
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "rate" in err or "too many" in err:
                logger.warning(f"Rate limit hit batch {i+1} — aborting remaining batches")
                _set_rate_limit(60.0)
                break
            else:
                logger.error(f"Batch {i+1} failed: {e}")
                for t in batch:
                    if t not in out:
                        _mark_bad(t)

        if i < total_batches - 1:
            time.sleep(0.5)

    return out


# ── Snapshot persistence (unchanged) ──────────────────────────────────────
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
        if not SNAP_PATH.exists() or not SNAP_PATH.with_suffix(".pkl").exists():
            return None
        with open(SNAP_PATH) as f:
            meta = json.load(f)
        saved_at = datetime.fromisoformat(meta["saved_at"])
        age = (datetime.now() - saved_at).total_seconds() / 3600
        if age > max_age_hours:
            return None
        with open(SNAP_PATH.with_suffix(".pkl"), "rb") as f:
            return pickle.load(f)
    except Exception:
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
