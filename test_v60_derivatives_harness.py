import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=subprocess.run([sys.executable,'run_v60_derivatives_driver_study.py'],cwd=ROOT,capture_output=True,text=True,timeout=180)
assert p.returncode==0,(p.stdout,p.stderr)
r=json.loads((ROOT/'research_v60/results/V60_DERIVATIVES_HARNESS_RESULTS.json').read_text())
assert r['status']=='PASS'
assert r['checks']['planted_origin_family_detected']
assert r['checks']['null_has_zero_survivors']
assert r['checks']['realized_liquidation_not_promoted_as_early_driver']
assert r['market_evidence_status']=='SYNTHETIC_CONTROL_ONLY_NOT_MARKET_PROOF'
print('4/4 PASS')
