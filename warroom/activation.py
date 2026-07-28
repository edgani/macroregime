"""warroom/activation.py — thesis activation clock (R6 §2.3).

Assigns every bottleneck thesis one of:
  RED_NOT_READY / YELLOW_ARMING / GREEN_ACTIVATE /
  GREEN_ACTIVE_HOLD_ADD / AMBER_LATE_TRIM / BLACK_INVALIDATED_EXIT

Rules:
- Activation inputs come ONLY from the market contract's activation_inputs list.
  RSI/MACD/SMA/EMA/VWAP/chart-pattern/momentum/breakout are hard-blocked.
- An input counts as ACTIVE only if an admitted PIT feed exists for it.
  Missing inputs are listed explicitly (fail-closed for trading, open for research).
- GREEN requires: admitted activation evidence + fresh quote + value bridge +
  risk plan. Without admitted fundamental feeds the honest state is RED/YELLOW.
"""
from __future__ import annotations

import json
from pathlib import Path

from warroom.market_contracts import CONTRACTS, FORBIDDEN_ACTIVATION_INPUTS

SCHEMA = "warroom.activation_board.v1"

# activation input -> admitted feed availability (R5 data plane status)
# True only where a real admitted feed exists today; gaps stay False.
INPUT_FEED_STATUS = {
    # shared/price-adjacent (context only, never alpha by themselves)
    "catalyst_proximity": True,            # calendar-driven from chain horizons
    # US fundamentals — gated
    "backlog_acceleration": False, "inventory_depletion": False,
    "capacity_utilization": False, "qualification_design_wins": False,
    "lead_time_changes": False, "asp_cost_spread": False, "signed_contracts": False,
    "customer_mix": False, "guidance_vs_consensus": False, "estimate_revisions": False,
    "capex_response": False, "regulatory_permit": False,
    "institutional_borrow_options_confirmation": False,
    # IHSG — gated on licensed broker/flow data
    "controller_action": False, "free_float_change": False, "corporate_action": False,
    "crossing_adjusted_broker_inventory": False, "broker_persistence": False,
    "foreign_flow": False, "done_detail_volume": False, "institutional_vs_retail": False,
    "import_cost": False, "commodity_pass_through": False, "government_policy": False,
    "project_contract_award": False, "issuer_disclosure": False, "liquidity_impact": False,
    # Crypto — gated on on-chain/venue data
    "protocol_activity": False, "fee_revenue": False, "token_required_usage": False,
    "stablecoin_liquidity": False, "unlock_emission_schedule": False,
    "treasury_entity_flow": False, "exchange_reserves": False,
    "venue_funding_basis_oi": False, "liquidations": False,
    "governance_upgrade_milestone": False, "protocol_resource_bottleneck": False,
    "adoption_vs_valuation_gap": False,
    # Commodities — gated on EIA/USDA/LME/CFTC wiring
    "inventory_surprise": False, "stock_flow_balance": False, "spare_capacity": False,
    "grade_location_basis": False, "freight": False, "storage": False,
    "processing_refinery": False, "weather_geopolitical": False,
    "production_response": False, "futures_curve": False,
    "producer_consumer_hedging": False, "cftc_positioning": False,
    "contract_expiry_liquidity": True,   # contract calendar is known statically
    # FX — partial (carry computable from FRED rates; rest gated)
    "relative_growth_inflation": True,   # FRED CPI/GDP admitted
    "policy_differential": True,         # FRED policy rates admitted
    "carry": True,                       # computable from FRED rate differentials
    "dollar_liquidity": True,            # FRED plumbing admitted
    "expected_policy_path": False, "bop_current_account": False, "reserves": False,
    "intervention": False, "fiscal_credibility": False, "cross_currency_basis": False,
    "cftc_tff_cot": False, "options": False, "funding_stress": False,
    "external_vulnerability": False,
}


def evaluate_thesis(record: dict) -> dict:
    """Traffic light for one bottleneck record. Fail-closed, explicit reasons."""
    market = record.get("market", "us")
    contract = CONTRACTS.get(market)
    if contract is None:
        return {"bottleneck_id": record.get("bottleneck_id"), "state": "RED_NOT_READY",
                "reason": f"no market contract for {market}"}

    inputs = contract["activation_inputs"]
    all_tokens = {t for inp in inputs for t in inp.lower().split("_")}
    for banned in FORBIDDEN_ACTIVATION_INPUTS:
        assert banned.lower() not in all_tokens, f"forbidden input token leaked: {banned}"

    active = [i for i in inputs if INPUT_FEED_STATUS.get(i, False)]
    missing = [i for i in inputs if not INPUT_FEED_STATUS.get(i, False)]
    stage = (record.get("current_stage") or "").upper()

    if stage in {"DECAYED", "INVALIDATED", "COMPLETE"}:
        state, reason = "BLACK_INVALIDATED_EXIT", "chain marked decayed/complete in registry"
    elif len(active) == 0:
        state = "RED_NOT_READY"
        reason = "no admitted activation feeds; all candidate inputs gated"
    elif len(active) <= 2:
        state = "YELLOW_ARMING"
        reason = f"partial activation context ({', '.join(active)}); fundamental confirmation gated"
    else:
        state = "YELLOW_ARMING"
        reason = f"context inputs active ({len(active)}); GREEN requires value bridge + risk plan + fresh quote"

    return {
        "bottleneck_id": record.get("bottleneck_id"),
        "market": market,
        "state": state,
        "reason": reason,
        "active_inputs": active,
        "missing_inputs": missing,
        "instruments": record.get("affected_instruments", []),
        "invalidation": record.get("invalidation"),
        "proof_status": record.get("proof_status", "MAPPED"),
        "claim_limit": contract["claim_limit"],
        "schema": SCHEMA,
    }


def build_board(registry_path: Path) -> dict:
    records = [json.loads(l) for l in registry_path.read_text(encoding="utf-8").strip().splitlines()]
    board = [evaluate_thesis(r) for r in records]
    counts = {}
    for b in board:
        counts[b["state"]] = counts.get(b["state"], 0) + 1
    return {"schema": SCHEMA, "states": counts, "board": board}
