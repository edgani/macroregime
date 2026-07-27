"""Strict all-market narrative, bottleneck and projection research kernel for War Room OS V9.7."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from research_evidence_v83 import attach_research_evidence_v83
from research_evidence_v84 import attach_research_evidence_v84
from research_evidence_v85 import attach_research_evidence_v85
from research_evidence_v86 import attach_research_evidence_v86
from research_evidence_v87 import attach_research_evidence_v87
from research_evidence_v88 import attach_research_evidence_v88
from proof_registry_v97 import attach_proof_registry

MARKET_CAUSAL_SEQUENCE = {
    "us": ["economic origin", "filing fundamentals", "expectations gap", "capacity/qualification bottleneck", "beneficiary value capture", "activation clock", "equity price bridge", "positioning amplification", "cost/capacity"],
    "idx": ["economic/sector origin", "fundamentals", "controller/free float", "broker/foreign inventory", "bottleneck value capture", "activation clock", "equity price bridge", "cost/capacity"],
    "commodity": ["stock-flow origin", "inventory surprise", "physical bottleneck", "grade/location/freight transmission", "activation clock", "scarcity price bridge", "positioning amplification", "cost/roll"],
    "fx": ["relative macro origin", "policy/BOP transmission", "funding/reserve bottleneck", "expectations gap", "activation clock", "external-balance rate bridge", "positioning/intervention", "cost/capacity"],
    "crypto": ["protocol origin", "token-required bottleneck", "stablecoin/unlocks", "venue/on-chain transmission", "expectations gap", "activation clock", "value-capture token bridge", "leverage amplification", "cost/counterparty"],
}

MARKET_PROJECTION_METHODS = {
    "us": ["equity_earnings_bridge", "equity_sales_bridge", "equity_fcf_bridge"],
    "idx": ["equity_earnings_bridge", "equity_sales_bridge", "equity_fcf_bridge"],
    "commodity": ["commodity_scarcity_bridge"],
    "fx": ["fx_external_balance_bridge"],
    "crypto": ["crypto_value_capture_bridge"],
}


def _market_kernel(market_id: str, row: Mapping[str, Any]) -> dict[str, Any]:
    evidence = row.get("evidence_domains") if isinstance(row.get("evidence_domains"), Mapping) else {}
    ready = [name for name, item in evidence.items() if isinstance(item, Mapping) and item.get("point_in_time_eligible")]
    missing = [name for name, item in evidence.items() if not (isinstance(item, Mapping) and item.get("point_in_time_eligible"))]
    return {
        "market": market_id,
        "causal_sequence": MARKET_CAUSAL_SEQUENCE.get(market_id, []),
        "projection_methods": MARKET_PROJECTION_METHODS.get(market_id, []),
        "observed_evidence": evidence,
        "point_in_time_ready_domains": ready,
        "missing_domains": missing,
        "projection": {
            "status": "NO_PROVEN_PROJECTION",
            "low_target": None,
            "base_target": None,
            "high_target": None,
            "expected_target": None,
            "scenario_probabilities": None,
            "horizon": None,
            "bottleneck_reason": None,
            "value_capture_bridge": None,
            "invalidation": None,
            "claim": "The calculator exists, but targets are withheld from capital until the exact-scope point-in-time model passes every frozen gate.",
        },
        "execution": {
            "capital_permission": "BLOCKED",
            "instrument": None,
            "direction": None,
            "allocation": 0.0,
            "reason": "No valid signed market-specific proof receipt is loaded.",
        },
        "validation": {
            "status": "DATA_AND_PROOF_INCOMPLETE",
            "required": [
                "point-in-time lineage", "pre-registered market-specific value bridge",
                "blind narrative timing benchmark", "blind target calibration benchmark",
                "purged walk-forward and untouched lockbox", "PBO/DSR/familywise correction",
                "actual fills and costs", "real profit factor and drawdown",
                "mature prospective forecasts", "signed limited-production approval",
            ],
        },
    }


def attach_research_kernel(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    out = deepcopy(desk)
    markets = out.get("markets") if isinstance(out.get("markets"), Mapping) else {}
    kernels = {str(mid): _market_kernel(str(mid), row if isinstance(row, Mapping) else {}) for mid, row in markets.items()}
    out["research_kernel"] = {
        "version": "9.7",
        "mode": "ALL_MARKET_NONTECHNICAL_BOTTLENECK_PRICE_PROJECTION_WITH_LIMITED_PRODUCTION_CONTROL",
        "markets": kernels,
        "global_permission": "CAPITAL_BLOCKED",
        "decision_domains": [
            "economics", "fundamentals", "expectations", "liquidity", "credit",
            "positioning", "signed flow", "physical markets", "bottlenecks", "valuation",
            "causal transmission", "market-specific microstructure",
        ],
        "price_roles": ["valuation denominator", "current execution reference", "future outcome measurement", "risk measurement", "post-prediction invalidation"],
        "claim": "Every target must be explained by a market-specific causal value bridge. No chart-derived feature is consumed.",
    }
    out["proof_status"] = {
        "final_trading_system": False,
        "all_market_trading_ready": False,
        "capital_permission": "BLOCKED",
        "decision_active_predictive_components": 0,
        "reason": "V9.7 can prepare broker-neutral limited-production orders only for an exact market with a valid bound proof run, fresh quote, passing risk limits and human HMAC approval.",
        "operational_permission": "LIMITED_PRODUCTION_CONTROL_PLANE_READY",
    }
    out = attach_proof_registry(out)
    out = attach_research_evidence_v83(out)
    out = attach_research_evidence_v84(out)
    out = attach_research_evidence_v85(out)
    out = attach_research_evidence_v86(out)
    out = attach_research_evidence_v87(out)
    return attach_research_evidence_v88(out)
