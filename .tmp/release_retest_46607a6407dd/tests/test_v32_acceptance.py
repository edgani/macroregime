from __future__ import annotations
import inspect
from pathlib import Path
import pandas as pd

import opportunity_discovery as d
import opportunity_learning as l
import opportunity_longitudinal as m
import opportunity_outcomes as o
from _state_dir import isolated_state_dir


def main():
    checks=[]
    # 1 automatic discovery surface
    checks.append(callable(d.sync_opportunities))
    # 2 manual ticker lookup preserved structurally in app
    app=Path('app.py').read_text(encoding='utf-8')
    checks.append('symbol' in app and 'selectbox' in app)
    # 3 persistence across restart
    with isolated_state_dir() as td:
        p=td/'x.sqlite'; mem=m.OpportunityMemory(p)
        payload={'first_seen_time':'2026-01-01T00:00:00Z','symbol':'X','market':'US','theme':'T','archetypes':['REVENUE_INFLECTION'],'price':10,'snapshot':{'known':1}}
        e=mem.create_event(payload); eid=e['event_id']
        mem2=m.OpportunityMemory(p); checks.append(len(mem2.events_frame())==1)
        # 4 first detection timestamp immutable
        first=mem2.get_event(eid)['first_seen_time']; mem2.record_state(eid,'HIGH_CONVICTION',observed_at_utc='2026-02-01T00:00:00Z',price=20)
        checks.append(mem2.get_event(eid)['first_seen_time']==first)
        # 5 first price preserved
        checks.append(float(mem2.get_event(eid)['first_seen_price'])==10.0)
        # 6 future data not inserted into frozen snapshot
        checks.append(mem2.get_event(eid)['snapshot_json'].find('future')<0)
        # 7 failed opportunity retained
        mem2.record_state(eid,'INVALIDATED',observed_at_utc='2026-03-01T00:00:00Z')
        checks.append(len(mem2.events_frame(active_only=False))==1)
    # 8 missed winner analysis exists
    checks.append(hasattr(m.OpportunityMemory,'record_missed_runner'))
    # 9 relative alpha measured
    checks.append('alpha_vs_benchmark' in m.SCHEMA)
    # 10 sector benchmark outcome exists
    checks.append('alpha_vs_sector' in m.SCHEMA)
    # 11 macro point-in-time frozen in event
    checks.append('macro_context_json' in m.SCHEMA)
    # 12 no random train/test split
    src=inspect.getsource(l.chronological_walk_forward).lower(); checks.append('train_test_split' not in src and 'shuffle' not in src and 'test_year' in src)
    # 13 no classic indicator dependency in primary discovery
    ds=Path('opportunity_discovery.py').read_text().lower(); checks.append('import ta' not in ds and 'from ta ' not in ds and 'talib' not in ds)
    # 14 economic capture visible
    checks.append('capture_score' in ds and 'revenue_link' in m.SCHEMA)
    # 15 narrative-only cannot be sufficient: meaningful detection needs evidence/change/score
    checks.append('meaningful_detection' in ds and 'narrative' not in inspect.getsource(d.meaningful_detection).lower())
    # 16 multi-market support
    checks.append(all(x in d.SUPPORTED_MARKETS for x in ['US','IHSG','Crypto','FX','Commodity','China','Europe','Taiwan']))
    # 17 cross-asset opportunity architecture still present
    checks.append('Commodity' in d.SUPPORTED_MARKETS and 'FX' in d.SUPPORTED_MARKETS)
    # 18 production weights stable / learning only reports
    checks.append('weights' not in inspect.getsource(l.learning_report).lower())
    # 19 no autotrading components in new longitudinal layer
    newcode='\n'.join(Path(x).read_text().lower() for x in ['opportunity_longitudinal.py','opportunity_discovery.py','opportunity_learning.py','opportunity_outcomes.py'])
    checks.append('private_key' not in newcode and 'place_order' not in newcode)
    # 20 insufficient sample remains gated
    empty=l.pattern_statistics(pd.DataFrame(),pd.DataFrame()); checks.append(empty.empty)
    assert len(checks)==20 and all(checks), [(i+1,v) for i,v in enumerate(checks) if not v]
    print('v3.2 acceptance: 20/20 structural checks passed')

if __name__=='__main__': main()
