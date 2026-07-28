"""Unified market/ticker decision packet for War Room OS V9.8.

Every ticker owns its causal thesis, value bridge, flow/positioning state, projection, risk,
execution and proof. No packet can imply a trade merely because a quote or public dataset exists.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Mapping

from market_projection_engine import project_payload

HERE = Path(__file__).resolve().parent
UTC = dt.timezone.utc
MARKETS = ("us", "idx", "crypto", "commodity", "fx")

MARKET_LABELS = {"us": "US Stocks", "idx": "IHSG", "crypto": "Crypto", "commodity": "Commodities", "fx": "FX"}
MARKET_CAUSAL_SEQUENCE = {
    "us": ["economic origin", "filing fundamentals", "expectations gap", "capacity / qualification bottleneck", "beneficiary value capture", "activation clock", "equity value bridge", "positioning amplification", "invalidation"],
    "idx": ["economic / sector origin", "issuer fundamentals", "controller / free float", "broker and foreign inventory", "bottleneck value capture", "activation clock", "equity value bridge", "liquidity / capacity", "invalidation"],
    "commodity": ["stock-flow origin", "inventory surprise", "physical bottleneck", "grade / location / freight transmission", "activation clock", "scarcity value bridge", "positioning amplification", "roll / capacity", "invalidation"],
    "fx": ["relative macro origin", "policy / balance-of-payments transmission", "funding / reserve bottleneck", "expectations gap", "activation clock", "external-balance value bridge", "positioning / intervention", "cost / capacity", "invalidation"],
    "crypto": ["protocol origin", "token-required bottleneck", "stablecoin / unlocks", "venue and on-chain transmission", "expectations gap", "activation clock", "token value-capture bridge", "leverage / counterparty", "invalidation"],
}
PROJECTION_METHODS = {
    "us": ["equity_earnings_bridge", "equity_sales_bridge", "equity_fcf_bridge"],
    "idx": ["equity_earnings_bridge", "equity_sales_bridge", "equity_fcf_bridge"],
    "commodity": ["commodity_scarcity_bridge"],
    "fx": ["fx_external_balance_bridge"],
    "crypto": ["crypto_value_capture_bridge"],
}
FLOW_KEYS = {
    "us": ("positioning_amplification", "cost_capacity"),
    "idx": ("controller_free_float", "broker_inventory", "foreign_flow", "cost_capacity"),
    "commodity": ("inventory_surprise", "positioning_amplification", "cost_capacity"),
    "fx": ("positioning_amplification", "carry_funding", "cost_capacity"),
    "crypto": ("stablecoin_and_unlocks", "venue_transmission", "positioning_amplification", "cost_capacity"),
}


def _parse_time(value: Any) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(UTC)
    except Exception:
        return None


def _quote_status(record: Mapping[str, Any] | None, market: str) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        return {"state": "NO_QUOTE", "reference_available": False, "execution_fresh": False, "reason": "No current execution-reference record is loaded."}
    received = _parse_time(record.get("received_at"))
    provider = _parse_time(record.get("provider_timestamp"))
    now = dt.datetime.now(UTC)
    receive_age = (now - received).total_seconds() if received else None
    provider_age = (now - provider).total_seconds() if provider else None
    receive_limit = 900 if market == "crypto" else 4 * 3600
    provider_limit = 900 if market == "crypto" else 36 * 3600
    validation = str(record.get("validation") or "")
    reference_available = validation in {"VALID_EXECUTION_REFERENCE", "CONTEXT_REFERENCE_ONLY", "STALE_LAST_KNOWN_REFERENCE"} and float(record.get("price") or 0) > 0
    fresh = bool(validation == "VALID_EXECUTION_REFERENCE" and reference_available and receive_age is not None and provider_age is not None and receive_age <= receive_limit and provider_age <= provider_limit)
    return {
        "state": "EXECUTION_FRESH" if fresh else "REFERENCE_AVAILABLE_NOT_EXECUTION_FRESH" if reference_available else "INVALID_QUOTE",
        "reference_available": reference_available,
        "execution_fresh": fresh,
        "receive_age_seconds": round(receive_age, 1) if receive_age is not None else None,
        "provider_age_seconds": round(provider_age, 1) if provider_age is not None else None,
        "reason": "Freshness is an execution gate only; quote direction is never an alpha input.",
    }


def _component_for_market(registry: Mapping[str, Any], market: str) -> dict[str, Any]:
    for _, row in (registry.get("components") or {}).items():
        if isinstance(row, Mapping) and str(row.get("market") or "").lower() == market:
            return dict(row)
    return {}


def _projection_from_request(market: str, ticker: str) -> dict[str, Any] | None:
    path = HERE / "runtime" / "v98_decisions" / market / f"{ticker}.json"
    if not path.is_file():
        return None
    try:
        request = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(request, dict):
            return {"valid": False, "projection_status": "INVALID_INPUT", "errors": ["projection request root must be an object"], "capital_permission": "BLOCKED"}
        result = project_payload(request)
        if result.get("valid") is True and (str(result.get("market") or "").lower() != market or str(result.get("ticker") or "") != ticker):
            return {"valid": False, "projection_status": "SCOPE_MISMATCH", "errors": ["projection market/ticker does not match packet path"], "capital_permission": "BLOCKED"}
        return result
    except Exception as exc:
        return {"valid": False, "projection_status": "INVALID_INPUT", "errors": [f"{type(exc).__name__}: {exc}"], "capital_permission": "BLOCKED"}


def _projection_blocked(market: str, price: float | None, proof: Mapping[str, Any]) -> dict[str, Any]:
    reason = "No pre-registered ticker value-bridge request is installed."
    if not proof.get("proof_run_valid"):
        reason += " Exact-market proof is also missing."
    return {
        "valid": False,
        "projection_status": "WITHHELD_NO_TICKER_VALUE_BRIDGE",
        "current_price": price,
        "target_low": None,
        "target_base": None,
        "target_high": None,
        "expected_target_price": None,
        "expected_return": None,
        "horizon_days": None,
        "methods_allowed": PROJECTION_METHODS.get(market, []),
        "reason": reason,
        "capital_permission": "BLOCKED",
    }


def _evidence_summary(evidence: Mapping[str, Any]) -> dict[str, Any]:
    observed = 0
    pit = 0
    rows: list[dict[str, Any]] = []
    for name, item in evidence.items():
        row = dict(item) if isinstance(item, Mapping) else {}
        state = str(row.get("state") or "NO_DATA")
        if state not in {"NO_DATA", "ROUTE_ONLY"}:
            observed += 1
        if row.get("point_in_time_eligible") is True:
            pit += 1
        rows.append({"domain": name, **row})
    return {"observed_domains": observed, "pit_ready_domains": pit, "total_domains": len(rows), "rows": rows}


def build_packets(*, markets: Mapping[str, Any], quotes: Mapping[str, Any], universe: Mapping[str, Any], proof_registry: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    by_market: dict[str, dict[str, Any]] = {m: {} for m in MARKETS}
    all_packets: list[dict[str, Any]] = []
    quote_markets = quotes.get("markets") if isinstance(quotes.get("markets"), Mapping) else {}
    for market in MARKETS:
        market_row = markets.get(market) if isinstance(markets.get(market), Mapping) else {}
        evidence = market_row.get("evidence_domains") if isinstance(market_row.get("evidence_domains"), Mapping) else {}
        evidence_summary = _evidence_summary(evidence)
        proof = _component_for_market(proof_registry, market)
        rows = universe.get(market) if isinstance(universe.get(market), list) else []
        market_quotes = quote_markets.get(market) if isinstance(quote_markets.get(market), Mapping) else {}
        for item in rows:
            ticker = str(item.get("instrument") or "").strip()
            if not ticker:
                continue
            quote = dict(market_quotes.get(ticker)) if isinstance(market_quotes.get(ticker), Mapping) else None
            quote_state = _quote_status(quote, market)
            price = float(quote.get("price")) if quote and quote_state["reference_available"] else None
            projection = _projection_from_request(market, ticker) or _projection_blocked(market, price, proof)
            projection_valid = projection.get("valid") is True
            proof_valid = proof.get("proof_run_valid") is True
            execution_fresh = quote_state["execution_fresh"] is True
            permitted = bool(projection_valid and proof_valid and execution_fresh and projection.get("capital_permission") == "LIMITED_PRODUCTION_ELIGIBLE")
            flow = [{"domain": key, **(dict(evidence.get(key)) if isinstance(evidence.get(key), Mapping) else {"state": "NO_DATA"})} for key in FLOW_KEYS.get(market, ())]
            causal = []
            evidence_items = list(evidence.items())
            for index, step in enumerate(MARKET_CAUSAL_SEQUENCE.get(market, [])):
                linked = evidence_items[index] if index < len(evidence_items) else (None, None)
                linked_row = linked[1] if isinstance(linked[1], Mapping) else {}
                causal.append({"step": index + 1, "name": step, "evidence_domain": linked[0], "state": linked_row.get("state", "UNMAPPED"), "source": linked_row.get("source"), "note": linked_row.get("note")})
            blockers = []
            if not quote_state["reference_available"]:
                blockers.append("CURRENT_QUOTE_MISSING")
            elif not execution_fresh:
                blockers.append("QUOTE_NOT_EXECUTION_FRESH")
            if not proof_valid:
                blockers.append("EXACT_MARKET_PROOF_MISSING")
            if not projection_valid:
                blockers.append("TICKER_VALUE_BRIDGE_MISSING_OR_INVALID")
            if evidence_summary["pit_ready_domains"] == 0:
                blockers.append("POINT_IN_TIME_EVIDENCE_INCOMPLETE")
            packet = {
                "schema": "warroom.v98.ticker_decision_packet.v1",
                "market": market,
                "market_label": MARKET_LABELS[market],
                "ticker": ticker,
                "asset_type": item.get("asset_type"),
                "provider": item.get("provider"),
                "provider_symbol": item.get("provider_symbol"),
                "decision": {
                    "state": "LIMITED_PRODUCTION_ELIGIBLE" if permitted else "NO_TRADE",
                    "direction": projection.get("direction") if permitted else None,
                    "conviction": projection.get("calibrated_probability") if permitted else None,
                    "horizon_days": projection.get("horizon_days"),
                    "capital_permission": "LIMITED_PRODUCTION_ELIGIBLE" if permitted else "BLOCKED",
                    "blockers": blockers,
                    "why_included": "Instrument is in the explicit execution-reference universe. Inclusion is not a recommendation.",
                },
                "quote": {**(quote or {}), **quote_state},
                "causal_chain": causal,
                "fundamental_value_capture": {
                    "state": "READY" if projection_valid else "NOT_INSTALLED",
                    "methods_allowed": PROJECTION_METHODS.get(market, []),
                    "projection_reason": projection.get("projection_reason"),
                    "beneficiary_value_capture": projection.get("beneficiary_value_capture"),
                    "bottleneck_claim": projection.get("bottleneck_claim"),
                },
                "flow_positioning": flow,
                "projection": projection,
                "risk_execution": {
                    "entry": None,
                    "stop": None,
                    "target": projection.get("expected_target_price"),
                    "expected_shortfall": None,
                    "position_size": 0.0,
                    "order_state": "AWAITING_APPROVED_PACKET" if permitted else "BLOCKED",
                    "manual_export_only": True,
                },
                "proof_data": {
                    "market_proof_valid": proof_valid,
                    "market_proof_state": proof.get("state", "AWAITING_BOUND_PROOF"),
                    "market_proof_reasons": proof.get("proof_run_reasons", []),
                    "evidence": evidence_summary,
                },
            }
            by_market[market][ticker] = packet
            all_packets.append(packet)

    watchlist = sorted(
        all_packets,
        key=lambda p: (
            p["decision"]["state"] == "LIMITED_PRODUCTION_ELIGIBLE",
            p["proof_data"]["evidence"]["pit_ready_domains"],
            p["proof_data"]["evidence"]["observed_domains"],
            p["quote"].get("reference_available") is True,
        ),
        reverse=True,
    )
    alpha_center = {
        "schema": "warroom.v98.alpha_center.v1",
        "promoted": [p for p in watchlist if p["decision"]["state"] == "LIMITED_PRODUCTION_ELIGIBLE"],
        "research_watchlist": watchlist,
        "state": "PROMOTED_ALPHA_AVAILABLE" if any(p["decision"]["state"] == "LIMITED_PRODUCTION_ELIGIBLE" for p in watchlist) else "NO_PROMOTED_ALPHA",
        "ranking_basis": "Coverage/readiness only; never price performance or chart-derived ranking.",
    }
    return by_market, alpha_center
