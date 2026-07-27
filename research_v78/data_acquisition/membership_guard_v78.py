"""Historical-membership interval guard for V7.8 research panels.

The bundled community-maintained S&P 500 interval file is a research cross-check only.  It
cannot substitute for a licensed security master, delistings, or official membership history.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

EXPECTED_SHA256 = "39c488ebd6ce6838599e54751adbe8c8e4b68d5801dd77d29b6d137dd77388ac"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_membership_file(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    issues: list[str] = []
    if not path.is_file():
        return {"status": "FAIL", "issues": ["file not found"], "capital_permission": "BLOCKED"}
    digest = _sha(path)
    if digest != EXPECTED_SHA256:
        issues.append(f"sha256 mismatch: {digest}")
    intervals: dict[str, list[tuple[date, date | None]]] = defaultdict(list)
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != ["ticker", "start_date", "end_date"]:
            issues.append(f"unexpected header: {reader.fieldnames}")
        for line, row in enumerate(reader, 2):
            try:
                ticker = (row.get("ticker") or "").strip().upper()
                start = date.fromisoformat((row.get("start_date") or "").strip())
                end_text = (row.get("end_date") or "").strip()
                end = date.fromisoformat(end_text) if end_text else None
                if not ticker:
                    raise ValueError("blank ticker")
                if end is not None and end < start:
                    raise ValueError("end before start")
                intervals[ticker].append((start, end))
            except Exception as exc:
                issues.append(f"line {line}: {exc}")
    overlapping = []
    for ticker, rows in intervals.items():
        ordered = sorted(rows)
        for left, right in zip(ordered, ordered[1:]):
            if right[0] <= (left[1] or date.max):
                overlapping.append({"ticker": ticker, "left": [str(left[0]), str(left[1] or "")], "right": [str(right[0]), str(right[1] or "")]})
    # Re-entry after leaving the index is valid; overlap is not.
    if overlapping:
        issues.append(f"{len(overlapping)} overlapping ticker intervals")
    return {
        "schema": "warroom.v78.membership_guard_validation.v1",
        "status": "PASS" if not issues else "FAIL",
        "capital_permission": "BLOCKED_RESEARCH_GUARD_ONLY",
        "sha256": digest,
        "rows": sum(len(v) for v in intervals.values()),
        "unique_tickers": len(intervals),
        "overlaps": overlapping[:25],
        "issues": issues,
        "claim_boundary": "Membership interval cross-check only; not a survivor-bias-free price/security-master proof.",
    }


def is_member(intervals_file: str | Path, ticker: str, as_of: str | date) -> bool:
    target = date.fromisoformat(as_of) if isinstance(as_of, str) else as_of
    ticker = ticker.strip().upper()
    with Path(intervals_file).open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if (row.get("ticker") or "").strip().upper() != ticker:
                continue
            start = date.fromisoformat(row["start_date"])
            end = date.fromisoformat(row["end_date"]) if row.get("end_date") else None
            if start <= target and (end is None or target <= end):
                return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate_membership_file(args.path)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
