"""Build byte-deterministic War Room OS v5.6 release."""
from __future__ import annotations
import hashlib,json,tempfile,zipfile
from pathlib import Path
from verify_manifest_v56 import ROOT,MANIFEST,release_files,verify
OUT=ROOT.parent/'War_Room_OS_v56_Signed_Dealer_Research_Continuation.zip'
CHECKSUM=ROOT.parent/'War_Room_OS_v56_Signed_Dealer_Research_Continuation.sha256.txt'
def sha256(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def manifest_payload():
 rows=[{'path':rel,'bytes':p.stat().st_size,'sha256':sha256(p)} for rel,p in release_files(ROOT).items()];rows.sort(key=lambda x:x['path'])
 can=json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
 return {'schema':'warroom.package_manifest.v56','release':'War_Room_OS_v56_Signed_Dealer_Research_Continuation','visual_application_version':'4.2','hardening_base':'5.2','research_accounting_base':'5.3','options_base':'5.5','signed_dealer_continuation':'V72_2_TBT_QUOTES_CALCS_OI_LIQUIDITY_MANIFEST_LOCKBOX','files_digest_sha256':hashlib.sha256(can).hexdigest(),'files':rows,'claim_boundary':'Signed-dealer research engineering and fail-closed lineage pass. Licensed historical outcomes and prospective profitability are not evaluated. Capital permission remains blocked.'}
def safe(name):
 p=Path(name);return bool(name) and not p.is_absolute() and '..' not in p.parts and not name.startswith(('/','\\'))
def write_zip(path):
 files=release_files(ROOT);files[MANIFEST.name]=MANIFEST
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9,strict_timestamps=True) as z:
  for rel in sorted(files):
   info=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(0o100644&0xffff)<<16;info.create_system=3
   z.writestr(info,files[rel].read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
def validate_zip(path):
 errors=[]
 with zipfile.ZipFile(path) as z:
  names=z.namelist()
  if len(names)!=len(set(names)):errors.append('duplicate zip members')
  errors.extend(f'unsafe:{n}' for n in names if not safe(n))
  with tempfile.TemporaryDirectory(prefix='v56_zip_') as td:
   z.extractall(td);r=verify(Path(td),Path(td)/MANIFEST.name)
   if r['status']!='PASS':errors.extend(r['errors'][:200])
 return {'status':'PASS' if not errors else 'FAIL','errors':errors}
def main():
 payload=manifest_payload();MANIFEST.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
 r=verify()
 if r['status']!='PASS':print(json.dumps(r,indent=2));return 1
 with tempfile.TemporaryDirectory(prefix='v56_build_') as td:
  a=Path(td)/'a.zip';b=Path(td)/'b.zip';write_zip(a);write_zip(b)
  if a.read_bytes()!=b.read_bytes():print('deterministic rebuild mismatch');return 1
  OUT.write_bytes(a.read_bytes())
 check=validate_zip(OUT)
 if check['status']!='PASS':print(json.dumps(check,indent=2));return 1
 d=sha256(OUT);CHECKSUM.write_text(f'{d}  {OUT.name}\n')
 print(json.dumps({'status':'PASS','zip':str(OUT),'sha256':d,'bytes':OUT.stat().st_size,'manifest_files':len(payload['files']),'deterministic_rebuild':True,'clean_extract_manifest':'PASS'},indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
