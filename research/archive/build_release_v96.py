"""Build a deterministic War Room OS V9.6 release ZIP and package manifest."""
from __future__ import annotations
import argparse, hashlib, json, os, zipfile
from pathlib import Path
from typing import Iterable

EXCLUDE_DIRS={"__pycache__",".git",".venv","venv"}
EXCLUDE_SUFFIXES={".pyc",".pyo",".part",".tmp"}
EXCLUDE_FILES={"PACKAGE_MANIFEST.json"}
FIXED_TIME=(2020,1,1,0,0,0)

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def files(root:Path)->Iterable[Path]:
    for path in sorted(root.rglob('*'),key=lambda p:p.relative_to(root).as_posix().lower()):
        rel=path.relative_to(root)
        if not path.is_file() or any(part in EXCLUDE_DIRS for part in rel.parts): continue
        if path.name in EXCLUDE_FILES or path.suffix.lower() in EXCLUDE_SUFFIXES: continue
        if rel.as_posix().startswith('runtime/v95_public_acquisition_test/'): continue
        yield path

def build(root:Path,output:Path)->dict:
    root=root.resolve(); output=output.resolve()
    entries=[]
    for path in files(root):
        rel=path.relative_to(root).as_posix()
        entries.append({'path':rel,'bytes':path.stat().st_size,'sha256':sha(path)})
    manifest={'schema':'warroom.v96.package_manifest.v1','release':'War Room OS V9.6 Causal Anti-Overfit Research Factory','file_count_excluding_manifest':len(entries),'files':entries}
    manifest['manifest_hash']=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    mp=root/'PACKAGE_MANIFEST.json'; mp.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    members=[(mp,'PACKAGE_MANIFEST.json')]+[(root/r['path'],r['path']) for r in entries]
    members.sort(key=lambda x:x[1].lower()); output.parent.mkdir(parents=True,exist_ok=True)
    temp=output.with_suffix(output.suffix+'.tmp'); temp.unlink(missing_ok=True)
    with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path,rel in members:
            info=zipfile.ZipInfo(rel,FIXED_TIME); info.compress_type=zipfile.ZIP_DEFLATED; info.create_system=3; info.external_attr=(0o100644&0xFFFF)<<16
            z.writestr(info,path.read_bytes())
    os.replace(temp,output)
    return {'schema':'warroom.v96.release_build.v1','zip':str(output),'zip_sha256':sha(output),'zip_bytes':output.stat().st_size,'zip_members':len(members),'manifest_hash':manifest['manifest_hash'],'manifest_entries':len(entries)}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--root',default='.'); p.add_argument('--output',required=True); a=p.parse_args()
    print(json.dumps(build(Path(a.root),Path(a.output)),indent=2))
if __name__=='__main__': main()
