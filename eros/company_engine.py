from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, math, time
from .models import TickerCandidate

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'data'/'cache'; CACHE.mkdir(parents=True,exist_ok=True)

# Scenario -> candidates. This is candidate generation, NOT a buy list.
# Exposure still needs company fundamentals/filings and priced-in validation before qualification.
THEME_UNIVERSE={
 'SCN_POLICY_CONFLICT': [('JPM','US','Banks'),('BAC','US','Banks'),('GS','US','Capital Markets'),('TLT','US','Long Duration'),('HYG','US','Credit')],
 'SCN_FISCAL_ABSORPTION': [('JPM','US','Banks'),('GS','US','Dealers/Capital Markets'),('TLT','US','Treasury Duration'),('HYG','US','Credit')],
 'SCN_LIQUIDITY_CREDIT': [('JPM','US','Banks'),('GS','US','Capital Markets'),('HYG','US','Credit'),('BTC-USD','CRYPTO','Crypto liquidity')],
 'RADAR_AI_CAPITAL': [('NVDA','US','AI compute'),('AVGO','US','AI networking/custom silicon'),('VRT','US','Data-center power/cooling'),('ETN','US','Electrical infrastructure'),('CEG','US','Power'),('VST','US','Power'),('DELL','US','Servers'),('SMCI','US','Servers')],
 'RADAR_AI_CREDIT': [('VRT','US','Data-center infrastructure'),('ETN','US','Electrical infrastructure'),('CEG','US','Power'),('VST','US','Power'),('DELL','US','Servers'),('DLR','US','Data centers'),('EQIX','US','Data centers')],
 'RADAR_CHINA_GOLD': [('NEM','US','Gold miner'),('AEM','US','Gold miner'),('GOLD','US','Gold miner'),('GC=F','COMMODITY','Gold future')],
 'RADAR_ENERGY_SUPPLY': [('XOM','US','Integrated oil'),('CVX','US','Integrated oil'),('COP','US','E&P'),('SLB','US','Oil services'),('CL=F','COMMODITY','WTI future')],
 'RADAR_INDONESIA': [('BBCA.JK','IDX','Bank'),('BMRI.JK','IDX','Bank'),('BBRI.JK','IDX','Bank'),('ANTM.JK','IDX','Metals'),('MDKA.JK','IDX','Metals'),('ADRO.JK','IDX','Energy'),('TLKM.JK','IDX','Telecom')],
 'SCN_GRAPH_CHINA_INDUSTRIAL_METALS': [('FCX','US','Copper producer'),('SCCO','US','Copper producer'),('ANTM.JK','IDX','Metals'),('MDKA.JK','IDX','Metals'),('HG=F','COMMODITY','Copper future')],
 'SCN_GRAPH_LIQUIDITY_CRYPTO': [('BTC-USD','CRYPTO','Bitcoin'),('ETH-USD','CRYPTO','Ethereum'),('COIN','US','Crypto platform')],
}


def _cache_read(name,max_age_h=6):
    p=CACHE/name
    if not p.exists() or (time.time()-p.stat().st_mtime)/3600>max_age_h:return None
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return None

def _cache_write(name,obj): (CACHE/name).write_text(json.dumps(obj,indent=2,default=str),encoding='utf-8')

def _safe_num(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except Exception:return None


def fetch_fundamentals(tickers, force=False):
    cached=None if force else _cache_read('company_fundamentals.json',6)
    cached_map={x['ticker']:x for x in (cached or {}).get('rows',[])}
    need=[t for t in tickers if t not in cached_map or cached_map[t].get('status') not in ('CURRENT_FUNDAMENTALS','MARKET_INSTRUMENT_NO_COMPANY_FUNDAMENTALS')]
    rows=list(cached_map.values())
    try:
        import yfinance as yf
        for t in need:
            if t.endswith('=F') or t.endswith('-USD') or t in ('TLT','HYG'):
                rows.append({'ticker':t,'status':'MARKET_INSTRUMENT_NO_COMPANY_FUNDAMENTALS','as_of':datetime.now(timezone.utc).isoformat()}); continue
            try:
                info=yf.Ticker(t).info or {}
                rows.append({
                  'ticker':t,'status':'CURRENT_FUNDAMENTALS','as_of':datetime.now(timezone.utc).isoformat(),
                  'shortName':info.get('shortName'),'sector':info.get('sector'),'industry':info.get('industry'),
                  'marketCap':_safe_num(info.get('marketCap')),'enterpriseValue':_safe_num(info.get('enterpriseValue')),
                  'revenueGrowth':_safe_num(info.get('revenueGrowth')),'earningsGrowth':_safe_num(info.get('earningsGrowth')),
                  'grossMargins':_safe_num(info.get('grossMargins')),'operatingMargins':_safe_num(info.get('operatingMargins')),
                  'freeCashflow':_safe_num(info.get('freeCashflow')),'operatingCashflow':_safe_num(info.get('operatingCashflow')),
                  'totalDebt':_safe_num(info.get('totalDebt')),'totalCash':_safe_num(info.get('totalCash')),
                  'forwardPE':_safe_num(info.get('forwardPE')),'trailingPE':_safe_num(info.get('trailingPE')),
                  'priceToBook':_safe_num(info.get('priceToBook')),'enterpriseToEbitda':_safe_num(info.get('enterpriseToEbitda')),
                  'businessSummary':(info.get('longBusinessSummary') or '')[:2500],
                })
            except Exception as e:
                rows.append({'ticker':t,'status':'NO_DATA','error':type(e).__name__,'as_of':datetime.now(timezone.utc).isoformat()})
    except Exception:
        for t in need: rows.append({'ticker':t,'status':'NO_DATA','as_of':datetime.now(timezone.utc).isoformat()})
    out={'as_of':datetime.now(timezone.utc).isoformat(),'rows':rows}; _cache_write('company_fundamentals.json',out); return out


def _balance_status(r):
    if r.get('status')!='CURRENT_FUNDAMENTALS':return 'NO_DATA'
    cash=r.get('totalCash'); debt=r.get('totalDebt'); fcf=r.get('freeCashflow')
    if cash is None or debt is None:return 'PARTIAL'
    if debt<=cash:return 'NET_CASH/LOW_NET_DEBT'
    if fcf is not None and fcf>0:return 'LEVERAGED_BUT_FCF_POSITIVE'
    return 'LEVERAGE_REQUIRES_REVIEW'

def _fund_status(r):
    if r.get('status')!='CURRENT_FUNDAMENTALS':return r.get('status','NO_DATA')
    fields=['revenueGrowth','operatingMargins','freeCashflow']; n=sum(r.get(k) is not None for k in fields)
    return 'GOOD_CURRENT_COVERAGE' if n==3 else 'PARTIAL_CURRENT_COVERAGE' if n else 'NO_DATA'

def _valuation(r, peer_pes):
    pe=r.get('forwardPE')
    if pe is None:return 'NO_DATA'
    vals=sorted(x for x in peer_pes if x is not None and x>0)
    if len(vals)<3:return f'FORWARD_PE_{pe:.1f}_NO_PEER_BASE'
    med=vals[len(vals)//2]
    return 'RICH_VS_CANDIDATE_PEERS' if pe>med*1.25 else 'CHEAP_VS_CANDIDATE_PEERS' if pe<med*.8 else 'MID_VS_CANDIDATE_PEERS'


def generate_candidates(verified_scenarios, radar_scenarios, force=False):
    ids=[]
    for s in verified_scenarios: ids.append((s.scenario_id,s.title,'VERIFIED_MACRO_SCENARIO'))
    for s in radar_scenarios: ids.append((s.get('scenario_id'),s.get('title'),'UNVERIFIED_NEWS_RADAR'))
    pairs=[]
    for sid,title,level in ids:
        for t,market,theme in THEME_UNIVERSE.get(sid,[]): pairs.append((sid,title,level,t,market,theme))
    # generic graph fallback by keywords
    for sid,title,level in ids:
        if sid.startswith('SCN_GRAPH_CHINA_'):
            for t,market,theme in THEME_UNIVERSE['SCN_GRAPH_CHINA_INDUSTRIAL_METALS']: pairs.append((sid,title,level,t,market,theme))
        if sid.startswith('SCN_GRAPH_LIQUIDITY_CRYPTO'):
            for t,market,theme in THEME_UNIVERSE['SCN_GRAPH_LIQUIDITY_CRYPTO']: pairs.append((sid,title,level,t,market,theme))
    # dedup scenario/ticker
    uniq=[]; seen=set()
    for p in pairs:
        k=(p[0],p[3])
        if k not in seen:seen.add(k);uniq.append(p)
    f=fetch_fundamentals(sorted(set(p[3] for p in uniq)),force=force); fmap={x['ticker']:x for x in f['rows']}
    peer_pes=[x.get('forwardPE') for x in f['rows'] if x.get('status')=='CURRENT_FUNDAMENTALS']
    out=[]
    for sid,title,level,t,market,theme in uniq:
        r=fmap.get(t,{'ticker':t,'status':'NO_DATA'})
        fund=_fund_status(r); bal=_balance_status(r); val=_valuation(r,peer_pes)
        if market in ('COMMODITY','CRYPTO') or t in ('TLT','HYG'):
            exposure='INSTRUMENT_EXPOSURE_DEFINED'; mechanism=f'{theme} is a direct market expression candidate for {title}'
        else:
            exposure='CANDIDATE_EXPOSURE_REQUIRES_FILINGS_CONFIRMATION'; mechanism=f'{theme} candidate; verify revenue/unit-economics exposure before production qualification'
        # Never fabricate priced-in probability or EV.
        action='VERIFY' if level=='UNVERIFIED_NEWS_RADAR' else 'WATCH/RESEARCH'
        if fund=='NO_DATA': action='NO_RANK'
        out.append(TickerCandidate(t,market,sid,theme,mechanism,exposure,fund,bal,val,'NOT_CALIBRATED','Scenario confirmation + company-specific catalyst','CURRENT_CONTEXT_NOT_PIT_VALIDATED',action,None,details=r))
    return out
