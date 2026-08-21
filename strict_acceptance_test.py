from pathlib import Path
import json, subprocess, sys, re, pandas as pd
ROOT=Path(__file__).resolve().parent; OUT=ROOT/'FINAL_HANDOFF'
checks=[]
def ck(name,cond,detail=''): checks.append({'check':name,'pass':bool(cond),'detail':detail})
def runpy(path):
 p=subprocess.run([sys.executable,str(path)],cwd=ROOT,env={**__import__('os').environ,'PYTHONPATH':str(ROOT)},capture_output=True,text=True)
 return p.returncode,p.stdout[-3000:],p.stderr[-3000:]
# executable tests
for name,path in [('attachment_scenarios',ROOT/'tests/test_scenario_acceptance.py'),('general_scenarios',ROOT/'tests/test_general_scenario_discovery.py'),('attachment_router',ROOT/'tests/test_event_router.py'),('general_router',ROOT/'tests/test_event_router_general.py'),('ticker_fail_closed',ROOT/'tests/test_ticker_fail_closed.py')]:
 rc,so,se=runpy(path); ck(name,rc==0,(so+se).strip())
ck('multi_engine_validation_artifact_exists',(OUT/'51_MULTI_ENGINE_VALIDATION_SUMMARY.json').exists())
rc,so,se=runpy(ROOT/'final_core/production_entry.py');ck('production_entry_executes',rc==0,(so+se).strip())
# factual/multi-engine
summ=json.loads((OUT/'51_MULTI_ENGINE_VALIDATION_SUMMARY.json').read_text());ck('multi_engine_count>=8',summ.get('engine_count',0)>=8,str(summ.get('engine_count')));ck('production_proven_not_fabricated',summ.get('production_proven_count')==0)
cov=pd.read_csv(OUT/'04_FACTUAL_DATA_COVERAGE.csv');ready=(cov.self_run_status.astype(str).str.startswith('FACTUAL')).sum(); debt=(cov.self_run_status=='DATA_DEBT_NOT_INGESTED').sum();ck('factual_snapshot_coverage_present',ready>=10,f'ready_or_scope={ready}');
# generalized discovery really outside attachments
ck('generalized_scenario_case_count>=8','GENERAL_SCENARIO_DISCOVERY: PASS 8' in next(x['detail'] for x in checks if x['check']=='general_scenarios'))
# source safety / no numeric production probabilities in scenario engine
src=(ROOT/'final_core/scenario_discovery.py').read_text();ck('scenario_probabilities_fail_closed','probability=None' in src and 'UNKNOWN_UNCALIBRATED' in src)
tick=(ROOT/'final_core/ticker_engine.py').read_text();ck('ticker_missing_data_no_rank','MISSING_REQUIRED_EVIDENCE' in tick and 'UNCALIBRATED_PROBABILITIES' in tick)
# five-tab UI and portability
html=(ROOT/'dashboard.html').read_text();ck('five_tab_ui',all(x in html for x in ['Command Center','Global Explorer','Opportunity Engine','Portfolio','Research Lab']))
allpy='\n'.join(p.read_text(errors='ignore') for p in ROOT.rglob('*.py'));bad='/mnt/data/'+'EROS_SELF_FINAL'; ck('no_old_absolute_self_path',bad not in allpy)
# current run must not fabricate ticker
cur=json.loads((OUT/'52_CURRENT_PRODUCTION_RUN.json').read_text());ck('current_no_fabricated_ticker',cur['current_action']=='NO_QUALIFIED_OPPORTUNITY' and len(cur['qualified_opportunities'])==0)
software_pass=all(x['pass'] for x in checks)
full_scope_blockers=[]
if debt: full_scope_blockers.append(f'{debt} dataset requirements remain DATA_DEBT_NOT_INGESTED')
if summ.get('production_proven_count',0)==0: full_scope_blockers.append('0 production-proven cross-market scientific models')
full_scope_blockers += ['IHSG/crypto/FX full PIT outcome panels not available in runtime','modern PIT company fundamentals + historical return ranker validation not complete','scenario probability/timing/duration calibration remains prospective/data-dependent']
res={'software_acceptance':'PASS' if software_pass else 'FAIL','scientific_full_scope_acceptance':'BLOCKED_DATA_DEBT' if full_scope_blockers else 'PASS','release_status':'FINAL_SOFTWARE_SCOPE_LIMITED' if software_pass else 'NOT_RELEASEABLE','checks':checks,'factual_rows_scope_ready':int(ready),'data_debt_rows':int(debt),'multi_engine_count':summ.get('engine_count'),'full_scope_blockers':full_scope_blockers}
(OUT/'100_STRICT_ACCEPTANCE_RESULT.json').write_text(json.dumps(res,indent=2),encoding='utf-8')
print(json.dumps(res,indent=2));sys.exit(0 if software_pass else 1)
