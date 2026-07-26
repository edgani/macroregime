from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VIEWS = ["mc","macro","ew","alpha","co","us","ihsg","crypto","commod","fx","flow","inst","deriv","sc","kg","execution","research","rc","datahealth"]
checks: dict[str, object] = {}

def check(name: str, ok: bool, detail: object = None) -> None:
    checks[name] = {"passed": bool(ok), "detail": detail}
    if not ok:
        print(f"FAIL {name}: {detail}", file=sys.stderr)

def main() -> None:
    html = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, re.S | re.I)
    js = scripts[-1]
    tmp_root = Path(tempfile.mkdtemp(prefix="warroom_v63_tabs_"))
    js_path = tmp_root / "v63_dashboard_check.js"
    js_path.write_text(js, encoding="utf-8")
    proc = subprocess.run(["node", "--check", str(js_path)], capture_output=True, text=True)
    check("javascript_parse", proc.returncode == 0, proc.stderr[-1000:])

    desk_path = ROOT / "runtime" / "v63_fixture_desk.json"
    if not desk_path.exists():
        proc = subprocess.run([
            sys.executable, "run.py", "--synthetic", "--markets", "us,idx,crypto,commodity,fx",
            "--out", str(desk_path), "--html", str(ROOT / "runtime" / "v63_fixture_dashboard.html")
        ], cwd=ROOT, capture_output=True, text=True, timeout=240)
        check("fixture_generation", proc.returncode == 0, (proc.stdout + proc.stderr)[-1000:])
    desk = json.loads(desk_path.read_text(encoding="utf-8"))
    # Deterministic company-candidate guard fixture: SPY ranks above AAPL, but must be excluded.
    us = desk.setdefault("markets", {}).setdefault("us", {})
    us["data_state"] = "LIVE"; us["bias"] = "NEUTRAL"; us["bias_state"] = "PARTIAL"
    us.setdefault("funnel", {})["universe"] = max(2, int(us.get("funnel", {}).get("universe", 0) or 0))
    us["funnel"]["setups"] = 2
    us["setups"] = [
        {"tk":"SPY","market":"us","act":"POSITIVE_PRICE_CONTEXT","dir":"long","setup_rank":99,"conv":99,"valid":False,"directional_permission":False,"capital_permission":"BLOCKED","why":"ETF benchmark guard"},
        {"tk":"AAPL","market":"us","act":"POSITIVE_PRICE_CONTEXT","dir":"long","setup_rank":80,"conv":80,"valid":False,"directional_permission":False,"capital_permission":"BLOCKED","why":"company guard fixture"},
    ]
    # No official HY OAS loaded: credit nodes must fail closed, not reuse fragility.
    desk["macro_observations"] = {}
    fixture = tmp_root / "v63_dashboard_audit_fixture.json"
    fixture.write_text(json.dumps(desk, separators=(",", ":")), encoding="utf-8")

    expose_at = "document.querySelectorAll('.seg')"
    if expose_at not in js:
        raise RuntimeError("dashboard exposure anchor missing")
    core = js.rsplit(expose_at, 1)[0]
    if not core.rstrip().endswith("\n"):
        core += "\n"
    core += "globalThis.__audit={setView:(v)=>{state.view=v;state.selected=null;state.selectedTicker=null;return getModel();},getState:()=>state};\n})();\n"
    runner = tmp_root / "v63_model_audit_runner.js"
    runner.write_text(
        "const fs=require('fs'),vm=require('vm');\n"
        f"const D=JSON.parse(fs.readFileSync({json.dumps(str(fixture))},'utf8'));\n"
        "const noop=()=>{}; const el={innerHTML:'',textContent:'',dataset:{},classList:{toggle:noop,add:noop,remove:noop},addEventListener:noop};\n"
        "const document={getElementById:()=>el,querySelectorAll:()=>[],querySelector:()=>el};\n"
        "const localStorage={getItem:()=>null,setItem:noop};\n"
        "const window={DASHBOARD_DATA:D,parent:{location:{href:'http://localhost/app/'}},location:{href:'http://localhost/'}};\n"
        "const sandbox={window,document,localStorage,location:{search:''},URL,URLSearchParams,Date,Math,JSON,Number,String,Boolean,Array,Object,Set,Map,RegExp,console,setTimeout,clearTimeout,AbortController,fetch:async()=>{throw new Error('disabled')}};\n"
        "vm.createContext(sandbox);\n"
        + "vm.runInContext(" + json.dumps(core) + ",sandbox,{timeout:10000});\n"
        + f"const views={json.dumps(VIEWS)}; const out={{}}; for(const v of views)out[v]=sandbox.__audit.setView(v); console.log(JSON.stringify(out));\n",
        encoding="utf-8",
    )
    proc = subprocess.run(["node", str(runner)], capture_output=True, text=True, timeout=60)
    check("all_tab_model_runner", proc.returncode == 0, proc.stderr[-2000:])
    if proc.returncode:
        models = {}
    else:
        models = json.loads(proc.stdout)
    (ROOT / "V63_TAB_MODEL_AUDIT.json").write_text(json.dumps(models, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    check("all_19_views_evaluated", set(models) == set(VIEWS), sorted(models))
    check("all_views_have_graph_and_rail", all(isinstance(m.get("graph",{}).get("nodes"), list) and isinstance(m.get("rail"), dict) for m in models.values()), {k:(len(v.get('graph',{}).get('nodes',[])),bool(v.get('rail'))) for k,v in models.items()})
    check("all_views_show_proof_and_capital", all(m.get("proof",{}).get("state") and m.get("proof",{}).get("capital") == "BLOCKED" and "PROOF " in m.get("sub","") and "CAPITAL BLOCKED" in m.get("sub","") for m in models.values()))

    company = models.get("co", {})
    check("company_excludes_benchmark_etf", company.get("rail",{}).get("title") == "AAPL", company.get("rail",{}).get("title"))
    check("company_valuation_fail_closed", next((n.get("value") for n in company.get("graph",{}).get("nodes",[]) if n.get("id")=="valuation"), None) in {"WITHHELD","RESEARCH NOT MAPPED","NO_DATA"}, company.get("graph",{}).get("nodes",[]))

    macro_credit = next((n for n in models.get("macro",{}).get("graph",{}).get("nodes",[]) if n.get("id")=="credit"), {})
    early_credit = next((n for n in models.get("ew",{}).get("graph",{}).get("nodes",[]) if n.get("id")=="credit2"), {})
    check("macro_credit_not_fragility_proxy", macro_credit.get("value") == "NO_DATA" and macro_credit.get("evidence") == "observed", macro_credit)
    check("early_credit_not_fragility_proxy", early_credit.get("value") == "NO_DATA" and early_credit.get("evidence") == "observed", early_credit)
    check("macro_roc_labeled_inferred", all(next((n for n in models.get('macro',{}).get('graph',{}).get('nodes',[]) if n.get('id')==nid),{}).get('evidence')=='inferred' for nid in ('growth','infl','liqm')))

    check("structural_supply_not_ranked", all((q.get("score") or 0) == 0 and "STRUCTURAL REFERENCE" in q.get("stage","") for q in models.get("sc",{}).get("queue",[])), models.get("sc",{}).get("queue",[]))
    check("structural_knowledge_not_ranked", all((q.get("score") or 0) == 0 and "STRUCTURAL REFERENCE" in q.get("stage","") for q in models.get("kg",{}).get("queue",[])), models.get("kg",{}).get("queue",[]))

    research_text = json.dumps(models.get("research",{}))
    validation_text = json.dumps(models.get("rc",{}))
    check("research_includes_v61_v62", "price_derived_network_diffusion" in research_text and "discrete_event_origin_proxy" in research_text and "232468" in research_text)
    check("validation_includes_v61_v62", "price_derived_network_diffusion" in validation_text and "discrete_event_origin_proxy" in validation_text and "232468" in validation_text)
    check("validation_zero_production", models.get("rc",{}).get("rail",{}).get("confidence") == 0 and "0 production-eligible" in models.get("rc",{}).get("rail",{}).get("desc", ""), models.get("rc",{}).get("rail",{}))
    check("mission_no_capital_action", "CAPITAL" in models.get("mc",{}).get("rail",{}).get("action","") or "NO CAPITAL" in models.get("mc",{}).get("rail",{}).get("action",""), models.get("mc",{}).get("rail",{}))
    check("market_tabs_not_promoted", all(models.get(v,{}).get("proof",{}).get("state") == "DESCRIPTIVE_CONTEXT_ONLY" for v in ("us","ihsg","crypto","commod","fx")), {v:models.get(v,{}).get('proof') for v in ("us","ihsg","crypto","commod","fx")})
    check("global_capital_blocked", desk.get("proof_status",{}).get("predictive_components_promoted") == 0 and desk.get("proof_status",{}).get("capital_permission") == "BLOCKED", desk.get("proof_status"))

    report = {
        "schema": "warroom.v63.all_tab_reaudit",
        "status": "PASS" if all(v["passed"] for v in checks.values()) else "FAIL",
        "passed": sum(v["passed"] for v in checks.values()),
        "total": len(checks),
        "checks": checks,
        "views": VIEWS,
        "predictive_components_promoted": 0,
        "capital_permission": "BLOCKED",
        "claim_boundary": "All tabs are contract-checked and proof-labeled. This is software/UI correctness, not predictive proof.",
    }
    (ROOT / "V63_ALL_TAB_VALIDATION.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"{report['passed']}/{report['total']} {report['status']}")
    shutil.rmtree(tmp_root, ignore_errors=True)
    raise SystemExit(0 if report["status"] == "PASS" else 1)

if __name__ == "__main__":
    main()
