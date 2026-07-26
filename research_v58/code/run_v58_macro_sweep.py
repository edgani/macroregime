from __future__ import annotations
import json,hashlib,re,math,sys
from pathlib import Path
from datetime import datetime,timezone
import numpy as np,pandas as pd,statsmodels.api as sm
from scipy.stats import norm
ROOT=Path('/mnt/data/v58_work/research_v58');PROTO=ROOT/'protocols/V58_MACRO_SWEEP_PROTOCOL_FROZEN.json'
sys.path.insert(0,'/mnt/data/v58_work/research_v55');from flat_parquet_snappy import read_flat_parquet

def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def reg(x,y,sign,z,lags=12):
 q=pd.concat([x.rename('x'),y.rename('y')],axis=1).replace([np.inf,-np.inf],np.nan).dropna()
 if len(q)<24:return {'n':len(q),'beta':None,'hac_se':None,'hac_t':None,'bonferroni_lb':None,'spearman':None}
 xr=q.x.rank(pct=True);yr=q.y.rank(pct=True);xr=(xr-xr.mean())/xr.std();yr=(yr-yr.mean())/yr.std();xr=xr*sign
 r=sm.OLS(yr.values,sm.add_constant(xr.values)).fit(cov_type='HAC',cov_kwds={'maxlags':min(lags,len(q)-1),'use_correction':True})
 b=float(r.params[1]);se=float(r.bse[1]);return {'n':len(q),'beta':b,'hac_se':se,'hac_t':b/se if se>0 else None,'bonferroni_lb':b-z*se,'spearman':float(xr.corr(yr))}
def clean(x):
 if isinstance(x,float) and not np.isfinite(x):return None
 if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
 if isinstance(x,list):return [clean(v) for v in x]
 return x
p=json.load(open(PROTO));z=float(norm.ppf(1-0.05/p['registered_claims']))
df=read_flat_parquet('/mnt/data/v58_work/research/macro_panel.parquet').copy();df.index=pd.to_datetime(df.index);df=df.sort_index()
spxret=df.spx.pct_change();rets={a:df[a].pct_change() for a in ['gold','oil','gas','dxy']}
cache={}
def zroll(s,h):return (s-s.rolling(h,min_periods=max(12,h//2)).mean())/s.rolling(h,min_periods=max(12,h//2)).std()
def feat(n):
 m=re.match(r'spx_mom_(\d+)',n)
 if m:return df.spx.pct_change(int(m.group(1)))
 m=re.match(r'spx_vol_(\d+)',n)
 if m:return spxret.rolling(int(m.group(1)),min_periods=max(3,int(m.group(1))//2)).std()
 m=re.match(r'spx_drawdown_(\d+)',n)
 if m:
  h=int(m.group(1));return df.spx/df.spx.rolling(h,min_periods=max(12,h//2)).max()-1
 m=re.match(r'cape_z_(\d+)',n)
 if m:return zroll(df.cape,int(m.group(1)))
 if n=='cape_level':return df.cape
 if n=='cape_change_12':return df.cape.diff(12)
 m=re.match(r'(cpi_yoy|rate10)_level',n)
 if m:return df[m.group(1)]
 m=re.match(r'(cpi_yoy|rate10)_change_(\d+)',n)
 if m:return df[m.group(1)].diff(int(m.group(2)))
 if n=='real_rate':return df.rate10-df.cpi_yoy
 if n=='real_rate_change_12':return (df.rate10-df.cpi_yoy).diff(12)
 m=re.match(r'(gold|oil|gas|dxy)_mom_(\d+)',n)
 if m:return df[m.group(1)].pct_change(int(m.group(2)))
 m=re.match(r'(gold|oil|gas|dxy)_vol_(\d+)',n)
 if m:return rets[m.group(1)].rolling(int(m.group(2)),min_periods=max(3,int(m.group(2))//2)).std()
 if n=='oil_gold_ratio_mom12':return (df.oil/df.gold).pct_change(12)
 if n=='gas_oil_ratio_mom12':return (df.gas/df.oil).pct_change(12)
 if n=='commodity_dxy_divergence':return pd.concat([df.gold.pct_change(12),df.oil.pct_change(12),df.gas.pct_change(12)],axis=1).mean(axis=1)-df.dxy.pct_change(12)
 if n=='inflation_oil_gap':return df.cpi_yoy-df.oil.pct_change(12)*100
 if n=='rate_inflation_gap':return df.rate10-df.cpi_yoy
 if n=='valuation_rate_interaction':return zroll(df.cape,120)*df.rate10
 if n=='valuation_momentum_interaction':return -zroll(df.cape,120)+df.spx.pct_change(12)
 if n=='inflation_momentum_interaction':return -df.cpi_yoy/10+df.spx.pct_change(12)
 if n=='cross_asset_stress':return df.dxy.pct_change(6)-pd.concat([df.gold.pct_change(6),df.oil.pct_change(6),df.gas.pct_change(6)],axis=1).mean(axis=1)
 if n=='commodity_dispersion':return pd.concat([df.gold.pct_change(12),df.oil.pct_change(12),df.gas.pct_change(12)],axis=1).std(axis=1)
 if n=='calendar_month_placebo':return pd.Series(df.index.month,index=df.index,dtype=float)
 if n=='linear_time_placebo':return pd.Series(np.arange(len(df)),index=df.index,dtype=float)
 if n=='fourier_7y_placebo':return pd.Series(np.sin(np.arange(len(df))*2*np.pi/84),index=df.index)
 if n=='fourier_10y_placebo':return pd.Series(np.sin(np.arange(len(df))*2*np.pi/120),index=df.index)
 if n=='deterministic_noise_placebo':
  a=np.sin(np.arange(len(df))*12.9898)*43758.5453;return pd.Series(a-np.floor(a),index=df.index)
 raise KeyError(n)
# Targets, fully defined before split evaluation.
targets={
 'future_6m_return':df.spx.shift(-6)/df.spx-1,
 'future_12m_return':df.spx.shift(-12)/df.spx-1,
 'future_6m_drawdown_loss':pd.Series(index=df.index,dtype=float),
 'future_6m_realized_vol':spxret.shift(-1).rolling(6).std().shift(-5)*np.sqrt(12)}
# Exact forward minimum drawdown from current level over next 6 observations.
vals=df.spx.values;loss=np.full(len(df),np.nan)
for i in range(len(df)-6):loss[i]=max(0.0,1-np.nanmin(vals[i+1:i+7])/vals[i])
targets['future_6m_drawdown_loss']=pd.Series(loss,index=df.index)
splits={'discovery':('1973-01-01','1994-12-31'),'validation':('1995-01-01','2007-12-31'),'diagnostic_holdout':('2008-01-01','2023-09-30')}
rows=[]
for fd in p['features']:
 x=feat(fd['feature'])
 for td in p['targets']:
  y=targets[td['name']]
  a,b=splits['discovery'];disc0=reg(x.loc[a:b],y.loc[a:b],1,z);orient=1 if disc0['beta'] is None or disc0['beta']>=0 else -1
  rec={'claim_id':f"{fd['feature']}:{td['name']}",'feature':fd['feature'],'family':fd['family'],'target':td['name'],'orientation':orient,'splits':{}}
  for sp,(a,b) in splits.items():rec['splits'][sp]=reg(x.loc[a:b],y.loc[a:b],orient,z)
  v=rec['splits']['validation'];h=rec['splits']['diagnostic_holdout'];rec['diagnostic_survivor']=bool(v['beta'] is not None and h['beta'] is not None and v['beta']>0 and h['beta']>0 and v['bonferroni_lb']>0 and h['bonferroni_lb']>0)
  rec['live_decision_weight']=0.0;rec['capital_permission']='BLOCKED';rows.append(rec)
counts={'registered':len(rows),'diagnostic_survivors':sum(r['diagnostic_survivor'] for r in rows),'placebo_claims':sum('placebo' in r['family'] for r in rows),'placebo_survivors':sum(r['diagnostic_survivor'] and 'placebo' in r['family'] for r in rows)}
out=clean({'schema':'warroom.v58.macro_sweep_results.v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(PROTO),'counts':counts,'claims':rows,'status':'REVISED_REUSED_MACRO_DIAGNOSTIC_ONLY','predictive_components_promoted_to_live':0,'research_live_decision_weight':0.0,'capital_permission':'BLOCKED'})
path=ROOT/'results/V58_MACRO_SWEEP_RESULTS.json';path.write_text(json.dumps(out,indent=2,sort_keys=True))
flat=[]
for r in rows:
 d={'claim_id':r['claim_id'],'feature':r['feature'],'family':r['family'],'target':r['target'],'orientation':r['orientation'],'diagnostic_survivor':r['diagnostic_survivor']}
 for sp in splits:
  for k in ['n','beta','hac_t','bonferroni_lb','spearman']:d[f'{sp}_{k}']=r['splits'][sp].get(k)
 flat.append(d)
f=pd.DataFrame(flat).sort_values(['diagnostic_survivor','diagnostic_holdout_beta'],ascending=[False,False]);f.to_csv(ROOT/'results/V58_MACRO_SWEEP_SUMMARY.csv',index=False)
print(json.dumps(counts,indent=2));print(f.head(40).to_string(index=False))
