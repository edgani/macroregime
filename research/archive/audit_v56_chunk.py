"""Fresh-copy audit chunks for v5.6 signed-dealer continuation."""
from __future__ import annotations
import hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
STATE=ROOT/'audit_state_v56';STATE.mkdir(exist_ok=True)
IGNORE_DIRS={'__pycache__','.git','.cache','.pytest_cache','runtime','audit_logs','.venv','audit_state_v55','audit_state_v56'}
GEN_PREFIX=('V42_','V52_','V53_','V55_','V56_','V70_','V71_','V72_','PACKAGE_MANIFEST_')

def h(p):
 x=hashlib.sha256();x.update(p.read_bytes());return x.hexdigest()
def manifest(root):
 out={}
 for p in sorted(root.rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(root);s=rel.as_posix()
  if any(x in IGNORE_DIRS for x in rel.parts) or p.suffix.lower() in {'.pyc','.tmp','.log'}:continue
  if p.name.startswith(GEN_PREFIX) and not s.startswith(('research_v55/','research_v56/')):continue
  if p.suffix.lower()=='.json' and not s.startswith(('research_v55/','research_v56/')):continue
  if p.suffix.lower() in {'.py','.html','.md','.txt','.csv','.parquet','.yaml','.yml','.toml','.bat'} or s.startswith(('research_v55/','research_v56/')):out[s]=h(p)
 return out
def copy(dst):
 def ign(_d,n):return {x for x in n if x in IGNORE_DIRS or x.endswith(('.pyc','.tmp'))}
 shutil.copytree(ROOT,dst,ignore=ign,dirs_exist_ok=True)
SPECS={
 'compile':([sys.executable,'-m','compileall','-q','.'],180,set()),
 'hardening39':([sys.executable,'hardening_tests/test_hardening_v52.py'],300,set()),
 'continuation11':([sys.executable,'hardening_tests/test_attachment_continuation_v53.py'],180,set()),
 'options29':([sys.executable,'hardening_tests/test_options_gamma_v70.py'],240,set()),
 'prospective19':([sys.executable,'hardening_tests/test_options_prospective_v71.py'],240,set()),
 'signed_dealer43':([sys.executable,'hardening_tests/test_signed_dealer_v72.py'],300,set()),
 'outcome11':([sys.executable,'hardening_tests/test_v72_outcome_evaluator.py'],300,set()),
 'runner19':([sys.executable,'hardening_tests/test_v72_release_runners.py'],300,set()),
 'manifest14':([sys.executable,'hardening_tests/test_v72_manifest_generators.py'],300,set()),
 'parquet36':([sys.executable,'hardening_tests/test_parquet_compat_v55.py'],300,set()),
 'gcfis':([sys.executable,'gcfis/tests/test_all.py'],360,set()),
 'deep':([sys.executable,'validate_v42_deep_reaudit.py'],600,set()),
 'live_options':([sys.executable,'validate_live_stack.py'],300,set()),
 'bundled':([sys.executable,'validate_bundled_data_v52.py'],300,set()),
 'synthetic':([sys.executable,'run.py','--synthetic','--markets','us,idx,crypto,commodity,fx','--out','runtime/v56_desk.json','--html','runtime/v56_dashboard.html'],480,set()),
 'controls':([sys.executable,'validation_plus.py'],300,set()),
 'component':([sys.executable,'component_validation.py'],600,set()),
 'composition':([sys.executable,'composition_audit.py'],600,set()),
 'filter':([sys.executable,'filter_validation.py'],600,set()),
 'real':([sys.executable,'validate_real.py'],900,set()),
 'gem':([sys.executable,'gem_validation.py'],600,set()),
 'alpha':([sys.executable,'alpha_discovery_test.py'],900,set()),
 'streamlit':([sys.executable,'validate_streamlit_health_v52.py'],180,{2}),
}
def main(names):
 with tempfile.TemporaryDirectory(prefix='v56_chunk_') as td:
  work=Path(td)/'pkg';copy(work)
  for name in names:
   cmd,timeout,blocked=SPECS[name];before=manifest(work)
   env=os.environ.copy();env.update({'PYTHONWARNINGS':'error','PYTHONDONTWRITEBYTECODE':'1','WARROOM_DISABLE_AUTOSTART':'1','TERM':'xterm'})
   try:
    p=subprocess.run(cmd,cwd=work,env=env,capture_output=True,text=True,timeout=timeout);rc=p.returncode;status='BLOCKED_BY_ENVIRONMENT' if rc in blocked else 'PASS' if rc==0 else 'FAIL';tail=(p.stdout+'\n'+p.stderr)[-12000:]
   except subprocess.TimeoutExpired as e:rc=None;status='FAIL';tail=f'timeout {timeout}: {e}'
   after=manifest(work);mut=sorted(set(k for k,v in before.items() if after.get(k)!=v)|set(before)-set(after)|set(after)-set(before))
   if mut:status='FAIL'
   row={'name':name,'status':status,'returncode':rc,'source_immutable':not mut,'mutated_paths':mut,'output_tail':tail}
   (STATE/f'{name}.json').write_text(json.dumps(row,indent=2,sort_keys=True)+'\n')
   print(json.dumps({k:row[k] for k in ('name','status','returncode','source_immutable')},sort_keys=True),flush=True)
 return 0
if __name__=='__main__':raise SystemExit(main(sys.argv[1:]))
