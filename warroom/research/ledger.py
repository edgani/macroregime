"""warroom/research/ledger.py — immutable hash-chained trial ledger (R7).

Every trial — pass or fail — is appended with a hash chain. No trial is ever
edited or deleted. Failed trials are first-class records.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "warroom.trial_ledger.v1"


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TrialLedger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "GENESIS"
        last = None
        with self.path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last = line
        if last is None:
            return "GENESIS"
        return json.loads(last)["entry_hash"]

    def record(self, trial: dict) -> dict:
        """Append one trial. Returns the stored entry."""
        entry = {
            "schema": SCHEMA,
            "recorded_at": utcnow(),
            "prev_hash": self._last_hash(),
            "trial": trial,
        }
        raw = json.dumps(entry, sort_keys=True, default=str).encode("utf-8")
        entry["entry_hash"] = hashlib.sha256(raw).hexdigest()
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        return entry

    def all(self) -> list:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]

    def verify_chain(self) -> bool:
        entries = self.all()
        prev = "GENESIS"
        for e in entries:
            if e["prev_hash"] != prev:
                return False
            raw_entry = {k: v for k, v in e.items() if k != "entry_hash"}
            raw = json.dumps(raw_entry, sort_keys=True, default=str).encode("utf-8")
            if hashlib.sha256(raw).hexdigest() != e["entry_hash"]:
                return False
            prev = e["entry_hash"]
        return True
