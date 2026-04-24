"""data/loader.py — Universal data loader with smart caching.

Architecture:
  1. Check snapshot cache (fast path — sub-second app open)
  2. Check file cache (< TTL — avoid API calls)
  3. Fetch from API (FRED / yfinance)
  4. Save to file cache

No blocking at app open. All heavy fetching is behind refresh button.
"""
from __future__ import annotations

import os
import time
import pickle
import hashlib
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

class Cache:
    def __init__(self, cache_dir: str = ".cache"):
        self.dir = Path(cache_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _key(self, name: str) -> Path:
        safe = hashlib.md5(name.encode()).hexdigest()[:12]
        return self.dir / f"{safe}.pkl"

    def get(self, name: str, ttl: int = 3600) -> Optional[object]:
        p = self._key(name)
        if p.exists() and (time.time() - p.stat().st_mtime) < ttl:
            try:
                with open(p, "rb") as f:
                    return pickle.load(f)
            except Exception:
                pass
        return None

    def set(self, name: str, value: object) -> None:
        p = self._key(name)
        try:
            with open(p, "wb") as f:
                pickle.dump(value, f)
        except Exception as e:
            logger.warning(f"Cache write failed for {name}: {e}")

    def clear(self, name: str) -> None:
        p = self._key(name)
        if p.exists():
            p.unlink()


_cache = Cache()

# ---------------------------------------------------------------------------
# FRED loader
# ---------------------------------------------------------------------------

def _load_fred_series(series_ids: List[str], months: int = 36) -> Dict[str, pd.Series]:
    """Load multiple FRED series. Returns dict of {series_id: pd.Series}."""
    from config.settings import FRED_API_KEY
    cache_key = f"fred_{'_'.join(sorted(series_ids))}_{months}"
    cached = _cache.get(cache_key, ttl=14400)  # 4hr TTL for macro data
    if cached is not None:
        return cached

    result: Dict[str, pd.Series] = {}

    if not FRED_API_KEY:
        logger.warning("FRED_API_KEY not set — using price proxies only")
        return result

    try:
        import fredapi
        fred = fredapi.Fred(api_key=FRED_API_KEY)
        end_date = pd.Timestamp.now()
        start_date = end_date - pd.DateOffset(months=months)

        for sid in series_ids:
            try:
                s = fred.get_series(sid, observation_start=start_date)
                if isinstance(s, pd.Series) and not s.empty:
                    result[sid] = pd.to_numeric(s, errors="coerce").dropna()
            except Exception as e:
                logger.debug(f"FRED {sid} failed: {e}")

    except ImportError:
        logger.warning("fredapi not installed — macro data limited to price proxies")
    except Exception as e:
        logger.warning(f"FRED load error: {e}")

    if result:
        _cache.set(cache_key, result)
    return result


def load_fred(months: int = 36) -> Dict[str, pd.Series]:
    """Load all configured FRED series."""
    from config.settings import (
        FRED_GROWTH_SERIES, FRED_INFLATION_SERIES,
        FRED_POLICY_SERIES,
    )
    all_ids = (
        list(FRED_GROWTH_SERIES.keys())
        + list(FRED_INFLATION_SERIES.keys())
        + list(FRED_POLICY_SERIES.keys())
    )
    return _load_fred_series(all_ids, months)


# ---------------------------------------------------------------------------
# Price loader (yfinance)
# ---------------------------------------------------------------------------

def load_prices(
    tickers: List[str],
    days: int = 756,
    ttl: int = 3600,
    return_ohlcv: bool = False,
) -> Dict[str, pd.Series | pd.DataFrame]:
    """
    Load closing prices (or full OHLCV frames) for a list of tickers.

    Returns: {ticker: pd.Series (close)} or {ticker: pd.DataFrame} if return_ohlcv.
    Stale tickers are silently skipped with a warning.
    """
    if not tickers:
        return {}

    cache_key = f"prices_{'_'.join(sorted(tickers))}_{days}_{return_ohlcv}"
    cached = _cache.get(cache_key, ttl=ttl)
    if cached is not None:
        return cached

    result: Dict[str, object] = {}

    try:
        import yfinance as yf
        period = f"{days}d"
        raw = yf.download(
            tickers, period=period, progress=False,
            auto_adjust=True, threads=True, timeout=30,
        )
        if raw.empty:
            return result

        # Handle single vs multi-ticker
        if len(tickers) == 1:
            t = tickers[0]
            close = pd.to_numeric(raw["Close"], errors="coerce").dropna()
            if return_ohlcv:
                result[t] = _extract_ohlcv(raw)
            else:
                result[t] = close
        else:
            for t in tickers:
                try:
                    if "Close" in raw.columns.get_level_values(0):
                        close_s = pd.to_numeric(raw["Close"][t], errors="coerce").dropna()
                    else:
                        close_s = pd.to_numeric(raw[t]["Close"], errors="coerce").dropna()
                    if close_s.empty:
                        continue
                    if return_ohlcv:
                        result[t] = _extract_ohlcv(raw, t)
                    else:
                        result[t] = close_s
                except Exception:
                    continue

    except Exception as e:
        logger.warning(f"Price load error: {e}")

    if result:
        _cache.set(cache_key, result)
    return result


def _extract_ohlcv(raw: pd.DataFrame, ticker: Optional[str] = None) -> pd.DataFrame:
    """Extract OHLCV DataFrame from yfinance multi-level or single output."""
    try:
        if ticker:
            df = raw.xs(ticker, level=1, axis=1) if ticker in raw.columns.get_level_values(1) else raw
        else:
            df = raw
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df = df.apply(pd.to_numeric, errors="coerce").dropna(subset=["Close"])
        return df
    except Exception:
        return pd.DataFrame()


def load_asset_universe(
    include_us_sectors: bool = True,
    include_forex: bool = True,
    include_commodities: bool = True,
    include_crypto: bool = True,
    include_ihsg: bool = True,
    include_bonds: bool = True,
    days: int = 756,
    ttl: int = 3600,
) -> Dict[str, pd.Series]:
    """
    Load the full multi-asset universe, lazy by asset class.
    Use flags to control what loads — keeps the app light.
    """
    from config.settings import (
        US_SECTORS, US_FACTORS, FOREX_PAIRS, COMMODITIES,
        CRYPTO, IHSG_TICKERS, BONDS, MACRO_PROXIES,
    )

    tickers: List[str] = list(MACRO_PROXIES.keys())  # always load macro proxies

    if include_us_sectors:
        tickers += list(US_SECTORS.keys()) + list(US_FACTORS.keys())
    if include_forex:
        tickers += FOREX_PAIRS
    if include_commodities:
        tickers += list(COMMODITIES.keys())
    if include_crypto:
        tickers += list(CRYPTO.keys())
    if include_ihsg:
        tickers += list(IHSG_TICKERS.keys())
    if include_bonds:
        tickers += list(BONDS.keys())

    # Remove duplicates while preserving order
    seen = set()
    unique = [t for t in tickers if not (t in seen or seen.add(t))]

    return load_prices(unique, days=days, ttl=ttl)


# ---------------------------------------------------------------------------
# Snapshot — fast app open
# ---------------------------------------------------------------------------

def save_snapshot(data: dict, path: str = None) -> None:
    from config.settings import SNAPSHOT_PATH
    p = Path(path or SNAPSHOT_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        pickle.dump({"ts": time.time(), "data": data}, f)


def load_snapshot(path: str = None, max_age_hours: float = 6.0) -> Optional[dict]:
    from config.settings import SNAPSHOT_PATH
    p = Path(path or SNAPSHOT_PATH)
    if not p.exists():
        return None
    try:
        with open(p, "rb") as f:
            snap = pickle.load(f)
        age_h = (time.time() - snap.get("ts", 0)) / 3600
        if age_h > max_age_hours:
            return None
        return snap.get("data")
    except Exception:
        return None


def snapshot_age_str(path: str = None) -> str:
    from config.settings import SNAPSHOT_PATH
    p = Path(path or SNAPSHOT_PATH)
    if not p.exists():
        return "No snapshot"
    try:
        age_s = time.time() - p.stat().st_mtime
        if age_s < 60:
            return f"< 1 min ago"
        elif age_s < 3600:
            return f"{int(age_s/60)} min ago"
        else:
            return f"{age_s/3600:.1f} hr ago"
    except Exception:
        return "Unknown"
