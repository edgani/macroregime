from __future__ import annotations
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "FINAL_HANDOFF"

TABS = ["Command Center", "Global Explorer", "Opportunity Engine", "Portfolio", "Research Lab"]


def _load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def build_dashboard(out_path: str | Path | None = None) -> Path:
    run = _load_json(OUT / "52_CURRENT_PRODUCTION_RUN.json", {})
    summary = _load_json(OUT / "51_MULTI_ENGINE_VALIDATION_SUMMARY.json", {})
    strict = _load_json(OUT / "100_STRICT_ACCEPTANCE_RESULT.json", {})
    payload = json.dumps({"run": run, "summary": summary, "strict": strict}, ensure_ascii=False)
    nav = "".join(f'<button onclick="showTab({json.dumps(x)})">{x}</button>' for x in TABS)
    page = f'''<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>EROS Warroom</title>
<style>
:root{{--bg:#090d13;--panel:#111823;--panel2:#151e2c;--line:#273348;--txt:#e8edf5;--muted:#96a2b5;--ok:#85d5a3;--warn:#e9bd67}}
*{{box-sizing:border-box}} body{{font:14px Inter,system-ui,Segoe UI,Arial;background:var(--bg);color:var(--txt);margin:0}}
nav{{display:flex;gap:8px;padding:14px 18px;position:sticky;top:0;background:rgba(9,13,19,.96);border-bottom:1px solid var(--line);z-index:10;flex-wrap:wrap}}
button{{background:var(--panel2);color:var(--txt);border:1px solid var(--line);padding:9px 13px;border-radius:8px;cursor:pointer}}
button:hover{{border-color:#53657f}} .tab{{display:none;padding:20px;max-width:1500px;margin:auto}}.tab.on{{display:block}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}}.card{{background:var(--panel);border:1px solid var(--line);padding:15px;border-radius:12px}}
.big{{font-size:24px;font-weight:700}} .muted{{color:var(--muted)}} pre{{white-space:pre-wrap;word-break:break-word;background:var(--panel);border:1px solid var(--line);padding:14px;border-radius:10px;max-height:70vh;overflow:auto}}
table{{width:100%;border-collapse:collapse;background:var(--panel)}}td,th{{padding:8px;border-bottom:1px solid var(--line);text-align:left}}h1,h2,h3{{margin-top:.2em}}
</style></head><body>
<nav>{nav}</nav>
<section id="Command Center" class="tab on"><h1>EROS Warroom</h1><div id="cc" class="grid"></div><h3>Current scenarios</h3><div id="scenarioCards" class="grid"></div></section>
<section id="Global Explorer" class="tab"><h2>Global Explorer</h2><pre id="ge"></pre></section>
<section id="Opportunity Engine" class="tab"><h2>Opportunity Engine</h2><pre id="oe"></pre></section>
<section id="Portfolio" class="tab"><h2>Portfolio</h2><div class="card" id="pf"></div></section>
<section id="Research Lab" class="tab"><h2>Research Lab</h2><pre id="rl"></pre></section>
<script>
const D={payload};
function showTab(x){{document.querySelectorAll('.tab').forEach(e=>e.classList.remove('on'));document.getElementById(x).classList.add('on')}}
function card(label,value,sub=''){{return `<div class="card"><div class="muted">${{label}}</div><div class="big">${{value}}</div><div class="muted">${{sub}}</div></div>`}}
const r=D.run||{{}}, s=D.summary||{{}}, a=D.strict||{{}};
document.getElementById('cc').innerHTML = card('System status', r.system_status||'UNKNOWN') + card('Current action', r.current_action||'UNKNOWN') + card('Scenarios', r.scenario_count||0) + card('Scientific engines tested', s.engine_count||0) + card('Production-proven models', s.production_proven_count??0) + card('Strict scope', a.scientific_full_scope_acceptance||'UNKNOWN');
const sc=r.scenarios||[]; document.getElementById('scenarioCards').innerHTML=sc.map(x=>`<div class="card"><b>${{x.title||x.scenario_id}}</b><div class="muted">${{x.scenario_id}}</div><p>${{(x.causal_chain||[]).join(' → ')}}</p><div>Probability: <b>${{x.probability_status||'UNKNOWN'}}</b></div><div>Action: <b>${{x.production_action||'UNKNOWN'}}</b></div></div>`).join('') || '<div class="card">No scenario.</div>';
document.getElementById('ge').textContent=JSON.stringify(sc,null,2);
document.getElementById('oe').textContent=JSON.stringify({{asset_candidates:r.asset_candidates||[],ticker_decisions:r.ticker_decisions||[],qualified_opportunities:r.qualified_opportunities||[]}},null,2);
document.getElementById('pf').textContent=(r.qualified_opportunities||[]).length ? JSON.stringify(r.qualified_opportunities,null,2) : 'NO QUALIFIED OPPORTUNITY — portfolio remains fail-closed until calibrated ticker/EV inputs exist.';
document.getElementById('rl').textContent=JSON.stringify({{validation_summary:s,strict_acceptance:a}},null,2);
</script></body></html>'''
    dest = Path(out_path) if out_path else ROOT / "dashboard.html"
    dest.write_text(page, encoding="utf-8")
    return dest


if __name__ == "__main__":
    print(build_dashboard())
