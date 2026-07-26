from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.hashing import canonical_hash
from warroom_v3.providers import ProviderRegistry

def build():
    release=json.loads((ROOT/'artifacts/release_manifest_ready.json').read_text())
    formulas=json.loads((ROOT/'evidence/formula_registry_active.json').read_text())
    matrix=json.loads((ROOT/'validation/market_matrix.json').read_text())
    applicability=json.loads((ROOT/'validation/applicability_registry.json').read_text())
    catalog=json.loads((ROOT/'validation/data_catalog.json').read_text())
    plan=json.loads((ROOT/'config/collection_plan.json').read_text())
    providers=ProviderRegistry.load(ROOT/'config/providers.json')
    payload={
      'seal_id':'V3-NEWZIP-PROSPECTIVE-ARMED-001','status':'ARMED',
      'collection_starts_at':'2026-07-13T00:00:00+07:00',
      'system_release_hash':release['release_hash'],'formula_registry_hash':formulas['registry_hash'],
      'market_matrix_hash':matrix['matrix_hash'],'applicability_registry_hash':applicability['registry_hash'],
      'data_catalog_hash':catalog['catalog_hash'],'provider_registry_hash':providers.snapshot_hash,
      'collection_plan_hash':plan['plan_hash'],'paper_live_eligible':False,
      'reason_codes':['FORMULAS_NOT_EVALUATED','PAPER_BLOCKED','LIVE_BLOCKED'],
    }
    payload['seal_hash']=canonical_hash(payload)
    return payload
if __name__=='__main__':
    out=ROOT/'prospective/SEAL.json'; expected=json.dumps(build(),indent=2,sort_keys=True)+'\n'
    if '--check' in sys.argv:
        if not out.exists() or out.read_text()!=expected: raise SystemExit('prospective seal stale')
        print('PASS: prospective seal')
    else: out.write_text(expected); print(out)
