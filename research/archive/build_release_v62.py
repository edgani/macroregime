from __future__ import annotations
import hashlib,json,os,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=Path('/mnt/data/War_Room_OS_v62_Deeper_Origin_and_Network_Research.zip')
EXCLUDE={'PACKAGE_MANIFEST_V62.json'}
def included_files(root=ROOT):
    out=[]
    for p in root.rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(root).as_posix()
        if rel in EXCLUDE or rel.startswith('__pycache__/') or '/__pycache__/' in rel or rel.endswith('.pyc'):continue
        out.append((rel,p))
    return sorted(out)
def write_manifest():
    rows=[]
    for rel,p in included_files():rows.append({'path':rel,'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    m={'schema':'warroom.package_manifest.v62','parent_v60_sha256':'72fa075da84be8fbbab233eb9a30a8f07270cd67ff005a44b9adcd31fe69a5e3','files':rows}
    (ROOT/'PACKAGE_MANIFEST_V62.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
def build():
    write_manifest()
    epoch=(2026,7,25,0,0,0)
    if OUT.exists():OUT.unlink()
    files=included_files()+[('PACKAGE_MANIFEST_V62.json',ROOT/'PACKAGE_MANIFEST_V62.json')]
    with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for rel,p in sorted(files):
            info=zipfile.ZipInfo(rel,date_time=epoch);info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
            z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    h=hashlib.sha256(OUT.read_bytes()).hexdigest();sha=OUT.with_suffix('.sha256.txt');sha.write_text(f'{h}  {OUT.name}\n')
    return h
if __name__=='__main__':print(build())
