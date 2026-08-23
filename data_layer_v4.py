
from __future__ import annotations
import io, os
from datetime import datetime, timezone
from pathlib import Path
import numpy as np,pandas as pd,requests
from providers.treasury_public import fetch as fetch_treasury
from providers.defillama_public import fetch as fetch_defillama
HERE=Path(__file__).resolve().parent
HEAD={'User-Agent':os.getenv('SEC_USER_AGENT','MacroDecisionOS/4.0 research-contact@example.com')}
FRED={
'CFNAI':('Growth','monthly','LATEST_REVISED'),'ICSA':('Labor','weekly','REVISED'),'UNRATE':('Labor','monthly','REVISED'),'TOTLL':('Bank credit','weekly','REVISED'),'BUSLOANS':('C&I loans','weekly','REVISED'),
'CPILFESL':('Inflation','monthly','REVISED'),'PCEPILFE':('Inflation','monthly','REVISED'),'T5YIE':('Inflation expectations','daily','MARKET_OBSERVED'),
'DGS2':('Rates','daily','MARKET_OBSERVED'),'DGS5':('Rates','daily','MARKET_OBSERVED'),'DGS10':('Rates','daily','MARKET_OBSERVED'),'DGS30':('Rates','daily','MARKET_OBSERVED'),'DFII10':('Real yield','daily','MARKET_OBSERVED'),
'T10Y3M':('Curve','daily','DERIVED_LATEST'),'THREEFYTP10':('Term premium','daily','MODEL_ESTIMATE_REVISED'),
'BAMLH0A0HYM2':('HY credit','daily','MARKET_OBSERVED'),'BAMLC0A0CM':('IG credit','daily','MARKET_OBSERVED'),'BAMLH0A3HYC':('CCC credit','daily','MARKET_OBSERVED'),
'DRTSCILM':('Lending standards','quarterly','REVISED_SURVEY'),'NFCI':('Financial conditions','weekly','REVISED_INDEX'),'ANFCI':('Adjusted financial conditions','weekly','REVISED_INDEX'),
'VIXCLS':('Volatility','daily','MARKET_OBSERVED'),'SOFR':('Funding','daily','MARKET_OBSERVED'),'IORB':('Funding','daily','OBSERVED'),'EFFR':('Funding','daily','OBSERVED'),
'WRESBAL':('Reserves','weekly','BALANCE_SHEET'),'WALCL':('Fed assets','weekly','BALANCE_SHEET'),'WTREGEN':('TGA','weekly','BALANCE_SHEET'),'RRPONTSYD':('RRP','daily','OBSERVED'),
'DTWEXBGS':('USD','daily','MARKET_OBSERVED')}
UNIVERSES={
'us':['SPY','IWM','QQQ','TLT','UUP','GLD','USO','PLTR','SNDK','GNRC','MOD','POWL','VRT','ETN','GEV','CEG','PWR','ANET','MU','NVDA','AMD','AVGO','JPM','XOM'],
'idx':['^JKSE','BBCA.JK','BBRI.JK','BMRI.JK','TLKM.JK','ASII.JK','ANTM.JK','MDKA.JK','ADRO.JK','AMMN.JK'],
'crypto':['BTC-USD','ETH-USD','SOL-USD','BNB-USD'],'commodity':['GC=F','CL=F','BZ=F','HG=F','NG=F'],'fx':['EURUSD=X','JPY=X','GBPUSD=X','AUDUSD=X','IDR=X','DX-Y.NYB']}
SYSTEM_TICKERS=['^VIX9D','^VIX3M','^VVIX','^MOVE']

def load_universes():return {k:list(v) for k,v in UNIVERSES.items()}

def _fred(sid):
    u=f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}';r=requests.get(u,headers=HEAD,timeout=20);r.raise_for_status();d=pd.read_csv(io.StringIO(r.text));d.iloc[:,0]=pd.to_datetime(d.iloc[:,0],errors='coerce');d.iloc[:,1]=pd.to_numeric(d.iloc[:,1],errors='coerce');s=d.dropna().set_index(d.columns[0])[d.columns[1]].sort_index();s.name=sid;return s,u

def strict_prices(tickers,period='max'):
    out={};meta={}
    try:import yfinance as yf
    except Exception as e:return {},{t:{'ok':False,'reason':f'yfinance missing: {e}'} for t in tickers}
    for t in tickers:
        try:
            d=yf.download(t,period=period,auto_adjust=True,progress=False,threads=False)
            if d is None or d.empty:raise ValueError('empty response')
            c=d['Close'];c=c.iloc[:,0] if isinstance(c,pd.DataFrame) else c;c=pd.to_numeric(c,errors='coerce').dropna();c.index=pd.to_datetime(c.index).tz_localize(None);out[t]=c.sort_index();meta[t]={'ok':True,'rows':len(c),'source':'YAHOO_LIVE','retrieved_at':datetime.now(timezone.utc).isoformat(),'revision_status':'MARKET_PRICE_ADJUSTED'}
        except Exception as e:meta[t]={'ok':False,'reason':str(e)[:160]}
    return out,meta

def _staleness(freq,last):
    if last is None:return ('UNKNOWN',None)
    try:
        age=(pd.Timestamp.utcnow().tz_localize(None).normalize()-pd.Timestamp(last).normalize()).days
    except:return ('UNKNOWN',None)
    limits={'daily':7,'weekly':16,'monthly':50,'quarterly':130}
    lim=limits.get(freq,60);return ('OK' if age<=lim else 'STALE',age)

def _lineage(name,source,url,series,freq,revision,transform='RAW'):
    last=None
    try:last=pd.Series(series).dropna().index[-1]
    except:pass
    stale,age=_staleness(freq,last)
    return {'dataset':name,'source':source,'url':url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'latest_observation':last.isoformat() if last is not None else None,'age_days':age,'staleness':stale,'release_vintage':'NOT_PRESERVED' if any(k in revision for k in ['REVISED','MODEL_ESTIMATE']) else 'N/A_MARKET_OR_OBSERVED','revision_status':revision,'update_frequency':freq,'transformation_lineage':transform}

def build_data_bundle(markets=None,max_per_market=30,fetch_specialized=True):
    markets=markets or list(UNIVERSES);fred={};ferr={};line=[]
    for sid,(role,freq,rev) in FRED.items():
        try:s,u=_fred(sid);fred[sid]=s;line.append(_lineage(sid,'FRED',u,s,freq,rev))
        except Exception as e:ferr[sid]=str(e)[:160]
    prices={};pmeta={}
    for m in markets:
        p,meta=strict_prices(UNIVERSES.get(m,[])[:max_per_market]);prices[m]=p;pmeta[m]=meta
        for tk,s in p.items():line.append(_lineage(tk,'Yahoo Finance',None,s,'daily','MARKET_PRICE_ADJUSTED','AUTO_ADJUSTED_CLOSE'))
    proxies=['SPY','IWM','^JKSE','BTC-USD','GLD','USO','UUP','TLT']+SYSTEM_TICKERS
    p,meta=strict_prices(proxies);prices['_proxies']=p;pmeta['_proxies']=meta
    for tk,s in p.items():line.append(_lineage(tk,'Yahoo Finance',None,s,'daily','MARKET_PRICE_ADJUSTED','SYSTEM/OUTCOME_CONTEXT'))
    treasury=fetch_treasury() if fetch_specialized else {'status':'DISABLED'}
    crypto_native=fetch_defillama() if fetch_specialized and 'crypto' in markets else {'status':'DISABLED'}
    return {'fred':fred,'fred_errors':ferr,'prices':prices,'price_meta':pmeta,'treasury':treasury,'crypto_native':crypto_native,'lineage':pd.DataFrame(line),'data_gaps':[
    'PIT/vintage macro history (ALFRED or equivalent)','Pre-release macro consensus history','PIT analyst estimates/revisions','Historical constituents + delisted securities','Historical option surfaces / dealer inventory','Cross-currency basis history','Broad commodity physical histories','Historical company backlog/RPO/order datasets','Crypto unlock/emission/exchange-balance history','Calibrated market-implied distribution history','IDX Type-F historical foreign-flow database']}
