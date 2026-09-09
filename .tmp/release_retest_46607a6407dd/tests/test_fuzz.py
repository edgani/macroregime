from __future__ import annotations
import numpy as np
from decision_core import entry_decision, expression_decision, compute_revision_edge
rng=np.random.default_rng(42)
stages=set()
for _ in range(5000):
    row={'market':rng.choice(['US','IHSG','Crypto','FX','Commodity']),'research_action':rng.choice(['BUILD CANDIDATE','SELECTIVE ADD / WATCH','HOLD / NEEDS BETTER PRICE','SELL / AVOID','WATCH / NO FORCED TRADE']),'market_model_status':rng.choice(['RESEARCH READY / FUNDAMENTALS','RESEARCH READY / VALUE CAPTURE','PARTIAL / ECONOMICS','GATED']),'data_quality':rng.choice(['HIGH','MEDIUM','LOW']),'vertical_status':rng.choice(['READY','PARTIAL','GATED']),'evidence_families':int(rng.integers(0,6)),'deterioration_families':int(rng.integers(0,5)),'price':float(abs(rng.normal(100,50))+0.1),'symbol':'BTC-USD'}
    val={'valuation_confidence':rng.choice(['HIGH','MEDIUM','GATED']),'expectation_gap':float(rng.normal(.1,.4)),'fv_base':float(abs(rng.normal(120,60))+0.1)}
    macro={'action_label':rng.choice(['RISK-ON','SELECTIVE RISK-ON','HOLD / SELECTIVE','DEFENSIVE','CRISIS RISK-OFF']),'crash_state':rng.choice(['RESILIENT','WATCH','POWDER KEG','CRASH DANGER'])}
    prior={'price':float(abs(rng.normal(100,30))+0.1),'fv_base':float(abs(rng.normal(120,40))+0.1)}
    e=entry_decision(row,val,macro,prior); stages.add(e['entry_stage'])
    x=expression_decision(row,e,macro)
    assert isinstance(x['best_expression'],str)
    if row['market']=='IHSG': assert not x['leverage_allowed'] and not x['option_allowed']
    if row['vertical_status']!='READY': assert not x['leverage_allowed'] and not x['option_allowed']
assert 'DISCOVER' in stages
print('TEST_FUZZ_PASS',{'iterations':5000,'stages':sorted(stages)})
