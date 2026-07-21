"""Master operational validator for War Room OS v3.3.1."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUITES = [
    ("v331_empty_board_worker_hotfix", "validate_v331_hotfix.py", 360),
    ("v33_full_operational_regression", "validate_release_v33.py", 900),
]
checks=[]
for name, script, timeout in SUITES:
    try:
        p=subprocess.run([sys.executable,str(ROOT/script)],cwd=ROOT,capture_output=True,text=True,timeout=timeout)
        detail=(p.stdout+"\n"+p.stderr).strip()[-16000:]
        checks.append({"name":name,"passed":p.returncode==0,"detail":detail})
        print(("PASS" if p.returncode==0 else "FAIL"),name)
    except Exception as exc:
        checks.append({"name":name,"passed":False,"detail":f"{type(exc).__name__}: {exc}"})
        print("FAIL",name,exc)
report={
    "version":"3.3.1",
    "suite":"master_operational_release_hotfix",
    "status":"PASS" if all(x["passed"] for x in checks) else "FAIL",
    "passed":sum(x["passed"] for x in checks),"total":len(checks),"checks":checks,
    "operational_permission":"READY_FOR_USER_REVIEW" if all(x["passed"] for x in checks) else "BLOCKED",
    "capital_permission":"CAPITAL_BLOCKED",
    "fixed":[
        "Undefined disc variable no longer crashes the core refresh worker.",
        "All 19 subviews render decision-board rows in BOARD mode.",
        "Institutional event helpers no longer throw browser page errors.",
    ],
    "proof_boundary":["Software regression PASS is not predictive edge.","Paid provider credentials remain external.","PIT WFA, lockbox and prospective evidence remain separate gates."],
}
(ROOT/'V331_MASTER_RELEASE_REPORT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if report['status']!='PASS': raise SystemExit(1)
