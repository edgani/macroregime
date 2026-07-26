"""Strict deterministic manifest verifier for War Room OS V6.0."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/'PACKAGE_MANIFEST_V60.json'
IGNORE_DIRS={'.git','.venv','__pycache__','.cache','.pytest_cache','audit_logs','runtime','audit_state_v55','audit_state_v56','audit_state_v57','audit_state_v58','audit_state_v59','audit_state_v60'}
IGNORE_EXACT={
 'PACKAGE_MANIFEST_V58.json','PACKAGE_MANIFEST_V59.json','PACKAGE_MANIFEST_V60.json',
 'V59_USER_VALIDATION_REPORT.json','V59_SOURCE_VALIDATION.json','V60_USER_VALIDATION_REPORT.json','V60_SOURCE_VALIDATION.json','V60_FINAL_ZIP_VALIDATION.json',
 'desk_data.json','dashboard_live.html','V42_DEEP_REAUDIT_PREVIEW.png','V42_DEEP_REAUDIT_VALIDATION_REPORT.json',
 'runtime/desk_snapshot.json','runtime/worker_status.json','runtime/force_refresh.flag','runtime/worker.instance.lock','runtime/worker.pid','runtime/worker_boot.log','runtime/worker.log',
 'static/desk_snapshot.json','static/worker_status.json','V52_HARDENING_ADVERSARIAL_REPORT.json','V52_BUNDLED_DATA_INTEGRITY_REPORT.json',
 'V55_PARQUET_COMPAT_VALIDATION.json','V70_OPTIONS_GAMMA_VALIDATION.json','V71_OPTIONS_PROSPECTIVE_VALIDATION.json','V72_SIGNED_DEALER_VALIDATION.json',
 'V72_OUTCOME_EVALUATOR_VALIDATION.json','V72_RELEASE_RUNNER_VALIDATION.json','V72_MANIFEST_GENERATOR_VALIDATION.json'}
IGNORE_SUFFIXES={'.pyc','.tmp','.log'}
def sha256(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def ignored(rel):
 s=rel.as_posix()
 return any(x in IGNORE_DIRS for x in rel.parts) or s in IGNORE_EXACT or rel.suffix.lower() in IGNORE_SUFFIXES or (s.startswith('proof/receipts/') and rel.name!='README.md') or (rel.name.startswith('.') and s not in {'.env.example','.streamlit/config.toml','runtime/.gitkeep','static/.gitkeep'})
def release_files(root=ROOT):
 return {p.relative_to(root).as_posix():p for p in sorted(root.rglob('*')) if p.is_file() and not ignored(p.relative_to(root))}
def verify(root=ROOT,manifest_path=None):
 mp=manifest_path or root/MANIFEST.name;out={'status':'FAIL','errors':[],'checked_files':0,'manifest_files':0}
 try:raw=json.loads(mp.read_text())
 except Exception as e:out['errors'].append(f'manifest unreadable:{type(e).__name__}:{e}');return out
 if raw.get('schema')!='warroom.package_manifest.v60':out['errors'].append('manifest schema mismatch')
 rows=raw.get('files') or [];expected={}
 for row in rows:
  rel=str(row.get('path') or '');p=Path(rel)
  if not rel or p.is_absolute() or '..' in p.parts or rel in expected:out['errors'].append(f'unsafe or duplicate path:{rel}')
  else:expected[rel]=row
 actual=release_files(root);out['manifest_files']=len(expected);out['checked_files']=len(actual)
 for rel in sorted(set(expected)-set(actual)):out['errors'].append(f'missing:{rel}')
 for rel in sorted(set(actual)-set(expected)):out['errors'].append(f'unexpected:{rel}')
 for rel in sorted(set(actual)&set(expected)):
  p=actual[rel];r=expected[rel]
  if p.stat().st_size!=int(r.get('bytes',-1)):out['errors'].append(f'size:{rel}')
  elif sha256(p)!=str(r.get('sha256') or ''):out['errors'].append(f'hash:{rel}')
 canonical=json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
 if hashlib.sha256(canonical).hexdigest()!=str(raw.get('files_digest_sha256') or ''):out['errors'].append('manifest files digest mismatch')
 out['status']='PASS' if not out['errors'] else 'FAIL';return out
if __name__=='__main__':
 import sys
 r=verify();print(json.dumps(r,indent=2));raise SystemExit(0 if r['status']=='PASS' else 1)
