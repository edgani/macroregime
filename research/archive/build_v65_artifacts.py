from __future__ import annotations
import json, hashlib, csv
from pathlib import Path
ROOT=Path(__file__).resolve().parent
G=json.loads((ROOT/'research_v65/results/V65_GLOBAL_SELECTION_ADJUDICATION_RESULTS.json').read_text())
S=json.loads((ROOT/'research_v65/results/V65_STABILITY_FALSIFICATION_RESULTS.json').read_text())
R=json.loads((ROOT/'COMPONENT_PROOF_REGISTRY_DEFAULT.json').read_text())
claims=[]
for cid in G['hurdle_10bp_survivors']:
    gd=G['details'][cid]; sd=S['details'][cid]
    claims.append({
      'component_id':cid,
      'component_class':'EVIDENCE_ACTIVE_RESEARCH_DECISION_INACTIVE',
      'market_scope':'US listed stocks with standardized option IV; maintained aggregate long-short archive',
      'causal_role':'tail-demand/jump-risk asymmetry plus information-origin underreaction',
      'global_216_10bp_validation_lb_monthly':gd['validation']['0.001']['global_216_simultaneous_lower_bound'],
      'global_216_10bp_lockbox_lb_monthly':gd['lockbox']['0.001']['global_216_simultaneous_lower_bound'],
      'validation_rolling_positive_share':sd['validation']['rolling']['positive_share'],
      'lockbox_rolling_positive_share':sd['lockbox']['rolling']['positive_share'],
      'validation_block_boot_positive_probability':sd['validation']['moving_block_bootstrap']['positive_probability'],
      'lockbox_block_boot_positive_probability':sd['lockbox']['moving_block_bootstrap']['positive_probability'],
      'exact_scope_contract_pass':True,
      '25bp_global_hurdle_pass':False,
      'non_micro_capacity_pass':False,
      'point_in_time_ticker_pass':False,
      'prospective_pass':False,
      'decision_active':False,
      'live_decision_weight':0.0,
      'capital_permission':'BLOCKED'
    })
operational=[
 {'component_id':'data_lineage_and_availability_gate','component_class':'ACTIVE_OPERATIONAL_VALIDATED','proof_scope':'timestamps, vintages, freshness and missing-data fail-closed','decision_active':True,'predictive_semantics':False},
 {'component_id':'market_capability_gate','component_class':'ACTIVE_OPERATIONAL_VALIDATED','proof_scope':'options/non-options and market-specific input contracts','decision_active':True,'predictive_semantics':False},
 {'component_id':'proof_receipt_enforcement','component_class':'ACTIVE_OPERATIONAL_VALIDATED','proof_scope':'exact component/scope/code/data/spec/trial hash and signed capital permission','decision_active':True,'predictive_semantics':False},
 {'component_id':'capital_zero_default','component_class':'ACTIVE_OPERATIONAL_VALIDATED','proof_scope':'no signed prospective proof means zero capital','decision_active':True,'predictive_semantics':False},
 {'component_id':'deterministic_snapshot_and_manifest','component_class':'ACTIVE_OPERATIONAL_VALIDATED','proof_scope':'source mutation detection, manifest and deterministic release integrity','decision_active':True,'predictive_semantics':False},
 {'component_id':'global_trial_accounting','component_class':'ACTIVE_OPERATIONAL_VALIDATED','proof_scope':'candidate registry, correction and negative-result retention','decision_active':True,'predictive_semantics':False},
]
quarantined=[]
for k,v in R['components'].items():
    if k.startswith('smile_') and k.endswith('_v65'): continue
    quarantined.append({'component_id':k,'state':v.get('state'),'scope':v.get('scope'),'decision_active':False,'capital_permission':'BLOCKED'})
kernel={
 'schema':'warroom.v65.proof_first_active_kernel.v1',
 'policy':'No component may affect direction, ranking, target, sizing or capital outside an exact proven contract.',
 'all_active_components_meet_their_own_contract':True,
 'active_operational_components':operational,
 'evidence_active_research_components':claims,
 'decision_active_predictive_components':[],
 'quarantined_predictive_or_descriptive_components':quarantined,
 'counts':{
   'active_operational':len(operational),
   'evidence_active_research':len(claims),
   'decision_active_predictive':0,
   'quarantined':len(quarantined)
 },
 'capital_permission':'BLOCKED',
 'live_decision_weight':0.0,
 'claim_boundary':'The kernel is proof-complete about active scope, not universally predictive. Archive-supported components cannot select tickers or authorize capital.'
}
(ROOT/'V65_PROOF_FIRST_ACTIVE_KERNEL.json').write_text(json.dumps(kernel,indent=2,sort_keys=True)+'\n')
(ROOT/'V65_COMPONENT_PROOF_MATRIX.json').write_text(json.dumps({'schema':'warroom.v65.component_proof_matrix.v1','operational':operational,'research_claims':claims,'quarantined':quarantined},indent=2,sort_keys=True)+'\n')
with (ROOT/'research_v65/ledgers/V65_PROOF_FIRST_ACTIVE_COMPONENT_LEDGER.csv').open('w',newline='') as f:
    fields=['component_id','component_class','decision_active','capital_permission','exact_scope_contract_pass','live_decision_weight']
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for x in operational:w.writerow({'component_id':x['component_id'],'component_class':x['component_class'],'decision_active':x['decision_active'],'capital_permission':'N/A_NON_PREDICTIVE','exact_scope_contract_pass':True,'live_decision_weight':0.0})
    for x in claims:w.writerow({k:x.get(k) for k in fields})
print(json.dumps(kernel['counts'],indent=2))
