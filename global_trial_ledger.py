"""Immutable project-wide trial ledger for War Room OS V8.5.

Every mechanism hypothesis, formula/configuration change, interaction, prompt retry,
model retry and abandoned experiment is a separate trial. The ledger is append-only
and hash chained. It is intentionally independent from strategy performance code.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "warroom.v85.global_trial.v1"
ALLOWED_STATES = {"REGISTERED", "RUNNING", "FAILED", "REJECTED", "VALIDATION_CANDIDATE", "FROZEN"}
REQUIRED = {
    "trial_id", "market", "mechanism_id", "hypothesis", "formula_hash", "config_hash",
    "data_contract_hash", "code_hash", "prompt_hash", "model_id", "registered_at",
    "state", "parent_trial_id", "notes",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def read_rows(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows = []
    for number, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at line {number}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"Ledger row {number} must be an object")
        rows.append(row)
    return rows


def _parse_utc(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return parsed.astimezone(dt.timezone.utc)


def validate_trial_body(body: dict[str, Any]) -> None:
    missing = sorted(REQUIRED.difference(body))
    if missing:
        raise ValueError(f"Missing trial fields: {', '.join(missing)}")
    if body.get("schema") != SCHEMA:
        raise ValueError("Trial schema mismatch")
    if not str(body["trial_id"]).strip():
        raise ValueError("trial_id is required")
    if body["state"] not in ALLOWED_STATES:
        raise ValueError(f"Invalid trial state: {body['state']}")
    for key in ("formula_hash", "config_hash", "data_contract_hash", "code_hash", "prompt_hash"):
        if not HEX64.fullmatch(str(body[key])):
            raise ValueError(f"{key} must be a lowercase SHA-256 digest")
    _parse_utc(str(body["registered_at"]))


def verify_ledger(path: str | Path) -> dict[str, Any]:
    try:
        rows = read_rows(path)
    except Exception as exc:
        return {"valid": False, "count": 0, "reason": str(exc)}
    previous = "GENESIS"
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        body = dict(row)
        recorded_hash = body.pop("record_hash", None)
        try:
            validate_trial_body(body)
        except Exception as exc:
            return {"valid": False, "count": len(rows), "row": index, "reason": str(exc)}
        if body.get("previous_hash") != previous:
            return {"valid": False, "count": len(rows), "row": index, "reason": "previous_hash mismatch"}
        calculated = hashlib.sha256(canonical(body)).hexdigest()
        if calculated != recorded_hash:
            return {"valid": False, "count": len(rows), "row": index, "reason": "record_hash mismatch"}
        trial_id = str(body["trial_id"])
        if trial_id in seen_ids:
            return {"valid": False, "count": len(rows), "row": index, "reason": "duplicate trial_id"}
        seen_ids.add(trial_id)
        previous = str(recorded_hash)
    return {"valid": True, "count": len(rows), "last_hash": previous, "unique_trials": len(seen_ids)}


def append_trial(path: str | Path, trial: dict[str, Any], *, now: dt.datetime | None = None) -> dict[str, Any]:
    p = Path(path)
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone aware")
    rows = read_rows(p)
    if rows:
        result = verify_ledger(p)
        if not result.get("valid"):
            raise ValueError(f"Existing trial ledger invalid: {result.get('reason')}")
    if any(str(row.get("trial_id")) == str(trial.get("trial_id")) for row in rows):
        raise ValueError("Duplicate trial_id")
    body = dict(trial)
    body.setdefault("schema", SCHEMA)
    body.setdefault("registered_at", now.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z"))
    body.setdefault("state", "REGISTERED")
    body.setdefault("parent_trial_id", None)
    body.setdefault("notes", "")
    body["previous_hash"] = rows[-1]["record_hash"] if rows else "GENESIS"
    validate_trial_body(body)
    registered = _parse_utc(str(body["registered_at"]))
    if abs((now.astimezone(dt.timezone.utc) - registered).total_seconds()) > 300:
        raise ValueError("Backfilled or future trial registration rejected")
    body["record_hash"] = hashlib.sha256(canonical(body)).hexdigest()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(body, sort_keys=True, ensure_ascii=False) + "\n")
    return body


def count_trials(path: str | Path, *, market: str | None = None, mechanism_id: str | None = None) -> int:
    rows = read_rows(path)
    return sum(
        1 for row in rows
        if (market is None or row.get("market") == market)
        and (mechanism_id is None or row.get("mechanism_id") == mechanism_id)
    )
