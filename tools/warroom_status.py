"""War Room operator status CLI (R10.2).

One read-only command answering: "is the system running, is the evidence
chain intact, and what is the capital verdict right now?"

    python tools/warroom_status.py          # human-readable
    python tools/warroom_status.py --json   # machine-readable

Shows: git HEAD, ledger verification + counts, days to first outcome
maturity, contamination verdict, last daily cycle result, scheduled task
presence. Never writes anything; never exits non-zero (status is information,
not a gate — the gates live in the evaluator and contamination verdict).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shadow_execution_ledger_v95 import verify  # noqa: E402
from warroom.research import contamination_gates, trial_counter  # noqa: E402

UTC = dt.timezone.utc
LEDGER = ROOT / "runtime" / "v101_shadow" / "shadow_ledger.jsonl"
CYCLE_LOG = ROOT / "logs" / "daily_cycle.jsonl"


def _git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except Exception:
        return "UNKNOWN"


def _ledger_summary() -> dict[str, Any]:
    verification = verify(LEDGER)
    rows = []
    if LEDGER.exists():
        rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    forecasts = [r for r in rows if r.get("record_type") == "FORECAST"]
    outcomes = [r for r in rows if r.get("record_type") == "OUTCOME"]
    days_to_first_maturity = None
    if forecasts:
        now = dt.datetime.now(UTC)
        ends = sorted(
            dt.datetime.fromisoformat(str(f["outcome_end"]).replace("Z", "+00:00")).astimezone(UTC)
            for f in forecasts
        )
        future = [e for e in ends if e > now]
        if future:
            days_to_first_maturity = (future[0] - now).days
    return {
        "verification_valid": verification["valid"],
        "rows": verification["rows"],
        "errors": len(verification["errors"]),
        "forecasts": len(forecasts),
        "outcomes_matured": len(outcomes),
        "observations_target": 30,
        "days_to_first_maturity": days_to_first_maturity,
    }


def _last_cycle() -> dict[str, Any] | None:
    if not CYCLE_LOG.exists():
        return None
    lines = [l for l in CYCLE_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    return json.loads(lines[-1]) if lines else None


def _scheduled_task() -> str:
    try:
        proc = subprocess.run(
            ["schtasks", "/Query", "/TN", "WarRoomDailyCycle", "/FO", "LIST"],
            capture_output=True, text=True, timeout=15,
        )
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                if "Next Run Time" in line:
                    return "INSTALLED, next: " + line.split(":", 1)[1].strip()
            return "INSTALLED"
        return "NOT_INSTALLED"
    except Exception:
        return "UNKNOWN (schtasks unavailable)"


def build_status() -> dict[str, Any]:
    contamination = contamination_gates.evaluate_contamination(LEDGER)
    registries = trial_counter.verify_all()
    return {
        "schema": "warroom.status.v1",
        "generated_at": dt.datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "git_head": _git_head(),
        "ledger": _ledger_summary(),
        "trial_registries": {"valid": registries["valid"], "entries": registries["total_entries"]},
        "contamination": {
            "shadow_pass": contamination["shadow_pass"],
            "capital_pass": contamination["capital_pass"],
            "blocking_capital_gates": [
                g["id"] for g in contamination["gates"] if g["tier"] == "capital" and not g["passed"]
            ],
        },
        "capital_permission": "BLOCKED",
        "last_daily_cycle": _last_cycle(),
        "scheduled_task": _scheduled_task(),
    }


def _render_text(status: dict[str, Any]) -> str:
    ledger = status["ledger"]
    cycle = status.get("last_daily_cycle") or {}
    lines = [
        f"War Room status — {status['generated_at']}",
        f"  git HEAD:            {status['git_head'][:12]}",
        f"  ledger:              {'VALID' if ledger['verification_valid'] else 'INVALID'} "
        f"({ledger['rows']} rows, {ledger['errors']} errors)",
        f"  forecasts:           {ledger['forecasts']} (matured outcomes: {ledger['outcomes_matured']}, "
        f"target >= {ledger['observations_target']})",
        f"  first maturity in:   {ledger['days_to_first_maturity']} days"
        if ledger["days_to_first_maturity"] is not None
        else "  first maturity in:   n/a",
        f"  trial registries:    {'VALID' if status['trial_registries']['valid'] else 'INVALID'} "
        f"({status['trial_registries']['entries']} entries)",
        f"  contamination:       shadow_pass={status['contamination']['shadow_pass']} "
        f"capital_pass={status['contamination']['capital_pass']}",
        f"  capital_permission:  {status['capital_permission']}",
        f"  scheduled task:      {status['scheduled_task']}",
        f"  last daily cycle:    {cycle.get('started_at', 'never')} ok={cycle.get('ok')}",
    ]
    if status["contamination"]["blocking_capital_gates"]:
        lines.append("  blocking capital:    " + ", ".join(status["contamination"]["blocking_capital_gates"]))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="War Room operator status")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    status = build_status()
    print(json.dumps(status, indent=2, ensure_ascii=False) if args.json else _render_text(status))


if __name__ == "__main__":
    main()
