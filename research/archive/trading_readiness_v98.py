"""Machine-readable V9.8 unified decision and execution readiness audit."""
from __future__ import annotations
import datetime as dt
import hashlib, json
from pathlib import Path
from typing import Any
from execution_reconciliation_v98 import verify_ledger
HERE=Path(__file__).resolve().parent
MARKETS=("us","idx","commodity","fx","crypto")

def _load(path:Path,default:Any)->Any:
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return default

def audit()->dict[str,Any]:
    policy=_load(HERE/'V98_LIMITED_PRODUCTION_POLICY.json',{})
    universe=_load(HERE/'V98_EXECUTION_REFERENCE_UNIVERSE.json',{})
    registry=_load(HERE/'component_registry_v98.json',{'components':{}})
    quotes=_load(HERE/'runtime'/'v98_trading'/'execution_quotes.json',{})
    routes=policy.get('market_routes') if isinstance(policy.get('market_routes'),dict) else {}
    components=registry.get('components') if isinstance(registry.get('components'),dict) else {}
    rows={}
    for market in MARKETS:
        component_rows=[row for row in components.values() if isinstance(row,dict) and str(row.get('market') or '').lower()==market]
        bound=[row for row in component_rows if row.get('proof_run_path') and row.get('proof_run_sha256')]
        quote_rows=((quotes.get('markets') or {}).get(market) or {}) if isinstance(quotes,dict) else {}
        rows[market]={
            'market':market,'route_defined':market in routes,'execution_reference_route_defined':bool(universe.get(market)),
            'current_quote_count':len(quote_rows),'proof_component_defined':len(component_rows)==1,'bound_proof_runs':len(bound),
            'operational_control_plane_ready':bool(market in routes and universe.get(market) and len(component_rows)==1),
            'limited_production_signal_ready':len(bound)==1 and bool(quote_rows),
            'capital_permission':'AWAITING_BOUND_PROOF' if not bound else 'REQUIRES_RUNTIME_RECOMPUTATION_AND_HUMAN_APPROVAL',
        }
    ledger=verify_ledger()
    required=['dashboard.html','decision_packet_v98.py','public_snapshot_reader_v98.py','trading_control_plane_v98.py','execution_quote_collector_v98.py','execution_reconciliation_v98.py','V98_LIMITED_PRODUCTION_POLICY.json','V98_EXECUTION_REFERENCE_UNIVERSE.json','component_registry_v98.json']
    missing=[name for name in required if not (HERE/name).is_file()]
    ready=sum(bool(x['operational_control_plane_ready']) for x in rows.values())
    payload={
        'schema':'warroom.v98.trading_readiness.v1','release':'War Room OS V9.8 Unified Decision Packet',
        'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
        'markets':rows,'operational_control_plane_ready_markets':ready,
        'current_execution_quote_markets':sum(bool(x['current_quote_count']) for x in rows.values()),
        'bound_proof_markets':sum(bool(x['bound_proof_runs']) for x in rows.values()),
        'limited_production_signal_ready_markets':sum(bool(x['limited_production_signal_ready']) for x in rows.values()),
        'auto_submit_enabled':bool((policy.get('execution_rules') or {}).get('auto_submit_enabled')),
        'broker_neutral_export_only':bool((policy.get('execution_rules') or {}).get('broker_neutral_export_only')),
        'kill_switch_engaged':(HERE/'runtime'/'v98_trading'/'KILL_SWITCH.json').is_file(),
        'ledger_integrity':ledger,'required_files_missing':missing,
        'software_state':'UNIFIED_DECISION_PACKET_CONTROL_PLANE_READY' if not missing and ready==5 and ledger.get('valid') else 'INCOMPLETE',
        'alpha_state':'NO_APPROVED_ALPHA' if sum(bool(x['bound_proof_runs']) for x in rows.values())==0 else 'BOUND_PROOF_PRESENT_RECOMPUTE_AT_ORDER_TIME',
        'operational_permission':'CONTEXT_REFRESH_UNIFIED_PACKET_RISK_CHECK_MANUAL_ORDER_EXPORT_RECONCILIATION',
        'capital_permission':'BLOCKED_UNTIL_EXACT_PROOF_AND_HUMAN_APPROVAL','fully_proven_markets':0,
        'claim_limit':'V9.8 unifies research and execution context. It does not manufacture alpha and exports no order without exact proof, a valid ticker value bridge, fresh quote, risk checks and human approval.',
    }
    payload['status_hash']=hashlib.sha256(json.dumps({k:v for k,v in payload.items() if k!='status_hash'},sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
    return payload

def write(path:Path|None=None)->dict[str,Any]:
    result=audit(); out=path or (HERE/'runtime'/'v98_trading'/'V98_TRADING_READINESS.json'); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2),encoding='utf-8'); return result
if __name__=='__main__':print(json.dumps(write(),indent=2))
