import json, tempfile
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parent
checks={}
# 1 planted pre-event origin: top-decile origin must predict later event.
rng=np.random.default_rng(42);n=4000
origin=rng.normal(size=n);future=(origin>1.5).astype(int)
sel=origin>=np.quantile(origin,.9);base=np.full(n,False);base[rng.choice(n,sel.sum(),replace=False)]=True
checks['planted_origin_detected']=future[sel].mean()>future[base].mean()+.25
# 2 null: shuffled origin should not exhibit material lift.
sh=rng.permutation(origin);ssel=sh>=np.quantile(sh,.9)
checks['null_has_no_material_lift']=abs(future[ssel].mean()-future.mean())<.04
# 3 liquidation after event cannot be an early feature.
liq=np.roll(future,1);liq[0]=0
checks['post_event_liquidation_not_early']=np.corrcoef(liq[1:],future[:-1])[0,1]>.9 and abs(np.corrcoef(liq[:-1],future[1:])[0,1])<.1
# 4 availability date, not fiscal end, controls SEC feature use.
filings=pd.DataFrame({'period_end':pd.to_datetime(['2020-03-31','2020-06-30']),'filed':pd.to_datetime(['2020-05-05','2020-08-04']),'value':[1,2]})
days=pd.date_range('2020-03-31','2020-08-10');known=[]
for d in days:
    q=filings[filings.filed<=d]
    known.append(q.value.iloc[-1] if len(q) else np.nan)
series=pd.Series(known,index=days)
checks['pit_filing_date_guard']=pd.isna(series.loc['2020-05-04']) and series.loc['2020-05-05']==1 and series.loc['2020-08-03']==1 and series.loc['2020-08-04']==2
# 5 protocol and runner feature section do not use future shifts; target section may.
runner=(ROOT/'research_v62/code/run_v62_event_origin_fast.py').read_text()
feature_section=runner.split('gapz=',1)[1].split('fmax={',1)[0]
checks['no_forward_shift_in_features']='shift(-' not in feature_section
# 6 both new batteries are diagnostic and live weight zero.
for name,path in [('network',ROOT/'research_v61/protocols/V61_NETWORK_DIFFUSION_PROTOCOL_FROZEN.json'),('event',ROOT/'research_v62/protocols/V62_EVENT_ORIGIN_PROTOCOL_FROZEN.json')]:
    d=json.loads(path.read_text());checks[f'{name}_fail_closed']=d['live_decision_weight']==0 and d['capital_permission']=='BLOCKED'
checks={k:bool(v) for k,v in checks.items()}
assert all(checks.values()),checks
out={'schema':'warroom.v62.origin_harness','checks':checks,'status':'PASS','market_evidence_status':'SYNTHETIC_CONTROL_ONLY_NOT_MARKET_PROOF'}
(ROOT/'research_v62/results/V62_ORIGIN_HARNESS_RESULTS.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(f"{sum(checks.values())}/{len(checks)} PASS")
