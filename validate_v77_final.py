"""Final validator for War Room OS V7.7 Human-Readable Final."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "V77_FINAL_VALIDATION.json"
CHECKS: list[dict[str, Any]] = []


def add(name: str, ok: bool, detail: Any = "") -> None:
    CHECKS.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:12000]})
    print(("PASS" if ok else "FAIL"), name, flush=True)


def run(name: str, args: list[str], timeout: int = 300) -> None:
    try:
        proc = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        output = re.sub(r"\b\d+(?:\.\d+)?s\b", "<elapsed>", proc.stdout + "\n" + proc.stderr)
        add(name, proc.returncode == 0, output[-12000:])
    except Exception as exc:
        add(name, False, f"{type(exc).__name__}: {exc}")


def contract_checks() -> None:
    from release_contract_v77 import release_contract, validate_runtime_desk
    from research_kernel import attach_research_kernel

    contract = release_contract()
    add("v77_contract_final_for_inherited_scope", contract.get("status") == "FINAL_HUMAN_READABLE_FOR_INHERITED_EXACT_SCOPE", contract)
    add("proof_boundary_inherited_from_v76", contract.get("proof_boundary_inherited_from") == "WAR_ROOM_OS_V76_FINAL_SAFE_KERNEL", contract.get("proof_boundary_inherited_from"))
    add("zero_new_ticker_directional_components", contract.get("decision_active_ticker_or_directional_components") == 0, contract)
    add("ticker_capital_still_blocked", contract.get("global_ticker_capital_permission") == "BLOCKED", contract)
    ux = contract.get("ux_contract") or {}
    add("ux_plain_language_default", ux.get("default_layout") == "PLAIN_LANGUAGE_BOARD" and ux.get("technical_detail") == "COLLAPSED_BY_DEFAULT", ux)
    add("ux_risk_state_contract", (ux.get("state_semantics") or {}).get("RISK_ON") == "CONSTRUCTIVE" and (ux.get("state_semantics") or {}).get("RISK_OFF") == "DESTRUCTIVE", ux)

    minimal = {
        "meta": {"generated": "2026-07-26T00:00:00Z", "source": "VALIDATION_FIXTURE"},
        "data_health": {"overall": "NO_DATA", "sources": []},
        "systemic": {}, "markets": {}, "alpha": [],
        "desk_picks": {"picks": [], "state": "CAPITAL_BLOCKED"},
        "reference": {}, "macro_observations": {}, "market_breadth": {}, "rotation_snapshot": {},
        "institutional": {"overall_state": "NOT_LOADED", "events": [], "statuses": []},
        "live_intelligence": {"overall_state": "NOT_LOADED", "events": [], "statuses": []},
        "full_live_data": {"overall_state": "NOT_LOADED", "statuses": [], "tab_coverage": {}},
    }
    attached = attach_research_kernel(minimal)
    add("v77_contract_attached_to_runtime", (attached.get("release_contract_v77") or {}).get("release_id") == "WAR_ROOM_OS_V77_HUMAN_READABLE_FINAL", attached.get("release_contract_v77"))
    runtime = validate_runtime_desk(attached)
    add("v77_runtime_fail_closed", runtime.get("status") == "PASS", runtime)


def dashboard_checks() -> None:
    dash = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    static_dash = (ROOT / "static" / "dashboard_live.html").read_text(encoding="utf-8")
    add("dashboard_static_copy_synced", dash == static_dash, {"dashboard_bytes": len(dash), "static_bytes": len(static_dash)})
    add("dashboard_v77_brand", "v7.7 HUMAN-READABLE FINAL" in dash and "release_contract_v77" in dash, "brand and contract binding")
    required = [
        "KESIMPULAN PALING SEDERHANA", "YANG DILAKUKAN SEKARANG", "KELENGKAPAN DATA", "STATUS PENGGUNAAN",
        "CARA BACA KONDISI SEKARANG", "ARTINYA", "YANG DILAKUKAN", "LIHAT DETAIL TEKNIS / MODE LANJUTAN",
        "RINGKAS", "PETA", "BUKTI", "DATA AKTUAL", "SEMUA LAPISAN",
    ]
    add("layperson_labels_present", all(x in dash for x in required), [x for x in required if x not in dash])
    add("capital_context_visually_separated", "Arah pasar dan izin penggunaan dipisahkan" in dash and "Belum boleh menjadi keputusan modal otomatis" in dash, "plain capital boundary")
    add("technical_table_collapsed", '<details class="technical-panel">' in dash and "<summary>LIHAT DETAIL TEKNIS" in dash, "advanced details")
    add("board_uses_full_width", ".page.board-layout .workspace{grid-template-columns:minmax(0,1fr)}" in dash and ".page.board-layout .rail{display:none}" in dash, "board layout")
    add("horizontal_overflow_hardening", "#app{height:100%;width:100%;min-width:0;overflow:hidden" in dash and ".tape-track{display:flex;gap:24px;min-width:0;overflow:hidden;flex:1" in dash, "overflow controls")

    scripts = re.findall(r"<script(?:[^>]*)>(.*?)</script>", dash, flags=re.S)
    js = scripts[-1] if scripts else ""
    tmp = ROOT / "runtime" / "_v77_dashboard_syntax_check.js"
    try:
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(js, encoding="utf-8")
        proc = subprocess.run(["node", "--check", str(tmp)], cwd=ROOT, capture_output=True, text=True, timeout=60)
        add("dashboard_javascript_syntax", proc.returncode == 0, proc.stdout + proc.stderr)
    finally:
        try: tmp.unlink()
        except Exception: pass

    match = re.search(r"const normalizeState = s => \{.*?\n\};", dash, flags=re.S)
    if not match:
        add("risk_on_off_semantic_execution", False, "normalizeState not found")
    else:
        snippet = match.group(0) + "\nconsole.log(JSON.stringify([normalizeState('RISK_ON'),normalizeState('RISK_OFF'),normalizeState('MODERATE_RESEARCH_BAND')]));\n"
        proc = subprocess.run(["node", "-e", snippet], cwd=ROOT, capture_output=True, text=True, timeout=30)
        try:
            values = json.loads(proc.stdout.strip())
        except Exception:
            values = []
        add("risk_on_off_semantic_execution", proc.returncode == 0 and values == ["constructive", "destructive", "watch"], {"values": values, "stderr": proc.stderr})


def docs_checks() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    start = (ROOT / "START_HERE.md").read_text(encoding="utf-8")
    status = (ROOT / "V77_FINAL_STATUS.md").read_text(encoding="utf-8")
    add("v77_documentation_current", all(("V7.7" in x and "Human-Readable Final" in x) for x in (readme, start, status)), "README / START / STATUS")
    add("documentation_no_new_alpha_claim", "does **not** claim new alpha" in status and "Ticker selection, long/short direction" in status, "scope disclosure")
    try:
        ui = json.loads((ROOT / "V77_UI_RENDER_VALIDATION.json").read_text(encoding="utf-8"))
        add("ui_render_regression", ui.get("status") == "PASS" and ui.get("passed") == ui.get("total") == 7, {k: ui.get(k) for k in ("status", "passed", "total")})
    except Exception as exc:
        add("ui_render_regression", False, f"{type(exc).__name__}: {exc}")


def main() -> int:
    run("v76_full_regression", [sys.executable, "validate_v76_final.py"], 360)
    contract_checks()
    dashboard_checks()
    docs_checks()

    passed = sum(x["status"] == "PASS" for x in CHECKS)
    report = {
        "schema": "warroom.validation.v77.human_readable_final",
        "release": "WAR_ROOM_OS_V77_HUMAN_READABLE_FINAL",
        "status": "PASS" if passed == len(CHECKS) else "FAIL",
        "passed": passed,
        "total": len(CHECKS),
        "inherited_decision_active_scoped_risk_controls": 1,
        "new_predictive_components": 0,
        "decision_active_ticker_or_directional_components": 0,
        "ticker_capital_permission": "BLOCKED",
        "checks": CHECKS,
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("release", "status", "passed", "total", "ticker_capital_permission")}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
