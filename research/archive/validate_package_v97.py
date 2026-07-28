"""Validate a clean extracted V9.7 package against its manifest."""
from __future__ import annotations
import argparse, hashlib, json, py_compile, tempfile, zipfile
from pathlib import Path

def sha(path:Path)->str:
    h=hashlib.sha256(); h.update(path.read_bytes()); return h.hexdigest()

def validate(zip_path:Path)->dict:
    with tempfile.TemporaryDirectory(prefix='warroom_v97_') as tmp:
        root=Path(tmp)
        with zipfile.ZipFile(zip_path) as z: z.extractall(root); members=z.namelist()
        manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
        errors=[]
        expected={r['path']:r for r in manifest.get('files',[])}
        actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='PACKAGE_MANIFEST.json'}
        if actual!=set(expected): errors.append({'kind':'member_set_mismatch','missing':sorted(set(expected)-actual),'extra':sorted(actual-set(expected))})
        for rel,row in expected.items():
            p=root/rel
            if not p.is_file(): continue
            if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']: errors.append({'kind':'hash_or_size_mismatch','path':rel})
        compile_errors=[]
        for p in root.rglob('*.py'):
            try: py_compile.compile(str(p),doraise=True)
            except Exception as exc: compile_errors.append({'path':p.relative_to(root).as_posix(),'error':f'{type(exc).__name__}: {exc}'})
        errors.extend({'kind':'compile_error',**x} for x in compile_errors)
        return {'schema':'warroom.v97.package_validation.v1','zip_sha256':sha(zip_path),'zip_members':len(members),'manifest_entries':len(expected),'manifest_valid':not any(x['kind'] in {'member_set_mismatch','hash_or_size_mismatch'} for x in errors),'python_compile_valid':not compile_errors,'errors':errors,'all_passed':not errors}

def main():
    p=argparse.ArgumentParser(); p.add_argument('zip'); a=p.parse_args(); print(json.dumps(validate(Path(a.zip)),indent=2))
if __name__=='__main__': main()
