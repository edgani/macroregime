from __future__ import annotations
import pathlib,json,hashlib,math,datetime
import pandas as pd, numpy as np
from scipy import stats
import statsmodels.api as sm
ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/'research_v66/protocols/V66_DIVERSIFIED_SLEEVE_PROTOCOL_FROZEN.json'; O=ROOT/'research_v66/results/V66_DIVERSIFIED_SLEEVE_RESULTS.json'
def sh(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def read_sheet(file,sheet,headerrow,datecol='DATE'):
 raw=pd.read_excel(file,sheet_name=sheet,header=None); hdr=list(raw.iloc[headerrow,:]); df=raw.iloc[headerrow+1:,:len(hdr)].copy();df.columns=hdr
 df[datecol]=pd.to_datetime(df[datecol],errors='coerce')
 for c in hdr:
  if c!=datecol:df[c]=pd.to_numeric(df[c],errors='coerce')
 return df.dropna(subset=[datecol]).set_index(datecol).sort_index()
def load():
 b=ROOT/'research_v58/data'
 # TSMOM header has blank first cell; reset manually
 raw=pd.read_excel(b/'Time-Series-Momentum-Factors-Monthly.xlsx',sheet_name='TSMOM Factors',header=None)
 cols=['DATE']+list(raw.iloc[17,1:6]); td=raw.iloc[18:,0:6].copy();td.columns=cols;td['DATE']=pd.to_datetime(td['DATE'],errors='coerce')
 for c in cols[1:]:td[c]=pd.to_numeric(td[c],errors='coerce')
 t=td.dropna(subset=['DATE']).set_index('DATE')['TSMOM']
 q=read_sheet(b/'Quality-Minus-Junk-Factors-Monthly.xlsx','QMJ Factors',18)['Global']
 bab=read_sheet(b/'Betting-Against-Beta-Equity-Factors-Monthly.xlsx','BAB Factors',18)['Global']
 v=read_sheet(b/'Value-and-Momentum-Everywhere-Factors-Monthly.xlsx','VME Factors',21)['MOM^AA']
 return pd.concat([t.rename('TSMOM'),q.rename('QMJ_GLOBAL'),bab.rename('BAB_GLOBAL'),v.rename('MOM_AA')],axis=1).dropna().sort_index()
def raw_date_col(*a):return 'DATE'
def hac(x):
 m=sm.OLS(x,np.ones((len(x),1))).fit(cov_type='HAC',cov_kwds={'maxlags':min(6,len(x)-1)});return float(m.params.iloc[0]),float(m.bse.iloc[0]),float(m.tvalues.iloc[0])
def rollfrac(x,w=36):return float(x.rolling(w).mean().dropna().gt(0).mean())
def looy(x):
 ys=sorted(set(x.index.year));return float(min(x[x.index.year!=y].mean() for y in ys))
def mdd(x):
 w=(1+x).cumprod();return float((w/w.cummax()-1).min())
def blockboot(x,reps=20000,block=12,seed=6602):
 a=x.to_numpy(float);n=len(a);rng=np.random.default_rng(seed);vals=[];nb=math.ceil(n/block)
 for _ in range(reps):
  starts=rng.integers(0,n,size=nb);idx=np.concatenate([np.arange(s,s+block)%n for s in starts])[:n];vals.append(a[idx].mean())
 return {'lower_0_333pct':float(np.quantile(vals,0.0033333333333)),'positive_probability':float(np.mean(np.array(vals)>0))}
def evals(s,start,end,z):
 x=s.loc[pd.Timestamp(start):(pd.Timestamp(end) if end else s.index.max())]
 n10=x-0.001;n25=x-0.0025;mean,se,t=hac(n10);bb=blockboot(n10)
 gates={'familywise_lb_positive':bool(mean-z*se>0),'net25_mean_positive':bool(n25.mean()>0),'rolling36_positive_ge75':bool(rollfrac(n10)>=.75),'looy_min_positive':bool(looy(n10)>0),'bootstrap_lb_positive':bool(bb['lower_0_333pct']>0)}
 return {'start':str(x.index.min().date()),'end':str(x.index.max().date()),'n':len(x),'net10':{'mean_monthly':mean,'annualized_mean':12*mean,'hac_se':se,'hac_t':t,'familywise_z':z,'familywise_lower_bound':mean-z*se,'rolling36_positive_fraction':rollfrac(n10),'leave_one_year_out_min_mean':looy(n10),'max_drawdown':mdd(n10),'bootstrap':bb},'net25':{'mean_monthly':float(n25.mean()),'annualized_mean':float(12*n25.mean()),'max_drawdown':mdd(n25)},'gates':gates,'pass':all(gates.values())}
def main():
 p=json.load(open(P));d=load(); forms={'TREND_DEFENSIVE':.5*d.TSMOM+.25*d.QMJ_GLOBAL+.25*d.BAB_GLOBAL,'TREND_CROSSASSET':.5*d.TSMOM+.5*d.MOM_AA,'INSTITUTIONAL_DIVERSIFIED':.4*d.TSMOM+.2*d.QMJ_GLOBAL+.2*d.BAB_GLOBAL+.2*d.MOM_AA}
 z=float(stats.norm.ppf(1-.01/3));res={}
 for i,(k,s) in enumerate(forms.items()):
  va=evals(s,'2010-01-01','2017-12-31',z);lo=evals(s,'2018-01-01',None,z);rva=evals(-s,'2010-01-01','2017-12-31',z);rlo=evals(-s,'2018-01-01',None,z)
  res[k]={'validation':va,'lockbox':lo,'reverse_validation':rva,'reverse_lockbox':rlo,'passes_both':bool(va['pass'] and lo['pass']),'reverse_control_fails':bool(not(rva['pass'] and rlo['pass']))}
 passes=[k for k,v in res.items() if v['passes_both'] and v['reverse_control_fails']]
 out={'schema':'warroom.v66.diversified_sleeve_results.v1','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protocol_sha256':p['protocol_sha256'],'protocol_file_sha256':sh(P),'available_range':[str(d.index.min().date()),str(d.index.max().date())],'results':res,'adjudication':{'survivors':passes,'survivor_count':len(passes),'scoped_claim':'SUPPORTED' if passes else 'NOT_PROVEN','decision_permission':'SHADOW_STRATEGIC_SLEEVE' if passes else 'NONE','live_capital_permission':'BLOCKED_PENDING_EXACT_EXECUTABLE_REPLICATION','ticker_permission':False,'live_weight':0.0},'claim_limit':p['claim_limit']}
 O.write_text(json.dumps(out,indent=2,sort_keys=True));print(json.dumps(out['adjudication'],indent=2));
 for k,v in res.items():print(k,'VA',v['validation']['pass'],v['validation']['net10'],'LO',v['lockbox']['pass'],v['lockbox']['net10'])
if __name__=='__main__':main()
