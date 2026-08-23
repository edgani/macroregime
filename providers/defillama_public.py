
from __future__ import annotations
import requests
from datetime import datetime, timezone
HEAD={'User-Agent':'MacroDecisionOS/4.0 research','Accept':'application/json'}
def _f(x):
    try:return float(x)
    except:return 0.0
def _peg(x):
    if not isinstance(x,dict):return 0.0
    if 'peggedUSD' in x:return _f(x.get('peggedUSD'))
    c=x.get('current'); return _f(c.get('peggedUSD')) if isinstance(c,dict) else 0.0

def fetch(timeout=20):
    out={'retrieved_at':datetime.now(timezone.utc).isoformat(),'source':'DeFiLlama','status':'DATA_GATED'}
    try:
        chains=requests.get('https://api.llama.fi/chains',headers=HEAD,timeout=timeout);chains.raise_for_status(); ch=chains.json()
        if isinstance(ch,list):
            vals=[_f(x.get('tvl')) for x in ch if isinstance(x,dict)]
            top=sorted([{'name':x.get('name'),'tvl':_f(x.get('tvl'))} for x in ch if isinstance(x,dict)],key=lambda z:z['tvl'],reverse=True)[:10]
            out['chains']={'ok':True,'total_tvl':sum(vals),'count':len(ch),'top':top}
    except Exception as e:out['chains']={'ok':False,'reason':str(e)[:160]}
    try:
        r=requests.get('https://stablecoins.llama.fi/stablecoins',headers=HEAD,timeout=timeout);r.raise_for_status(); d=r.json(); assets=d.get('peggedAssets',[]) if isinstance(d,dict) else []
        now=sum(_peg(x.get('circulating')) for x in assets if isinstance(x,dict)); d1=sum(_peg(x.get('circulatingPrevDay')) for x in assets if isinstance(x,dict)); d7=sum(_peg(x.get('circulatingPrevWeek')) for x in assets if isinstance(x,dict)); d30=sum(_peg(x.get('circulatingPrevMonth')) for x in assets if isinstance(x,dict))
        out['stablecoins']={'ok':bool(assets),'total_mcap':now,'change_1d':now/d1-1 if d1 else None,'change_7d':now/d7-1 if d7 else None,'change_30d':now/d30-1 if d30 else None,'count':len(assets)}
    except Exception as e:out['stablecoins']={'ok':False,'reason':str(e)[:160]}
    try:
        r=requests.get('https://api.llama.fi/overview/dexs',headers=HEAD,timeout=timeout);r.raise_for_status(); d=r.json()
        out['dex']={'ok':True,'total24h':_f(d.get('total24h')),'change_1d':d.get('change_1d'),'change_7d':d.get('change_7d'),'change_1m':d.get('change_1m')}
    except Exception as e:out['dex']={'ok':False,'reason':str(e)[:160]}
    out['status']='LIVE' if any(out.get(k,{}).get('ok') for k in ['chains','stablecoins','dex']) else 'DATA_GATED'
    return out
