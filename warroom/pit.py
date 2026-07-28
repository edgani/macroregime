"""warroom/pit.py — point-in-time data admission (R5).

Every datum entering the system gets an admission record:

  source, market, venue, instrument, retrieval_ts, release_ts, available_at,
  vintage, revision, sha256, schema_version, license_status, state

States: CURRENT, STALE_LAST_KNOWN, HISTORICAL_REFERENCE, PARTIAL, NO_DATA,
ERROR, LICENSE_REQUIRED. Missing numeric values are never coerced to zero.
Synthetic data is test-fixture-only (see warroom/data.py).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

SCHEMA = "warroom.pit_admission.v1"

STATES = {"CURRENT", "STALE_LAST_KNOWN", "HISTORICAL_REFERENCE", "PARTIAL",
          "NO_DATA", "ERROR", "LICENSE_REQUIRED"}

REQUIRED_FIELDS = ["source", "market", "venue", "instrument", "retrieval_ts",
                   "release_ts", "available_at", "vintage", "revision",
                   "sha256", "schema_version", "license_status", "state"]


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_payload(payload) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def admit(source, market, venue, instrument, payload, *,
          release_ts=None, available_at=None, vintage=None, revision=0,
          license_status="PUBLIC", state="CURRENT", retrieval_ts=None):
    """Create a PIT admission record for a payload.

    release_ts: when the source published the datum (None = unknown, kept null).
    available_at: when it became usable by the system (defaults to retrieval time
    for real-time sources; MUST be explicit for lagged releases like macro prints).
    """
    return {
        "source": source,
        "market": market,
        "venue": venue,
        "instrument": instrument,
        "retrieval_ts": retrieval_ts or utcnow(),
        "release_ts": release_ts,
        "available_at": available_at or retrieval_ts or utcnow(),
        "vintage": vintage or (release_ts or "realtime"),
        "revision": int(revision),
        "sha256": hash_payload(payload),
        "schema_version": SCHEMA,
        "license_status": license_status,
        "state": state,
    }


def validate(record: dict) -> list:
    """Schema validation. Returns list of error strings (empty = pass)."""
    errors = []
    for f in REQUIRED_FIELDS:
        if f not in record:
            errors.append(f"missing field: {f}")
    if record.get("state") not in STATES:
        errors.append(f"bad state: {record.get('state')}")
    if record.get("schema_version") != SCHEMA:
        errors.append(f"bad schema_version: {record.get('schema_version')}")
    # release_ts may be null (unknown) but must never be AFTER available_at
    rt, av = record.get("release_ts"), record.get("available_at")
    if rt and av and str(rt) > str(av):
        errors.append(f"release_ts {rt} after available_at {av} (impossible)")
    return errors


def is_pit_eligible(record: dict, decision_ts: str) -> bool:
    """True if the record was available at the decision timestamp (no look-ahead)."""
    av = record.get("available_at")
    if not av:
        return False
    return str(av) <= str(decision_ts)
