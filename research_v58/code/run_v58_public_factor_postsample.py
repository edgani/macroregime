from __future__ import annotations
import json, hashlib, math
from pathlib import Path
from datetime import datetime, timezone
import numpy as np, pandas as pd
from scipy.stats import norm
import statsmodels.api as sm

ROOT=Path('/mnt/data/v58_work/research_v58')
PROTO=ROOT/'protocols/V58_PUBLIC_FACTOR_POSTSAMPLE_PROTOCOL_FROZEN.json'

def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def read_data(name,path):
 if name=='TSMOM':
  df=pd.read_excel(path,sheet_name='TSMOM Factors',header=17)
  df=df.rename(columns={df.columns[0]:'DATE'})
 elif name=='VME': df=pd.read_excel(path,sheet_name='VME Factors',header=21)
 elif name=='BAB': df=pd.read_excel(path,sheet_name='BAB Factors',header=18)
 elif name=='QMJ': df=pd.read_excel(path,sheet_name='QMJ Factors',header=18)
 else: raise ValueError(name)
 df['DATE']=pd.to_datetime(df['DATE'],errors='coerce')
 df=df.dropna(subset=['DATE']).set_index('DATE').sort_index()
 for c in df.columns: df[c]=pd.to_numeric(df[c],errors='coerce')
 return df

def nw_se(x,lags=6):
 x=np.asarray(x,float); x=x[np.isfinite(x)]
 if len(x)<4:return float('nan')
 X=np.ones((len(x),1))
 res=sm.OLS(x,X).fit(cov_type='HAC',cov_kwds={'maxlags':min(lags,len(x)-1),'use_correction':True})
 return float(res.bse[0])

def max_drawdown(x):
 x=np.asarray(x,float); x=x[np.isfinite(x)]
 if not len(x): return float('nan')
 wealth=np.cumprod(1+x); peak=np.maximum.accumulate(wealth)
 return float(np.min(wealth/peak-1))

def positive_year_fraction(s):
 annual=s.groupby(s.index.year).apply(lambda z: float(np.prod(1+z)-1))
 return float((annual>0).mean()) if len(annual) else float('nan')

def loo_min_mean(s):
 years=sorted(set(s.index.year))
 vals=[]
 for y in years:
  z=s[s.index.year!=y]
  if len(z): vals.append(float(z.mean()))
 return min(vals) if vals else float('nan')

def metrics(s,cost,zcrit):
 s=s.dropna().astype(float)-cost; n=len(s)
 if n<1:return {'n':n}
 mu=float(s.mean()); sd=float(s.std(ddof=1)) if n>1 else float('nan'); se=nw_se(s.values)
 return {'n':n,'mean_monthly':mu,'annualized_mean':mu*12,'annualized_sharpe':(mu/sd*math.sqrt(12)) if sd and np.isfinite(sd) and sd>0 else float('nan'),
  'hac_se':se,'hac_t':mu/se if se and np.isfinite(se) and se>0 else float('nan'),'bonferroni_lower_bound':mu-zcrit*se if np.isfinite(se) else float('nan'),
  'max_drawdown':max_drawdown(s.values),'positive_year_fraction':positive_year_fraction(s),'leave_one_year_out_min_mean':loo_min_mean(s)}

def clean(v):
 if isinstance(v,float) and (math.isnan(v) or math.isinf(v)): return None
 if isinstance(v,dict): return {k:clean(x) for k,x in v.items()}
 if isinstance(v,list): return [clean(x) for x in v]
 return v

p=json.load(open(PROTO));
for k,v in p['data_files'].items():
 if sha(Path(v['path']))!=v['sha256']: raise SystemExit(f'hash mismatch {k}')
data={k:read_data(k,Path(v['path'])) for k,v in p['data_files'].items()}
m=len(p['claims']); zcrit=float(norm.ppf(1-0.05/m))
rows=[]
for c in p['claims']:
 df=data[c['dataset']]
 if c['series'] not in df: s=pd.Series(dtype=float)
 else:s=df[c['series']].dropna()
 val=s.loc[pd.Timestamp(c['validation_start']):pd.Timestamp(c['validation_end'])]
 lock=s.loc[pd.Timestamp(c['lockbox_start']):]
 rec={'claim':c,'available_start':str(s.index.min().date()) if len(s) else None,'available_end':str(s.index.max().date()) if len(s) else None,'zcrit':zcrit,'splits':{}}
 for label,ss in [('validation',val),('lockbox',lock)]:
  rec['splits'][label]={str(cost):metrics(ss,cost,zcrit) for cost in p['cost_sensitivity_monthly']}
 def mm(split,cost,key): return rec['splits'][split][str(cost)].get(key)
 minobs=p['minimum_observations_per_split']
 enough=mm('validation',0.0,'n')>=minobs and mm('lockbox',0.0,'n')>=minobs
 points=enough and mm('validation',0.0,'mean_monthly')>0 and mm('lockbox',0.0,'mean_monthly')>0
 gross=points and mm('validation',0.0,'bonferroni_lower_bound')>0 and mm('lockbox',0.0,'bonferroni_lower_bound')>0 and mm('validation',0.0,'leave_one_year_out_min_mean')>0 and mm('lockbox',0.0,'leave_one_year_out_min_mean')>0
 cost25=gross and mm('validation',0.0025,'bonferroni_lower_bound')>0 and mm('lockbox',0.0025,'bonferroni_lower_bound')>0
 if cost25: tier='ROBUST_25BPS_POSTSAMPLE'
 elif gross: tier='ROBUST_GROSS_POSTSAMPLE'
 elif points: tier='DIRECTIONALLY_PERSISTENT_ONLY'
 else:tier='FAILED_OR_UNIDENTIFIABLE'
 rec['tier']=tier; rec['historical_support']=tier.startswith('ROBUST'); rec['live_decision_weight']=0.0; rec['capital_permission']='BLOCKED'
 rows.append(rec)

counts={}
for r in rows: counts[r['tier']]=counts.get(r['tier'],0)+1
out={
 'schema':'warroom.v58.public_factor_postsample_results.v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
 'protocol_path':str(PROTO),'protocol_sha256':sha(PROTO),'registered_claims':m,'bonferroni_one_sided_z':zcrit,
 'tier_counts':counts,'claims':rows,'interpretation':{
   'ROBUST_25BPS_POSTSAMPLE':'Strong historical persistence in maintained factor series under strict simultaneous gate and coarse cost sensitivity; still not an executable War Room edge.',
   'ROBUST_GROSS_POSTSAMPLE':'Strong gross historical persistence but not robust to 25 bps/month sensitivity.',
   'DIRECTIONALLY_PERSISTENT_ONLY':'Positive point means in both periods without simultaneous proof.',
   'FAILED_OR_UNIDENTIFIABLE':'Did not maintain positive point means or lacked enough observations.'},
 'predictive_components_promoted_to_live':0,'research_live_decision_weight':0.0,'capital_permission':'BLOCKED'}
out=clean(out)
path=ROOT/'results/V58_PUBLIC_FACTOR_POSTSAMPLE_RESULTS.json'; path.write_text(json.dumps(out,indent=2,sort_keys=True))
# CSV summary
flat=[]
for r in rows:
 d={'claim_id':r['claim']['claim_id'],'family':r['claim']['family'],'tier':r['tier'],'available_start':r['available_start'],'available_end':r['available_end']}
 for split in ['validation','lockbox']:
  for k in ['n','mean_monthly','annualized_sharpe','hac_t','bonferroni_lower_bound','leave_one_year_out_min_mean','max_drawdown']:
   d[f'{split}_{k}']=r['splits'][split]['0.0'].get(k)
  d[f'{split}_lb_after_25bps']=r['splits'][split]['0.0025'].get('bonferroni_lower_bound')
 flat.append(d)
pd.DataFrame(flat).to_csv(ROOT/'results/V58_PUBLIC_FACTOR_POSTSAMPLE_SUMMARY.csv',index=False)
print(json.dumps({'tier_counts':counts,'zcrit':zcrit,'result_sha256':sha(path)},indent=2))
print(pd.DataFrame(flat).sort_values(['tier','lockbox_mean_monthly'],ascending=[True,False]).to_string(index=False,max_rows=100))
