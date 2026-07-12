from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.validation import Check,run_checks
checks=[
 Check('pytest',(sys.executable,'-m','pytest','-q')),
 Check('compileall',(sys.executable,'-m','compileall','-q','src','scripts','streamlit_app.py')),
 Check('streamlit-smoke',(sys.executable,'scripts/check_streamlit_app.py')),
 Check('import-boundaries',(sys.executable,'scripts/check_import_boundaries.py')),
 Check('formula-registry',(sys.executable,'scripts/build_formula_registry.py','--check')),
 Check('data-catalog',(sys.executable,'scripts/build_data_catalog.py','--check')),
 Check('market-matrix',(sys.executable,'scripts/build_market_matrix.py','--check')),
 Check('applicability',(sys.executable,'scripts/build_applicability.py','--check')),
 Check('collection-plan',(sys.executable,'scripts/build_collection_plan.py','--check')),
 Check('provider-registry',(sys.executable,'scripts/check_provider_registry.py')),
 Check('release-manifest',(sys.executable,'scripts/build_release_manifest.py','--check')),
 Check('prospective-seal',(sys.executable,'scripts/build_prospective_seal.py','--check')),
 Check('trial-ledger',(sys.executable,'scripts/check_trial_ledger.py')),
 Check('runtime-store',(sys.executable,'scripts/check_runtime_store.py')),
]
run_checks(checks,cwd=ROOT)
print('ALL VALIDATION LAYERS PASSED')
