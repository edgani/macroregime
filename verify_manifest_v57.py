"""Strict deterministic package manifest verifier for War Room OS v5.7."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/'PACKAGE_MANIFEST_V57.json'
IGNORE_DIRS={'.git','.venv','__pycache__','.cache','.pytest_cache','audit_logs','runtime','audit_state_v55','audit_state_v56','audit_state_v57'}
IGNORE_EXACT={
 'PACKAGE_MANIFEST_V57.json','PACKAGE_MANIFEST_V56.json','PACKAGE_MANIFEST_V55.json','PACKAGE_MANIFEST_V53.json',
 'V55_USER_VALIDATION_REPORT.json','V56_USER_VALIDATION_REPORT.json','V57_USER_VALIDATION_REPORT.json',
 'desk_data.json','dashboard_live.html','V42_DEEP_REAUDIT_PREVIEW.png','V42_DEEP_REAUDIT_VALIDATION_REPORT.json',
 'runtime/desk_snapshot.json','runtime/worker_status.json','runtime/force_refresh.flag','runtime/worker.instance.lock',
 'runtime/worker.pid','runtime/worker_boot.log','runtime/worker.log','static/desk_snapshot.json','static/worker_status.json'
}
IGNORE_SUFFIXES={'.pyc','.tmp','.log'}
def sha256(p:Path)->str:
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def ignored(rel:Path)->bool:
 s=rel.as_posix()
 return any(x in IGNORE_DIRS for x in rel.parts) or s in IGNORE_EXACT or rel.suffix.lower() in IGNORE_SUFFIXES or (s.startswith('proof/receipts/') and rel.name!='README.md') or (rel.name.startswith('.') and s not in {'.env.example','.streamlit/config.toml','runtime/.gitkeep','static/.gitkeep'})
def release_files(root:Path=ROOT)->dict[str,Path]:
 return {p.relative_to(root).as_posix():p for p in sorted(root.rglob('*')) if p.is_file() and not ignored(p.relative_to(root))}
def verify(root:Path=ROOT,manifest_path:Path|None=None)->dict:
 mp=manifest_path or root/MANIFEST.name;res={'status':'FAIL','errors':[],'checked_files':0,'manifest_files':0}
 try:raw=json.loads(mp.read_text(encoding='utf-8'))
 except Exception as e:res['errors'].append(f'manifest unreadable:{type(e).__name__}:{e}');return res
 if raw.get('schema')!='warroom.package_manifest.v57':res['errors'].append('manifest schema mismatch')
 rows=raw.get('files') or [];expected={}
 for row in rows:
  rel=str(row.get('path') or '');p=Path(rel)
  if not rel or p.is_absolute() or '..' in p.parts or rel in expected:res['errors'].append(f'unsafe or duplicate path:{rel}')
  else:expected[rel]=row
 actual=release_files(root);res['manifest_files']=len(expected);res['checked_files']=len(actual)
 for rel in sorted(set(expected)-set(actual)):res['errors'].append(f'missing:{rel}')
 for rel in sorted(set(actual)-set(expected)):res['errors'].append(f'unexpected:{rel}')
 for rel in sorted(set(actual)&set(expected)):
  p=actual[rel];row=expected[rel]
  if p.stat().st_size!=int(row.get('bytes',-1)):res['errors'].append(f'size:{rel}')
  elif sha256(p)!=str(row.get('sha256') or ''):res['errors'].append(f'hash:{rel}')
 can=json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
 if hashlib.sha256(can).hexdigest()!=str(raw.get('files_digest_sha256') or ''):res['errors'].append('manifest files digest mismatch')
 res['status']='PASS' if not res['errors'] else 'FAIL';return res
if __name__=='__main__':
 import sys;r=verify();print(json.dumps(r,indent=2));raise SystemExit(0 if r['status']=='PASS' else 1)
