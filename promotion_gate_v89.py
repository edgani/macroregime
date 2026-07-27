"""V8.9 anti-fixture promotion wrapper around the exact-scope V8.8 gate."""
from __future__ import annotations
from typing import Any
import hashlib
import json
import re

from promotion_gate_v88 import evaluate as evaluate_v88

HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")


def evaluate(receipt: dict[str, Any]) -> dict[str, Any]:
    base = evaluate_v88(receipt)
    reasons = list(base.get("reasons") or [])
    if receipt.get("evidence_mode") != "REAL_POINT_IN_TIME_BLIND":
        reasons.append("evidence_mode is not REAL_POINT_IN_TIME_BLIND")
    if receipt.get("synthetic_data") is not False:
        reasons.append("synthetic_data must be false")
    if receipt.get("test_fixture") is not False:
        reasons.append("test_fixture must be false")
    if receipt.get("holdout_visible_to_model") is not False:
        reasons.append("holdout_visible_to_model must be false")
    if receipt.get("data_admission_pass") is not True:
        reasons.append("real data admission did not pass")
    for field in ("data_admission_hash", "dataset_manifest_hash", "blind_custodian_receipt_hash"):
        if not HEX64.fullmatch(str(receipt.get(field) or "").lower()):
            reasons.append(f"invalid {field}")
    payload = {
        "schema": "warroom.v89.market_promotion_adjudication.v1",
        "eligible": not reasons,
        "permission": "LIMITED_PRODUCTION_ELIGIBLE" if not reasons else "BLOCKED",
        "scope": receipt.get("scope") or {},
        "reasons": sorted(set(reasons)),
    }
    payload["adjudication_hash"] = hashlib.sha256(_canonical(payload)).hexdigest()
    return payload
