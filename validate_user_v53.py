"""User-machine validation for v5.3 attachment continuation."""
from __future__ import annotations
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
COMMANDS=[('compile',[sys.executable,'-m','compileall','-q','.'],180),('attachment_continuation',[sys.executable,'hardening_tests/test_attachment_continuation_v53.py'],120),('hardening_adversarial',[sys.executable,'hardening_tests/test_hardening_v52.py'],180),('ui_contracts',[sys.executable,'validate_v42_deep_reaudit.py'],300),('synthetic_snapshot',[sys.executable,'run.py','--synthetic','--markets','us,idx,crypto,commodity,fx','--out','runtime/v53_desk.json','--html','runtime/v53_dashboard.html'],300),('manifest',[sys.executable,'verify_manifest_v53.py'],120)]
def main():
 rows=[]
 for name,cmd,to in COMMANDS:
  try:p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=to);status='PASS' if p.returncode==0 else 'FAIL';out=(p.stdout+'\n'+p.stderr)[-8000:]
  except subprocess.TimeoutExpired as e:status='FAIL';p=None;out=f'timeout:{e}'
  rows.append({'name':name,'status':status,'returncode':None if p is None else p.returncode,'output_tail':out})
 report={'schema':'warroom.user_validation.v53','status':'PASS' if all(x['status']=='PASS' for x in rows) else 'FAIL','predictive_components_promoted_to_live':0,'capital_permission':'BLOCKED','tests':rows}
 (ROOT/'V53_USER_VALIDATION_REPORT.json').write_text(json.dumps(report,indent=2,sort_keys=True),encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='tests'},indent=2));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
