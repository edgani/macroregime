from __future__ import annotations
import json, hashlib
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parent; O=ROOT/'research_v60'
checks=[]
def ck(name,cond,detail=''):checks.append({'name':name,'status':'PASS' if cond else 'FAIL','detail':str(detail)})
try:
 s=json.load(open(O/'results/V62_UNIFIED_GLOBAL_RESULTS.json'));g=json.load(open(O/'results/V62_CAUSAL_DISCOVERY_GRAMMAR.json'));m=json.load(open(O/'results/V60_MASSIVE_MOVE_RESULTS.json'));a=json.load(open(O/'results/V60_ALTERNATE_TARGETS_RESULTS.json'));p=json.load(open(O/'results/V60_OPENAP_PAIR_RESULTS.json'));r=json.load(open(O/'results/V61_OPENAP_PAIR_ROBUSTNESS_RESULTS.json'))
except Exception as e:
 print(json.dumps({'status':'FAIL','error':repr(e)},indent=2));raise SystemExit(1)
ck('new_trial_count_192430',s['new_trials_registered']==192430,s['new_trials_registered'])
ck('cumulative_trial_count_193225',s['cumulative_empirical_trial_count']==193225,s['cumulative_empirical_trial_count'])
ck('absolute_winner_zero_full_gate',m['full_gate_survivors']==0,m['full_gate_survivors'])
# alternate summary may only contain absolute loser if interrupted; validate ledgers directly
rw=pd.read_csv(O/'ledgers/V60_RELATIVE_WINNER_GLOBAL_TRIAL_LEDGER.csv');dl=pd.read_csv(O/'ledgers/V60_ABSOLUTE_LOSER_GLOBAL_TRIAL_LEDGER.csv')
ck('relative_winner_34322',len(rw)==34322,len(rw));ck('relative_winner_zero_gate',rw.passes_full_gate.astype(str).str.lower().isin(['true','1']).sum()==0)
ck('absolute_loser_34322',len(dl)==34322,len(dl));ck('absolute_loser_zero_gate',dl.passes_full_gate.astype(str).str.lower().isin(['true','1']).sum()==0)
ck('openap_pair_89464',p['registered']==89464,p['registered'])
ck('strict_robustness_61',r['gate_attrition']['strict_survivors']==61,r['gate_attrition']['strict_survivors'])
ck('unified_research_candidates_25',s['research_candidate_only_after_all_available_stresses']==25,s['research_candidate_only_after_all_available_stresses'])
uni=pd.read_csv(O/'ledgers/V62_UNIFIED_GLOBAL_TRIAL_LEDGER.csv');ck('unified_ledger_192430',len(uni)==192430,len(uni));ck('all_live_weight_zero',(uni.live_decision_weight==0).all());ck('all_capital_blocked',(uni.capital_permission=='BLOCKED').all())
ck('grammar_868',g['base_candidates']==868,g['base_candidates']);ck('grammar_single_5155920',g['single_claim_potential']==5155920,g['single_claim_potential']);ck('grammar_no_live',g['current_live_promotions']==0);ck('registry_v60',json.load(open(ROOT/'COMPONENT_PROOF_REGISTRY_DEFAULT.json'))['version']=='6.0')
status='PASS' if all(x['status']=='PASS' for x in checks) else 'FAIL';out={'schema':'warroom.validation.v60.exhaustive_causal_discovery','status':status,'passed':sum(x['status']=='PASS' for x in checks),'failed':sum(x['status']=='FAIL' for x in checks),'checks':checks,'predictive_components_promoted_to_live':0,'capital_permission':'BLOCKED'};(ROOT/'V60_EXHAUSTIVE_CAUSAL_DISCOVERY_VALIDATION.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2));raise SystemExit(0 if status=='PASS' else 1)
