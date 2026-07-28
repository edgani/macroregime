"""Reproducible build-environment master audit for War Room OS v4.2.

Mandatory checks cover source semantics, browser rendering, legacy compatibility, Python
compilation and an offline worker cycle. Streamlit health is recorded separately because the
build environment may not contain the runtime dependency; the user-machine verifier performs
that check after installation.
"""
from __future__ import annotations

import compileall
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHECKS: list[dict] = []


def run(name: str, cmd: list[str], timeout: int = 360, required_text: str | None = None) -> None:
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        text = p.stdout + "\n" + p.stderr
        ok = p.returncode == 0 and (required_text is None or required_text in text)
        CHECKS.append({"name": name, "passed": ok, "returncode": p.returncode, "detail": text[-12000:]})
        print(("PASS" if ok else "FAIL"), name)
    except Exception as exc:
        CHECKS.append({"name": name, "passed": False, "detail": f"{type(exc).__name__}: {exc}"})
        print("FAIL", name, exc)


def check(name: str, value: bool, detail="") -> None:
    CHECKS.append({"name": name, "passed": bool(value), "detail": str(detail)[-12000:]})
    print(("PASS" if value else "FAIL"), name, detail)


def clean_runtime() -> None:
    for rel in (
        "runtime/desk_snapshot.json", "runtime/worker_status.json", "runtime/force_refresh.flag",
        "runtime/worker.instance.lock", "runtime/worker.pid", "runtime/worker_boot.log",
        "runtime/v42_fixture_desk.json", "runtime/v42_fixture_dashboard.html",
        "static/desk_snapshot.json", "static/worker_status.json",
    ):
        (ROOT / rel).unlink(missing_ok=True)
    for folder in (ROOT / "runtime", ROOT / "static"):
        folder.mkdir(exist_ok=True)
        (folder / ".gitkeep").touch(exist_ok=True)


def offline_worker() -> None:
    clean_runtime()
    env = os.environ.copy()
    env.update({
        "WARROOM_NETWORK_MODE": "offline", "WARROOM_DISABLE_RADAR": "1",
        "WARROOM_FAST_CORE_HARD_TIMEOUT": "30", "WARROOM_EVENT_HARD_TIMEOUT": "30",
        "WARROOM_SLOW_HARD_TIMEOUT": "30", "WARROOM_EXPANDED_CORE_HARD_TIMEOUT": "30",
    })
    try:
        p = subprocess.run([sys.executable, "warroom_data_worker.py", "--once"], cwd=ROOT,
                           capture_output=True, text=True, timeout=240, env=env)
        snap_path = ROOT / "runtime" / "desk_snapshot.json"
        status_path = ROOT / "runtime" / "worker_status.json"
        snap = json.loads(snap_path.read_text()) if snap_path.exists() else {}
        status = json.loads(status_path.read_text()) if status_path.exists() else {}
        proof = snap.get("proof_status") or {}
        ok = (p.returncode == 0 and isinstance(snap.get("markets"), dict)
              and proof.get("predictive_components_promoted") == 0
              and proof.get("capital_permission") == "BLOCKED"
              and "Traceback" not in (p.stdout + p.stderr))
        check("offline_worker_cycle", ok,
              {"rc": p.returncode, "state": status.get("state"), "source": (snap.get("meta") or {}).get("source"), "proof": proof})
    except Exception as exc:
        check("offline_worker_cycle", False, f"{type(exc).__name__}: {exc}")
    finally:
        clean_runtime()


def secret_scan() -> None:
    # Detect common concrete secrets, while ignoring documented placeholders.
    patterns = [
        re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[=:]\s*['\"](?!YOUR_|CHANGEME|<|\$\{|example)[A-Za-z0-9_\-]{16,}['\"]"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ]
    hits = []
    allowed_suffix = {".py", ".json", ".md", ".txt", ".toml", ".bat", ".example", ".html"}
    for p in ROOT.rglob("*"):
        if not p.is_file() or any(part in {".venv", ".cache", "__pycache__"} for part in p.parts):
            continue
        if p.suffix.lower() not in allowed_suffix and p.name != ".env.example":
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat in patterns:
            if pat.search(text):
                hits.append(str(p.relative_to(ROOT)))
                break
    check("concrete_secret_scan", not hits, hits[:50])


def main() -> None:
    started = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    check("python_compile", compileall.compile_dir(str(ROOT), quiet=1, force=True))
    check("dashboard_static_sync", (ROOT / "dashboard.html").read_bytes() == (ROOT / "static/dashboard_live.html").read_bytes())
    run("deep_reaudit_contracts", [sys.executable, "validate_v42_deep_reaudit.py"], timeout=360)
    run("legacy_quarantined_compatibility", [sys.executable, "gcfis/tests/test_all.py"], timeout=360, required_text="ALL TESTS PASSED")
    offline_worker()
    secret_scan()

    try:
        import streamlit  # noqa: F401
        streamlit_state = "AVAILABLE_NOT_STARTED_BY_MASTER"
    except Exception as exc:
        streamlit_state = f"NOT_RUN_BUILD_ENV_DEPENDENCY: {type(exc).__name__}: {exc}"

    mandatory_pass = all(x.get("passed") for x in CHECKS)
    deep = {}
    try:
        deep = json.loads((ROOT / "V42_DEEP_REAUDIT_VALIDATION_REPORT.json").read_text())
    except Exception:
        pass
    report = {
        "version": "4.2",
        "suite": "master_deep_reaudit",
        "started_utc": started,
        "completed_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "status": "PASS" if mandatory_pass else "FAIL",
        "passed": sum(bool(x.get("passed")) for x in CHECKS),
        "total": len(CHECKS),
        "checks": CHECKS,
        "deep_contract_suite": {"status": deep.get("status"), "passed": deep.get("passed"), "total": deep.get("total")},
        "streamlit_health": streamlit_state,
        "software_permission": "READY_FOR_USER_REVIEW" if mandatory_pass else "BLOCKED",
        "predictive_components_promoted": 0,
        "capital_permission": "BLOCKED",
        "finality_boundary": {
            "software_and_governance": "PASS" if mandatory_pass else "FAIL",
            "predictive_edge": "NOT_PROVEN",
            "full_point_in_time_wfa": "NOT_RUN_WITH_EXTERNAL_DATA",
            "untouched_lockbox": "NOT_ARMED",
            "prospective_evidence": "NOT_MATURED",
            "paid_or_entitled_live_feeds": "DEPEND_ON_USER_KEYS",
        },
        "proof_boundary": "No software audit can manufacture predictive proof. The package is final as a fail-closed research system; every predictive selector remains blocked until exact-scope external evidence passes the declared ladder.",
    }
    (ROOT / "V42_MASTER_REAUDIT_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not mandatory_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
