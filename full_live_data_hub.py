"""Full live-data coverage hub for War Room OS.

This module fills the non-price context required by every workspace while preserving four
production invariants:
1) no synthetic fallback;
2) no missing-as-neutral;
3) provider/reporting latency is explicit;
4) a failed optional provider cannot crash the dashboard.

Free/public sources are used where an official interface exists. Licensed or exchange-controlled
feeds are exposed through adapters/bridges and remain NOT_CONFIGURED until credentials are set.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import csv, io, json, math, os, time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache" / "full_live_hub"
CACHE.mkdir(parents=True, exist_ok=True)


@dataclass
class Status:
    provider: str
    dataset: str
    state: str
    observed: bool = True
    fetched_at: Optional[str] = None
    age_seconds: Optional[float] = None
    stale_after_seconds: Optional[int] = None
    records: int = 0
    note: str = ""
    endpoint: str = ""
    required_for: Optional[List[str]] = None
    def to_dict(self): return asdict(self)


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def f(value, default=None):
    try:
        x=float(value)
        return x if math.isfinite(x) else default
    except (TypeError,ValueError): return default


def session():
    s=requests.Session(); retry=Retry(total=1,connect=1,read=1,backoff_factor=.25,
        status_forcelist=(429,500,502,503,504),allowed_methods=frozenset({"GET","POST"}),raise_on_status=False)
    adapter=HTTPAdapter(max_retries=retry,pool_connections=30,pool_maxsize=40)
    s.mount("https://",adapter);s.mount("http://",adapter)
    s.headers.update({"User-Agent":"WarRoomOS/2.1 full-live-hub"});return s
HTTP=session()


def network_enabled():
    return os.getenv("WARROOM_NETWORK_MODE", "live").strip().lower() not in {"offline", "disabled", "0", "false"}


def safe_name(x): return "".join(c if c.isalnum() or c in "-_" else "_" for c in x)[:120]
def cache_path(key): return CACHE/f"{safe_name(key)}.json"

def read_cache(key):
    p=cache_path(key)
    if not p.exists(): return None
    try:
        obj=json.loads(p.read_text(encoding="utf-8"));obj["_age_seconds"]=max(0,time.time()-p.stat().st_mtime);return obj
    except Exception:return None

def write_cache(key,obj):
    p=cache_path(key);tmp=p.with_suffix(".tmp");tmp.write_text(json.dumps(obj,default=str,separators=(",",":")),encoding="utf-8");tmp.replace(p)


def request_json(provider,dataset,url,*,cache_key,ttl,stale_after,method="GET",headers=None,params=None,json_body=None,timeout=7):
    cached=read_cache(cache_key)
    if cached and cached["_age_seconds"]<=ttl:
        return {"state":"LIVE","payload":cached.get("payload"),"fetched_at":cached.get("fetched_at"),"age_seconds":cached["_age_seconds"],"note":"fresh cache"}
    if not network_enabled():
        if cached:
            return {"state":"STALE","payload":cached.get("payload"),"fetched_at":cached.get("fetched_at"),"age_seconds":cached["_age_seconds"],"note":"offline mode: last-good cache"}
        return {"state":"OFFLINE","payload":None,"fetched_at":None,"age_seconds":None,"note":"WARROOM_NETWORK_MODE=offline"}
    try:
        r=HTTP.request(method,url,headers=headers or {},params=params,json=json_body,timeout=min(timeout,float(os.getenv("WARROOM_HTTP_TIMEOUT","8"))))
        if not 200<=r.status_code<300: raise RuntimeError(f"HTTP {r.status_code}: {r.text[:180]}")
        payload=r.json();wrapped={"payload":payload,"fetched_at":now_iso()};write_cache(cache_key,wrapped)
        return {"state":"LIVE","payload":payload,"fetched_at":wrapped["fetched_at"],"age_seconds":0,"note":"network"}
    except Exception as exc:
        stale=read_cache(cache_key)
        if stale:
            return {"state":"STALE","payload":stale.get("payload"),"fetched_at":stale.get("fetched_at"),"age_seconds":stale["_age_seconds"],"note":f"last-good after {type(exc).__name__}: {exc}"}
        return {"state":"ERROR","payload":None,"fetched_at":None,"age_seconds":None,"note":f"{type(exc).__name__}: {exc}"}



def request_many(specs: Dict[str, Dict[str, Any]], max_workers: int = 12) -> Dict[str, Dict[str, Any]]:
    if not specs:
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(specs))) as pool:
        futures = {pool.submit(request_json, **kwargs): name for name, kwargs in specs.items()}
        for fut in as_completed(futures):
            name = futures[fut]
            try: out[name] = fut.result()
            except Exception as exc: out[name] = {"state":"ERROR","payload":None,"note":f"{type(exc).__name__}: {exc}"}
    return out

def status(result,provider,dataset,records,stale_after,note,endpoint,required_for=None):
    state=result.get("state","ERROR")
    if state=="LIVE" and records==0: state="EMPTY"
    return Status(provider,dataset,state,True,result.get("fetched_at"),result.get("age_seconds"),stale_after,records,
                  f"{note} · {result.get('note','')}".strip(" ·"),endpoint,required_for).to_dict()


def not_configured(provider,dataset,env_name,required_for,stale_after=300,note="",state="NOT_CONFIGURED"):
    return {"status":Status(provider,dataset,state,True,None,None,stale_after,0,
            f"Set {env_name}. {note}".strip(),required_for=required_for).to_dict(),"data":[]}


def rows(payload):
    if isinstance(payload,list): return [x for x in payload if isinstance(x,dict)]
    if not isinstance(payload,dict): return []
    for path in (("data",),("results",),("items",),("records",),("response","data"),("data","items"),("data","data")):
        cur=payload
        for key in path:
            if not isinstance(cur,dict) or key not in cur: cur=None;break
            cur=cur[key]
        if isinstance(cur,list): return [x for x in cur if isinstance(x,dict)]
    return []


def shortlist(desk,limit=12):
    out=[]
    for market in (desk.get("markets") or {}).values():
        for x in market.get("setups") or []:
            t=str(x.get("tk") or "").upper()
            if t and ".JK" not in t and "=" not in t and "-" not in t and t not in out: out.append(t)
    for x in desk.get("alpha") or []:
        t=str(x.get("tk") or "").upper()
        if t and ".JK" not in t and "=" not in t and "-" not in t and t not in out: out.append(t)
    if not out: out=["SPY","QQQ","NVDA","AMD","TSLA"]
    return out[:limit]


# ----------------------------- SEC XBRL fundamentals -----------------------------
def sec_headers():
    ua=os.getenv("WARROOM_SEC_USER_AGENT","").strip()
    return {"User-Agent":ua,"Accept":"application/json","Accept-Encoding":"gzip, deflate"}


def sec_ticker_map():
    ua=os.getenv("WARROOM_SEC_USER_AGENT","").strip()
    if not ua:return None,None
    url="https://www.sec.gov/files/company_tickers.json"
    r=request_json("SEC EDGAR","ticker_map",url,cache_key="sec_ticker_map",ttl=86400,stale_after=172800,headers=sec_headers(),timeout=8)
    payload=r.get("payload") or {}; out={}
    for x in payload.values() if isinstance(payload,dict) else []:
        if isinstance(x,dict) and x.get("ticker"):
            out[str(x["ticker"]).upper()]={"cik":str(x.get("cik_str") or "").zfill(10),"title":x.get("title")}
    return r,out


def latest_fact(fact:Dict[str,Any],forms=("10-Q","10-K","20-F","40-F","8-K")):
    candidates=[]
    for unit,vals in (fact.get("units") or {}).items():
        for x in vals if isinstance(vals,list) else []:
            if x.get("form") not in forms or f(x.get("val")) is None: continue
            candidates.append({**x,"unit":unit})
    if not candidates:return None
    candidates.sort(key=lambda x:(str(x.get("filed") or ""),str(x.get("end") or ""),str(x.get("fy") or "")),reverse=True)
    x=candidates[0]
    return {"value":f(x.get("val")),"unit":x.get("unit"),"period_end":x.get("end"),"filed":x.get("filed"),"form":x.get("form"),"fy":x.get("fy"),"fp":x.get("fp"),"frame":x.get("frame")}


FACT_TAGS={
 "revenue":["RevenueFromContractWithCustomerExcludingAssessedTax","Revenues","SalesRevenueNet"],
 "net_income":["NetIncomeLoss","ProfitLoss"],"operating_income":["OperatingIncomeLoss"],
 "assets":["Assets"],"liabilities":["Liabilities"],"equity":["StockholdersEquity","StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
 "cash":["CashAndCashEquivalentsAtCarryingValue","CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
 "operating_cash_flow":["NetCashProvidedByUsedInOperatingActivities"],
 "capex":["PaymentsToAcquirePropertyPlantAndEquipment"],"shares":["CommonStockSharesOutstanding","EntityCommonStockSharesOutstanding"],
}


def fetch_sec_fundamentals(tickers):
    ua=os.getenv("WARROOM_SEC_USER_AGENT","").strip()
    if not ua:return not_configured("SEC EDGAR","company_facts","WARROOM_SEC_USER_AGENT",["alpha_center","us_stocks","company_intel","institutional"], note="Public API; provide a descriptive user-agent with contact email for fair-access compliance.", state="ACTION_REQUIRED")
    map_result,mapping=sec_ticker_map(); mapping=mapping or {}
    specs={}
    metadata={}
    for ticker in tickers[:10]:
        info=mapping.get(ticker)
        if not info: continue
        url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{info['cik']}.json"
        specs[ticker]=dict(provider="SEC EDGAR",dataset=f"companyfacts_{ticker}",url=url,cache_key=f"sec_facts_{ticker}",ttl=900,stale_after=86400,headers=sec_headers(),timeout=8)
        metadata[ticker]=(info,url)
    fetched=request_many(specs,max_workers=6)
    data=[];statuses=[]
    for ticker,r in fetched.items():
        info,url=metadata[ticker]; facts=(r.get("payload") or {}).get("facts") or {}; flattened={}
        for namespace in ("us-gaap","ifrs-full","dei"):
            nf=facts.get(namespace) or {}
            for name,tags in FACT_TAGS.items():
                if name in flattened: continue
                for tag in tags:
                    if tag in nf:
                        val=latest_fact(nf[tag])
                        if val: flattened[name]=val;break
        if flattened:
            ocf=(flattened.get("operating_cash_flow") or {}).get("value");capex=(flattened.get("capex") or {}).get("value")
            if ocf is not None and capex is not None: flattened["free_cash_flow_proxy"]={"value":ocf-capex,"unit":"USD","note":"latest filed OCF minus latest filed capex; verify matching periods"}
            data.append({"provider":"SEC EDGAR","ticker":ticker,"company":info.get("title"),"cik":info["cik"],"facts":flattened,
                         "semantics":"Filed XBRL facts; reporting periods and units must be checked before comparison."})
        statuses.append(status(r,"SEC EDGAR",f"companyfacts_{ticker}",1 if flattened else 0,86400,"Official filed XBRL company facts.",url,["alpha_center","us_stocks","company_intel"]))
    if map_result: statuses.insert(0,status(map_result,"SEC EDGAR","ticker_map",len(mapping),172800,"Official ticker-to-CIK mapping.","https://www.sec.gov/files/company_tickers.json",["institutional","company_intel"]))
    state="LIVE" if data else "OFFLINE" if any(x.get("state")=="OFFLINE" for x in statuses) else "EMPTY"
    return {"status":Status("SEC EDGAR","company_facts_bundle",state,records=len(data),fetched_at=now_iso(),stale_after_seconds=86400,required_for=["alpha_center","us_stocks","company_intel"]).to_dict(),"statuses":statuses,"data":data}


# ----------------------------- Intrinio context -----------------------------
def fetch_intrinio_context(tickers,etfs):
    key=os.getenv("INTRINIO_API_KEY","").strip()
    if not key:return not_configured("Intrinio","fundamentals_etf_earnings_ownership","INTRINIO_API_KEY",["alpha_center","us_stocks","flow_rotation","company_intel"],3600,state="NOT_ENTITLED")
    base=os.getenv("INTRINIO_BASE_URL","https://api-v2.intrinio.com").rstrip("/");headers={"Accept":"application/json"}
    specs={}; meta={}
    for ticker in tickers[:6]:
        for kind,path,params,stale in (
            ("earnings",f"/securities/{ticker}/earnings/latest",{},21600),
            ("ownership",f"/securities/{ticker}/institutional_ownership",{"page_size":100},86400),
            ("eps_estimates",f"/securities/{ticker}/zacks/eps_estimates",{"page_size":40},21600),
        ):
            name=f"{kind}_{ticker}";url=base+path
            specs[name]=dict(provider="Intrinio",dataset=name,url=url,cache_key=f"intrinio_{name}",ttl=300,stale_after=stale,params={"api_key":key,**params},headers=headers,timeout=8)
            meta[name]=(kind,ticker,url,stale)
    start_date=(datetime.now(timezone.utc)-timedelta(days=45)).date().isoformat()
    for etf in etfs[:12]:
        name=f"etf_nav_flow_{etf}";url=f"{base}/etfs/{etf}/historical_nav_flows"
        specs[name]=dict(provider="Intrinio",dataset=name,url=url,cache_key=f"intrinio_{name}",ttl=300,stale_after=21600,params={"api_key":key,"start_date":start_date,"page_size":100},headers=headers,timeout=8)
        meta[name]=(name,etf,url,21600)
    fetched=request_many(specs,max_workers=12);statuses=[]
    companies={t:{"ticker":t,"earnings":None,"ownership":[],"eps_estimates":[]} for t in tickers[:6]}
    etf_rows=[]
    for name,r in fetched.items():
        kind,symbol,url,stale=meta[name]
        if kind=="earnings": companies[symbol]["earnings"]=r.get("payload"); n=1 if r.get("payload") else 0; note="Latest earnings calendar/record."; req=["us_stocks","company_intel"]
        elif kind=="ownership": companies[symbol]["ownership"]=rows(r.get("payload"))[:100]; n=len(companies[symbol]["ownership"]); note="Institutional ownership; 13F reporting lag applies."; req=["institutional","company_intel"]
        elif kind=="eps_estimates": companies[symbol]["eps_estimates"]=rows(r.get("payload"))[:40]; n=len(companies[symbol]["eps_estimates"]); note="Analyst EPS estimates; revisions are expectations, not facts."; req=["alpha_center","us_stocks","company_intel"]
        else:
            rr=rows(r.get("payload"));etf_rows.append({"ticker":symbol,"rows":rr});n=len(rr);note="NAV, shares outstanding and net-flow history.";req=["mission_control","us_stocks","flow_rotation"]
        statuses.append(status(r,"Intrinio",name,n,stale,note,url,req))
    results=list(companies.values())
    live=any(x.get("state") in {"LIVE","STALE"} for x in statuses)
    return {"status":Status("Intrinio","context_bundle","LIVE" if live else "EMPTY",records=len(results)+len(etf_rows),fetched_at=now_iso(),stale_after_seconds=21600,required_for=["alpha_center","us_stocks","flow_rotation","company_intel"]).to_dict(),"statuses":statuses,"companies":results,"etf_flows":etf_rows}


# ----------------------------- EIA configurable official API -----------------------------
DEFAULT_EIA_REQUESTS=[
 {"name":"weekly_petroleum_stocks","path":"/v2/petroleum/stoc/wstk/data/","params":{"frequency":"weekly","data[0]":"value","sort[0][column]":"period","sort[0][direction]":"desc","offset":0,"length":100}},
 {"name":"weekly_natural_gas_storage","path":"/v2/natural-gas/stor/wkly/data/","params":{"frequency":"weekly","data[0]":"value","sort[0][column]":"period","sort[0][direction]":"desc","offset":0,"length":100}},
]

def fetch_eia_context():
    key=os.getenv("EIA_API_KEY","").strip()
    if not key:return not_configured("EIA","energy_physical","EIA_API_KEY",["commodities","early_warning"],86400,"Use EIA_REQUESTS_JSON to narrow products/areas.",state="ACTION_REQUIRED")
    try: specs=json.loads(os.getenv("EIA_REQUESTS_JSON",json.dumps(DEFAULT_EIA_REQUESTS)))
    except Exception: specs=DEFAULT_EIA_REQUESTS
    base=os.getenv("EIA_BASE_URL","https://api.eia.gov").rstrip("/"); calls={};meta={}
    for spec in specs[:10]:
        name=str(spec.get("name") or "eia_series");url=base+str(spec.get("path") or "");params={"api_key":key,**(spec.get("params") or {})}
        calls[name]=dict(provider="EIA",dataset=name,url=url,cache_key=f"eia_{name}",ttl=1800,stale_after=172800,params=params,timeout=10);meta[name]=(url,spec)
    fetched=request_many(calls,max_workers=8);data=[];statuses=[]
    for name,r in fetched.items():
        url,spec=meta[name];rr=rows(r.get("payload"));data.append({"name":name,"rows":rr,"route":spec.get("path")})
        statuses.append(status(r,"EIA",name,len(rr),172800,"Official physical energy data; release cadence is not tick-live.",url,["commodities","early_warning"]))
    state="LIVE" if any(x["rows"] for x in data) else "OFFLINE" if any(x.get("state")=="OFFLINE" for x in statuses) else "EMPTY"
    return {"status":Status("EIA","energy_physical",state,records=sum(len(x["rows"]) for x in data),fetched_at=now_iso(),stale_after_seconds=172800,required_for=["commodities","early_warning"]).to_dict(),"statuses":statuses,"data":data}


# ----------------------------- existing public specialist feeds -----------------------------
def _cftc_csv_fallback(dataset: str, resource_url: str) -> dict:
    """Official Socrata CSV fallback when the JSON endpoint is blocked or rate-limited."""
    key = f"cftc_csv_{dataset}"
    cached = read_cache(key)
    if cached and cached.get("_age_seconds", 1e9) <= 21600:
        return {"state":"LIVE","payload":cached.get("payload") or [],"fetched_at":cached.get("fetched_at"),"age_seconds":cached.get("_age_seconds"),"note":"fresh official CSV cache"}
    csv_url = resource_url.rsplit('.', 1)[0] + '.csv'
    try:
        response = HTTP.get(csv_url, params={"$limit":1000,"$order":"report_date_as_yyyy_mm_dd DESC"}, timeout=min(8,float(os.getenv("WARROOM_HTTP_TIMEOUT","8"))))
        if not 200 <= response.status_code < 300:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:120]}")
        parsed = list(csv.DictReader(io.StringIO(response.text)))
        wrapped={"payload":parsed,"fetched_at":now_iso()};write_cache(key,wrapped)
        return {"state":"LIVE","payload":parsed,"fetched_at":wrapped["fetched_at"],"age_seconds":0,"note":"official Socrata CSV fallback"}
    except Exception as exc:
        stale=read_cache(key)
        if stale:
            return {"state":"STALE","payload":stale.get("payload") or [],"fetched_at":stale.get("fetched_at"),"age_seconds":stale.get("_age_seconds"),"note":f"last-good CSV after {type(exc).__name__}"}
        return {"state":"ERROR","payload":[],"fetched_at":None,"age_seconds":None,"note":f"CSV fallback {type(exc).__name__}: {exc}"}


def fetch_cftc_context():
    datasets={
        "tff_futures":("https://publicreporting.cftc.gov/resource/gpe5-46if.json","Traders in Financial Futures: dealer, asset manager, leveraged funds and other reportables."),
        "disaggregated_futures":("https://publicreporting.cftc.gov/resource/72hh-3qpy.json","Physical commodities: producer, swap dealer, managed money and other reportables."),
    }
    specs={name:dict(provider="CFTC PRE",dataset=name,url=url,cache_key=f"cftc_{name}",ttl=21600,stale_after=8*86400,
                     params={"$limit":1000,"$order":"report_date_as_yyyy_mm_dd DESC"},timeout=8) for name,(url,_) in datasets.items()}
    fetched=request_many(specs,max_workers=2);data={};statuses=[]
    for name,r in fetched.items():
        url,note=datasets[name];rr=rows(r.get("payload"))
        if not rr:
            fallback=_cftc_csv_fallback(name,url)
            if rows(fallback.get("payload")):
                r=fallback;rr=rows(r.get("payload"))
        latest=max((str(x.get("report_date_as_yyyy_mm_dd") or "") for x in rr),default="")
        current=[x for x in rr if str(x.get("report_date_as_yyyy_mm_dd") or "")==latest] if latest else []
        data[name]={"report_date":latest,"rows":current,"semantics":"Weekly reported positions; not intraday positioning."}
        statuses.append(status(r,"CFTC PRE",name,len(current),8*86400,note,url,["commodities","fx","flow_rotation"]))
    state="LIVE" if any(v["rows"] for v in data.values()) else "OFFLINE" if any(x.get("state")=="OFFLINE" for x in statuses) else "EMPTY"
    return {"status":Status("CFTC PRE","COT",state,records=sum(len(v["rows"]) for v in data.values()),fetched_at=now_iso(),stale_after_seconds=8*86400,note="Weekly reporting lag is explicit.",required_for=["commodities","fx","flow_rotation"]).to_dict(),"statuses":statuses,"data":data}


def fetch_defillama_context():
    chains_url="https://api.llama.fi/v2/chains"
    chain_result=request_json("DeFiLlama","chains",chains_url,cache_key="defillama_chains",ttl=600,stale_after=1800,timeout=8)
    chain_rows=rows(chain_result.get("payload"));by_name={str(x.get("name") or "").lower():x for x in chain_rows}
    mapping={"BTC-USD":"bitcoin","ETH-USD":"ethereum","SOL-USD":"solana","ARB-USD":"arbitrum","OP-USD":"optimism"}
    specs={};meta={}
    for ticker,name in mapping.items():
        url=f"https://api.llama.fi/v2/historicalChainTvl/{name}"
        specs[ticker]=dict(provider="DeFiLlama",dataset=f"history_{name}",url=url,cache_key=f"defillama_hist_{name}",ttl=600,stale_after=1800,timeout=8);meta[ticker]=(name,url)
    hist=request_many(specs,max_workers=5);out={};statuses=[status(chain_result,"DeFiLlama","chains",len(chain_rows),1800,"Current chain TVL registry.",chains_url,["crypto","flow_rotation"])]
    for ticker,(name,url) in meta.items():
        current=by_name.get(name,{}) ; hr=hist.get(ticker,{}) ; hrows=hr.get("payload") if isinstance(hr.get("payload"),list) else []
        change=None
        if len(hrows)>=8:
            a=f(hrows[-1].get("tvl"));b=f(hrows[-8].get("tvl"));change=(a/b-1)*100 if a is not None and b not in (None,0) else None
        out[ticker]={"tvl_usd":f(current.get("tvl")),"protocol_tvl_change_7d":change,"source":"DeFiLlama","semantics":"Protocol TVL is not whale positioning."}
        statuses.append(status(hr,"DeFiLlama",f"history_{name}",len(hrows),1800,"Protocol TVL history.",url,["crypto","flow_rotation"]))
    state="LIVE" if any(v.get("tvl_usd") is not None for v in out.values()) else "OFFLINE" if any(x.get("state")=="OFFLINE" for x in statuses) else "EMPTY"
    return {"status":Status("DeFiLlama","protocol_tvl",state,records=len(out),fetched_at=now_iso(),stale_after_seconds=1800,note="Protocol TVL is not wallet-level Smart Money flow.",required_for=["crypto","flow_rotation"]).to_dict(),"statuses":statuses,"data":out}


# ----------------------------- local persistent bridges -----------------------------
def fetch_bridge(provider,dataset,url_env,token_env,required_for,params=None,stale_after=30):
    url=os.getenv(url_env,"").strip()
    if not url:return not_configured(provider,dataset,url_env,required_for,stale_after,state="NOT_ENTITLED")
    token=os.getenv(token_env,"").strip();headers={"Authorization":f"Bearer {token}"} if token else {}
    r=request_json(provider,dataset,url,cache_key=f"bridge_{provider}_{dataset}",ttl=3,stale_after=stale_after,headers=headers,params=params or {},timeout=5)
    rr=rows(r.get("payload"));return {"status":status(r,provider,dataset,len(rr),stale_after,"Persistent bridge snapshot.",url,required_for),"data":rr,"raw":r.get("payload")}


def fetch_databento_bridge():
    return fetch_bridge("Databento","futures_options_statistics","DATABENTO_STREAM_BRIDGE_URL","DATABENTO_STREAM_BRIDGE_TOKEN",
                        ["commodities","fx","derivatives_squeeze"],{"limit":1500},30)

def fetch_idx_bridge():
    return fetch_bridge("IDX licensed feed","broker_foreign_orderbook","IDX_DATA_BRIDGE_URL","IDX_DATA_BRIDGE_TOKEN",
                        ["ihsg","flow_rotation","institutional"],{"limit":5000},30)


# ----------------------------- coverage -----------------------------
REQUIREMENTS={
 "mission_control":["core_prices","macro_observations","breadth","rotation","institutional_events","derivatives_state"],
 "macro_regime":["macro_observations","rates","credit","liquidity","rotation"],
 "early_warning":["breadth","volatility","credit","funding_stress","derivatives_state"],
 "alpha_center":["fundamentals","earnings_estimates","ownership","institutional_events","price_state"],
 "institutional":["options_flow","trf_prints","sec_filings","ownership","smart_money","idx_broker"],
 "derivatives_squeeze":["oi","funding","long_short","taker","short_interest","borrow","option_surface","greeks","liquidations","futures_statistics"],
 "us_stocks":["prices","breadth","fundamentals","earnings_estimates","etf_flow","options","trf_prints","sec_filings"],
 "ihsg":["prices","foreign_flow","broker_summary","free_float","controller","fx_macro"],
 "crypto":["spot","perp_oi","funding","liquidations","options","protocol_tvl","smart_money","transfers"],
 "commodities":["futures_price","cot","curve","inventory","physical_flow","futures_statistics"],
 "fx":["spot","rate_differential","cot","options_vol","central_bank","futures_statistics"],
 "flow_rotation":["price_rotation","etf_flow","sector_options_flow","cot","onchain","idx_foreign"],
 "company_intel":["fundamentals","earnings","ownership","filings","options","short_interest","trf","price_state"],
 "validation":["source_lineage","freshness","frozen_spec","oos","calibration","drift"],
}

# Only these datasets determine whether a workspace has usable core data. Licensed enrichments
# may make the workspace PARTIAL, but can no longer turn a healthy price/macro tab into NO_DATA.
CORE_DATASETS_BY_TAB = {
 "mission_control":{"macro_observations","market_breadth","cross_asset_rotation","core_prices"},
 "macro_regime":{"macro_observations","liquidity_state"},
 "early_warning":{"market_breadth","macro_observations","liquidity_state"},
 "alpha_center":{"price_state","core_prices"},
 "institutional":{"company_facts","sec_filings"},
 "derivatives_squeeze":{"COT","futures_options_statistics"},
 "us_stocks":{"core_prices","market_breadth","price_state"},
 "ihsg":{"core_prices","market_breadth","price_state"},
 "crypto":{"core_prices","market_breadth"},
 "commodities":{"core_prices","COT"},
 "fx":{"core_prices","COT"},
 "flow_rotation":{"cross_asset_rotation","core_prices"},
 "company_intel":{"price_state","core_prices"},
 "validation":{"source_lineage"},
}


def collect_full_live_data(desk:Dict[str,Any]):
    tickers=shortlist(desk); etfs=[x.strip().upper() for x in os.getenv("WARROOM_ETF_FLOW_WATCHLIST","SPY,QQQ,IWM,SMH,XLF,XLE,XLK,XLI,GLD,TLT,EEM,EIDO").split(",") if x.strip()]
    tasks={
      "sec_fundamentals":(fetch_sec_fundamentals,(tickers,)),"intrinio":(fetch_intrinio_context,(tickers,etfs)),
      "eia":(fetch_eia_context,()),"cftc":(fetch_cftc_context,()),"defillama":(fetch_defillama_context,()),
      "databento":(fetch_databento_bridge,()),"idx":(fetch_idx_bridge,()),
    }
    results={}
    with ThreadPoolExecutor(max_workers=7) as pool:
        futures={pool.submit(fn,*args):name for name,(fn,args) in tasks.items()}
        for fut in as_completed(futures):
            name=futures[fut]
            try: results[name]=fut.result()
            except Exception as exc: results[name]={"status":Status(name,name,"ERROR",note=f"{type(exc).__name__}: {exc}").to_dict(),"data":[]}
    statuses=[]
    for result in results.values():
        statuses.extend(result.get("statuses") or [])
        if result.get("status"): statuses.append(result["status"])
    # Include core derived coverage in the same registry.
    macro=desk.get("macro_observations") or {}; breadth=desk.get("market_breadth") or {}; rotation=desk.get("rotation_snapshot") or {}
    loaded_markets={k:int((v.get("funnel") or {}).get("universe") or 0) for k,v in (desk.get("markets") or {}).items()}
    core_price_count=sum(loaded_markets.values())
    breadth_count=sum(int((v or {}).get("coverage") or 0) for v in breadth.values())
    setup_count=sum(len(v.get("setups") or []) for v in (desk.get("markets") or {}).values())
    liq=(desk.get("systemic") or {}).get("liquidity")
    liq_state="LIVE" if liq and str(liq).upper() not in {"NO_DATA","NONE","—","INITIALIZING"} else "NO_DATA"
    statuses += [
      Status("FRED","macro_observations","LIVE" if macro else "NO_DATA",records=len(macro),fetched_at=(desk.get("meta") or {}).get("generated"),stale_after_seconds=86400,note="Latest observations from loaded official macro series.",required_for=["mission_control","macro_regime","early_warning"]).to_dict(),
      Status("War Room derived","market_breadth","LIVE" if breadth_count else "NO_DATA",records=breadth_count,fetched_at=(desk.get("meta") or {}).get("generated"),stale_after_seconds=300,note="Derived only from currently loaded universe; coverage disclosed.",required_for=["mission_control","early_warning","us_stocks","ihsg","crypto"]).to_dict(),
      Status("War Room derived","cross_asset_rotation","LIVE" if rotation.get("rows") else "NO_DATA",records=len(rotation.get("rows") or []),fetched_at=(desk.get("meta") or {}).get("generated"),stale_after_seconds=300,note="Relative-price rotation, not dollar flow.",required_for=["mission_control","macro_regime","flow_rotation"]).to_dict(),
      Status("War Room core","core_prices","LIVE" if core_price_count else "NO_DATA",records=core_price_count,fetched_at=(desk.get("meta") or {}).get("generated"),stale_after_seconds=600,note=f"Loaded per market: {loaded_markets}",required_for=["mission_control","alpha_center","us_stocks","ihsg","crypto","commodities","fx","flow_rotation","company_intel"]).to_dict(),
      Status("War Room core","price_state","LIVE" if setup_count else ("NO_SIGNAL" if core_price_count else "NO_DATA"),records=setup_count,fetched_at=(desk.get("meta") or {}).get("generated"),stale_after_seconds=600,note="NO_SIGNAL means price data loaded but no setup passed current gates.",required_for=["alpha_center","us_stocks","ihsg","company_intel"]).to_dict(),
      Status("Treasury/NY Fed/FRED","liquidity_state",liq_state,records=1 if liq_state=="LIVE" else 0,fetched_at=(desk.get("meta") or {}).get("generated"),stale_after_seconds=86400,note=str(liq or "No usable liquidity observation"),required_for=["mission_control","macro_regime","early_warning"]).to_dict(),
      Status("War Room","source_lineage","LIVE",records=len(statuses),fetched_at=(desk.get("meta") or {}).get("generated"),stale_after_seconds=86400,note="Provider, state and reporting lag registry.",required_for=["validation"]).to_dict(),
    ]
    live=sum(1 for x in statuses if x.get("state")=="LIVE");stale=sum(1 for x in statuses if x.get("state")=="STALE");errors=sum(1 for x in statuses if x.get("state")=="ERROR")
    configured=[x for x in statuses if x.get("state")!="NOT_CONFIGURED"]
    overall="LIVE" if configured and all(x.get("state") in {"LIVE","STANDBY"} for x in configured) else "PARTIAL" if live or stale else "ERROR" if errors else "NOT_CONFIGURED"
    tab_coverage={}
    bad={"NOT_CONFIGURED","ACTION_REQUIRED","NOT_ENTITLED","NO_DATA","EMPTY","ERROR","OFFLINE"}
    usable={"LIVE","STALE","PARTIAL","NO_SIGNAL","CASH_ONLY"}
    for tab,reqs in REQUIREMENTS.items():
        related=[x for x in statuses if tab in (x.get("required_for") or [])]
        core_names=CORE_DATASETS_BY_TAB.get(tab,set())
        core=[x for x in related if x.get("dataset") in core_names]
        core_usable=[x for x in core if x.get("state") in usable]
        optional_missing=[x for x in related if x not in core and x.get("state") in bad]
        if core and not core_usable:
            state="ACTION_REQUIRED" if any(x.get("state")=="ACTION_REQUIRED" for x in core) else "NO_DATA"
        elif core_usable and optional_missing:
            state="PARTIAL"
        elif core_usable:
            state="LIVE"
        elif any(x.get("state") in usable for x in related):
            state="PARTIAL"
        else:
            state="NO_DATA"
        tab_coverage[tab]={"required_datasets":reqs,"core_datasets":sorted(core_names),"provider_statuses":related,
                           "live":sum(1 for x in related if x.get("state")=="LIVE"),
                           "stale":sum(1 for x in related if x.get("state")=="STALE"),
                           "missing":sum(1 for x in related if x.get("state") in bad),
                           "optional_missing":len(optional_missing),"state":state}
    return {"generated":now_iso(),"overall_state":overall,"status_counts":{"live":live,"stale":stale,"error":errors,"total":len(statuses)},
            "watchlist":tickers,"etf_watchlist":etfs,"statuses":statuses,"tab_coverage":tab_coverage,"requirements":REQUIREMENTS,
            "sec_fundamentals":results.get("sec_fundamentals",{}).get("data") or [],
            "intrinio_companies":results.get("intrinio",{}).get("companies") or [],"etf_flows":results.get("intrinio",{}).get("etf_flows") or [],
            "eia":results.get("eia",{}).get("data") or [],"cftc":results.get("cftc",{}).get("data") or {},
            "defillama":results.get("defillama",{}).get("data") or {},"databento":results.get("databento",{}).get("data") or [],
            "idx_live":results.get("idx",{}).get("data") or [],
            "rules":{"no_synthetic":True,"missing_is_not_neutral":True,"reporting_lags_explicit":True,"bridge_failure_isolated":True}}
