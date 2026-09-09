from __future__ import annotations

import io
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode

import pandas as pd
import requests

DEFAULT_HEADERS={"User-Agent":"OpportunityIntelligence/2.3 research dashboard contact=local-user"}


def sec_company_tickers_url() -> str:
    return "https://www.sec.gov/files/company_tickers.json"


def parse_sec_company_tickers(payload: Dict[str, Any]) -> pd.DataFrame:
    rows=[]
    for _,item in (payload or {}).items():
        if not isinstance(item,dict):
            continue
        ticker=str(item.get("ticker","")).strip().upper()
        cik=item.get("cik_str")
        if ticker and cik is not None:
            rows.append({"ticker":ticker,"cik":str(int(cik)).zfill(10),"name":str(item.get("title",ticker))})
    return pd.DataFrame(rows).drop_duplicates("ticker") if rows else pd.DataFrame(columns=["ticker","cik","name"])


def fetch_sec_company_tickers(timeout: int=20) -> pd.DataFrame:
    r=requests.get(sec_company_tickers_url(),headers=DEFAULT_HEADERS,timeout=timeout)
    r.raise_for_status()
    return parse_sec_company_tickers(r.json())


def sec_companyfacts_url(cik: str) -> str:
    return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{str(int(cik)).zfill(10)}.json"


def companyfacts_pit_values(payload: Dict[str,Any], concept: str, as_of: datetime, unit_preference: Optional[str]=None) -> pd.DataFrame:
    """Return facts whose SEC filing timestamp/date was available by as_of.

    Uses `filed` as the availability clock. It deliberately does not back-date facts to period end.
    """
    facts=(payload or {}).get("facts",{}) or {}
    found=None
    for taxonomy in ("us-gaap","dei"):
        if concept in (facts.get(taxonomy,{}) or {}):
            found=facts[taxonomy][concept]
            break
    if not found:
        return pd.DataFrame()
    units=found.get("units",{}) or {}
    if unit_preference and unit_preference in units:
        items=units[unit_preference]
    else:
        items=[]
        for arr in units.values(): items.extend(arr or [])
    cutoff=pd.Timestamp(as_of)
    if cutoff.tzinfo is not None:
        cutoff=cutoff.tz_convert("UTC").tz_localize(None)
    rows=[]
    for item in items:
        filed=pd.to_datetime(item.get("filed"),errors="coerce")
        if pd.isna(filed) or filed>cutoff:
            continue
        rows.append({
            "concept":concept,"value":item.get("val"),"start":item.get("start"),"end":item.get("end"),
            "filed":item.get("filed"),"form":item.get("form"),"fy":item.get("fy"),"fp":item.get("fp"),
            "frame":item.get("frame"),"accn":item.get("accn"),
        })
    return pd.DataFrame(rows).sort_values(["filed","end"],kind="stable") if rows else pd.DataFrame()


def alfred_csv_url(series_id: str, vintage_date: str) -> str:
    # ALFRED key-free graph CSV route; vintage_date controls what was known on that date.
    return f"https://api.stlouisfed.org/fred/series/observations?{urlencode({'series_id':series_id,'api_key':'','file_type':'json'})}" if False else f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd=1900-01-01&coed={vintage_date}&vintage_date={vintage_date}"


def parse_fredgraph_csv(text: str, series_id: str) -> pd.Series:
    df=pd.read_csv(io.StringIO(text))
    if df.empty: return pd.Series(dtype=float)
    date_col=df.columns[0]
    value_col=series_id if series_id in df.columns else df.columns[-1]
    df[date_col]=pd.to_datetime(df[date_col],errors="coerce")
    df[value_col]=pd.to_numeric(df[value_col],errors="coerce")
    return df.dropna(subset=[date_col]).set_index(date_col)[value_col].dropna().sort_index()


def idx_company_list_url(page_size: int=5000) -> str:
    return "https://www.idx.co.id/primary/ListedCompany/GetCompanyProfiles?" + urlencode({"start":0,"length":page_size})


def parse_idx_company_profiles(payload: Dict[str,Any]) -> pd.DataFrame:
    candidates=(payload or {}).get("data") or (payload or {}).get("Results") or []
    rows=[]
    for item in candidates:
        if not isinstance(item,dict): continue
        code=item.get("KodeEmiten") or item.get("KodeEmitenBaru") or item.get("Code") or item.get("kodeEmiten")
        name=item.get("NamaEmiten") or item.get("NamaEmitenBaru") or item.get("Name") or item.get("namaEmiten")
        if code:
            code=str(code).strip().upper()
            rows.append({"ticker":code+".JK" if not code.endswith(".JK") else code,"code":code.replace(".JK",""),"name":str(name or code)})
    return pd.DataFrame(rows).drop_duplicates("ticker") if rows else pd.DataFrame(columns=["ticker","code","name"])


def idx_financial_report_url(year: int, *, report_type: str="rdf", page_size: int=100, index_from: int=1, period: str="audit", code: str="") -> str:
    params={"indexFrom":index_from,"pageSize":page_size,"year":year,"reportType":report_type,"EmitenType":"s","periode":period,"kodeEmiten":code,"SortColumn":"FileModified","SortOrder":"desc"}
    return "https://www.idx.co.id/primary/ListedCompany/GetFinancialReport?"+urlencode(params)


def parse_idx_financial_reports(payload: Dict[str,Any]) -> pd.DataFrame:
    items=(payload or {}).get("Results") or (payload or {}).get("data") or []
    rows=[]
    for item in items:
        if not isinstance(item,dict): continue
        code=item.get("KodeEmiten") or item.get("kodeEmiten") or item.get("Code")
        modified=item.get("FileModified") or item.get("fileModified") or item.get("Modified")
        rows.append({"code":code,"file_modified":modified,"raw":item})
    out=pd.DataFrame(rows)
    if not out.empty:
        out["file_modified_dt"]=pd.to_datetime(out["file_modified"],errors="coerce",utc=True)
    return out
