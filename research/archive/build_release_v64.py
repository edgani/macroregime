from __future__ import annotations
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=Path('/mnt/data/War_Room_OS_v64_Scoped_Proof_Breakthrough.zip')
EXCLUDE={'PACKAGE_MANIFEST_V64.json'}
PARENT_SHA='2f3966e21c05236f404ebb6ac5f8e331eb574fb9779fcaa8830c46695b0bf433'

def included_files(root=ROOT):
    rows=[]
    for p in root.rglob('*'):
        if not p.is_file(): continue
        rel=p.relative_to(root).as_posix()
        if rel in EXCLUDE or rel.startswith('__pycache__/') or '/__pycache__/' in rel or rel.endswith('.pyc'): continue
        rows.append((rel,p))
    return sorted(rows)

def write_manifest():
    files=[{'path':r,'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for r,p in included_files()]
    manifest={
      'schema':'warroom.package_manifest.v64','release':'War_Room_OS_v64_Scoped_Proof_Breakthrough',
      'parent_v63_sha256':PARENT_SHA,'files_digest_sha256':hashlib.sha256(json.dumps(files,separators=(',',':'),sort_keys=True).encode()).hexdigest(),
      'files':files,'historical_gross_market_claims_proven':3,'modern_all_stock_archive_claims_supported':1,
      'independent_modern_claims_proven':0,'modern_non_micro_investable_claims_proven':0,'stock_level_pit_selectors_proven':0,
      'live_predictive_components_promoted':0,'capital_permission':'BLOCKED',
      'claim_boundary':'Scoped market claims only. No ticker-level, independent modern, operational or capital proof.'}
    (ROOT/'PACKAGE_MANIFEST_V64.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest

def build(out=OUT):
    write_manifest(); files=included_files()+[('PACKAGE_MANIFEST_V64.json',ROOT/'PACKAGE_MANIFEST_V64.json')]
    epoch=(2026,7,26,0,0,0)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for rel,p in sorted(files):
            info=zipfile.ZipInfo(rel,date_time=epoch);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    h=hashlib.sha256(out.read_bytes()).hexdigest()
    Path('/mnt/data/War_Room_OS_v64_Scoped_Proof_Breakthrough.sha256.txt').write_text(f'{h}  {out.name}\n')
    return h
if __name__=='__main__':print(build())
