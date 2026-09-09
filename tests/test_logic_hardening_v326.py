from __future__ import annotations
import json, math, tempfile
from pathlib import Path
import numpy as np, pandas as pd

from opportunity_outcomes import path_outcome, daily_bar_availability
from opportunity_learning import chronological_walk_forward, pattern_statistics
from opportunity_longitudinal import OpportunityMemory
from opportunity_discovery import component_scores, classify_archetypes
from verticals import available_families_from_row

# Weekend/holiday horizon: +1D from Friday must use first observation on/after Saturday -> Monday.
anchor=pd.Timestamp('2026-01-02T21:10:00Z')
asset=pd.Series([100.0,110.0], index=pd.to_datetime(['2026-01-02T21:10:00Z','2026-01-05T21:10:00Z']))
out=path_outcome(asset,anchor,anchor_price=100.0,horizon_days=1)
assert out['completed'] is True and abs(out['absolute_return']-0.10)<1e-12, out
assert out['asset_end_observation_utc'].startswith('2026-01-05'),out

# Benchmark anchor cannot come from the future relative to detection.
bench=pd.Series([100.0,200.0], index=pd.to_datetime(['2026-01-02T21:10:00Z','2026-01-05T21:10:00Z']))
out=path_outcome(asset,pd.Timestamp('2026-01-03T00:00:00Z'),anchor_price=100.0,benchmark=bench,horizon_days=1)
assert out['benchmark_anchor_observation_utc'].startswith('2026-01-02'),out
assert abs(out['benchmark_return']-1.0)<1e-12,out
assert pd.Timestamp(out['label_available_at_utc'])>=pd.Timestamp(out['benchmark_end_observation_utc'])

# Daily US close date is not knowable at midnight; Jan 2 2026 EST close + buffer = 21:10 UTC.
av=daily_bar_availability(pd.DatetimeIndex([pd.Timestamp('2026-01-02')]),'US')[0]
assert av == pd.Timestamp('2026-01-02T21:10:00Z'),av

# WFO embargo: Dec-2023 event with 3M label available Mar-2024 is not training data for 2024 test.
events=pd.DataFrame([
 {'event_id':'A','first_seen_time':'2022-06-01T00:00:00Z','market':'US','scores_json':{'opportunity_score':60}},
 {'event_id':'B','first_seen_time':'2023-12-15T00:00:00Z','market':'US','scores_json':{'opportunity_score':70}},
 {'event_id':'C','first_seen_time':'2024-06-01T00:00:00Z','market':'US','scores_json':{'opportunity_score':80}},
])
outs=pd.DataFrame([
 {'event_id':'A','horizon':'3M','completed':1,'alpha_vs_benchmark':.1,'absolute_return':.12,'mae':-.04,'peak_return':.2,'outcome_json':json.dumps({'label_available_at_utc':'2022-10-01T00:00:00Z'})},
 {'event_id':'B','horizon':'3M','completed':1,'alpha_vs_benchmark':.2,'absolute_return':.22,'mae':-.05,'peak_return':.3,'outcome_json':json.dumps({'label_available_at_utc':'2024-03-20T00:00:00Z'})},
 {'event_id':'C','horizon':'3M','completed':1,'alpha_vs_benchmark':.1,'absolute_return':.14,'mae':-.03,'peak_return':.2,'outcome_json':json.dumps({'label_available_at_utc':'2024-10-01T00:00:00Z'})},
])
wf=chronological_walk_forward(events,outs,min_train=1)
r=wf[wf['test_year']==2024]
assert len(r)==1 and int(r.iloc[0]['train_n'])==1,wf

# Missing alpha stays UNKNOWN, not a false loss in pattern stats.
evs=[]; os=[]
for i in range(5):
    evs.append({'event_id':f'P{i}','first_seen_time':'2024-01-01T00:00:00Z','market':'US','sector':'X','theme':'T','archetypes_json':['A'],'macro_context_json':{'regime':'RISK_ON'}})
    os.append({'event_id':f'P{i}','horizon':'3M','completed':1,'absolute_return':.1,'alpha_vs_benchmark':.05 if i==0 else np.nan,'mae':-.02,'outcome_json':json.dumps({'success_plus10_before_minus5':True,'success_plus20_before_minus10':False,'success_plus50_before_minus15':False})})
ps=pattern_statistics(pd.DataFrame(evs),pd.DataFrame(os),min_n=5)
g=ps[(ps['level']=='GLOBAL') & (ps['horizon']=='3M')].iloc[0]
assert int(g['relative_n'])==1 and abs(float(g['p_outperform_benchmark'])-1.0)<1e-12,g

# Generic narrative cannot manufacture economic capture/opportunity score.
row={'market':'US','symbol':'X','sector':'Software','change_score':90,'expectation_gap':.5,'valuation_confidence':'HIGH','revenue_growth_yoy':.4,'gross_margin_change':.03,'notes':'AI narrative only'}
sc=component_scores(row,{})
assert math.isnan(float(sc['capture_score'])) and math.isnan(float(sc['opportunity_score'])),sc

# Archetypes require evidence; capex spend / market membership / low FDV is insufficient.
assert 'CAPEX_BENEFICIARY' not in classify_archetypes({'market':'US','capex_to_revenue':.5})
assert 'FX_POLICY_DISLOCATION' not in classify_archetypes({'market':'FX'})
assert 'COMMODITY_SUPPLY_SHOCK' not in classify_archetypes({'market':'Commodity'})
assert 'SUPPLY_SCARCITY' not in classify_archetypes({'market':'Crypto','fdv_premium':0.0})

# Empty memory/revision placeholders do not count as evidence families.
fams=available_families_from_row({'market':'US','memory_observations':0,'expectation_revision_state':'N/A','chain_evidence':'UNVERIFIED'})
assert 'memory' not in fams and 'estimate_revisions' not in fams and 'causal_chain' not in fams,fams

# Terminal episode cannot be resurrected; new detection gets a new immutable event.
with tempfile.TemporaryDirectory() as td:
    mem=OpportunityMemory(Path(td)/'o.sqlite')
    payload={'first_seen_time':'2026-01-01T00:00:00Z','symbol':'ABC','market':'US','theme':'THEME','archetypes':[],'price':100,'snapshot':{},'macro_context':{},'fundamental_change':{},'expectation':{},'scores':{}}
    e1=mem.create_event(payload); eid1=e1['event_id']
    mem.record_state(eid1,'INVALIDATED',observed_at_utc='2026-01-10T00:00:00Z')
    p2=dict(payload); p2['first_seen_time']='2026-02-01T00:00:00Z'; p2['price']=120
    e2=mem.create_event(p2)
    assert e2['event_id']!=eid1,(e1,e2)
    assert mem.opportunity_status_at('ABC','US','2026-01-05T00:00:00Z')['active'] is True
    assert mem.opportunity_status_at('ABC','US','2026-01-20T00:00:00Z')['active'] is False
    assert mem.opportunity_status_at('ABC','US','2026-02-02T00:00:00Z')['active'] is True
    # Miss audit is immutable/idempotent.
    assert mem.record_missed_runner(symbol='ABC',market='US',anchor_at_utc='2025-01-01',runner_definition='+25% within 3M',future_return=.3,classification='DISCOVERY_MISS',observable_then=True,evidence={'v':1})
    assert not mem.record_missed_runner(symbol='ABC',market='US',anchor_at_utc='2025-01-01',runner_definition='+25% within 3M',future_return=.8,classification='FOUND',observable_then=True,evidence={'v':2})
    mr=mem.missed_frame().iloc[0]
    assert mr['classification']=='DISCOVERY_MISS' and abs(float(mr['future_return'])-.3)<1e-12

print('TEST_LOGIC_HARDENING_V326_PASS')
