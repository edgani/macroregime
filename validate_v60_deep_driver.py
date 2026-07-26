"""Focused source/evidence validation for War Room OS V6.0."""
from __future__ import annotations
import csv, json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def run(name,cmd,timeout=600):
    try:
        p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=timeout)
        return {'name':name,'status':'PASS' if p.returncode==0 else 'FAIL','returncode':p.returncode,'output_tail':(p.stdout+'\n'+p.stderr)[-12000:]}
    except subprocess.TimeoutExpired as e:return {'name':name,'status':'FAIL','returncode':None,'output_tail':f'timeout:{e}'}

def ncsv(path):
    with (ROOT/path).open(newline='',encoding='utf-8') as f:return sum(1 for _ in csv.DictReader(f))

def add(rows,name,ok,detail=''):rows.append({'name':name,'status':'PASS' if ok else 'FAIL','detail':detail})

def main():
    tests=[]
    acct=json.loads((ROOT/'V60_GLOBAL_TRIAL_ACCOUNTING.json').read_text())
    mech=json.loads((ROOT/'research_v60/V60_MECHANISM_UNIVERSE.json').read_text())
    paths=json.loads((ROOT/'research_v60/V60_CAUSAL_PATH_REGISTRY.json').read_text())
    harness=json.loads((ROOT/'research_v60/results/V60_DERIVATIVES_HARNESS_RESULTS.json').read_text())
    early=json.loads((ROOT/'research_v60/results/V60_EARLY_MOVE_DRIVER_RESULTS.json').read_text())
    precursor=json.loads((ROOT/'research_v60/results/V60_MASSIVE_MOVE_PRECURSOR_RESULTS.json').read_text())
    reg=json.loads((ROOT/'COMPONENT_PROOF_REGISTRY_DEFAULT.json').read_text())
    formula=json.loads((ROOT/'FORMULA_AND_SELECTOR_REGISTER.json').read_text())
    src=(ROOT/'mechanical_flow_driver.py').read_text()
    lifecycle=(ROOT/'position_lifecycle.py').read_text()

    add(tests,'trial_accounting_exact',acct['total_empirical_claim_records']==215788,str(acct['total_empirical_claim_records']))
    add(tests,'price_volume_claims_exact',acct['price_volume_extreme_move_claims']==125529,str(acct['price_volume_extreme_move_claims']))
    add(tests,'production_driver_zero',acct['production_proven_early_move_drivers']==0)
    add(tests,'mechanism_primitives',mech['primitive_count']==193,str(mech['primitive_count']))
    add(tests,'causal_paths_registered',paths['path_count']>=50000,str(paths['path_count']))
    add(tests,'early_move_zero_promoted',early['promoted_claims']==0)
    add(tests,'precursor_zero_adjusted_survivor',precursor['counts']['globally_adjusted_diagnostic_survivors']==0)
    add(tests,'harness_pass',harness['status']=='PASS')
    add(tests,'harness_null_zero',harness['checks']['null_has_zero_survivors'])
    add(tests,'liquidation_not_early_control',harness['checks']['realized_liquidation_not_promoted_as_early_driver'])
    add(tests,'oi_explicitly_ambiguous','Every open contract has one long and one short' in src)
    add(tests,'liquidation_timing_boundary','MOVE_UNDERWAY_OR_AMPLIFYING' in src)
    add(tests,'mechanical_nested_in_lifecycle','mechanical_driver' in lifecycle)
    add(tests,'registry_v60',reg.get('version')=='6.0' and 'early_move_driver_research_v60' in reg['components'])
    add(tests,'formula_register_v60',formula.get('version')=='6.0' and 'mechanical_flow_driver_v60' in formula['rules'])
    add(tests,'openap_pair_rows',ncsv('research_v60/ledgers/V60_OPENAP_PAIR_GLOBAL_LEDGER.csv')==89464)
    add(tests,'early_claim_rows',ncsv('research_v60/ledgers/V60_EARLY_MOVE_GLOBAL_TRIAL_LEDGER.csv')==16200)
    add(tests,'relative_winner_rows',ncsv('research_v60/ledgers/V60_RELATIVE_WINNER_GLOBAL_TRIAL_LEDGER.csv')==34322)
    add(tests,'absolute_loser_rows',ncsv('research_v60/ledgers/V60_ABSOLUTE_LOSER_GLOBAL_TRIAL_LEDGER.csv')==34322)

    tests.extend([
      run('mechanical_flow_adversarial',[sys.executable,'test_v60_mechanical_flow.py'],180),
      run('derivatives_harness_controls',[sys.executable,'test_v60_derivatives_harness.py'],240),
      run('v59_regression',[sys.executable,'validate_v59_position_lifecycle.py'],1200),
      run('v58_research_regression',[sys.executable,'validate_v58_exhaustive_research.py'],600),
      run('v42_ui_regression',[sys.executable,'validate_v42_deep_reaudit.py'],900),
      run('compileall',[sys.executable,'-m','compileall','-q','.'],300),
    ])
    report={'schema':'warroom.validation.v60.deep_driver','status':'PASS' if all(x['status']=='PASS' for x in tests) else 'FAIL','tests_passed':sum(x['status']=='PASS' for x in tests),'tests_total':len(tests),'live_predictive_components_promoted':0,'capital_permission':'BLOCKED','tests':tests}
    (ROOT/'V60_SOURCE_VALIDATION.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2))
    if report['status']!='PASS':
        for x in tests:
            if x['status']!='PASS':print(json.dumps(x,indent=2))
    return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
