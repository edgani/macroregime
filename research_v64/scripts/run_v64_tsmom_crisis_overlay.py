from __future__ import annotations
import json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import norm
import statsmodels.api as sm

ROOT=Path(__file__).resolve().parents[2]
PROTO=ROOT/'research_v64/protocols/V64_TSMOM_CRISIS_OVERLAY_PROTOCOL_FROZEN.json'
OUT=ROOT/'research_v64/results/V64_TSMOM_CRISIS_OVERLAY_RESULTS.json'

def sha(p:Path)->str:
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def read_tsmom():
    p=ROOT/'research_v58/data/Time-Series-Momentum-Factors-Monthly.xlsx'
    raw=pd.read_excel(p,sheet_name='TSMOM Factors',header=None)
    # data header is first row whose second cell is TSMOM
    hdr=None
    for i in range(len(raw)):
        if raw.shape[1]>1 and str(raw.iloc[i,1]).strip()=='TSMOM':
            hdr=i; break
    if hdr is None: raise RuntimeError('TSMOM header not found')
    cols=['date']+[str(x).strip() for x in raw.iloc[hdr,1:].tolist()]
    df=raw.iloc[hdr+1:,:len(cols)].copy(); df.columns=cols
    df['date']=pd.to_datetime(df['date'],errors='coerce')
    df['TSMOM']=pd.to_numeric(df['TSMOM'],errors='coerce')
    return df[['date','TSMOM']].dropna().sort_values('date')

def read_state():
    p=ROOT/'research/shiller.csv'
    df=pd.read_csv(p,usecols=['Date','SP500'])
    df['date']=pd.to_datetime(df['Date'],errors='coerce')
    df['SP500']=pd.to_numeric(df['SP500'],errors='coerce')
    df=df.dropna().sort_values('date').set_index('date')
    # Use month-end labels. Shiller dates are month-start observations; map to month-end.
    df.index=df.index.to_period('M').to_timestamp('M')
    px=df['SP500']
    ret3=px.pct_change(3)
    ret12=px.pct_change(12)
    dd12=px/px.rolling(12,min_periods=12).max()-1
    # state available for outcome month t uses previous month's computed state
    st=pd.DataFrame({'RET3':ret3,'RET12':ret12,'DD12':dd12}).shift(1)
    return st

def hac_stats(x:pd.Series,zcrit:float):
    x=x.dropna().astype(float)
    n=len(x)
    if n<2: return {'n':n,'mean_monthly':None,'hac_se':None,'hac_t':None,'simultaneous_lower_bound':None}
    X=np.ones((n,1))
    fit=sm.OLS(x.values,X).fit(cov_type='HAC',cov_kwds={'maxlags':min(6,max(1,n//4))},use_t=False)
    mean=float(fit.params[0]); se=float(fit.bse[0]); t=mean/se if se>0 else None
    return {'n':n,'mean_monthly':mean,'annualized_mean':mean*12,'hac_se':se,'hac_t':t,
            'simultaneous_lower_bound':mean-zcrit*se}

def positive_year_fraction(sub:pd.DataFrame):
    if sub.empty: return None
    y=sub.groupby(sub['date'].dt.year)['TSMOM'].agg(['count','sum'])
    y=y[y['count']>=2]
    if y.empty: return None
    return float((y['sum']>0).mean())

def main():
    proto=json.loads(PROTO.read_text())
    zcrit=float(norm.ppf(1-0.05/8))
    t=read_tsmom(); s=read_state()
    df=t.set_index('date').join(s,how='inner').reset_index()
    states={
      'DD12_LE_M10':df['DD12']<=-0.10,
      'DD12_LE_M15':df['DD12']<=-0.15,
      'RET12_LT_0':df['RET12']<0,
      'RET3_LE_M10':df['RET3']<=-0.10,
    }
    splits={'validation':('2010-01-01','2017-12-31'),'lockbox':('2018-01-01','2099-12-31')}
    results=[]
    for sid,mask in states.items():
      row={'state_id':sid,'splits':{}}
      all_pass=True
      for split,(a,b) in splits.items():
        base=df[(df['date']>=a)&(df['date']<=b)&mask]
        stats_by_cost={}
        for cost in [0.0,0.001,0.0025]:
          st=hac_stats(base['TSMOM']-cost,zcrit)
          st['positive_year_fraction']=positive_year_fraction(base.assign(TSMOM=base['TSMOM']-cost))
          stats_by_cost[str(cost)]=st
        primary=stats_by_cost['0.0']
        split_pass=(primary['n']>=6 and primary['mean_monthly'] is not None and primary['mean_monthly']>0 and
                    primary['simultaneous_lower_bound'] is not None and primary['simultaneous_lower_bound']>0 and
                    (primary['positive_year_fraction'] is None or primary['positive_year_fraction']>=0.5))
        row['splits'][split]={'pass_primary':bool(split_pass),'cost_stresses':stats_by_cost,
                              'event_months':[d.strftime('%Y-%m-%d') for d in base['date']]}
        all_pass=all_pass and split_pass
      row['market_claim_proven']=bool(all_pass)
      results.append(row)
    proven=[r['state_id'] for r in results if r['market_claim_proven']]
    out={
      'schema':'warroom.v64.tsmom_crisis_overlay.results.v1',
      'protocol_sha256':sha(PROTO),
      'input_sha256':{
        'tsmom':sha(ROOT/'research_v58/data/Time-Series-Momentum-Factors-Monthly.xlsx'),
        'shiller':sha(ROOT/'research/shiller.csv')},
      'zcrit_one_sided_bonferroni_8':zcrit,
      'common_start':df['date'].min().strftime('%Y-%m-%d'),
      'common_end':df['date'].max().strftime('%Y-%m-%d'),
      'states':results,
      'proven_states':proven,
      'market_claim_status':'PROVEN_NARROW_CRISIS_DEFENSE' if proven else 'NOT_PROVEN',
      'operational_ready':False,
      'capital_permission':'BLOCKED',
      'claim_limit':proto['claim_limit']
    }
    OUT.write_text(json.dumps(out,indent=2))
    print(json.dumps({'status':out['market_claim_status'],'proven_states':proven,'end':out['common_end']},indent=2))
    for r in results:
      print('\n',r['state_id'],r['market_claim_proven'])
      for sp,v in r['splits'].items():
        q=v['cost_stresses']['0.0']; print(sp,q['n'],q['mean_monthly'],q['simultaneous_lower_bound'],q['positive_year_fraction'])
if __name__=='__main__': main()
