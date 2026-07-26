from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.hashing import canonical_hash

def build():
    formulas=json.loads((ROOT/'evidence/formula_registry_active.json').read_text())['entries']
    matrix=json.loads((ROOT/'validation/market_matrix.json').read_text())['scopes']
    rows=[]
    for f in formulas:
      for s in matrix:
        rows.append({"component":f['component'],"spec_id":f['spec_id'],"formula_hash":f['formula_hash'],"asset":s['asset'],"timeframe":s['timeframe'],"status":"NOT_EVALUATED","reason":"NO_APPROVED_EVIDENCE"})
    return {"entries":rows,"registry_hash":canonical_hash(rows)}
if __name__=='__main__':
    out=ROOT/'validation/applicability_registry.json'; expected=json.dumps(build(),indent=2,sort_keys=True)+"\n"
    if '--check' in sys.argv:
      if not out.exists() or out.read_text()!=expected: raise SystemExit('applicability registry stale')
      print('PASS: applicability registry')
    else: out.write_text(expected); print(out)
