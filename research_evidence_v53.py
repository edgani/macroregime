"""Attach reconciled v5.1 research evidence without granting a live trading permission."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "research_evidence_registry_v53.json"


def _fallback(reason: str) -> dict[str, Any]:
    return {
        "schema": "warroom.research_evidence_registry.v53.fallback",
        "status": "UNAVAILABLE_FAIL_CLOSED",
        "reason": reason,
        "claims": [],
        "predictive_components_promoted_to_live": 0,
        "capital_permission": "BLOCKED",
    }


def load_research_evidence() -> dict[str, Any]:
    try:
        raw = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except Exception as exc:
        return _fallback(f"registry unreadable: {type(exc).__name__}: {exc}")
    if raw.get("schema") != "warroom.research_evidence_registry.v53":
        return _fallback("registry schema mismatch")
    claims = raw.get("claims")
    if not isinstance(claims, list):
        return _fallback("claims must be a list")
    for row in claims:
        if not isinstance(row, dict):
            return _fallback("invalid claim row")
        if float(row.get("live_decision_weight", 1.0)) != 0.0:
            return _fallback("historical claim attempted nonzero live weight")
        if row.get("capital_permission") != "BLOCKED":
            return _fallback("historical claim attempted capital permission")
        if row.get("prospective_pass") is not False:
            return _fallback("historical claim attempted prospective promotion")
    if int(raw.get("predictive_components_promoted_to_live", -1)) != 0:
        return _fallback("live promotion count must remain zero")
    if raw.get("capital_permission") != "BLOCKED":
        return _fallback("global capital permission must remain blocked")
    out = deepcopy(raw)
    out["status"] = "RECONCILED_RESEARCH_EVIDENCE_ONLY"
    out["semantics"] = "Historical claim accounting and failed/aborted studies; never an autonomous direction, target, order, or size."
    return out


def attach_research_evidence_v53(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    out = deepcopy(desk)
    out["research_evidence_v53"] = load_research_evidence()
    return out
