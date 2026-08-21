from __future__ import annotations
from pathlib import Path
import json, csv
from dataclasses import asdict
from final_core.scenario_discovery import Evidence, discover, save
from final_core.asset_transmission import candidate_assets
from final_core.ticker_engine import qualify
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'FINAL_HANDOFF'

def run(current_evidence_path=None, company_input_path=None):
    ep=Path(current_evidence_path or ROOT/'data'/'current'/'evidence.json')
    raw=json.loads(ep.read_text(encoding='utf-8')); events=[Evidence(**x) for x in raw]
    scenarios=discover(events); save(events,scenarios)
    assets=candidate_assets(scenarios,OUT/'51_MULTI_ENGINE_VALIDATION_SUMMARY.json')
    # Company input is intentionally optional; no input => no rank, not invented names.
    company_rows=[]
    cp=Path(company_input_path) if company_input_path else ROOT/'data'/'current'/'company_inputs.json'
    if cp.exists(): company_rows=json.loads(cp.read_text(encoding='utf-8'))
    tickers=qualify(company_rows)
    qualified=[asdict(x) for x in tickers if x.status=='QUALIFIED']
    result={
      'system_status':'PASS_SCOPE_LIMITED_FAIL_CLOSED',
      'scenario_count':len(scenarios),
      'scenarios':[asdict(s) for s in scenarios],
      'asset_candidates':[asdict(a) for a in assets],
      'ticker_decisions':[asdict(t) for t in tickers],
      'qualified_opportunities':qualified,
      'current_action':'NO_QUALIFIED_OPPORTUNITY' if not qualified else 'QUALIFIED_OPPORTUNITIES_EXIST',
      'note':'No ticker is emitted unless factual company evidence, calibrated probabilities and EV inputs are supplied.'
    }
    (OUT/'52_CURRENT_PRODUCTION_RUN.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    # stable CSV for downstream/UI
    with (OUT/'42_CURRENT_QUALIFIED_OPPORTUNITIES.csv').open('w',newline='',encoding='utf-8') as f:
      fields=['ticker','status','reason','p_mechanism_true','p_catalyst_within_horizon','p_not_fully_priced','p_trade_profitable_net','ev_net','action']
      w=csv.DictWriter(f,fieldnames=fields);w.writeheader();
      for x in qualified:w.writerow({k:x.get(k) for k in fields})
      if not qualified:w.writerow({'ticker':'','status':'NO_QUALIFIED_OPPORTUNITY','reason':'NO_FULLY_CALIBRATED_TICKER_PIPELINE_INPUT','action':'WAIT'})
    return result

if __name__=='__main__':
    r=run(); print(json.dumps({'system_status':r['system_status'],'scenario_count':r['scenario_count'],'asset_candidate_count':len(r['asset_candidates']),'qualified_opportunity_count':len(r['qualified_opportunities']),'current_action':r['current_action']},indent=2))
