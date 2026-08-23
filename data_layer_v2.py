
from __future__ import annotations
import io, os
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
HEADERS = {"User-Agent":"Mozilla/5.0 MacroDecisionEngine/2.1 research"}

FRED_IDS = [
    "CFNAI","ICSA","UNRATE","CPILFESL","PCEPILFE","T5YIE",
    "DGS2","DGS10","DFII10","T10Y3M","THREEFYTP10",
    "BAMLH0A0HYM2","DRTSCILM","NFCI","VIXCLS",
    "WRESBAL","WALCL","WTREGEN","RRPONTSYD","DTWEXBGS"
]

UNIVERSES = {
    "us": [
        "SPY","IWM","QQQ","TLT","UUP","GLD","USO",
        "PLTR","SNDK","GNRC","MOD","POWL","NVDA","AMD","AVGO","MU",
        "VRT","ETN","GEV","CEG","PWR","ANET","LITE","COHR","CRDO",
        "JPM","XOM","CAT","DE","AMZN","META","MSFT","GOOGL","AAPL"
    ],
    "idx": ["^JKSE","BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","ASII.JK","ANTM.JK","MDKA.JK","ADRO.JK","AMMN.JK"],
    "crypto": ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD"],
    "commodity": ["GC=F","CL=F","BZ=F","HG=F","SI=F","NG=F","GLD","USO"],
    "fx": ["EURUSD=X","JPY=X","GBPUSD=X","AUDUSD=X","IDR=X","DX-Y.NYB","UUP"],
}

def load_universes():
    return {k:list(v) for k,v in UNIVERSES.items()}

def _fred_public(series_id: str) -> pd.Series:
    url=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    r=requests.get(url,headers=HEADERS,timeout=20)
    r.raise_for_status()
    d=pd.read_csv(io.StringIO(r.text))
    if len(d.columns)<2: raise ValueError("empty FRED response")
    d.iloc[:,0]=pd.to_datetime(d.iloc[:,0],errors="coerce")
    d.iloc[:,1]=pd.to_numeric(d.iloc[:,1],errors="coerce")
    s=d.dropna().set_index(d.columns[0])[d.columns[1]].sort_index()
    s.name=series_id
    return s

def _strict_yfinance_prices(tickers: List[str], days: int=5000):
    prices, meta = {}, {}
    if not tickers: return prices,meta
    try:
        import yfinance as yf
    except Exception as e:
        for t in tickers: meta[t]={"ok":False,"reason":f"yfinance unavailable: {e}"}
        return prices,meta
    period="max" if days>=4000 else "5y"
    for t in tickers:
        try:
            d=yf.download(t,period=period,auto_adjust=True,progress=False,threads=False)
            if d is None or d.empty:
                meta[t]={"ok":False,"reason":"empty Yahoo response"}; continue
            c=d["Close"]
            if isinstance(c,pd.DataFrame): c=c.iloc[:,0]
            c=pd.to_numeric(c,errors="coerce").dropna()
            c.index=pd.to_datetime(c.index).tz_localize(None)
            if len(c):
                prices[t]=c.sort_index()
                meta[t]={"ok":True,"rows":len(c),"source":"LIVE_YAHOO"}
            else: meta[t]={"ok":False,"reason":"no close data"}
        except Exception as e:
            meta[t]={"ok":False,"reason":str(e)[:140]}
    return prices,meta

def _treasury_plumbing():
    # Fail-closed. App explicitly shows unavailable rather than inventing values.
    return {
        "tga":{"ok":False,"latest":None,"source":"DATA_GATED"},
        "rrp":{"ok":False,"amount":None,"source":"DATA_GATED"},
        "sofr":{"ok":False,"sofr":None,"source":"DATA_GATED"},
    }

def _research_meta():
    rdir=HERE/"research"
    files=[]
    if rdir.exists():
        for p in rdir.iterdir():
            if p.is_file():
                files.append({"file":p.name,"bytes":p.stat().st_size})
    return {"files":files}

def _load_bundled_fed_research():
    # Optional files can be dropped under research/ later. Missing => fail closed.
    out={}
    specs={
        "ebp":"fed_ebp.csv",
        "fci_g":"fed_fcig.csv",
        "scb":"fed_scb.csv",
        "spf_scenarios":"fed_spf_scenarios.csv",
    }
    for key,fn in specs.items():
        p=HERE/"research"/fn
        if p.exists():
            try:
                out[key]={"source":"BUNDLED_OFFICIAL_SNAPSHOT","data":pd.read_csv(p),"url":None}
            except Exception:
                out[key]={"source":"ERROR","data":pd.DataFrame(),"url":None}
        else:
            out[key]={"source":"DATA_GATED","data":pd.DataFrame(),"url":None}
    return out

def build_data_bundle(markets=None, fetch_live_feeds=False, max_per_market=35):
    markets=markets or ["us","idx","crypto","commodity","fx"]

    fred={}
    fred_err={}
    for sid in FRED_IDS:
        try: fred[sid]=_fred_public(sid)
        except Exception as e: fred_err[sid]=str(e)[:160]

    market_prices={}
    market_sources={}
    for m in markets:
        universe=UNIVERSES.get(m,[])[:int(max_per_market)]
        # Always keep key cross-market proxies if in universe.
        p,meta=_strict_yfinance_prices(universe,days=5000)
        market_prices[m]=p
        market_sources[m]={
            "requested":len(universe),
            "loaded":len(p),
            "source":"LIVE_YAHOO",
            "errors":sum(1 for x in meta.values() if not x.get("ok"))
        }

    # Ensure cross-market proxies are present independently of selected cap/market.
    proxies=["SPY","IWM","^JKSE","BTC-USD","GLD","USO","UUP","TLT"]
    pp,_=_strict_yfinance_prices(proxies,days=5000)
    market_prices["_proxies"]=pp

    # Discovery priors are nominations only; zero score contribution.
    priors={
        "tickers":["SNDK","PLTR","GNRC","MOD","POWL","VRT","ETN","GEV","ANET","MU"],
        "policy":"DISCOVERY_PRIOR_ONLY_NO_SCORE"
    }

    # Specialized feeds are deliberately fail-closed in this clean deploy.
    feeds={"_status":{
        "cot":"DATA_GATED",
        "onchain":"DATA_GATED",
        "gex":"DATA_GATED",
        "finra":"DATA_GATED"
    }}

    try:
        from data.eia_physical import load_eia_if_configured
        eia=load_eia_if_configured()
    except Exception as e:
        eia={"status":"DATA_GATED","reason":str(e)[:160],"series":{}}

    return {
        "fred":{"series":fred,"meta":{"requested":len(FRED_IDS),"loaded":len(fred),"errors":fred_err}},
        "fed_research":_load_bundled_fed_research(),
        "market":{"prices":market_prices,"sources":market_sources},
        "treasury_plumbing":_treasury_plumbing(),
        "feeds":feeds,
        "research_meta":_research_meta(),
        "eia_physical":eia,
        "discovery_priors":priors,
    }
