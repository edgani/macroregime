from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = ROOT.parent


def run(name: str, command: list[str], cwd: Path, timeout: int = 240) -> dict:
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return {
        "name": name,
        "command": " ".join(command),
        "returncode": proc.returncode,
        "pass": proc.returncode == 0,
        "stdout_tail": proc.stdout[-5000:],
        "stderr_tail": proc.stderr[-5000:],
    }


commands = [
    run(
        "python_compile",
        [sys.executable, "-m", "py_compile", "app.py", "data_layer.py", "run.py",
         "consistency_guard.py", "feed_doctor.py", "alpha_foundry_adapter.py",
         "audit_no_hardcoded_outputs.py", "audit_v6.py", "data/loader.py",
         "data/resilient_market_data.py"],
        ROOT,
    ),
    run(
        "resilient_feed_tests",
        [sys.executable, "-m", "pytest", "-q", "test_resilient_feeds.py", "test_resilient_integration.py"],
        ROOT,
    ),
    run(
        "alpha_foundry_tests",
        [sys.executable, "-m", "pytest", "-q", "tests/test_pipeline.py"],
        ROOT / "alpha_foundry",
    ),
    run("gcfis_full_logic_suite", [sys.executable, "gcfis/tests/test_all.py"], ROOT, timeout=300),
    run("no_hardcoded_current_output_audit", [sys.executable, "audit_no_hardcoded_outputs.py"], ROOT),
    run("deep_runtime_render_audit", [sys.executable, "audit_v6.py"], ROOT),
]

html = (ROOT / "dashboard.html").read_text(encoding="utf-8")
js = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", html, re.S | re.I))
js_path = ROOT / "_release_dashboard_v6.js"
js_path.write_text(js, encoding="utf-8")
commands.append(run("javascript_syntax", ["node", "--check", str(js_path)], ROOT))
js_path.unlink(missing_ok=True)

checks = {
    "commands_pass": all(item["pass"] for item in commands),
    "fourteen_tabs": len(re.findall(r'<div class="tab(?: on| core)?" data-v=', html)) == 14,
    "rich_mission_control": all(term in html for term in (
        "Data Feed Health & Freshness", "Multi-Timeframe Regime", "Regional Regime",
        "Cross-Market Opportunity Monitor", "Early-Warning Snapshot", "Alpha Proof Factory",
    )),
    "alpha_runtime_and_foundry": all(term in html for term in (
        "Current Cross-Market Tactical Discovery Watch", "Frozen US Alpha Foundry",
    )),
    "major_tabs_rich": all(term in html for term in (
        "Growth / Inflation Nowcast", "Current Early-Warning State",
        "Causal Chain Reference Library", "Current US Company Watch",
        "Current Surfaced Nodes", "Runtime Integrity & Research Ledger",
    )),
    "no_mock_current_fallback": all(term not in html for term in (
        "const mock=", "Late Expansion", "Recovery 31%", "MOCK v0.2", "v0.3 · MOCK",
    )),
    "no_static_current_payload": all(term not in html for term in (
        "const ALPHA", "const TABS", "const MARKET=",
    )),
    "research_only_permission": "RESEARCH ONLY · PAPER/LIVE BLOCKED" in html,
    "schema_guard": "V6_RICH_DYNAMIC_2026_07_18" in (ROOT / "app.py").read_text(encoding="utf-8"),
    "v6_feed_cache_namespace": "market_v6" in (ROOT / "data/resilient_market_data.py").read_text(encoding="utf-8"),
    "alpha_membership_reference": (ROOT / "alpha_foundry/data/reference/sp500_ticker_start_end.csv").exists(),
    "alpha_current_universe_reference": (ROOT / "alpha_foundry/data/reference/current_us_universe_2026-07-17.csv").exists(),
    "no_packaged_synthetic_desk": not (ROOT / "desk_data.json").exists(),
    "no_packaged_generated_dashboard": not (ROOT / "dashboard_live.html").exists(),
}

report = {
    "version": "v6",
    "pass": all(checks.values()),
    "checks_passed": sum(checks.values()),
    "checks_total": len(checks),
    "checks": checks,
    "command_results": commands,
    "claim_state": {
        "tactical_alpha_watch": "UNPROVEN_RESEARCH_WATCH",
        "foundry_selector": "HISTORICAL_CANDIDATE_MAX_UNTIL_LOCKBOX_AND_PROSPECTIVE",
        "paper": "BLOCKED",
        "live": "BLOCKED",
    },
}
(ROOT / "RELEASE_VALIDATION_v6.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps({
    "pass": report["pass"],
    "checks": f'{report["checks_passed"]}/{report["checks_total"]}',
    "commands": {item["name"]: item["pass"] for item in commands},
}, indent=2))
raise SystemExit(0 if report["pass"] else 1)
