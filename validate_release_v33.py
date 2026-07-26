"""Master operational release validator for War Room OS v3.3.

This aggregates deterministic UI/semantic contracts, lineage, live-stack parser
fixtures, GCFIS synthetic correctness, and an actual Streamlit health start. It
never promotes predictive alpha or capital permission.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CHECKS=[]

def record(name, passed, detail=""):
    row={"name":name,"passed":bool(passed),"detail":detail[-12000:] if isinstance(detail,str) else str(detail)}
    CHECKS.append(row)
    print(("PASS" if passed else "FAIL"),name,row["detail"][:500])

def run_script(name, rel, timeout=240):
    try:
        proc=subprocess.run([sys.executable,str(ROOT/rel)],cwd=ROOT,capture_output=True,text=True,timeout=timeout)
        out=(proc.stdout+"\n"+proc.stderr).strip()
        record(name,proc.returncode==0,out)
    except subprocess.TimeoutExpired as exc:
        record(name,False,f"timeout after {timeout}s: {exc}")
    except Exception as exc:
        record(name,False,f"{type(exc).__name__}: {exc}")

def streamlit_health():
    sock=socket.socket(); sock.bind(("127.0.0.1",0)); port=sock.getsockname()[1]; sock.close()
    env=os.environ.copy()
    env.update({
        "WARROOM_DISABLE_AUTOSTART":"1",
        "WARROOM_NETWORK_MODE":"offline",
        "WARROOM_RADAR_INITIAL_DELAY_SECONDS":"9999",
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS":"false",
    })
    cmd=[sys.executable,"-m","streamlit","run","app.py","--server.headless=true",f"--server.port={port}","--server.address=127.0.0.1"]
    proc=subprocess.Popen(cmd,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    ok=False; body=""; log=""
    try:
        deadline=time.time()+45
        while time.time()<deadline:
            if proc.poll() is not None: break
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health",timeout=1.5) as r:
                    body=r.read().decode("utf-8","replace")
                    if r.status==200 and "ok" in body.lower(): ok=True; break
            except Exception:
                time.sleep(.5)
        if not ok and proc.stdout:
            time.sleep(.3)
            try: log=proc.stdout.read(8000)
            except Exception: pass
    finally:
        proc.terminate()
        try: proc.wait(timeout=8)
        except Exception:
            proc.kill(); proc.wait(timeout=4)
    record("streamlit_health",ok,f"port={port}; body={body}; log={log}")

def source_inventory():
    try:
        dev=json.loads((ROOT/'data'/'current_developments.json').read_text(encoding='utf-8'))
        watch=json.loads((ROOT/'data'/'source_watchlist.json').read_text(encoding='utf-8'))
        markets={x['market'] for x in dev['entries']}
        crypto_categories={x['category'] for x in dev['entries'] if x['market']=='crypto'}
        good={'us','idx','crypto','commodity','fx'} <= markets and len(watch['sources'])>=20 and len(crypto_categories)>=6
        record('current_source_inventory',good,f"markets={sorted(markets)}; sources={len(watch['sources'])}; crypto_categories={sorted(crypto_categories)}")
    except Exception as exc:
        record('current_source_inventory',False,f"{type(exc).__name__}: {exc}")

def main():
    run_script('decision_intelligence_contract','validate_v33_decision_intelligence.py',300)
    run_script('arrow_lineage_contract','validate_arrow_lineage.py',180)
    run_script('live_stack_fixture_contract','validate_live_stack.py',300)
    run_script('gcfis_synthetic_correctness','gcfis/tests/test_all.py',300)
    source_inventory()
    streamlit_health()
    report={
      'version':'3.3',
      'suite':'master_operational_release',
      'status':'PASS' if all(x['passed'] for x in CHECKS) else 'FAIL',
      'passed':sum(x['passed'] for x in CHECKS),'total':len(CHECKS),'checks':CHECKS,
      'operational_permission':'READY_FOR_USER_REVIEW' if all(x['passed'] for x in CHECKS) else 'BLOCKED',
      'capital_permission':'CAPITAL_BLOCKED',
      'proof_boundary':[
        'Synthetic/parser/semantic correctness is not predictive edge.',
        'Paid-provider reachability and entitlements require user credentials.',
        'Point-in-time WFA, untouched lockbox and mature prospective evidence remain separate gates.',
        'No monitoring system guarantees complete capture of every future development.'
      ]
    }
    (ROOT/'V33_MASTER_RELEASE_REPORT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    if report['status']!='PASS': raise SystemExit(1)

if __name__=='__main__': main()
