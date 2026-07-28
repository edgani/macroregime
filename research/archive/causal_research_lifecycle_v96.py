"""War Room OS V9.6 causal research lifecycle.

The lifecycle enforces the user's required order:
    mapping -> candidate metric -> test -> adjudication -> final metric.

A formula cannot be registered before its causal map is frozen. Every event is append-only,
chronology checked and SHA-256 hash chained. Failed and removed candidates remain in the ledger so
multiple-testing corrections can use the full search history rather than only the winner.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from warroom.no_technical_policy import validate_feature_names

SCHEMA = "warroom.v96.research_lifecycle_event.v1"
MARKETS = {"us", "idx", "commodity", "fx", "crypto"}
EVENT_TYPES = {"MAP_FREEZE", "CANDIDATE_REGISTER", "TEST_START", "ADJUDICATE", "FINAL_METRIC"}
VERDICTS = {"PROVEN_USE", "TEST_ALTERNATE", "REMOVE"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAPPING_FIELDS = {
    "decision_purpose",
    "causal_role",
    "source_country_liquidity",
    "stock_flow_surprise_state",
    "transmission_path",
    "benchmark_target_horizon",
    "data_lineage_availability",
    "interaction_conditions",
    "invalidation",
    "claim_limits",
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _parse_time(value: Any) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(dt.timezone.utc)


def read_events(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at line {line_no}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"line {line_no} must contain an object")
        rows.append(row)
    return rows


def _require_hash(payload: dict[str, Any], field: str) -> None:
    if not HEX64.fullmatch(str(payload.get(field) or "")):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")


def _validate_mapping(payload: dict[str, Any]) -> None:
    missing = sorted(MAPPING_FIELDS.difference(payload))
    if missing:
        raise ValueError("mapping missing fields: " + ", ".join(missing))
    for key in MAPPING_FIELDS:
        value = payload.get(key)
        if value is None or (isinstance(value, str) and not value.strip()) or (isinstance(value, (list, dict)) and not value):
            raise ValueError(f"mapping field is empty: {key}")
    if not isinstance(payload.get("transmission_path"), list) or len(payload["transmission_path"]) < 3:
        raise ValueError("transmission_path must contain at least trigger, direct effect and value recipient")
    if not isinstance(payload.get("interaction_conditions"), list):
        raise ValueError("interaction_conditions must be a list")
    if not isinstance(payload.get("invalidation"), list) or not payload["invalidation"]:
        raise ValueError("invalidation must be a non-empty list")
    _require_hash(payload, "data_contract_hash")


def _validate_candidate(payload: dict[str, Any]) -> None:
    required = {
        "candidate_id", "metric_role", "formula_hash", "config_hash", "code_hash",
        "benchmark_id", "target_definition", "horizon", "feature_names", "family_id",
        "parameter_vector", "expected_failure_modes",
    }
    missing = sorted(required.difference(payload))
    if missing:
        raise ValueError("candidate missing fields: " + ", ".join(missing))
    for field in ("formula_hash", "config_hash", "code_hash"):
        _require_hash(payload, field)
    if not str(payload.get("candidate_id") or "").strip():
        raise ValueError("candidate_id is required")
    if not str(payload.get("benchmark_id") or "").strip():
        raise ValueError("benchmark_id is required")
    features = payload.get("feature_names")
    if not isinstance(features, list) or not features:
        raise ValueError("feature_names must be a non-empty list")
    violations = validate_feature_names([str(x) for x in features])
    if violations:
        raise ValueError("technical predictor rejected: " + " | ".join(violations))
    if not isinstance(payload.get("parameter_vector"), dict):
        raise ValueError("parameter_vector must be an object")
    if not isinstance(payload.get("expected_failure_modes"), list) or not payload["expected_failure_modes"]:
        raise ValueError("expected_failure_modes must be a non-empty list")


def _event_body(event: dict[str, Any]) -> dict[str, Any]:
    body = dict(event)
    body.pop("record_hash", None)
    return body


def _validate_event_shape(body: dict[str, Any]) -> None:
    required = {"schema", "event_id", "research_id", "market", "event_type", "registered_at", "payload", "previous_hash"}
    missing = sorted(required.difference(body))
    if missing:
        raise ValueError("event missing fields: " + ", ".join(missing))
    if body.get("schema") != SCHEMA:
        raise ValueError("event schema mismatch")
    if str(body.get("market") or "").lower() not in MARKETS:
        raise ValueError("unsupported market")
    if body.get("event_type") not in EVENT_TYPES:
        raise ValueError("unsupported event_type")
    if not str(body.get("event_id") or "").strip() or not str(body.get("research_id") or "").strip():
        raise ValueError("event_id and research_id are required")
    if not isinstance(body.get("payload"), dict):
        raise ValueError("payload must be an object")
    _parse_time(body["registered_at"])


def replay(path: str | Path) -> dict[str, Any]:
    try:
        rows = read_events(path)
    except Exception as exc:
        return {"valid": False, "events": 0, "errors": [str(exc)]}

    previous = "GENESIS"
    seen_events: set[str] = set()
    seen_candidates: set[str] = set()
    research: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    last_time: dt.datetime | None = None

    for index, row in enumerate(rows):
        body = _event_body(row)
        recorded_hash = str(row.get("record_hash") or "")
        try:
            _validate_event_shape(body)
            event_time = _parse_time(body["registered_at"])
            if last_time is not None and event_time < last_time:
                raise ValueError("event chronology moved backwards")
            last_time = event_time
            if body.get("previous_hash") != previous:
                raise ValueError("previous_hash mismatch")
            if hashlib.sha256(canonical(body)).hexdigest() != recorded_hash:
                raise ValueError("record_hash mismatch")
            event_id = str(body["event_id"])
            if event_id in seen_events:
                raise ValueError("duplicate event_id")
            seen_events.add(event_id)

            rid = str(body["research_id"])
            state = research.setdefault(rid, {
                "market": str(body["market"]).lower(), "mapped": False, "mapping_hash": None,
                "candidates": {}, "final_metric": None,
            })
            if state["market"] != str(body["market"]).lower():
                raise ValueError("research_id cannot span markets")
            event_type = str(body["event_type"])
            payload = dict(body["payload"])

            if event_type == "MAP_FREEZE":
                if state["mapped"]:
                    raise ValueError("mapping already frozen")
                _validate_mapping(payload)
                state["mapped"] = True
                state["mapping_hash"] = sha256_json(payload)
            elif event_type == "CANDIDATE_REGISTER":
                if not state["mapped"]:
                    raise ValueError("candidate formula registered before frozen mapping")
                _validate_candidate(payload)
                candidate_id = str(payload["candidate_id"])
                if candidate_id in seen_candidates:
                    raise ValueError("duplicate candidate_id")
                seen_candidates.add(candidate_id)
                if str(payload.get("mapping_hash") or "") != state["mapping_hash"]:
                    raise ValueError("candidate not bound to frozen mapping")
                state["candidates"][candidate_id] = {"tested": False, "verdict": None, "payload": payload}
            elif event_type == "TEST_START":
                candidate_id = str(payload.get("candidate_id") or "")
                if candidate_id not in state["candidates"]:
                    raise ValueError("test started for unknown candidate")
                _require_hash(payload, "test_protocol_hash")
                _require_hash(payload, "dataset_manifest_hash")
                state["candidates"][candidate_id]["tested"] = True
            elif event_type == "ADJUDICATE":
                candidate_id = str(payload.get("candidate_id") or "")
                candidate = state["candidates"].get(candidate_id)
                if not candidate or not candidate["tested"]:
                    raise ValueError("candidate adjudicated before test")
                verdict = str(payload.get("verdict") or "")
                if verdict not in VERDICTS:
                    raise ValueError("invalid verdict")
                if candidate["verdict"] is not None:
                    raise ValueError("candidate already adjudicated")
                _require_hash(payload, "test_result_hash")
                candidate["verdict"] = verdict
            elif event_type == "FINAL_METRIC":
                candidate_id = str(payload.get("candidate_id") or "")
                candidate = state["candidates"].get(candidate_id)
                if not candidate or candidate.get("verdict") != "PROVEN_USE":
                    raise ValueError("final metric must reference a PROVEN_USE candidate")
                if state["final_metric"] is not None:
                    raise ValueError("final metric already selected")
                state["final_metric"] = candidate_id
        except Exception as exc:
            errors.append(f"row {index}: {exc}")
        previous = recorded_hash

    counts = {
        "research_programs": len(research),
        "mapped_programs": sum(1 for x in research.values() if x["mapped"]),
        "registered_candidates": sum(len(x["candidates"]) for x in research.values()),
        "tested_candidates": sum(sum(1 for c in x["candidates"].values() if c["tested"]) for x in research.values()),
        "proven_candidates": sum(sum(1 for c in x["candidates"].values() if c["verdict"] == "PROVEN_USE") for x in research.values()),
        "removed_candidates": sum(sum(1 for c in x["candidates"].values() if c["verdict"] == "REMOVE") for x in research.values()),
        "alternate_candidates": sum(sum(1 for c in x["candidates"].values() if c["verdict"] == "TEST_ALTERNATE") for x in research.values()),
        "final_metrics": sum(1 for x in research.values() if x["final_metric"] is not None),
    }
    return {
        "schema": "warroom.v96.research_lifecycle_replay.v1",
        "valid": not errors,
        "events": len(rows),
        "last_hash": previous,
        "errors": errors,
        "counts": counts,
        "research": research,
    }


def append_event(path: str | Path, event: dict[str, Any], *, now: dt.datetime | None = None) -> dict[str, Any]:
    p = Path(path)
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    existing = read_events(p)
    if existing:
        verified = replay(p)
        if not verified.get("valid"):
            raise ValueError("existing lifecycle ledger is invalid: " + " | ".join(verified.get("errors") or []))
    body = dict(event)
    body.setdefault("schema", SCHEMA)
    body.setdefault("registered_at", now.isoformat().replace("+00:00", "Z"))
    body["market"] = str(body.get("market") or "").lower()
    body["previous_hash"] = existing[-1]["record_hash"] if existing else "GENESIS"
    _validate_event_shape(body)
    event_time = _parse_time(body["registered_at"])
    if abs((now - event_time).total_seconds()) > 300:
        raise ValueError("backfilled or future lifecycle event rejected")
    if any(str(row.get("event_id")) == str(body.get("event_id")) for row in existing):
        raise ValueError("duplicate event_id")
    body["record_hash"] = hashlib.sha256(canonical(body)).hexdigest()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(body, sort_keys=True, ensure_ascii=False) + "\n")
    verified = replay(p)
    if not verified.get("valid"):
        raise ValueError("new event violates lifecycle: " + " | ".join(verified.get("errors") or []))
    return body
