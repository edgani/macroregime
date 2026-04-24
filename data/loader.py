"""data/loader.py — Smart cache + FRED + yfinance. Light at open."""
from __future__ import annotations
import os, time, pickle, hashlib, logging
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class Cache:
    def __init__(self, d=".cache"):
        self.dir = Path(d); self.dir.mkdir(parents=True, exist_ok=True)
    def _p(self, n): return self.dir / f"{hashlib.md5(n.encode()).hexdigest()[:12]}.pkl"
    def get(self, n, ttl=3600):
        p = self._p(n)
        if p.exists() and (time.time()-p.stat().st_mtime) < ttl:
            try:
                with open(p,"rb") as f: return pickle.load(f)
            except: pass
        return None
    def set(self, n, v):
        try:
            with open(self._p(n),"wb") as f: pickle.dump(v,f)
        except Exception as e: logger.warning(f"Cache write {n}: {e}")

_cache = Cache()

def _get_fred_key() -> str:
    """Read FRED key from env or Streamlit secrets."""
    key = os.environ.get("FRED_API_KEY","")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("FRED_API_KEY","")
        except Exception: pass
    return key

def load_fred(months=36) -> Dict[str, pd.Series]:
    from config.settings import FRED_GROWTH_SERIES, FRED_INFLATION_SERIES, FRED_POLICY_SERIES
    all_ids = list(FRED_GROWTH_SERIES)+list(FRED_INFLATION_SERIES)+list(FRED_POLICY_SERIES)
    ck = f"fred_{'_'.join(sorted(all_ids))}_{months}"
    cached = _cache.get(ck, ttl=14400)
    if cached is not None: return cached
    key = _get_fred_key()
    if not key:
        logger.warning("FRED_API_KEY not set — proxy mode only")
        return {}
    result = {}
    try:
        import fredapi
        fred = fredapi.Fred(api_key=key)
        start = pd.Timestamp.now() - pd.DateOffset(months=months)
        for sid in all_ids:
            try:
                s = fred.get_series(sid, observation_start=start)
                if isinstance(s, pd.Series) and not s.empty:
                    result[sid] = pd.to_numeric(s, errors="coerce").dropna()
            except Exception as e: logger.debug(f"FRED {sid}: {e}")
    except ImportError: logger.warning("fredapi not installed")
    except Exception as e: logger.warning(f"FRED load: {e}")
    if result: _cache.set(ck, result)
    return result

def load_prices(tickers: List[str], days=756, ttl=3600) -> Dict[str, pd.Series]:
    if not tickers: return {}
    ck = f"prices_{'_'.join(sorted(tickers))}_{days}"
    cached = _cache.get(ck, ttl=ttl)
    if cached is not None: return cached
    result = {}
    try:
        import yfinance as yf
        raw = yf.download(tickers, period=f"{days}d", progress=False,
                          auto_adjust=True, threads=True, timeout=30)
        if raw.empty: return result
        if len(tickers)==1:
            t = tickers[0]
            c = pd.to_numeric(raw["Close"] if "Close" in raw.columns else raw.iloc[:,0], errors="coerce").dropna()
            if not c.empty: result[t] = c
        else:
            cl = raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw.xs("Close",level=0,axis=1) if "Close" in raw.columns.get_level_values(1) else None
            if cl is None: return result
            for t in tickers:
                try:
                    if t in cl.columns:
                        s = pd.to_numeric(cl[t], errors="coerce").dropna()
                        if not s.empty: result[t] = s
                except Exception: pass
    except Exception as e: logger.warning(f"Price load {e}")
    if result: _cache.set(ck, result)
    return result

def save_snapshot(data, path=None):
    from config.settings import SNAPSHOT_PATH
    p = Path(path or SNAPSHOT_PATH); p.parent.mkdir(parents=True, exist_ok=True)
    with open(p,"wb") as f: pickle.dump({"ts":time.time(),"data":data},f)

def load_snapshot(path=None, max_age_hours=6.0) -> Optional[dict]:
    from config.settings import SNAPSHOT_PATH
    p = Path(path or SNAPSHOT_PATH)
    if not p.exists(): return None
    try:
        with open(p,"rb") as f: snap=pickle.load(f)
        if (time.time()-snap.get("ts",0))/3600 > max_age_hours: return None
        return snap.get("data")
    except: return None

def snapshot_age_str(path=None) -> str:
    from config.settings import SNAPSHOT_PATH
    p = Path(path or SNAPSHOT_PATH)
    if not p.exists(): return "No snapshot"
    try:
        s = time.time()-p.stat().st_mtime
        return f"< 1 min ago" if s<60 else f"{int(s/60)} min ago" if s<3600 else f"{s/3600:.1f} hr ago"
    except: return "Unknown"
