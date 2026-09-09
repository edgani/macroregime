from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from prospective_validation import ProspectiveValidationStore
from universe_catalog import deterministic_rotation, merge_seed_with_rotation
from _state_dir import isolated_state_dir

with isolated_state_dir() as td:
    st=ProspectiveValidationStore(td/'p.sqlite')
    cat=pd.DataFrame({'market':['US']*4,'symbol':['AAA','BBB','CCC','DDD'],'name':['A','B','C','D'],'catalog_source':['SEC']*4})
    assert st.snapshot_universe(cat,'US','SEC',observed_at='2026-01-02T15:00:00Z')==4
    # Repeating same day's catalog is idempotent and provider absence is not interpreted here as delisting.
    assert st.snapshot_universe(cat.iloc[:2],'US','SEC',observed_at='2026-01-02T20:00:00Z')==0
    assert len(st.universe_frame('US'))==4

    seed=pd.DataFrame({'market':['US'],'symbol':['AAA'],'name':['A'],'notes':['seed']})
    r1=deterministic_rotation(cat,['AAA'],as_of='2026-01-02T12:00:00Z',n=2)
    r2=deterministic_rotation(cat,['AAA'],as_of='2026-01-02T12:20:00Z',n=2)
    assert r1['symbol'].tolist()==r2['symbol'].tolist() and 'AAA' not in r1['symbol'].tolist()
    merged=merge_seed_with_rotation(seed,{'US':cat},['US'],as_of='2026-01-02T12:00:00Z',extras_per_market=2)
    assert len(merged)==3 and merged['symbol'].nunique()==3

    scan=pd.DataFrame([
      {'market':'US','symbol':'AAA','price':100,'price_change_6m':.5,'eps_growth_yoy':.1,'forward_pe':20,'expectation_revision_score':55,'sector':'S1','avg_value_20d':10,'vertical_status':'READY'},
      {'market':'US','symbol':'BBB','price':100,'price_change_6m':.2,'eps_growth_yoy':.5,'forward_pe':10,'expectation_revision_score':80,'sector':'S1','avg_value_20d':20,'vertical_status':'READY'},
      {'market':'US','symbol':'CCC','price':100,'price_change_6m':.3,'eps_growth_yoy':.2,'forward_pe':30,'expectation_revision_score':60,'sector':'S2','avg_value_20d':30,'vertical_status':'PARTIAL'},
    ])
    n=st.freeze_baselines(scan,{'US':'SPY'},observed_at='2026-01-02T20:00:00Z')
    assert n>=4,n
    assert st.freeze_baselines(scan,{'US':'SPY'},observed_at='2026-01-02T21:00:00Z')==0
    # Daily runner cohort frozen once per symbol; no hindsight fields are added later.
    assert st.freeze_runner_cohort(scan,{'US':'SPY'},observed_at='2026-01-02T20:00:00Z')==3
    assert st.freeze_runner_cohort(scan,{'US':'SPY'},observed_at='2026-01-02T21:00:00Z')==0
    due=st.runner_anchors_due(min_age_days=91,limit=10,now='2026-04-10T00:00:00Z')
    assert len(due)==3
    aid=int(due.iloc[0]['id']); st.mark_runner_audited(aid,observed_at='2026-04-10T00:00:00Z')
    due2=st.runner_anchors_due(min_age_days=91,limit=10,now='2026-04-10T00:00:00Z')
    assert aid not in set(due2['id'].astype(int))

print('TEST_PROSPECTIVE_VALIDATION_PASS')
