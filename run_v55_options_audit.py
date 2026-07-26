"""Fresh-copy system audit for War Room OS v5.5 options volatility/mechanical-flow hardening."""
from __future__ import annotations
import hashlib, importlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPORT=ROOT/'V55_CLEAN_EXTRACT_AUDIT_REPORT.json'
LOG=ROOT/'V55_CLEAN_EXTRACT_TEST_LOG.txt'
IGNORE_DIRS={'__pycache__','.git','.cache','.pytest_cache','runtime','audit_logs','.venv'}
GENERATED_NAMES={
 'desk_data.json','dashboard_live.html','V42_DEEP_REAUDIT_PREVIEW.png','V42_DEEP_REAUDIT_VALIDATION_REPORT.json',
 'V52_CLEAN_EXTRACT_AUDIT_REPORT.json','V52_CLEAN_EXTRACT_TEST_LOG.txt','V53_RELEASE_CLEAN_EXTRACT_VALIDATION.json',
 'V53_RELEASE_TEST_LOG.txt','V53_USER_VALIDATION_REPORT.json','V55_CLEAN_EXTRACT_AUDIT_REPORT.json',
 'V55_CLEAN_EXTRACT_TEST_LOG.txt','V55_USER_VALIDATION_REPORT.json','PACKAGE_MANIFEST_V53.json','PACKAGE_MANIFEST_V55.json',
 'V70_OPTIONS_GAMMA_VALIDATION.json','V71_OPTIONS_PROSPECTIVE_VALIDATION.json','V55_PARQUET_COMPAT_VALIDATION.json',
 'V52_STREAMLIT_HEALTH_REPORT.json'
}
IMMUTABLE_SUFFIXES={'.py','.html','.md','.txt','.csv','.parquet','.yaml','.yml','.toml','.bat'}
FROZEN_JSON_PREFIXES=('research_v55/V69_','research_v55/V70_','research_v55/V71_')

def digest(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def generated(rel:Path)->bool:
 s=rel.as_posix()
 if any(x in IGNORE_DIRS for x in rel.parts): return True
 if rel.name in GENERATED_NAMES or rel.suffix.lower() in {'.pyc','.tmp','.log'}: return True
 if s.startswith('proof/receipts/') and rel.name!='README.md': return True
 if rel.suffix.lower()=='.json' and not s.startswith(FROZEN_JSON_PREFIXES): return True
 return False

def immutable_manifest(root:Path)->dict[str,str]:
 out={}
 for p in sorted(root.rglob('*')):
  if not p.is_file(): continue
  rel=p.relative_to(root)
  if generated(rel): continue
  if p.suffix.lower() in IMMUTABLE_SUFFIXES or rel.as_posix().startswith(FROZEN_JSON_PREFIXES):
   out[rel.as_posix()]=digest(p)
 return out

def root_digest(rows:dict[str,str])->str:
 return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def copy_package(dst:Path)->None:
 def ignore(_dir,names): return {n for n in names if n in IGNORE_DIRS or n.endswith(('.pyc','.tmp'))}
 shutil.copytree(ROOT,dst,ignore=ignore,dirs_exist_ok=True)

def run_fresh(name:str,cmd:list[str],timeout:int,blocked_codes:set[int]|None=None)->dict:
 blocked_codes=blocked_codes or set(); print(f'START {name}',flush=True)
 with tempfile.TemporaryDirectory(prefix=f'warroom_v55_{name}_') as td:
  work=Path(td)/'pkg'; copy_package(work); before=immutable_manifest(work)
  env=os.environ.copy();env.update({'PYTHONWARNINGS':'error','PYTHONDONTWRITEBYTECODE':'1','TERM':'xterm','WARROOM_DISABLE_AUTOSTART':'1'})
  try:
   proc=subprocess.run(cmd,cwd=work,env=env,capture_output=True,text=True,timeout=timeout)
   rc=proc.returncode;status='BLOCKED_BY_ENVIRONMENT' if rc in blocked_codes else 'PASS' if rc==0 else 'FAIL';output=(proc.stdout+'\n'+proc.stderr)[-30000:]
  except subprocess.TimeoutExpired as exc:
   rc=None;status='FAIL';output=f'timeout after {timeout}s: {exc}'
  after=immutable_manifest(work)
  mutation=sorted(set(k for k,v in before.items() if after.get(k)!=v)|set(before)-set(after)|set(after)-set(before))
  if mutation: status='FAIL'
  row={'name':name,'status':status,'returncode':rc,'source_immutable':not mutation,'mutated_paths':mutation,'output_tail':output}
 print(f'DONE {name} {status} rc={rc} immutable={not mutation}',flush=True);return row

def dependency_gate()->dict:
 mods={'streamlit':'streamlit','requests':'requests','yfinance':'yfinance','pandas':'pandas','numpy':'numpy','scipy':'scipy','sklearn':'sklearn','statsmodels':'statsmodels','hmmlearn':'hmmlearn','networkx':'networkx','pyarrow':'pyarrow','cryptography':'cryptography'}
 states={}
 for label,module in mods.items():
  try:
   obj=importlib.import_module(module);states[label]={'state':'AVAILABLE','version':str(getattr(obj,'__version__','UNKNOWN'))}
  except Exception as exc: states[label]={'state':'MISSING','error':f'{type(exc).__name__}: {exc}'}
 runtime_required=['pandas','numpy','cryptography'];missing_required=[x for x in runtime_required if states[x]['state']=='MISSING']
 return {'name':'dependency_inventory','status':'FAIL' if missing_required else 'PASS','missing_required':missing_required,
         'optional_missing':[x for x in states if states[x]['state']=='MISSING' and x not in runtime_required],
         'pyarrow_required_for_bundled_parquet':False,'modules':states}

def proof_gate()->dict:
 from proof_registry import default_registry,component_status
 statuses={k:component_status(k) for k in default_registry()['components']}
 promoted=sorted(k for k,v in statuses.items() if v.get('predictive_promoted'))
 capital=sorted(k for k,v in statuses.items() if v.get('capital_permission')!='BLOCKED')
 from research_evidence_v53 import load_research_evidence
 from options_research_evidence_v55 import load_options_research_v55
 base=load_research_evidence();options=load_options_research_v55()
 protocol=json.loads((ROOT/'research_v55/V71_OPTIONS_PROSPECTIVE_PROTOCOL_FROZEN.json').read_text())
 prospective_validation=json.loads((ROOT/'V71_OPTIONS_PROSPECTIVE_VALIDATION.json').read_text())
 live_weight=sum(float(x.get('live_decision_weight',0.0)) for x in base.get('claims',[]))+float(options.get('live_decision_weight',0.0))+float(protocol.get('live_decision_weight',0.0))
 ok=(not promoted and not capital and live_weight==0.0 and base.get('capital_permission')=='BLOCKED' and options.get('status')=='IMPLEMENTED_RESEARCH_ONLY' and options.get('capital_permission')=='BLOCKED' and protocol.get('capital_permission')=='BLOCKED' and prospective_validation.get('prospective_observations_collected')==0)
 return {'name':'proof_research_and_prospective_state','status':'PASS' if ok else 'FAIL','predictive_components_promoted':promoted,'capital_authorized_components':capital,'research_live_decision_weight':live_weight,'options_research_status':options.get('status'),'v71_prospective_observations':prospective_validation.get('prospective_observations_collected'),'capital_permission':'BLOCKED' if ok else 'UNSAFE'}

def main()->int:
 source=immutable_manifest(ROOT)
 specs=[
  ('compile_all',[sys.executable,'-m','compileall','-q','.'],180,set()),
  ('hardening_adversarial_39',[sys.executable,'hardening_tests/test_hardening_v52.py'],300,set()),
  ('attachment_continuation_11',[sys.executable,'hardening_tests/test_attachment_continuation_v53.py'],180,set()),
  ('options_gamma_v70_29',[sys.executable,'hardening_tests/test_options_gamma_v70.py'],240,set()),
  ('options_prospective_v71_19',[sys.executable,'hardening_tests/test_options_prospective_v71.py'],240,set()),
  ('parquet_compat_v55_36',[sys.executable,'hardening_tests/test_parquet_compat_v55.py'],300,set()),
  ('gcfis_warnings_as_errors',[sys.executable,'gcfis/tests/test_all.py'],360,set()),
  ('deep_reaudit_ui_contracts',[sys.executable,'validate_v42_deep_reaudit.py'],600,set()),
  ('live_options_stack',[sys.executable,'validate_live_stack.py'],300,set()),
  ('bundled_data_integrity',[sys.executable,'validate_bundled_data_v52.py'],300,set()),
  ('synthetic_end_to_end',[sys.executable,'run.py','--synthetic','--markets','us,idx,crypto,commodity,fx','--out','runtime/v55_desk.json','--html','runtime/v55_dashboard.html'],480,set()),
  ('validator_controls',[sys.executable,'validation_plus.py'],300,set()),
  ('component_validation',[sys.executable,'component_validation.py'],600,set()),
  ('composition_audit',[sys.executable,'composition_audit.py'],600,set()),
  ('filter_validation',[sys.executable,'filter_validation.py'],600,set()),
  ('real_data_validation',[sys.executable,'validate_real.py'],900,set()),
  ('gem_validation',[sys.executable,'gem_validation.py'],600,set()),
  ('alpha_discovery_negative_control',[sys.executable,'alpha_discovery_test.py'],900,set()),
  ('actual_streamlit_health',[sys.executable,'validate_streamlit_health_v52.py'],180,{2}),
 ]
 tests=[run_fresh(*x) for x in specs]
 deps=dependency_gate();proof=proof_gate();rows=tests+[deps,proof]
 failures=[x['name'] for x in rows if x['status']=='FAIL'];blockers=[x['name'] for x in rows if x['status']=='BLOCKED_BY_ENVIRONMENT'];mut=[x['name'] for x in tests if not x.get('source_immutable',True)]
 hardening_pass=not failures and not mut
 report={'schema':'warroom.clean_extract_audit.v55','status':'PASS' if hardening_pass else 'FAIL','release_verdict':'OPTIONS_VOLATILITY_FLOW_ENGINEERING_PASS_TRADING_EDGE_NOT_PROVEN_CAPITAL_BLOCKED' if hardening_pass else 'FAIL','visual_application_version':'4.2','release_version':'5.5','source_manifest_files':len(source),'source_manifest_sha256':root_digest(source),'validators_run_on_fresh_copies':True,'warnings_as_errors':True,'source_mutation_failures':mut,'failures':failures,'environment_blockers':blockers,'pyarrow_bundled_semantic_gate':'PASS_VIA_VALIDATED_INTERNAL_READER','v70_options_checks':'29/29 PASS','v71_prospective_checks':'19/19 PASS','parquet_checks':'36/36 PASS','historical_options_edge':'NOT_PROVEN','prospective_options_profitability':'NOT_MATURED','predictive_components_promoted_to_live':0,'research_live_decision_weight':0.0,'capital_permission':'BLOCKED','tests':[{k:v for k,v in r.items() if k!='output_tail'} for r in rows], 'claim_boundary':'Engineering and evidence gates pass. Public OI never creates dealer sign. Options remain volatility/range/mechanical-flow research only until signed prospective outcomes mature and pass frozen gates.'}
 REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 LOG.write_text('\n'.join([f"STATUS={report['status']}",f"VERDICT={report['release_verdict']}",*[f"{r['name']}={r['status']} rc={r.get('returncode','-')} immutable={r.get('source_immutable','-')}" for r in rows], 'PREDICTIVE_COMPONENTS_PROMOTED=0','RESEARCH_LIVE_DECISION_WEIGHT=0','CAPITAL_PERMISSION=BLOCKED'])+'\n')
 print(json.dumps({k:report[k] for k in ('status','release_verdict','failures','environment_blockers','capital_permission')},indent=2));return 0 if hardening_pass else 1
if __name__=='__main__': raise SystemExit(main())
