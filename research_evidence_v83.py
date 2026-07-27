"""V8.3 strict drawdown and real-profit-factor evidence attachment."""
from __future__ import annotations
import json
from copy import deepcopy
from pathlib import Path

HERE=Path(__file__).resolve().parent
RESULT=HERE/'research_v83/V83_RISK_PROFIT_AUDIT_RESULTS.json'
PROTO=HERE/'V83_RISK_PROFIT_PROTOCOL_FROZEN.json'

def _read(p:Path)->dict:
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return {}

def attach_research_evidence_v83(desk:dict)->dict:
    out=deepcopy(desk) if isinstance(desk,dict) else {}
    r=_read(RESULT); p=_read(PROTO); s=(r.get('cost_scenarios_bps_per_month') or {}).get('25') or {}
    out['v83_risk_profit_evidence']={
      'version':'8.3',
      'state':r.get('adjudication','NO_RESULT'),
      'capital_permission':'BLOCKED',
      'archive_risk_profile_pass':bool(r.get('archive_risk_profile_pass')),
      'all_live_trading_gates_pass':bool(r.get('all_live_trading_gates_pass')),
      'stress_25bps':s,
      'gates':r.get('gates') or {},
      'statistical_bounds':r.get('v82_statistical_bounds') or {},
      'real_trade_profit_factor':r.get('real_trade_profit_factor') or {},
      'profit_factor_definition':((p.get('real_trade_profit_factor_gates') or {}).get('definition')),
      'claim':'The aggregate archive drawdown profile survives a flat 25 bps/month stress, but this is not a real trade profit factor and cannot authorize capital.',
      'missing_for_live':['actual stock-level fills','explicit costs per trade','point-in-time holdings','independent modern holdout','200 matured prospective closed trades across four regimes']
    }
    return out
