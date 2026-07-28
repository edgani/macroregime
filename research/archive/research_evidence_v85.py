"""Attach V8.5 evidence-production status to dashboard snapshots."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
VALIDATION = HERE / "V85_FINAL_VALIDATION.json"
SOURCE_MATRIX = HERE / "V85_OFFICIAL_SOURCE_MATRIX.json"


def _read(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def attach_research_evidence_v85(desk: dict) -> dict:
    out = deepcopy(desk) if isinstance(desk, dict) else {}
    validation = _read(VALIDATION)
    source_matrix = _read(SOURCE_MATRIX)
    out["v85_evidence_factory"] = {
        "version": "8.5",
        "state": "EVIDENCE_PRODUCTION_READY_CAPITAL_BLOCKED",
        "capital_permission": "BLOCKED",
        "software_validation": {
            "passed": validation.get("passed", 0),
            "total": validation.get("total", 0),
            "all_pass": bool(validation.get("all_pass")),
        },
        "official_sources": source_matrix.get("sources") or [],
        "proof_objects": [
            "immutable global trial ledger",
            "encrypted blind signal map",
            "point-in-time evidence contract",
            "prospective forecast/outcome ledger",
            "actual-fill profit-factor gate",
            "daily-equity drawdown and stress gate",
            "exact-scope promotion adjudicator",
        ],
        "claim": "The package can produce auditable future evidence, but no predictive model has yet accumulated the required mature outcomes.",
    }
    proof = out.setdefault("proof_status", {})
    proof.update({
        "final_trading_system": False,
        "capital_permission": "BLOCKED",
        "decision_active_predictive_components": 0,
        "evidence_production_runtime_ready": bool(validation.get("all_pass")),
        "reason": "Prospective outcomes, actual fills and exact-scope proof receipts do not yet exist.",
    })
    return out
