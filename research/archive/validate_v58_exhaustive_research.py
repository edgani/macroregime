"""Fail-closed integrity validation for V5.8 exhaustive research accounting."""
from __future__ import annotations
import hashlib, json, math, sys
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parent
RV=ROOT/'research_v58'
checks=[]
def ck(name, cond, detail=''):
    checks.append({'name':name,'status':'PASS' if bool(cond) else 'FAIL','detail':detail})
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def load(rel): return json.loads((ROOT/rel).read_text(encoding='utf-8'))

univ=load('research_v58/V58_RESEARCH_UNIVERSE.json')
readiness=load('research_v58/V58_DATA_READINESS_MATRIX.json')
ledger=load('research_v58/ledgers/V58_GLOBAL_TRIAL_LEDGER.json')
openap=load('research_v58/results/V58_OPENAP_212_POSTSAMPLE_RESULTS.json')
public=load('research_v58/results/V58_PUBLIC_FACTOR_POSTSAMPLE_RESULTS.json')
pv=load('research_v58/results/V58_PRICE_VOLUME_SWEEP_RESULTS.json')
macro=load('research_v58/results/V58_MACRO_SWEEP_RESULTS.json')
queue=load('research_v58/V59_SURVIVOR_REPLICATION_QUEUE.json')
acq=load('research_v58/V58_PLACEBO_ALT_PORTS_ACQUISITION_STATUS.json')
untested=load('research_v58/V60_ALL_UNTESTED_ACQUISITION_QUEUE.json')
registry=load('research_evidence_registry_v53.json')

ck('universe_count_868', univ['summary']['candidate_count']==868)
ck('universe_literal_completeness_false', univ['summary']['governance']['literal_world_completeness_claimed'] is False)
ck('signal_class_counts', univ['summary']['signal_class_counts']=={'PREDICTOR':212,'PLACEBO':114,'DROP':5}, str(univ['summary']['signal_class_counts']))
ck('universe_zero_live', all(float(x.get('live_decision_weight',9))==0 for x in univ['candidates']))
ck('universe_capital_blocked', all(x.get('capital_permission')=='BLOCKED' for x in univ['candidates']))
ck('readiness_count', readiness['candidate_count']==868 and len(readiness['rows'])==868)

study_expected={'V58_OPENAP_212_POSTSAMPLE':212,'V58_PUBLIC_FACTOR_POSTSAMPLE':39,'V58_PRICE_VOLUME_SWEEP':200,'V58_MACRO_SWEEP':344}
ck('global_registered_795', ledger['registered_claims_in_v58_batteries']==795 and len(ledger['rows'])==795)
ck('study_counts_exact', all(ledger['study_counts'][k]['registered']==v for k,v in study_expected.items()), str(ledger['study_counts']))
ck('study_result_claim_counts', len(openap['claims'])==212 and len(public['claims'])==39 and len(pv['claims'])==200 and len(macro['claims'])==344)
ck('global_gross_exact_three', ledger['global_gross_survivors']==['AnalystRevision','AnnouncementReturn','DivYieldST'], str(ledger['global_gross_survivors']))
ck('global_25bps_none', ledger['global_25bps_survivors']==[])
ck('global_narrative_matches_count', 'three OpenAP global-gross survivors' in ledger['important_boundary'])
ck('ledger_zero_live', all(float(r.get('live_decision_weight',9))==0 for r in ledger['rows']))
ck('ledger_capital_blocked', all(r.get('capital_permission')=='BLOCKED' for r in ledger['rows']))
ck('ledger_no_live_promotion', ledger['predictive_components_promoted_to_live']==0 and ledger['research_live_decision_weight']==0)

hashdoc=load('research_v58/ledgers/V58_GLOBAL_TRIAL_LEDGER.sha256.json')
ck('ledger_hash_matches', hashdoc['ledger_sha256']==sha(RV/'ledgers/V58_GLOBAL_TRIAL_LEDGER.json'), f"expected={hashdoc['ledger_sha256']} actual={sha(RV/'ledgers/V58_GLOBAL_TRIAL_LEDGER.json')}")
ck('ledger_csv_hash_matches', hashdoc['ledger_csv_sha256']==sha(RV/'ledgers/V58_GLOBAL_TRIAL_LEDGER.csv'))
ck('readiness_hash_matches', hashdoc['readiness_sha256']==sha(RV/'V58_DATA_READINESS_MATRIX.json'))
for src in hashdoc['sources']:
    p=RV/'data'/src['file']
    ck('source_hash_'+src['file'], p.exists() and sha(p)==src['sha256'])

ck('queue_exact_three', queue['queue_order']==['AnnouncementReturn','AnalystRevision','DivYieldST'])
ck('queue_source_hash_matches', queue['source_v58_ledger_sha256']==hashdoc['ledger_sha256'])
ck('queue_zero_live', all(float(x['live_decision_weight'])==0 and x['capital_permission']=='BLOCKED' for x in queue['claims']))
ck('announcement_bias_controls_present', any('earnings date revisions' in x for x in queue['claims'][0]['critical_bias_tests']))
ck('placebo_defs_accounted', acq['requested_negative_controls']['placebo_definitions']==114 and acq['requested_negative_controls']['drop_definitions']==5)
ck('placebo_returns_not_fabricated', acq['research_consequence']['placebo_return_trials_added']==0)
ck('alt_construction_not_fabricated', acq['research_consequence']['alternative_construction_trials_added']==0)
ck('acquisition_capital_blocked', acq['capital_permission']=='BLOCKED' and acq['live_decision_weight']==0)
ck('untested_queue_count_656', untested['candidate_count']==656 and len(untested['rows'])==656)
ck('untested_queue_zero_live', all(float(x['live_decision_weight'])==0 and x['capital_permission']=='BLOCKED' for x in untested['rows']))
ck('untested_queue_covers_placebo_drop', untested['accessibility_tier_counts'].get('A_OFFICIAL_SIGNAL_FILES_OR_WRDS')==119)

v58reg=registry['v58_exhaustive_research']
ck('registry_counts', v58reg['mapped_candidates']==868 and v58reg['registered_claims']==795)
ck('registry_survivors', v58reg['global_795_gross_survivors']==['AnnouncementReturn','AnalystRevision','DivYieldST'] and v58reg['global_795_25bps_survivors']==[])
ck('registry_hash_matches', v58reg['trial_ledger_sha256']==hashdoc['ledger_sha256'], f"registry={v58reg['trial_ledger_sha256']} ledger={hashdoc['ledger_sha256']}")
ck('registry_queue_hash_matches', v58reg['replication_queue_sha256']==sha(RV/'V59_SURVIVOR_REPLICATION_QUEUE.json'))
ck('registry_zero_live', registry['predictive_components_promoted_to_live']==0 and registry['research_live_decision_weight']==0 and registry['capital_permission']=='BLOCKED')

fails=[x for x in checks if x['status']=='FAIL']
out={'schema':'warroom.v58_exhaustive_validation','status':'PASS' if not fails else 'FAIL','checks':checks,'passed':len(checks)-len(fails),'failed':len(fails),'capital_permission':'BLOCKED','predictive_components_promoted_to_live':0}
(ROOT/'V58_EXHAUSTIVE_RESEARCH_VALIDATION.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
raise SystemExit(0 if not fails else 1)
