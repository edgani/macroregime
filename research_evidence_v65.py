"""V6.5 proof-first kernel evidence.

This module makes a strict distinction between:
- evidence-active research claims that passed their exact archive-level contract,
- operational controls that are allowed to run because their software contract is validated,
- predictive/live components, which remain inactive until PIT, capacity, prospective and signed receipt gates pass.

The point is not to make every idea look proven.  The point is to guarantee that no unproven
component is active in a scope broader than its evidence.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent
GLOBAL_RESULTS=ROOT/'research_v65/results/V65_GLOBAL_SELECTION_ADJUDICATION_RESULTS.json'
GLOBAL_PROTOCOL=ROOT/'research_v65/protocols/V65_GLOBAL_SELECTION_ADJUDICATION_PROTOCOL.json'
STABILITY_RESULTS=ROOT/'research_v65/results/V65_STABILITY_FALSIFICATION_RESULTS.json'
STABILITY_PROTOCOL=ROOT/'research_v65/protocols/V65_STABILITY_FALSIFICATION_PROTOCOL_FROZEN.json'
INFO_RESULTS=ROOT/'research_v65/results/V65_INFORMATION_ORIGIN_ENSEMBLE_RESULTS.json'
INFO_PROTOCOL=ROOT/'research_v65/protocols/V65_INFORMATION_ORIGIN_ENSEMBLE_PROTOCOL_FROZEN.json'
EXPECTED=['SMILE_ANN','SMILE_ONLY','SMILE_EXPECTATIONS_DIV']

def _sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()

def _fallback(reason:str)->dict[str,Any]:
    return {
      'schema':'warroom.v65.proof_first_kernel.fallback','status':'UNAVAILABLE_FAIL_CLOSED','reason':reason,
      'evidence_active_research_claims':[], 'evidence_active_research_claim_count':0,
      'all_evidence_active_claims_pass_exact_contract':False,'live_predictive_components_promoted':0,
      'live_decision_weight':0.0,'capital_permission':'BLOCKED'
    }

def load_research_evidence_v65()->dict[str,Any]:
    try:
        glob=json.loads(GLOBAL_RESULTS.read_text()); stab=json.loads(STABILITY_RESULTS.read_text()); info=json.loads(INFO_RESULTS.read_text())
    except Exception as exc: return _fallback(f'V65 evidence unreadable: {type(exc).__name__}: {exc}')
    if glob.get('schema')!='warroom.v65.global_selection_adjudication.results.v1': return _fallback('global schema mismatch')
    if stab.get('schema')!='warroom.v65.stability_falsification.results.v1': return _fallback('stability schema mismatch')
    if info.get('schema')!='warroom.v65.information_origin_ensemble.results.v1': return _fallback('information-origin schema mismatch')
    if glob.get('protocol_sha256')!=_sha(GLOBAL_PROTOCOL): return _fallback('global protocol hash mismatch')
    if stab.get('protocol_sha256')!=_sha(STABILITY_PROTOCOL): return _fallback('stability protocol hash mismatch')
    if info.get('protocol_sha256')!=_sha(INFO_PROTOCOL): return _fallback('information-origin protocol hash mismatch')
    if glob.get('hurdle_10bp_survivors')!=EXPECTED: return _fallback('global 10bp survivor invariant mismatch')
    if glob.get('hurdle_25bp_survivors')!=[]: return _fallback('global 25bp survivor invariant mismatch')
    if stab.get('stability_survivors')!=EXPECTED: return _fallback('stability survivor invariant mismatch')
    claims=[]
    for cid in EXPECTED:
        gd=glob['details'][cid]; sd=stab['details'][cid]
        if not gd.get('hurdle_10bp_pass_global_216') or not sd.get('stability_pass'):
            return _fallback(f'{cid} exact contract failed')
        claims.append({
          'claim_id':cid,
          'proof_scope':'MAINTAINED_ARCHIVE_MODERN_AGGREGATE_10BP_STABILITY_SUPPORTED',
          'market_scope':'US_LISTED_STOCKS_WITH_OPTION_DATA; AGGREGATE LONG_SHORT ARCHIVE',
          'primary_role':'OPTION_IMPLIED_TAIL_ASYMMETRY_AND_INFORMATION_ORIGIN',
          'members':gd.get('definition',{}).get('members',[]),
          'global_selection_family_count':glob.get('global_family_count'),
          'validation_10bp_alpha_monthly':gd['validation']['0.001'].get('alpha_monthly'),
          'validation_10bp_global_lower_bound':gd['validation']['0.001'].get('global_216_simultaneous_lower_bound'),
          'lockbox_10bp_alpha_monthly':gd['lockbox']['0.001'].get('alpha_monthly'),
          'lockbox_10bp_global_lower_bound':gd['lockbox']['0.001'].get('global_216_simultaneous_lower_bound'),
          'validation_rolling_positive_share':sd['validation']['rolling'].get('positive_share'),
          'lockbox_rolling_positive_share':sd['lockbox']['rolling'].get('positive_share'),
          'validation_bootstrap_positive_probability':sd['validation']['moving_block_bootstrap'].get('positive_probability'),
          'lockbox_bootstrap_positive_probability':sd['lockbox']['moving_block_bootstrap'].get('positive_probability'),
          'stability_pass':True,
          'flat_25bp_global_pass':False,
          'independent_external_lockbox':False,
          'non_micro_capacity_proven':False,
          'point_in_time_ticker_selector_proven':False,
          'prospective_profitability_proven':False,
          'evidence_active':True,
          'decision_active':False,
          'live_decision_weight':0.0,
          'capital_permission':'BLOCKED'
        })
    return {
      'schema':'warroom.v65.proof_first_kernel.v1','status':'PROOF_FIRST_KERNEL_RECONCILED',
      'kernel_policy':'ONLY_COMPONENTS_THAT_PASS_THEIR_EXACT_SCOPE_CONTRACT_MAY_BE_EVIDENCE_ACTIVE; ONLY_SIGNED_PIT_PROSPECTIVE_COMPONENTS_MAY_BE_DECISION_ACTIVE',
      'evidence_active_research_claims':claims,'evidence_active_research_claim_count':len(claims),
      'all_evidence_active_claims_pass_exact_contract':True,
      'global_10bp_archive_supported_count':glob.get('hurdle_10bp_pass_count'),
      'global_25bp_archive_supported_count':glob.get('hurdle_25bp_pass_count'),
      'stability_confirmed_count':stab.get('stability_pass_count'),
      'live_predictive_components_promoted':0,'decision_active_predictive_components':[],
      'independent_modern_claims_proven':0,'non_micro_capacity_claims_proven':0,
      'point_in_time_ticker_selectors_proven':0,'prospective_capital_claims_proven':0,
      'active_component_semantics':{
         'operational_controls':'May run only within validated software/fail-closed contracts.',
         'evidence_active_research':'May be displayed as exact-scope evidence; cannot rank tickers, set direction, target, size or capital.',
         'decision_active':'Requires PIT reconstruction, non-micro/capacity, costs, untouched prospective evidence and signed human approval.'
      },
      'claim_boundary':glob.get('claim_limit'),
      'live_decision_weight':0.0,'capital_permission':'BLOCKED'
    }

def attach_research_evidence_v65(desk:dict)->dict:
    if not isinstance(desk,dict): return desk
    out=deepcopy(desk);out['research_evidence_v65']=load_research_evidence_v65();return out
