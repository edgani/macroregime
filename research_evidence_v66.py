"""V6.6 scoped decision evidence: one historical US broad-equity risk-reduction control.

The component is decision-active only as an exposure cap at completed monthly rebalances.
It is not a return forecast, crash warning, ticker selector, short signal, or allocation target.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
import hashlib,json
import pandas as pd

from us_equity_risk_cap_v66 import evaluate_monthly_risk_cap
ROOT=Path(__file__).resolve().parent
RESULT=ROOT/'research_v66/results/V66_SMA10_RISK_REDUCTION_CONFIRMATION_RESULTS.json'
PROTOCOL=ROOT/'research_v66/protocols/V66_SMA10_RISK_REDUCTION_CONFIRMATION_PROTOCOL_FROZEN.json'
DATA=ROOT/'research_v66/data/sp500_monthly_shiller.csv'

def _sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def _protocol_sha(p:Path)->str:
    obj=json.loads(p.read_text()); obj.pop('protocol_sha256',None)
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def _fallback(reason:str)->dict[str,Any]:
    return {'schema':'warroom.v66.scoped_risk_control.fallback','status':'UNAVAILABLE_FAIL_CLOSED','reason':reason,
      'decision_active_risk_controls':[],'decision_active_risk_control_count':0,'directional_or_ticker_components':0,
      'capital_permission':'DIRECTIONAL_CAPITAL_BLOCKED','scoped_risk_permission':'NO_PERMISSION_FAIL_CLOSED'}

def load_research_evidence_v66()->dict[str,Any]:
    try:r=json.loads(RESULT.read_text()); p=json.loads(PROTOCOL.read_text())
    except Exception as exc:return _fallback(f'evidence unreadable: {type(exc).__name__}: {exc}')
    if not r.get('passed'):return _fallback('confirmation result did not pass')
    if r.get('protocol_sha256')!=_protocol_sha(PROTOCOL):return _fallback('protocol hash mismatch')
    if r.get('adjudication',{}).get('scoped_claim')!='CONFIRMED_HISTORICAL_RISK_REDUCTION':return _fallback('claim adjudication mismatch')
    try:
        d=pd.read_csv(DATA); d['Date']=pd.to_datetime(d['Date']); d=d[d['SP500'].gt(0)].sort_values('Date')
        obs=[{'observed_month':x.Date.date().isoformat(),'close':float(x.SP500)} for x in d.tail(18).itertuples()]
        decision=evaluate_monthly_risk_cap(obs,as_of='2026-07-26',max_staleness_months=1).to_dict()
    except Exception as exc:return _fallback(f'current state unavailable: {type(exc).__name__}: {exc}')
    c=r['confirmatory']; c25=r['confirmatory_25bps']; roll=r['rolling']
    control={
      'component_id':'US_SMA10_MONTHLY_RISK_CAP','component_class':'DECISION_ACTIVE_SCOPED_RISK_CONTROL',
      'market_scope':'US_BROAD_EQUITY_ONLY','instrument_scope':'broad US equity benchmark exposure; no individual ticker selection',
      'decision_active':decision['status'] in {'BASELINE_CAP_ALLOWED','REDUCE_TO_CASH_CAP'},
      'predictive_semantics':False,'live_alpha_weight':0.0,'capital_creation_permission':False,
      'decision_permission':'REDUCE_US_BROAD_EQUITY_EXPOSURE_ONLY_AT_MONTHLY_REBALANCE',
      'current_decision':decision,'confirmatory_period':'1920-01 through 1959-12',
      'confirmatory_max_drawdown_improvement':c['dd_improvement'],'confirmatory_es5_improvement':c['es_improvement'],
      'confirmatory_annual_return_difference':c['ret_diff'],'confirmatory_25bps_es5_improvement':c25['es_improvement'],
      'rolling_20y_windows':roll['n_windows'],'rolling_drawdown_positive_share':roll['dd_positive_share'],
      'rolling_es_positive_share':roll['es_positive_share'],'rolling_median_return_difference':roll['return_difference_median'],
      'bootstrap_es_lower_bound':c['bootstrap']['es_lower'],'bootstrap_drawdown_positive_probability':c['bootstrap']['dd_positive_probability'],
      'crash_prediction_permission':False,'ticker_permission':False,'short_permission':False,'leverage_permission':False,
      'cross_market_permission':False,'claim_limit':r['claim_limit'],'protocol_sha256':r['protocol_sha256'],
      'data_sha256':_sha(DATA),'capital_permission':'CONDITIONAL_RISK_CAP_ONLY'
    }
    return {
      'schema':'warroom.v66.scoped_risk_control.v1','status':'SCOPED_RISK_CONTROL_CONFIRMED',
      'decision_active_risk_controls':[control],'decision_active_risk_control_count':1,
      'directional_or_ticker_components':0,'alpha_components_capital_ready':0,
      'scoped_risk_permission':decision['status'],'capital_permission':'DIRECTIONAL_CAPITAL_BLOCKED',
      'prospective_shadow_required':True,
      'claim_boundary':'One historical broad-US-equity monthly risk-reduction control is usable as a fail-closed exposure cap. No ticker, directional alpha, target, short, leverage, crash forecast, or cross-market permission is granted.'
    }

def attach_research_evidence_v66(desk:dict)->dict:
    if not isinstance(desk,dict):return desk
    out=deepcopy(desk);out['research_evidence_v66']=load_research_evidence_v66();return out
