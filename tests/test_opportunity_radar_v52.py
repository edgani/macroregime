import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from engines.projection_engine import opportunity_radar

rng=np.random.default_rng(7)
idx=pd.date_range('2000-01-31', periods=300, freq='ME')
# Build monthly-compatible features with required names. ICSA must remain positive.
fred={
'T10Y3M':pd.Series(rng.normal(0,1,300).cumsum()/10,index=idx),
'BAMLH0A0HYM2':pd.Series(3+np.abs(rng.normal(0,1,300)),index=idx),
'DFII10':pd.Series(rng.normal(1.5,.3,300),index=idx),
'THREEFYTP10':pd.Series(rng.normal(.3,.2,300),index=idx),
'NFCI':pd.Series(rng.normal(0,.5,300),index=idx),
'ICSA':pd.Series(200000*np.exp(rng.normal(0,.05,300)),index=idx),
'T5YIE':pd.Series(rng.normal(2.2,.25,300),index=idx),
}
prices={}
for i,t in enumerate(['A','B','C']):
    rets=rng.normal(.006+i*.001,.04+i*.005,300)
    prices[t]=pd.Series(100*np.cumprod(1+rets),index=idx)

d=opportunity_radar(fred,prices,['A','B','C'],'3M',20)
assert len(d)>=2
assert 'pareto_candidate' in d.columns
assert d['pareto_candidate'].any()
print('OPPORTUNITY_RADAR_V52_PASS', d[['instrument','median','p_loss10','pareto_candidate']].to_dict('records'))
