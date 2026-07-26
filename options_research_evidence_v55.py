"""Attach V69/V70 options research state without granting trading permission."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
MAPPING = ROOT / "research_v55" / "V69_OPTIONS_GAMMA_MAPPING_FROZEN.json"
IMPLEMENTATION = ROOT / "research_v55" / "V70_OPTIONS_VOLATILITY_FLOW_IMPLEMENTATION.json"
VALIDATION = ROOT / "V70_OPTIONS_GAMMA_VALIDATION.json"
PROSPECTIVE_PROTOCOL = ROOT / "research_v55" / "V71_OPTIONS_PROSPECTIVE_PROTOCOL_FROZEN.json"
PROSPECTIVE_VALIDATION = ROOT / "V71_OPTIONS_PROSPECTIVE_VALIDATION.json"
SIGNED_DEALER_PROTOCOL = ROOT / "research_v56" / "V72_SPX_SIGNED_DEALER_PROTOCOL_FROZEN.json"
SIGNED_DEALER_EVALUATOR = ROOT / "research_v56" / "V72_OUTCOME_EVALUATOR_SPEC_FROZEN.json"
SIGNED_DEALER_EXTERNAL = ROOT / "research_v56" / "V72_EXTERNAL_EVIDENCE_REGISTER.json"
SIGNED_DEALER_VALIDATION = ROOT / "V72_SIGNED_DEALER_VALIDATION.json"
SIGNED_DEALER_EVALUATOR_VALIDATION = ROOT / "V72_OUTCOME_EVALUATOR_VALIDATION.json"
SIGNED_DEALER_ACQUISITION = ROOT / "V72_DATA_ACQUISITION_STATUS.json"
SIGNED_DEALER_RUNNER_VALIDATION = ROOT / "V72_RELEASE_RUNNER_VALIDATION.json"
SIGNED_DEALER_MANIFEST_VALIDATION = ROOT / "V72_MANIFEST_GENERATOR_VALIDATION.json"
SIGNED_DEALER_CALENDAR = ROOT / "research_v56" / "V72_C1_RTH_EXPECTED_CALENDAR.csv"


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {"status": "UNAVAILABLE_FAIL_CLOSED", "reason": "not an object"}
    except Exception as exc:
        return {"status": "UNAVAILABLE_FAIL_CLOSED", "reason": f"{path.name}: {type(exc).__name__}: {exc}"}


def load_options_research_v55() -> dict[str, Any]:
    mapping = _load(MAPPING)
    implementation = _load(IMPLEMENTATION)
    validation = _load(VALIDATION)
    prospective_protocol = _load(PROSPECTIVE_PROTOCOL)
    prospective_validation = _load(PROSPECTIVE_VALIDATION)
    signed_protocol = _load(SIGNED_DEALER_PROTOCOL)
    signed_evaluator = _load(SIGNED_DEALER_EVALUATOR)
    signed_external = _load(SIGNED_DEALER_EXTERNAL)
    signed_validation = _load(SIGNED_DEALER_VALIDATION)
    evaluator_validation = _load(SIGNED_DEALER_EVALUATOR_VALIDATION)
    acquisition = _load(SIGNED_DEALER_ACQUISITION)
    runner_validation = _load(SIGNED_DEALER_RUNNER_VALIDATION)
    manifest_validation = _load(SIGNED_DEALER_MANIFEST_VALIDATION)
    failures = []
    if mapping.get("live_decision_weight") != 0.0 or mapping.get("capital_permission") != "BLOCKED":
        failures.append("mapping attempted permission")
    if implementation.get("live_decision_weight") != 0.0 or implementation.get("capital_permission") != "BLOCKED":
        failures.append("implementation attempted permission")
    if validation.get("status") != "PASS" or validation.get("live_decision_weight") != 0.0 or validation.get("capital_permission") != "BLOCKED":
        failures.append("validation unavailable or unsafe")
    if prospective_protocol.get("live_decision_weight") != 0.0 or prospective_protocol.get("capital_permission") != "BLOCKED":
        failures.append("prospective protocol attempted permission")
    if prospective_validation.get("status") != "PASS" or prospective_validation.get("prospective_observations_collected") != 0 or prospective_validation.get("capital_permission") != "BLOCKED":
        failures.append("prospective ledger validation unavailable or unsafe")
    if signed_protocol.get("live_decision_weight") != 0.0 or signed_protocol.get("capital_permission") != "BLOCKED":
        failures.append("V72 protocol attempted permission")
    if signed_evaluator.get("live_decision_weight") != 0.0 or signed_evaluator.get("capital_permission") != "BLOCKED":
        failures.append("V72 evaluator attempted permission")
    if signed_validation.get("status") != "PASS" or signed_validation.get("capital_permission") != "BLOCKED":
        failures.append("V72 reconstruction validation unavailable or unsafe")
    if evaluator_validation.get("status") != "PASS" or evaluator_validation.get("capital_permission") != "BLOCKED":
        failures.append("V72 evaluator validation unavailable or unsafe")
    if acquisition.get("historical_outcomes_opened") is not False or acquisition.get("capital_permission") != "BLOCKED":
        failures.append("V72 acquisition state unsafe")
    if runner_validation.get("status") != "PASS" or runner_validation.get("checks_passed") != 19 or runner_validation.get("capital_permission") != "BLOCKED":
        failures.append("V72 release runner validation unavailable or unsafe")
    if manifest_validation.get("status") != "PASS" or manifest_validation.get("checks_passed") != 14 or manifest_validation.get("capital_permission") != "BLOCKED":
        failures.append("V72 manifest generator validation unavailable or unsafe")
    frozen_calendar = ((signed_protocol.get("data_integrity") or {}).get("frozen_expected_calendar") or {})
    if frozen_calendar.get("sessions") != 1440 or frozen_calendar.get("path") != "research_v56/V72_C1_RTH_EXPECTED_CALENDAR.csv":
        failures.append("V72 frozen calendar unavailable or unsafe")
    return {
        "schema": "warroom.options_research_evidence.v55",
        "status": "FAIL_CLOSED" if failures else "IMPLEMENTED_RESEARCH_ONLY",
        "failures": failures,
        "mapping": mapping,
        "implementation": implementation,
        "validation_summary": {
            "status": validation.get("status"),
            "checks_passed": validation.get("checks_passed"),
            "checks_total": validation.get("checks_total"),
        },
        "prospective_protocol": prospective_protocol,
        "prospective_validation_summary": {
            "status": prospective_validation.get("status"),
            "checks_passed": prospective_validation.get("checks_passed"),
            "checks_total": prospective_validation.get("checks_total"),
            "observations_collected": prospective_validation.get("prospective_observations_collected"),
        },
        "signed_dealer_v72": {
            "protocol": signed_protocol,
            "evaluator_spec": signed_evaluator,
            "external_evidence": signed_external,
            "reconstruction_validation": {
                "status": signed_validation.get("status"),
                "checks_passed": signed_validation.get("checks_passed"),
                "checks_total": signed_validation.get("checks_total"),
            },
            "outcome_evaluator_validation": {
                "status": evaluator_validation.get("status"),
                "checks_passed": evaluator_validation.get("checks_passed"),
                "checks_total": evaluator_validation.get("checks_total"),
                "production_outcomes": evaluator_validation.get("production_outcomes"),
            },
            "acquisition": acquisition,
            "release_runner_validation": {
                "status": runner_validation.get("status"),
                "checks_passed": runner_validation.get("checks_passed"),
                "checks_total": runner_validation.get("checks_total"),
            },
            "manifest_generator_validation": {
                "status": manifest_validation.get("status"),
                "checks_passed": manifest_validation.get("checks_passed"),
                "checks_total": manifest_validation.get("checks_total"),
            },
            "frozen_calendar": frozen_calendar,
            "historical_edge": "NOT_EVALUATED_LICENSED_DATA_REQUIRED",
            "prospective_profitability": "NOT_MATURED",
            "live_decision_weight": 0.0,
            "capital_permission": "BLOCKED",
        },
        "claim_ceiling": "Unsigned options topology is descriptive. Verified C1 signed-dealer reconstruction, complete one-minute surface marking with Calcs plus Open Interest, deterministic source/derived manifest generation, licensed-package preflight, one-time lockbox opening, and the frozen historical evaluator are implemented and tested, but licensed historical outcomes have not been opened and V71 has zero prospective observations. No standalone direction, calibrated pin/break probability, gamma-scalping profit, or capital claim is permitted.",
        "live_decision_weight": 0.0,
        "predictive_components_promoted": 0,
        "capital_permission": "BLOCKED",
    }


def attach_options_research_v55(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    out = deepcopy(desk)
    out["options_research_v55"] = load_options_research_v55()
    return out
