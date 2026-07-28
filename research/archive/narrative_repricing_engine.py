"""War Room OS V8.7 narrative-to-repricing state engine.

The engine does not infer direction from charts or price history. It converts point-in-time,
nontechnical evidence into a falsifiable causal state. Current market capitalization is used only
as a valuation denominator; it is not a price-derived signal.

Important: this module is a deterministic research classifier. It does not grant capital.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, asdict
from typing import Any, Mapping

from warroom.no_technical_policy import validate_feature_names

HEX64 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_MARKETS = {"us", "idx", "commodity", "fx", "crypto"}
ALLOWED_FEATURE_DOMAINS = {
    "economics", "fundamentals", "expectations", "liquidity", "credit", "valuation",
    "positioning", "signed_flow", "physical_market", "bottleneck", "causal_transmission",
    "corporate_actions", "market_structure", "supply_chain", "customer_qualification",
    "protocol_value_capture", "controller_free_float", "broker_inventory", "policy",
    "balance_of_payments", "inventory", "capacity", "orders_backlog", "guidance",
    "analyst_estimates", "unit_economics", "customer_concentration", "regulatory",
}
REQUIRED_HASHES = (
    "feature_snapshot_hash", "evidence_lineage_hash", "universe_snapshot_hash",
    "model_hash", "trial_ledger_hash",
)
REQUIRED_BOOLEANS = (
    "origin_confirmed", "transmission_confirmed", "bottleneck_confirmed",
    "beneficiary_identified", "monetization_started", "expectations_gap_open",
    "supply_response_lagged", "catalyst_within_horizon", "amplification_present",
    "invalidation_triggered", "alternative_explanations_tested",
    "negative_control_peers_passed",
)
REQUIRED_COUNTS = (
    "origin_evidence_count", "transmission_evidence_count", "bottleneck_evidence_count",
    "value_capture_evidence_count", "expectations_evidence_count", "catalyst_evidence_count",
    "positioning_evidence_count",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")


def _parse_ts(value: Any):
    import pandas as pd
    return pd.to_datetime(value, utc=True, errors="coerce")


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _domains(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        raw = value
    else:
        raw = str(value or "").replace("|", ",").split(",")
    return sorted({str(x).strip().lower() for x in raw if str(x).strip()})


@dataclass(frozen=True)
class NarrativeState:
    valid: bool
    state: str
    causal_chain_complete: bool
    timing_ready: bool
    valuation_gap_low: float | None
    valuation_gap_base: float | None
    valuation_gap_high: float | None
    amplification_overlay: str
    capital_permission: str
    reasons: tuple[str, ...]
    state_hash: str


def validate_narrative(row: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required_text = (
        "narrative_id", "strategy_id", "as_of", "market", "security_id", "ticker",
        "decision_purpose", "causal_claim", "bottleneck_type", "value_capture_path",
        "invalidation_rule", "feature_domains", "availability_max",
    )
    for field in required_text:
        if not str(row.get(field) or "").strip():
            errors.append(f"missing {field}")

    market = str(row.get("market") or "").strip().lower()
    if market not in ALLOWED_MARKETS:
        errors.append("unsupported market")

    as_of = _parse_ts(row.get("as_of"))
    available = _parse_ts(row.get("availability_max"))
    if getattr(as_of, "tzinfo", None) is None or str(as_of) == "NaT":
        errors.append("invalid as_of")
    if getattr(available, "tzinfo", None) is None or str(available) == "NaT":
        errors.append("invalid availability_max")
    if not errors and available > as_of:
        errors.append("future information: availability_max exceeds as_of")

    try:
        horizon = int(row.get("decision_horizon_days"))
        if horizon <= 0:
            errors.append("decision_horizon_days must be positive")
    except Exception:
        errors.append("invalid decision_horizon_days")

    for field in REQUIRED_HASHES:
        if not HEX64.fullmatch(str(row.get(field) or "")):
            errors.append(f"invalid {field}")

    parsed_bools: dict[str, bool] = {}
    for field in REQUIRED_BOOLEANS:
        value = _as_bool(row.get(field))
        if value is None:
            errors.append(f"invalid boolean {field}")
        else:
            parsed_bools[field] = value

    for field in REQUIRED_COUNTS:
        try:
            count = int(row.get(field))
            if count < 0:
                errors.append(f"negative {field}")
        except Exception:
            errors.append(f"invalid {field}")

    numeric_fields = ("current_market_cap", "scenario_market_cap_low", "scenario_market_cap_base", "scenario_market_cap_high")
    nums: dict[str, float] = {}
    for field in numeric_fields:
        try:
            value = float(row.get(field))
            if not math.isfinite(value) or value <= 0:
                errors.append(f"invalid {field}")
            nums[field] = value
        except Exception:
            errors.append(f"invalid {field}")
    if len(nums) == 4 and not (nums["scenario_market_cap_low"] <= nums["scenario_market_cap_base"] <= nums["scenario_market_cap_high"]):
        errors.append("scenario market caps must be ordered low <= base <= high")

    domains = _domains(row.get("feature_domains"))
    if not domains:
        errors.append("feature_domains empty")
    if validate_feature_names(domains):
        errors.append("technical or price-derived predictor domain prohibited")
    unknown = sorted(set(domains) - ALLOWED_FEATURE_DOMAINS)
    if unknown:
        errors.append("unknown feature domains: " + ",".join(unknown))

    if parsed_bools.get("bottleneck_confirmed") and not parsed_bools.get("transmission_confirmed"):
        errors.append("bottleneck cannot be confirmed without transmission evidence")
    if parsed_bools.get("beneficiary_identified") and not str(row.get("value_capture_path") or "").strip():
        errors.append("beneficiary requires value_capture_path")

    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "domains": domains,
        "parsed_booleans": parsed_bools,
        "schema": "warroom.v87.narrative_validation.v1",
    }


def classify_narrative(row: Mapping[str, Any]) -> NarrativeState:
    validation = validate_narrative(row)
    if not validation["valid"]:
        payload = {"state": "INVALID_INPUT", "errors": validation["errors"]}
        return NarrativeState(
            valid=False, state="INVALID_INPUT", causal_chain_complete=False, timing_ready=False,
            valuation_gap_low=None, valuation_gap_base=None, valuation_gap_high=None,
            amplification_overlay="UNKNOWN", capital_permission="BLOCKED",
            reasons=tuple(validation["errors"]), state_hash=hashlib.sha256(_canonical(payload)).hexdigest(),
        )

    b = validation["parsed_booleans"]
    counts = {field: int(row[field]) for field in REQUIRED_COUNTS}
    causal_chain_complete = all([
        b["origin_confirmed"], b["transmission_confirmed"], b["bottleneck_confirmed"],
        b["beneficiary_identified"], counts["origin_evidence_count"] > 0,
        counts["transmission_evidence_count"] > 0, counts["bottleneck_evidence_count"] > 0,
        counts["value_capture_evidence_count"] > 0,
    ])
    timing_ready = all([
        causal_chain_complete,
        b["expectations_gap_open"],
        b["supply_response_lagged"],
        b["alternative_explanations_tested"],
        b["negative_control_peers_passed"],
        (b["monetization_started"] or b["catalyst_within_horizon"]),
        not b["invalidation_triggered"],
        counts["expectations_evidence_count"] > 0,
        (counts["catalyst_evidence_count"] > 0 or counts["value_capture_evidence_count"] > 1),
    ])

    current = float(row["current_market_cap"])
    low = float(row["scenario_market_cap_low"]) / current - 1.0
    base = float(row["scenario_market_cap_base"]) / current - 1.0
    high = float(row["scenario_market_cap_high"]) / current - 1.0

    reasons: list[str] = []
    if b["invalidation_triggered"]:
        state = "INVALIDATED"
        reasons.append("pre-registered invalidation triggered")
    elif not causal_chain_complete:
        state = "INCOMPLETE_CAUSAL_CHAIN"
        reasons.append("origin → transmission → bottleneck → beneficiary path incomplete")
    elif not b["expectations_gap_open"]:
        state = "RECOGNIZED_OR_LATE"
        reasons.append("expectation gap is no longer open")
    elif not b["monetization_started"] and not b["catalyst_within_horizon"]:
        state = "STRUCTURAL_DORMANT"
        reasons.append("bottleneck exists but no monetization or dated activation evidence yet")
    elif not b["supply_response_lagged"]:
        state = "SUPPLY_RESPONSE_CAN_CLOSE_GAP"
        reasons.append("supply response may arrive within the decision horizon")
    elif not (b["alternative_explanations_tested"] and b["negative_control_peers_passed"]):
        state = "NARRATIVE_NOT_FALSIFIED"
        reasons.append("alternative explanations or matched negative-control peers not cleared")
    elif timing_ready and low > 0:
        state = "REPRICING_READY_RESEARCH_CANDIDATE"
        reasons.append("causal chain, monetization/catalyst timing, open expectations gap, and conservative valuation gap align")
    elif timing_ready:
        state = "ACTIVATION_WITHOUT_CONSERVATIVE_VALUATION_MARGIN"
        reasons.append("activation evidence exists but low scenario does not exceed current valuation")
    else:
        state = "EVIDENCE_BUILDING"
        reasons.append("causal thesis exists but activation conditions are not all present")

    amplification = "AMPLIFIED" if b["amplification_present"] and counts["positioning_evidence_count"] > 0 else "UNAMPLIFIED"
    payload = {
        "narrative_id": row["narrative_id"], "as_of": str(row["as_of"]), "state": state,
        "causal_chain_complete": causal_chain_complete, "timing_ready": timing_ready,
        "valuation_gap_low": low, "valuation_gap_base": base, "valuation_gap_high": high,
        "amplification": amplification, "reasons": reasons,
    }
    return NarrativeState(
        valid=True, state=state, causal_chain_complete=causal_chain_complete, timing_ready=timing_ready,
        valuation_gap_low=low, valuation_gap_base=base, valuation_gap_high=high,
        amplification_overlay=amplification, capital_permission="BLOCKED",
        reasons=tuple(reasons), state_hash=hashlib.sha256(_canonical(payload)).hexdigest(),
    )


def classify_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    return asdict(classify_narrative(row)) | {
        "schema": "warroom.v87.narrative_state.v1",
        "claim_limit": "Research-state classification only. Capital requires blind incremental timing proof, real costs, drawdown, profit factor, and prospective approval.",
    }
