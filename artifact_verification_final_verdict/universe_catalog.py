from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable, Optional

import pandas as pd
import requests

from data_adapters import fetch_sec_company_tickers, idx_company_list_url, parse_idx_company_profiles, DEFAULT_HEADERS


def fetch_idx_company_catalog(timeout: int=20) -> pd.DataFrame:
    r=requests.get(idx_company_list_url(),headers=DEFAULT_HEADERS,timeout=timeout)
    r.raise_for_status()
    return parse_idx_company_profiles(r.json())


def current_catalog(market: str, timeout: int=20) -> pd.DataFrame:
    """Best-effort current issuer catalog. Failure returns an empty frame, never a fake list."""
    m=str(market)
    try:
        if m=="US":
            x=fetch_sec_company_tickers(timeout=timeout)
            if x.empty: return pd.DataFrame()
            return pd.DataFrame({"market":"US","symbol":x["ticker"].astype(str),"name":x["name"].astype(str),"catalog_source":"SEC company_tickers"})
        if m=="IHSG":
            x=fetch_idx_company_catalog(timeout=timeout)
            if x.empty: return pd.DataFrame()
            return pd.DataFrame({"market":"IHSG","symbol":x["ticker"].astype(str),"name":x["name"].astype(str),"catalog_source":"IDX company profiles"})
    except Exception:
        return pd.DataFrame()
    return pd.DataFrame()


def deterministic_rotation(catalog: pd.DataFrame, seed_symbols: Iterable[str], *, as_of: Any, n: int=6) -> pd.DataFrame:
    """Rotate broad catalogs prospectively without scanning thousands of names per refresh."""
    if catalog is None or catalog.empty or n<=0: return pd.DataFrame()
    seed={str(x).upper() for x in seed_symbols}
    c=catalog[~catalog["symbol"].astype(str).str.upper().isin(seed)].copy().sort_values("symbol").reset_index(drop=True)
    if c.empty: return c
    t=pd.Timestamp(as_of)
    if t.tzinfo is None: t=t.tz_localize("UTC")
    # Half-hour bucket creates deterministic breadth over time while reruns within the
    # same scan window are stable.
    bucket=t.floor("30min").isoformat()
    h=int(hashlib.sha256(bucket.encode()).hexdigest()[:12],16)
    start=h%len(c)
    idx=[(start+i)%len(c) for i in range(min(int(n),len(c)))]
    return c.iloc[idx].reset_index(drop=True)


def merge_seed_with_rotation(seed: pd.DataFrame, catalogs: Dict[str,pd.DataFrame], selected_markets: Iterable[str], *, as_of: Any, extras_per_market: int=6) -> pd.DataFrame:
    base=seed[seed["market"].isin(list(selected_markets))].copy() if not seed.empty else pd.DataFrame()
    parts=[base]
    for market in selected_markets:
        cat=catalogs.get(str(market),pd.DataFrame())
        if cat is None or cat.empty: continue
        seed_syms=base.loc[base["market"].eq(market),"symbol"].astype(str).tolist() if not base.empty else []
        rot=deterministic_rotation(cat,seed_syms,as_of=as_of,n=extras_per_market)
        if rot.empty: continue
        for col in seed.columns:
            if col not in rot.columns: rot[col]=""
        parts.append(rot[seed.columns.tolist() + (["catalog_source"] if "catalog_source" not in seed.columns else [])] if "catalog_source" not in seed.columns else rot[seed.columns])
    out=pd.concat(parts,ignore_index=True,sort=False) if parts else pd.DataFrame()
    return out.drop_duplicates(["market","symbol"],keep="first").reset_index(drop=True)
