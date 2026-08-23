
from __future__ import annotations
import io, os
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import requests
HERE=Path(__file__).resolve().parent
HEADERS={"User-Agent":os.getenv("SEC_USER_AGENT","MacroDecisionOS/3.0 research-contact@example.com")}

FRED={
"CFNAI":("Growth","monthly","LATEST_REVISED"),"ICSA":("Labor","weekly","REVISED"),"UNRATE":("Labor","monthly","REVISED"),
"CPILFESL":("Inflation","monthly","REVISED"),"PCEPILFE":("Inflation","monthly","REVISED"),"T5YIE":("Inflation expectations","daily","MARKET_OBSERVED"),
"DGS2":("Rates","daily","MARKET_OBSERVED"),"DGS10":("Rates","daily","MARKET_OBSERVED"),"DFII10":("Real yield","daily","MARKET_OBSERVED"),
"T10Y3M":("Curve","daily","DERIVED_LATEST"),"THREEFYTP10":("Term premium","daily","MODEL_ESTIMATE_REVISED"),"BAMLH0A0HYM2":("Credit","daily","MARKET_OBSERVED"),
"DRTSCILM":("Lending standards","quarterly","REVISED_SURVEY"),"NFCI":("Financial conditions","weekly","REVISED_INDEX"),"VIXCLS":("Volatility","daily","MARKET_OBSERVED"),
"WRESBAL":("Reserves","weekly","BALANCE_SHEET"),"WALCL":("Fed assets","weekly","BALANCE_SHEET"),"WTREGEN":("TGA","weekly","BALANCE_SHEET"),"RRPONTSYD":("RRP","daily","OBSERVED"),
"DTWEXBGS":("USD","daily","MARKET_OBSERVED"),
}
UNIVERSES={
"us":["SPY","IWM","QQQ","TLT","UUP","GLD","USO","PLTR","SNDK","GNRC","MOD","POWL","VRT","ETN","GEV","CEG","PWR","ANET","MU","NVDA","AMD","AVGO","JPM","XOM"],
"idx":["^JKSE","BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","ASII.JK","ANTM.JK","MDKA.JK","ADRO.JK","AMMN.JK"],
"crypto":["BTC-USD","ETH-USD","SOL-USD","BNB-USD"],"commodity":["GC=F","CL=F","BZ=F","HG=F","NG=F"],
"fx":["EURUSD=X","JPY=X","GBPUSD=X","AUDUSD=X","IDR=X","DX-Y.NYB"]}

def load_universes(): return {k:list(v) for k,v in UNIVERSES.items()}

def _fred(sid):
    u=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    r=requests.get(u,headers=HEADERS,timeout=20); r.raise_for_status()
    d=pd.read_csv(io.StringIO(r.text)); d.iloc[:,0]=pd.to_datetime(d.iloc[:,0],errors='coerce'); d.iloc[:,1]=pd.to_numeric(d.iloc[:,1],errors='coerce')
    s=d.dropna().set_index(d.columns[0])[d.columns[1]].sort_index(); s.name=sid
    return s,u

def strict_prices(tickers,period='max'):
    out={}; meta={}
    try: import yfinance as yf
    except Exception as e:
        return {},{t:{'ok':False,'reason':f'yfinance missing: {e}'} for t in tickers}
    for t in tickers:
        try:
            d=yf.download(t,period=period,auto_adjust=True,progress=False,threads=False)
            if d is None or d.empty: raise ValueError('empty response')
            c=d['Close']; c=c.iloc[:,0] if isinstance(c,pd.DataFrame) else c
            c=pd.to_numeric(c,errors='coerce').dropna(); c.index=pd.to_datetime(c.index).tz_localize(None)
            out[t]=c.sort_index(); meta[t]={'ok':True,'rows':len(c),'source':'YAHOO_LIVE','retrieved_at':datetime.now(timezone.utc).isoformat(),'revision_status':'MARKET_PRICE_ADJUSTED'}
        except Exception as e: meta[t]={'ok':False,'reason':str(e)[:160]}
    return out,meta

def _lineage_row(name,source,url,series,freq,revision,transform='RAW'):
    last=None
    try: last=pd.Series(series).dropna().index[-1].isoformat()
    except Exception: pass
    return {'dataset':name,'source':source,'url':url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'latest_observation':last,
            'release_vintage':'NOT_PRESERVED' if 'REVISED' in revision else 'N/A_MARKET_OR_OBSERVED','revision_status':revision,'update_frequency':freq,
            'staleness_threshold':'SOURCE_FREQUENCY_DEPENDENT','transformation_lineage':transform}

def build_data_bundle(markets=None,max_per_market=30):
    markets=markets or list(UNIVERSES)
    fred={}; ferr={}; lineage=[]
    for sid,(role,freq,rev) in FRED.items():
        try:
            s,u=_fred(sid); fred[sid]=s; lineage.append(_lineage_row(sid,'FRED',u,s,freq,rev))
        except Exception as e: ferr[sid]=str(e)[:160]
    prices={}; pmeta={}
    for m in markets:
        p,meta=strict_prices(UNIVERSES.get(m,[])[:max_per_market]); prices[m]=p; pmeta[m]=meta
        for tk,s in p.items(): lineage.append(_lineage_row(tk,'Yahoo Finance',None,s,'daily','MARKET_PRICE_ADJUSTED','AUTO_ADJUSTED_CLOSE'))
    proxies=['SPY','IWM','^JKSE','BTC-USD','GLD','USO','UUP','TLT']
    p,meta=strict_prices(proxies); prices['_proxies']=p; pmeta['_proxies']=meta
    return {'fred':fred,'fred_errors':ferr,'prices':prices,'price_meta':pmeta,'lineage':pd.DataFrame(lineage),
            'data_gaps':[
            'PIT/vintage macro history (ALFRED or equivalent)','Pre-release macro consensus history','PIT analyst estimates/revisions','Historical constituents + delisted securities',
            'Historical option surfaces / dealer inventory','Cross-currency basis history','Broad commodity physical histories','Historical company backlog/RPO/order datasets',
            'Crypto unlock/emission/exchange-balance history','Calibrated market-implied distribution history']}
