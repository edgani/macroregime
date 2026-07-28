"""Strict manifest verifier for War Room OS v5.3."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent; MANIFEST=ROOT/'PACKAGE_MANIFEST_V53.json'
IGNORE_DIRS={'.git','.venv','__pycache__','.cache','.pytest_cache','audit_logs','runtime'}
IGNORE_EXACT={'PACKAGE_MANIFEST_V53.json','V53_USER_VALIDATION_REPORT.json','desk_data.json','dashboard_live.html','V42_DEEP_REAUDIT_PREVIEW.png','V42_DEEP_REAUDIT_VALIDATION_REPORT.json',
 'runtime/desk_snapshot.json','runtime/worker_status.json','runtime/force_refresh.flag','runtime/worker.instance.lock','runtime/worker.pid','runtime/worker_boot.log','runtime/worker.log','static/desk_snapshot.json','static/worker_status.json'}
IGNORE_SUFFIXES={'.pyc','.tmp','.log'}
def sha256(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def ignored(rel):
 s=rel.as_posix()
 return any(x in IGNORE_DIRS for x in rel.parts) or s in IGNORE_EXACT or rel.suffix.lower() in IGNORE_SUFFIXES or (s.startswith('proof/receipts/') and rel.name!='README.md') or (rel.name.startswith('.') and s not in {'.env.example','.streamlit/config.toml','runtime/.gitkeep','static/.gitkeep'})
def release_files(root=ROOT):
 return {p.relative_to(root).as_posix():p for p in sorted(root.rglob('*')) if p.is_file() and not ignored(p.relative_to(root))}
def verify(root=ROOT,manifest_path=None):
 mp=manifest_path or root/MANIFEST.name;r={'status':'FAIL','errors':[],'checked_files':0,'manifest_files':0}
 try:raw=json.loads(mp.read_text(encoding='utf-8'))
 except Exception as e:r['errors'].append(f'manifest unreadable: {type(e).__name__}: {e}');return r
 if raw.get('schema')!='warroom.package_manifest.v53':r['errors'].append('manifest schema mismatch')
 rows=raw.get('files') or [];exp={}
 for row in rows:
  rel=str(row.get('path') or '');p=Path(rel)
  if not rel or p.is_absolute() or '..' in p.parts or rel in exp:r['errors'].append(f'unsafe or duplicate path:{rel}')
  else:exp[rel]=row
 act=release_files(root);r['manifest_files']=len(exp);r['checked_files']=len(act)
 for rel in sorted(set(exp)-set(act)):r['errors'].append(f'missing:{rel}')
 for rel in sorted(set(act)-set(exp)):r['errors'].append(f'unexpected:{rel}')
 for rel in sorted(set(act)&set(exp)):
  p=act[rel];row=exp[rel]
  if p.stat().st_size!=int(row.get('bytes',-1)):r['errors'].append(f'size:{rel}')
  elif sha256(p)!=str(row.get('sha256') or ''):r['errors'].append(f'hash:{rel}')
 canonical=json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
 if hashlib.sha256(canonical).hexdigest()!=str(raw.get('files_digest_sha256') or ''):r['errors'].append('manifest files digest mismatch')
 r['status']='PASS' if not r['errors'] else 'FAIL';return r
if __name__=='__main__':
 import sys;res=verify();print(json.dumps(res,indent=2));raise SystemExit(0 if res['status']=='PASS' else 1)
