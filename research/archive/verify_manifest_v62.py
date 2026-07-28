import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;M=ROOT/'PACKAGE_MANIFEST_V62.json'
d=json.loads(M.read_text());bad=[]
for r in d['files']:
    p=ROOT/r['path']
    if not p.is_file():bad.append([r['path'],'missing']);continue
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    if h!=r['sha256'] or p.stat().st_size!=r['size']:bad.append([r['path'],'mismatch'])
extra=[]
tracked={r['path'] for r in d['files']}
for p in ROOT.rglob('*'):
    if p.is_file():
        rel=p.relative_to(ROOT).as_posix()
        if rel in {'PACKAGE_MANIFEST_V62.json'} or rel.startswith('__pycache__/') or '/__pycache__/' in rel or rel.endswith('.pyc'):continue
        if rel not in tracked:extra.append(rel)
out={'status':'PASS' if not bad and not extra else 'FAIL','manifest_files':len(tracked),'bad':bad,'unexpected':extra}
print(json.dumps(out,indent=2));raise SystemExit(0 if out['status']=='PASS' else 1)
