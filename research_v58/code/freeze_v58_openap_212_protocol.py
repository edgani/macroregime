from __future__ import annotations
import pandas as pd, json, hashlib
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path('/mnt/data/v58_work/research_v58')
SIG=Path('/mnt/data/SignalDoc.csv'); RET=Path('/mnt/data/PredictorLSretWide.csv')
def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
df=pd.read_csv(SIG); df=df[df['Cat.Signal']=='Predictor'].copy().sort_values('Acronym')
claims=[]
for _,r in df.iterrows():
 end=int(r['SampleEndYear']) if pd.notna(r['SampleEndYear']) else None
 yr=int(r['Year']) if pd.notna(r['Year']) else None
 if end is None and yr is None: post=2000
 else: post=max([x for x in [end+1 if end else None,yr+1 if yr else None] if x is not None])
 claims.append({'claim_id':f"OPENAP:{r['Acronym']}",'series':r['Acronym'],'name':r['LongDescription'],'data_category':r['Cat.Data'],'economic_category':r['Cat.Economic'],
  'original_year':yr,'original_sample_end_year':end,'post_start_year':post,'expected_sign':'as_supplied_original_paper_long_short'})
protocol={
 'schema':'warroom.v58.openap_212_postsample_protocol.v1','frozen_at_utc':datetime.now(timezone.utc).isoformat(),
 'purpose':'Test every one of the 212 Open Source Asset Pricing predictor long-short return series, not a hand-picked subset, after both the original sample end and original paper year where available.',
 'source':{
   'signal_doc':{'path':str(SIG),'sha256':sha(SIG),'provenance':'official OpenSourceAP repository'},
   'predictor_returns':{'path':str(RET),'sha256':sha(RET),'provenance':'public GitHub mirror of OpenSourceAP PredictorLSretWide.csv; exact hash pinned; maintained-series reconstruction, not vintage data'}},
 'claims':claims,'claim_count':len(claims),
 'split_rule':'For each signal, begin at January of max(original sample end + 1, paper year + 1). The first 60 nonmissing monthly observations are validation. After a one-observation embargo, all remaining observations are lockbox.',
 'minimum_observations':{'validation':60,'lockbox':60},
 'primary_metric':'mean monthly long-short return with supplied original-paper sign',
 'secondary_metrics':['HAC_t_lag6','annualized_sharpe','max_drawdown','positive_year_fraction','leave_one_year_out_min_mean'],
 'multiplicity':'one-sided Bonferroni 95% simultaneous lower bound over all 212 registered predictors, separately for validation and lockbox',
 'cost_sensitivity_monthly':[0.0,0.0025,0.0050],
 'tiers':{
  'ROBUST_25BPS_POSTSAMPLE':'positive validation and lockbox; simultaneous lower bound >0 in both after 25 bps/month; leave-one-year-out mean >0 in both',
  'ROBUST_GROSS_POSTSAMPLE':'same gross gate but not 25 bps/month',
  'DIRECTIONALLY_PERSISTENT_ONLY':'positive point mean in both but simultaneous gate not met',
  'FAILED_OR_UNIDENTIFIABLE':'negative split or insufficient post-sample observations'},
 'discovery_policy':'No parameters are optimized. All 212 series are tested exactly as supplied. No survivors may be dropped from trial accounting.',
 'claim_limit':'Post-original-sample persistence in maintained academic portfolio returns. Not a point-in-time stock-level replication, executable net alpha, current winner selection, or capital permission.',
 'no_live_promotion':True,'live_decision_weight':0.0,'capital_permission':'BLOCKED',
 'forbidden':['select only famous anomalies','use in-sample t-stat as proof','change post-start rule after results','drop failed signals','ignore 212-way multiplicity','treat maintained data as historical vintage']}
text=json.dumps(protocol,indent=2,sort_keys=True)
out=ROOT/'protocols/V58_OPENAP_212_POSTSAMPLE_PROTOCOL_FROZEN.json';out.write_text(text)
(ROOT/'protocols/V58_OPENAP_212_POSTSAMPLE_PROTOCOL_FROZEN.sha256.txt').write_text(hashlib.sha256(text.encode()).hexdigest()+'  '+out.name+'\n')
print(len(claims),hashlib.sha256(text.encode()).hexdigest())
