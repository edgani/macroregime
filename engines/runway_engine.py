
from __future__ import annotations

def remaining_runway(**components):
    valid={k:v for k,v in components.items() if isinstance(v,dict) and v.get('calibrated') is True}
    if not valid:return {'status':'DATA_GATED','reason':'No calibrated valuation/fundamental/market-implied/analog component. Do not extrapolate prior price move.','p25':None,'median':None,'p75':None,'tail':None,'p_over80_priced':None}
    return {'status':'PARTIAL_CALIBRATED_COMPONENTS','components':list(valid),'rule':'Do not combine into a single target unless the combination rule was preregistered and calibrated OOS.'}
