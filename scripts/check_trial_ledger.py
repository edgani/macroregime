from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.hashing import canonical_hash
path=ROOT/'research/trial_ledger/trials.jsonl'
prev='GENESIS'; count=0
for line in path.read_text(encoding='utf-8').splitlines():
    if not line.strip(): continue
    row=json.loads(line); stored=row.pop('entry_hash')
    if row.get('previous_hash') != prev: raise SystemExit(f'broken previous hash at row {count+1}')
    actual=canonical_hash(row)
    if actual != stored: raise SystemExit(f'entry hash mismatch at row {count+1}')
    prev=stored; count+=1
if count < 2: raise SystemExit('trial ledger too short')
print(f'PASS: trial ledger ({count} entries, head={prev})')
