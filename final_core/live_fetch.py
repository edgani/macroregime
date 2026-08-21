from __future__ import annotations
import json, os, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data'/'raw'; RAW.mkdir(parents=True,exist_ok=True)
UA=os.getenv('EROS_USER_AGENT','EROS research contact@example.invalid')

def _get(url, headers=None, timeout=30):
    req=urllib.request.Request(url,headers={'User-Agent':UA,**(headers or {})})
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()

def _post_json(url,payload,timeout=30):
    b=json.dumps(payload).encode(); req=urllib.request.Request(url,data=b,headers={'Content-Type':'application/json','User-Agent':UA})
    with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read())

def save_raw(name,content:bytes):
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'); p=RAW/f'{name}_{stamp}'
    p.write_bytes(content); return p

def bls(series_ids,start_year,end_year):
    """Official BLS public API. Registration key optional via BLS_API_KEY."""
    payload={'seriesid':series_ids,'startyear':str(start_year),'endyear':str(end_year)}
    if os.getenv('BLS_API_KEY'): payload['registrationkey']=os.getenv('BLS_API_KEY')
    return _post_json('https://api.bls.gov/publicAPI/v2/timeseries/data/',payload)

def world_bank(country,indicator,per_page=20000):
    q=urllib.parse.urlencode({'format':'json','per_page':per_page})
    return json.loads(_get(f'https://api.worldbank.org/v2/country/{country}/indicator/{indicator}?{q}'))

def sec_companyfacts(cik:int|str):
    c=str(cik).zfill(10)
    return json.loads(_get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{c}.json'))

def sec_ticker_map():
    return json.loads(_get('https://www.sec.gov/files/company_tickers.json'))

def fred(series_id,start=None,end=None):
    key=os.getenv('FRED_API_KEY')
    if not key: raise RuntimeError('FRED_API_KEY missing; optional source, use primary producers when available')
    q={'series_id':series_id,'api_key':key,'file_type':'json'}
    if start:q['observation_start']=start
    if end:q['observation_end']=end
    return json.loads(_get('https://api.stlouisfed.org/fred/series/observations?'+urllib.parse.urlencode(q)))

def treasury_fiscal(endpoint,params=None):
    base='https://api.fiscaldata.treasury.gov/services/api/fiscal_service/'
    u=base+endpoint.lstrip('/')
    if params:u+='?'+urllib.parse.urlencode(params,doseq=True)
    return json.loads(_get(u))

if __name__=='__main__':
    print('EROS official/public adapters loaded. Network fetches are explicit and fail closed.')
