from pathlib import Path
import json, html
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'FINAL_HANDOFF'
run=json.loads((OUT/'52_CURRENT_PRODUCTION_RUN.json').read_text()) if (OUT/'52_CURRENT_PRODUCTION_RUN.json').exists() else {}
summary=json.loads((OUT/'51_MULTI_ENGINE_VALIDATION_SUMMARY.json').read_text()) if (OUT/'51_MULTI_ENGINE_VALIDATION_SUMMARY.json').exists() else {}
js=json.dumps({'run':run,'summary':summary})
page=f'''<!doctype html><meta charset="utf-8"><title>EROS Command Center</title>
<style>body{{font:14px system-ui;background:#0b0e14;color:#e8edf5;margin:0}}nav{{display:flex;gap:8px;padding:16px;position:sticky;top:0;background:#111722}}button{{background:#1a2230;color:#fff;border:1px solid #334;padding:10px 14px;border-radius:8px}}.tab{{display:none;padding:20px}}.tab.on{{display:block}}pre{{white-space:pre-wrap;background:#111722;padding:14px;border-radius:10px}}.card{{background:#111722;padding:14px;margin:10px 0;border-radius:10px}}</style>
<nav>{''.join(f'<button onclick="show(\'{x}\')">{x}</button>' for x in ['Command Center','Global Explorer','Opportunity Engine','Portfolio','Research Lab'])}</nav>
<div id="Command Center" class="tab on"><h2>Command Center</h2><div class="card" id="cc"></div></div>
<div id="Global Explorer" class="tab"><h2>Global Explorer</h2><pre id="ge"></pre></div>
<div id="Opportunity Engine" class="tab"><h2>Opportunity Engine</h2><pre id="oe"></pre></div>
<div id="Portfolio" class="tab"><h2>Portfolio</h2><p>Fail-closed until qualified opportunities and calibrated portfolio inputs exist.</p></div>
<div id="Research Lab" class="tab"><h2>Research Lab</h2><pre id="rl"></pre></div>
<script>const D={js};function show(x){{document.querySelectorAll('.tab').forEach(e=>e.classList.remove('on'));document.getElementById(x).classList.add('on')}}
document.getElementById('cc').innerText='Status: '+(D.run.system_status||'UNKNOWN')+'\nAction: '+(D.run.current_action||'UNKNOWN')+'\nScenarios: '+(D.run.scenario_count||0);
document.getElementById('ge').innerText=JSON.stringify(D.run.scenarios||[],null,2);document.getElementById('oe').innerText=JSON.stringify({{asset_candidates:D.run.asset_candidates||[],ticker_decisions:D.run.ticker_decisions||[],qualified:D.run.qualified_opportunities||[]}},null,2);document.getElementById('rl').innerText=JSON.stringify(D.summary,null,2);</script>'''
(ROOT/'dashboard.html').write_text(page,encoding='utf-8')
print(ROOT/'dashboard.html')
