from __future__ import annotations
import pathlib,json,hashlib,math,datetime
import pandas as pd,numpy as np
from scipy import stats
import statsmodels.api as sm
ROOT=pathlib.Path(__file__).resolve().parents[2]; P=ROOT/'research_v66/protocols/V66_STYLE_PARITY_PROTOCOL_FROZEN.json';O=ROOT/'research_v66/results/V66_STYLE_PARITY_RESULTS.json'
def read(file,sheet,hr):
 r=pd.read_excel(file,sheet_name=sheet,header=None);h=list(r.iloc[hr,:]);d=r.iloc[hr+1:,:len(h)].copy();d.columns=h;d['DATE']=pd.to_datetime(d['DATE'],errors='coerce')
 for c in h[1:]:d[c]=pd.to_numeric(d[c],errors='coerce')
 return d.dropna(subset=['DATE']).set_index('DATE').sort_index()
def load():
 b=ROOT/'research_v58/data'
 r=pd.read_excel(b/'Time-Series-Momentum-Factors-Monthly.xlsx',sheet_name='TSMOM Factors',header=None);h=['DATE']+list(r.iloc[17,1:6]);t=r.iloc[18:,0:6].copy();t.columns=h;t.DATE=pd.to_datetime(t.DATE,errors='coerce');
 for c in h[1:]:t[c]=pd.to_numeric(t[c],errors='coerce')
 t=t.dropna(subset=['DATE']).set_index('DATE')
 v=read(b/'Value-and-Momentum-Everywhere-Factors-Monthly.xlsx','VME Factors',21);q=read(b/'Quality-Minus-Junk-Factors-Monthly.xlsx','QMJ Factors',18);bb=read(b/'Betting-Against-Beta-Equity-Factors-Monthly.xlsx','BAB Factors',18)
 return pd.concat([t.TSMOM.rename('TSMOM'),v.VAL.rename('VAL'),v.MOM.rename('MOM'),v['VAL^AA'].rename('VAL_AA'),v['MOM^AA'].rename('MOM_AA'),q.Global.rename('QMJ'),bb.Global.rename('BAB')],axis=1).dropna().sort_index()
def volscale(df,cols):
 vol=df[cols].rolling(36).std().shift(1)*np.sqrt(12);scale=(.10/vol).clip(.25,2.0);return (df[cols]*scale).mean(axis=1)
def hac(x):
 m=sm.OLS(x.to_numpy(),np.ones((len(x),1))).fit(cov_type='HAC',cov_kwds={'maxlags':6});return float(m.params[0]),float(m.bse[0]),float(m.tvalues[0])
def roll(x):return float(x.rolling(36).mean().dropna().gt(0).mean())
def looy(x):return float(min(x[x.index.year!=y].mean() for y in sorted(set(x.index.year))))
def mdd(x):
 w=(1+x).cumprod();return float((w/w.cummax()-1).min())
def bb(x,reps=20000,block=12,seed=6603):
 a=x.to_numpy();n=len(a);rng=np.random.default_rng(seed);nb=math.ceil(n/block);z=[]
 for _ in range(reps):
  st=rng.integers(0,n,nb);idx=np.concatenate([np.arange(s,s+block)%n for s in st])[:n];z.append(a[idx].mean())
 return {'lower_0_1pct':float(np.quantile(z,.001)),'positive_probability':float(np.mean(np.array(z)>0))}
def ev(s,a,b,z):
 x=s.loc[pd.Timestamp(a):(pd.Timestamp(b) if b else s.index.max())].dropna();n10=x-.001;n25=x-.0025;mn,se,t=hac(n10);boot=bb(n10)
 g={'lb':bool(mn-z*se>0),'net25':bool(n25.mean()>0),'rolling':bool(roll(n10)>=.75),'looy':bool(looy(n10)>0),'boot':bool(boot['lower_0_1pct']>0)}
 return {'start':str(x.index.min().date()),'end':str(x.index.max().date()),'n':len(x),'net10':{'mean':mn,'annualized':12*mn,'se':se,'t':t,'z':z,'lb':mn-z*se,'rolling36_positive':roll(n10),'looy_min':looy(n10),'mdd':mdd(n10),'bootstrap':boot},'net25':{'mean':float(n25.mean()),'annualized':float(12*n25.mean()),'mdd':mdd(n25)},'gates':g,'pass':all(g.values())}
def main():
 p=json.load(open(P));d=load();forms={'RAW_FIVE_STYLE_EQUAL':d[['TSMOM','VAL','MOM','BAB','QMJ']].mean(axis=1),'VOL_BALANCED_FIVE_STYLE':volscale(d,['TSMOM','VAL','MOM','BAB','QMJ']),'VOL_BALANCED_CROSS_ASSET':volscale(d,['TSMOM','VAL_AA','MOM_AA','BAB','QMJ'])};z=float(stats.norm.ppf(1-.01/10));R={}
 for k,s in forms.items():
  va=ev(s,'2010-01-01','2017-12-31',z);lo=ev(s,'2018-01-01',None,z);rva=ev(-s,'2010-01-01','2017-12-31',z);rlo=ev(-s,'2018-01-01',None,z);R[k]={'validation':va,'lockbox':lo,'reverse_validation':rva,'reverse_lockbox':rlo,'pass':bool(va['pass'] and lo['pass'] and not(rva['pass'] and rlo['pass']))}
 surv=[k for k,v in R.items() if v['pass']];out={'schema':'warroom.v66.style_parity_results.v1','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protocol_sha256':p['protocol_sha256'],'results':R,'adjudication':{'survivors':surv,'scoped_claim':'SUPPORTED' if surv else 'NOT_PROVEN','permission':'SHADOW_STYLE_SLEEVE' if surv else 'NONE','live_weight':0.0,'capital_permission':'BLOCKED_PENDING_EXACT_EXECUTION','ticker_permission':False},'claim_limit':p['claim_limit']};O.write_text(json.dumps(out,indent=2,sort_keys=True));print(json.dumps(out['adjudication'],indent=2));
 for k,v in R.items():print(k,'VA',v['validation']['pass'],v['validation']['net10'],'LO',v['lockbox']['pass'],v['lockbox']['net10'])
if __name__=='__main__':main()
