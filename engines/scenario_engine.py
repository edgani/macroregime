
from __future__ import annotations
from pathlib import Path
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parents[1]

def catalog():return pd.read_csv(HERE/'research'/'scenario_catalog.csv')
def _finite(x):
    try:return np.isfinite(float(x))
    except:return False

def live_evidence(state):
    g=state.get('Growth',{});i=state.get('Inflation',{});r=state.get('Policy/Rates',{});c=state.get('Credit/Funding',{});v=state.get('Volatility',{});x=state.get('FX',{});k=state.get('Crypto Native',{})
    defs=[
    ('BASE','Growth resilient / inflation cooling',[
      ('Broad activity non-negative',_finite(g.get('CFNAI')) and g['CFNAI']>=0),('Short-run core inflation <3%',_finite(i.get('Core_3m_ann')) and i['Core_3m_ann']<.03),('HY spreads not accelerating >75bp/13w',_finite(c.get('HYOAS_13w_delta')) and c['HYOAS_13w_delta']<=.75)],
     [('Credit acceleration contradicts base',_finite(c.get('HYOAS_13w_delta')) and c['HYOAS_13w_delta']>.75)]),
    ('COMPETING','Sticky inflation / long-rate pressure',[
      ('Short-run core inflation >=3%',_finite(i.get('Core_3m_ann')) and i['Core_3m_ann']>=.03),('Real yield rising over 13w',_finite(r.get('Real10Y_13w_delta')) and r['Real10Y_13w_delta']>0),('Term premium rising over 13w',_finite(r.get('TermPremium_13w_delta')) and r['TermPremium_13w_delta']>0)],
     [('Inflation cooling and real yields falling',_finite(i.get('Core_3m_ann')) and i['Core_3m_ann']<.025 and _finite(r.get('Real10Y_13w_delta')) and r['Real10Y_13w_delta']<0)]),
    ('TAIL','Growth slowdown + credit/funding stress',[
      ('Claims deteriorating',_finite(g.get('Claims_13w_pct')) and g['Claims_13w_pct']>.10),('HY spreads widening',_finite(c.get('HYOAS_13w_delta')) and c['HYOAS_13w_delta']>0),('Financial conditions tighter than average',_finite(c.get('NFCI')) and c['NFCI']>0),('SOFR-IORB dislocation positive',_finite(c.get('SOFR_minus_IORB')) and c['SOFR_minus_IORB']>.10)],
     [('Credit/funding normalize',_finite(c.get('HYOAS_13w_delta')) and c['HYOAS_13w_delta']<0 and _finite(c.get('NFCI')) and c['NFCI']<0)]),
    ('NULL','No meaningful macro edge / mixed transmission',[],[]),
    ]
    rows=[]
    for typ,name,sup,contra in defs:
        supporting=[a for a,b in sup if b]; contradict=[a for a,b in contra if b]; observed=len([1 for a,b in sup if b])+len([1 for a,b in contra if b]); total=len(sup)+len(contra)
        rows.append({'type':typ,'scenario':name,'probability':np.nan,'probability_status':'DATA_GATED: no calibrated live-compatible probability','supporting_evidence':'; '.join(supporting) or 'None in loaded subset','contradicting_evidence':'; '.join(contradict) or 'None in loaded subset','evidence_observed':observed,'evidence_defined':total,'pricing':'PARTIAL: rates/credit/FX are observed; full implied expectations unavailable','beneficiaries':'EMPIRICAL CROSS-MARKET RANKING REQUIRED','losers':'EMPIRICAL CROSS-MARKET RANKING REQUIRED','duration':'DATA_GATED','expected_peak':'DATA_GATED','next_discriminating_observation':'Highest-value missing/contradicting variable in the scenario mechanism'})
    return pd.DataFrame(rows)

def research_evidence():
    p=HERE/'research'/'scenario_evidence_registry_v2.csv';return pd.read_csv(p) if p.exists() else pd.DataFrame()
