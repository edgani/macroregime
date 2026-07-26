"""Cryptographically verified proof receipts.

Editable registry booleans are never evidence.  Promotion requires an Ed25519 signature from a
locally trusted key, exact component/scope binding, artifact hashes, expiry/revocation checks, and
all frozen proof gates.  The shipped trust store is empty, therefore every predictive component is
blocked until the owner explicitly installs a trusted public key and signed receipt.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import base64
import hashlib
import json
import os

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

HERE = Path(__file__).resolve().parent
TRUST_STORE = HERE / "proof" / "trusted_public_keys.json"
REVOCATIONS = HERE / "proof" / "revoked_receipts.json"
RECEIPTS_DIR = HERE / "proof" / "receipts"
SCHEMA = "warroom.proof_receipt.v2"
TRUST_SCHEMA = "warroom.trusted_keys.v1"
REVOCATION_SCHEMA = "warroom.revocations.v1"
REQUIRED_GATES = ("wfa_pass", "lockbox_pass", "prospective_pass", "cost_model_pass", "multiple_testing_pass")
ARTIFACT_HASH_ROLES = {
    "formula_sha256": "formula",
    "code_manifest_sha256": "code_manifest",
    "dataset_manifest_sha256": "dataset_manifest",
    "frozen_spec_sha256": "frozen_spec",
    "trial_ledger_sha256": "trial_ledger",
    "prospective_evidence_sha256": "prospective_evidence",
}



def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _json_file(path: Path) -> dict | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None
    except Exception:
        return None


def load_trust_store(path: Path = TRUST_STORE) -> dict[str, dict]:
    raw = _json_file(path) or {}
    keys = raw.get("keys") if raw.get("schema") == TRUST_SCHEMA else None
    return {str(k): dict(v) for k, v in (keys or {}).items() if isinstance(v, dict)}


def load_revocations(path: Path = REVOCATIONS) -> set[str]:
    raw = _json_file(path) or {}
    if raw.get("schema") != REVOCATION_SCHEMA:
        return set()
    return {str(x) for x in (raw.get("revoked_receipt_ids") or [])}


def file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return None

def receipt_payload(receipt: dict) -> dict:
    return {k: v for k, v in receipt.items() if k != "signature"}


def receipt_digest(receipt: dict) -> str:
    return hashlib.sha256(_canonical(receipt_payload(receipt))).hexdigest()


def _safe_artifact_path(rel: str) -> Path | None:
    try:
        p = (HERE / rel).resolve()
        p.relative_to(HERE.resolve())
        return p
    except Exception:
        return None


def _verify_artifacts(receipt: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    artifacts = receipt.get("artifacts") or []
    if not isinstance(artifacts, list) or not artifacts:
        return False, ["artifact bindings missing"]
    by_role: dict[str, dict] = {}
    for row in artifacts:
        if not isinstance(row, dict):
            reasons.append("invalid artifact binding")
            continue
        role = str(row.get("role") or "")
        if not role or role in by_role:
            reasons.append(f"artifact role missing or duplicate: {role or 'NONE'}")
            continue
        by_role[role] = row
        path = _safe_artifact_path(str(row.get("path") or ""))
        expected = str(row.get("sha256") or "").lower()
        if path is None or not path.is_file() or len(expected) != 64:
            reasons.append(f"artifact unavailable: {row.get('path')}")
            continue
        h = hashlib.sha256(path.read_bytes()).hexdigest()
        if h != expected:
            reasons.append(f"artifact hash mismatch: {row.get('path')}")
    proof = receipt.get("proof") or {}
    for proof_key, role in ARTIFACT_HASH_ROLES.items():
        row = by_role.get(role)
        if not row:
            reasons.append(f"required artifact role missing: {role}")
            continue
        if str(row.get("sha256") or "").lower() != str(proof.get(proof_key) or "").lower():
            reasons.append(f"proof hash not bound to artifact role: {role}")
    return not reasons, reasons

def verify_receipt(receipt: dict | str | Path | None, *, component: str | None = None, scope: str | None = None,
                   claim_type: str | None = None, now: datetime | None = None,
                   trust_store_path: Path = TRUST_STORE, revocations_path: Path = REVOCATIONS,
                   trust_store_sha256: str | None = None, verify_artifacts: bool = True) -> dict:
    result = {"valid": False, "reasons": [], "receipt_id": None, "key_id": None, "digest": None}
    if receipt is None:
        result["reasons"].append("signed receipt missing")
        return result
    try:
        if isinstance(receipt, (str, Path)):
            p = Path(receipt)
            if not p.is_absolute():
                p = (HERE / p).resolve()
                p.relative_to(HERE.resolve())
            receipt = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise TypeError("receipt must be an object")
    except Exception as exc:
        result["reasons"].append(f"receipt unreadable: {type(exc).__name__}")
        return result

    result.update({"receipt_id": receipt.get("receipt_id"), "key_id": receipt.get("key_id"), "digest": receipt_digest(receipt)})
    if receipt.get("schema") != SCHEMA:
        result["reasons"].append("receipt schema mismatch")
    if not receipt.get("receipt_id"):
        result["reasons"].append("receipt id missing")
    revocation_raw = _json_file(revocations_path)
    if not revocation_raw or revocation_raw.get("schema") != REVOCATION_SCHEMA:
        result["reasons"].append("revocation registry missing or invalid")
        revoked_ids: set[str] = set()
    else:
        revoked_ids = {str(x) for x in (revocation_raw.get("revoked_receipt_ids") or [])}
    if str(receipt.get("receipt_id")) in revoked_ids:
        result["reasons"].append("receipt revoked")
    if bool(receipt.get("revoked")):
        result["reasons"].append("receipt self-revoked")
    if component and receipt.get("component") != component:
        result["reasons"].append("component mismatch")
    if scope and receipt.get("scope") != scope:
        result["reasons"].append("scope mismatch")
    if claim_type and str(receipt.get("claim_type") or "").upper() != claim_type.upper():
        result["reasons"].append("claim type mismatch")

    now = now or datetime.now(timezone.utc)
    issued = _parse_time(receipt.get("issued_at")); expires = _parse_time(receipt.get("expires_at"))
    if issued is None or expires is None:
        result["reasons"].append("issued/expiry time missing or invalid")
    else:
        if issued > now:
            result["reasons"].append("receipt not yet valid")
        if expires <= now:
            result["reasons"].append("receipt expired")

    proof = receipt.get("proof") or {}
    for gate in REQUIRED_GATES:
        if proof.get(gate) is not True:
            result["reasons"].append(f"proof gate missing: {gate}")
    frozen = tuple(ARTIFACT_HASH_ROLES)
    for key in frozen:
        val = str(proof.get(key) or "")
        if len(val) != 64 or any(c not in "0123456789abcdefABCDEF" for c in val):
            result["reasons"].append(f"invalid proof hash: {key}")
    prospective_start = _parse_time(proof.get("prospective_start"))
    prospective_end = _parse_time(proof.get("prospective_end"))
    try:
        prospective_observations = int(proof.get("prospective_observations") or 0)
    except (TypeError, ValueError):
        prospective_observations = 0
    if prospective_start is None or prospective_end is None or prospective_start >= prospective_end:
        result["reasons"].append("prospective evidence window missing or invalid")
    elif prospective_end > now:
        result["reasons"].append("prospective evidence has not matured")
    if prospective_observations < 20:
        result["reasons"].append("insufficient prospective observations")

    if claim_type and claim_type.upper() == "CAPITAL_PERMISSION":
        approval = receipt.get("human_approval") or {}
        if approval.get("approved") is not True or not approval.get("approver_id"):
            result["reasons"].append("human approval missing")

    if verify_artifacts:
        ok, reasons = _verify_artifacts(receipt)
        if not ok:
            result["reasons"].extend(reasons)

    expected_trust_hash = str(trust_store_sha256 or os.getenv("WARROOM_TRUST_ROOT_SHA256", "")).lower()
    actual_trust_hash = file_sha256(trust_store_path)
    trust_raw = _json_file(trust_store_path)
    if not expected_trust_hash or len(expected_trust_hash) != 64:
        result["reasons"].append("out-of-band trust-root hash not configured")
    elif actual_trust_hash != expected_trust_hash:
        result["reasons"].append("trust-root hash mismatch")
    if not trust_raw or trust_raw.get("schema") != TRUST_SCHEMA:
        result["reasons"].append("trust store schema invalid")
        keys = {}
    else:
        keys = {str(k): dict(v) for k, v in (trust_raw.get("keys") or {}).items() if isinstance(v, dict)}
    key_id = str(receipt.get("key_id") or "")
    key_row = keys.get(key_id)
    if not key_row:
        result["reasons"].append("signing key is not trusted")
    else:
        if key_row.get("disabled") is True:
            result["reasons"].append("signing key disabled")
        key_expiry = _parse_time(key_row.get("expires_at")) if key_row.get("expires_at") else None
        if key_expiry is not None and key_expiry <= now:
            result["reasons"].append("signing key expired")
        allowed_components = key_row.get("allowed_components") or ["*"]
        allowed_scopes = key_row.get("allowed_scopes") or ["*"]
        if component and "*" not in allowed_components and component not in allowed_components:
            result["reasons"].append("key not authorized for component")
        if scope and "*" not in allowed_scopes and scope not in allowed_scopes:
            result["reasons"].append("key not authorized for scope")
        try:
            public_raw = base64.b64decode(str(key_row.get("public_key_base64") or ""), validate=True)
            sig = base64.b64decode(str(receipt.get("signature") or ""), validate=True)
            Ed25519PublicKey.from_public_bytes(public_raw).verify(sig, _canonical(receipt_payload(receipt)))
        except (ValueError, InvalidSignature, TypeError):
            result["reasons"].append("signature invalid")

    result["valid"] = not result["reasons"]
    return result


def find_receipt(receipt_id: str | None) -> Path | None:
    if not receipt_id:
        return None
    candidate = RECEIPTS_DIR / f"{receipt_id}.json"
    return candidate if candidate.is_file() else None
