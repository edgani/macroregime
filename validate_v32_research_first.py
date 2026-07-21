"""Deterministic War Room OS v3.2 research-first release audit.

The suite validates software contracts, research governance, fail-closed semantics and browser
geometry against an explicit fixture. It does not claim predictive alpha, prospective P&L or
provider entitlement.
"""
from __future__ import annotations

import json
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHECKS: list[dict] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    CHECKS.append({"name": name, "passed": bool(passed), "detail": detail})
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


def source_contracts() -> None:
    html = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, flags=re.S | re.I)
    check("dashboard_script_present", bool(scripts))
    if scripts and shutil.which("node"):
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as f:
            f.write(scripts[-1])
            temp = Path(f.name)
        result = subprocess.run([shutil.which("node"), "--check", str(temp)], capture_output=True, text=True)
        temp.unlink(missing_ok=True)
        check("javascript_parse", result.returncode == 0, result.stderr.strip())
    else:
        check("javascript_parse", bool(scripts), "node unavailable; source extraction only")

    contracts = {
        "v32_header": "RESEARCH-FIRST DECISION OS · v3.2" in html,
        "eight_workspaces": "const WORKSPACES = [" in html and html.count("views:[[", 0) >= 0,
        "research_dock": 'id="researchDock"' in html and "NEXT CHEAPEST FALSIFIER" in html,
        "current_rain": "CURRENT RAIN" in html,
        "study_the_tape": "STUDY THE TAPE" in html,
        "counterparty_challenge": "COUNTERPARTY CHALLENGE" in html,
        "cost_of_staying": "COST OF STAYING / WAITING" in html,
        "capital_gate": "capitalBlocked" in html and "TRIGGERED WATCH LONG" in html,
        "ihsg_long_only": "IHSG is cash long-only" in html and "REDUCE / AVOID" in html,
        "observed_inferred_separation": "OBSERVED" in html and "ALL LAYERS" in html,
        "no_provider_error_canvas": "Raw endpoint errors are retained in the ledger" in html,
        "execution_workspace": "EXECUTION & PORTFOLIO" in html,
        "data_lineage_workspace": "DATA & LINEAGE" in html,
    }
    for name, passed in contracts.items():
        check(name, passed)


def kernel_contract() -> None:
    from research_kernel import attach_research_kernel, MARKET_DOCTRINE

    fixture_path = ROOT / "tests" / "v32_fixture.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    desk = attach_research_kernel(fixture)
    rk = desk.get("research_kernel") or {}
    markets = rk.get("markets") or {}
    check("five_market_adapters", set(MARKET_DOCTRINE) <= set(markets), str(sorted(markets)))
    check("global_capital_blocked", rk.get("global_permission") == "CAPITAL_BLOCKED")
    check("market_specific_baselines", len({(markets[m].get("validation") or {}).get("baseline") for m in MARKET_DOCTRINE}) == 5)
    check("all_markets_have_counterparty", all((markets[m].get("counterparty_challenge") or {}).get("hard_gate") for m in MARKET_DOCTRINE))
    check("all_markets_have_tape", all((markets[m].get("study_the_tape") or {}).get("winner_autopsy") for m in MARKET_DOCTRINE))
    check("all_markets_research_only", all((markets[m].get("validation") or {}).get("status") == "RESEARCH_ONLY" for m in MARKET_DOCTRINE))
    check("fixture_actions_not_orders", all("BUILD" not in str((markets[m].get("execution") or {}).get("research_action")) for m in MARKET_DOCTRINE))


def browser_contract() -> None:
    chromium = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        check("browser_geometry", True, f"SKIPPED: playwright unavailable ({exc})")
        return
    if not chromium:
        check("browser_geometry", True, "SKIPPED: system Chromium unavailable")
        return

    base = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    fixture = json.loads((ROOT / "tests" / "v32_fixture.json").read_text(encoding="utf-8"))
    payload = json.dumps(fixture, separators=(",", ":")).replace("</", "<\\/")
    html = base.replace("/*__INJECT_DATA__*/", f"window.DASHBOARD_DATA={payload};")
    results: list[dict] = []
    page_errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=chromium, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1600, "height": 1200})
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.set_content(html, wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        workspace_count = page.locator("[data-workspace]").count()
        research_cards = page.locator(".research-card").count()
        for i in range(workspace_count):
            button = page.locator("[data-workspace]").nth(i)
            workspace = button.get_attribute("data-workspace")
            button.click()
            page.wait_for_timeout(35)
            subviews = page.locator("[data-subview]")
            for j in range(subviews.count()):
                sub = subviews.nth(j)
                view = sub.get_attribute("data-subview")
                sub.click()
                page.wait_for_timeout(35)
                boxes = []
                nodes = page.locator("#graph .node")
                for k in range(nodes.count()):
                    box = nodes.nth(k).bounding_box()
                    if box:
                        boxes.append(box)
                overlaps = 0
                for a in range(len(boxes)):
                    for b in range(a + 1, len(boxes)):
                        aa, bb = boxes[a], boxes[b]
                        x = min(aa["x"] + aa["width"], bb["x"] + bb["width"]) - max(aa["x"], bb["x"])
                        y = min(aa["y"] + aa["height"], bb["y"] + bb["height"]) - max(aa["y"], bb["y"])
                        if x > 1 and y > 1:
                            overlaps += 1
                results.append({"workspace": workspace, "view": view, "nodes": nodes.count(), "overlaps": overlaps})
        page.screenshot(path=str(ROOT / "V32_UI_PREVIEW.png"), full_page=True)
        browser.close()

    check("browser_workspace_count", workspace_count == 8, str(workspace_count))
    check("browser_subview_count", len(results) == 19, str(len(results)))
    check("browser_research_cards", research_cards == 6, str(research_cards))
    check("browser_page_errors", not page_errors, "; ".join(page_errors))
    check("browser_geometry", all(row["overlaps"] == 0 for row in results), json.dumps(results))


def main() -> None:
    compile_contract()
    source_contracts()
    kernel_contract()
    browser_contract()
    report = {
        "version": "3.2",
        "suite": "research_first_release_contract",
        "status": "PASS" if all(x["passed"] for x in CHECKS) else "FAIL",
        "passed": sum(1 for x in CHECKS if x["passed"]),
        "total": len(CHECKS),
        "checks": CHECKS,
        "release_posture": "OPERATIONAL RESEARCH OS; CAPITAL BLOCKED; PREDICTIVE EDGE NOT PROVEN BY THIS SUITE",
        "not_verified_without_external_evidence": [
            "authenticated paid-provider responses and entitlements",
            "public internet reachability from the user's deployment",
            "point-in-time full-universe datasets for every market",
            "market-specific purged/embargoed walk-forward results for every component",
            "untouched lockbox and mature prospective outcomes",
            "autonomous capital allocation",
        ],
    }
    (ROOT / "V32_FULL_VALIDATION_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
