import sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from engines.projection_engine import walkforward_calibration, analog_distribution, FEATURES
rng=np.random.default_rng(7)
dates=pd.date_range('2000-01-31',periods=300,freq='ME')
# Build daily-ish/monthly features accepted by resample.
fred={}
for j,sid in enumerate(FEATURES):
    vals=np.cumsum(rng.normal(0,.1,300))+j
    if sid=='ICSA':vals=np.exp(vals/10+10)
    fred[sid]=pd.Series(vals,index=dates)
# price has a deterministic relationship to a lagged feature + noise, just for code-path testing
ret=.01-.01*np.tanh(pd.Series(fred['BAMLH0A0HYM2'],index=dates).diff().fillna(0).values)+rng.normal(0,.03,300)
price=pd.Series(100*np.cumprod(1+ret),index=dates)
stats,analogs,meta=analog_distribution(fred,price,12)
assert len(stats)==4 and len(analogs)>=8
cal,cm=walkforward_calibration(fred,price,k=12,min_train=60,step=6)
assert len(cal)>=1
assert cm['status']=='TEMPORAL_SAFE_BUT_REVISION_UNSAFE'
assert (cal['n_oos']>0).all()
print('PROJECTION_TEMPORAL_TEST_PASS',cal[['horizon','n_oos']].to_dict('records'))
