"""War Room OS v3.3.1 regression hotfix validator.

Covers the production failure reported by the user:
- worker NameError from an undefined `disc` variable;
- BOARD mode empty on non-market workspaces;
- missing institutional event rendering helpers.

This validates software behavior only. It does not prove predictive edge.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHECKS: list[dict] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    CHECKS.append({"name": name, "passed": bool(passed), "detail": detail})
    print(("PASS" if passed else "FAIL"), name, detail[:500])


def source_contract() -> None:
    run = (ROOT / "run.py").read_text(encoding="utf-8")
    html = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    check("undefined_disc_removed", 'disc["summary"]' not in run and 'alpha_meta.get("note"' in run)
    check("v331_header", "DECISION-INTELLIGENCE OS · v3.3.1" in html)
    check("generic_workspace_board", "function normalizedBoard(model)" in html)
    check("event_helpers_present", "function eventDescription(e)" in html and "function eventState(e)" in html)


def fast_desk_contract() -> None:
    try:
        import data_layer as DL
        from run import build_fast_desk
        data = DL.load_all(
            markets=["us", "idx", "crypto", "commodity", "fx"],
            start="2025-01-01",
            allow_live=False,
            fetch_live_feeds=False,
            allow_synthetic=True,
        )
        desk = build_fast_desk(data, top_per_market=3)
        check("fast_desk_no_nameerror", isinstance(desk, dict) and "meta" in desk, str((desk.get("meta") or {}).get("note")))
    except Exception as exc:
        check("fast_desk_no_nameerror", False, f"{type(exc).__name__}: {exc}")


def browser_contract() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        check("browser_all_views", False, f"playwright unavailable: {exc}")
        return
    chromium = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    if not chromium:
        check("browser_all_views", False, "Chromium unavailable")
        return

    payload = json.dumps(json.loads((ROOT / "tests" / "v32_fixture.json").read_text(encoding="utf-8")), separators=(",", ":")).replace("</", "<\\/")
    html = (ROOT / "dashboard.html").read_text(encoding="utf-8").replace("/*__INJECT_DATA__*/", f"window.DASHBOARD_DATA={payload};")
    mapping = {
        "mc": "mission", "macro": "regime", "ew": "regime", "alpha": "opportunities", "co": "opportunities",
        "us": "markets", "ihsg": "markets", "crypto": "markets", "commod": "markets", "fx": "markets",
        "flow": "positioning", "inst": "positioning", "deriv": "positioning", "sc": "causal", "kg": "causal",
        "execution": "execution", "research": "research", "rc": "research", "datahealth": "research",
    }
    errors: list[str] = []
    counts: dict[str, int] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=chromium, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1800, "height": 1000})
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.set_content(html, wait_until="domcontentloaded")
        page.wait_for_timeout(150)
        for view, workspace in mapping.items():
            page.locator(f'[data-workspace="{workspace}"]').click()
            page.wait_for_timeout(15)
            sub = page.locator(f'[data-subview="{view}"]')
            if sub.count():
                sub.click()
            page.wait_for_timeout(15)
            counts[view] = page.locator("[data-board-row]").count()
        page.locator('[data-workspace="mission"]').click()
        page.wait_for_timeout(30)
        page.screenshot(path=str(ROOT / "V331_HOTFIX_PREVIEW.png"), full_page=True)
        browser.close()
    zero = [name for name, count in counts.items() if count == 0]
    check("browser_page_errors", not errors, "; ".join(errors))
    check("all_19_views_have_board_rows", not zero and len(counts) == 19, f"counts={counts}; zero={zero}")


def javascript_contract() -> None:
    html = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, flags=re.S | re.I)
    node = shutil.which("node")
    if not scripts or not node:
        check("javascript_parse", False, "script or node missing")
        return
    temp = ROOT / "runtime" / "v331_check.js"
    temp.parent.mkdir(exist_ok=True)
    temp.write_text(scripts[-1], encoding="utf-8")
    proc = subprocess.run([node, "--check", str(temp)], capture_output=True, text=True)
    temp.unlink(missing_ok=True)
    check("javascript_parse", proc.returncode == 0, proc.stderr.strip())


def main() -> None:
    source_contract()
    javascript_contract()
    fast_desk_contract()
    browser_contract()
    report = {
        "version": "3.3.1",
        "suite": "empty_board_and_worker_hotfix",
        "status": "PASS" if all(row["passed"] for row in CHECKS) else "FAIL",
        "passed": sum(1 for row in CHECKS if row["passed"]),
        "total": len(CHECKS),
        "checks": CHECKS,
        "capital_permission": "CAPITAL_BLOCKED",
        "proof_boundary": "This suite verifies UI/runtime regression behavior, not predictive alpha.",
    }
    (ROOT / "V331_HOTFIX_VALIDATION_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
