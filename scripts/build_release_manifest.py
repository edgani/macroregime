from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.hashing import canonical_hash,file_hash
INCLUDE=[
 'src/warroom_v3/contracts.py','src/warroom_v3/gates.py','src/warroom_v3/data.py','src/warroom_v3/hashing.py',
 'src/warroom_v3/registry.py','src/warroom_v3/applicability.py','src/warroom_v3/causality.py','src/warroom_v3/mtf.py',
 'src/warroom_v3/pipeline.py','src/warroom_v3/sensors/mqa.py','src/warroom_v3/sensors/momentum.py','src/warroom_v3/validation.py',
 'src/warroom_v3/providers.py','src/warroom_v3/storage.py','src/warroom_v3/runtime.py','src/warroom_v3/evaluation.py',
 'src/warroom_v3/api.py','src/warroom_v3/cli.py','src/warroom_v3/trading.py',
 'streamlit_app.py','.streamlit/config.toml',
 'scripts/warroom.py','scripts/check_streamlit_app.py','scripts/check_import_boundaries.py','scripts/check_trial_ledger.py','scripts/build_formula_registry.py',
 'scripts/build_data_catalog.py','scripts/build_market_matrix.py','scripts/build_applicability.py','scripts/build_collection_plan.py',
 'scripts/check_provider_registry.py','scripts/check_runtime_store.py','static/index.html','config/providers.json','config/collection_plan.json',
 'evidence/formula_registry_active.json','validation/data_catalog.json','validation/market_matrix.json','validation/applicability_registry.json',
 'README.md','.env.example','Makefile','requirements-dev.txt','READY_STATUS_2026-07-12.md','STREAMLIT_TRADING_STATUS_2026-07-13.md','ops/README.md','pyproject.toml','requirements.txt',
 'Dockerfile','docker-compose.yml','ops/systemd/warroom-api.service','ops/systemd/warroom-streamlit.service',
 'ops/systemd/warroom-collector.service','ops/systemd/warroom-collector.timer','ops/install_oracle_ubuntu.sh'
]
def build():
    missing=[p for p in INCLUDE if not (ROOT/p).exists()]
    if missing: raise FileNotFoundError(missing)
    rows=[{'path':p,'sha256':file_hash(ROOT/p)} for p in sorted(INCLUDE)]
    return {'release_id':'WARROOM-V3-STREAMLIT-TRADING-20260713','files':rows,'release_hash':canonical_hash(rows)}
if __name__=='__main__':
    out=ROOT/'artifacts/release_manifest_ready.json'; expected=json.dumps(build(),indent=2,sort_keys=True)+'\n'
    if '--check' in sys.argv:
        if not out.exists() or out.read_text()!=expected: raise SystemExit('release manifest stale')
        print('PASS: streamlit trading release manifest')
    else: out.write_text(expected); print(out)
