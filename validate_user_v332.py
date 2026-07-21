"""Fast user-machine release verifier for War Room OS v3.3.2.

This verifies packaging, source integrity, fail-closed semantics, an offline collector pass,
and an actual Streamlit health endpoint after dependencies are installed. It deliberately does
not claim predictive edge or capital permission.
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
    row = {"name": name, "passed": bool(passed), "detail": str(detail)[-8000:]}
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
        "runtime/worker.instance.lock", "runtime/worker.pid", "runtime/worker_boot.log",
        "static/desk_snapshot.json", "static/worker_status.json",
    ):
        (ROOT / rel).unlink(missing_ok=True)
    (ROOT / "runtime").mkdir(exist_ok=True)
    (ROOT / "static").mkdir(exist_ok=True)
    (ROOT / "runtime" / ".gitkeep").touch(exist_ok=True)
    (ROOT / "static" / ".gitkeep").touch(exist_ok=True)


def verify_manifest() -> None:
    p = ROOT / "PACKAGE_MANIFEST_V332.json"
    if not p.exists():
        check("package_manifest", False, "PACKAGE_MANIFEST_V332.json missing")
        return
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        mismatches = []
        for item in data.get("files", []):
            fp = ROOT / item["path"]
            if not fp.exists():
                mismatches.append(f"missing:{item['path']}")
            elif sha256(fp) != item["sha256"]:
                mismatches.append(f"hash:{item['path']}")
        check("package_manifest", not mismatches, f"files={len(data.get('files', []))}; mismatches={mismatches[:20]}")
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
            cwd=ROOT, capture_output=True, text=True, timeout=180, env=env,
        )
        snap_path = ROOT / "runtime" / "desk_snapshot.json"
        snap = json.loads(snap_path.read_text(encoding="utf-8")) if snap_path.exists() else {}
        detail = (proc.stdout + "\n" + proc.stderr)[-5000:]
        ok = (
            proc.returncode == 0 and isinstance(snap, dict)
            and isinstance(snap.get("meta"), dict) and isinstance(snap.get("markets"), dict)
            and "name 'disc' is not defined" not in detail
        )
        check("offline_collector", ok, f"rc={proc.returncode}; source={snap.get('meta',{}).get('source')}; health={snap.get('data_health',{}).get('overall')}")
    except Exception as exc:
        check("offline_collector", False, f"{type(exc).__name__}: {exc}")
    finally:
        clean_runtime()


def streamlit_health() -> None:
    try:
        import streamlit  # noqa: F401
    except Exception as exc:
        check("streamlit_health", False, f"Streamlit unavailable after dependency install: {exc}")
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
        deadline = time.time() + 60
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1.5) as r:
                    body = r.read().decode("utf-8", "replace")
                    ok = r.status == 200 and "ok" in body.lower()
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
    worker = (ROOT / "warroom_data_worker.py").read_text(encoding="utf-8", errors="ignore")
    runtime = (ROOT / "runtime_store.py").read_text(encoding="utf-8", errors="ignore")

    check("version", "v3.3.2" in dash and "DECISION-INTELLIGENCE OS · v3.3.2" in dash)
    check("dashboard_static_sync", dash == static)
    check("readability_patch", "font-size:14px" in dash and ".decision-value{font:12.25px" in dash)
    check("stale_error_guard", "error=None" in worker and "current.pop(\"error\", None)" in runtime)
    check("error_only_in_error_state", "/ERROR|FATAL/.test(st)?String(status.error||''):''" in dash)
    check("capital_fail_closed", "capital blocked" in dash.lower() and "No prospective proof" in dash)

    src = json.loads((ROOT / "data" / "source_watchlist.json").read_text(encoding="utf-8"))
    dev = json.loads((ROOT / "data" / "current_developments.json").read_text(encoding="utf-8"))
    sources = src.get("sources", src if isinstance(src, list) else [])
    developments = dev.get("entries", dev.get("developments", dev if isinstance(dev, list) else []))
    check("current_source_inventory", len(sources) >= 30, f"sources={len(sources)}")
    check("current_developments_inventory", len(developments) >= 15, f"developments={len(developments)}")

    ok_compile = compileall.compile_dir(str(ROOT), quiet=1, force=True)
    check("python_compile", ok_compile)
    verify_manifest()

    report_path = ROOT / "V332_MASTER_RELEASE_REPORT.json"
    try:
        master = json.loads(report_path.read_text(encoding="utf-8"))
        check("master_release_evidence", master.get("status") == "PASS", f"{master.get('passed')}/{master.get('total')}")
    except Exception as exc:
        check("master_release_evidence", False, f"{type(exc).__name__}: {exc}")

    offline_worker()
    streamlit_health()

    report = {
        "version": "3.3.2",
        "suite": "user_release_verifier",
        "status": "PASS" if all(c["passed"] for c in CHECKS) else "FAIL",
        "passed": sum(c["passed"] for c in CHECKS),
        "total": len(CHECKS),
        "checks": CHECKS,
        "operational_permission": "READY_FOR_USER_REVIEW" if all(c["passed"] for c in CHECKS) else "BLOCKED",
        "capital_permission": "CAPITAL_BLOCKED",
        "proof_boundary": "Operational verification is not predictive proof. PIT WFA, costs/capacity, lockbox and prospective results remain separate gates.",
    }
    (ROOT / "V332_USER_VALIDATION_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
