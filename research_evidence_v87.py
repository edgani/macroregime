"""Attach V8.7 narrative-to-repricing evidence status to dashboard snapshots."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def _load(name: str) -> Any:
    try:
        return json.loads((HERE / name).read_text(encoding="utf-8"))
    except Exception:
        return None


def attach_research_evidence_v87(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    current = _load("V87_CURRENT_NARRATIVE_AUDIT.json") or {}
    protocol = _load("V87_REPRICING_READINESS_PROTOCOL_FROZEN.json") or {}
    desk["v87_narrative_repricing"] = {
        "version": "8.7",
        "state": current.get("state", "BLOCKED_AWAITING_PIT_NARRATIVE_PANEL"),
        "capital_permission": "BLOCKED",
        "claim": "War Room must capture a falsifiable causal narrative and prove that activation evidence adds timing value beyond bottleneck discovery alone.",
        "current_result": current,
        "protocol": protocol,
        "technical_predictors": 0,
        "named_cases_are_diagnostics_not_formula_inputs": True,
    }
    return desk
