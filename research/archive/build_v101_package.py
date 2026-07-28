"""Deterministic clean package builder for War Room OS V10.1."""
from __future__ import annotations
import hashlib,json,shutil,subprocess,tempfile,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'War_Room_OS_v101_Carry_Trade_Proof_Factory.zip'
OUT2=ROOT.parent/'War_Room_OS_v101_Carry_Trade_Proof_Factory.rebuild.zip'
MANIFEST=ROOT/'V101_PACKAGE_MANIFEST.json'
FIXED=(2020,1,1,0,0,0)

EXACT_EXCLUDE={
 'V101_PACKAGE_MANIFEST.json',
 'runtime/v101_validation_dashboard.js',
 'runtime/worker_status.json',
 'runtime/desk_snapshot.json',
 'desk_data.json',
}

def sha(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def included()->list[Path]:
 rows=[]
 for p in ROOT.rglob('*'):
  if not p.is_file():continue
  rel=p.relative_to(ROOT).as_posix()
  if rel in EXACT_EXCLUDE:continue
  if any(x in p.parts for x in ('.venv','__pycache__','.git')):continue
  if p.suffix.lower() in {'.pyc','.tmp','.lock'}:continue
  if rel.endswith('.rebuild.zip') or rel.endswith('.sha256.txt'):continue
  rows.append(p)
 return sorted(rows,key=lambda x:x.relative_to(ROOT).as_posix())

def write_manifest()->dict:
 entries=[]
 for p in included():
  rel=p.relative_to(ROOT).as_posix()
  entries.append({'path':rel,'size':p.stat().st_size,'sha256':sha(p)})
 payload={'schema':'warroom.v101.package_manifest.v1','version':'10.1','entries':entries,'entry_count':len(entries)}
 MANIFEST.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
 return payload

def create(path:Path)->None:
 files=included()+[MANIFEST]
 files=sorted(files,key=lambda x:x.relative_to(ROOT).as_posix())
 with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in files:
   rel=p.relative_to(ROOT).as_posix();info=zipfile.ZipInfo(rel,FIXED);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
   z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

def verify(path:Path,run_validation:bool=False)->dict:
 with tempfile.TemporaryDirectory() as td:
  td=Path(td)
  with zipfile.ZipFile(path) as z:z.extractall(td)
  m=json.loads((td/'V101_PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
  errors=[]
  for row in m['entries']:
   p=td/row['path']
   if not p.is_file():errors.append('missing:'+row['path']);continue
   if p.stat().st_size!=row['size']:errors.append('size:'+row['path'])
   if sha(p)!=row['sha256']:errors.append('hash:'+row['path'])
  validation=None
  if run_validation and not errors:
   r=subprocess.run(['python','validate_v101_carry.py'],cwd=td,capture_output=True,text=True,timeout=180)
   validation={'returncode':r.returncode,'stdout':r.stdout[-2000:],'stderr':r.stderr[-2000:]}
   if r.returncode!=0:errors.append('validator_failed')
  return {'manifest_entries':m['entry_count'],'errors':errors,'valid':not errors,'validation':validation}

def main()->None:
 for p in (OUT,OUT2):
  if p.exists():p.unlink()
 write_manifest();create(OUT);first=verify(OUT,run_validation=True)
 if not first['valid']:raise SystemExit(json.dumps(first,indent=2))
 create(OUT2)
 deterministic=OUT.read_bytes()==OUT2.read_bytes()
 second=verify(OUT2,run_validation=False)
 if not deterministic or not second['valid']:raise SystemExit('deterministic/second validation failed')
 OUT2.unlink()
 digest=sha(OUT)
 (ROOT.parent/'War_Room_OS_v101_Carry_Trade_Proof_Factory.sha256.txt').write_text(f'{digest}  {OUT.name}\n',encoding='utf-8')
 report={'zip':str(OUT),'sha256':digest,'zip_members':len(zipfile.ZipFile(OUT).namelist()),'manifest_entries':first['manifest_entries'],'clean_extract_valid':first['valid'],'validator_returncode':first['validation']['returncode'] if first['validation'] else None,'deterministic_rebuild':deterministic}
 print(json.dumps(report,indent=2))

if __name__=='__main__':main()
