"""War Room OS v4.2 deep-reaudit and fail-closed release validation.

This suite proves software contracts and governance behavior only. It deliberately cannot prove
predictive edge, profitability, target accuracy or production capital permission.
"""
from __future__ import annotations

import compileall
import json
import re
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHECKS: list[dict] = []


def check(name: str, passed: bool, detail="") -> None:
    row = {"name": name, "passed": bool(passed), "detail": str(detail)[-12000:]}
    CHECKS.append(row)
    print(("PASS" if passed else "FAIL"), name, row["detail"][:900])


def source_contract() -> None:
    html = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    run = (ROOT / "run.py").read_text(encoding="utf-8")
    ps = (ROOT / "price_setups.py").read_text(encoding="utf-8")
    dealer = (ROOT / "gcfis" / "engines" / "dealer.py").read_text(encoding="utf-8")
    fx = (ROOT / "fx_pair_state.py").read_text(encoding="utf-8")
    check("version_v42", "DECISION-INTELLIGENCE OS · v4.2" in html and "War Room OS v4.2" in run)
    check("no_generic_watch_labels", not any(x in html for x in ["WATCH LONG", "WATCH SHORT", "TRIGGERED WATCH LONG", "TRIGGERED WATCH SHORT"]), "dashboard")
    check("no_alpha_headroom_classes", not any(x in html for x in ["500x+", "50–500x", "50-500x", "+49,900%"]), "dashboard")
    check("setup_not_evidence_column", "SETUP / DATA" in html and '<th style="width:9%">EVIDENCE</th>' not in html)
    check("generic_context_claim_ceiling", "DESCRIPTIVE_PRICE_CONTEXT_ONLY" in ps and "directional_permission\": False" in ps)
    check("equal_weight_not_fitted", "mean(axis=1)" in ps and "NOT FITTED" in ps and "0.40" not in ps)
    check("dealer_sign_required", "dealer_sign" in dealer and "UNKNOWN_UNLESS" not in dealer and "calls are dealer-long" in dealer)
    check("fx_fail_closed", "selector_promoted" in fx and "DIRECTIONAL RESEARCH CONTEXT · NO TRADE" in fx)
    check("legacy_final_desk_not_exposed", '"desk_picks": {"picks": [], "state": "CAPITAL_BLOCKED"' in run)
    check("rotation_legacy_withheld", '"rotation_in": [], "rotation_out": []' in run)
    check("current_source_review_split", "source_verification" in (ROOT / "current_developments.py").read_text(encoding="utf-8") and "REVIEW_REQUIRED" in (ROOT / "current_developments.py").read_text(encoding="utf-8"))


def price_context_contract() -> None:
    import numpy as np
    import pandas as pd
    from price_setups import price_signal_setups
    rng = np.random.default_rng(42)
    idx = pd.date_range("2023-01-01", periods=420, freq="B")

    def frame(start, drift, vol=0.012, volume=2_000_000):
        r = rng.normal(drift, vol, len(idx))
        close = start * np.exp(np.cumsum(r))
        v = np.maximum(1, rng.normal(volume, volume * 0.15, len(idx))).astype(int)
        return pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * .99, "Close": close, "Volume": v}, index=idx)

    rows = price_signal_setups({
        "UP": frame(50, .0012),
        "DOWN": frame(50, -.0012),
        "MIX": frame(50, 0),
        "ILLIQ": frame(.25, .0015, volume=2_000),
    }, top=10, market_id="us")
    check("price_context_rows_exist", bool(rows), rows)
    check("price_context_unique", len({x["tk"] for x in rows}) == len(rows), [x["tk"] for x in rows])
    check("price_context_no_directional_permission", all(x.get("directional_permission") is False and x.get("capital_permission") == "BLOCKED" for x in rows), rows)
    check("price_context_allowed_actions", all(x.get("act") in {"POSITIVE_PRICE_CONTEXT", "NEGATIVE_PRICE_CONTEXT", "NO_TRADE_CONFLICTED", "LOW_LIQUIDITY_CONTEXT_ONLY"} for x in rows), [x.get("act") for x in rows])
    check("setup_rank_not_probability", all("not probability" in x.get("evidence_semantics", "").lower() for x in rows), rows)
    illiq = next((x for x in rows if x["tk"] == "ILLIQ"), {})
    check("liquidity_gate_visible", illiq.get("liquidity_state") == "BELOW_RESEARCH_FLOOR" and illiq.get("act") == "LOW_LIQUIDITY_CONTEXT_ONLY", illiq)


def capability_contract() -> None:
    from market_capabilities import derive_market_capabilities
    base = {"live_intelligence": {"us_options": [], "crypto_options": [], "statuses": []}, "full_live_data": {"statuses": []}}
    c = derive_market_capabilities(deepcopy(base))
    check("ihsg_options_disabled", c["idx"]["options_enabled"] is False and c["idx"]["options_data_state"] == "NOT_APPLICABLE", c["idx"])
    check("all_options_disabled_without_specific_data", all(c[m]["options_enabled"] is False for m in ("us", "crypto", "commodity", "fx")), c)
    desk = deepcopy(base)
    desk["live_intelligence"]["us_options"] = [{"ticker": "SPY", "state": "LIVE"}]
    desk["live_intelligence"]["crypto_options"] = [{"ticker": "BTC-USD", "state": "LIVE", "venue": "X"}]
    c2 = derive_market_capabilities(desk)
    check("us_options_per_instrument", c2["us"]["options_enabled"] and c2["us"]["option_instruments"] == ["SPY"], c2["us"])
    check("crypto_options_per_underlying", c2["crypto"]["options_enabled"] and c2["crypto"]["option_instruments"] == ["BTC"], c2["crypto"])
    desk = deepcopy(base)
    desk["full_live_data"]["statuses"] = [
        {"provider": "X", "dataset": "commodity futures COT", "state": "LIVE"},
        {"provider": "Y", "dataset": "FX spot", "state": "LIVE"},
    ]
    c3 = derive_market_capabilities(desk)
    check("futures_or_spot_do_not_enable_options", not c3["commodity"]["options_enabled"] and not c3["fx"]["options_enabled"], c3)


def dealer_contract() -> None:
    import pandas as pd
    from gcfis.engines.dealer import run_dealer
    chain = pd.DataFrame([
        {"strike": 100, "oi": 1000, "iv": .2, "type": "C", "T": 1/365},
        {"strike": 95, "oi": 800, "iv": .25, "type": "P", "T": 5/365},
        {"strike": 110, "oi": 500, "iv": .22, "type": "C", "T": 45/365},
    ])
    u = run_dealer(chain, 100)
    check("unsigned_dealer_context", u.get("ok") and u.get("dealer_sign_state") == "UNKNOWN" and u.get("regime") == "unknown" and u.get("gex") is None, u)
    check("dte_buckets_present", set(u.get("dte_buckets", {})) == {"0DTE", "1_7DTE", "8_30DTE", "31P_DTE"}, u)
    signed = chain.copy(); signed["dealer_sign"] = [-1, 1, -1]
    g = run_dealer(signed, 100)
    check("signed_dealer_only_explicit", g.get("dealer_sign_state") == "EXPLICIT" and g.get("gex") is not None and g.get("regime") != "unknown", g)


def valuation_and_proof_contract() -> None:
    from scenario_valuation import equity_scenarios, token_scenarios
    from proof_registry import default_registry, component_status
    from regime_tournament import build_regime_tournament
    check("equity_valuation_withheld_missing", equity_scenarios(100, {}).get("state") == "WITHHELD")
    eq = {k: {"demand": 100, "share": .1, "margin": .2, "multiple": 10, "net_debt": 0, "future_diluted_shares": 10} for k in ("bear", "base", "bull")}
    r = equity_scenarios(10, eq)
    check("scenario_range_no_uncalibrated_ev", r.get("state") == "SCENARIO_RANGE" and r.get("expected_return_pct") is None and r.get("probability_status") == "UNCALIBRATED", r)
    tok = {k: {"economic_activity": 100, "capture_rate": .1, "net_costs": 2, "multiple": 5, "future_diluted_supply": 100} for k in ("bear", "base", "bull")}
    tr = token_scenarios(100, tok)
    check("token_range_no_uncalibrated_ev", tr.get("state") == "SCENARIO_RANGE" and tr.get("expected_return_pct") is None, tr)
    reg = default_registry()
    check("zero_default_predictive_promotion", all(v.get("capital_permission") == "BLOCKED" for v in reg["components"].values()), reg)
    check("component_status_fail_closed", component_status("wasserstein_hmm").get("predictive_promoted") is False and component_status("wasserstein_hmm").get("capital_permission") == "BLOCKED")
    tour = build_regime_tournament()
    check("regime_tournament_no_winner", tour.get("winner") is None and all(x.get("selection_permission") == "BLOCKED" for x in tour.get("models", [])), tour)


def synthetic_snapshot() -> dict:
    path = ROOT / "runtime" / "v42_fixture_desk.json"
    html = ROOT / "runtime" / "v42_fixture_dashboard.html"
    proc = subprocess.run([sys.executable, str(ROOT / "run.py"), "--synthetic", "--markets", "us,idx,crypto,commodity,fx", "--out", str(path), "--html", str(html)], cwd=ROOT, capture_output=True, text=True, timeout=180)
    check("synthetic_runner", proc.returncode == 0 and path.exists() and html.exists(), (proc.stdout + proc.stderr)[-5000:])
    desk = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    # deterministic descriptive context rows so every market board exercises table semantics.
    for mid, ticker, direction in [("us","TESTUS","long"),("idx","TEST.JK","short"),("crypto","TEST-USD","long"),("commodity","TEST=F","short"),("fx","EURUSD=X","long")]:
        m = desk.setdefault("markets", {}).setdefault(mid, {"label":mid,"bias":"NEUTRAL","funnel":{}})
        m["bias"] = "NEUTRAL"; m["bias_state"] = "PARTIAL"; m["data_state"] = "LIVE"
        m.setdefault("funnel", {})["universe"] = max(1, m.get("funnel", {}).get("universe", 0));m["funnel"]["setups"] = 1
        m["setups"] = [{"tk":ticker,"market":mid,"act":"POSITIVE_PRICE_CONTEXT" if direction=="long" else "NEGATIVE_PRICE_CONTEXT","dir":direction,"setup_rank":70,"conv":70,"e":100,"s":95 if direction=="long" else 105,"t":110 if direction=="long" else 90,"rr":2,"valid":False,"directional_permission":False,"capital_permission":"BLOCKED","execution_state":"REFERENCE_GEOMETRY_ONLY","why":"deterministic descriptive fixture","agreement_count":3,"liquidity_state":"ELIGIBLE","evidence_semantics":"not probability"}]
    desk["institutional"]={"overall_state":"ACTION_REQUIRED","statuses":[{"provider":"SEC EDGAR","dataset":"filings","state":"ACTION_REQUIRED","note":"fixture"}],"events":[]}
    desk["live_intelligence"]={"overall_state":"NO_DATA","statuses":[],"events":[],"us_options":[],"crypto_options":[],"crypto_derivatives":[]}
    desk["full_live_data"]={"overall_state":"NO_DATA","statuses":[],"sec_fundamentals":[],"cftc":{},"databento":[]}
    from research_kernel import attach_research_kernel
    desk = attach_research_kernel(desk)
    return desk


def js_and_browser_contract(desk: dict) -> None:
    html_src=(ROOT/"dashboard.html").read_text(encoding="utf-8")
    scripts=re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>",html_src,re.S|re.I)
    node=shutil.which("node")
    temp=ROOT/"runtime"/"v42_dashboard_check.js";temp.parent.mkdir(exist_ok=True);temp.write_text("\n".join(scripts),encoding="utf-8")
    proc=subprocess.run([node,"--check",str(temp)],capture_output=True,text=True) if node else None
    check("javascript_parse", bool(proc and proc.returncode==0), proc.stderr if proc else "node missing")
    temp.unlink(missing_ok=True)
    try:
        from playwright.sync_api import sync_playwright
        chromium=shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
        if not chromium: raise RuntimeError("chromium missing")
        payload=json.dumps(desk,separators=(",",":"),default=str).replace("</","<\\/")
        html=html_src.replace("/*__INJECT_DATA__*/",f"window.DASHBOARD_DATA={payload};")
        mapping={"mc":"mission","macro":"regime","ew":"regime","alpha":"opportunities","co":"opportunities","us":"markets","ihsg":"markets","crypto":"markets","commod":"markets","fx":"markets","flow":"positioning","inst":"positioning","deriv":"positioning","sc":"causal","kg":"causal","execution":"execution","research":"research","rc":"research","datahealth":"research"}
        errors=[];counts={};texts={};orients={}
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,executable_path=chromium,args=["--no-sandbox"])
            page=browser.new_page(viewport={"width":1800,"height":1000});page.on("pageerror",lambda e:errors.append(str(e)))
            page.set_content(html,wait_until="domcontentloaded");page.wait_for_timeout(150)
            for view,ws in mapping.items():
                page.locator(f'[data-workspace="{ws}"]').click();page.wait_for_timeout(15)
                sub=page.locator(f'[data-subview="{view}"]')
                if sub.count():sub.click()
                page.wait_for_timeout(20)
                counts[view]=page.locator("[data-board-row]").count()
                texts[view]=" ".join(page.locator(".decision-table tbody").all_inner_texts()) if page.locator(".decision-table tbody").count() else ""
                orients[view]=page.locator(".decision-table tbody tr td:nth-child(3) .action").all_inner_texts() if page.locator(".decision-table").count() else []
            page.locator('[data-workspace="markets"]').click();page.locator('[data-subview="us"]').click();page.wait_for_timeout(30)
            page.screenshot(path=str(ROOT/"V42_DEEP_REAUDIT_PREVIEW.png"),full_page=True)
            browser.close()
        check("browser_no_page_errors", not errors, errors)
        check("all_19_views_have_rows", len(counts)==19 and all(v>0 for v in counts.values()), counts)
        market_text=" ".join(texts[v] for v in ("us","ihsg","crypto","commod"))
        check("market_ui_no_generic_trade_watch", not any(x in market_text for x in ("WATCH LONG","WATCH SHORT","TRIGGERED WATCH","BUILD LONG","BUILD SHORT")), market_text[:1500])
        check("ihsg_ui_no_short_orientation", "SHORT" not in orients.get("ihsg",[]), orients.get("ihsg"))
        check("alpha_ui_no_numeric_alpha", not any(x in texts.get("alpha","") for x in ("500x","EXPECTED RETURN","FAIR VALUE","WATCH LONG","WATCH SHORT")), texts.get("alpha","")[:1500])
        check("execution_ui_capital_blocked", "CAPITAL BLOCKED" in texts.get("execution","") and "SIZE ZERO" not in texts.get("execution","") or "CAPITAL BLOCKED" in texts.get("execution",""), texts.get("execution","")[:1200])
    except Exception as exc:
        check("browser_contract",False,f"{type(exc).__name__}: {exc}")


def main() -> None:
    (ROOT/"runtime").mkdir(exist_ok=True)
    source_contract();price_context_contract();capability_contract();dealer_contract();valuation_and_proof_contract()
    check("python_compile",compileall.compile_dir(str(ROOT),quiet=1,force=True))
    desk=synthetic_snapshot()
    check("snapshot_zero_promoted", (desk.get("proof_status") or {}).get("predictive_components_promoted")==0 and (desk.get("proof_status") or {}).get("capital_permission")=="BLOCKED", desk.get("proof_status"))
    check("snapshot_no_capital_picks", not (desk.get("desk_picks") or {}).get("picks"), desk.get("desk_picks"))
    check("current_developments_review_required", (desk.get("current_developments") or {}).get("review_required_count",0)>=1 and (desk.get("current_developments") or {}).get("reviewed_fresh_count",0)==0, desk.get("current_developments"))
    js_and_browser_contract(desk)
    report={"version":"4.2","suite":"deep_reaudit_fail_closed","status":"PASS" if all(x["passed"] for x in CHECKS) else "FAIL","passed":sum(x["passed"] for x in CHECKS),"total":len(CHECKS),"checks":CHECKS,"software_permission":"READY_FOR_USER_REVIEW" if all(x["passed"] for x in CHECKS) else "BLOCKED","predictive_components_promoted":0,"capital_permission":"BLOCKED","proof_boundary":"Software contracts are tested. Predictive proof requires external PIT WFA, one-time lockbox, costs/capacity and matured prospective outcomes."}
    (ROOT/"V42_DEEP_REAUDIT_VALIDATION_REPORT.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    if report["status"]!="PASS":raise SystemExit(1)

if __name__=="__main__":main()
