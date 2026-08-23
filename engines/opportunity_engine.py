
from __future__ import annotations
import pandas as pd, numpy as np
OBJECTIVES=['Maximize asymmetric upside','Preserve capital','Hedge crash risk','Exploit short catalyst window','Express long-duration macro view','Relative-value opportunity']
REQUIRED=['mechanism_probability','catalyst_probability','not_fully_priced_probability','net_profitability_probability']

def evaluate_candidate(candidate,objective):
    missing=[x for x in REQUIRED if candidate.get(x) is None or not np.isfinite(candidate.get(x,np.nan))]
    if missing:return {'action':'NO TRADE','rankable':False,'reason':'Missing distinct calibrated components: '+', '.join(missing),'objective':objective}
    # No arbitrary score: require expected payoff inputs and compare directly.
    if candidate.get('expected_net_return') is None:return {'action':'NO TRADE','rankable':False,'reason':'Expected net payoff distribution unavailable','objective':objective}
    return {'action':'RESEARCH_ELIGIBLE','rankable':True,'reason':'All mandatory calibrated components supplied; instrument selection still required','objective':objective}

def rank(candidates,objective):
    rows=[]
    for c in candidates:
        e=evaluate_candidate(c,objective);rows.append({**c,**e})
    d=pd.DataFrame(rows)
    if len(d) and 'expected_net_return' in d:
        d=d.sort_values(['rankable','expected_net_return'],ascending=[False,False],na_position='last')
    return d
