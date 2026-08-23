
from __future__ import annotations
import numpy as np,pandas as pd

def _status(evidence):
    vals=[v for v in evidence if v is not None]
    if not vals:return 'DATA_GATED'
    if any(v=='TRIGGER' for v in vals):return 'ACTIVE / INVESTIGATE'
    if any(v=='WATCH' for v in vals):return 'WATCH'
    return 'NO ACTIVE EVIDENCE IN LOADED SUBSET'

def crash_matrix(state):
    c=state.get('Credit/Funding',{});g=state.get('Growth',{});v=state.get('Volatility',{});r=state.get('Policy/Rates',{})
    hy=c.get('HYOAS_13w_delta',np.nan);nfci=c.get('NFCI',np.nan);fund=c.get('SOFR_minus_IORB',np.nan);vp=v.get('VIX_5y_percentile',np.nan);claims=g.get('Claims_13w_pct',np.nan);realp=r.get('Real10Y_percentile',np.nan)
    frag=[]
    if np.isfinite(realp):frag.append('WATCH' if realp>.8 else 'CLEAR')
    early=[]
    if np.isfinite(hy):early.append('WATCH' if hy>.5 else 'CLEAR')
    if np.isfinite(nfci):early.append('WATCH' if nfci>0 else 'CLEAR')
    if np.isfinite(claims):early.append('WATCH' if claims>.10 else 'CLEAR')
    acute=[]
    if np.isfinite(fund):acute.append('TRIGGER' if fund>.25 else ('WATCH' if fund>.10 else 'CLEAR'))
    if np.isfinite(vp):acute.append('WATCH' if vp>.95 else 'CLEAR')
    recovery=[]
    if np.isfinite(hy) and np.isfinite(nfci):recovery.append('WATCH' if hy<0 and nfci<0 else 'CLEAR')
    return pd.DataFrame([
    {'phase':'FRAGILITY','status':_status(frag),'observable':'Refinancing vulnerability, leverage, valuation severity, high real funding hurdle','current_evidence':f'Real10Y pct={realp:.1%}' if np.isfinite(realp) else 'Leverage/refinancing PIT data incomplete','decision_use':'Risk budget / vulnerability only; never crash timing'},
    {'phase':'EARLY WARNING','status':_status(early),'observable':'HY/EBP velocity, lending/financial conditions, labor deterioration','current_evidence':f'HY Δ13w={hy:.3f}; NFCI={nfci:.3f}; claims Δ13w={claims:.1%}' if all(np.isfinite(x) for x in [hy,nfci,claims]) else 'Partial data','decision_use':'Distinguish ordinary repricing from broad deterioration'},
    {'phase':'ACUTE TRIGGER','status':_status(acute),'observable':'Repo/funding dislocation, Treasury liquidity, basis stress, forced deleveraging','current_evidence':f'SOFR-IORB={fund:.3f}; VIX pct={vp:.1%}' if np.isfinite(fund) and np.isfinite(vp) else 'Partial; basis/Treasury depth data gated','decision_use':'Mechanism capable of forcing rapid repricing'},
    {'phase':'SEVERITY','status':'DATA_GATED','observable':'Leverage, maturity wall, balance-sheet vulnerability, market depth','current_evidence':'Historical leverage/refinancing database incomplete','decision_use':'Conditional loss severity, not trigger probability'},
    {'phase':'RECOVERY / REENTRY','status':_status(recovery),'observable':'Credit/funding normalization and liquidation pressure clearing','current_evidence':f'HY Δ13w={hy:.3f}; NFCI={nfci:.3f}' if np.isfinite(hy) and np.isfinite(nfci) else 'Partial data','decision_use':'Reentry hypothesis requires independent validation'},
    ])

def crash_conclusion(state):
    m=crash_matrix(state);active=list(m.loc[m.status.str.contains('ACTIVE',na=False),'phase']);watch=list(m.loc[m.status.eq('WATCH'),'phase'])
    return {'crash_probability':None,'probability_status':'NO CALIBRATED CRASH PROBABILITY','active_phases':active,'watch_phases':watch,'ordinary_correction_vs_systemic':'SYSTEMIC cannot be asserted without funding/credit acute-trigger evidence','reason':'Phases are separated; no arbitrary composite score is used.'}
