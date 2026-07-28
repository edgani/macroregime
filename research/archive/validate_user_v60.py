"""User-machine validation for V6.0. Full regressions remain available in validate_v60_deep_driver.py."""
from __future__ import annotations
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CMDS=[
 ('manifest',[sys.executable,'verify_manifest_v60.py'],300),
 ('release_contracts',[sys.executable,'validate_v60_release_contracts.py'],300),
 ('mechanical_flow',[sys.executable,'test_v60_mechanical_flow.py'],180),
 ('derivatives_harness',[sys.executable,'test_v60_derivatives_harness.py'],300),
 ('synthetic_snapshot',[sys.executable,'run.py','--synthetic','--markets','us,idx,crypto,commodity,fx','--out','runtime/v60_desk.json','--html','runtime/v60_dashboard.html'],900),
]
def main():
 rows=[]
 for name,cmd,timeout in CMDS:
  try:
   p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=timeout)
   rows.append({'name':name,'status':'PASS' if p.returncode==0 else 'FAIL','returncode':p.returncode,'output_tail':(p.stdout+'\n'+p.stderr)[-12000:]})
  except subprocess.TimeoutExpired as e:rows.append({'name':name,'status':'FAIL','returncode':None,'output_tail':f'timeout:{e}'})
 report={'schema':'warroom.user_validation.v60','status':'PASS' if all(x['status']=='PASS' for x in rows) else 'FAIL','predictive_components_promoted_to_live':0,'capital_permission':'BLOCKED','tests':rows}
 (ROOT/'V60_USER_VALIDATION_REPORT.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
