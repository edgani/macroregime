from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
from datetime import datetime, timezone
import json
from .live_data import fetch_all
from .state_engine import derive_states
from .scenario_engine import discover_verified, radar_from_news, radar_from_news_general
from .company_engine import generate_candidates
from .asset_engine import generate_assets

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data'/'current'; OUT.mkdir(parents=True,exist_ok=True)


def _state_map(states): return {s.state_id:s for s in states}

def _global_posture(states):
    sm=_state_map(states)
    risk=[]
    for k in ('GROWTH','LABOR','INFLATION','POLICY','CREDIT','LIQUIDITY','HOUSING'):
        s=sm.get(k)
        if not s:continue
        if s.value in ('WEAKENING','SOFTENING','HOT/STICKY','RESTRICTIVE','STRESS','TIGHTENING','WEAK'): risk.append(k)
    if len(risk)>=4:return 'DEFENSIVE / CONFLICTED',risk
    if len(risk)>=2:return 'MIXED / SELECTIVE',risk
    return 'BENIGN / SELECTIVE',risk


def run(force=False):
    data=fetch_all(force=force)
    states,evidence=derive_states(data)
    scenarios=discover_verified(evidence)
    radar=radar_from_news(data.get('news_leads',{}))
    general_radar=radar_from_news_general(data.get('news_leads',{}))
    seen={x.get('scenario_id') for x in radar}
    radar = radar + [x for x in general_radar if x.get('scenario_id') not in seen]
    assets=generate_assets(scenarios,radar)
    tickers=generate_candidates(scenarios,radar,force=force)
    posture,risk=_global_posture(states)
    # No calibrated P(trade profitable) => no production BUY/SHORT.
    current_action='WAIT / RESEARCH CANDIDATES' if tickers else 'WAIT / NO QUALIFIED OPPORTUNITY'
    result={
      'generated_at':datetime.now(timezone.utc).isoformat(),
      'system_status':'LIVE_DECISION_SUPPORT_FAIL_CLOSED',
      'global_posture':posture,'risk_flags':risk,'current_action':current_action,
      'states':[asdict(s) for s in states],
      'evidence':[asdict(e) for e in evidence],
      'scenarios':[asdict(s) for s in scenarios],
      'scenario_radar':radar,
      'asset_candidates':assets,
      'ticker_candidates':[asdict(t) for t in tickers],
      'qualified_opportunities':[],
      'markets':data.get('markets',{}),
      'world':data.get('world',{}),
      'source_summary':{
        'macro_series':len(data.get('macro',{}).get('series',{})),
        'macro_as_of':data.get('macro',{}).get('as_of'),
        'market_status':data.get('markets',{}).get('status'),
        'news_status':data.get('news_leads',{}).get('status'),
        'treasury_status':data.get('treasury',{}).get('status'),
      },
      'news_leads':data.get('news_leads',{}).get('leads',[]),
      'production_note':'Ticker candidates are generated automatically, but BUY/SHORT qualification remains blocked until PIT company transmission, calibrated probabilities, priced-in and EV gates are validated.'
    }
    (OUT/'warroom_state.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    return result


def load_or_run(force=False):
    p=OUT/'warroom_state.json'
    if p.exists() and not force:
        try:return json.loads(p.read_text(encoding='utf-8'))
        except Exception:pass
    return run(force=force)

if __name__=='__main__':
    r=run(force=True)
    print(json.dumps({'status':r['system_status'],'posture':r['global_posture'],'states':len(r['states']),'scenarios':len(r['scenarios']),'radar':len(r['scenario_radar']),'candidates':len(r['ticker_candidates']),'action':r['current_action']},indent=2))
