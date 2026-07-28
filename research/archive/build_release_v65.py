from __future__ import annotations
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=Path('/mnt/data/War_Room_OS_v65_Proof_First_Active_Kernel.zip')
SHA_OUT=Path('/mnt/data/War_Room_OS_v65_Proof_First_Active_Kernel.sha256.txt')
EXCLUDE={'PACKAGE_MANIFEST_V65.json'}
PARENT_SHA='816440420eadc03fdae95be12c5f457ca77d88ff21f07d724c34a975e48bb296'

def included_files(root=ROOT):
    rows=[]
    for p in root.rglob('*'):
        if not p.is_file(): continue
        rel=p.relative_to(root).as_posix()
        if rel in EXCLUDE or rel.startswith('__pycache__/') or '/__pycache__/' in rel or rel.endswith('.pyc'):
            continue
        rows.append((rel,p))
    return sorted(rows)

def write_manifest():
    files=[{'path':r,'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for r,p in included_files()]
    manifest={
      'schema':'warroom.package_manifest.v65',
      'release':'War_Room_OS_v65_Proof_First_Active_Kernel',
      'parent_v64_sha256':PARENT_SHA,
      'files_digest_sha256':hashlib.sha256(json.dumps(files,separators=(',',':'),sort_keys=True).encode()).hexdigest(),
      'files':files,
      'active_operational_components':6,
      'evidence_active_research_components':3,
      'decision_active_predictive_components':0,
      'global_216_10bp_archive_stability_claims':3,
      'global_216_25bp_claims':0,
      'point_in_time_ticker_selectors_proven':0,
      'prospective_capital_components':0,
      'live_decision_weight':0.0,
      'capital_permission':'BLOCKED',
      'kernel_policy':'Every active component must pass its own exact contract. No archive claim can affect direction, ranking, target, sizing or capital.'
    }
    (ROOT/'PACKAGE_MANIFEST_V65.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest

def build(out=OUT):
    write_manifest()
    files=included_files()+[('PACKAGE_MANIFEST_V65.json',ROOT/'PACKAGE_MANIFEST_V65.json')]
    epoch=(2026,7,26,0,0,0)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for rel,p in sorted(files):
            info=zipfile.ZipInfo(rel,date_time=epoch)
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    h=hashlib.sha256(out.read_bytes()).hexdigest()
    SHA_OUT.write_text(f'{h}  {out.name}\n')
    return {'sha256':h,'files':len(files),'out':str(out)}
if __name__=='__main__': print(json.dumps(build(),indent=2))
