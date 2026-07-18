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

    registry = {}
    for row in components:
        registry.setdefault(row.get("tab", "UNKNOWN"), []).append({
            "component_id": row.get("component_id"),
            "component_name": row.get("component_name"),
            "decision_role": row.get("decision_role"),
            "current_status": row.get("current_status"),
            "main_blocker": row.get("main_blocker"),
            "impact_on_final_result": row.get("impact_on_final_result"),
        })

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
        "component_registry": registry,
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
    state = load_alpha_foundry_state()
    desk["alpha_foundry"] = state
    desk["component_registry"] = state.get("component_registry", {})
    desk.setdefault("meta", {})
    desk["meta"]["safe_fail_closed"] = True

    # One source of truth for ticker surfaces. Mission Control may only name a ticker if it
    # is also emitted by Alpha, a market setup, or the frozen Foundry shortlist. Raw RS rotation
    # remains available for the Flow tab as a descriptive observation.
    surfaced = set()
    setup_map = {}
    for market in (desk.get("markets") or {}).values():
        for row in market.get("setups") or []:
            tk = str(row.get("tk") or "").upper()
            if tk and tk != "—":
                surfaced.add(tk); setup_map[tk] = row
    for row in desk.get("alpha") or []:
        tk = str(row.get("tk") or "").upper()
        if tk: surfaced.add(tk)
    for row in state.get("shortlist") or []:
        tk = str(row.get("ticker") or "").upper()
        if tk:
            surfaced.add(tk)
            if tk in setup_map:
                row.update({
                    "entry": setup_map[tk].get("e"), "stop": setup_map[tk].get("s"),
                    "target": setup_map[tk].get("t"), "rr": setup_map[tk].get("rr"),
                    "level_source": setup_map[tk].get("level_source"),
                    "structural_target": setup_map[tk].get("structural_target"),
                })

    systemic = desk.setdefault("systemic", {})
    raw_in = [str(x).upper() for x in systemic.get("rotation_in_raw") or []]
    raw_out = [str(x).upper() for x in systemic.get("rotation_out_raw") or []]
    # RS rotation and PRICE_RS setups share the same price/relative-strength family. Their overlap
    # is not independent confirmation. Only a frozen selector/fundamental output can confirm Mission.
    independent = {str(row.get("ticker") or "").upper() for row in state.get("shortlist") or [] if row.get("ticker")}
    for market in (desk.get("markets") or {}).values():
        for row in market.get("setups") or []:
            if str(row.get("evidence_family") or "").upper() not in {"PRICE_RS", "PRICE_ONLY", ""}:
                tk = str(row.get("tk") or "").upper()
                if tk: independent.add(tk)
    systemic["rotation_in"] = [x for x in raw_in if x in independent]
    systemic["rotation_out"] = [x for x in raw_out if x in independent]
    systemic["rotation_same_family_overlap"] = [x for x in raw_in if x in surfaced and x not in independent]
    systemic["rotation_unconfirmed"] = [x for x in raw_in if x not in independent]
    systemic["rotation_claim"] = "INDEPENDENT_EVIDENCE_REQUIRED"
    systemic["surfaced_tickers"] = sorted(surfaced)
    return desk


def minimal_desk(error: str | None = None) -> dict[str, Any]:
    markets = {
        key: {"label": key.upper(), "long_only": key == "ihsg", "drivers": [], "bias": "NO_DATA", "funnel": {"loaded": 0, "surfaceable": 0, "history_eligible": 0, "signal_valid": 0, "displayed": 0, "failed": 0, "non_surfaceable": 0}, "setups": []}
        for key in ("us", "ihsg", "crypto", "commod", "fx")
    }
    return attach_alpha_foundry({
        "meta": {"generated": None, "source": "NO_DATA", "sources": {}, "fred_source": "NO_DATA", "universe_n": 0, "note": error or "Live data unavailable; research state still loaded.", "feeds_status": {}, "safe_fail_closed": True, "desk_schema_version": "V6_RICH_DYNAMIC_2026_07_18"},
        "systemic": {}, "regime_tf": {}, "regional": {}, "grades": {}, "markets": markets,
        "alpha": [], "alpha_watch": [], "macro_state": {}, "early_warning": {},
        "flow_rotation": {}, "supply_chain": {"claim":"REFERENCE_ONLY_NOT_CURRENT_SIGNAL","chains":[],"bottleneck":{}},
        "company_intel": [], "knowledge_graph": {"current_nodes":[],"current_edges":[]},
        "validation_state": {}, "research_engine": {}, "desk_picks": {}, "feeds": {},
    })
