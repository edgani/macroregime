"""User-machine verifier for War Room OS v4.2.

This proves package integrity, software contracts, offline fail-closed collection and an
actual Streamlit health endpoint after dependencies are installed. It does not and cannot
promote any predictive component or authorize capital.
"""
from __future__ import annotations

import compileall
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHECKS: list[dict] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    row = {"name": name, "passed": bool(passed), "detail": str(detail)[-10000:]}
    CHECKS.append(row)
    print(("PASS" if passed else "FAIL"), name, detail)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_runtime() -> None:
    for rel in (
        "runtime/desk_snapshot.json", "runtime/worker_status.json",
        "runtime/force_refresh.flag", "runtime/worker.instance.lock",
        "runtime/worker.pid", "runtime/worker_boot.log",
        "runtime/v42_fixture_desk.json", "runtime/v42_fixture_dashboard.html",
        "static/desk_snapshot.json", "static/worker_status.json",
    ):
        (ROOT / rel).unlink(missing_ok=True)
    for folder in (ROOT / "runtime", ROOT / "static"):
        folder.mkdir(exist_ok=True)
        (folder / ".gitkeep").touch(exist_ok=True)


def verify_manifest() -> None:
    p = ROOT / "PACKAGE_MANIFEST_V42.json"
    if not p.exists():
        check("package_manifest", False, "PACKAGE_MANIFEST_V42.json missing")
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        mismatches = []
        for item in data.get("files", []):
            fp = ROOT / item["path"]
            if not fp.exists():
                mismatches.append(f"missing:{item['path']}")
            elif fp.stat().st_size != item.get("bytes"):
                mismatches.append(f"size:{item['path']}")
            elif sha256(fp) != item["sha256"]:
                mismatches.append(f"hash:{item['path']}")
        check("package_manifest", not mismatches,
              f"files={len(data.get('files', []))}; mismatches={mismatches[:20]}")
    except Exception as exc:
        check("package_manifest", False, f"{type(exc).__name__}: {exc}")


def offline_worker() -> None:
    clean_runtime()
    env = os.environ.copy()
    env.update({
        "WARROOM_NETWORK_MODE": "offline",
        "WARROOM_FAST_CORE_HARD_TIMEOUT": "30",
        "WARROOM_EVENT_HARD_TIMEOUT": "30",
        "WARROOM_SLOW_HARD_TIMEOUT": "30",
        "WARROOM_EXPANDED_CORE_HARD_TIMEOUT": "30",
        "WARROOM_DISABLE_RADAR": "1",
    })
    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "warroom_data_worker.py"), "--once"],
            cwd=ROOT, capture_output=True, text=True, timeout=240, env=env,
        )
        snap_path = ROOT / "runtime" / "desk_snapshot.json"
        status_path = ROOT / "runtime" / "worker_status.json"
        snap = json.loads(snap_path.read_text(encoding="utf-8")) if snap_path.exists() else {}
        status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
        output = (proc.stdout + "\n" + proc.stderr)[-8000:]
        proof = snap.get("proof_status") or {}
        ok = (
            proc.returncode == 0
            and isinstance(snap.get("meta"), dict)
            and isinstance(snap.get("markets"), dict)
            and proof.get("predictive_components_promoted") == 0
            and proof.get("capital_permission") == "BLOCKED"
            and "Traceback" not in output
        )
        check("offline_collector", ok,
              f"rc={proc.returncode}; worker={status.get('state')}; source={snap.get('meta',{}).get('source')}; "
              f"promoted={proof.get('predictive_components_promoted')}; capital={proof.get('capital_permission')}")
    except Exception as exc:
        check("offline_collector", False, f"{type(exc).__name__}: {exc}")
    finally:
        clean_runtime()


def legacy_compatibility_suite() -> None:
    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "gcfis" / "tests" / "test_all.py")],
            cwd=ROOT, capture_output=True, text=True, timeout=300,
        )
        text = (proc.stdout + "\n" + proc.stderr)[-12000:]
        check("legacy_quarantined_compatibility", proc.returncode == 0 and "ALL TESTS PASSED" in text,
              f"rc={proc.returncode}; tail={text[-1600:]}")
    except Exception as exc:
        check("legacy_quarantined_compatibility", False, f"{type(exc).__name__}: {exc}")


def streamlit_health() -> None:
    try:
        import streamlit  # noqa: F401
    except Exception as exc:
        check("streamlit_health", False, f"Streamlit unavailable after dependency installation: {exc}")
        return
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    env = os.environ.copy()
    env.update({
        "WARROOM_DISABLE_AUTOSTART": "1",
        "WARROOM_NETWORK_MODE": "offline",
        "WARROOM_RADAR_INITIAL_DELAY_SECONDS": "9999",
        "WARROOM_DISABLE_RADAR": "1",
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
    })
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless=true",
         f"--server.port={port}", "--server.address=127.0.0.1"],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    ok = False
    body = ""
    try:
        deadline = time.time() + 75
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1.5) as response:
                    body = response.read().decode("utf-8", "replace")
                    ok = response.status == 200 and "ok" in body.lower()
                    if ok:
                        break
            except Exception:
                time.sleep(0.5)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except Exception:
            proc.kill()
            proc.wait(timeout=4)
    check("streamlit_health", ok, f"port={port}; body={body}")


def main() -> None:
    dash = (ROOT / "dashboard.html").read_text(encoding="utf-8", errors="ignore")
    static = (ROOT / "static" / "dashboard_live.html").read_text(encoding="utf-8", errors="ignore")
    registry = json.loads((ROOT / "COMPONENT_PROOF_REGISTRY_DEFAULT.json").read_text(encoding="utf-8"))
    capabilities = json.loads((ROOT / "MARKET_CAPABILITY_MATRIX.json").read_text(encoding="utf-8"))

    check("version", "DECISION-INTELLIGENCE OS · v4.2" in dash)
    check("dashboard_static_sync", dash == static)
    check("capital_fail_closed", "CAPITAL BLOCKED" in dash and "No prospective proof" in dash)
    check("generic_labels_descriptive", "POSITIVE PRICE CONTEXT" in dash and "NEGATIVE PRICE CONTEXT" in dash
          and "WATCH LONG" not in dash and "WATCH SHORT" not in dash)
    check("zero_predictive_promotion",
          all(v.get("capital_permission") == "BLOCKED" for v in registry.get("components", {}).values()))
    check("ihsg_options_disabled",
          (capabilities.get("markets") or capabilities).get("idx", {}).get("options_product") == "NONE")
    check("scenario_targets_fail_closed", "scenario valuation" in dash.lower() and "WITHHELD" in dash)

    verify_manifest()
    check("python_compile", compileall.compile_dir(str(ROOT), quiet=1, force=True))

    try:
        master = json.loads((ROOT / "V42_MASTER_REAUDIT_REPORT.json").read_text(encoding="utf-8"))
        check("shipped_master_audit", master.get("status") == "PASS" and master.get("predictive_components_promoted") == 0,
              f"status={master.get('status')}; promoted={master.get('predictive_components_promoted')}")
    except Exception as exc:
        check("shipped_master_audit", False, f"{type(exc).__name__}: {exc}")

    legacy_compatibility_suite()
    offline_worker()
    streamlit_health()

    report = {
        "version": "4.2",
        "suite": "user_machine_release_verifier",
        "status": "PASS" if all(c["passed"] for c in CHECKS) else "FAIL",
        "passed": sum(c["passed"] for c in CHECKS),
        "total": len(CHECKS),
        "checks": CHECKS,
        "software_permission": "READY_FOR_USER_REVIEW" if all(c["passed"] for c in CHECKS) else "BLOCKED",
        "predictive_components_promoted": 0,
        "capital_permission": "BLOCKED",
        "proof_boundary": "This verifies installation and fail-closed software behavior only. Predictive proof requires exact-scope PIT WFA, realistic costs/capacity, a one-time untouched lockbox, matured prospective outcomes and human approval.",
    }
    (ROOT / "V42_USER_VALIDATION_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
