"""Attach V8.6 extreme-winner falsification status to dashboard snapshots."""
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


def attach_research_evidence_v86(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    current = _load("V86_CURRENT_EXTREME_WINNER_AUDIT.json") or {}
    cases = _load("V86_CANONICAL_CASE_REGISTRY.json") or {}
    desk["v86_extreme_winner_benchmark"] = {
        "version": "8.6",
        "state": current.get("state", "BLOCKED_NO_SELECTOR_OUTPUT"),
        "capital_permission": "BLOCKED",
        "claim": "War Room is rejected unless it captures SNDK, PLTR, and a blind universe of extreme winners early while material upside remains.",
        "known_cases": [row.get("ticker") for row in cases.get("cases", []) if isinstance(row, dict)],
        "current_result": current,
        "technical_predictors": 0,
    }
    return desk
