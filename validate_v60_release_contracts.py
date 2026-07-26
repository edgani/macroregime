"""Fast immutable artifact/contract validation for a released V6.0 package."""
from __future__ import annotations
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def n(path):
 with (ROOT/path).open(newline='',encoding='utf-8') as f:return sum(1 for _ in csv.DictReader(f))
def main():
 checks=[]
 def add(name,ok,detail=''):checks.append({'name':name,'status':'PASS' if ok else 'FAIL','detail':detail})
 a=json.loads((ROOT/'V60_GLOBAL_TRIAL_ACCOUNTING.json').read_text())
 h=json.loads((ROOT/'research_v60/results/V60_DERIVATIVES_HARNESS_RESULTS.json').read_text())
 m=json.loads((ROOT/'research_v60/V60_MECHANISM_UNIVERSE.json').read_text())
 p=json.loads((ROOT/'research_v60/V60_CAUSAL_PATH_REGISTRY.json').read_text())
 r=json.loads((ROOT/'COMPONENT_PROOF_REGISTRY_DEFAULT.json').read_text())
 add('total_claim_records',a['total_empirical_claim_records']==215788,str(a['total_empirical_claim_records']))
 add('price_volume_zero_live',a['price_volume_extreme_move_claims']==125529 and a['production_proven_early_move_drivers']==0)
 add('openap_ledger',n('research_v60/ledgers/V60_OPENAP_PAIR_GLOBAL_LEDGER.csv')==89464)
 add('early_ledger',n('research_v60/ledgers/V60_EARLY_MOVE_GLOBAL_TRIAL_LEDGER.csv')==16200)
 add('mechanism_universe',m['primitive_count']==193)
 add('causal_paths',p['path_count']==55496)
 add('harness',h['status']=='PASS' and all(h['checks'].values()))
 add('registry_capital_blocked',r['components']['early_move_driver_research_v60']['capital_permission']=='BLOCKED')
 report={'schema':'warroom.validation.v60.release_contracts','status':'PASS' if all(x['status']=='PASS' for x in checks) else 'FAIL','tests_passed':sum(x['status']=='PASS' for x in checks),'tests_total':len(checks),'tests':checks}
 print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
