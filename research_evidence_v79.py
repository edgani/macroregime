"""Attach the V7.9 final exact-scope trading core and its live fail-closed instruction."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any
import hashlib
import json
import os

from final_trading_core_v79 import CoreConfig, SYSTEM_ID, build_trade_instruction
from release_contract_v79 import release_contract
from us_broad_equity_live_feed_v79 import fetch_completed_monthly_closes

ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "research_v66" / "results" / "V66_SMA10_RISK_REDUCTION_CONFIRMATION_RESULTS.json"
PROTOCOL = ROOT / "research_v66" / "protocols" / "V66_SMA10_RISK_REDUCTION_CONFIRMATION_PROTOCOL_FROZEN.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _protocol_semantic_sha(path: Path) -> str:
    obj = json.loads(path.read_text(encoding="utf-8"))
    obj.pop("protocol_sha256", None)
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _truthy(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _verify_proof() -> dict[str, Any]:
    try:
        result = json.loads(RESULT.read_text(encoding="utf-8"))
        protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"status": "FAIL", "reason": f"proof files unreadable: {type(exc).__name__}: {exc}"}
    failures = []
    if result.get("passed") is not True:
        failures.append("confirmation result is not PASS")
    if result.get("protocol_sha256") != protocol.get("protocol_sha256"):
        failures.append("result/protocol receipt mismatch")
    if protocol.get("protocol_sha256") != _protocol_semantic_sha(PROTOCOL):
        failures.append("frozen protocol semantic hash mismatch")
    adjudication = result.get("adjudication") or {}
    if adjudication.get("scoped_claim") != "CONFIRMED_HISTORICAL_RISK_REDUCTION":
        failures.append("confirmation claim mismatch")
    if not all((result.get("gates") or {}).values()):
        failures.append("one or more frozen confirmation gates failed")
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "result_sha256": _sha(RESULT),
        "protocol_file_sha256": _sha(PROTOCOL),
        "protocol_semantic_sha256": protocol.get("protocol_sha256"),
        "confirmatory": result.get("confirmatory"),
        "confirmatory_25bps": result.get("confirmatory_25bps"),
        "rolling": result.get("rolling"),
        "claim_limit": result.get("claim_limit"),
    }


def load_research_evidence_v79(*, live: bool = True) -> dict[str, Any]:
    proof = _verify_proof()
    contract = release_contract()
    authorized = _truthy("WARROOM_V79_BASELINE_AUTHORIZED", False)
    instrument = os.getenv("WARROOM_V79_EQUITY_INSTRUMENT", "SPY").strip().upper() or "SPY"
    sleeve = _float_env("WARROOM_V79_SLEEVE_FRACTION", 1.0)
    cost = _float_env("WARROOM_V79_ESTIMATED_ONE_WAY_COST_BPS", 10.0)
    current_weight_raw = os.getenv("WARROOM_V79_CURRENT_EQUITY_WEIGHT")
    try:
        current_weight = float(current_weight_raw) if current_weight_raw not in (None, "") else None
    except Exception:
        current_weight = None

    if proof.get("status") != "PASS":
        return {
            "schema": "warroom.research_evidence.v79",
            "status": "PROOF_RECEIPT_FAIL_CLOSED",
            "system_id": SYSTEM_ID,
            "final_trading_system": False,
            "proof": proof,
            "release_contract": contract,
            "current_instruction": {},
            "capital_permission": "BLOCKED",
        }

    feed = fetch_completed_monthly_closes(timeout=4.0) if live else None
    rows = feed.observations if feed else []
    config = CoreConfig(
        equity_instrument=instrument,
        defensive_instrument="CASH",
        sleeve_fraction_of_account=sleeve,
        baseline_authorized=authorized,
        maximum_one_way_cost_bps=25.0,
        max_staleness_months=1,
    )
    instruction = build_trade_instruction(
        rows,
        config=config,
        current_equity_weight_in_sleeve=current_weight,
        estimated_one_way_cost_bps=cost,
        verified_live_feed=bool(feed and feed.status == "LIVE_DUAL_SOURCE_CONFIRMED" and feed.consensus_status == "PASS"),
    )
    return {
        "schema": "warroom.research_evidence.v79",
        "status": "FINAL_PROVEN_READY_TO_TRADE_EXACT_SCOPE",
        "system_id": SYSTEM_ID,
        "final_trading_system": True,
        "exact_scope": contract["final_scope"],
        "proof": proof,
        "live_feed": feed.to_dict() if feed else {
            "status": "LIVE_FETCH_DISABLED_FOR_VALIDATION",
            "observations": [],
            "reason": "Validation mode injects observations and does not use network data.",
        },
        "configuration": {
            "baseline_authorized": authorized,
            "equity_instrument": instrument,
            "defensive_instrument": "CASH",
            "sleeve_fraction_of_account": sleeve,
            "estimated_one_way_cost_bps": cost,
            "activation_env": "WARROOM_V79_BASELINE_AUTHORIZED=1",
        },
        "current_instruction": instruction.to_dict(),
        "capital_permission": "EXACT_SCOPE_READY" if instruction.ready_to_execute else "NO_ORDER_FAIL_CLOSED",
        "all_other_markets": {
            "US_INDIVIDUAL_TICKERS": "NO_TRADE_RESEARCH_ONLY",
            "IHSG": "NO_TRADE_RESEARCH_ONLY",
            "FX": "NO_TRADE_RESEARCH_ONLY",
            "COMMODITIES": "NO_TRADE_RESEARCH_ONLY",
            "CRYPTO": "NO_TRADE_RESEARCH_ONLY",
        },
        "claim_boundary": "Final and execution-ready only for the dedicated broad-US-equity monthly long/cash sleeve. No future-profit guarantee or permission outside that scope.",
    }


def attach_research_evidence_v79(desk: dict) -> dict:
    out = deepcopy(desk) if isinstance(desk, dict) else {}
    out["release_contract_v79"] = release_contract()
    out["research_evidence_v79"] = load_research_evidence_v79(live=not _truthy("WARROOM_V79_DISABLE_LIVE_FETCH", False))
    return out
