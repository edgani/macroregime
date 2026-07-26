from __future__ import annotations
import json, hashlib, math, re, sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np, pandas as pd
from scipy.stats import norm
import statsmodels.api as sm
ROOT=Path('/mnt/data/v58_work/research_v58'); PROTO=ROOT/'protocols/V58_PRICE_VOLUME_SWEEP_PROTOCOL_FROZEN.json'
sys.path.insert(0,'/mnt/data/v58_work/research_v55')
from flat_parquet_snappy import read_flat_parquet

def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def hac_lb(x,z,lags=2):
 x=np.asarray(x,float);x=x[np.isfinite(x)]
 if len(x)<4:return {'n':len(x),'mean':None,'hac_se':None,'hac_t':None,'bonferroni_lb':None}
 r=sm.OLS(x,np.ones((len(x),1))).fit(cov_type='HAC',cov_kwds={'maxlags':min(lags,len(x)-1),'use_correction':True})
 mu=float(np.mean(x));se=float(r.bse[0]);return {'n':len(x),'mean':mu,'hac_se':se,'hac_t':mu/se if se>0 else None,'bonferroni_lb':mu-z*se}
def eval_dates(f,t,dates,sign):
 ics=[];spreads=[];ns=[]
 for dt in dates:
  if dt not in f.index or dt not in t.index:continue
  x=f.loc[dt]*sign;y=t.loc[dt]
  q=pd.concat([x.rename('x'),y.rename('y')],axis=1).replace([np.inf,-np.inf],np.nan).dropna()
  if len(q)<50:continue
  ic=q.x.corr(q.y,method='spearman')
  ranks=q.x.rank(pct=True,method='average')
  top=q.loc[ranks>=0.8,'y'].mean();bot=q.loc[ranks<=0.2,'y'].mean()
  ics.append(ic);spreads.append(float(top-bot));ns.append(len(q))
 return np.array(ics,float),np.array(spreads,float),ns

def clean(x):
 if isinstance(x,float) and (not np.isfinite(x)):return None
 if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
 if isinstance(x,list):return [clean(v) for v in x]
 return x
p=json.load(open(PROTO));z=float(norm.ppf(1-0.05/p['registered_claims']))
raw=read_flat_parquet('/mnt/data/v58_work/research/sp500_panel.parquet')
raw['date']=pd.to_datetime(raw['date']);raw=raw.sort_values(['date','Name'])
def piv(c):return raw.pivot(index='date',columns='Name',values=c).sort_index()
close,open_,high,low,volume=[piv(c) for c in ['close','open','high','low','volume']]
# Remove impossible/nonpositive points; retain source unchanged.
for x in [close,open_,high,low,volume]:x[x<=0]=np.nan
ret=close.pct_change(fill_method=None).replace([np.inf,-np.inf],np.nan)
# Clip only feature daily returns to reduce split/outlier contamination; future target remains raw but filtered below.
ret_feat=ret.clip(-0.5,0.5)
market_ret=ret_feat.mean(axis=1,skipna=True)
month_last=pd.Series(close.index,index=close.index).groupby(close.index.to_period('M')).last().values
dates=pd.DatetimeIndex(month_last)
splits={
 'discovery':dates[(dates>=pd.Timestamp('2014-01-01'))&(dates<=pd.Timestamp('2015-12-31'))],
 'validation':dates[(dates>=pd.Timestamp('2016-01-01'))&(dates<=pd.Timestamp('2016-12-31'))],
 'diagnostic_holdout':dates[(dates>=pd.Timestamp('2017-01-01'))&(dates<=pd.Timestamp('2018-02-28'))]}
targets={h:(close.shift(-h)/close-1).where(lambda x:x.abs()<=3.0) for h in [21,63]}
cache={}
def roll(name,h,fn):
 k=(name,h)
 if k not in cache:cache[k]=fn(h)
 return cache[k]
def mom(h):return close/close.shift(h)-1
def vol(h):return ret_feat.rolling(h,min_periods=max(3,h//2)).std()
def downvol(h):return ret_feat.clip(upper=0).rolling(h,min_periods=max(3,h//2)).std()
def beta(h):
 k=('beta',h)
 if k not in cache:
  cov=ret_feat.rolling(h,min_periods=max(5,h//2)).cov(market_ret)
  cache[k]=cov.div(market_ret.rolling(h,min_periods=max(5,h//2)).var(),axis=0)
 return cache[k]
def feature(name):
 m=re.match(r'mom_(\d+)$',name)
 if m:return mom(int(m.group(1)))
 m=re.match(r'reversal_(\d+)$',name)
 if m:return -mom(int(m.group(1)))
 m=re.match(r'mom_(\d+)_skip_(\d+)',name)
 if m:return close.shift(int(m.group(2)))/close.shift(int(m.group(1)))-1
 m=re.match(r'vol_(\d+)',name)
 if m:return vol(int(m.group(1)))
 m=re.match(r'downvol_(\d+)',name)
 if m:return downvol(int(m.group(1)))
 m=re.match(r'(skew|kurt|maxret|minret)_(\d+)',name)
 if m:
  typ,h=m.group(1),int(m.group(2));r=ret_feat.rolling(h,min_periods=max(5,h//2))
  return {'skew':r.skew(),'kurt':r.kurt(),'maxret':r.max(),'minret':r.min()}[typ]
 m=re.match(r'dist_high_(\d+)',name)
 if m:
  h=int(m.group(1));return close/close.rolling(h,min_periods=max(5,h//2)).max()-1
 m=re.match(r'dist_low_(\d+)',name)
 if m:
  h=int(m.group(1));return close/close.rolling(h,min_periods=max(5,h//2)).min()-1
 m=re.match(r'sma_dist_(\d+)',name)
 if m:
  h=int(m.group(1));return close/close.rolling(h,min_periods=max(5,h//2)).mean()-1
 m=re.match(r'efficiency_(\d+)',name)
 if m:
  h=int(m.group(1));return mom(h).abs()/ret_feat.abs().rolling(h,min_periods=max(5,h//2)).sum()
 m=re.match(r'volume_z_(\d+)',name)
 if m:
  h=int(m.group(1));lv=np.log(volume);rr=lv.rolling(h,min_periods=max(3,h//2));return (lv-rr.mean())/rr.std()
 m=re.match(r'dollar_volume_(\d+)',name)
 if m:
  h=int(m.group(1));return (close*volume).rolling(h,min_periods=max(3,h//2)).mean()
 m=re.match(r'amihud_(\d+)',name)
 if m:
  h=int(m.group(1));return (ret_feat.abs()/(close*volume)).rolling(h,min_periods=max(3,h//2)).mean()
 m=re.match(r'range_(\d+)',name)
 if m:
  h=int(m.group(1));return ((high-low)/close).rolling(h,min_periods=max(3,h//2)).mean()
 m=re.match(r'clv_(\d+)',name)
 if m:
  h=int(m.group(1));return ((close-low)/(high-low).replace(0,np.nan)).rolling(h,min_periods=max(3,h//2)).mean()
 m=re.match(r'volume_ratio_(\d+)_(\d+)',name)
 if m:
  a,b=map(int,m.groups());return volume.rolling(a,min_periods=max(3,a//2)).mean()/volume.rolling(b,min_periods=max(3,b//2)).mean()
 m=re.match(r'intraday_(\d+)',name)
 if m:
  h=int(m.group(1));return (close/open_-1).rolling(h,min_periods=max(3,h//2)).mean()
 m=re.match(r'overnight_(\d+)',name)
 if m:
  h=int(m.group(1));return (open_/close.shift(1)-1).rolling(h,min_periods=max(3,h//2)).mean()
 m=re.match(r'beta_(\d+)',name)
 if m:return beta(int(m.group(1)))
 m=re.match(r'residual_mom_(\d+)',name)
 if m:
  h=int(m.group(1));market_mom=(1+market_ret).rolling(h,min_periods=max(5,h//2)).apply(np.prod,raw=True)-1
  return mom(h)-beta(h).mul(market_mom,axis=0)
 if name=='mom63_over_vol21':return mom(63)/vol(21)
 if name=='mom126_over_vol63':return mom(126)/vol(63)
 if name=='mom252_over_vol63':return mom(252)/vol(63)
 if name=='mom63_x_volumez21':return mom(63)*feature('volume_z_21')
 if name=='dist_high63_x_volumez21':return feature('dist_high_63')*feature('volume_z_21')
 if name=='reversal5_x_amihud21':return feature('reversal_5')*feature('amihud_21').rank(axis=1,pct=True)
 if name=='lowvol21_x_mom63':return -vol(21)+mom(63)
 if name=='range21_x_mom21':return feature('range_21')*mom(21)
 if name=='clv21_x_volumez21':return feature('clv_21')*feature('volume_z_21')
 if name=='price_level':return np.log(close)
 if name=='alphabetical_ticker':return pd.DataFrame(np.tile(np.arange(close.shape[1]),(close.shape[0],1)),index=close.index,columns=close.columns)
 if name=='calendar_month':return pd.DataFrame(np.tile(close.index.month.values[:,None],(1,close.shape[1])),index=close.index,columns=close.columns)
 if name=='deterministic_hash_noise':
  r=np.arange(close.shape[0])[:,None];c=np.arange(close.shape[1])[None,:];a=np.sin(r*12.9898+c*78.233)*43758.5453
  return pd.DataFrame(a-np.floor(a),index=close.index,columns=close.columns)
 raise KeyError(name)
rows=[]
for fi,fd in enumerate(p['features']):
 f=feature(fd['feature']).replace([np.inf,-np.inf],np.nan)
 for h,t in targets.items():
  disc_ic,disc_spread,_=eval_dates(f,t,splits['discovery'],1)
  orient=1 if len(disc_ic)==0 or np.nanmean(disc_ic)>=0 else -1
  rec={'claim_id':f"{fd['feature']}:future_{h}d_return",'feature':fd['feature'],'family':fd['family'],'target_horizon_days':h,'orientation':orient,'splits':{}}
  for sp in ['discovery','validation','diagnostic_holdout']:
   ic,spread,ns=eval_dates(f,t,splits[sp],orient)
   rec['splits'][sp]={'ic':hac_lb(ic,z),'spread':hac_lb(spread,z),'mean_cross_section_n':float(np.mean(ns)) if ns else None}
  v=rec['splits']['validation']['ic'];d=rec['splits']['diagnostic_holdout']['ic']
  rec['diagnostic_survivor']=bool(v['mean'] is not None and d['mean'] is not None and v['mean']>0 and d['mean']>0 and v['bonferroni_lb'] is not None and d['bonferroni_lb'] is not None and v['bonferroni_lb']>0 and d['bonferroni_lb']>0)
  rec['live_decision_weight']=0.0;rec['capital_permission']='BLOCKED';rows.append(rec)
counts={'registered':len(rows),'diagnostic_survivors':sum(r['diagnostic_survivor'] for r in rows),'placebo_claims':sum('placebo' in r['family'] for r in rows),'placebo_survivors':sum(r['diagnostic_survivor'] and 'placebo' in r['family'] for r in rows)}
out={'schema':'warroom.v58.price_volume_sweep_results.v1','created_at_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(PROTO),'counts':counts,'claims':rows,
 'status':'REUSED_FIXED_UNIVERSE_DIAGNOSTIC_ONLY','interpretation':'No claim is proof because the panel is fixed-universe, corporate-action limited, and previously reused. Survivors only prioritize fresh point-in-time replication.',
 'predictive_components_promoted_to_live':0,'research_live_decision_weight':0.0,'capital_permission':'BLOCKED'}
out=clean(out);path=ROOT/'results/V58_PRICE_VOLUME_SWEEP_RESULTS.json';path.write_text(json.dumps(out,indent=2,sort_keys=True))
flat=[]
for r in rows:
 d={'claim_id':r['claim_id'],'feature':r['feature'],'family':r['family'],'horizon':r['target_horizon_days'],'orientation':r['orientation'],'diagnostic_survivor':r['diagnostic_survivor']}
 for sp in ['discovery','validation','diagnostic_holdout']:
  for metric in ['ic','spread']:
   for k in ['n','mean','hac_t','bonferroni_lb']:
    d[f'{sp}_{metric}_{k}']=r['splits'][sp][metric].get(k)
 flat.append(d)
f=pd.DataFrame(flat).sort_values(['diagnostic_survivor','diagnostic_holdout_ic_mean'],ascending=[False,False]);f.to_csv(ROOT/'results/V58_PRICE_VOLUME_SWEEP_SUMMARY.csv',index=False)
print(json.dumps(counts,indent=2));print(f.head(40).to_string(index=False))
