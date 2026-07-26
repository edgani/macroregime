from __future__ import annotations
import pathlib,json,math,datetime
import pandas as pd,numpy as np
from scipy import stats
import statsmodels.api as sm
ROOT=pathlib.Path(__file__).resolve().parents[2];P=ROOT/'research_v66/protocols/V66_FACTOR_MOMENTUM_PROTOCOL_FROZEN.json';O=ROOT/'research_v66/results/V66_FACTOR_MOMENTUM_RESULTS.json'
def read(file,sheet,hr):
 r=pd.read_excel(file,sheet_name=sheet,header=None);h=list(r.iloc[hr,:]);d=r.iloc[hr+1:,:len(h)].copy();d.columns=h;d['DATE']=pd.to_datetime(d['DATE'],errors='coerce');
 for c in h[1:]:d[c]=pd.to_numeric(d[c],errors='coerce')
 return d.dropna(subset=['DATE']).set_index('DATE').sort_index()
def load():
 b=ROOT/'research_v58/data';r=pd.read_excel(b/'Time-Series-Momentum-Factors-Monthly.xlsx',sheet_name='TSMOM Factors',header=None);h=['DATE']+list(r.iloc[17,1:6]);t=r.iloc[18:,0:6].copy();t.columns=h;t.DATE=pd.to_datetime(t.DATE,errors='coerce');
 for c in h[1:]:t[c]=pd.to_numeric(t[c],errors='coerce')
 t=t.dropna(subset=['DATE']).set_index('DATE');v=read(b/'Value-and-Momentum-Everywhere-Factors-Monthly.xlsx','VME Factors',21);q=read(b/'Quality-Minus-Junk-Factors-Monthly.xlsx','QMJ Factors',18);bb=read(b/'Betting-Against-Beta-Equity-Factors-Monthly.xlsx','BAB Factors',18)
 return pd.concat([t.TSMOM.rename('TSMOM'),v.VAL.rename('VAL'),v.MOM.rename('MOM'),bb.Global.rename('BAB'),q.Global.rename('QMJ')],axis=1).dropna().sort_index()
def construct(d,longcash=False,reverse=False,costbps=10):
 trailing=(1+d).rolling(12).apply(np.prod,raw=True)-1;sg=np.sign(trailing).shift(1)
 if longcash:sg=(sg>0).astype(float)
 if reverse:sg=-sg
 w=sg/len(d.columns);gross=(w*d).sum(axis=1);turn=.5*w.diff().abs().sum(axis=1);net=gross-.0005-(costbps/10000)*turn
 return pd.DataFrame({'gross':gross,'net':net,'turnover':turn}).dropna()
def hac(x):
 m=sm.OLS(x.to_numpy(),np.ones((len(x),1))).fit(cov_type='HAC',cov_kwds={'maxlags':6});return float(m.params[0]),float(m.bse[0]),float(m.tvalues[0])
def roll(x):return float(x.rolling(36).mean().dropna().gt(0).mean())
def looy(x):return float(min(x[x.index.year!=y].mean() for y in sorted(set(x.index.year))))
def mdd(x):w=(1+x).cumprod();return float((w/w.cummax()-1).min())
def boot(x,reps=20000,block=12,seed=6604):
 a=x.to_numpy();n=len(a);rng=np.random.default_rng(seed);nb=math.ceil(n/block);v=[]
 for _ in range(reps):
  st=rng.integers(0,n,nb);idx=np.concatenate([np.arange(s,s+block)%n for s in st])[:n];v.append(a[idx].mean())
 return {'lower_0_0833pct':float(np.quantile(v,.000833333333)),'positive_probability':float(np.mean(np.array(v)>0))}
def ev(x,a,b,z):
 s=x.loc[pd.Timestamp(a):(pd.Timestamp(b) if b else x.index.max())];mn,se,t=hac(s.net);bb=boot(s.net);g={'lb':bool(mn-z*se>0),'rolling':bool(roll(s.net)>=.75),'looy':bool(looy(s.net)>0),'boot':bool(bb['lower_0_0833pct']>0)}
 return {'start':str(s.index.min().date()),'end':str(s.index.max().date()),'n':len(s),'mean':mn,'annualized':12*mn,'se':se,'t':t,'z':z,'lb':mn-z*se,'rolling36_positive':roll(s.net),'looy_min':looy(s.net),'mdd':mdd(s.net),'avg_turnover':float(s.turnover.mean()),'bootstrap':bb,'gates':g,'pass':all(g.values())}
def main():
 p=json.load(open(P));d=load();z=float(stats.norm.ppf(1-.01/12));R={}
 for name,lc in [('FACTOR_MOMENTUM_SIGN',False),('FACTOR_MOMENTUM_LONG_CASH',True)]:
  x=construct(d,lc,False,10);xs=construct(d,lc,False,25);xr=construct(d,lc,True,10);va=ev(x,'2010-01-01','2017-12-31',z);lo=ev(x,'2018-01-01',None,z);sv=ev(xs,'2010-01-01','2017-12-31',z);sl=ev(xs,'2018-01-01',None,z);rv=ev(xr,'2010-01-01','2017-12-31',z);rl=ev(xr,'2018-01-01',None,z)
  R[name]={'validation_primary':va,'lockbox_primary':lo,'validation_25bps_turnover':sv,'lockbox_25bps_turnover':sl,'reverse_validation':rv,'reverse_lockbox':rl,'pass':bool(va['pass'] and lo['pass'] and sv['mean']>0 and sl['mean']>0 and not(rv['pass'] and rl['pass']))}
 surv=[k for k,v in R.items() if v['pass']];out={'schema':'warroom.v66.factor_momentum_results.v1','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protocol_sha256':p['protocol_sha256'],'results':R,'adjudication':{'survivors':surv,'claim':'SUPPORTED' if surv else 'NOT_PROVEN','permission':'SHADOW_ADAPTIVE_STYLE_SLEEVE' if surv else 'NONE','live_weight':0.0,'capital_permission':'BLOCKED_PENDING_EXACT_INSTRUMENT_REPLICATION','ticker_permission':False},'claim_limit':p['claim_limit']};O.write_text(json.dumps(out,indent=2,sort_keys=True));print(json.dumps(out['adjudication'],indent=2));
 for k,v in R.items():print(k,'VA',v['validation_primary'],'LO',v['lockbox_primary'])
if __name__=='__main__':main()
