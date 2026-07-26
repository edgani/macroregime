from pathlib import Path
import pandas as pd, numpy as np, json, hashlib, math
BASE=Path('/mnt/data/warroom_v60_work/src');O=BASE/'research_v60'
P={'study_id':'V61_OPENAP_PAIR_CAPACITY_OUTLIER_STRESS','candidate_set':'61 V61 strict robustness survivors, no discretionary selection','registration_note':'Post-discovery stress test; not untouched proof.','transform':'clip each signed constituent monthly return to +/-20% before equal weighting','cost_stress_bps_per_month':[25,50,100],'gates':['falsification NW t>2','after 100bps positive','4/5 positive years','both 2020-22 and 2023-24 positive','rolling 24-month means positive >=80%','delete best month then after 25bps positive'],'claim_limit':'Cannot replace value-weighted, liquidity-screened, stock-level point-in-time replication.','live_decision_weight':0.0,'capital_permission':'BLOCKED'}
pp=O/'protocols/V61_OPENAP_CAPACITY_STRESS_PROTOCOL_FROZEN.json';pp.write_text(json.dumps(P,indent=2,sort_keys=True));ph=hashlib.sha256(pp.read_bytes()).hexdigest()
D=pd.read_csv(BASE/'research_v58/data/PredictorLSretWide.csv');D.date=pd.to_datetime(D.date);Lmask=D.date.between('2020-01-01','2024-12-31');dates=D.loc[Lmask,'date'].reset_index(drop=True)
R=pd.read_csv(O/'ledgers/V61_OPENAP_PAIR_ROBUSTNESS_LEDGER.csv');R=R[R.passes_strict_robustness.astype(str).str.lower().isin(['true','1'])]
def nw_t(x,lag=6):
 x=np.asarray(x);u=x-x.mean();n=len(x);s=np.dot(u,u)/n
 for k in range(1,min(lag,n-1)+1):s+=2*(1-k/(lag+1))*np.dot(u[k:],u[:-k])/n
 return x.mean()/np.sqrt(max(s,0)/n) if s>0 else np.nan
out=[]
for r in R.itertuples():
 a=np.clip(r.sign_a*D.loc[Lmask,r.factor_a].to_numpy(float)/100,-.2,.2);b=np.clip(r.sign_b*D.loc[Lmask,r.factor_b].to_numpy(float)/100,-.2,.2);x=(a+b)/2;m=np.isfinite(x);x=x[m];dt=dates[m].reset_index(drop=True); yrs=dt.dt.year.to_numpy();early=x[dt<'2023-01-01'];late=x[dt>='2023-01-01'];roll=pd.Series(x).rolling(24).mean().dropna();rm=np.delete(x,np.argmax(x))
 row={'candidate_id':r.candidate_id,'n':len(x),'mean':x.mean(),'nw_t':nw_t(x),'after_100bps':x.mean()-.01,'positive_years':sum(np.mean(x[yrs==y])>0 for y in set(yrs)),'early_mean':early.mean(),'late_mean':late.mean(),'rolling24_positive_share':(roll>0).mean(),'drop_best_after_25bps':rm.mean()-.0025}
 row['passes_capacity_stress']=bool(len(x)==60 and row['nw_t']>2 and row['after_100bps']>0 and row['positive_years']>=4 and row['early_mean']>0 and row['late_mean']>0 and row['rolling24_positive_share']>=.8 and row['drop_best_after_25bps']>0);out.append(row)
Q=pd.DataFrame(out).sort_values(['passes_capacity_stress','after_100bps'],ascending=[False,False]);Q.to_csv(O/'ledgers/V61_OPENAP_CAPACITY_STRESS_LEDGER.csv',index=False)
S={'protocol_sha256':ph,'initial':len(Q),'survivors':int(Q.passes_capacity_stress.sum()),'top':Q.head(25).to_dict('records'),'claim_status':'POST_DISCOVERY_STRESS_NOT_LIVE_PROOF','live_decision_weight':0.0,'capital_permission':'BLOCKED'};(O/'results/V61_OPENAP_CAPACITY_STRESS_RESULTS.json').write_text(json.dumps(S,indent=2,default=str));print(json.dumps({'initial':len(Q),'survivors':S['survivors']},indent=2));print(Q.head(20).to_string(index=False))
