
from __future__ import annotations
import pandas as pd, numpy as np
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]

SCENARIOS=[
{'id':'BASE-GROWTH-COOLING','name':'Growth resilient / inflation cooling','type':'BASE','mechanism':'Real activity remains positive while inflation impulse cools; policy pressure eases without credit break','actors':'Households, firms, central bank, credit investors','catalyst_window':'1-4Q','invalidation':'Growth activity deteriorates with credit/funding stress OR inflation reaccelerates materially','next_observation':'Growth impulse, short-run inflation, credit velocity, policy path'},
{'id':'COMP-STICKY-INFLATION','name':'Growth resilient / sticky inflation / long-rate pressure','type':'COMPETING','mechanism':'Demand remains resilient while inflation/term premium keep real discount rates restrictive','actors':'Firms, workers, Treasury investors, central bank','catalyst_window':'1-4Q','invalidation':'Inflation expectations and real yields fall while growth stays resilient','next_observation':'Core inflation impulse, breakevens, term premium, real yield'},
{'id':'TAIL-CREDIT-STRESS','name':'Growth slowdown + credit/funding stress','type':'TAIL','mechanism':'Activity weakness meets tighter risk-bearing/refinancing, causing nonlinear deleveraging','actors':'Levered borrowers, credit investors, dealers, banks','catalyst_window':'Days-4Q','invalidation':'Credit/funding normalize despite weaker activity','next_observation':'HY velocity, EBP/funding when available, NFCI, lending standards'},
{'id':'NULL-NO-EDGE','name':'No meaningful macro edge / mixed transmission','type':'NULL','mechanism':'Signals conflict or current pricing absorbs the macro information','actors':'All','catalyst_window':'Indeterminate','invalidation':'A discriminating data sequence creates stable separation between scenarios','next_observation':'Whichever variable has highest tested conditional information'},
]

def empirical_scenario_models():
    p=HERE/'research'/'scenario_evidence_registry_v2.csv'
    return pd.read_csv(p) if p.exists() else pd.DataFrame()

def lifecycle(state, pricing_available=False, crowding_available=False):
    models=empirical_scenario_models()
    out=[]
    for s in SCENARIOS:
        # No numerical prior unless a calibrated, current-compatible model exists.
        prob=np.nan; probability_status='DATA_GATED: no calibrated live-compatible scenario probability'
        support=[]; contradict=[]
        g=state.get('Growth',{}); inf=state.get('Inflation',{}); c=state.get('Credit/Funding',{}); r=state.get('Policy/Rates',{})
        if s['id']=='BASE-GROWTH-COOLING':
            if np.isfinite(g.get('CFNAI',np.nan)) and g['CFNAI']>=0:support.append('Current activity index non-negative')
            if np.isfinite(inf.get('Core_3m_ann',np.nan)) and inf['Core_3m_ann']<.03:support.append('Short-run core inflation below 3% annualized')
            if np.isfinite(c.get('HYOAS_13w_delta',np.nan)) and c['HYOAS_13w_delta']>0.75:contradict.append('Credit spread velocity deteriorating')
        elif s['id']=='COMP-STICKY-INFLATION':
            if np.isfinite(inf.get('Core_3m_ann',np.nan)) and inf['Core_3m_ann']>=.03:support.append('Short-run core inflation remains elevated')
            if np.isfinite(r.get('Real10Y_13w_delta',np.nan)) and r['Real10Y_13w_delta']>0:support.append('Real-yield impulse rising')
        elif s['id']=='TAIL-CREDIT-STRESS':
            if np.isfinite(c.get('HYOAS_13w_delta',np.nan)) and c['HYOAS_13w_delta']>0:support.append('Credit spreads widening')
            if np.isfinite(c.get('NFCI',np.nan)) and c['NFCI']>0:support.append('Financial conditions tighter than average')
        out.append({**s,'probability':prob,'probability_status':probability_status,'supporting_evidence':'; '.join(support) or 'No validated current evidence loaded',
                    'contradicting_evidence':'; '.join(contradict) or 'None observed in loaded subset','pricing':'DATA_GATED' if not pricing_available else 'AVAILABLE',
                    'crowding':'DATA_GATED' if not crowding_available else 'AVAILABLE','thesis_decay':'DATA_GATED: requires dated catalyst likelihood model'})
    return pd.DataFrame(out)

def coherent_probability_check(df):
    p=pd.to_numeric(df.get('probability'),errors='coerce').dropna()
    if len(p)!=len(df): return False,'Probabilities unavailable; no normalization performed.'
    return abs(p.sum()-1)<1e-6,f'Sum={p.sum():.6f}'
