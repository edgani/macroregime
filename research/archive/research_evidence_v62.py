"""Attach V6.1/V6.2 research evidence and global trial accounting fail-closed.

This module is evidence accounting only. It cannot grant direction, targets, sizing,
or capital permission. Every component must keep zero live weight and zero production
survivors unless a separately verified exact-scope proof receipt exists.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "V62_RESEARCH_EVIDENCE_REGISTRY.json"
TRIALS = ROOT / "V62_GLOBAL_TRIAL_ACCOUNTING.json"


def _fallback(reason: str) -> dict[str, Any]:
    return {
        "schema": "warroom.v62.research_evidence.fallback",
        "status": "UNAVAILABLE_FAIL_CLOSED",
        "reason": reason,
        "components": [],
        "global_trial_accounting": {},
        "production_promoted": 0,
        "capital_permission": "BLOCKED",
    }


def load_research_evidence_v62() -> dict[str, Any]:
    try:
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        trials = json.loads(TRIALS.read_text(encoding="utf-8"))
    except Exception as exc:
        return _fallback(f"V62 evidence unreadable: {type(exc).__name__}: {exc}")

    if registry.get("schema") != "warroom.v62.research_evidence_registry":
        return _fallback("V62 registry schema mismatch")
    if trials.get("schema") != "warroom.v62.global_trial_accounting":
        return _fallback("V62 trial-accounting schema mismatch")
    components = registry.get("components")
    if not isinstance(components, list):
        return _fallback("V62 components must be a list")
    for row in components:
        if not isinstance(row, dict):
            return _fallback("invalid V62 component row")
        if float(row.get("live_decision_weight", 1.0)) != 0.0:
            return _fallback("V62 component attempted nonzero live weight")
        if int(row.get("production_survivors", -1)) != 0:
            return _fallback("V62 component attempted production promotion")
    if int(registry.get("production_promoted", -1)) != 0:
        return _fallback("V62 registry production count must remain zero")
    if registry.get("capital_permission") != "BLOCKED":
        return _fallback("V62 registry capital permission must remain blocked")
    if int(trials.get("live_predictive_components_promoted", -1)) != 0:
        return _fallback("V62 trial accounting attempted live promotion")
    if int(trials.get("production_proven_early_move_drivers", -1)) != 0:
        return _fallback("V62 trial accounting attempted production proof")
    if trials.get("capital_permission") != "BLOCKED":
        return _fallback("V62 trial accounting capital permission must remain blocked")

    return {
        **deepcopy(registry),
        "status": "RECONCILED_RESEARCH_EVIDENCE_ONLY",
        "global_trial_accounting": deepcopy(trials),
        "semantics": (
            "Negative/blocked research accounting and engineering pipeline status only; "
            "never an autonomous direction, target, expected return, order, or position size."
        ),
    }


def attach_research_evidence_v62(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    out = deepcopy(desk)
    out["research_evidence_v62"] = load_research_evidence_v62()
    return out
