from __future__ import annotations
import json, hashlib, time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import average_precision_score, roc_auc_score

BASE=Path('/mnt/data/warroom_v60_work/src')
OUT=BASE/'research_v60'
for d in ['protocols','results','ledgers','code']: (OUT/d).mkdir(parents=True,exist_ok=True)

P={
 'study_id':'V60_ALTERNATE_EXTREME_TARGETS_PRICE_VOLUME',
 'parent_protocol':'V60_MASSIVE_MOVE_PROTOCOL_FROZEN.json',
 'purpose':'Test the predeclared alternate targets using the exact frozen feature ranks and candidate grid; no new features or candidate selection.',
 'inputs':['data/V60_MONTHLY_FEATURE_RANKS.npz','data/V60_MONTHLY_OUTCOMES.csv','protocols/V60_CANDIDATE_GRID_FROZEN.csv'],
 'targets':{
   'relative_winner':{'column':'target_rel_up','return_column':'fwd_max_ret_63','better_return':'higher','description':'top 5% future maximum return in each monthly cross-section over next 63 trading days'},
   'absolute_loser':{'column':'target_abs_down','return_column':'fwd_min_ret_63','better_return':'lower','description':'future minimum return <= -20% over next 63 trading days'},
 },
 'splits':{'validation':['2015-02','2016-01'],'diagnostic_lockbox':['2016-02','2017-11']},
 'baseline_candidates':['mom_63:+1','mom_63:-1','mom_126:+1','mom_126:-1','volume_ratio_20_63:+1','volume_ratio_20_63:-1','rel_mom_63:+1','rel_mom_63:-1'],
 'candidate_universe':'exact 34,322 frozen candidates from V60_CANDIDATE_GRID_FROZEN.csv',
 'primary_test':'monthly top-10 precision improvement versus best declared validation baseline; one-sided t-test; BH-FDR globally per target over all 34,322 trials',
 'lockbox_open_rule':'only globally corrected validation survivors may open diagnostic lockbox',
 'promotion_limit':'diagnostic only; reused fixed universe, short era, survivorship concerns, OHLCV only',
 'live_decision_weight':0.0,'capital_permission':'BLOCKED'
}
pp=OUT/'protocols/V60_ALTERNATE_TARGETS_PROTOCOL_FROZEN.json'; pp.write_text(json.dumps(P,indent=2,sort_keys=True)); ph=hashlib.sha256(pp.read_bytes()).hexdigest(); (OUT/'protocols/V60_ALTERNATE_TARGETS_PROTOCOL_FROZEN.sha256').write_text(ph+'  '+pp.name+'\n')

z=np.load(OUT/'data/V60_MONTHLY_FEATURE_RANKS.npz',allow_pickle=True)
R=z['ranks'].astype(np.float32); fn=list(z['feature_names']); fi={f:i for i,f in enumerate(fn)}
M=pd.read_csv(OUT/'data/V60_MONTHLY_OUTCOMES.csv'); M['month']=pd.PeriodIndex(M['month'],freq='M')
G=pd.read_csv(OUT/'protocols/V60_CANDIDATE_GRID_FROZEN.csv').fillna('')
assert len(G)==34322 and len(M)==len(R)

splits={k:(pd.Period(v[0],'M'),pd.Period(v[1],'M')) for k,v in P['splits'].items()}
def score_row(r):
 a=R[:,fi[r.f1]]; s=a if int(r.s1)==1 else 1-a
 if isinstance(r.f2,str) and r.f2:
  b=R[:,fi[r.f2]]; s=(s+(b if int(r.s2)==1 else 1-b))/2
 return s

def score_feature(f,sign):
 a=R[:,fi[f]]; return a if sign==1 else 1-a

def split_data(target,retcol,start,end):
 mask=((M.month>=start)&(M.month<=end)&M[target].notna()&M[retcol].notna()).to_numpy()
 pos=np.flatnonzero(mask); mons=M.loc[mask,'month'].astype(str).to_numpy(); ug=pd.unique(mons)
 groups=[np.flatnonzero(mons==m) for m in ug]
 return pos,groups,M.loc[mask,target].to_numpy(np.int8),M.loc[mask,retcol].to_numpy(float),ug

def monthly_metrics(sc,y,ret,groups,lower_is_better=False):
 precision=[]; recall=[]; meanret=[]
 for ix in groups:
  k=min(10,len(ix)); top=ix[np.argpartition(sc[ix],-k)[-k:]]
  hits=y[top]; ev=y[ix].sum(); precision.append(hits.mean()); recall.append(hits.sum()/ev if ev else np.nan); meanret.append(np.nanmean(ret[top]))
 return np.asarray(precision,float),np.asarray(recall,float),np.asarray(meanret,float)

def bh(p):
 p=np.asarray(p,float); order=np.argsort(p); q=np.empty_like(p); prev=1.0; m=len(p)
 for rank,ix in reversed(list(enumerate(order,start=1))):
  val=min(prev,p[ix]*m/rank); q[ix]=val; prev=val
 return q

summaries={}
for target_name,spec in P['targets'].items():
 target=spec['column']; retcol=spec['return_column']; lower=spec['better_return']=='lower'
 V=split_data(target,retcol,*splits['validation']); L=split_data(target,retcol,*splits['diagnostic_lockbox'])
 vpos,vgroups,vy,vret,vmonths=V; lpos,lgroups,ly,lret,lmonths=L
 # select best declared baseline by validation AP
 bases={}
 for b in P['baseline_candidates']:
  f,sg=b.rsplit(':',1); sg=int(sg); sc=score_feature(f,sg)
  bases[b]={'val_ap':average_precision_score(vy,sc[vpos]),'val_auc':roc_auc_score(vy,sc[vpos])}
 best=max(bases,key=lambda x:bases[x]['val_ap']); bf,bsg=best.rsplit(':',1); bsc=score_feature(bf,int(bsg))
 bvp,bvr,bvret=monthly_metrics(bsc[vpos],vy,vret,vgroups,lower); blp,blr,blret=monthly_metrics(bsc[lpos],ly,lret,lgroups,lower)
 base={'candidate':best,'validation':{'ap':float(average_precision_score(vy,bsc[vpos])),'auc':float(roc_auc_score(vy,bsc[vpos])),'precision10':float(np.nanmean(bvp)),'recall10':float(np.nanmean(bvr)),'mean_selected_return':float(np.nanmean(bvret))},'diagnostic_lockbox':{'ap':float(average_precision_score(ly,bsc[lpos])),'auc':float(roc_auc_score(ly,bsc[lpos])),'precision10':float(np.nanmean(blp)),'recall10':float(np.nanmean(blr)),'mean_selected_return':float(np.nanmean(blret))}}
 rec=[]; st=time.time()
 for n,r in enumerate(G.itertuples(index=False),1):
  sc=score_row(r); vp,vr,vmr=monthly_metrics(sc[vpos],vy,vret,vgroups,lower); diff=vp-bvp; finite=np.isfinite(diff)
  pval=float(stats.ttest_1samp(diff[finite],0,alternative='greater').pvalue) if finite.sum()>=8 and np.nanstd(diff[finite],ddof=1)>0 else 1.0
  rec.append({'candidate_id':r.candidate_id,'kind':r.kind,'f1':r.f1,'s1':int(r.s1),'f2':r.f2,'s2':int(r.s2) if r.f2 else 0,'family1':r.family1,'family2':r.family2,
              'validation_precision10':float(np.nanmean(vp)),'validation_recall10':float(np.nanmean(vr)),'validation_mean_selected_return':float(np.nanmean(vmr)),'validation_precision_improvement':float(np.nanmean(diff)),'validation_p':pval})
  if n%10000==0: print(target_name,n,'elapsed',round(time.time()-st,1),flush=True)
 D=pd.DataFrame(rec); D['validation_q_global']=bh(D.validation_p.fillna(1)); D['validation_screen_pass']=(D.validation_q_global<.05)&(D.validation_precision_improvement>0)
 for c in ['validation_ap','validation_ap_improvement','lockbox_ap','lockbox_ap_improvement','lockbox_precision10','lockbox_precision_improvement','lockbox_mean_selected_return','lockbox_return_improvement']:D[c]=np.nan
 selected=np.flatnonzero(D.validation_screen_pass.to_numpy())
 for j in selected:
  r=G.iloc[j]; sc=score_row(r); lp,lr,lmr=monthly_metrics(sc[lpos],ly,lret,lgroups,lower)
  vap=float(average_precision_score(vy,sc[vpos])); lap=float(average_precision_score(ly,sc[lpos])); lmean=float(np.nanmean(lmr))
  D.at[j,'validation_ap']=vap;D.at[j,'validation_ap_improvement']=vap-base['validation']['ap'];D.at[j,'lockbox_ap']=lap;D.at[j,'lockbox_ap_improvement']=lap-base['diagnostic_lockbox']['ap'];D.at[j,'lockbox_precision10']=np.nanmean(lp);D.at[j,'lockbox_precision_improvement']=np.nanmean(lp)-base['diagnostic_lockbox']['precision10'];D.at[j,'lockbox_mean_selected_return']=lmean
  D.at[j,'lockbox_return_improvement']=(base['diagnostic_lockbox']['mean_selected_return']-lmean) if lower else (lmean-base['diagnostic_lockbox']['mean_selected_return'])
 D['passes_full_gate']=D.validation_screen_pass&(D.validation_ap_improvement>0)&(D.lockbox_ap_improvement>0)&(D.lockbox_precision_improvement>0)&(D.lockbox_return_improvement>0)
 D=D.sort_values(['passes_full_gate','validation_screen_pass','validation_q_global','validation_precision_improvement'],ascending=[False,False,True,False])
 lp=OUT/f'ledgers/V60_{target_name.upper()}_GLOBAL_TRIAL_LEDGER.csv'; D.to_csv(lp,index=False)
 summaries[target_name]={'registered':len(D),'validation_fdr_survivors':int((D.validation_q_global<.05).sum()),'validation_screen_survivors':int(D.validation_screen_pass.sum()),'full_gate_survivors':int(D.passes_full_gate.sum()),'best_declared_baseline':base,'top_20':D.head(20).to_dict('records')}
 print(target_name,{k:v for k,v in summaries[target_name].items() if k!='top_20'},flush=True)

out={'study_id':P['study_id'],'protocol_sha256':ph,'candidate_grid_sha256':hashlib.sha256((OUT/'protocols/V60_CANDIDATE_GRID_FROZEN.csv').read_bytes()).hexdigest(),'results':summaries,'total_claims_tested':34322*len(P['targets']),'claim_status':'DIAGNOSTIC_ONLY_NOT_LIVE_PROOF','live_decision_weight':0.0,'capital_permission':'BLOCKED'}
(OUT/'results/V60_ALTERNATE_TARGETS_RESULTS.json').write_text(json.dumps(out,indent=2,default=str))
print(json.dumps({k:{x:y for x,y in v.items() if x not in ['top_20','best_declared_baseline']} for k,v in summaries.items()},indent=2))
