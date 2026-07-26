from __future__ import annotations
import json,math,pathlib,datetime
import numpy as np,pandas as pd
ROOT=pathlib.Path(__file__).resolve().parents[2]
P=ROOT/'research_v66/protocols/V66_SMA10_RISK_REDUCTION_CONFIRMATION_PROTOCOL_FROZEN.json'
O=ROOT/'research_v66/results/V66_SMA10_RISK_REDUCTION_CONFIRMATION_RESULTS.json'
D=ROOT/'research_v66/data/sp500_monthly_shiller.csv'
def load():
 d=pd.read_csv(D);d.Date=pd.to_datetime(d.Date,errors='coerce')
 for c in ['SP500','Dividend']:d[c]=pd.to_numeric(d[c],errors='coerce')
 d=d.dropna(subset=['Date','SP500']).sort_values('Date').set_index('Date');d=d[(d.SP500>0)&(d.Dividend>0)].copy()
 d['ret']=(d.SP500+d.Dividend/12)/d.SP500.shift(1)-1
 d['sig']=(d.SP500.shift(1)>d.SP500.shift(1).rolling(10).mean()).astype(float)
 return d.dropna(subset=['ret'])
def build(d,cost=10,reverse=False):
 s=d.sig.copy();s=1-s if reverse else s;t=s.diff().abs().fillna(0);g=s*d.ret-cost/10000*t
 return pd.DataFrame({'b':d.ret,'s':s,'t':t,'g':g}).dropna()
def mdd(x):
 w=np.cumprod(1+np.asarray(x,float));return float(np.min(w/np.maximum.accumulate(w)-1))
def es(x):
 a=np.asarray(x,float);k=max(1,int(np.ceil(.05*len(a))));return float(np.partition(a,k-1)[:k].mean())
def caps(g,b):
 up=b>0;dn=b<0;return float(g[up].sum()/b[up].sum()),float(g[dn].sum()/b[dn].sum())
def boot(z,reps,block,seed,q):
 a=z[['b','g']].to_numpy();n=len(a);nb=math.ceil(n/block);rng=np.random.default_rng(seed);ei=[];di=[]
 for off in range(0,reps,250):
  nrep=min(250,reps-off);st=rng.integers(0,n,size=(nrep,nb));idx=np.concatenate([((st[:,j,None]+np.arange(block)[None,:])%n) for j in range(nb)],1)[:,:n]
  b=a[idx,0];g=a[idx,1];k=max(1,int(np.ceil(.05*n)));bei=np.partition(b,k-1,axis=1)[:,:k].mean(1);gei=np.partition(g,k-1,axis=1)[:,:k].mean(1);ei.extend((gei-bei).tolist())
  bw=np.cumprod(1+b,1);gw=np.cumprod(1+g,1);bd=np.min(bw/np.maximum.accumulate(bw,1)-1,1);gd=np.min(gw/np.maximum.accumulate(gw,1)-1,1);di.extend((gd-bd).tolist())
 ei=np.asarray(ei);di=np.asarray(di)
 return {'es_lower':float(np.quantile(ei,q)),'es_positive_probability':float(np.mean(ei>0)),'dd_lower':float(np.quantile(di,q)),'dd_positive_probability':float(np.mean(di>0))}
def ev(z,p,seed):
 b=z.b.to_numpy();g=z.g.to_numpy();up,dn=caps(g,b);bm=mdd(b);gm=mdd(g);be=es(b);ge=es(g);q=p['selection_correction']['quantile'];bt=boot(z,p['bootstrap']['repetitions'],p['bootstrap']['moving_block_months'],seed,q)
 return {'start':str(z.index.min().date()),'end':str(z.index.max().date()),'n':len(z),'bench_ann':float(b.mean()*12),'gate_ann':float(g.mean()*12),'ret_diff':float((g.mean()-b.mean())*12),'bench_mdd':bm,'gate_mdd':gm,'dd_improvement':gm-bm,'bench_es5':be,'gate_es5':ge,'es_improvement':ge-be,'up_capture':up,'down_capture':dn,'avg_exposure':float(z.s.mean()),'avg_turnover':float(z.t.mean()),'bootstrap':bt}
def rolling(x,start,end,years=20,step=12):
 z=x.loc[start:end];months=years*12;rows=[]
 for i in range(0,len(z)-months+1,step):
  q=z.iloc[i:i+months];r=ev(q,{'selection_correction':{'quantile':.0005882352941176471},'bootstrap':{'repetitions':1000,'moving_block_months':12}},7000+i)
  rows.append({'start':r['start'],'end':r['end'],'es_imp':r['es_improvement'],'dd_imp':r['dd_improvement'],'ret_diff':r['ret_diff']})
 return rows
def main():
 p=json.load(open(P));d=load();x=build(d,10);xs=build(d,25);xr=build(d,10,True)
 a,b=p['confirmatory_holdout'];c=ev(x.loc[a:b],p,6618);cs=ev(xs.loc[a:b],p,6619);r=ev(xr.loc[a:b],p,6620)
 rows=rolling(x,p['rolling_stability']['start'],p['rolling_stability']['end'],p['rolling_stability']['window_years'],p['rolling_stability']['step_months'])
 es_share=float(np.mean([q['es_imp']>0 for q in rows]));dd_share=float(np.mean([q['dd_imp']>0 for q in rows]));ret_med=float(np.median([q['ret_diff'] for q in rows]))
 g={
  'dd':c['dd_improvement']>=p['gates']['confirmatory_max_drawdown_improvement_ge'],
  'es':c['es_improvement']>p['gates']['confirmatory_expected_shortfall5_improvement_gt'],
  'ret':c['ret_diff']>=p['gates']['confirmatory_annualized_return_shortfall_ge'],
  'down':c['down_capture']<p['gates']['confirmatory_downside_capture_lt'],
  'up':c['up_capture']>=p['gates']['confirmatory_upside_capture_ge'],
  'boot_es':c['bootstrap']['es_lower']>p['gates']['confirmatory_bootstrap_es_lower_gt'],
  'boot_dd':c['bootstrap']['dd_positive_probability']>=p['gates']['confirmatory_bootstrap_drawdown_positive_probability_ge'],
  'stress_es':cs['es_improvement']>p['gates']['stress25_es_improvement_gt'],
  'roll_es':es_share>=p['gates']['rolling_es_improvement_positive_share_ge'],
  'roll_dd':dd_share>=p['gates']['rolling_drawdown_improvement_positive_share_ge'],
  'roll_ret':ret_med>=p['gates']['rolling_return_shortfall_median_ge'],
  'reverse_fail':not(r['dd_improvement']>=p['gates']['confirmatory_max_drawdown_improvement_ge'] and r['es_improvement']>0 and r['ret_diff']>=p['gates']['confirmatory_annualized_return_shortfall_ge'])
 }
 passed=all(g.values())
 out={'schema':'warroom.v66.sma10_risk_reduction_confirmation_results.v1','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protocol_sha256':p['protocol_sha256'],'confirmatory':c,'confirmatory_25bps':cs,'reverse_control':r,'rolling':{'n_windows':len(rows),'es_positive_share':es_share,'dd_positive_share':dd_share,'return_difference_median':ret_med,'rows':rows},'gates':g,'passed':passed,'adjudication':{'scoped_claim':'CONFIRMED_HISTORICAL_RISK_REDUCTION' if passed else 'NOT_PROVEN','decision_permission':p['decision_scope_if_passed']['permission'] if passed else 'NONE','capital_permission':p['decision_scope_if_passed']['capital_permission'] if passed else 'BLOCKED','ticker_permission':False,'crash_prediction_permission':False},'claim_limit':p['claim_limit']}
 O.write_text(json.dumps(out,indent=2,sort_keys=True));print(json.dumps({'passed':passed,'confirmatory':c,'rolling':out['rolling']|{'rows':None},'gates':g},indent=2))
if __name__=='__main__':main()
