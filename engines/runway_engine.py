
from __future__ import annotations
import numpy as np

def remaining_runway(valuation_distribution=None,market_implied_distribution=None,analog_distribution=None,pricing_probability=None):
    calibrated=[]
    for name,x in [('valuation',valuation_distribution),('market_implied',market_implied_distribution),('analog',analog_distribution)]:
        if isinstance(x,dict) and x.get('calibrated') is True:calibrated.append((name,x))
    if not calibrated:
        return {'status':'DATA_GATED','reason':'No calibrated component is available. Historical analog quantiles may be shown as context but cannot be called RemainingRunway.',
                'p25':None,'median':None,'p75':None,'tail':None,'p_over80_priced':pricing_probability}
    return {'status':'CALIBRATED_COMPONENTS_AVAILABLE','components':[x[0] for x in calibrated],'note':'Combine only under a preregistered calibration rule.'}
