"""War Room daily cycle supervisor (R9.4).

Runs one full prospective-evidence cycle with retry and honest postcondition
checks, designed to be invoked by Windows Task Scheduler (or manually):

    1. warroom_data_worker_v101.py --once --full   (live collectors + snapshot)
       - one automatic retry after a failure (intermittent native crashes were
         observed on Windows: segfault EXIT=139 in ~1 of 3 fast cycles)
    2. Postconditions (fail-closed):
       - runtime/desk_snapshot.json regenerated within the freshness window
       - runtime/worker_status.json state == READY_OPERATIONAL_RESEARCH
    3. shadow_runner_v101.py          (record new shadow candidates; idempotent)
    4. shadow_outcome_recorder_v101.py (mature any forecasts past horizon)
    5. tools/paper_trading/evaluate_shadow_ledger.py -> dated evaluation report
    6. Append one JSONL summary line to logs/daily_cycle.jsonl

Exit code is non-zero if any stage fails, so the scheduler surfaces failure
instead of a silent green. No stage ever fabricates data: collector outages
become honest skips or a failed cycle, never synthetic fills.

Usage:
    python tools/worker_supervisor.py [--max-snapshot-age-seconds 1800] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"
DESK_SNAPSHOT = ROOT / "runtime" / "desk_snapshot.json"
WORKER_STATUS = ROOT / "runtime" / "worker_status.json"
EVAL_DIR = ROOT / "runtime" / "v101_shadow" / "evaluations"
CYCLE_LOG = LOGS / "daily_cycle.jsonl"
UTC = dt.timezone.utc

REQUIRED_STATUS_STATE = "READY_OPERATIONAL_RESEARCH"


def check_cycle_postconditions(
    desk_snapshot: Path,
    worker_status: Path,
    *,
    max_age_seconds: int,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Pure postcondition check, separated for testing.

    Fresh means: the desk snapshot was rewritten inside the freshness window
    AND the worker status file reports a successful operational cycle.
    """
    now = (now or dt.datetime.now(UTC)).astimezone(UTC)
    failures: list[str] = []
    snapshot_age: float | None = None
    status_state: str | None = None

    if not desk_snapshot.exists():
        failures.append("DESK_SNAPSHOT_MISSING")
    else:
        snapshot_age = now.timestamp() - desk_snapshot.stat().st_mtime
        if snapshot_age > max_age_seconds:
            failures.append(f"DESK_SNAPSHOT_STALE: age {int(snapshot_age)}s > {max_age_seconds}s")

    if not worker_status.exists():
        failures.append("WORKER_STATUS_MISSING")
    else:
        try:
            status = json.loads(worker_status.read_text(encoding="utf-8"))
            status_state = status.get("state")
            if status_state != REQUIRED_STATUS_STATE:
                failures.append(f"WORKER_STATE_NOT_READY: {status_state}")
            if status.get("error"):
                failures.append(f"WORKER_REPORTED_ERROR: {status['error']}")
        except Exception as exc:
            failures.append(f"WORKER_STATUS_UNREADABLE: {type(exc).__name__}: {exc}")

    return {
        "ok": not failures,
        "failures": failures,
        "snapshot_age_seconds": None if snapshot_age is None else int(snapshot_age),
        "status_state": status_state,
    }


def _run_stage(name: str, command: list[str], log_path: Path, timeout_seconds: int) -> dict[str, Any]:
    started = dt.datetime.now(UTC)
    try:
        proc = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        log_path.write_text(output, encoding="utf-8", errors="replace")
        return {
            "stage": name,
            "exit_code": proc.returncode,
            "ok": proc.returncode == 0,
            "log": str(log_path),
            "duration_seconds": (dt.datetime.now(UTC) - started).total_seconds(),
        }
    except subprocess.TimeoutExpired:
        return {"stage": name, "exit_code": None, "ok": False, "log": str(log_path), "error": f"TIMEOUT>{timeout_seconds}s"}


def run_cycle(*, max_snapshot_age_seconds: int = 1800, dry_run: bool = False) -> dict[str, Any]:
    LOGS.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    result: dict[str, Any] = {"schema": "warroom.daily_cycle.v1", "started_at": stamp, "stages": []}

    worker_cmd = [sys.executable, "warroom_data_worker_v101.py", "--once", "--full"]
    if dry_run:
        result["stages"].append({"stage": "worker", "ok": True, "dry_run": True})
    else:
        attempt = _run_stage("worker", worker_cmd, LOGS / f"worker_{stamp}.log", timeout_seconds=1800)
        result["stages"].append(attempt)
        if not attempt["ok"]:
            time.sleep(60)
            retry = _run_stage("worker_retry", worker_cmd, LOGS / f"worker_{stamp}_retry.log", timeout_seconds=1800)
            retry["note"] = "automatic single retry after first failure (intermittent native crash mitigation)"
            result["stages"].append(retry)

    worker_ok = any(s["stage"].startswith("worker") and s.get("ok") for s in result["stages"])
    postconditions = check_cycle_postconditions(
        DESK_SNAPSHOT, WORKER_STATUS, max_age_seconds=max_snapshot_age_seconds
    )
    result["postconditions"] = postconditions
    if dry_run:
        worker_ok = True
    if not worker_ok or not postconditions["ok"]:
        result["ok"] = False
        result["failure"] = "WORKER_FAILED_OR_POSTCONDITIONS_UNMET"
        _append_cycle_log(result)
        return result

    if dry_run:
        result["stages"].append({"stage": "shadow_record", "ok": True, "dry_run": True})
        result["stages"].append({"stage": "outcome_record", "ok": True, "dry_run": True})
    else:
        result["stages"].append(
            _run_stage("shadow_record", [sys.executable, "shadow_runner_v101.py"], LOGS / f"shadow_{stamp}.log", 600)
        )
        result["stages"].append(
            _run_stage("outcome_record", [sys.executable, "shadow_outcome_recorder_v101.py"], LOGS / f"outcome_{stamp}.log", 900)
        )

    if not dry_run:
        evaluation = _run_stage(
            "evaluation",
            [sys.executable, "tools/paper_trading/evaluate_shadow_ledger.py", "--out", str(EVAL_DIR / f"{stamp}.json")],
            LOGS / f"evaluation_{stamp}.log",
            300,
        )
        result["stages"].append(evaluation)

    result["ok"] = all(s.get("ok") for s in result["stages"])
    if not result["ok"]:
        result["failure"] = "STAGE_FAILED: " + ",".join(s["stage"] for s in result["stages"] if not s.get("ok"))
    _append_cycle_log(result)
    return result


def _append_cycle_log(result: dict[str, Any]) -> None:
    summary = {
        "started_at": result["started_at"],
        "ok": result.get("ok"),
        "failure": result.get("failure"),
        "postconditions": result.get("postconditions"),
        "stages": [
            {"stage": s["stage"], "ok": s.get("ok"), "exit_code": s.get("exit_code")} for s in result["stages"]
        ],
    }
    LOGS.mkdir(parents=True, exist_ok=True)
    with CYCLE_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="War Room daily cycle supervisor")
    parser.add_argument("--max-snapshot-age-seconds", type=int, default=1800)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = run_cycle(max_snapshot_age_seconds=args.max_snapshot_age_seconds, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("ok") else 2)


if __name__ == "__main__":
    main()
