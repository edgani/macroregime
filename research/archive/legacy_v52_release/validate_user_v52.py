"""Strict user-machine verifier for War Room OS v5.2 real-source hardening.

This verifies installation, package integrity, fail-closed software contracts, deterministic
synthetic behavior, the offline collector, statistical validator controls, and an actual Streamlit
health endpoint. It never promotes predictive claims or authorizes capital.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "V52_USER_VALIDATION_REPORT.json"
CHECKS: list[dict] = []


def add(name: str, status: str, detail: str = "") -> None:
    status = status.upper()
    CHECKS.append({"name": name, "status": status, "detail": str(detail)[-12000:]})
    print(status, name, detail)


def run(name: str, command: list[str], timeout: int, blocked_rc: set[int] | None = None,
        extra_env: dict[str, str] | None = None) -> None:
    env = os.environ.copy()
    env.update({"PYTHONWARNINGS": "error", "PYTHONDONTWRITEBYTECODE": "1", "TERM": "xterm", "WARROOM_DISABLE_AUTOSTART": "1"})
    env.update(extra_env or {})
    try:
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=env)
        output = (proc.stdout + "\n" + proc.stderr)[-12000:]
        status = "BLOCKED_BY_ENVIRONMENT" if proc.returncode in (blocked_rc or set()) else "PASS" if proc.returncode == 0 else "FAIL"
        add(name, status, f"rc={proc.returncode}; tail={output[-2500:]}")
    except subprocess.TimeoutExpired as exc:
        add(name, "FAIL", f"timeout after {timeout}s: {exc}")
    except Exception as exc:
        add(name, "FAIL", f"{type(exc).__name__}: {exc}")


def clean_runtime() -> None:
    for rel in (
        "runtime/desk_snapshot.json", "runtime/worker_status.json", "runtime/force_refresh.flag",
        "runtime/worker.instance.lock", "runtime/worker.pid", "runtime/worker_boot.log",
        "runtime/v42_fixture_desk.json", "runtime/v42_fixture_dashboard.html",
        "runtime/v52_desk.json", "runtime/v52_dashboard.html",
        "static/desk_snapshot.json", "static/worker_status.json",
    ):
        (ROOT / rel).unlink(missing_ok=True)
    for folder in (ROOT / "runtime", ROOT / "static"):
        folder.mkdir(exist_ok=True)
        (folder / ".gitkeep").touch(exist_ok=True)


def dependency_check() -> None:
    modules = ["streamlit", "requests", "yfinance", "pandas", "numpy", "scipy", "sklearn", "statsmodels", "hmmlearn", "networkx", "pyarrow", "dotenv", "cryptography"]
    missing = [m for m in modules if importlib.util.find_spec(m) is None]
    add("runtime_dependencies", "PASS" if not missing else "BLOCKED_BY_ENVIRONMENT", f"missing={missing}")


def offline_collector() -> None:
    clean_runtime()
    run("offline_collector_process", [sys.executable, "warroom_data_worker.py", "--once"], 300, extra_env={
        "WARROOM_NETWORK_MODE": "offline", "WARROOM_INPROCESS_COLLECTORS": "1",
        "WARROOM_FAST_CORE_HARD_TIMEOUT": "45", "WARROOM_EVENT_HARD_TIMEOUT": "45",
        "WARROOM_SLOW_HARD_TIMEOUT": "45", "WARROOM_EXPANDED_CORE_HARD_TIMEOUT": "45",
        "WARROOM_DISABLE_RADAR": "1",
    })
    try:
        from runtime_store import read_snapshot
        snapshot = read_snapshot() or {}
        proof = snapshot.get("proof_status") or {}
        ok = bool(snapshot.get("meta")) and isinstance(snapshot.get("markets"), dict) and proof.get("predictive_components_promoted") == 0 and proof.get("capital_permission") == "BLOCKED"
        add("offline_snapshot_contract", "PASS" if ok else "FAIL", f"source={(snapshot.get('meta') or {}).get('source')}; proof={proof}")
    except Exception as exc:
        add("offline_snapshot_contract", "FAIL", f"{type(exc).__name__}: {exc}")
    finally:
        clean_runtime()


def static_contracts() -> None:
    try:
        from proof_registry import default_registry, component_status
        reg = default_registry(); states = {k: component_status(k) for k in reg.get("components", {})}
        promoted = [k for k, v in states.items() if v.get("predictive_promoted")]
        capital = [k for k, v in states.items() if v.get("capital_permission") != "BLOCKED"]
        add("default_proof_state", "PASS" if not promoted and not capital else "FAIL", f"promoted={promoted}; capital={capital}")
    except Exception as exc:
        add("default_proof_state", "FAIL", f"{type(exc).__name__}: {exc}")
    try:
        dash = (ROOT / "dashboard.html").read_text(encoding="utf-8", errors="strict")
        static = (ROOT / "static" / "dashboard_live.html").read_text(encoding="utf-8", errors="strict")
        add("dashboard_static_sync", "PASS" if dash == static else "FAIL")
        descriptive = all(x in dash for x in ("POSITIVE PRICE CONTEXT", "NEGATIVE PRICE CONTEXT", "CAPITAL BLOCKED")) and "WATCH LONG" not in dash and "WATCH SHORT" not in dash
        add("dashboard_fail_closed_semantics", "PASS" if descriptive else "FAIL")
    except Exception as exc:
        add("dashboard_static_contract", "FAIL", f"{type(exc).__name__}: {exc}")


def main() -> int:
    clean_runtime()
    dependency_check()
    run("package_manifest", [sys.executable, "verify_manifest_v52.py"], 120)
    static_contracts()
    run("python_compile", [sys.executable, "-m", "compileall", "-q", "."], 180)
    run("hardening_adversarial_39", [sys.executable, "hardening_tests/test_hardening_v52.py"], 240)
    run("gcfis_warnings_as_errors", [sys.executable, "gcfis/tests/test_all.py"], 300)
    run("bundled_data_integrity", [sys.executable, "validate_bundled_data_v52.py"], 180)
    run("validator_controls", [sys.executable, "validation_plus.py"], 900)
    offline_collector()
    run("streamlit_health", [sys.executable, "validate_streamlit_health_v52.py"], 180, blocked_rc={2})
    if importlib.util.find_spec("pyarrow") is None:
        add("legacy_parquet_semantic_batteries", "BLOCKED_BY_ENVIRONMENT", "pyarrow missing")
    else:
        run("legacy_parquet_semantic_batteries", [sys.executable, "validate_all.py"], 1800, blocked_rc={2})

    failures = [x["name"] for x in CHECKS if x["status"] == "FAIL"]
    blockers = [x["name"] for x in CHECKS if x["status"] == "BLOCKED_BY_ENVIRONMENT"]
    report = {
        "schema": "warroom.user_validation.v52", "hardening_status": "PASS" if not failures else "FAIL",
        "runtime_status": "PASS" if not failures and not blockers else "BLOCKED" if not failures else "FAIL",
        "failures": failures, "environment_blockers": blockers, "checks": CHECKS,
        "predictive_components_promoted": 0, "capital_permission": "BLOCKED",
        "software_permission": "READY_FOR_RESEARCH_REVIEW" if not failures and not blockers else "BLOCKED",
        "claim_boundary": "Installation/software validation is not predictive proof. Capital remains blocked without signed exact-scope matured evidence and human approval.",
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("hardening_status", "runtime_status", "failures", "environment_blockers", "capital_permission")}, indent=2))
    return 0 if not failures and not blockers else 2 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
