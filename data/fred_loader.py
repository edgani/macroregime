"""data/fred_loader.py — Parallel FRED Fetcher v2 (Patched)
Fixes:
 • Graceful fallback if settings constants missing
 • Parallel fetch via ThreadPoolExecutor (was sequential → 100s delay)
 • Shorter per-series timeout (8s) with 12s future timeout
 • Returns empty series instead of crashing on failure
"""
from __future__ import annotations

from io import StringIO
from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import requests

# Safe import of settings with fallbacks
try:
    from config.settings import FRED_CACHE_TTL_SECONDS, LIVE_FETCH_ENABLED
except Exception:
    FRED_CACHE_TTL_SECONDS = 3600
    LIVE_FETCH_ENABLED = True

try:
    from utils.streamlit_compat import st
except Exception:
    # Dummy st object if import fails
    class _DummySt:
        def cache_data(self, *a, **k):
            def decorator(f):
                return f
            return decorator
    st = _DummySt()

FRED_SERIES = {
    "INDPRO": "INDPRO",
    "RSAFS": "RSAFS",
    "PAYEMS": "PAYEMS",
    "UNRATE": "UNRATE",
    "ICSA": "ICSA",
    "CPI": "CPIAUCSL",
    "CORECPI": "CPILFESL",
    "DGS2": "DGS2",
    "DGS10": "DGS10",
    "DFII10": "DFII10",
    "T5YIE": "T5YIE",
    "HYOAS": "BAMLH0A0HYM2",
    "ISMNO": "NAPMNOI",
    "HOUST": "HOUST",
    "FEDFUNDS": "FEDFUNDS",
}


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    return session


def _empty_meta() -> dict:
    return {
        "requested": len(FRED_SERIES),
        "loaded": 0,
        "missing": len(FRED_SERIES),
        "loaded_keys": [],
        "missing_keys": list(FRED_SERIES.keys()),
        "source": "fred_csv",
    }


def _fetch_one(session: requests.Session, nice: str, sid: str) -> tuple:
    """Fetch a single FRED series. Returns (nice, series_or_None)."""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    try:
        resp = session.get(url, timeout=8)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text))
        df.columns = [c.strip() for c in df.columns]
        if "DATE" not in df.columns:
            return nice, None
        df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
        value_cols = [c for c in df.columns if c != "DATE"]
        if not value_cols:
            return nice, None
        series = pd.to_numeric(df[value_cols[0]], errors="coerce")
        s = pd.Series(series.values, index=df["DATE"], name=nice).dropna()
        if s.empty:
            return nice, None
        return nice, s
    except Exception:
        return nice, None


@st.cache_data(ttl=FRED_CACHE_TTL_SECONDS, show_spinner=False)
def load_fred_bundle(*, force_refresh: bool = False) -> dict:
    out: Dict[str, pd.Series] = {}
    meta = _empty_meta()

    if not LIVE_FETCH_ENABLED:
        return {
            "series": {k: pd.Series(dtype=float) for k in FRED_SERIES.keys()},
            "meta": meta,
        }

    session = _session()
    loaded_keys: list = []
    missing_keys: list = []

    # PATCH: Parallel fetch with 3 workers (was sequential)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_fetch_one, session, nice, sid): nice
            for nice, sid in FRED_SERIES.items()
        }
        for future in as_completed(futures):
            nice = futures[future]
            try:
                _, s = future.result(timeout=12)
                if s is not None and not s.empty:
                    out[nice] = s
                    loaded_keys.append(nice)
                else:
                    out[nice] = pd.Series(dtype=float)
                    missing_keys.append(nice)
            except Exception:
                out[nice] = pd.Series(dtype=float)
                missing_keys.append(nice)

    meta.update({
        "requested": len(FRED_SERIES),
        "loaded": len(loaded_keys),
        "missing": len(missing_keys),
        "loaded_keys": loaded_keys,
        "missing_keys": missing_keys,
        "real_share": (len(loaded_keys) / max(len(FRED_SERIES), 1)),
        "source": "fred_csv",
    })
    return {"series": out, "meta": meta}


@st.cache_data(ttl=FRED_CACHE_TTL_SECONDS, show_spinner=False)
def load_fred_series(*, force_refresh: bool = False) -> Dict[str, pd.Series]:
    return load_fred_bundle(force_refresh=force_refresh)["series"]
