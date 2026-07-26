"""Attach V6.4 scoped proof evidence without granting live selection or capital.

V6.4 deliberately separates four questions:
1) did a historical aggregate market claim survive confirmatory controls,
2) did it survive in the modern all-stock era,
3) is a point-in-time stock selector reconstructed and validated,
4) is it operationally/capital ready.
Only (1) passes for three frozen V58 candidates. Everything live remains blocked.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "research_v64/results/V64_THREE_SURVIVOR_CONFIRMATION_RESULTS.json"
TSMOM = ROOT / "research_v64/results/V64_TSMOM_CRISIS_OVERLAY_RESULTS.json"
PROTOCOL = ROOT / "research_v64/protocols/V64_THREE_SURVIVOR_CONFIRMATION_PROTOCOL_FROZEN.json"
TSMOM_PROTOCOL = ROOT / "research_v64/protocols/V64_TSMOM_CRISIS_OVERLAY_PROTOCOL_FROZEN.json"
MODERN_RESULTS = ROOT / "research_v64/results/V64_MODERN_212_FACTOR_CONFIRMATION_RESULTS.json"
MODERN_PROTOCOL = ROOT / "research_v64/protocols/V64_MODERN_212_FACTOR_CONFIRMATION_PROTOCOL_FROZEN.json"
MODERN_GRID = ROOT / "research_v64/protocols/V64_MODERN_212_FACTOR_GRID_FROZEN.csv"
TRIALS = ROOT / "V64_GLOBAL_TRIAL_ACCOUNTING.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fallback(reason: str) -> dict[str, Any]:
    return {
        "schema": "warroom.v64.scoped_proof_evidence.fallback",
        "status": "UNAVAILABLE_FAIL_CLOSED",
        "reason": reason,
        "claims": [],
        "historical_gross_market_claims_proven": 0,
        "modern_all_stock_claims_proven": 0,
        "modern_non_micro_investable_claims_proven": 0,
        "stock_level_pit_selectors_proven": 0,
        "operational_ready_components": 0,
        "live_predictive_components_promoted": 0,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }


def load_research_evidence_v64() -> dict[str, Any]:
    try:
        results = json.loads(RESULTS.read_text(encoding="utf-8"))
        tsmom = json.loads(TSMOM.read_text(encoding="utf-8"))
        modern = json.loads(MODERN_RESULTS.read_text(encoding="utf-8"))
        trials = json.loads(TRIALS.read_text(encoding="utf-8"))
    except Exception as exc:
        return _fallback(f"V64 evidence unreadable: {type(exc).__name__}: {exc}")
    if results.get("schema") != "warroom.v64.three_survivor_confirmation.results.v1":
        return _fallback("V64 survivor results schema mismatch")
    if tsmom.get("schema") != "warroom.v64.tsmom_crisis_overlay.results.v1":
        return _fallback("V64 TSMOM results schema mismatch")
    if modern.get("schema") != "warroom.v64.modern_212_factor_confirmation.results.v1":
        return _fallback("V64 modern factor results schema mismatch")
    if trials.get("schema") != "warroom.v64.global_trial_accounting.v1":
        return _fallback("V64 trial accounting schema mismatch")
    if results.get("protocol_sha256") != _sha(PROTOCOL):
        return _fallback("V64 survivor protocol hash mismatch")
    if tsmom.get("protocol_sha256") != _sha(TSMOM_PROTOCOL):
        return _fallback("V64 TSMOM protocol hash mismatch")
    if modern.get("protocol_sha256") != _sha(MODERN_PROTOCOL) or modern.get("grid_sha256") != _sha(MODERN_GRID):
        return _fallback("V64 modern factor protocol/grid hash mismatch")
    if modern.get("survivors") != ["SmileSlope"] or modern.get("modern_gross_claims_passed") != 1:
        return _fallback("V64 modern factor survivor invariant mismatch")
    claims = results.get("claim_ledger")
    if not isinstance(claims, list) or len(claims) != 3:
        return _fallback("V64 exact frozen claim ledger must contain three rows")
    for row in claims:
        if not isinstance(row, dict):
            return _fallback("V64 invalid claim row")
        if row.get("proof_scope") != "HISTORICAL_GROSS_MARKET_CLAIM_PROVEN":
            return _fallback("V64 attempted unsupported proof scope")
        if row.get("historical_gross_proven") is not True:
            return _fallback("V64 historical proof count inconsistent")
        if row.get("modern_all_stock_gross_proven") is not False:
            return _fallback("V64 attempted modern promotion")
        if row.get("modern_non_micro_investable_proven") is not False:
            return _fallback("V64 attempted investable promotion")
        if row.get("stock_level_pit_selector_proven") is not False:
            return _fallback("V64 attempted stock-selector promotion")
        if row.get("operational_ready") is not False or row.get("capital_permission") != "BLOCKED":
            return _fallback("V64 attempted operational/capital promotion")
    modern_detail = modern.get("details", {}).get("SmileSlope", {})
    modern_claim = {
        "claim_id": "SmileSlope",
        "proof_scope": "MODERN_ALL_STOCK_AGGREGATE_GROSS_CLAIM_SUPPORTED",
        "modern_all_stock_gross_proven": True,
        "independent_external_lockbox": False,
        "flat_10bp_hurdle_pass": bool(modern_detail.get("flat_10bp_hurdle_pass", False)),
        "flat_25bp_hurdle_pass": bool(modern_detail.get("flat_25bp_hurdle_pass", False)),
        "modern_non_micro_investable_proven": False,
        "stock_level_pit_selector_proven": False,
        "operational_ready": False,
        "capital_permission": "BLOCKED",
        "claim_limit": modern.get("claim_limit"),
    }
    all_claims = deepcopy(claims) + [modern_claim]
    invariants = {
        "historical_gross_market_claims_proven": 3,
        "modern_all_stock_claims_proven": 1,
        "independent_modern_claims_proven": 0,
        "modern_non_micro_investable_claims_proven": 0,
        "stock_level_pit_selectors_proven": 0,
        "operational_ready_components": 0,
        "live_predictive_components_promoted": 0,
    }
    for key, expected in invariants.items():
        actual = trials.get(key)
        if actual != expected:
            return _fallback(f"V64 invariant mismatch: {key}={actual!r}")
    if trials.get("capital_permission") != "BLOCKED" or float(trials.get("live_decision_weight", 1)) != 0.0:
        return _fallback("V64 capital/live-weight invariant mismatch")
    return {
        "schema": "warroom.v64.scoped_proof_evidence.v1",
        "status": "RECONCILED_SCOPED_PROOF",
        "created_at_utc": trials.get("created_at_utc"),
        "claims": all_claims,
        **invariants,
        "tsmom_crisis_overlay_verdict": tsmom.get("verdict", "NOT_PROVEN"),
        "new_confirmatory_claim_records": trials.get("new_confirmatory_claim_records", 20),
        "total_empirical_claim_records": trials.get("total_empirical_claim_records", 232488),
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
        "claim_boundary": (
            "Three aggregate historical gross factor claims passed frozen confirmatory controls. One options-based "
            "factor, SmileSlope, passed the modern all-stock aggregate screen in the reused maintained archive, but "
            "did not clear the familywise 10bp/month hurdle and has no independent external lockbox, non-micro "
            "investable reconstruction, point-in-time ticker selector, operational feed, or capital permission."
        ),
    }


def attach_research_evidence_v64(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    out = deepcopy(desk)
    out["research_evidence_v64"] = load_research_evidence_v64()
    return out
