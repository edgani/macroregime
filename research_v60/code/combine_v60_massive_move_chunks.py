from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
chunks=[(0,60),(60,120),(120,180),(180,240),(240,303)]
objs=[json.loads((ROOT/f'results/V60_MASSIVE_MOVE_PRECURSOR_RESULTS_{a}_{b}.json').read_text()) for a,b in chunks]
claims=[r for o in objs for r in o['claims']]
counts={'features':303,'registered_claims':len(claims),'gross_directionally_positive':sum(r['gross_directionally_positive'] for r in claims),'globally_adjusted_diagnostic_survivors':sum(r['globally_adjusted_diagnostic_survivor'] for r in claims),'placebo_claims':sum(r['family']=='placebo' for r in claims),'placebo_survivors':sum(r['family']=='placebo' and r['globally_adjusted_diagnostic_survivor'] for r in claims)}
out={k:v for k,v in objs[0].items() if k not in ['claims','counts','created_at_utc']};out['created_at_utc']=datetime.now(timezone.utc).isoformat();out['counts']=counts;out['claims']=claims
p=ROOT/'results/V60_MASSIVE_MOVE_PRECURSOR_RESULTS.json';p.write_text(json.dumps(out,indent=2,sort_keys=True));
dfs=[pd.read_csv(ROOT/f'results/V60_MASSIVE_MOVE_PRECURSOR_SUMMARY_{a}_{b}.csv') for a,b in chunks];df=pd.concat(dfs,ignore_index=True).sort_values(['globally_adjusted_diagnostic_survivor','gross_directionally_positive','diagnostic_lockbox_lift_mean'],ascending=[False,False,False]);df.to_csv(ROOT/'results/V60_MASSIVE_MOVE_PRECURSOR_SUMMARY.csv',index=False)
# Per target best gross candidates and family diagnostics.
best=[]
for target,g in df[df.family!='placebo'].groupby('target'):
    g=g[(g.validation_lift_mean>0)&(g.diagnostic_lockbox_lift_mean>0)].copy()
    g['min_lift']=g[['validation_lift_mean','diagnostic_lockbox_lift_mean']].min(axis=1)
    best.append(g.sort_values('min_lift',ascending=False).head(20))
bestdf=pd.concat(best,ignore_index=True) if best else pd.DataFrame();bestdf.to_csv(ROOT/'results/V60_MASSIVE_MOVE_BEST_GROSS_CANDIDATES.csv',index=False)
print(json.dumps(counts,indent=2));print('\nBEST BY TARGET');
for target,g in bestdf.groupby('target'):
 print('\n',target);print(g[['feature','family','top_fraction','validation_lift_mean','validation_lift_lb','diagnostic_lockbox_lift_mean','diagnostic_lockbox_lift_lb','validation_precision','validation_base_rate','diagnostic_lockbox_precision','diagnostic_lockbox_base_rate','diagnostic_lockbox_median_lead_days']].head(5).to_string(index=False))
