from __future__ import annotations
import os, subprocess, sys, tempfile, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TESTS=[
 'tests/self_test.py','tests/final_contract.py','tests/test_static_contract.py','tests/test_decision_core.py',
 'tests/test_data_adapters.py','tests/test_ihsg_transaction.py','tests/test_story_optionality.py','tests/test_opportunity_kernel.py','tests/test_defillama_adapter.py','tests/test_macro_logic.py','tests/test_macro_snapshot.py','tests/test_replay_timestamps.py','tests/test_negative_controls.py','tests/test_fuzz.py','tests/test_walkforward.py','tests/test_visual_contract.py','tests/test_longitudinal_opportunity.py','tests/test_v32_acceptance.py'
]
results=[]
for rel in TESTS:
    with tempfile.TemporaryDirectory(prefix='oie_state_') as td:
        env=os.environ.copy(); env['OIE_STATE_DIR']=td; env['PYTHONPATH']=str(ROOT)+os.pathsep+str(ROOT/'tests')+os.pathsep+env.get('PYTHONPATH','')
        t=time.time()
        try:
            p=subprocess.run([sys.executable,str(ROOT/rel)],cwd=ROOT,env=env,text=True,capture_output=True,timeout=45)
            status='PASS' if p.returncode==0 else 'FAIL'
            results.append((rel,status,round(time.time()-t,2),p.stdout.strip(),p.stderr.strip()))
        except subprocess.TimeoutExpired as e:
            results.append((rel,'TIMEOUT',45.0,e.stdout or '',e.stderr or ''))
for rel,status,dur,out,err in results:
    print(f'{status:7} {dur:6.2f}s {rel}')
    if status!='PASS':
        print(out); print(err,file=sys.stderr)
failed=[r for r in results if r[1]!='PASS']
print(f'AGGREGATE: {len(results)-len(failed)} PASS / {len(failed)} NONPASS / {len(results)} TOTAL')
if failed: raise SystemExit(1)
