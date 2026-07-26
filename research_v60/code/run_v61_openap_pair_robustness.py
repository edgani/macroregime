from __future__ import annotations
import json, hashlib, math
from pathlib import Path
import numpy as np
import pandas as pd

BASE=Path('/mnt/data/warroom_v60_work/src'); OUT=BASE/'research_v60'
for d in ['protocols','results','ledgers']: (OUT/d).mkdir(parents=True,exist_ok=True)
P={
 'study_id':'V61_OPENAP_PAIR_ROBUSTNESS_CHALLENGE',
 'parent':'V60_OPENAP_ALL_PAIR_SIGN_COMBINATIONS',
 'purpose':'Determine whether the 572 gross pair candidates add robust diversification rather than inherit one constituent or one extreme month.',
 'registration_note':'Follow-up robustness protocol frozen after V60 candidate discovery; therefore not an untouched lockbox and cannot confer proof.',
 'candidate_set':'all V60 passes_full_gate candidates, with no discretionary selection',
 'windows':{'validation':'2010-01 to 2019-12','falsification':'2020-01 to 2024-12'},
 'stress_tests':[
  'complete 120 and 60 monthly observations','raw and validation-quantile winsorized Newey-West t > 2 in falsification',
  'mean remains positive after 25, 50, and 100 bps monthly stresses','positive in at least 4 of 5 falsification years',
  'positive mean in both 2020-2022 and 2023-2024','positive in >=80% of rolling 24-month falsification windows',
  'mean after deleting largest positive month remains positive after 25 bps','pair Newey-West t exceeds both signed constituents in validation and falsification',
  'pair max drawdown is no worse than best signed constituent in falsification','absolute constituent correlation <=0.80 in falsification'
 ],
 'claim_limit':'Maintained portfolio returns only; no stock-level point-in-time selection, capacity, survivorship-safe reconstruction, or prospective proof.',
 'live_decision_weight':0.0,'capital_permission':'BLOCKED'
}
pp=OUT/'protocols/V61_OPENAP_PAIR_ROBUSTNESS_PROTOCOL_FROZEN.json';pp.write_text(json.dumps(P,indent=2,sort_keys=True));ph=hashlib.sha256(pp.read_bytes()).hexdigest();(OUT/'protocols/V61_OPENAP_PAIR_ROBUSTNESS_PROTOCOL_FROZEN.sha256').write_text(ph+'  '+pp.name+'\n')
D=pd.read_csv(BASE/'research_v58/data/PredictorLSretWide.csv');D.date=pd.to_datetime(D.date); cols=[c for c in D if c!='date']; idx={c:i for i,c in enumerate(cols)}; X=D[cols].to_numpy(float)/100
Vmask=(D.date>='2010-01-01')&(D.date<='2019-12-31'); Lmask=(D.date>='2020-01-01')&(D.date<='2024-12-31'); V=X[Vmask];L=X[Lmask]; Ldates=D.loc[Lmask,'date'].reset_index(drop=True)
G=pd.read_csv(OUT/'ledgers/V60_OPENAP_PAIR_GLOBAL_LEDGER.csv');G=G[G.passes_full_gate.astype(str).str.lower().isin(['true','1'])].copy(); assert len(G)==572,len(G)
def nw_t(x,lag=6):
 x=np.asarray(x,float);x=x[np.isfinite(x)];n=len(x)
 if n<12:return np.nan
 u=x-x.mean();s=np.dot(u,u)/n
 for k in range(1,min(lag,n-1)+1):s+=2*(1-k/(lag+1))*np.dot(u[k:],u[:-k])/n
 se=math.sqrt(max(s,0)/n);return x.mean()/se if se>0 else np.nan
def maxdd(x):
 x=np.nan_to_num(x,nan=0.0); wealth=np.cumprod(1+x); peak=np.maximum.accumulate(wealth); return float(np.min(wealth/peak-1))
def roll_positive_share(x,w=24):
 s=pd.Series(x); r=s.rolling(w,min_periods=w).mean().dropna(); return float((r>0).mean()) if len(r) else np.nan
rec=[]
for r in G.itertuples(index=False):
 ia,ib=idx[r.factor_a],idx[r.factor_b]; va=r.sign_a*V[:,ia];vb=r.sign_b*V[:,ib];la=r.sign_a*L[:,ia];lb=r.sign_b*L[:,ib]
 pairv=(va+vb)/2; pairl=(la+lb)/2; okv=np.isfinite(pairv)&np.isfinite(va)&np.isfinite(vb);okl=np.isfinite(pairl)&np.isfinite(la)&np.isfinite(lb)
 pv,pL=pairv[okv],pairl[okl]; av,bv=va[okv],vb[okv];aL,bL=la[okl],lb[okl]; dates=Ldates.loc[np.flatnonzero(okl)].reset_index(drop=True)
 if len(pv):
  lo,hi=np.quantile(pv,[.01,.99]); wL=np.clip(pL,lo,hi)
 else: lo=hi=np.nan;wL=pL
 years=dates.dt.year.to_numpy(); yrmeans={int(y):float(np.mean(pL[years==y])) for y in sorted(set(years))}
 early=float(np.mean(pL[dates<'2023-01-01'])) if np.any(dates<'2023-01-01') else np.nan; late=float(np.mean(pL[dates>='2023-01-01'])) if np.any(dates>='2023-01-01') else np.nan
 rm=np.delete(pL,int(np.nanargmax(pL))) if len(pL)>1 else np.array([])
 tv,tl=nw_t(pv),nw_t(pL); tav,tbv=nw_t(av),nw_t(bv);taL,tbL=nw_t(aL),nw_t(bL)
 corr=float(np.corrcoef(aL,bL)[0,1]) if len(aL)>2 and np.std(aL)>0 and np.std(bL)>0 else np.nan
 mdd_pair=maxdd(pL);mdd_a=maxdd(aL);mdd_b=maxdd(bL); best_const_mdd=max(mdd_a,mdd_b)
 row={
  'candidate_id':r.candidate_id,'factor_a':r.factor_a,'sign_a':int(r.sign_a),'factor_b':r.factor_b,'sign_b':int(r.sign_b),'n_validation':len(pv),'n_falsification':len(pL),
  'validation_mean':float(np.mean(pv)),'validation_nw_t':tv,'falsification_mean':float(np.mean(pL)),'falsification_nw_t':tl,'winsorized_falsification_mean':float(np.mean(wL)),'winsorized_falsification_nw_t':nw_t(wL),
  'after_25bps':float(np.mean(pL)-.0025),'after_50bps':float(np.mean(pL)-.005),'after_100bps':float(np.mean(pL)-.01),
  'positive_years':sum(v>0 for v in yrmeans.values()),'early_2020_2022_mean':early,'late_2023_2024_mean':late,'rolling24_positive_share':roll_positive_share(pL),
  'drop_best_month_after_25bps':float(np.mean(rm)-.0025) if len(rm) else np.nan,'constituent_corr_falsification':corr,
  'pair_t_increment_validation':float(tv-max(tav,tbv)) if np.isfinite(tv) else np.nan,'pair_t_increment_falsification':float(tl-max(taL,tbL)) if np.isfinite(tl) else np.nan,
  'pair_max_drawdown':mdd_pair,'best_constituent_max_drawdown':best_const_mdd,'drawdown_increment':mdd_pair-best_const_mdd,
 }
 row['passes_strict_robustness']=bool(len(pv)==120 and len(pL)==60 and tl>2 and row['winsorized_falsification_nw_t']>2 and row['after_100bps']>0 and row['positive_years']>=4 and early>0 and late>0 and row['rolling24_positive_share']>=.8 and row['drop_best_month_after_25bps']>0 and row['pair_t_increment_validation']>0 and row['pair_t_increment_falsification']>0 and np.isfinite(corr) and abs(corr)<=.8 and row['drawdown_increment']>=0)
 rec.append(row)
R=pd.DataFrame(rec).sort_values(['passes_strict_robustness','after_100bps','pair_t_increment_falsification'],ascending=[False,False,False]);R.to_csv(OUT/'ledgers/V61_OPENAP_PAIR_ROBUSTNESS_LEDGER.csv',index=False)
# gate attrition
checks={
 'initial_candidates':len(R),'complete_windows':int(((R.n_validation==120)&(R.n_falsification==60)).sum()),'raw_falsification_nw_t_gt2':int((R.falsification_nw_t>2).sum()),'winsorized_nw_t_gt2':int((R.winsorized_falsification_nw_t>2).sum()),'positive_after_100bps':int((R.after_100bps>0).sum()),'positive_4_of_5_years':int((R.positive_years>=4).sum()),'both_subperiods_positive':int(((R.early_2020_2022_mean>0)&(R.late_2023_2024_mean>0)).sum()),'rolling24_positive_80pct':int((R.rolling24_positive_share>=.8).sum()),'survives_drop_best_month':int((R.drop_best_month_after_25bps>0).sum()),'adds_t_both_windows':int(((R.pair_t_increment_validation>0)&(R.pair_t_increment_falsification>0)).sum()),'drawdown_not_worse':int((R.drawdown_increment>=0).sum()),'corr_abs_le_080':int((R.constituent_corr_falsification.abs()<=.8).sum()),'strict_survivors':int(R.passes_strict_robustness.sum())}
out={'study_id':P['study_id'],'protocol_sha256':ph,'gate_attrition':checks,'top_25':R.head(25).to_dict('records'),'claim_status':'ROBUSTNESS_CHALLENGE_NOT_UNTOUCHED_NOT_LIVE_PROOF','live_decision_weight':0.0,'capital_permission':'BLOCKED'};(OUT/'results/V61_OPENAP_PAIR_ROBUSTNESS_RESULTS.json').write_text(json.dumps(out,indent=2,default=str));print(json.dumps(checks,indent=2));print(R.head(15)[['candidate_id','after_100bps','falsification_nw_t','winsorized_falsification_nw_t','pair_t_increment_validation','pair_t_increment_falsification','drawdown_increment','passes_strict_robustness']].to_string(index=False))
