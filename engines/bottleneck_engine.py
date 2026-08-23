
from __future__ import annotations
import os,re,requests,numpy as np,pandas as pd
HEAD={'User-Agent':os.getenv('SEC_USER_AGENT','MacroDecisionOS/4.0 research-contact@example.com')}
TERMS={'constraint':['capacity constraint','supply constraint','shortage','lead time','capacity expansion','constrained','allocation'],'demand':['backlog','remaining performance obligations','rpo','bookings','orders','hyperscaler','data center','demand','qualification'],'monetization':['gross margin','operating margin','free cash flow','pricing','price increase','revenue growth'],'resolution':['new capacity','capacity online','inventory increase','lead times declined','supply normalization']}

def _cik(t):
    try:
        r=requests.get('https://www.sec.gov/files/company_tickers.json',headers=HEAD,timeout=20);r.raise_for_status();j=r.json()
        for x in j.values():
            if str(x.get('ticker','')).upper()==t.upper():return str(x['cik_str']).zfill(10)
    except Exception:pass

def _filing(t):
    cik=_cik(t)
    if not cik:return {'ok':False,'reason':'CIK unavailable'}
    try:
        r=requests.get(f'https://data.sec.gov/submissions/CIK{cik}.json',headers=HEAD,timeout=20);r.raise_for_status();j=r.json();rec=j['filings']['recent']
        for i,f in enumerate(rec['form']):
            if f in ('10-Q','10-K'):
                acc=rec['accessionNumber'][i].replace('-','');doc=rec['primaryDocument'][i];url=f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}';tx=requests.get(url,headers=HEAD,timeout=20);tx.raise_for_status();text=re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',tx.text)).lower();hits={g:[] for g in TERMS};sn=[]
                for g,terms in TERMS.items():
                    for term in terms:
                        for m in list(re.finditer(re.escape(term),text))[:2]:
                            hits[g].append(term);sn.append({'group':g,'term':term,'snippet':text[max(0,m.start()-180):m.start()+330][:510]})
                return {'ok':True,'form':f,'filed':rec['filingDate'][i],'url':url,'hits':hits,'snippets':sn[:16]}
        return {'ok':False,'reason':'No recent 10-Q/10-K'}
    except Exception as e:return {'ok':False,'reason':str(e)[:180]}

def _quarter_facts(t):
    cik=_cik(t)
    if not cik:return {'ok':False,'reason':'CIK unavailable'}
    try:
        r=requests.get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json',headers=HEAD,timeout=25);r.raise_for_status();us=r.json().get('facts',{}).get('us-gaap',{})
        def qrows(tags):
            rows=[]
            for tag in tags:
                for unit,vals in (us.get(tag,{}).get('units',{}) or {}).items():
                    if unit!='USD':continue
                    for x in vals:
                        if x.get('form') not in ('10-Q','10-K') or not x.get('filed') or not x.get('end') or not x.get('start'):continue
                        try:dur=(pd.Timestamp(x['end'])-pd.Timestamp(x['start'])).days
                        except:continue
                        frame=str(x.get('frame',''));quarter_like=(70<=dur<=110) or ('Q' in frame and 'YTD' not in frame)
                        if quarter_like:rows.append({'tag':tag,'end':pd.Timestamp(x['end']),'filed':pd.Timestamp(x['filed']),'val':float(x['val']),'frame':frame,'dur':dur})
            if not rows:return pd.DataFrame()
            d=pd.DataFrame(rows).sort_values(['end','filed']).drop_duplicates('end',keep='last');return d
        def yoy(tags):
            d=qrows(tags)
            if len(d)<5:return (np.nan,None,len(d))
            z=d.iloc[-1];prior=d.iloc[:-1].copy();target=z['end']-pd.DateOffset(years=1);prior['gap']=(prior['end']-target).abs();p=prior.sort_values('gap').iloc[0]
            return ((z['val']/p['val']-1) if p['val'] else np.nan,z['filed'].date().isoformat(),len(d))
        rev,fd,n=yoy(['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet']);gp,_,_=yoy(['GrossProfit']);op,_,_=yoy(['OperatingIncomeLoss']);ni,_,_=yoy(['NetIncomeLoss'])
        return {'ok':n>=4,'latest_filed':fd,'revenue_yoy':rev,'gross_profit_yoy':gp,'operating_income_yoy':op,'net_income_yoy':ni,'quarter_points':n,'lineage':'SEC Company Facts; filed-date and quarter-duration filtered'}
    except Exception as e:return {'ok':False,'reason':str(e)[:180]}

def _current(t):
    try:
        import yfinance as yf
        q=yf.Ticker(t);info=q.info or {};h=q.history(period='5y',auto_adjust=True);c=pd.to_numeric(h['Close'],errors='coerce').dropna()
        return {'ok':len(c)>0,'price':float(c.iloc[-1]) if len(c) else np.nan,'drawdown_5y_peak':float(c.iloc[-1]/c.max()-1) if len(c) else np.nan,'revenue_growth':info.get('revenueGrowth'),'earnings_growth':info.get('earningsGrowth'),'gross_margin':info.get('grossMargins'),'operating_margin':info.get('operatingMargins'),'fcf':info.get('freeCashflow')}
    except Exception as e:return {'ok':False,'reason':str(e)[:160]}

def investigate(tickers):
    rows=[];details={}
    for t in tickers:
        filing=_filing(t);facts=_quarter_facts(t);cur=_current(t);h=filing.get('hits',{})
        chain={'constraint_evidence':bool(h.get('constraint')),'demand_capture_evidence':bool(h.get('demand')),'monetization_language':bool(h.get('monetization')),'resolution_language':bool(h.get('resolution')),'sec_revenue_capture':bool(facts.get('ok') and np.isfinite(facts.get('revenue_yoy',np.nan)) and facts['revenue_yoy']>0),'sec_operating_capture':bool(facts.get('ok') and np.isfinite(facts.get('operating_income_yoy',np.nan)) and facts['operating_income_yoy']>0)}
        mech=filing.get('ok') and chain['demand_capture_evidence'] and (chain['constraint_evidence'] or chain['monetization_language']);mon=chain['sec_revenue_capture'] and (chain['sec_operating_capture'] or chain['monetization_language'])
        status='MONETIZATION_CONFIRMED' if mech and mon else ('MECHANISM_EVIDENCE_FOUND' if mech else 'WATCH / INSUFFICIENT EVIDENCE')
        reason='SEC filing supports constraint→capture and SEC filed-date facts confirm revenue/operating monetization.' if status=='MONETIZATION_CONFIRMED' else ('Constraint/capture language found, but filed-date monetization is not fully confirmed.' if mech else 'No complete constraint→capture chain found in the latest filing.')
        action='NO TRADE';action_reason='P(NotFullyPriced), PIT estimate revisions, catalyst probability and calibrated runway are not available.'
        rows.append({'ticker':t,'evidence_status':status,'action':action,'price':cur.get('price'),'drawdown_5y_peak':cur.get('drawdown_5y_peak'),'SEC_revenue_yoy':facts.get('revenue_yoy'),'SEC_operating_income_yoy':facts.get('operating_income_yoy'),'filing_date':filing.get('filed')})
        details[t]={'filing':filing,'sec_facts':facts,'current':cur,'chain':chain,'reason':reason,'competing_thesis':'The constraint may resolve, demand may be cyclical, capacity may catch up, or valuation may already discount the rents.','action':action,'action_reason':action_reason,'kill_switches':['Demand-capture evidence reverses','Revenue/operating/FCF capture deteriorates','Capacity/inventory evidence shows the bottleneck resolving','Credit/funding stress breaks the transmission','Pricing consumes the remaining payoff before catalyst realization']}
    return pd.DataFrame(rows),details
