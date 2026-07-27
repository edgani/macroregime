"""V9.5 exact-scope proof registry.

The dashboard consumes only hash-bound V9.5 proof-run outputs. Legacy receipt booleans and raw
editable metrics cannot activate a component. The global result is fail-closed unless all five exact
market proof runs independently pass the V9.5 cryptographic and recomputation firewall.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from global_market_promotion_gate_v95 import evaluate_all

HERE = Path(__file__).resolve().parent
REGISTRY_PATH = HERE / "component_registry_v95.json"
POLICY_PATH = HERE / "NO_TECHNICAL_ANALYSIS_POLICY.json"


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_path(relative: str) -> Path | None:
    try:
        path = (HERE / relative).resolve(); path.relative_to(HERE.resolve())
        return path
    except Exception:
        return None


def load_registry() -> dict[str, Any]:
    try:
        raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        raw = {"version": "9.5", "schema": "warroom.v95.component_registry.v1", "components": {}}
    if raw.get("schema") != "warroom.v95.component_registry.v1" or not isinstance(raw.get("components"), dict):
        return {"version": "9.5", "schema": "warroom.v95.component_registry.v1", "components": {}}
    return raw


def component_status(component: str, row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    out = dict(row); market = str(out.get("market") or "").lower()
    out.update({"decision_active": False, "capital_permission": "BLOCKED", "live_weight": 0.0})
    relative = str(out.get("proof_run_path") or "")
    expected = str(out.get("proof_run_sha256") or "").lower()
    path = _safe_path(relative) if relative else None
    run: dict[str, Any] | None = None
    reasons: list[str] = []
    if path is None or not path.is_file():
        reasons.append("V9.5 proof run not installed")
    elif len(expected) != 64 or _sha(path) != expected:
        reasons.append("proof-run hash missing or mismatched")
    else:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("proof run root is not an object")
            run = raw
        except Exception as exc:
            reasons.append(f"proof run unreadable: {type(exc).__name__}: {exc}")
    if run is not None:
        if run.get("schema") != "warroom.v95.blind_proof_run.v1":
            reasons.append("wrong proof-run schema")
        if str(run.get("market") or "").lower() != market:
            reasons.append("proof-run market mismatch")
        if run.get("trading_ready") is not True or run.get("capital_permission") != "LIMITED_PRODUCTION_ELIGIBLE":
            reasons.append("proof run did not pass")
        if (run.get("signed_receipt_verification") or {}).get("valid") is not True:
            reasons.append("signed receipt is not valid")
        if run.get("errors"):
            reasons.append("proof run contains errors")
    valid = not reasons and run is not None
    out.update({
        "proof_run_valid": valid,
        "proof_run_hash": expected if valid else None,
        "proof_run_reasons": sorted(set(reasons)),
        "decision_active": valid,
        "capital_permission": "HUMAN_APPROVED_LIMITED_PRODUCTION" if valid else "BLOCKED",
        "live_weight": 1.0 if valid else 0.0,
        "state": "HUMAN_APPROVED_LIMITED_PRODUCTION" if valid else "AWAITING_BOUND_V95_PROOF",
    })
    return out, run if valid else None


def attach_proof_registry(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    registry = load_registry(); statuses: dict[str, Any] = {}; runs: dict[str, dict[str, Any]] = {}
    for name, row in registry["components"].items():
        status, run = component_status(name, row if isinstance(row, dict) else {})
        statuses[name] = status
        if run is not None:
            runs[str(status.get("market"))] = run
    global_result = evaluate_all(runs)
    authorized = sorted(name for name, row in statuses.items() if row.get("decision_active") is True)
    desk["proof_registry"] = {**registry, "components": statuses, "global_adjudication": global_result}
    try:
        desk["no_technical_analysis_policy"] = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except Exception:
        desk["no_technical_analysis_policy"] = {"capital_default": "BLOCKED", "effective_version": "9.5"}
    desk["proof_status"] = {
        "final_trading_system": bool(global_result["global_trading_ready"]),
        "all_market_trading_ready": bool(global_result["global_trading_ready"]),
        "predictive_components_promoted": len(authorized),
        "decision_active_predictive_components": len(authorized),
        "capital_authorized_components": authorized,
        "missing_market_components": [m for m in ("us", "idx", "commodity", "fx", "crypto") if m not in runs],
        "capital_permission": global_result["capital_permission"],
        "operational_permission": "SHADOW_TRADING_READY",
        "software_is_not_alpha": True,
        "evidence_production_runtime_ready": True,
        "proof_firewall_version": "9.5",
    }
    return desk
