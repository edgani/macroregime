"""Exact-scope directional and execution authorization contract."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import hashlib
import json

from proof_receipts import find_receipt, verify_receipt


def _num(value: Any) -> float | None:
    try:
        x = float(value)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def _parse_time(value: Any) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def lineage_digest(data_contract: dict) -> str:
    clean = {k: data_contract.get(k) for k in sorted(data_contract) if k not in {"lineage_hash", "signature"}}
    return hashlib.sha256(json.dumps(clean, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def authorize_direction(*, component: str, scope: str, market: str, instrument: str, horizon: str,
                        orientation: str, data_contract: dict | None, execution_geometry: dict | None,
                        receipt: dict | str | None = None, now: datetime | None = None) -> dict:
    reasons: list[str] = []
    market = str(market or "").lower(); instrument = str(instrument or "").upper(); orientation = str(orientation or "").upper()
    if orientation not in {"LONG", "SHORT"}:
        reasons.append("orientation must be LONG or SHORT")
    if market in {"idx", "ihsg"} and orientation == "SHORT":
        reasons.append("IHSG is long-only")
    if not instrument or not horizon:
        reasons.append("instrument/horizon missing")

    dc = data_contract or {}
    as_of = _parse_time(dc.get("as_of")); now = now or datetime.now(timezone.utc)
    max_age = _num(dc.get("max_age_seconds"))
    if not dc.get("source") or not dc.get("dataset"):
        reasons.append("data source/dataset missing")
    if as_of is None or max_age is None or max_age <= 0:
        reasons.append("freshness contract missing")
    elif (now - as_of).total_seconds() > max_age:
        reasons.append("data contract stale")
    expected_lineage = str(dc.get("lineage_hash") or "")
    if len(expected_lineage) != 64 or expected_lineage != lineage_digest(dc):
        reasons.append("lineage hash invalid")

    eg = execution_geometry or {}
    entry = _num(eg.get("entry")); stop = _num(eg.get("stop")); target = _num(eg.get("target"))
    if None in {entry, stop, target}:
        reasons.append("execution geometry incomplete")
    elif orientation == "LONG" and not (stop < entry < target):
        reasons.append("invalid long execution geometry")
    elif orientation == "SHORT" and not (target < entry < stop):
        reasons.append("invalid short execution geometry")

    exact_scope = f"{scope}|{market}|{instrument}|{horizon}|{orientation}"
    receipt_ref = receipt
    if isinstance(receipt_ref, str) and "/" not in receipt_ref and "\\" not in receipt_ref and not receipt_ref.endswith(".json"):
        receipt_ref = find_receipt(receipt_ref)
    proof = verify_receipt(receipt_ref, component=component, scope=exact_scope, claim_type="CAPITAL_PERMISSION", now=now)
    if not proof.get("valid"):
        reasons.extend(f"receipt: {r}" for r in proof.get("reasons") or [])
    return {
        "authorized": not reasons,
        "directional_permission": not reasons,
        "capital_permission": "HUMAN_APPROVED_LIMITED_PRODUCTION" if not reasons else "BLOCKED",
        "exact_scope": exact_scope,
        "receipt_id": proof.get("receipt_id"),
        "reasons": reasons,
    }
