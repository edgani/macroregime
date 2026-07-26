from __future__ import annotations
import pathlib,json,math,datetime
import pandas as pd,numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[2];P=ROOT/'research_v66/protocols/V66_GLOBAL_EQUITY_RISK_GATE_PROTOCOL_FROZEN.json';O=ROOT/'research_v66/results/V66_GLOBAL_EQUITY_RISK_GATE_RESULTS.json'
def load():
 f=ROOT/'research_v58/data/Quality-Minus-Junk-Factors-Monthly.xlsx';r=pd.read_excel(f,sheet_name='MKT',header=None);h=list(r.iloc[18,:30]);d=r.iloc[19:,:30].copy();d.columns=h;d.DATE=pd.to_datetime(d.DATE,errors='coerce');
 for c in h[1:]:d[c]=pd.to_numeric(d[c],errors='coerce')
 return d.dropna(subset=['DATE']).set_index('DATE').Global.dropna().sort_index()
def build(m,costbps=10,reverse=False):
 tr12=(1+m).rolling(12).apply(np.prod,raw=True)-1;sig=(tr12.shift(1)>0).astype(float)
 if reverse:sig=1-sig
 turn=sig.diff().abs();net=sig*m-(costbps/10000)*turn.fillna(0)
 return pd.DataFrame({'mkt':m,'signal':sig,'turnover':turn,'gate':net}).dropna()
def mdd(x):w=(1+x).cumprod();return float((w/w.cummax()-1).min())
def es(x):
 a=np.sort(np.asarray(x,float));k=max(1,int(np.ceil(.05*len(a))));return float(a[:k].mean())
def captures(g,m):
 up=m>0;dn=m<0;return float(g[up].sum()/m[up].sum()),float(g[dn].sum()/m[dn].sum())
def bootstrap(df,reps=10000,block=12,seed=6605):
    n=len(df); rng=np.random.default_rng(seed); nb=math.ceil(n/block); a=df[['mkt','gate']].to_numpy(); esimp=[]; ddimp=[]
    chunk=250
    for off in range(0,reps,chunk):
        b=min(chunk,reps-off); starts=rng.integers(0,n,size=(b,nb))
        idx=np.concatenate([((starts[:,j,None]+np.arange(block)[None,:])%n) for j in range(nb)],axis=1)[:,:n]
        m=a[idx,0]; g=a[idx,1]
        k=max(1,int(np.ceil(.05*n)))
        mes=np.partition(m,k-1,axis=1)[:,:k].mean(axis=1); ges=np.partition(g,k-1,axis=1)[:,:k].mean(axis=1); esimp.extend((ges-mes).tolist())
        mw=np.cumprod(1+m,axis=1); gw=np.cumprod(1+g,axis=1)
        mpeak=np.maximum.accumulate(mw,axis=1); gpeak=np.maximum.accumulate(gw,axis=1)
        mddv=np.min(mw/mpeak-1,axis=1); gddv=np.min(gw/gpeak-1,axis=1); ddimp.extend((gddv-mddv).tolist())
    return {'es_improvement_lower_0_0769pct':float(np.quantile(esimp,.000769230769)),'es_improvement_positive_probability':float(np.mean(np.array(esimp)>0)),'drawdown_improvement_positive_probability':float(np.mean(np.array(ddimp)>0)),'drawdown_improvement_lower_0_0769pct':float(np.quantile(ddimp,.000769230769))}
def ev(x,a,b):
 d=x.loc[pd.Timestamp(a):(pd.Timestamp(b) if b else x.index.max())];up,down=captures(d.gate,d.mkt);bm=mdd(d.mkt);gm=mdd(d.gate);be=es(d.mkt);ge=es(d.gate);boot=bootstrap(d)
 ar_b=float(d.mkt.mean()*12);ar_g=float(d.gate.mean()*12)
 gates={'dd':bool(gm-bm>=.05),'es':bool(ge-be>0),'return_shortfall':bool(ar_g-ar_b>=-.02),'down_capture':bool(down<.8),'up_capture':bool(up>=.6),'boot_es':bool(boot['es_improvement_lower_0_0769pct']>0),'boot_dd_prob':bool(boot['drawdown_improvement_positive_probability']>=.95)}
 return {'start':str(d.index.min().date()),'end':str(d.index.max().date()),'n':len(d),'benchmark_annualized_mean':ar_b,'gate_annualized_mean':ar_g,'return_difference':ar_g-ar_b,'benchmark_mdd':bm,'gate_mdd':gm,'drawdown_improvement':gm-bm,'benchmark_es5':be,'gate_es5':ge,'es5_improvement':ge-be,'upside_capture':up,'downside_capture':down,'avg_exposure':float(d.signal.mean()),'avg_turnover':float(d.turnover.mean()),'bootstrap':boot,'gates':gates,'pass':all(gates.values())}
def main():
 p=json.load(open(P));m=load();x=build(m,10);xs=build(m,25);xr=build(m,10,True);va=ev(x,'2010-01-01','2017-12-31');lo=ev(x,'2018-01-01',None);sv=ev(xs,'2010-01-01','2017-12-31');sl=ev(xs,'2018-01-01',None);rv=ev(xr,'2010-01-01','2017-12-31');rl=ev(xr,'2018-01-01',None);passed=va['pass'] and lo['pass'] and not(rv['pass'] and rl['pass'])
 out={'schema':'warroom.v66.global_equity_risk_gate_results.v1','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protocol_sha256':p['protocol_sha256'],'validation':va,'lockbox':lo,'validation_25bps':sv,'lockbox_25bps':sl,'reverse_validation':rv,'reverse_lockbox':rl,'current_frozen_signal':int(x.signal.iloc[-1]),'current_frozen_signal_date':str(x.index[-1].date()),'adjudication':{'passed':bool(passed),'scoped_claim':'SUPPORTED' if passed else 'NOT_PROVEN','decision_permission':'REDUCE_GLOBAL_EQUITY_RISK_ONLY' if passed else 'NONE','ticker_permission':False,'may_increase_exposure':False,'capital_permission':'CONDITIONAL_DOWNSIDE_CAP' if passed else 'BLOCKED','live_weight':0.0 if not passed else None},'claim_limit':p['claim_limit']};O.write_text(json.dumps(out,indent=2,sort_keys=True));print(json.dumps(out,indent=2)[:10000])
if __name__=='__main__':main()
