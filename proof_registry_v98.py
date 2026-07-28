"""V9.8 exact-market proof registry. A source/quote/ticker packet can never replace proof."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any
from global_market_promotion_gate_v98 import evaluate_all
HERE=Path(__file__).resolve().parent
REGISTRY_PATH=HERE/'component_registry_v98.json'; POLICY_PATH=HERE/'NO_TECHNICAL_ANALYSIS_POLICY.json'

def _sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _safe(relative:str)->Path|None:
    try:
        p=(HERE/relative).resolve(); p.relative_to(HERE.resolve()); return p
    except Exception:return None

def load_registry()->dict[str,Any]:
    try: raw=json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))
    except Exception: raw={"version":"9.8","schema":"warroom.v98.component_registry.v1","components":{}}
    if raw.get('schema')!='warroom.v98.component_registry.v1' or not isinstance(raw.get('components'),dict):
        return {"version":"9.8","schema":"warroom.v98.component_registry.v1","components":{}}
    return raw

def component_status(name:str,row:dict[str,Any])->tuple[dict[str,Any],dict[str,Any]|None]:
    out=dict(row); market=str(out.get('market') or '').lower(); reasons=[]; run=None
    out.update({'decision_active':False,'capital_permission':'BLOCKED','live_weight':0.0})
    rel=str(out.get('proof_run_path') or ''); expected=str(out.get('proof_run_sha256') or '').lower(); path=_safe(rel) if rel else None
    if path is None or not path.is_file(): reasons.append('V9.8 bound proof run not installed')
    elif len(expected)!=64 or _sha(path)!=expected: reasons.append('proof-run hash missing or mismatched')
    else:
        try:
            raw=json.loads(path.read_text(encoding='utf-8')); run=raw if isinstance(raw,dict) else None
            if run is None: raise ValueError('proof root is not object')
        except Exception as exc: reasons.append(f'proof run unreadable: {type(exc).__name__}: {exc}')
    if run is not None:
        if run.get('schema') not in {'warroom.v96.blind_proof_run.v1','warroom.v97.blind_proof_run.v1','warroom.v98.blind_proof_run.v1'}: reasons.append('wrong proof-run schema')
        if str(run.get('market') or '').lower()!=market: reasons.append('proof market mismatch')
        if run.get('trading_ready') is not True or run.get('capital_permission')!='LIMITED_PRODUCTION_ELIGIBLE': reasons.append('proof run did not pass')
        if (run.get('signed_receipt_verification') or {}).get('valid') is not True: reasons.append('signed receipt invalid')
        if run.get('errors'): reasons.append('proof run contains errors')
    valid=not reasons and run is not None
    out.update({'proof_run_valid':valid,'proof_run_hash':expected if valid else None,'proof_run_reasons':sorted(set(reasons)),'decision_active':valid,'capital_permission':'LIMITED_PRODUCTION_ELIGIBLE' if valid else 'BLOCKED','live_weight':1.0 if valid else 0.0,'state':'AWAITING_HUMAN_ORDER_APPROVAL' if valid else 'AWAITING_BOUND_V98_PROOF'})
    return out,run if valid else None

def attach_proof_registry(desk:dict)->dict:
    if not isinstance(desk,dict):return desk
    registry=load_registry(); statuses={}; runs={}
    for name,row in registry['components'].items():
        status,run=component_status(name,row if isinstance(row,dict) else {}); statuses[name]=status
        if run is not None:runs[str(status.get('market'))]=run
    global_result=evaluate_all(runs); authorized=sorted(name for name,row in statuses.items() if row.get('decision_active') is True)
    desk['proof_registry']={**registry,'components':statuses,'global_adjudication':global_result}
    try:desk['no_technical_analysis_policy']=json.loads(POLICY_PATH.read_text(encoding='utf-8'))
    except Exception:desk['no_technical_analysis_policy']={'capital_default':'BLOCKED','effective_version':'9.8'}
    desk['proof_status']={'final_trading_system':bool(global_result['global_trading_ready']),'all_market_trading_ready':bool(global_result['global_trading_ready']),'predictive_components_promoted':len(authorized),'decision_active_predictive_components':len(authorized),'capital_authorized_components':authorized,'missing_market_components':[m for m in ('us','idx','commodity','fx','crypto') if m not in runs],'capital_permission':global_result['capital_permission'],'operational_permission':'UNIFIED_DECISION_PACKET_CONTROL_PLANE_READY','software_is_not_alpha':True,'order_export_requires_human_approval':True,'auto_submit':False,'proof_firewall_version':'9.8'}
    return desk
