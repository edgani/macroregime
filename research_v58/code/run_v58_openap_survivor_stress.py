from __future__ import annotations
import pandas as pd, numpy as np, json, hashlib, math
from pathlib import Path
from datetime import datetime, timezone
import statsmodels.api as sm
ROOT=Path('/mnt/data/v58_work/research_v58')
RES=json.load(open(ROOT/'results/V58_OPENAP_212_POSTSAMPLE_RESULTS.json'))
surv=[r for r in RES['claims'] if r['tier'].startswith('ROBUST')]
series=[r['claim']['series'] for r in surv]
ret=pd.read_csv('/mnt/data/PredictorLSretWide.csv');ret['date']=pd.to_datetime(ret['date']);ret=ret.set_index('date')[series].apply(pd.to_numeric,errors='coerce')/100

def nw(x,l=6):
 x=pd.Series(x).dropna();r=sm.OLS(x.values,np.ones((len(x),1))).fit(cov_type='HAC',cov_kwds={'maxlags':min(l,len(x)-1),'use_correction':True});return float(x.mean()),float(r.bse[0]),float(r.tvalues[0])
def mdd(x):
 w=(1+pd.Series(x).dropna()).cumprod();return float((w/w.cummax()-1).min())
def stats(x):
 x=pd.Series(x).dropna();mu,se,t=nw(x);return {'n':len(x),'mean_monthly':mu,'annualized_sharpe':float(mu/x.std()*np.sqrt(12)) if x.std()>0 else None,'hac_t':t,'max_drawdown':mdd(x),'worst_month':float(x.min()),'best_month':float(x.max())}
out={'schema':'warroom.v58.openap_survivor_stress.v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'selected_from_registered_claims':212,'survivors':{},'correlation_full':ret.corr().to_dict(),'claim_limit':'Post-selection diagnostics on the same maintained data; no new proof or untouched holdout.'}
for s in series:
 x=ret[s].dropna();claim=next(r['claim'] for r in surv if r['claim']['series']==s);post=x[x.index>=pd.Timestamp(f"{claim['post_start_year']}-01-01")]
 years=pd.DataFrame({'r':post,'year':post.index.year});annual=years.groupby('year').r.apply(lambda z:float((1+z).prod()-1))
 rec={'primary_tier':next(r['tier'] for r in surv if r['claim']['series']==s),'post_sample':stats(post),'recent_2020_2024':stats(post.loc['2020':'2024']),
      'annual_returns':{str(k):float(v) for k,v in annual.items()},'positive_year_fraction':float((annual>0).mean()),
      'exclude_best_calendar_year':stats(post[post.index.year!=annual.idxmax()]),'exclude_worst_calendar_year':stats(post[post.index.year!=annual.idxmin()]),
      'cost_stress':{str(c):stats(post-c) for c in [0.0025,0.005,0.01]},
      'source_dependency':{'AnnouncementReturn':'IBES announcement dates + CRSP','ShortInterest':'short interest + shares + availability lag','DivYieldST':'CRSP distributions + prices','AnalystRevision':'IBES estimates'}[s],
      'capacity_and_turnover_status':'NOT_AVAILABLE_IN_WIDE_FACTOR_FILE','live_decision_weight':0.0,'capital_permission':'BLOCKED'}
 out['survivors'][s]=rec
# Equal weight ensemble when all available.
e=ret.dropna().mean(axis=1);out['equal_weight_four_factor']={'full_overlap':stats(e),'recent_2020_2024':stats(e.loc['2020':'2024']),'cost_stress':{str(c):stats(e-c) for c in [0.0025,0.005,0.01]},'not_proof_reason':'constructed after survivor selection on same data'}
p=ROOT/'results/V58_OPENAP_SURVIVOR_STRESS.json';p.write_text(json.dumps(out,indent=2,sort_keys=True))
print('survivors',series);print(json.dumps({s:{'recent':out['survivors'][s]['recent_2020_2024'],'cost50':out['survivors'][s]['cost_stress']['0.005']} for s in series},indent=2));print('ensemble',json.dumps(out['equal_weight_four_factor'],indent=2))
