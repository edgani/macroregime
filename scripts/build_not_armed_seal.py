from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.hashing import canonical_hash,file_hash

def build():
    release=json.loads((ROOT/'artifacts/release_manifest_sprint1.json').read_text())
    formulas=json.loads((ROOT/'evidence/formula_registry_active.json').read_text())
    matrix=json.loads((ROOT/'validation/market_matrix.json').read_text())
    applicability=json.loads((ROOT/'validation/applicability_registry.json').read_text())
    catalog=json.loads((ROOT/'validation/data_catalog.json').read_text())
    payload={
      'seal_id':'V3-NEWZIP-PROSPECTIVE-NOT-ARMED-001','status':'NOT_ARMED',
      'reason_codes':['NO_APPROVED_POINT_IN_TIME_PROVIDER','NO_PROSPECTIVE_DATASET','FORMULAS_NOT_EVALUATED'],
      'system_release_hash':release['release_hash'],'formula_registry_hash':formulas['registry_hash'],
      'market_matrix_hash':matrix['matrix_hash'],'applicability_registry_hash':applicability['registry_hash'],
      'data_catalog_hash':catalog['catalog_hash'],'prospective_batches':0,'paper_live_eligible':False
    }
    payload['seal_hash']=canonical_hash(payload)
    return payload
if __name__=='__main__':
 out=ROOT/'prospective/SEAL_NOT_ARMED.json'; expected=json.dumps(build(),indent=2,sort_keys=True)+"\n"
 if '--check' in sys.argv:
  if not out.exists() or out.read_text()!=expected: raise SystemExit('not-armed seal stale')
  print('PASS: prospective seal remains NOT_ARMED')
 else: out.write_text(expected); print(out)
