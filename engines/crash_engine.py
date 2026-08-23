
from __future__ import annotations
import numpy as np, pandas as pd

def crash_matrix(state):
    c=state.get('Credit/Funding',{}); p=state.get('percentiles',{}); v=state.get('Volatility',{})
    return pd.DataFrame([
      {'phase':'FRAGILITY','observable':'Private/systemic leverage, refinancing vulnerability, valuations','current_evidence':'DATA_GATED','interpretation':'Vulnerability only; not crash timing'},
      {'phase':'EARLY WARNING','observable':'HY/EBP velocity, lending/financial conditions','current_evidence':f"HY Δ13w={c.get('HYOAS_13w_delta',np.nan):.3f}" if np.isfinite(c.get('HYOAS_13w_delta',np.nan)) else 'NO DATA','interpretation':'Deterioration; needs funding/real-economy confirmation'},
      {'phase':'ACUTE TRIGGER','observable':'Repo/basis/Treasury liquidity + forced deleveraging','current_evidence':'DATA_GATED','interpretation':'Mechanism capable of rapid repricing'},
      {'phase':'SEVERITY','observable':'Leverage + balance-sheet vulnerability + market depth','current_evidence':'DATA_GATED','interpretation':'Conditional damage, not trigger probability'},
      {'phase':'RECOVERY / REENTRY','observable':'Funding/credit normalization + liquidation pressure clearing','current_evidence':'DATA_GATED','interpretation':'Reentry condition must be validated separately'},
    ])

def crash_conclusion(state):
    return {'crash_probability':None,'status':'NO CALIBRATED CRASH PROBABILITY','reason':'Funding, leverage, vintage-safe credit and calibrated phase-transition data are incomplete. Ordinary correction and systemic event are not collapsed into one score.'}
