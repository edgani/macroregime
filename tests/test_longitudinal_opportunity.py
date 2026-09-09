from __future__ import annotations

import tempfile
from pathlib import Path
import pandas as pd

from opportunity_longitudinal import OpportunityMemory
from opportunity_discovery import build_event_payload, sync_opportunities
from opportunity_outcomes import path_outcome
from opportunity_learning import chronological_walk_forward


def row(price=100.0, gap=0.30, stage='CONFIRMED INFLECTION'):
    return {
        'market':'US','symbol':'TEST','name':'Test Corp','sector':'Industrials','price':price,'market_cap':1_000_000_000,
        'revenue_growth_yoy':0.25,'eps_growth_yoy':0.30,'gross_margin_change':0.03,'fcf_growth_yoy':0.40,
        'expectation_gap':gap,'valuation_confidence':'HIGH','research_action':'BUILD CANDIDATE','stage':stage,
        'evidence_families':4,'deterioration_families':0,'data_quality':'HIGH','change_score':75,'change_state':'EMERGING',
        'notes':'data-center power/grid chain','vertical_status':'READY','causal_chain_verified':True,'theme_revenue_exposure_score':80,'margin_capture_score':75,'catalyst_quality_score':70,'refreshed_at_utc':'2026-01-02T00:00:00+00:00'
    }


def main():
    with tempfile.TemporaryDirectory() as td:
        mem=OpportunityMemory(Path(td)/'opp.sqlite')
        df=pd.DataFrame([row()])
        macro={'regime':'RISK-ON','action_label':'RISK-ON'}
        sync_opportunities(df,mem,macro,now='2026-01-02T00:00:00Z')
        ev=mem.events_frame()
        assert len(ev)==1
        first=float(ev.iloc[0]['first_seen_price'])
        eid=ev.iloc[0]['event_id']

        # Future/current refresh can change price but must never rewrite first detection.
        df2=pd.DataFrame([row(price=150.0,stage='HIGH-CONVICTION CANDIDATE')])
        sync_opportunities(df2,mem,macro,now='2026-02-02T00:00:00Z')
        ev2=mem.events_frame()
        assert len(ev2)==1
        assert float(ev2.iloc[0]['first_seen_price'])==first==100.0
        assert str(ev2.iloc[0]['first_high_conviction_time']).startswith('2026-02-02')
        assert float(ev2.iloc[0]['price_at_high_conviction'])==150.0

        # Outcome math starts at frozen anchor and uses only subsequent path.
        idx=pd.date_range('2026-01-02',periods=100,freq='D',tz='UTC')
        px=pd.Series([100+i*0.5 for i in range(100)],index=idx)
        bench=pd.Series([100+i*0.2 for i in range(100)],index=idx)
        out=path_outcome(px,'2026-01-02T00:00:00Z',benchmark=bench,horizon_days=30)
        assert out['completed'] is True
        assert out['absolute_return']>out['benchmark_return']
        assert out['mfe']>=out['absolute_return']
        assert out['mae']<=0.0

        # No random split: expanding WF trains only on years strictly before test year.
        events=[]; outs=[]
        for i,year in enumerate([2019]*10+[2020]*10+[2021]*10+[2022]*10+[2023]*10+[2024]*10):
            eid2=f'E{i}'
            events.append({'event_id':eid2,'first_seen_time':f'{year}-06-01T00:00:00Z','market':'US','scores_json':{'opportunity_score':40+(i%20)}})
            outs.append({'event_id':eid2,'horizon':'3M','completed':1,'alpha_vs_benchmark':0.1 if i%3 else -0.05,'absolute_return':0.12,'mae':-0.05,'peak_return':0.30,'outcome_json':{'label_available_at_utc':f'{year}-10-01T00:00:00Z'}})
        wf=chronological_walk_forward(pd.DataFrame(events),pd.DataFrame(outs),min_train=20)
        assert not wf.empty
        assert (wf['train_end'] < wf['test_year']).all()
        assert wf['method'].str.contains('chronological').all()

    print('longitudinal opportunity tests passed')

if __name__=='__main__': main()
