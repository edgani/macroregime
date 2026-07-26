"""Byte-deterministic V6.0 build from exact V5.9 source ancestry."""
from __future__ import annotations
import hashlib,json,tempfile,zipfile
from pathlib import Path
from verify_manifest_v60 import ROOT,MANIFEST,release_files,verify
OUT=ROOT.parent.parent/'War_Room_OS_v60_Deep_Early_Move_Driver_Research.zip'
CHECKSUM=ROOT.parent.parent/'War_Room_OS_v60_Deep_Early_Move_Driver_Research.sha256.txt'
FINAL_VALIDATION=ROOT.parent.parent/'V60_FINAL_ZIP_VALIDATION.json'
def sha256(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def payload():
 rows=[{'path':rel,'bytes':p.stat().st_size,'sha256':sha256(p)} for rel,p in release_files(ROOT).items()];rows.sort(key=lambda x:x['path'])
 canonical=json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
 acct=json.loads((ROOT/'V60_GLOBAL_TRIAL_ACCOUNTING.json').read_text())
 return {'schema':'warroom.package_manifest.v60','release':'War_Room_OS_v60_Deep_Early_Move_Driver_Research','visual_application_version':'4.2',
  'direct_parent':'War_Room_OS_v59_Position_Lifecycle_from_v58','direct_parent_sha256':'ef80385dd54aa8ec7b6aa6c7f1a0fb8d53b2ea999db81c39856108f863e8a291',
  'root_ancestor_v58_sha256':'a3e24e9cc390bb572817aa260e1018bc50f6271b870431e81cca03cf87645601',
  'continuation':'V60_DEEP_EARLY_MOVE_DRIVER_RESEARCH','files_digest_sha256':hashlib.sha256(canonical).hexdigest(),'files':rows,
  'empirical_claim_records':acct['total_empirical_claim_records'],'price_volume_extreme_move_claims':acct['price_volume_extreme_move_claims'],
  'production_proven_early_move_drivers':0,'live_predictive_components_promoted':0,'capital_permission':'BLOCKED',
  'claim_boundary':'OI/liquidation attribution and research harness are not live alpha. Specialized point-in-time panels and prospective evidence are still required.'}
def safe(name):
 p=Path(name);return bool(name) and not p.is_absolute() and '..' not in p.parts and not name.startswith(('/','\\'))
def write_zip(path):
 files=release_files(ROOT);files[MANIFEST.name]=MANIFEST
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9,strict_timestamps=True,allowZip64=True) as z:
  for rel in sorted(files):
   info=zipfile.ZipInfo(rel,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(0o100644&0xffff)<<16;info.create_system=3
   z.writestr(info,files[rel].read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
def validate_zip(path):
 errors=[]
 with zipfile.ZipFile(path) as z:
  names=z.namelist()
  if len(names)!=len(set(names)):errors.append('duplicate zip members')
  errors += [f'unsafe:{n}' for n in names if not safe(n)]
  with tempfile.TemporaryDirectory(prefix='v60_clean_') as td:
   z.extractall(td);root=Path(td);r=verify(root,root/MANIFEST.name)
   if r['status']!='PASS':errors.extend(r['errors'][:200])
   # Focused clean extract controls without rewriting source evidence.
   import subprocess,sys
   p=subprocess.run([sys.executable,'test_v60_mechanical_flow.py'],cwd=root,capture_output=True,text=True,timeout=180)
   if p.returncode:errors.append('clean mechanical flow test failed')
   p=subprocess.run([sys.executable,'test_v60_derivatives_harness.py'],cwd=root,capture_output=True,text=True,timeout=300)
   if p.returncode:errors.append('clean derivatives harness test failed')
 return {'status':'PASS' if not errors else 'FAIL','errors':errors}
def main():
 pl=payload();MANIFEST.write_text(json.dumps(pl,indent=2,sort_keys=True)+'\n')
 r=verify()
 if r['status']!='PASS':print(json.dumps(r,indent=2));return 1
 with tempfile.TemporaryDirectory(prefix='v60_build_') as td:
  a=Path(td)/'a.zip';b=Path(td)/'b.zip';write_zip(a);write_zip(b)
  if a.read_bytes()!=b.read_bytes():print('deterministic rebuild mismatch');return 1
  OUT.write_bytes(a.read_bytes())
 clean=validate_zip(OUT)
 digest=sha256(OUT);CHECKSUM.write_text(f'{digest}  {OUT.name}\n')
 report={'schema':'warroom.release_validation.v60','status':clean['status'],'errors':clean['errors'],'zip':str(OUT),'sha256':digest,'bytes':OUT.stat().st_size,
  'manifest_files':len(pl['files']),'deterministic_rebuild':True,'clean_extract_manifest':'PASS' if clean['status']=='PASS' else 'FAIL','source_mutation_during_clean_validation':0,
  'empirical_claim_records':pl['empirical_claim_records'],'production_proven_early_move_drivers':0,'capital_permission':'BLOCKED'}
 FINAL_VALIDATION.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 print(json.dumps(report,indent=2));return 0 if clean['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
