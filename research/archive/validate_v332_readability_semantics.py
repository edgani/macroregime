"""War Room OS v3.3.2 readability and semantic-integrity regression suite.

Verifies user-reported production failures and semantic overclaims. This suite proves software
behavior and display contracts only; it does not prove predictive alpha or capital permission.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHECKS: list[dict] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    row = {"name": name, "passed": bool(passed), "detail": str(detail)[-12000:]}
    CHECKS.append(row)
    print(("PASS" if passed else "FAIL"), name, row["detail"][:800])


def source_contract() -> None:
    html = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    worker = (ROOT / "warroom_data_worker.py").read_text(encoding="utf-8")
    runtime = (ROOT / "runtime_store.py").read_text(encoding="utf-8")
    setup = (ROOT / "price_setups.py").read_text(encoding="utf-8")
    check("v332_header", "DECISION-INTELLIGENCE OS · v3.3.2" in html)
    check("small_text_enlarged", "font:11.5px/1.46 var(--mono)" in html and "font:12.25px var(--mono)" in html)
    check("static_dashboard_synced", (ROOT / "static" / "dashboard_live.html").read_bytes() == (ROOT / "dashboard.html").read_bytes())
    check("recovered_error_cleared", 'current.pop("error", None)' in runtime and "error=None" in worker)
    check("error_only_rendered_in_error_state", "const err=/ERROR|FATAL/.test(st)?String(status.error||''):''" in html)
    check("one_row_price_generator", "only the stronger side is retained" in setup and "conflicted = gap < 0.08" in setup)
    check("low_price_precision", "digits = 2 if a >= 100 else 4 if a >= 1 else 6 if a >= 0.01 else 8" in setup)
    forbidden = ["markup-readiness", "distribution context", "position building", "liquidation context"]
    check("unsafe_setup_semantics_removed", not any(x in setup.lower() for x in forbidden), [x for x in forbidden if x in setup.lower()])
    check("company_candidate_filter", "function isCompanyCandidate" in html and "!t.endsWith('=F')" in html and "!t.endsWith('-USD')" in html)
    check("dxy_excluded_from_fx_pair_table", "function isFxPairName" in html and "!t.startsWith('DXY')" in html)
    check("provider_status_dedup", "function dedupeStatuses" in html)
    check("poor_rr_blocked", "NO TRADE · POOR R/R" in html)
    check("context_not_false_trade_direction", "return'CONSTRUCTIVE'" in html and "return'ADVERSE'" in html)
    check("validation_exact_production", "new Set(['PRODUCTION','LIMITED_PRODUCTION'])" in html and "/VALIDATED|PRODUCTION/" not in html)
    check("alpha_numeric_upside_withheld", "numeric headroom withheld" in html and "ALPHA RESEARCH INVENTORY" in html)


def price_setup_contract() -> None:
    try:
        import numpy as np
        import pandas as pd
        from price_setups import price_signal_setups
        np.random.seed(17)
        idx = pd.date_range("2024-01-01", periods=330, freq="D")
        def frame(start: float, drift: float):
            ret = np.random.normal(drift, 0.014, len(idx))
            close = start * np.exp(np.cumsum(ret))
            return pd.DataFrame({
                "Open": close * (1 + np.random.normal(0, .002, len(close))),
                "High": close * 1.01,
                "Low": close * .99,
                "Close": close,
                "Volume": np.random.randint(10_000, 1_000_000, len(close)),
            }, index=idx)
        rows = price_signal_setups({"UP": frame(10, .002), "LOW": frame(.006, -.001), "MIX": frame(100, 0)}, top=10)
        tickers = [x["tk"] for x in rows]
        check("price_rows_unique", len(tickers) == len(set(tickers)), tickers)
        check("no_ownership_intent_claim", all("institutional intent" in x.get("evidence_semantics", "") for x in rows), rows)
        low = next((x for x in rows if x["tk"] == "LOW"), None)
        precision_ok = low is not None and all(v is None or len(str(v).split(".")[-1]) >= 4 for v in [low.get("e"), low.get("s"), low.get("t")])
        check("crypto_like_precision_preserved", precision_ok, low)
    except Exception as exc:
        check("price_setup_contract", False, f"{type(exc).__name__}: {exc}")


def javascript_contract() -> None:
    html = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", html, flags=re.S | re.I)
    node = shutil.which("node")
    if not scripts or not node:
        check("javascript_parse", False, "node or script unavailable")
        return
    temp = ROOT / "runtime" / "v332_check.js"
    temp.parent.mkdir(exist_ok=True)
    temp.write_text(scripts[-1], encoding="utf-8")
    proc = subprocess.run([node, "--check", str(temp)], capture_output=True, text=True)
    temp.unlink(missing_ok=True)
    check("javascript_parse", proc.returncode == 0, proc.stderr)


def browser_contract() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        check("browser_contract", False, f"playwright unavailable: {exc}")
        return
    chromium = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
    if not chromium:
        check("browser_contract", False, "Chromium unavailable")
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
    duplicate_views: dict[str, list[str]] = {}
    company_names: list[str] = []
    alpha_actions: list[str] = []
    macro_orientations: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=chromium, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1800, "height": 1000})
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.set_content(html, wait_until="domcontentloaded")
        page.wait_for_timeout(200)
        for view, workspace in mapping.items():
            page.locator(f'[data-workspace="{workspace}"]').click()
            page.wait_for_timeout(20)
            sub = page.locator(f'[data-subview="{view}"]')
            if sub.count():
                sub.click()
            page.wait_for_timeout(25)
            names = page.locator("[data-board-row]").evaluate_all("els => els.map(e => e.getAttribute('data-board-row'))")
            counts[view] = len(names)
            if view in {"us", "ihsg", "crypto", "commod", "fx"} and len(names) != len(set(names)):
                duplicate_views[view] = names
            if view == "co": company_names = names
            if view == "alpha": alpha_actions = page.locator(".decision-table tbody tr td:nth-child(2) .action").all_inner_texts()
            if view == "macro": macro_orientations = page.locator(".decision-table tbody tr td:nth-child(3) .action").all_inner_texts()
        page.locator('[data-workspace="mission"]').click()
        page.wait_for_timeout(30)
        page.screenshot(path=str(ROOT / "V332_READABILITY_PREVIEW.png"), full_page=True)
        browser.close()
    check("browser_page_errors", not errors, errors)
    check("all_19_views_have_rows", len(counts) == 19 and all(v > 0 for v in counts.values()), counts)
    check("market_rows_no_duplicate_instruments", not duplicate_views, duplicate_views)
    check("company_intel_is_equity_only", bool(company_names) and all(not x.endswith("=F") and not x.endswith("=X") and not x.endswith("-USD") for x in company_names), company_names)
    check("alpha_board_has_no_unproven_trade_direction", all("WATCH LONG" not in x and "WATCH SHORT" not in x and not x.startswith("BUILD ") for x in alpha_actions), alpha_actions)
    check("macro_context_not_labeled_long_short", all(x not in {"LONG", "SHORT"} for x in macro_orientations), macro_orientations)


def inventory_contract() -> None:
    try:
        dev = json.loads((ROOT / "data" / "current_developments.json").read_text(encoding="utf-8"))
        watch = json.loads((ROOT / "data" / "source_watchlist.json").read_text(encoding="utf-8"))
        titles = {x.get("title") for x in dev.get("entries", [])}
        ids = {x.get("id") for x in watch.get("sources", [])}
        required_titles = {
            "Robinhood Chain public mainnet and onchain distribution",
            "Circle receives final OCC approval for a national trust bank",
            "USDC enters regulated derivatives-margin workflow through Coinbase and Marex",
            "Ethereum protocol-security team reports agent-assisted discovery and triage of real bugs",
        }
        required_ids = {"coinbase_blog", "circle_pressroom", "ethereum_foundation_blog", "solana_news", "arbitrum_blog", "optimism_blog", "chainlink_newsroom", "occ_news_releases"}
        check("dated_current_developments_expanded", required_titles <= titles, sorted(required_titles - titles))
        check("official_source_radar_expanded", required_ids <= ids and len(ids) >= 30, {"count": len(ids), "missing": sorted(required_ids - ids)})
        check("coverage_taxonomy_present", set(watch.get("coverage_taxonomy", {})) >= {"us", "idx", "crypto", "commodity", "fx"}, watch.get("coverage_taxonomy", {}).keys())
    except Exception as exc:
        check("inventory_contract", False, f"{type(exc).__name__}: {exc}")


def main() -> None:
    source_contract()
    javascript_contract()
    price_setup_contract()
    browser_contract()
    inventory_contract()
    report = {
        "version": "3.3.2",
        "suite": "readability_semantic_integrity",
        "status": "PASS" if all(x["passed"] for x in CHECKS) else "FAIL",
        "passed": sum(x["passed"] for x in CHECKS),
        "total": len(CHECKS),
        "checks": CHECKS,
        "operational_permission": "READY_FOR_USER_REVIEW" if all(x["passed"] for x in CHECKS) else "BLOCKED",
        "capital_permission": "CAPITAL_BLOCKED",
        "proof_boundary": [
            "Readability and semantic integrity are not predictive edge.",
            "Current-source coverage cannot guarantee that every future development is captured.",
            "Point-in-time WFA, untouched lockbox, costs/capacity and mature prospective evidence remain separate gates.",
        ],
    }
    (ROOT / "V332_READABILITY_SEMANTICS_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
