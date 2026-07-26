from __future__ import annotations
import hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=Path('/mnt/data/War_Room_OS_v63_All_Tab_Proof_Reaudit.zip')
EXCLUDE={'PACKAGE_MANIFEST_V63.json'}
PARENT_SHA='5e66419c7c9d8ede091b2682e60d610198039e8cf212d468d35f9ea68c809daa'

def included_files(root=ROOT):
    out=[]
    for p in root.rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(root).as_posix()
        if rel in EXCLUDE or rel.startswith('__pycache__/') or '/__pycache__/' in rel or rel.endswith('.pyc'):continue
        out.append((rel,p))
    return sorted(out)

def write_manifest():
    rows=[{'path':rel,'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for rel,p in included_files()]
    m={'schema':'warroom.package_manifest.v63','parent_v62_sha256':PARENT_SHA,'files':rows,'capital_permission':'BLOCKED','predictive_components_promoted':0}
    (ROOT/'PACKAGE_MANIFEST_V63.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')

def build(out=OUT):
    write_manifest(); epoch=(2026,7,26,0,0,0)
    if out.exists():out.unlink()
    files=included_files()+[('PACKAGE_MANIFEST_V63.json',ROOT/'PACKAGE_MANIFEST_V63.json')]
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for rel,p in sorted(files):
            info=zipfile.ZipInfo(rel,date_time=epoch);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    h=hashlib.sha256(out.read_bytes()).hexdigest()
    out.with_suffix('.sha256.txt').write_text(f'{h}  {out.name}\n')
    return h
if __name__=='__main__':print(build())
