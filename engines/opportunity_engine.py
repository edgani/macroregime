
from __future__ import annotations
import numpy as np,pandas as pd
OBJECTIVES=['Max asymmetric upside','Preserve capital','Crash hedge','Short catalyst window','Long-duration macro view','Relative value']
REQUIRED=['mechanism_probability','catalyst_probability','not_fully_priced_probability','net_profitability_probability']
def evaluate_candidate(c,objective):
    missing=[x for x in REQUIRED if c.get(x) is None or not np.isfinite(c.get(x,np.nan))]
    if missing:return {'action':'NO TRADE','rankable':False,'reason':'Missing distinct calibrated components: '+', '.join(missing),'objective':objective}
    if c.get('expected_net_return') is None:return {'action':'NO TRADE','rankable':False,'reason':'Expected net payoff distribution unavailable','objective':objective}
    return {'action':'RESEARCH_ELIGIBLE','rankable':True,'reason':'All mandatory calibrated components supplied; choose the cleanest instrument expression next','objective':objective}
def rank(candidates,objective):
    rows=[{**c,**evaluate_candidate(c,objective)} for c in candidates];d=pd.DataFrame(rows)
    if len(d) and 'expected_net_return' in d:d=d.sort_values(['rankable','expected_net_return'],ascending=[False,False],na_position='last')
    return d
