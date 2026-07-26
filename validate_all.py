"""Run the legacy validation stack with strict, machine-readable failure semantics.

Unlike the historical wrapper, a child failure, timeout, warning promoted to error, or missing
required dependency cannot be printed as "all complete".  Exit codes: 0=all pass, 1=failed,
2=blocked by environment/dependency.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
SCRIPTS = [
    "validation_plus.py",
    "validate_real.py",
    "component_validation.py",
    "composition_audit.py",
    "filter_validation.py",
    "gem_validation.py",
    "alpha_discovery_test.py",
]
DEPENDENCIES = {
    "validate_real.py": (),
    "component_validation.py": (),
}


def _missing(modules: tuple[str, ...]) -> list[str]:
    missing = []
    for name in modules:
        try:
            __import__(name)
        except Exception:
            missing.append(name)
    return missing


def main() -> int:
    timeout = float(os.getenv("WARROOM_VALIDATION_TIMEOUT", "300"))
    env = os.environ.copy()
    env["PYTHONWARNINGS"] = "error"
    rows = []
    for script in SCRIPTS:
        path = HERE / script
        row = {"script": script, "status": "PENDING", "returncode": None, "seconds": 0.0, "detail": ""}
        print("\n" + "#" * 90 + f"\n# {script}\n" + "#" * 90, flush=True)
        if not path.is_file():
            row.update(status="FAIL", detail="script missing")
            rows.append(row)
            continue
        missing = _missing(DEPENDENCIES.get(script, ()))
        if missing:
            row.update(status="BLOCKED_BY_ENVIRONMENT", detail="missing: " + ", ".join(missing))
            rows.append(row)
            print(row["detail"], flush=True)
            continue
        started = time.monotonic()
        try:
            proc = subprocess.run(
                [sys.executable, str(path)], cwd=HERE, env=env,
                text=True, capture_output=True, timeout=timeout,
            )
            row["seconds"] = round(time.monotonic() - started, 3)
            row["returncode"] = proc.returncode
            row["detail"] = (proc.stdout + "\n" + proc.stderr)[-20000:]
            row["status"] = "PASS" if proc.returncode == 0 else "FAIL"
            print(row["detail"], flush=True)
        except subprocess.TimeoutExpired as exc:
            row["seconds"] = round(time.monotonic() - started, 3)
            row["status"] = "FAIL"
            row["detail"] = f"timeout after {timeout}s: {exc}"
            print(row["detail"], flush=True)
        rows.append(row)

    status = "FAIL" if any(x["status"] == "FAIL" for x in rows) else (
        "BLOCKED_BY_ENVIRONMENT" if any(x["status"] == "BLOCKED_BY_ENVIRONMENT" for x in rows) else "PASS"
    )
    report = {
        "schema": "warroom.validation_stack.v52",
        "status": status,
        "warnings_as_errors": True,
        "timeout_seconds_per_script": timeout,
        "results": rows,
    }
    (HERE / "V52_LEGACY_VALIDATION_STACK_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\n" + "=" * 90)
    print(f"VALIDATION STACK: {status}")
    if status == "PASS":
        print("All child scripts returned zero under warnings-as-errors.")
        return 0
    if status == "BLOCKED_BY_ENVIRONMENT":
        print("No child failed, but one or more required dependencies are unavailable.")
        return 2
    print("At least one child failed or timed out; no completion claim is permitted.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
