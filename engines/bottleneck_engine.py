
from __future__ import annotations
import re,os,requests,numpy as np,pandas as pd
HEAD={'User-Agent':os.getenv('SEC_USER_AGENT','MacroDecisionOS/3.0 research-contact@example.com')}
TERMS={'constraint':['capacity constraint','supply constraint','shortage','lead time','capacity expansion','constrained'],
'demand':['backlog','remaining performance obligations','rpo','bookings','orders','hyperscaler','data center','demand'],
'monetization':['gross margin','operating margin','free cash flow','pricing','revenue growth']}

def _cik(t):
    try:
        j=requests.get('https://www.sec.gov/files/company_tickers.json',headers=HEAD,timeout=20).json()
        for r in j.values():
            if str(r.get('ticker','')).upper()==t.upper():return str(r['cik_str']).zfill(10)
    except Exception:pass

def _filing(t):
    cik=_cik(t)
    if not cik:return {'ok':False,'reason':'CIK unavailable'}
    try:
        j=requests.get(f'https://data.sec.gov/submissions/CIK{cik}.json',headers=HEAD,timeout=20).json(); rec=j['filings']['recent']
        for i,f in enumerate(rec['form']):
            if f in ('10-Q','10-K'):
                acc=rec['accessionNumber'][i].replace('-','');doc=rec['primaryDocument'][i];url=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}';
                tx=requests.get(url,headers=HEAD,timeout=20);tx.raise_for_status(); text=re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',tx.text)).lower();hits={k:[] for k in TERMS};sn=[]
                for g,terms in TERMS.items():
                    for term in terms:
                        pos=text.find(term)
                        if pos>=0:hits[g].append(term);sn.append({'group':g,'term':term,'snippet':text[max(0,pos-160):pos+300][:460]})
                return {'ok':True,'form':f,'filed':rec['filingDate'][i],'url':url,'hits':hits,'snippets':sn[:10]}
        return {'ok':False,'reason':'No 10-Q/10-K'}
    except Exception as e:return {'ok':False,'reason':str(e)[:180]}

def _current(t):
    try:
        import yfinance as yf
        q=yf.Ticker(t);info=q.info or {};h=q.history(period='5y',auto_adjust=True)
        c=pd.to_numeric(h['Close'],errors='coerce').dropna();
        return {'ok':len(c)>0,'price':float(c.iloc[-1]) if len(c) else np.nan,'drawdown_5y_peak':float(c.iloc[-1]/c.max()-1) if len(c) else np.nan,
                'revenue_growth':info.get('revenueGrowth'),'earnings_growth':info.get('earningsGrowth'),'gross_margin':info.get('grossMargins'),'operating_margin':info.get('operatingMargins'),'fcf':info.get('freeCashflow')}
    except Exception as e:return {'ok':False,'reason':str(e)[:160]}

def investigate(tickers):
    rows=[];details={}
    for t in tickers:
        f=_filing(t);q=_current(t); h=f.get('hits',{})
        chain={'constraint_evidence':bool(h.get('constraint')),'demand_capture_evidence':bool(h.get('demand')),'monetization_language':bool(h.get('monetization')),
               'current_revenue_growth_positive':bool(q.get('revenue_growth') is not None and np.isfinite(q.get('revenue_growth')) and q.get('revenue_growth')>0),
               'current_earnings_growth_positive':bool(q.get('earnings_growth') is not None and np.isfinite(q.get('earnings_growth')) and q.get('earnings_growth')>0)}
        evidence_ok=f.get('ok') and chain['demand_capture_evidence'] and (chain['constraint_evidence'] or chain['monetization_language'])
        status='EVIDENCE_CHAIN_FOUND' if evidence_ok else 'WATCH / INSUFFICIENT EVIDENCE'
        action='NO TRADE'
        action_reason='Pricing/not-fully-priced probability, PIT revisions and calibrated runway are unavailable.'
        rows.append({'ticker':t,'evidence_status':status,'action':action,'current_price':q.get('price'),'drawdown_5y_peak':q.get('drawdown_5y_peak'),
                     'revenue_growth':q.get('revenue_growth'),'earnings_growth':q.get('earnings_growth'),'filing_date':f.get('filed')})
        details[t]={'filing':f,'current':q,'chain':chain,'action':action,'action_reason':action_reason,
                    'competing_thesis':'Constraint may resolve, demand may be cyclical, or backlog may reflect inability to deliver.',
                    'kill_switches':['Demand-capture evidence reverses','Revenue/margin/FCF fail to monetize the constraint','Capacity grows faster than demand','Pricing hurdle becomes too demanding','Credit/funding shock breaks transmission']}
    return pd.DataFrame(rows),details
