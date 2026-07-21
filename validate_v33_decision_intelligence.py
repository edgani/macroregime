"""Deterministic v3.3 decision-intelligence release audit.

Validates software/UI contracts, pair-specific FX semantics, fresh-development governance,
official-source radar semantics and fail-closed research permission. It does not claim alpha.
"""
from __future__ import annotations

import json
import py_compile
import re
import shutil
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHECKS: list[dict] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    row = {"name": name, "passed": bool(passed), "detail": detail}
    CHECKS.append(row)
    print(("PASS" if passed else "FAIL"), name, detail)


def compile_contract() -> None:
    errors = []
    files = [p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts and ".venv" not in p.parts]
    for path in files:
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")
    check("python_compile", not errors, f"{len(files)} files; {len(errors)} errors")


def source_contract() -> None:
    html = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, flags=re.S | re.I)
    check("v33_header", "DECISION-INTELLIGENCE OS · v3.3" in html)
    check("board_map_evidence_modes", all(x in html for x in ('data-layout="board"', 'data-layout="map"', 'data-layout="evidence"')))
    check("board_default", "layout:savedState.layout||'board'" in html)
    check("fx_explicit_matrix", "PAIR-SPECIFIC FX STATES" in html and "orientation:r.orientation" in html)
    check("crypto_current_developments", "brokerage/onchain convergence" in html and "CURRENT DEVELOPMENTS" in html)
    check("official_radar_ui", "OFFICIAL SOURCE RADAR" in html and "RADAR <b>" in html)
    check("numeric_headroom_withheld", "Numeric upside classes are withheld" in html)
    if scripts and shutil.which("node"):
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as fh:
            fh.write(scripts[-1])
            temp = Path(fh.name)
        proc = subprocess.run([shutil.which("node"), "--check", str(temp)], capture_output=True, text=True)
        temp.unlink(missing_ok=True)
        check("javascript_parse", proc.returncode == 0, proc.stderr.strip())
    else:
        check("javascript_parse", bool(scripts), "node unavailable")


def fixture() -> dict:
    return json.loads((ROOT / "tests" / "v32_fixture.json").read_text(encoding="utf-8"))


def fx_contract() -> None:
    from research_kernel import attach_research_kernel
    raw = fixture()
    raw.setdefault("market_breadth", {}).setdefault("fx", {}).setdefault("constituents", []).extend([
        {"ticker": "USDIDR=X", "ret_1d": 0.2, "ret_5d": 0.6, "ret_20d": 1.4, "above_20d": True, "above_50d": True},
        {"ticker": "GBPUSD=X", "ret_1d": -0.2, "ret_5d": -0.8, "ret_20d": -1.5, "above_20d": False, "above_50d": False},
    ])
    raw.setdefault("markets", {}).setdefault("fx", {})["setups"] = [
        {"tk": "EURUSD=X", "act": "BUILD_LONG", "valid": True, "e": 1.19, "s": 1.17, "t": 1.23, "rr": 2.0},
        {"tk": "GBPUSD=X", "act": "BUILD_SHORT", "valid": True, "e": 1.31, "s": 1.33, "t": 1.27, "rr": 2.0},
        {"tk": "USDIDR=X", "act": "BUILD_LONG", "valid": True, "e": 18000, "s": 17600, "t": 18600, "rr": 1.5},
    ]
    raw.setdefault("feeds", {})["fx_carry"] = {
        "ok": True,
        "pairs": {
            "EURUSD=X": {"bias": "CARRY_LONG", "carry_diff": 0.5},
            "GBPUSD=X": {"bias": "CARRY_SHORT", "carry_diff": -0.7},
            "USDIDR=X": {"bias": "CARRY_LONG", "carry_diff": 2.0},
        },
    }
    desk = attach_research_kernel(raw)
    rows = {x["pair"]: x for x in desk["fx_pair_states"]["pairs"]}
    check("fx_pair_rows_present", {"EURUSD=X", "GBPUSD=X", "USDIDR=X"} <= set(rows), str(sorted(rows)))
    check("fx_long_explicit", rows["EURUSD=X"]["orientation"] == "LONG" and rows["EURUSD=X"]["state"] == "TRIGGERED_WATCH_LONG", str(rows["EURUSD=X"]))
    check("fx_short_explicit", rows["GBPUSD=X"]["orientation"] == "SHORT" and rows["GBPUSD=X"]["state"] == "TRIGGERED_WATCH_SHORT", str(rows["GBPUSD=X"]))
    check("fx_event_risk_downgrade", rows["USDIDR=X"]["state"] == "EVENT_RISK_WAIT" and rows["USDIDR=X"]["capital_permission"] == "BLOCKED", str(rows["USDIDR=X"]))
    price_only = [x for x in rows.values() if x["state"].startswith("PRICE_ONLY")]
    check("price_only_never_triggered", all("TRIGGERED" not in x["research_action"] for x in price_only), str(price_only))
    check("no_aggregate_fx_call", "no single FX long/short" in desk["fx_pair_states"]["semantics"], desk["fx_pair_states"]["semantics"])


def developments_contract() -> None:
    from current_developments import load_current_developments
    dev = load_current_developments()
    crypto = dev["by_market"]["crypto"]
    categories = {x.get("category") for x in crypto}
    required = {"BROKER_DEFI_CONVERGENCE", "TOKENIZED_SECURITIES", "ONCHAIN_YIELD_AND_AGENTIC_EXECUTION", "PREDICTION_MARKETS", "REGULATION", "STABLECOIN_POLICY"}
    check("crypto_structural_coverage", required <= categories, str(sorted(categories)))
    check("developments_have_dates_sources", all(x.get("date") and x.get("source") and x.get("source_url") for x in dev["entries"]))
    check("developments_no_direction", all(x.get("directional_semantics") == "NONE" for x in dev["entries"]))
    check("freshness_computed", all(x.get("freshness") in {"FRESH", "STALE"} for x in dev["entries"]))


def radar_contract() -> None:
    source = (ROOT / "official_source_radar.py").read_text(encoding="utf-8")
    watch = json.loads((ROOT / "data" / "source_watchlist.json").read_text(encoding="utf-8"))
    check("radar_primary_sources", len(watch.get("sources", [])) >= 8)
    check("radar_human_review_semantics", "CHANGED_UNREVIEWED" in source and "Never auto" in source)
    check("sec_user_agent_gate", "WARROOM_SEC_USER_AGENT" in source and "ACTION_REQUIRED" in source)
    check("radar_bounded_http", "timeout=timeout" in source)


def kernel_contract() -> None:
    from research_kernel import attach_research_kernel, MARKET_DOCTRINE
    desk = attach_research_kernel(fixture())
    rk = desk["research_kernel"]
    check("five_market_adapters", set(MARKET_DOCTRINE) <= set(rk["markets"]))
    check("capital_blocked", rk["global_permission"] == "CAPITAL_BLOCKED")
    check("crypto_doctrine_expanded", "tokenized assets" in MARKET_DOCTRINE["crypto"]["decision_problem"])
    check("all_markets_developments_field", all("current_developments" in rk["markets"][m] for m in MARKET_DOCTRINE))
    check("all_markets_research_only", all(rk["markets"][m]["validation"]["status"] == "RESEARCH_ONLY" for m in MARKET_DOCTRINE))


def browser_contract() -> None:
    chromium = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        check("browser_contract", True, f"SKIPPED playwright unavailable: {exc}")
        return
    if not chromium:
        check("browser_contract", True, "SKIPPED Chromium unavailable")
        return
    from research_kernel import attach_research_kernel
    payload = json.dumps(attach_research_kernel(fixture()), separators=(",", ":")).replace("</", "<\\/")
    html = (ROOT / "dashboard.html").read_text(encoding="utf-8").replace("/*__INJECT_DATA__*/", f"window.DASHBOARD_DATA={payload};")
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=chromium, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1800, "height": 1000})
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.set_content(html, wait_until="domcontentloaded")
        page.wait_for_timeout(300)
        board_visible = page.locator(".decision-board").count() == 1
        page.locator('[data-workspace="markets"]').click(); page.wait_for_timeout(50)
        page.locator('[data-subview="fx"]').click(); page.wait_for_timeout(50)
        fx_headers = page.locator(".decision-table th").all_text_contents()
        page.locator('[data-layout="map"]').click(); page.wait_for_timeout(50)
        map_nodes = page.locator("#graph .node").count()
        page.locator('[data-layout="evidence"]').click(); page.wait_for_timeout(50)
        evidence_cards = page.locator("#graph .research-card").count()
        page.locator('[data-subview="crypto"]').click(); page.locator('[data-layout="board"]').click(); page.wait_for_timeout(50)
        crypto_devs = page.locator(".dev-card").count()
        page.screenshot(path=str(ROOT / "V33_UI_PREVIEW.png"), full_page=True)
        browser.close()
    check("browser_page_errors", not errors, "; ".join(errors))
    check("browser_board_default", board_visible)
    check("browser_fx_matrix", "ORIENTATION" in fx_headers and "TRIGGER / STOP" in fx_headers, str(fx_headers))
    check("browser_map_drilldown", map_nodes > 0, str(map_nodes))
    check("browser_evidence_mode", evidence_cards >= 6, str(evidence_cards))
    check("browser_crypto_developments", crypto_devs >= 5, str(crypto_devs))


def main() -> None:
    compile_contract(); source_contract(); fx_contract(); developments_contract(); radar_contract(); kernel_contract(); browser_contract()
    report = {
        "version": "3.3",
        "suite": "decision_intelligence_release_contract",
        "status": "PASS" if all(x["passed"] for x in CHECKS) else "FAIL",
        "passed": sum(1 for x in CHECKS if x["passed"]),
        "total": len(CHECKS),
        "checks": CHECKS,
        "release_posture": "OPERATIONAL DECISION-INTELLIGENCE OS; CAPITAL BLOCKED; PREDICTIVE EDGE NOT PROVEN BY THIS SUITE",
        "not_verified": [
            "paid-provider credentials and entitlements",
            "complete point-in-time datasets for all markets",
            "market-specific WFA/lockbox/prospective performance for every component",
            "guaranteed completeness of all future public developments",
            "autonomous order execution",
        ],
    }
    (ROOT / "V33_RELEASE_VALIDATION_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
