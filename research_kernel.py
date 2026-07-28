"""War Room OS V9.9 market-specific causal research map.

The kernel defines what each market must explain. Ticker-level projections and execution live in the
unified decision packets, not in separate global tabs.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Mapping
from proof_registry_v99 import attach_proof_registry
from decision_packet_v99 import MARKET_CAUSAL_SEQUENCE, PROJECTION_METHODS


def attach_research_kernel(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    out = deepcopy(desk)
    markets = out.get("markets") if isinstance(out.get("markets"), Mapping) else {}
    kernels = {}
    for market, row in markets.items():
        evidence = row.get("evidence_domains") if isinstance(row, Mapping) and isinstance(row.get("evidence_domains"), Mapping) else {}
        kernels[str(market)] = {
            "market": str(market),
            "causal_sequence": MARKET_CAUSAL_SEQUENCE.get(str(market), []),
            "projection_methods": PROJECTION_METHODS.get(str(market), []),
            "observed_domains": [name for name, item in evidence.items() if isinstance(item, Mapping) and item.get("state") not in {"NO_DATA", "ROUTE_ONLY"}],
            "point_in_time_ready_domains": [name for name, item in evidence.items() if isinstance(item, Mapping) and item.get("point_in_time_eligible") is True],
            "claim_limit": "Mapping specifies what must be explained; it is not a recommendation or a fitted formula.",
        }
    out["research_kernel"] = {
        "version": "9.9",
        "mode": "ACTUAL_BUNDLED_DATA_WITH_MARKET_SPECIFIC_UNIFIED_TICKER_PACKETS",
        "markets": kernels,
        "global_permission": "CAPITAL_BLOCKED",
        "decision_domains": ["economics", "fundamentals", "expectations", "liquidity", "credit", "positioning", "signed flow", "physical markets", "bottlenecks", "valuation", "causal transmission", "market-specific microstructure"],
        "price_roles": ["valuation denominator", "current execution reference", "future outcome measurement", "risk measurement", "post-prediction invalidation"],
        "claim": "Projection, flow, causal thesis, risk, execution and proof are attached to the same ticker packet. No chart-derived feature is consumed.",
    }
    out = attach_proof_registry(out)
    out["proof_status"].update({
        "final_trading_system": False,
        "all_market_trading_ready": False,
        "reason": "Bundled research context and current execution context are displayed independently. Capital remains blocked until exact proof, a valid ticker value bridge, fresh quote, risk checks and human approval all pass.",
    })
    return out
