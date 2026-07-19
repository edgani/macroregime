"""Institutional data adapters for War Room OS.

The module normalizes *observed events* from optional providers. Missing credentials never
produce fabricated values: every adapter returns an explicit NOT_CONFIGURED / ERROR / EMPTY state.

Environment variables
---------------------
WARROOM_SEC_USER_AGENT   Required by SEC.gov, e.g. "Edward Gani edward@example.com"
UNUSUAL_WHALES_API_KEY   Options flow + dark-pool REST feed
MASSIVE_API_KEY          Tick-level US equity trades; TRF prints identified by exchange=4 + trf_id
NANSEN_API_KEY           Smart Money holdings
ARKHAM_API_KEY           Labeled on-chain transfer events
WARROOM_WATCHLIST        Comma-separated symbols. If omitted, the current shortlist is used.

Data semantics
--------------
* Options alerts are observations, not automatically directional positions.
* Dark-pool/TRF prints are observations, not automatically accumulation/distribution.
* SEC filings have different reporting lags and must not be treated as equally timely.
* Nansen Smart Money labels are provider classifications, not proof of future returns.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import json
import os
import re
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / ".cache" / "institutional"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=1, connect=1, read=1, backoff_factor=0.25,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}), raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=30)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": "WarRoomOS/2.0 institutional-data"})
    return session


HTTP = _session()


@dataclass
class FeedStatus:
    provider: str
    dataset: str
    state: str
    observed: bool = True
    fetched_at: Optional[str] = None
    age_seconds: Optional[float] = None
    stale_after_seconds: Optional[int] = None
    records: int = 0
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _network_enabled() -> bool:
    return os.getenv("WARROOM_NETWORK_MODE", "live").strip().lower() not in {"offline", "disabled", "0", "false"}


def _as_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default



def _iso_timestamp(value: Any, fallback: Optional[str] = None) -> str:
    """Normalize provider timestamps (ISO strings or seconds/ms/us/ns epochs) to UTC ISO."""
    if value is None or value == "":
        return fallback or _utc_now()
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return fallback or _utc_now()
        try:
            numeric = float(stripped)
        except ValueError:
            return stripped
        value = numeric
    if isinstance(value, (int, float)):
        seconds = float(value)
        if seconds > 1e18:
            seconds /= 1e9
        elif seconds > 1e15:
            seconds /= 1e6
        elif seconds > 1e12:
            seconds /= 1e3
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        except (OverflowError, OSError, ValueError):
            pass
    return fallback or _utc_now()


def _nested(row: Dict[str, Any], *paths: str) -> Any:
    for path in paths:
        cur: Any = row
        for part in path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                cur = None
                break
            cur = cur[part]
        if cur not in (None, ""):
            return cur
    return None

def _cache_path(key: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)
    return CACHE_DIR / f"{safe}.json"


def _read_cache(key: str, ttl_seconds: int) -> Optional[Dict[str, Any]]:
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        age = time.time() - path.stat().st_mtime
        if age > ttl_seconds:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_cache_age_seconds"] = round(age, 2)
        return payload
    except Exception:
        return None


def _write_cache(key: str, payload: Dict[str, Any]) -> None:
    path = _cache_path(key)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, default=str), encoding="utf-8")
    temp.replace(path)


def _read_cache_any(key: str) -> Optional[Dict[str, Any]]:
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        age = time.time() - path.stat().st_mtime
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_cache_age_seconds"] = round(age, 2)
        return payload
    except Exception:
        return None


def _cached_json_request(
    *,
    cache_key: str,
    ttl_seconds: int,
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    cached = _read_cache(cache_key, ttl_seconds)
    if cached is not None:
        cached["_cache_state"] = "LIVE"
        return cached
    if not _network_enabled():
        stale = _read_cache_any(cache_key)
        if stale is not None:
            stale["_cache_state"] = "STALE"
            stale["_cache_error"] = "WARROOM_NETWORK_MODE=offline"
            return stale
        raise RuntimeError("WARROOM_NETWORK_MODE=offline")
    try:
        response = HTTP.request(
            method, url, headers=headers or {}, params=params, json=json_body,
            timeout=min(float(timeout), float(os.getenv("WARROOM_HTTP_TIMEOUT", "8"))),
        )
        response.raise_for_status()
        payload = response.json()
        wrapped = {"payload": payload, "fetched_at": _utc_now(), "status_code": response.status_code, "_cache_state": "LIVE"}
        _write_cache(cache_key, wrapped)
        return wrapped
    except Exception as exc:
        stale = _read_cache_any(cache_key)
        if stale is not None:
            stale["_cache_state"] = "STALE"
            stale["_cache_error"] = f"{type(exc).__name__}: {exc}"
            return stale
        raise


def _parallel_cached_requests(specs: Dict[str, Dict[str, Any]], max_workers: int = 10) -> Dict[str, Dict[str, Any]]:
    if not specs:
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(specs))) as pool:
        futures = {pool.submit(_cached_json_request, **kwargs): name for name, kwargs in specs.items()}
        for fut in as_completed(futures):
            name = futures[fut]
            try: out[name] = fut.result()
            except Exception as exc: out[name] = {"_request_error": f"{type(exc).__name__}: {exc}", "payload": None, "fetched_at": None}
    return out


def _extract_rows(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "results", "items", "records", "transfers"):
        value = payload.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    return []


def _not_configured(provider: str, dataset: str, env_name: str, stale_after: int, state: str = "NOT_ENTITLED") -> Dict[str, Any]:
    return {
        "status": FeedStatus(
            provider=provider,
            dataset=dataset,
            state=state,
            stale_after_seconds=stale_after,
            note=f"Set {env_name}; no placeholder or synthetic records emitted.",
        ).to_dict(),
        "data": [],
    }


def fetch_unusual_whales_options(limit: int = 100, min_premium: int = 100_000) -> Dict[str, Any]:
    key = os.getenv("UNUSUAL_WHALES_API_KEY", "").strip()
    if not key:
        return _not_configured("Unusual Whales", "options_flow", "UNUSUAL_WHALES_API_KEY", 30)
    try:
        wrapped = _cached_json_request(
            cache_key=f"uw_options_{limit}_{min_premium}",
            ttl_seconds=12,
            method="GET",
            url="https://api.unusualwhales.com/api/option-trades/flow-alerts",
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            params={"limit": min(limit, 200), "min_premium": min_premium},
        )
        raw_rows = _extract_rows(wrapped["payload"])
        rows: List[Dict[str, Any]] = []
        for r in raw_rows:
            premium = _as_float(r.get("total_premium"), 0.0) or 0.0
            ask_prem = _as_float(r.get("total_ask_side_prem"), 0.0) or 0.0
            bid_prem = _as_float(r.get("total_bid_side_prem"), 0.0) or 0.0
            side_total = ask_prem + bid_prem
            ask_pct = ask_prem / side_total if side_total > 0 else None
            option_type = str(r.get("type") or r.get("option_type") or "").lower()
            # This is trade-side interpretation only, explicitly not a position claim.
            tape_bias = "NEUTRAL"
            if ask_pct is not None:
                if option_type == "call" and ask_pct >= 0.75:
                    tape_bias = "CALL_ASK_DOMINANT"
                elif option_type == "put" and ask_pct >= 0.75:
                    tape_bias = "PUT_ASK_DOMINANT"
                elif option_type == "call" and ask_pct <= 0.25:
                    tape_bias = "CALL_BID_DOMINANT"
                elif option_type == "put" and ask_pct <= 0.25:
                    tape_bias = "PUT_BID_DOMINANT"
            flags = []
            if r.get("has_sweep"):
                flags.append("SWEEP")
            if r.get("has_floor"):
                flags.append("FLOOR")
            if r.get("has_multileg"):
                flags.append("MULTI_LEG")
            if r.get("all_opening_trades"):
                flags.append("ALL_OPENING")
            rows.append({
                "event_type": "OPTIONS_FLOW",
                "provider": "Unusual Whales",
                "ticker": r.get("ticker") or "—",
                "timestamp": _iso_timestamp(r.get("created_at") or r.get("executed_at"), wrapped["fetched_at"]),
                "premium": premium,
                "size": r.get("total_size"),
                "trade_count": r.get("trade_count"),
                "contract": r.get("option_chain"),
                "option_type": option_type.upper() if option_type else None,
                "strike": r.get("strike"),
                "expiry": r.get("expiry"),
                "underlying_price": _as_float(r.get("underlying_price")),
                "volume_oi_ratio": _as_float(r.get("volume_oi_ratio")),
                "ask_side_pct": round(ask_pct, 4) if ask_pct is not None else None,
                "rule": r.get("alert_rule") or r.get("rule_name"),
                "flags": flags,
                "classification": tape_bias,
                "observed": True,
                "position_inference": "UNCONFIRMED",
                "raw_id": r.get("id"),
            })
        return {
            "status": FeedStatus(
                provider="Unusual Whales", dataset="options_flow", state=(wrapped.get("_cache_state") or "LIVE") if rows else "EMPTY",
                fetched_at=wrapped["fetched_at"], age_seconds=wrapped.get("_cache_age_seconds", 0),
                stale_after_seconds=30, records=len(rows),
                note="Trade-side flow; hedge/open-close intent remains unconfirmed unless separately reconciled.",
            ).to_dict(),
            "data": rows,
        }
    except Exception as exc:
        return {
            "status": FeedStatus(provider="Unusual Whales", dataset="options_flow", state="ERROR",
                                 stale_after_seconds=30, note=f"{type(exc).__name__}: {exc}").to_dict(),
            "data": [],
        }


def fetch_unusual_whales_dark_pool(limit: int = 100, min_premium: int = 100_000) -> Dict[str, Any]:
    key = os.getenv("UNUSUAL_WHALES_API_KEY", "").strip()
    if not key:
        return _not_configured("Unusual Whales", "dark_pool", "UNUSUAL_WHALES_API_KEY", 30)
    try:
        wrapped = _cached_json_request(
            cache_key=f"uw_darkpool_{limit}_{min_premium}",
            ttl_seconds=12,
            method="GET",
            url="https://api.unusualwhales.com/api/darkpool/recent",
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            params={"limit": min(limit, 200), "min_premium": min_premium, "order_by": "premium", "order": "desc"},
        )
        raw_rows = _extract_rows(wrapped["payload"])
        rows = []
        for r in raw_rows:
            price = _as_float(r.get("price"))
            bid = _as_float(r.get("nbbo_bid"))
            ask = _as_float(r.get("nbbo_ask"))
            location = "UNKNOWN"
            if price is not None and bid is not None and ask is not None and ask >= bid:
                if abs(price - ask) <= max(0.0001, (ask - bid) * 0.1):
                    location = "AT_ASK"
                elif abs(price - bid) <= max(0.0001, (ask - bid) * 0.1):
                    location = "AT_BID"
                else:
                    location = "MID_OR_INSIDE"
            rows.append({
                "event_type": "DARK_POOL",
                "provider": "Unusual Whales",
                "ticker": r.get("ticker") or "—",
                "timestamp": _iso_timestamp(r.get("executed_at") or r.get("trf_executed_at"), wrapped["fetched_at"]),
                "premium": _as_float(r.get("premium"), 0.0) or 0.0,
                "price": price,
                "size": r.get("size"),
                "volume": r.get("volume"),
                "nbbo_bid": bid,
                "nbbo_ask": ask,
                "nbbo_location": location,
                "trf": True,
                "observed": True,
                "position_inference": "UNCONFIRMED",
                "raw_id": r.get("tracking_id"),
            })
        return {
            "status": FeedStatus(
                provider="Unusual Whales", dataset="dark_pool", state=(wrapped.get("_cache_state") or "LIVE") if rows else "EMPTY",
                fetched_at=wrapped["fetched_at"], age_seconds=wrapped.get("_cache_age_seconds", 0),
                stale_after_seconds=30, records=len(rows),
                note="Off-exchange prints; accumulation/distribution requires clustering and price-response confirmation.",
            ).to_dict(),
            "data": rows,
        }
    except Exception as exc:
        return {
            "status": FeedStatus(provider="Unusual Whales", dataset="dark_pool", state="ERROR",
                                 stale_after_seconds=30, note=f"{type(exc).__name__}: {exc}").to_dict(),
            "data": [],
        }


def fetch_massive_stream_bridge(tickers: Iterable[str], limit: int = 500) -> Dict[str, Any]:
    url = os.getenv("MASSIVE_STREAM_BRIDGE_URL", "").strip()
    if not url:
        return _not_configured("Massive Stream", "trades_quotes", "MASSIVE_STREAM_BRIDGE_URL", 15)
    token = os.getenv("MASSIVE_STREAM_BRIDGE_TOKEN", "").strip()
    symbols = [str(t).upper() for t in tickers if t]
    try:
        wrapped = _cached_json_request(
            cache_key="massive_stream_bridge", ttl_seconds=2, method="GET", url=url,
            headers={"Authorization": f"Bearer {token}"} if token else {},
            params={"kind": "all", "tickers": ",".join(symbols), "limit": min(limit, 2000)}, timeout=4,
        )
        raw_rows = _extract_rows(wrapped["payload"])
        rows: List[Dict[str, Any]] = []
        for r in raw_rows:
            market = str(r.get("market") or "")
            ticker = str(r.get("ticker") or "")
            price = _as_float(r.get("price"))
            size = _as_float(r.get("size"))
            premium = (price or 0.0) * (size or 0.0)
            if market == "stocks" and (r.get("exchange") == 4 or r.get("trf_id") not in (None, "")):
                rows.append({
                    "event_type": "DARK_POOL", "provider": "Massive Stream", "ticker": ticker,
                    "timestamp": _iso_timestamp(r.get("timestamp"), wrapped["fetched_at"]),
                    "premium": premium, "price": price, "size": size,
                    "trf_id": r.get("trf_id"), "trf": True, "conditions": r.get("conditions") or [],
                    "observed": True, "position_inference": "UNCONFIRMED", "raw_id": r.get("received_at"),
                })
            elif market == "options" and str(r.get("event") or "").upper() == "T":
                contract = ticker
                match = re.match(r"(?:O:)?([A-Z.]+?)\d{6,}", contract)
                underlying = match.group(1) if match else contract
                rows.append({
                    "event_type": "OPTIONS_FLOW", "provider": "Massive Stream", "ticker": underlying,
                    "timestamp": _iso_timestamp(r.get("timestamp"), wrapped["fetched_at"]),
                    "premium": premium * 100.0, "price": price, "size": size,
                    "contract": contract, "conditions": r.get("conditions") or [],
                    "classification": "RAW_OPTION_TRADE", "flags": ["STREAM"],
                    "observed": True, "position_inference": "UNCONFIRMED", "raw_id": r.get("received_at"),
                })
        rows.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
        return {
            "status": FeedStatus(provider="Massive Stream", dataset="trades_quotes",
                                 state=(wrapped.get("_cache_state") or "LIVE") if rows else "EMPTY",
                                 fetched_at=wrapped["fetched_at"], age_seconds=wrapped.get("_cache_age_seconds", 0),
                                 stale_after_seconds=15, records=len(rows),
                                 note="Persistent WebSocket bridge; option trade direction/open-close remains unconfirmed.").to_dict(),
            "data": rows,
        }
    except Exception as exc:
        return {"status": FeedStatus(provider="Massive Stream", dataset="trades_quotes", state="ERROR",
                                     stale_after_seconds=15, note=f"{type(exc).__name__}: {exc}").to_dict(), "data": []}


def fetch_massive_dark_pool(tickers: Iterable[str], limit_per_ticker: int = 250) -> Dict[str, Any]:
    key = os.getenv("MASSIVE_API_KEY", "").strip()
    if not key:
        return _not_configured("Massive", "trf_trades", "MASSIVE_API_KEY", 45)
    symbols = [str(t).upper() for t in tickers if t and "." not in str(t) and "=" not in str(t) and "-" not in str(t)]
    symbols = list(dict.fromkeys(symbols))[:8]
    if not symbols:
        return {"status": FeedStatus(provider="Massive", dataset="trf_trades", state="EMPTY",
                                      stale_after_seconds=45, note="No eligible US shortlist tickers.").to_dict(), "data": []}
    date = datetime.now(timezone.utc).date().isoformat()
    specs={ticker:dict(cache_key=f"massive_trf_{ticker}_{date}",ttl_seconds=30,method="GET",
        url=f"https://api.massive.com/v3/trades/{ticker}",params={"apiKey":key,"timestamp":date,"limit":min(limit_per_ticker,50_000),"sort":"timestamp","order":"desc"},timeout=8) for ticker in symbols}
    fetched=_parallel_cached_requests(specs,max_workers=8)
    all_rows: List[Dict[str, Any]]=[];errors=[];any_stale=False
    for ticker,wrapped in fetched.items():
        if wrapped.get("_request_error"):
            errors.append(f"{ticker}: {wrapped['_request_error']}");continue
        any_stale=any_stale or wrapped.get("_cache_state")=="STALE"
        for r in _extract_rows(wrapped.get("payload")):
            if r.get("exchange") != 4 or r.get("trf_id") is None: continue
            price=_as_float(r.get("price"),0.0) or 0.0;size=_as_float(r.get("size"),0.0) or 0.0
            all_rows.append({"event_type":"DARK_POOL","provider":"Massive","ticker":ticker,
                "timestamp":_iso_timestamp(r.get("sip_timestamp") or r.get("participant_timestamp"),wrapped.get("fetched_at")),
                "premium":price*size,"price":price,"size":size,"conditions":r.get("conditions") or [],"trf_id":r.get("trf_id"),
                "trf":True,"observed":True,"position_inference":"UNCONFIRMED","raw_id":r.get("id")})
    all_rows.sort(key=lambda x:x.get("premium",0),reverse=True)
    state=("STALE" if any_stale else "LIVE") if all_rows else ("ERROR" if errors else "EMPTY")
    return {"status":FeedStatus(provider="Massive",dataset="trf_trades",state=state,fetched_at=_utc_now(),stale_after_seconds=45,
        records=len(all_rows),note=("; ".join(errors[:3]) if errors else "exchange=4 and trf_id present; intent unconfirmed")).to_dict(),"data":all_rows[:200]}


def _sec_headers() -> Dict[str, str]:
    ua = os.getenv("WARROOM_SEC_USER_AGENT", "").strip()
    return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate", "Accept": "application/json"}


def _sec_ticker_map() -> Dict[str, Dict[str, Any]]:
    wrapped = _cached_json_request(
        cache_key="sec_company_tickers", ttl_seconds=24 * 3600, method="GET",
        url="https://www.sec.gov/files/company_tickers.json", headers=_sec_headers(), timeout=20,
    )
    payload = wrapped["payload"]
    rows = payload.values() if isinstance(payload, dict) else []
    result = {}
    for row in rows:
        if isinstance(row, dict) and row.get("ticker"):
            result[str(row["ticker"]).upper()] = row
    return result


def fetch_sec_filings(tickers: Iterable[str], limit_per_ticker: int = 12) -> Dict[str, Any]:
    if not os.getenv("WARROOM_SEC_USER_AGENT", "").strip():
        return _not_configured("SEC EDGAR", "filings", "WARROOM_SEC_USER_AGENT", 180, state="ACTION_REQUIRED")
    symbols=[str(t).upper().replace(".JK","") for t in tickers if t]
    symbols=[t for t in dict.fromkeys(symbols) if t and "-USD" not in t and "=" not in t][:20]
    if not symbols:
        return {"status":FeedStatus(provider="SEC EDGAR",dataset="filings",state="EMPTY",stale_after_seconds=180,note="No US shortlist tickers.").to_dict(),"data":[]}
    try:
        mapping=_sec_ticker_map();specs={};meta={};missing=[]
        for ticker in symbols:
            info=mapping.get(ticker)
            if not info:missing.append(ticker);continue
            cik_int=int(info["cik_str"]);cik=str(cik_int).zfill(10);url=f"https://data.sec.gov/submissions/CIK{cik}.json"
            specs[ticker]=dict(cache_key=f"sec_submissions_{cik}",ttl_seconds=90,method="GET",url=url,headers=_sec_headers(),timeout=8)
            meta[ticker]=(info,cik_int,cik)
        fetched=_parallel_cached_requests(specs,max_workers=8);rows_out=[];any_stale=False;errors=[]
        target_forms={"4","8-K","13D","13D/A","13G","13G/A","13F-HR","10-Q","10-K","S-1","424B5"}
        for ticker,wrapped in fetched.items():
            if wrapped.get("_request_error"):errors.append(f"{ticker}: {wrapped['_request_error']}");continue
            info,cik_int,cik=meta[ticker];any_stale=any_stale or wrapped.get("_cache_state")=="STALE"
            recent=((wrapped.get("payload") or {}).get("filings") or {}).get("recent") or {}
            forms=recent.get("form") or [];accessions=recent.get("accessionNumber") or [];filing_dates=recent.get("filingDate") or []
            report_dates=recent.get("reportDate") or [];docs=recent.get("primaryDocument") or [];descriptions=recent.get("primaryDocDescription") or [];accepted=recent.get("acceptanceDateTime") or []
            emitted=0
            for idx,form in enumerate(forms):
                if form not in target_forms:continue
                accession=accessions[idx] if idx<len(accessions) else "";document=docs[idx] if idx<len(docs) else "";clean=accession.replace("-","")
                url=f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{clean}/{document}" if accession and document else None
                rows_out.append({"event_type":"SEC_FILING","provider":"SEC EDGAR","ticker":ticker,"company":info.get("title"),
                    "timestamp":accepted[idx] if idx<len(accepted) else (filing_dates[idx] if idx<len(filing_dates) else wrapped.get("fetched_at")),
                    "form":form,"filing_date":filing_dates[idx] if idx<len(filing_dates) else None,"report_date":report_dates[idx] if idx<len(report_dates) else None,
                    "description":descriptions[idx] if idx<len(descriptions) else None,"accession":accession,"url":url,"observed":True,"position_inference":"DISCLOSURE_ONLY"})
                emitted+=1
                if emitted>=limit_per_ticker:break
        rows_out.sort(key=lambda x:str(x.get("timestamp") or ""),reverse=True)
        state=("STALE" if any_stale else "LIVE") if rows_out else ("ERROR" if errors else "EMPTY")
        notes=[]
        if missing:notes.append(f"Missing ticker mapping: {', '.join(missing[:5])}")
        if errors:notes.append("; ".join(errors[:3]))
        if not notes:notes.append("Direct SEC submissions JSON; filing lags vary by form.")
        return {"status":FeedStatus(provider="SEC EDGAR",dataset="filings",state=state,fetched_at=_utc_now(),stale_after_seconds=180,records=len(rows_out),note=" · ".join(notes)).to_dict(),"data":rows_out[:200]}
    except Exception as exc:
        return {"status":FeedStatus(provider="SEC EDGAR",dataset="filings",state="ERROR",stale_after_seconds=180,note=f"{type(exc).__name__}: {exc}").to_dict(),"data":[]}


def fetch_arkham_transfers(limit: int = 100, min_usd: int = 500_000) -> Dict[str, Any]:
    """Fetch large labeled transfers from Arkham. Transfer direction is not trade intent."""
    key = os.getenv("ARKHAM_API_KEY", "").strip()
    if not key:
        return _not_configured("Arkham", "labeled_transfers", "ARKHAM_API_KEY", 45)
    try:
        wrapped = _cached_json_request(
            cache_key=f"arkham_transfers_{limit}_{min_usd}", ttl_seconds=20, method="GET",
            url="https://api.arkm.com/transfers",
            headers={"API-Key": key, "Accept": "application/json"},
            params={
                "chains": "ethereum,solana,base,arbitrum,bitcoin",
                "timeLast": "24h", "usdGte": min_usd,
                "sortKey": "usd", "sortDir": "desc", "limit": min(limit, 100), "offset": 0,
            },
            timeout=25,
        )
        rows: List[Dict[str, Any]] = []
        for r in _extract_rows(wrapped["payload"]):
            from_entity = _nested(r, "fromAddress.entity.name", "from.entity.name", "fromEntity.name", "from.name")
            to_entity = _nested(r, "toAddress.entity.name", "to.entity.name", "toEntity.name", "to.name")
            from_addr = _nested(r, "fromAddress.address", "from.address", "fromAddress", "from")
            to_addr = _nested(r, "toAddress.address", "to.address", "toAddress", "to")
            token = _nested(r, "token.symbol", "tokenSymbol", "unit", "asset.symbol") or "—"
            value_usd = _as_float(_nested(r, "historicalUSD", "usd", "valueUsd", "value_usd", "historicalUsd"), 0.0) or 0.0
            rows.append({
                "event_type": "ARKHAM_TRANSFER",
                "provider": "Arkham",
                "ticker": str(token).upper(),
                "timestamp": _iso_timestamp(_nested(r, "blockTimestamp", "timestamp", "time"), wrapped["fetched_at"]),
                "chain": _nested(r, "chain", "blockchain"),
                "value_usd": value_usd,
                "amount": _as_float(_nested(r, "unitValue", "amount", "value")),
                "from_entity": from_entity, "to_entity": to_entity,
                "from_address": from_addr if isinstance(from_addr, str) else None,
                "to_address": to_addr if isinstance(to_addr, str) else None,
                "tx_hash": _nested(r, "transactionHash", "txHash", "hash"),
                "classification": "LABELED_TRANSFER",
                "observed": True,
                "position_inference": "UNCONFIRMED_TRANSFER_NOT_TRADE_INTENT",
            })
        return {
            "status": FeedStatus(
                provider="Arkham", dataset="labeled_transfers", state=(wrapped.get("_cache_state") or "LIVE") if rows else "EMPTY",
                fetched_at=wrapped["fetched_at"], age_seconds=wrapped.get("_cache_age_seconds", 0),
                stale_after_seconds=45, records=len(rows),
                note="Labeled entity/address transfers above threshold; exchange, custody and internal movements require classification.",
            ).to_dict(),
            "data": rows,
        }
    except Exception as exc:
        return {
            "status": FeedStatus(provider="Arkham", dataset="labeled_transfers", state="ERROR",
                                 stale_after_seconds=45, note=f"{type(exc).__name__}: {exc}").to_dict(),
            "data": [],
        }


def fetch_nansen_smart_money(limit: int = 50) -> Dict[str, Any]:
    key = os.getenv("NANSEN_API_KEY", "").strip()
    if not key:
        return _not_configured("Nansen", "smart_money", "NANSEN_API_KEY", 120)
    headers = {"Content-Type": "application/json", "apikey": key, "Accept": "application/json"}
    body = {
        "chains": ["ethereum", "solana", "base", "arbitrum"],
        "filters": {
            "include_smart_money_labels": ["Fund", "Smart Trader"],
            "include_stablecoins": False,
            "value_usd": {"min": 10_000},
        },
        "pagination": {"page": 1, "per_page": min(limit, 100)},
        "order_by": [{"field": "balance_24h_percent_change", "direction": "DESC"}],
    }
    try:
        wrapped = _cached_json_request(
            cache_key=f"nansen_holdings_{limit}", ttl_seconds=60, method="POST",
            url="https://api.nansen.ai/api/v1/smart-money/holdings", headers=headers, json_body=body, timeout=25,
        )
        rows = []
        for r in _extract_rows(wrapped["payload"]):
            change = _as_float(r.get("balance_24h_percent_change"))
            rows.append({
                "event_type": "SMART_MONEY",
                "provider": "Nansen",
                "ticker": r.get("token_symbol") or "—",
                "timestamp": wrapped["fetched_at"],
                "chain": r.get("chain"),
                "value_usd": _as_float(r.get("value_usd"), 0.0) or 0.0,
                "change_24h_pct": change,
                "holders_count": r.get("holders_count"),
                "share_of_holdings_pct": _as_float(r.get("share_of_holdings_percent")),
                "market_cap_usd": _as_float(r.get("market_cap_usd")),
                "classification": "ACCUMULATING" if change is not None and change > 0 else ("REDUCING" if change is not None and change < 0 else "UNCHANGED"),
                "observed": True,
                "position_inference": "PROVIDER_CLASSIFIED_SMART_MONEY",
            })
        return {
            "status": FeedStatus(provider="Nansen", dataset="smart_money", state=(wrapped.get("_cache_state") or "LIVE") if rows else "EMPTY",
                                 fetched_at=wrapped["fetched_at"], age_seconds=wrapped.get("_cache_age_seconds", 0),
                                 stale_after_seconds=120, records=len(rows),
                                 note="Provider-classified Funds/Smart Traders; not a guarantee of future performance.").to_dict(),
            "data": rows,
        }
    except Exception as exc:
        return {
            "status": FeedStatus(provider="Nansen", dataset="smart_money", state="ERROR",
                                 stale_after_seconds=120, note=f"{type(exc).__name__}: {exc}").to_dict(),
            "data": [],
        }


def _ticker_shortlist(desk: Dict[str, Any]) -> List[str]:
    env = os.getenv("WARROOM_WATCHLIST", "").strip()
    if env:
        return [x.strip().upper() for x in env.split(",") if x.strip()]
    out: List[str] = []
    for item in desk.get("alpha") or []:
        if item.get("tk"):
            out.append(str(item["tk"]))
    for market in (desk.get("markets") or {}).values():
        for setup in market.get("setups") or []:
            if setup.get("tk"):
                out.append(str(setup["tk"]))
    return list(dict.fromkeys(out))[:30]


def collect_institutional_data(desk: Dict[str, Any]) -> Dict[str, Any]:
    shortlist = _ticker_shortlist(desk)
    jobs = {
        "options": (fetch_unusual_whales_options, ()),
        "stream": (fetch_massive_stream_bridge, (shortlist,)),
        "uw_dark": (fetch_unusual_whales_dark_pool, ()),
        "sec": (fetch_sec_filings, (shortlist,)),
        "smart": (fetch_nansen_smart_money, ()),
        "arkham": (fetch_arkham_transfers, ()),
    }
    results: Dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {pool.submit(fn, *args): name for name, (fn, args) in jobs.items()}
        for fut in as_completed(futures):
            name=futures[fut]
            try: results[name]=fut.result()
            except Exception as exc: results[name]={"status":FeedStatus(name,name,"ERROR",note=f"{type(exc).__name__}: {exc}").to_dict(),"data":[]}

    options = results["options"]
    stream = results["stream"]
    uw_dark = results["uw_dark"]
    sec = results["sec"]
    smart = results["smart"]
    arkham = results["arkham"]
    stream_options = [x for x in stream.get("data") or [] if x.get("event_type") == "OPTIONS_FLOW"]
    stream_dark = [x for x in stream.get("data") or [] if x.get("event_type") == "DARK_POOL"]

    # Massive REST is an isolated raw fallback; skip it when another TRF source is active.
    if uw_dark.get("status", {}).get("state") in {"NOT_CONFIGURED", "NOT_ENTITLED", "ACTION_REQUIRED", "ERROR", "EMPTY", "OFFLINE"} and not stream_dark:
        massive = fetch_massive_dark_pool(shortlist)
    else:
        massive = {
            "status": FeedStatus(provider="Massive", dataset="trf_trades", state="STANDBY",
                                 stale_after_seconds=45, note="Another TRF source is active; Massive REST retained as fallback.").to_dict(),
            "data": [],
        }

    dark_rows = (stream_dark + (uw_dark.get("data") or []) + (massive.get("data") or []))[:300]
    option_rows = (stream_options + (options.get("data") or []))[:300]
    events = option_rows + dark_rows + (sec.get("data") or []) + (smart.get("data") or []) + (arkham.get("data") or [])
    events.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)

    statuses = [options["status"], stream["status"], uw_dark["status"], massive["status"], sec["status"], smart["status"], arkham["status"]]
    active = sum(1 for x in statuses if x.get("state") == "LIVE")
    stale = sum(1 for x in statuses if x.get("state") == "STALE")
    errors = sum(1 for x in statuses if x.get("state") == "ERROR")
    sec_state = str((sec.get("status") or {}).get("state") or "").upper()
    if events and (active or stale):
        overall = "LIVE" if active >= 2 else "PARTIAL"
    elif sec_state in {"LIVE", "STALE", "EMPTY", "NO_SIGNAL"}:
        # Public filing transport is healthy; an empty event set means no new qualifying filing.
        overall = "NO_SIGNAL"
    elif sec_state == "ACTION_REQUIRED":
        overall = "ACTION_REQUIRED"
    elif active or stale:
        overall = "PARTIAL"
    elif errors:
        overall = "ERROR"
    else:
        overall = "NOT_ENTITLED"
    return {
        "generated": _utc_now(), "overall_state": overall, "watchlist": shortlist,
        "status_counts": {"live": active, "stale": stale, "error": errors, "total": len(statuses)},
        "statuses": statuses, "options_flow": option_rows, "dark_pool": dark_rows,
        "sec_filings": sec.get("data") or [], "smart_money": smart.get("data") or [],
        "arkham_transfers": arkham.get("data") or [], "events": events[:300],
        "rules": {"no_synthetic": True, "intent_from_single_event": False, "failure_isolated": True},
    }

