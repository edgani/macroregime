from pathlib import Path
import json, subprocess, sys, re
ROOT=Path(__file__).resolve().parent
checks={}
def chk(name,cond): checks[name]=bool(cond)
chk('ROOT_APP_EXISTS',(ROOT/'app.py').exists())
chk('WINDOWS_ONE_CLICK_EXISTS',(ROOT/'EROS.bat').exists())
chk('FIVE_TABS',all(x in (ROOT/'app.py').read_text() for x in ['COMMAND CENTER','GLOBAL EXPLORER','OPPORTUNITY ENGINE','PORTFOLIO','RESEARCH LAB']))
chk('NO_MANUAL_COMPANY_JSON_UPLOAD','file_uploader' not in (ROOT/'app.py').read_text())
prod='\n'.join(p.read_text(errors='ignore') for p in (ROOT/'eros').glob('*.py'))
chk('NO_SYNTHETIC_PRODUCTION','_synth(' not in prod and 'synthetic fallback' not in prod.lower())
chk('NO_CLASSIC_TECH_ALPHA',not re.search(r'\b(RSI|MACD|Bollinger|Fibonacci|price_setups)\b',prod,re.I))
chk('AUTO_FACTUAL_FETCH','fetch_all(force=' in (ROOT/'eros'/'pipeline.py').read_text())
chk('GENERAL_EVENT_ROUTER',(ROOT/'eros'/'event_router.py').exists())
chk('GENERAL_CAUSAL_GRAPH','GRAPH = {' in (ROOT/'eros'/'scenario_engine.py').read_text())
chk('GENERAL_NEWS_SCENARIO_DISCOVERY','radar_from_news_general' in (ROOT/'eros'/'scenario_engine.py').read_text())
chk('AUTO_ASSET_ENGINE',(ROOT/'eros'/'asset_engine.py').exists())
chk('AUTO_TICKER_CANDIDATES','generate_candidates' in (ROOT/'eros'/'pipeline.py').read_text())
chk('NO_FAKE_QUALIFICATION',"'qualified_opportunities':[]" in (ROOT/'eros'/'pipeline.py').read_text())
chk('LEGACY_WARROOM_PRESERVED',(ROOT/'legacy_warroom_reference'/'app.py').exists() and (ROOT/'legacy_warroom_reference'/'warroom').exists())
# executable tests
for name,cmd in {
 'TEST_NO_SYNTHETIC':[sys.executable,'tests/test_no_synthetic.py'],
 'TEST_PRODUCT_SHAPE':[sys.executable,'tests/test_product_shape.py'],
 'TEST_VISION_SCENARIOS':[sys.executable,'tests/test_vision_acceptance.py'],
 'TEST_END_TO_END':[sys.executable,'tests/test_end_to_end_mocked.py'],
 'TEST_FAIL_CLOSED':[sys.executable,'tests/test_fail_closed_no_data.py'],
}.items():
    p=subprocess.run(cmd,cwd=ROOT,env={**__import__('os').environ,'PYTHONPATH':str(ROOT)},capture_output=True,text=True)
    checks[name]=p.returncode==0
result={'status':'PASS' if all(checks.values()) else 'FAIL','passed':sum(checks.values()),'total':len(checks),'checks':checks,
        'scope_note':'Product/behavior acceptance. Does not convert unresolved PIT/scenario-calibration/ticker-OOS data debt into scientific proof.'}
out=ROOT/'FINAL_HANDOFF'/'102_VISION_PRODUCT_ACCEPTANCE.json'; out.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['status']=='PASS' else 1)
