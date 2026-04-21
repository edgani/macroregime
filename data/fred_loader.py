from __future__ import annotations

import os
import time
from io import StringIO
from typing import Dict

import pandas as pd
import requests

from config.settings import FRED_CACHE_TTL_SECONDS, LIVE_FETCH_ENABLED
from utils.streamlit_compat import st

FRED_API_KEY = os.getenv("FRED_API_KEY", "").strip()

FRED_SERIES = {
    "INDPRO": "INDPRO",
    "RSAFS": "RSAFS",
    "PAYEMS": "PAYEMS",
    "UNRATE": "UNRATE",
    "ICSA": "ICSA",
    "CPI": "CPIAUCSL",
    "CORECPI": "CPILFESL",
    "PCE": "PCEPI",
    "COREPCE": "PCEPILFE",
    "DGS2": "DGS2",
    "DGS10": "DGS10",
    "DFII10": "DFII10",
    "T5YIE": "T5YIE",
    "T5YIFR": "T5YIFR",
    "HYOAS": "BAMLH0A0HYM2",
    "IGOAS": "BAMLC0A0CM",
    "ISMNO": "NAPMNOI",
    "HOUST": "HOUST",
    "FEDFUNDS": "FEDFUNDS",
    "LEI": "USSLIND",
    "M2SL": "M2SL",
    "WALCL": "WALCL",
    "USDINDEX": "DTWEXBGS",
    "VIX": "VIXCLS",
}


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "MacroRegime-Pro/0.34"})
    return session


def _fetch_series_api(session: requests.Session, sid: str) -> pd.DataFrame:
    if FRED_API_KEY:
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={sid}&api_key={FRED_API_KEY}"
            f"&file_type=json&sort_order=desc&limit=5000"
        )
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get("observations"):
                df = pd.DataFrame(data["observations"])
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
                df["date"] = pd.to_datetime(df["date"])
                return df[["date", "value"]].dropna()
        except Exception:
            pass

    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    for attempt in range(3):
        try:
            resp = session.get(url, timeout=(6 + attempt * 4))
            resp.raise_for_status()
            df = pd.read_csv(StringIO(resp.text))
            df.columns = [c.strip() for c in df.columns]
            date_col = next((c for c in df.columns if "DATE" in c.upper()), None)
            if not date_col:
                raise ValueError(f"No date column for {sid}")
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            val_col = [c for c in df.columns if c != date_col][0]
            df[val_col] = pd.to_numeric(df[val_col], errors="coerce")
            return (
                df[[date_col, val_col]]
                .rename(columns={date_col: "date", val_col: "value"})
                .dropna()
            )
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    return pd.DataFrame()


def _validate_series(s: pd.Series, sid: str) -> pd.Series:
    if s.empty:
        return pd.Series(dtype=float)
    days_since = (pd.Timestamp.now(tz="UTC") - s.index[-1]).days
    if days_since > 90:
        return pd.Series(dtype=float)
    if s.nunique() <= 1 and len(s) > 10:
        return pd.Series(dtype=float)
    return s


@st.cache_data(ttl=FRED_CACHE_TTL_SECONDS, show_spinner=False)
def load_fred_bundle(*, force_refresh: bool = False) -> dict:
    out: Dict[str, pd.Series] = {}
    if not LIVE_FETCH_ENABLED:
        return {
            "series": {k: pd.Series(dtype=float) for k in FRED_SERIES.keys()},
            "meta": _empty_meta(),
        }

    session = _session()
    loaded, missing = [], []

    for nice, sid in FRED_SERIES.items():
        try:
            df = _fetch_series_api(session, sid)
            if df.empty:
                missing.append(nice)
                out[nice] = pd.Series(dtype=float)
                continue
            s = pd.Series(
                df["value"].values,
                index=pd.to_datetime(df["date"]),
                name=nice,
            )
            s = _validate_series(s, sid)
            if s.empty:
                missing.append(nice)
                out[nice] = pd.Series(dtype=float)
            else:
                out[nice] = s
                loaded.append(nice)
        except Exception:
            missing.append(nice)
            out[nice] = pd.Series(dtype=float)

    total = len(FRED_SERIES)
    real_share = len(loaded) / max(total, 1)

    return {
        "series": out,
        "meta": {
            "requested": total,
            "loaded": len(loaded),
            "missing": len(missing),
            "loaded_keys": loaded,
            "missing_keys": missing,
            "real_share": real_share,
            "source": "fred_api_v2",
            "api_key_present": bool(FRED_API_KEY),
            "staleness_threshold_days": 90,
        },
    }


def _empty_meta() -> dict:
    return {
        "requested": len(FRED_SERIES),
        "loaded": 0,
        "missing": len(FRED_SERIES),
        "loaded_keys": [],
        "missing_keys": list(FRED_SERIES.keys()),
        "real_share": 0.0,
        "source": "fred_api_v2",
        "api_key_present": bool(FRED_API_KEY),
    }


@st.cache_data(ttl=FRED_CACHE_TTL_SECONDS, show_spinner=False)
def load_fred_series(*, force_refresh: bool = False) -> Dict[str, pd.Series]:
    return load_fred_bundle(force_refresh=force_refresh)["series"]
