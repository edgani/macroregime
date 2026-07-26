"""Signed, append-only prospective evidence ledger for V71 options research.

This module records observations and outcomes; it never emits a trade. Each JSONL row is bound to
one frozen protocol, the previous row digest, exact source payload hashes and an Ed25519 signature.
Private keys are never stored by this package.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from datetime import datetime, timezone
import base64, hashlib, json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

ROOT = Path(__file__).resolve().parent
PROTOCOL = ROOT / "research_v55" / "V71_OPTIONS_PROSPECTIVE_PROTOCOL_FROZEN.json"
SCHEMA = "warroom.options_prospective_observation.v71"
ALLOWED_PHASES = {"PREDICTION", "OUTCOME"}
ALLOWED_MARKETS = {"us", "commodity", "fx", "crypto"}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def parse_time(value: Any) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def payload(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in {"signature", "row_sha256"}}


def digest_row(row: dict) -> str:
    return sha256_bytes(canonical(payload(row)))


def _valid_hash(value: Any) -> bool:
    s = str(value or "").lower()
    return len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def _scope_key(row: dict) -> tuple:
    return (
        row.get("claim_id"), row.get("market"), row.get("underlying"), row.get("venue"),
        row.get("option_contract"), row.get("prediction_id"),
    )


def build_signed_row(*, private_key: Ed25519PrivateKey, key_id: str, phase: str, claim_id: str,
                     observed_at: str, market: str, underlying: str, venue: str,
                     option_contract: str, prediction_id: str, source_payload_sha256: str,
                     source_schema: str, features_or_outcome: dict, previous_row_sha256: str | None,
                     protocol_path: Path = PROTOCOL) -> dict:
    phase = str(phase).upper()
    if phase not in ALLOWED_PHASES:
        raise ValueError("invalid phase")
    if market not in ALLOWED_MARKETS:
        raise ValueError("market disabled or unknown")
    if not all(str(x or "").strip() for x in (key_id, claim_id, underlying, venue, option_contract, prediction_id, source_schema)):
        raise ValueError("exact scope fields are required")
    if parse_time(observed_at) is None:
        raise ValueError("invalid observed_at")
    if not _valid_hash(source_payload_sha256):
        raise ValueError("invalid source payload hash")
    if previous_row_sha256 is not None and not _valid_hash(previous_row_sha256):
        raise ValueError("invalid previous row hash")
    protocol_sha = file_sha256(protocol_path)
    row = {
        "schema": SCHEMA,
        "protocol_sha256": protocol_sha,
        "phase": phase,
        "claim_id": claim_id,
        "observed_at": observed_at,
        "market": market,
        "underlying": underlying,
        "venue": venue,
        "option_contract": option_contract,
        "prediction_id": prediction_id,
        "source_payload_sha256": source_payload_sha256.lower(),
        "source_schema": source_schema,
        "previous_row_sha256": previous_row_sha256,
        "evidence": features_or_outcome,
        "key_id": key_id,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }
    signature = private_key.sign(canonical(row))
    row["signature"] = base64.b64encode(signature).decode("ascii")
    row["row_sha256"] = digest_row(row)
    return row


def append_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_rows(path)
    expected_previous = existing[-1].get("row_sha256") if existing else None
    if row.get("previous_row_sha256") != expected_previous:
        raise ValueError("hash-chain previous row mismatch")
    # An outcome cannot precede its exact prediction or alter scope.
    if row.get("phase") == "OUTCOME":
        predictions = [x for x in existing if x.get("phase") == "PREDICTION" and x.get("prediction_id") == row.get("prediction_id")]
        if len(predictions) != 1 or _scope_key(predictions[0]) != _scope_key(row):
            raise ValueError("outcome has no unique exact-scope prediction")
        if parse_time(row.get("observed_at")) <= parse_time(predictions[0].get("observed_at")):
            raise ValueError("outcome timestamp must follow prediction")
    line = canonical(row).decode("utf-8") + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(line)
        f.flush()


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError("ledger row is not an object")
            out.append(obj)
    return out


def verify_rows(rows: Iterable[dict], public_keys: dict[str, Ed25519PublicKey], *, protocol_path: Path = PROTOCOL) -> dict:
    rows = list(rows)
    errors: list[str] = []
    previous = None
    predictions: dict[str, dict] = {}
    outcomes: set[str] = set()
    protocol_sha = file_sha256(protocol_path)
    for i, row in enumerate(rows):
        prefix = f"row {i}"
        if row.get("schema") != SCHEMA: errors.append(f"{prefix}: schema")
        if row.get("protocol_sha256") != protocol_sha: errors.append(f"{prefix}: protocol hash")
        if row.get("previous_row_sha256") != previous: errors.append(f"{prefix}: chain")
        if digest_row(row) != row.get("row_sha256"): errors.append(f"{prefix}: digest")
        if row.get("market") not in ALLOWED_MARKETS: errors.append(f"{prefix}: market")
        if row.get("phase") not in ALLOWED_PHASES: errors.append(f"{prefix}: phase")
        if parse_time(row.get("observed_at")) is None: errors.append(f"{prefix}: time")
        if not _valid_hash(row.get("source_payload_sha256")): errors.append(f"{prefix}: source hash")
        if row.get("live_decision_weight") != 0.0 or row.get("capital_permission") != "BLOCKED": errors.append(f"{prefix}: permission")
        key = public_keys.get(str(row.get("key_id")))
        if key is None:
            errors.append(f"{prefix}: unknown key")
        else:
            try:
                key.verify(base64.b64decode(row.get("signature") or ""), canonical(payload(row)))
            except (InvalidSignature, ValueError, TypeError):
                errors.append(f"{prefix}: signature")
        pid = str(row.get("prediction_id") or "")
        if row.get("phase") == "PREDICTION":
            if pid in predictions: errors.append(f"{prefix}: duplicate prediction")
            predictions[pid] = row
        elif row.get("phase") == "OUTCOME":
            pred = predictions.get(pid)
            if pred is None or _scope_key(pred) != _scope_key(row): errors.append(f"{prefix}: unmatched outcome")
            elif parse_time(row.get("observed_at")) <= parse_time(pred.get("observed_at")): errors.append(f"{prefix}: non-forward outcome")
            if pid in outcomes: errors.append(f"{prefix}: duplicate outcome")
            outcomes.add(pid)
        previous = row.get("row_sha256")
    return {
        "schema": "warroom.options_prospective_ledger_validation.v71",
        "status": "PASS" if not errors else "FAIL",
        "rows": len(rows),
        "predictions": len(predictions),
        "outcomes": len(outcomes),
        "errors": errors,
        "predictive_components_promoted": 0,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }
