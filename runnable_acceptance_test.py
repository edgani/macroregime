from pathlib import Path
import ast, json, subprocess, sys
ROOT=Path(__file__).resolve().parent
checks=[]
def ck(name, cond, detail=''): checks.append({'check':name,'pass':bool(cond),'detail':detail})
for f in ['app.py','run.py','run_eros.bat','setup_windows.bat','run_cli.bat','run_eros.sh','requirements.txt']:
    ck(f'file:{f}', (ROOT/f).exists())
# parse active python entrypoints
for f in ['app.py','run.py','run_eros.py','final_core/app_model.py','final_core/build_dashboard.py']:
    try: ast.parse((ROOT/f).read_text(encoding='utf-8')); ck(f'ast:{f}',True)
    except Exception as e: ck(f'ast:{f}',False,repr(e))
# active app must not import quarantined legacy package
active='\n'.join((ROOT/f).read_text(errors='ignore') for f in ['app.py','run.py']+[str(p.relative_to(ROOT)) for p in (ROOT/'final_core').glob('*.py')])
ck('legacy_not_imported_in_active','legacy_warroom_original' not in active.replace('legacy_warroom_original/',''))
# app model must load current artifacts and production engine must execute
p=subprocess.run([sys.executable,'run.py'],cwd=ROOT,capture_output=True,text=True)
ck('cli_run',p.returncode==0,(p.stdout+p.stderr)[-2000:])
try:
    from final_core.app_model import load_app_state
    st=load_app_state(False)
    ck('app_model_sections',all(k in st for k in ['run','validation_summary','strict','engine_registry','metric_registry','data_coverage','experiment_ledger']))
    ck('app_model_current_action',bool(st['run'].get('current_action')),str(st['run'].get('current_action')))
except Exception as e:
    ck('app_model_sections',False,repr(e)); ck('app_model_current_action',False,repr(e))
# original Warroom must be present as reference
for f in ['legacy_warroom_original/app.py','legacy_warroom_original/run.py','legacy_warroom_original/data_layer.py','legacy_warroom_original/warroom/decision_engine.py','legacy_warroom_original/gcfis/orchestrator.py']:
    ck(f'legacy_preserved:{f}',(ROOT/f).exists())
# dashboard generated and 5 tabs
html=(ROOT/'dashboard.html').read_text(encoding='utf-8') if (ROOT/'dashboard.html').exists() else ''
ck('dashboard_five_tabs',all(x in html for x in ['Command Center','Global Explorer','Opportunity Engine','Portfolio','Research Lab']))
ck('dashboard_has_payload','const D=' in html and 'NO QUALIFIED OPPORTUNITY' in html)
# requirements must include runnable UI + parquet support
req=(ROOT/'requirements.txt').read_text().lower()
ck('requirements_streamlit','streamlit' in req)
ck('requirements_pyarrow','pyarrow' in req)
result={'pass':all(x['pass'] for x in checks),'checks':checks}
(ROOT/'FINAL_HANDOFF'/'101_RUNNABLE_APP_ACCEPTANCE.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2)); raise SystemExit(0 if result['pass'] else 1)
