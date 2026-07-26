"""Launch the actual Streamlit application and require /_stcore/health HTTP 200."""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "V52_STREAMLIT_HEALTH_REPORT.json"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _write(status: str, **detail) -> int:
    payload = {"schema": "warroom.streamlit_health.v52", "status": status, **detail}
    REPORT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if status == "PASS" else 2 if status == "BLOCKED_BY_ENVIRONMENT" else 1


def main() -> int:
    try:
        import streamlit  # noqa: F401
    except Exception as exc:
        return _write("BLOCKED_BY_ENVIRONMENT", reason=f"streamlit import failed: {type(exc).__name__}: {exc}")
    port = _free_port()
    env = os.environ.copy()
    env.update({
        "WARROOM_DISABLE_AUTOSTART": "1",
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        "PYTHONWARNINGS": "error",
    })
    cmd = [
        sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
        "--server.headless=true", f"--server.port={port}",
        "--server.address=127.0.0.1", "--browser.gatherUsageStats=false",
    ]
    proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    url = f"http://127.0.0.1:{port}/_stcore/health"
    body = ""; code = None
    deadline = time.monotonic() + float(os.getenv("WARROOM_STREAMLIT_HEALTH_TIMEOUT", "45"))
    try:
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            try:
                with urlopen(url, timeout=2) as response:
                    code = response.status
                    body = response.read(4096).decode("utf-8", "replace")
                if code == 200:
                    return _write("PASS", url=url, http_status=code, body=body.strip(), command=cmd)
            except Exception:
                time.sleep(0.5)
        output = ""
        if proc.stdout:
            try:
                output = proc.stdout.read()[-12000:]
            except Exception:
                pass
        return _write("FAIL", url=url, http_status=code, body=body, process_returncode=proc.poll(), output=output)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
