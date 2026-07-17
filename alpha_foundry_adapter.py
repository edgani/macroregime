from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
FOUNDRY = HERE / "alpha_foundry"
OUTPUTS = FOUNDRY / "outputs"
PROCESSED = FOUNDRY / "data" / "processed"
REVIEW = HERE / "research_review"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_csv(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        return rows[:limit] if limit else rows
    except Exception:
        return []


def _file_state(relative: str) -> dict[str, Any]:
    path = FOUNDRY / relative
    if not path.exists():
        return {"file": relative, "status": "MISSING", "size_mb": None, "modified": None}
    stat = path.stat()
    return {
        "file": relative,
        "status": "READY",
        "size_mb": round(stat.st_size / 1024 / 1024, 3),
        "modified": int(stat.st_mtime),
    }


def _latest_prospective() -> dict[str, Any] | None:
    root = OUTPUTS / "prospective"
    if not root.exists():
        return None
    seals = sorted(root.glob("*/PROSPECTIVE_SEAL.json"))
    return _read_json(seals[-1]) if seals else None


def load_alpha_foundry_state() -> dict[str, Any]:
    shortlist_path = OUTPUTS / "current" / "US_TOP20_SHADOW_SHORTLIST.csv"
    receipt_path = OUTPUTS / "current" / "US_TOP20_SHADOW_RECEIPT.json"
    validation_path = OUTPUTS / "discovery" / "COMPONENT_SELECTOR_TOURNAMENT__VALIDATION.csv"
    discovery_path = OUTPUTS / "discovery" / "COMPONENT_SELECTOR_TOURNAMENT__DISCOVERY.csv"
    graveyard_path = OUTPUTS / "discovery" / "TRIAL_GRAVEYARD.csv"
    lockbox_path = OUTPUTS / "lockbox" / "LOCKBOX_OPENED.json"

    shortlist = _read_csv(shortlist_path, 20)
    validation = _read_csv(validation_path)
    discovery = _read_csv(discovery_path)
    graveyard = _read_csv(graveyard_path)
    receipt = _read_json(receipt_path)
    lockbox = _read_json(lockbox_path)
    prospective = _latest_prospective()

    candidates = [row for row in validation if str(row.get("promotion_pass", "")).lower() in {"true", "1", "yes"}]
    components = _read_csv(REVIEW / "MASTER_COMPONENT_COVERAGE.csv")
    blockers = _read_csv(REVIEW / "BLOCKER_IMPACT_MATRIX.csv")
    decisions = _read_csv(REVIEW / "CPI_LABOR_FINAL_DECISIONS.csv")
    free_full = sum(row.get("free_proof_feasibility") == "FULL" for row in components)
    free_partial = sum(row.get("free_proof_feasibility") == "PARTIAL" for row in components)
    free_low = sum(row.get("free_proof_feasibility") == "LOW" for row in components)

    readiness = [
        _file_state("data/processed/us_monthly_research_panel.parquet"),
        _file_state("data/processed/prices_sp500_pit.parquet"),
        _file_state("data/processed/entity_master.parquet"),
        _file_state("outputs/current/US_TOP20_SHADOW_SHORTLIST.csv"),
        _file_state("outputs/discovery/COMPONENT_SELECTOR_TOURNAMENT__VALIDATION.csv"),
        _file_state("outputs/discovery/TRIAL_GRAVEYARD.csv"),
        _file_state("outputs/lockbox/LOCKBOX_OPENED.json"),
    ]
    required_ready = sum(row["status"] == "READY" for row in readiness)

    return {
        "integrated": True,
        "ui_contract": "ORIGINAL_14_TAB_UI_PRESERVED",
        "active_branch": "US Stocks Free Alpha Foundry",
        "status": "SHADOW_READY" if shortlist else "RUNNER_READY_NOT_EXECUTED",
        "claim_ceiling": "HISTORICAL_CANDIDATE / PROSPECTIVE_SHADOW",
        "permissions": {"research": True, "shadow": True, "paper": False, "live": False},
        "counts": {
            "shortlist": len(shortlist),
            "registered_trials": len(graveyard),
            "historical_candidates": len(candidates),
            "proven_components": 0,
            "proven_selectors": 0,
            "proven_alpha": 0,
            "coverage_components": len(components),
            "free_full": free_full,
            "free_partial": free_partial,
            "free_low": free_low,
            "readiness_ready": required_ready,
            "readiness_total": len(readiness),
        },
        "shortlist": shortlist,
        "shortlist_receipt": receipt,
        "validation": validation,
        "discovery": discovery,
        "lockbox": lockbox,
        "prospective": prospective,
        "readiness": readiness,
        "blockers": blockers[:12],
        "final_decisions": decisions,
        "fixed_results": {
            "cpi_labor_actual_pipeline": "FIXED_KEEP",
            "cpi_labor_5d20d_signal": "FINAL_DROP",
            "ndx_d0_packet": "FROZEN_SHADOW_ONLY",
            "system_proven_components": 0,
            "system_proven_selectors": 0,
            "system_proven_alpha": 0,
        },
        "warning": (
            "Alpha Foundry is integrated behind the original UI. A real shortlist appears only after "
            "the free-data pipeline runs. Historical positives remain candidates until one-shot lockbox "
            "and prospective gates pass."
        ),
    }


def attach_alpha_foundry(desk: dict[str, Any]) -> dict[str, Any]:
    desk = dict(desk or {})
    desk["alpha_foundry"] = load_alpha_foundry_state()
    desk.setdefault("meta", {})
    desk["meta"]["safe_fail_closed"] = True
    return desk


def minimal_desk(error: str | None = None) -> dict[str, Any]:
    markets = {
        key: {"label": key.upper(), "long_only": key == "ihsg", "drivers": [], "bias": "NO_DATA", "funnel": {"universe": 0, "eliminated": 0, "setups": 0}, "setups": []}
        for key in ("us", "ihsg", "crypto", "commodity", "fx")
    }
    return attach_alpha_foundry({
        "meta": {"generated": None, "source": "NO_DATA", "sources": {}, "fred_source": "NO_DATA", "universe_n": 0, "note": error or "Live data unavailable; research state still loaded.", "feeds_status": {}, "safe_fail_closed": True},
        "systemic": {}, "regime_tf": {}, "regional": {}, "grades": {}, "markets": markets, "alpha": [], "desk_picks": {}, "feeds": {},
    })
