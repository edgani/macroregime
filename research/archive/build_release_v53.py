"""Build deterministic War Room OS v5.3 release."""
from __future__ import annotations
import hashlib,json,tempfile,zipfile
from pathlib import Path
from verify_manifest_v53 import ROOT,MANIFEST,release_files,verify
OUT=ROOT.parent/'War_Room_OS_v53_Attachment_Continuation.zip';CHECKSUM=ROOT.parent/'War_Room_OS_v53_Attachment_Continuation.sha256.txt'
def sha256(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def manifest():
 rows=[{'path':rel,'bytes':p.stat().st_size,'sha256':sha256(p)} for rel,p in release_files(ROOT).items()];rows.sort(key=lambda x:x['path'])
 can=json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
 return {'schema':'warroom.package_manifest.v53','release':'War_Room_OS_v53_Attachment_Continuation','visual_application_version':'4.2','hardening_base':'5.2','research_accounting_base':'5.1','files_digest_sha256':hashlib.sha256(can).hexdigest(),'files':rows,'claim_boundary':'Historical evidence is visible with zero live decision weight. V61 failed, V62 acquisition blocked, capital blocked.'}
def safe(n):
 p=Path(n);return bool(n) and not p.is_absolute() and '..' not in p.parts and not n.startswith(('/','\\\\'))
def write_zip(p):
 files=release_files(ROOT);files[MANIFEST.name]=MANIFEST
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=9,strict_timestamps=True) as z:
  for rel in sorted(files):
   info=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(0o100644&0xffff)<<16;info.create_system=3
   z.writestr(info,files[rel].read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
def validate_zip(p):
 errs=[]
 with zipfile.ZipFile(p) as z:
  ns=z.namelist()
  if len(ns)!=len(set(ns)):errs.append('duplicate zip members')
  errs += [f'unsafe:{n}' for n in ns if not safe(n)]
  with tempfile.TemporaryDirectory(prefix='v53_zip_') as d:
   z.extractall(d);res=verify(Path(d),Path(d)/MANIFEST.name)
   if res['status']!='PASS':errs+=res['errors'][:100]
 return {'status':'PASS' if not errs else 'FAIL','errors':errs}
def main():
 payload=manifest();MANIFEST.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 if verify()['status']!='PASS':print(json.dumps(verify(),indent=2));return 1
 with tempfile.TemporaryDirectory(prefix='v53_build_') as d:
  a=Path(d)/'a.zip';b=Path(d)/'b.zip';write_zip(a);write_zip(b)
  if a.read_bytes()!=b.read_bytes():print('deterministic rebuild mismatch');return 1
  OUT.write_bytes(a.read_bytes())
 check=validate_zip(OUT)
 if check['status']!='PASS':print(json.dumps(check,indent=2));return 1
 digest=sha256(OUT);CHECKSUM.write_text(f'{digest}  {OUT.name}\n',encoding='utf-8')
 print(json.dumps({'status':'PASS','zip':str(OUT),'sha256':digest,'bytes':OUT.stat().st_size,'manifest_files':len(payload['files']),'deterministic_rebuild':True,'clean_extract_manifest':'PASS'},indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
