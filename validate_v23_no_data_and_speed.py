from __future__ import annotations
from pathlib import Path
import json, os, re, subprocess, sys, tempfile

HERE=Path(__file__).resolve().parent
checks=[]
def check(name, cond):
    checks.append((name,bool(cond)))
    if not cond: raise AssertionError(name)

# Static architecture checks
app=(HERE/'app.py').read_text(encoding='utf-8')
worker=(HERE/'warroom_data_worker.py').read_text(encoding='utf-8')
dash=(HERE/'dashboard.html').read_text(encoding='utf-8')
loader=(HERE/'data/loader.py').read_text(encoding='utf-8')
full=(HERE/'full_live_data_hub.py').read_text(encoding='utf-8')
check('Streamlit reads local snapshot', 'read_snapshot' in app and 'collect_live_market_intelligence' not in app)
check('Background worker owns collectors', 'collect_live_market_intelligence' in worker and 'collect_full_live_data' in worker)
check('Hard timeout around core loaders', 'build_core_bounded' in worker and 'process.terminate()' in worker)
check('Canonical FX aliases', '"USDJPY=X": "JPY=X"' in loader and '"USDIDR=X": "IDR=X"' in loader)
check('Bounded Yahoo serial retries', 'WARROOM_YF_RETRY_CAP' in loader)
check('Persistent price cache', 'WARROOM_PRICE_DISK_TTL' in loader and 'price_cache.pkl' in loader)
check('NO_SIGNAL distinguished from NO_DATA', 'NO_SIGNAL is not NO_DATA' in dash)
check('Company Intel no longer requires aligned Alpha', '||pool[0]' in dash)
check('Coverage core vs optional', 'CORE_DATASETS_BY_TAB' in full and 'optional_missing' in full)
check('SEC public setup is ACTION_REQUIRED', 'state="ACTION_REQUIRED"' in full)
check('CFTC official CSV fallback', '_cftc_csv_fallback' in full)
check('Liquid option anchors reserved', 'WARROOM_OPTIONS_ANCHORS' in (HERE/'live_market_intelligence.py').read_text())
check('No generic modulo arrow routing', '%ids.length' not in dash and 'j %' not in dash)

# Syntax checks
ok=True
for py in HERE.rglob('*.py'):
    try: compile(py.read_text(encoding='utf-8'),str(py),'exec')
    except Exception as exc:
        print('PYTHON FAIL',py,exc);ok=False
check('All Python files compile',ok)
scripts='\n'.join(re.findall(r'<script[^>]*>(.*?)</script>',dash,re.S))
js=HERE/'.cache'/'dashboard_check.js';js.parent.mkdir(exist_ok=True);js.write_text(scripts,encoding='utf-8')
node=subprocess.run(['node','--check',str(js)],capture_output=True,text=True)
check('Dashboard JavaScript parses',node.returncode==0)

# Offline state: missing data must remain missing and worker must finish without network.
env=dict(os.environ);env['WARROOM_NETWORK_MODE']='offline'
run=subprocess.run([sys.executable,str(HERE/'warroom_data_worker.py'),'--once'],cwd=HERE,env=env,capture_output=True,text=True,timeout=60)
check('Offline worker completes',run.returncode==0)
snapshot=json.loads((HERE/'runtime/desk_snapshot.json').read_text(encoding='utf-8'))
check('Offline does not create synthetic market source',snapshot.get('meta',{}).get('source')!='SYNTHETIC_TEST')
check('SEC missing contact shown as action required',snapshot.get('full_live_data',{}).get('tab_coverage',{}).get('institutional',{}).get('state')=='ACTION_REQUIRED')
check('Offline derivatives not falsely live',snapshot.get('full_live_data',{}).get('tab_coverage',{}).get('derivatives_squeeze',{}).get('state')!='LIVE')

report={'passed':sum(v for _,v in checks),'total':len(checks),'checks':[{'name':n,'passed':v} for n,v in checks]}
(HERE/'V23_VALIDATION_REPORT.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
