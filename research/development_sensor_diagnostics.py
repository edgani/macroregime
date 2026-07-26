from __future__ import annotations
import json,sys,time,math
from pathlib import Path
from collections import Counter
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.sensors import compute_mqa_benchmarks,compute_momentum_axes,true_ranges
from warroom_v3.hashing import canonical_hash,file_hash

source=Path('/mnt/data/_newzip_extract/warroom_os/research/sp500_panel.parquet')
df=pd.read_parquet(source).sort_values(['Name','date'])
state_counts=Counter(); rows=0; mqa_ready=0; conformal_ready=0; location_ready=0
axis_names=['trend_context','acceleration','release_rank','signed_persistence','path_efficiency','noise_ratio','exhaustion_risk']
axis_values={k:[] for k in axis_names}; failures=[]; start=time.time()
for ticker,g in df.groupby('Name',sort=True):
    try:
        h=g['high'].astype(float).tolist();l=g['low'].astype(float).tolist();c=g['close'].astype(float).tolist()
        mqa=compute_mqa_benchmarks(h,l,c); mom=compute_momentum_axes(c,true_ranges(h,l,c))
        rows+=len(g)
        for x in mqa:
            state_counts[x.volatility_state]+=1
            mqa_ready+=x.atr is not None
            conformal_ready+=x.conformal_lower is not None
            location_ready+=x.prior_range_location is not None
        for x in mom:
            for name in axis_names:
                v=getattr(x,name)
                if v is not None:
                    if not math.isfinite(v): raise ValueError(f'nonfinite {name}')
                    axis_values[name].append(v)
    except Exception as e:
        failures.append({'ticker':ticker,'error':repr(e)})
summary={
 'diagnostic_id':'SPRINT1-SENSOR-DIAGNOSTIC-001',
 'claim_ceiling':'DEVELOPMENT_ENGINEERING_ONLY',
 'source_file':'warroom_os/research/sp500_panel.parquet',
 'source_sha256':file_hash(source),
 'rows':rows,'tickers':int(df['Name'].nunique()),'failures':failures,
 'mqa':{
   'atr_ready_fraction':mqa_ready/rows,'conformal_ready_fraction':conformal_ready/rows,
   'location_ready_fraction':location_ready/rows,'volatility_state_counts':dict(state_counts)
 },
 'momentum_axes':{},'elapsed_seconds':time.time()-start,
 'forbidden_claims':['predictive_edge','probability','entry','stop','target','paper','live']
}
for name,vals in axis_values.items():
    s=pd.Series(vals,dtype=float)
    summary['momentum_axes'][name]={
      'n':len(vals),'ready_fraction':len(vals)/rows,'mean':float(s.mean()),'std':float(s.std(ddof=0)),
      'min':float(s.min()),'p01':float(s.quantile(.01)),'median':float(s.median()),'p99':float(s.quantile(.99)),'max':float(s.max()),
      'unique_rounded_6':int(s.round(6).nunique())
    }
summary['diagnostic_hash']=canonical_hash(summary)
out=ROOT/'artifacts/development_sensor_diagnostics.json';out.write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
print(json.dumps(summary,indent=2,sort_keys=True))
