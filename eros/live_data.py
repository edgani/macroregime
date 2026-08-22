from __future__ import annotations
from pathlib import Path
from io import StringIO
from datetime import datetime, timezone
import json, time
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data' / 'cache'
CACHE.mkdir(parents=True, exist_ok=True)
UA = {'User-Agent':'EROS-Warroom/1.0 factual macro research'}

FRED = {
    # growth/labor
    'INDPRO':'Industrial Production','PAYEMS':'Nonfarm Payrolls','UNRATE':'Unemployment Rate','ICSA':'Initial Claims',
    'HOUST':'Housing Starts','PERMIT':'Building Permits','RSAFS':'Retail Sales',
    # inflation
    'CPIAUCSL':'Headline CPI','CPILFESL':'Core CPI','PPIACO':'PPI','PCEPI':'PCE Price Index','PCEPILFE':'Core PCE Price Index',
    # policy/rates
    'FEDFUNDS':'Fed Funds','DGS2':'2Y Treasury','DGS10':'10Y Treasury','DGS30':'30Y Treasury','DFII10':'10Y Real Yield','T10YIE':'10Y Breakeven',
    # credit/liquidity
    'BAMLH0A0HYM2':'HY OAS','M2SL':'M2','WALCL':'Fed Assets','RRPONTSYD':'Reverse Repo','WTREGEN':'TGA',
}

MARKET_TICKERS = {
    'US': ['SPY','QQQ','IWM','TLT','HYG','UUP'],
    'INDONESIA': ['^JKSE','BBCA.JK','BMRI.JK','BBRI.JK','TLKM.JK','ANTM.JK','MDKA.JK','ADRO.JK'],
    'CHINA': ['MCHI','FXI','KWEB'],
    'JAPAN': ['EWJ','^N225'],
    'EUROZONE': ['FEZ','VGK'],
    'CRYPTO': ['BTC-USD','ETH-USD','SOL-USD'],
    'COMMODITIES': ['GC=F','HG=F','CL=F','NG=F','SI=F'],
    'FX': ['EURUSD=X','USDJPY=X','USDIDR=X','DX-Y.NYB'],
}


def _utcnow():
    return datetime.now(timezone.utc).isoformat()


def _cache_path(name): return CACHE / name

def _write_cache(name, obj):
    p=_cache_path(name); p.write_text(json.dumps(obj,default=str),encoding='utf-8')

def _read_cache(name, max_age_hours=24):
    p=_cache_path(name)
    if not p.exists(): return None
    age=(time.time()-p.stat().st_mtime)/3600
    if age>max_age_hours: return None
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return None


def fetch_fred_series(series_id: str, start='2015-01-01') -> tuple[pd.Series|None,str]:
    """Factual-only cascading FRED graph CSV -> DBnomics. Never synthetic."""
    # FRED graph (no key)
    try:
        u=f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}'
        r=requests.get(u,headers=UA,timeout=8)
        if r.ok:
            df=pd.read_csv(StringIO(r.text))
            if len(df.columns)>=2:
                d=pd.to_datetime(df.iloc[:,0],errors='coerce'); v=pd.to_numeric(df.iloc[:,1],errors='coerce')
                s=pd.Series(v.values,index=d,name=series_id).dropna()
                s=s[s.index>=pd.Timestamp(start)]
                if len(s): return s,'FRED graph CSV'
    except Exception: pass
    # DBnomics official mirror
    try:
        u=f'https://api.db.nomics.world/v22/series/FED/{series_id}?observations=1'
        r=requests.get(u,headers=UA,timeout=8)
        if r.ok:
            docs=r.json().get('series',{}).get('docs',[])
            if docs:
                doc=docs[0]; periods=doc.get('period',[]); vals=doc.get('value',[])
                d=pd.to_datetime(periods,errors='coerce'); v=pd.to_numeric(pd.Series(vals),errors='coerce')
                s=pd.Series(v.values,index=d,name=series_id).dropna(); s=s[s.index>=pd.Timestamp(start)]
                if len(s): return s,'DBnomics FED mirror'
    except Exception: pass
    return None,'NO_DATA'


def fetch_macro(force=False):
    cached=None if force else _read_cache('macro_latest.json',12)
    if cached: return cached
    out={'as_of':_utcnow(),'series':{},'source_status':{}}
    for sid,label in FRED.items():
        s,src=fetch_fred_series(sid)
        out['source_status'][sid]=src
        if s is not None and len(s):
            vals=[]
            for idx,val in s.tail(36).items(): vals.append([str(pd.Timestamp(idx).date()),float(val)])
            out['series'][sid]={'label':label,'source':src,'last_date':str(s.index[-1].date()),'last_value':float(s.iloc[-1]),'values':vals}
    _write_cache('macro_latest.json',out)
    return out


def fetch_treasury(force=False):
    cached=None if force else _read_cache('treasury_latest.json',6)
    if cached:return cached
    out={'as_of':_utcnow(),'debt':None,'source':'US Treasury Fiscal Data','status':'NO_DATA'}
    try:
        u='https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny?sort=-record_date&page[size]=5'
        r=requests.get(u,headers=UA,timeout=10); r.raise_for_status(); d=r.json().get('data',[])
        if d:
            out['debt']=d[0]; out['status']='LIVE'
    except Exception as e: out['error']=type(e).__name__
    _write_cache('treasury_latest.json',out); return out


def fetch_prices(force=False):
    cached=None if force else _read_cache('market_latest.json',2)
    if cached:return cached
    out={'as_of':_utcnow(),'markets':{},'source':'yfinance','status':'NO_DATA'}
    try:
        import yfinance as yf
        all_tickers=list(dict.fromkeys(t for xs in MARKET_TICKERS.values() for t in xs))
        raw=yf.download(all_tickers,period='6mo',interval='1d',auto_adjust=True,progress=False,threads=True,group_by='column')
        if raw is not None and len(raw):
            close=raw['Close'] if isinstance(raw.columns,pd.MultiIndex) and 'Close' in raw.columns.get_level_values(0) else raw
            for market,tickers in MARKET_TICKERS.items():
                rows=[]
                for t in tickers:
                    try:
                        s=close[t].dropna() if isinstance(close,pd.DataFrame) and t in close.columns else None
                        if s is None or len(s)<2: continue
                        ret1=float(s.iloc[-1]/s.iloc[-2]-1); ret20=float(s.iloc[-1]/s.iloc[-21]-1) if len(s)>21 else None
                        rows.append({'ticker':t,'last':float(s.iloc[-1]),'as_of':str(pd.Timestamp(s.index[-1]).date()),'ret_1d':ret1,'ret_20d':ret20})
                    except Exception: continue
                out['markets'][market]=rows
            if any(out['markets'].values()):out['status']='LIVE'
    except Exception as e: out['error']=f'{type(e).__name__}: {e}'
    _write_cache('market_latest.json',out); return out


def fetch_world_bank_country(country_code:str, force=False):
    key=f'wb_{country_code}.json'; cached=None if force else _read_cache(key,72)
    if cached:return cached
    indicators={'NY.GDP.MKTP.KD.ZG':'GDP growth','FP.CPI.TOTL.ZG':'Inflation','BN.CAB.XOKA.GD.ZS':'Current account % GDP'}
    out={'as_of':_utcnow(),'country':country_code,'data':{},'source':'World Bank','status':'NO_DATA'}
    for code,label in indicators.items():
        try:
            u=f'https://api.worldbank.org/v2/country/{country_code}/indicator/{code}?format=json&per_page=10'
            r=requests.get(u,headers=UA,timeout=8); j=r.json(); rows=j[1] if isinstance(j,list) and len(j)>1 else []
            row=next((x for x in rows if x.get('value') is not None),None)
            if row: out['data'][label]={'value':row['value'],'year':row['date'],'indicator':code}; out['status']='LIVE'
        except Exception: pass
    _write_cache(key,out); return out


def fetch_news_leads(force=False):
    """GDELT is lead discovery only. Nothing returned here is 'verified' evidence."""
    cached=None if force else _read_cache('news_leads.json',1)
    if cached:return cached
    queries={
      'POLICY_CONFLICT':'Federal Reserve inflation labor housing',
      'AI_CAPITAL':'OpenAI Anthropic IPO AI capital spending data center',
      'AI_CREDIT':'data center securitization AI debt private credit',
      'CHINA_GOLD':'China central bank gold reserves imports',
      'ENERGY_SUPPLY':'OPEC oil supply outage shipping',
      'FISCAL_FUNDING':'Treasury auction dealer funding repo basis',
      'INDONESIA':'Indonesia BI rupiah commodity investment',
      'BROAD_DISCOVERY':'global economy credit funding regulation supply shortage capacity IPO debt inflation central bank commodities crypto geopolitical',
    }
    out={'as_of':_utcnow(),'source':'GDELT 2.0','status':'NO_DATA','leads':[]}
    for theme,q in queries.items():
        try:
            u='https://api.gdeltproject.org/api/v2/doc/doc'
            params={'query':q,'mode':'ArtList','maxrecords':5,'format':'json','sort':'HybridRel'}
            r=requests.get(u,params=params,headers=UA,timeout=10)
            if not r.ok: continue
            for a in r.json().get('articles',[])[:5]:
                out['leads'].append({'theme':theme,'title':a.get('title'),'url':a.get('url'),'domain':a.get('domain'),'seendate':a.get('seendate'),'sourcecountry':a.get('sourcecountry'),'verified':False,'status':'LEAD_REQUIRES_VERIFICATION'})
        except Exception: continue
    if out['leads']:out['status']='LIVE_LEADS_ONLY'
    _write_cache('news_leads.json',out); return out


def fetch_all(force=False):
    return {
      'macro':fetch_macro(force=force),
      'treasury':fetch_treasury(force=force),
      'markets':fetch_prices(force=force),
      'world':{
        'US':fetch_world_bank_country('USA',force=force),
        'INDONESIA':fetch_world_bank_country('IDN',force=force),
        'CHINA':fetch_world_bank_country('CHN',force=force),
        'JAPAN':fetch_world_bank_country('JPN',force=force),
        'EUROZONE':fetch_world_bank_country('EMU',force=force),
      },
      'news_leads':fetch_news_leads(force=force),
    }
