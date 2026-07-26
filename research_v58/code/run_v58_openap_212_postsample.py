from __future__ import annotations
import json, hashlib, math
from pathlib import Path
from datetime import datetime, timezone
import numpy as np, pandas as pd
from scipy.stats import norm
import statsmodels.api as sm
ROOT=Path('/mnt/data/v58_work/research_v58'); PROTO=ROOT/'protocols/V58_OPENAP_212_POSTSAMPLE_PROTOCOL_FROZEN.json'
def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def nw_se(x,lags=6):
 x=np.asarray(x,float);x=x[np.isfinite(x)]
 if len(x)<4:return np.nan
 r=sm.OLS(x,np.ones((len(x),1))).fit(cov_type='HAC',cov_kwds={'maxlags':min(lags,len(x)-1),'use_correction':True})
 return float(r.bse[0])
def mdd(x):
 w=np.cumprod(1+np.asarray(x,float));p=np.maximum.accumulate(w);return float(np.min(w/p-1)) if len(w) else np.nan
def pyf(s):
 a=s.groupby(s.index.year).apply(lambda z:float(np.prod(1+z)-1));return float((a>0).mean()) if len(a) else np.nan
def loo(s):
 ys=sorted(set(s.index.year));v=[float(s[s.index.year!=y].mean()) for y in ys if len(s[s.index.year!=y])];return min(v) if v else np.nan
def met(s,c,z):
 s=s.dropna().astype(float)-c;n=len(s)
 if not n:return {'n':0}
 mu=float(s.mean());sd=float(s.std(ddof=1));se=nw_se(s)
 return {'n':n,'start':str(s.index.min().date()),'end':str(s.index.max().date()),'mean_monthly':mu,'annualized_mean':12*mu,
  'annualized_sharpe':mu/sd*np.sqrt(12) if sd>0 else None,'hac_se':se,'hac_t':mu/se if se>0 else None,
  'bonferroni_lower_bound':mu-z*se if np.isfinite(se) else None,'max_drawdown':mdd(s),'positive_year_fraction':pyf(s),'leave_one_year_out_min_mean':loo(s)}
def clean(x):
 if isinstance(x,float) and (np.isnan(x) or np.isinf(x)):return None
 if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
 if isinstance(x,list):return [clean(v) for v in x]
 return x
p=json.load(open(PROTO))
for v in p['source'].values():
 if sha(Path(v['path']))!=v['sha256']:raise SystemExit('hash mismatch '+v['path'])
ret=pd.read_csv(p['source']['predictor_returns']['path']);ret['date']=pd.to_datetime(ret['date']);ret=ret.set_index('date').sort_index()
# Values are percentage points in the public file.
ret=ret.apply(pd.to_numeric,errors='coerce')/100.0
m=p['claim_count'];z=float(norm.ppf(1-0.05/m));rows=[]
for c in p['claims']:
 s=ret[c['series']].dropna();s=s[s.index>=pd.Timestamp(f"{c['post_start_year']}-01-01")]
 val=s.iloc[:60]; lock=s.iloc[61:] if len(s)>61 else s.iloc[0:0]
 rec={'claim':c,'post_sample_available_n':len(s),'zcrit':z,'splits':{}}
 for lab,ss in [('validation',val),('lockbox',lock)]:
  rec['splits'][lab]={str(cost):met(ss,cost,z) for cost in p['cost_sensitivity_monthly']}
 def g(sp,cost,k):return rec['splits'][sp][str(cost)].get(k)
 enough=g('validation',0.0,'n')>=60 and g('lockbox',0.0,'n')>=60
 points=enough and g('validation',0.0,'mean_monthly')>0 and g('lockbox',0.0,'mean_monthly')>0
 gross=points and g('validation',0.0,'bonferroni_lower_bound')>0 and g('lockbox',0.0,'bonferroni_lower_bound')>0 and g('validation',0.0,'leave_one_year_out_min_mean')>0 and g('lockbox',0.0,'leave_one_year_out_min_mean')>0
 cost25=gross and g('validation',0.0025,'bonferroni_lower_bound')>0 and g('lockbox',0.0025,'bonferroni_lower_bound')>0
 tier='ROBUST_25BPS_POSTSAMPLE' if cost25 else 'ROBUST_GROSS_POSTSAMPLE' if gross else 'DIRECTIONALLY_PERSISTENT_ONLY' if points else 'FAILED_OR_UNIDENTIFIABLE'
 rec.update(tier=tier,historical_support=tier.startswith('ROBUST'),live_decision_weight=0.0,capital_permission='BLOCKED');rows.append(rec)
counts={}
for r in rows:counts[r['tier']]=counts.get(r['tier'],0)+1
out={'schema':'warroom.v58.openap_212_postsample_results.v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(PROTO),
 'registered_claims':m,'bonferroni_one_sided_z':z,'tier_counts':counts,'claims':rows,'predictive_components_promoted_to_live':0,
 'research_live_decision_weight':0.0,'capital_permission':'BLOCKED','data_caveat':'Maintained reconstructed portfolio series from a public mirror; not point-in-time vintage stock-level data.'}
out=clean(out);path=ROOT/'results/V58_OPENAP_212_POSTSAMPLE_RESULTS.json';path.write_text(json.dumps(out,indent=2,sort_keys=True))
flat=[]
for r in rows:
 d={'claim_id':r['claim']['claim_id'],'series':r['claim']['series'],'name':r['claim']['name'],'data_category':r['claim']['data_category'],'economic_category':r['claim']['economic_category'],'post_start_year':r['claim']['post_start_year'],'post_sample_available_n':r['post_sample_available_n'],'tier':r['tier']}
 for sp in ['validation','lockbox']:
  for k in ['n','start','end','mean_monthly','annualized_sharpe','hac_t','bonferroni_lower_bound','leave_one_year_out_min_mean','max_drawdown']:
   d[f'{sp}_{k}']=r['splits'][sp]['0.0'].get(k)
  d[f'{sp}_lb_after_25bps']=r['splits'][sp]['0.0025'].get('bonferroni_lower_bound')
 flat.append(d)
f=pd.DataFrame(flat).sort_values(['tier','lockbox_mean_monthly'],ascending=[True,False]);f.to_csv(ROOT/'results/V58_OPENAP_212_POSTSAMPLE_SUMMARY.csv',index=False)
print(json.dumps({'counts':counts,'zcrit':z,'result_sha256':sha(path)},indent=2))
print('\nTOP BY LOCKBOX MEAN AMONG IDENTIFIABLE\n',f[f.lockbox_n>=60].sort_values('lockbox_mean_monthly',ascending=False).head(30).to_string(index=False))
print('\nROBUST\n',f[f.tier.str.startswith('ROBUST')].to_string(index=False))
