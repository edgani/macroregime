"""Unified market/ticker decision packet for War Room OS V9.9.

V9.9 fixes the main V9.8 classification bug: real bundled research data is displayed even when live
capital remains blocked.  Research availability, quote freshness, proof and capital permission are
four separate states.  No price-derived feature is consumed as a directional predictor.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Mapping

from market_projection_engine import project_payload
from bundled_research_reader_v99 import ticker_context

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
        return {"state": "NO_CURRENT_QUOTE", "reference_available": False, "execution_fresh": False, "reason": "No current execution-reference record is loaded."}
    received = _parse_time(record.get("received_at")); provider = _parse_time(record.get("provider_timestamp")); now = dt.datetime.now(UTC)
    receive_age = (now - received).total_seconds() if received else None
    provider_age = (now - provider).total_seconds() if provider else None
    receive_limit = 900 if market == "crypto" else 4 * 3600
    provider_limit = 900 if market == "crypto" else 36 * 3600
    validation = str(record.get("validation") or "")
    reference_available = validation in {"VALID_EXECUTION_REFERENCE", "CONTEXT_REFERENCE_ONLY", "STALE_LAST_KNOWN_REFERENCE"} and float(record.get("price") or 0) > 0
    fresh = bool(validation == "VALID_EXECUTION_REFERENCE" and reference_available and receive_age is not None and provider_age is not None and receive_age <= receive_limit and provider_age <= provider_limit)
    return {
        "state": "EXECUTION_FRESH" if fresh else "CURRENT_REFERENCE_STALE" if reference_available else "INVALID_CURRENT_QUOTE",
        "reference_available": reference_available,
        "execution_fresh": fresh,
        "receive_age_seconds": round(receive_age, 1) if receive_age is not None else None,
        "provider_age_seconds": round(provider_age, 1) if provider_age is not None else None,
        "reason": "Quote freshness is an execution gate only; quote direction is never an alpha input.",
    }


def _component_for_market(registry: Mapping[str, Any], market: str) -> dict[str, Any]:
    for row in (registry.get("components") or {}).values():
        if isinstance(row, Mapping) and str(row.get("market") or "").lower() == market:
            return dict(row)
    return {}


def _projection_from_request(market: str, ticker: str) -> dict[str, Any] | None:
    for folder in ("v99_decisions", "v98_decisions"):
        path = HERE / "runtime" / folder / market / f"{ticker}.json"
        if not path.is_file():
            continue
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
    return None


def _projection_blocked(market: str, price: float | None, proof: Mapping[str, Any], research: Mapping[str, Any]) -> dict[str, Any]:
    references = []
    for chain in research.get("chains") or []:
        if not isinstance(chain, Mapping):
            continue
        references.append({
            "type": "CAUSAL_CHAIN_RANGE_NOT_A_PRICE_TARGET",
            "chain": chain.get("name"),
            "role": chain.get("role"),
            "expected_multiplier_reference": chain.get("expected_multiplier"),
            "horizon_reference": chain.get("horizon"),
            "claim_limit": "Narrative/reference range from the bundled map; not calibrated, not a target and not executable.",
        })
    bottleneck = research.get("bottleneck_reference")
    if isinstance(bottleneck, Mapping):
        references.append({
            "type": "BOTTLENECK_REFERENCE",
            "role": bottleneck.get("role"),
            "priority": bottleneck.get("priority"),
            "reference_target_text": bottleneck.get("target"),
            "claim_limit": "Research reference only; no frozen valuation bridge or target calibration.",
        })
    for entry in research.get("historical_reference_entries") or []:
        if isinstance(entry, Mapping):
            references.append({"type": "HISTORICAL_THIRD_PARTY_ENTRY_REFERENCE", **dict(entry), "claim_limit": "Historical reference, not a current entry or recommendation."})
    return {
        "valid": False,
        "projection_status": "RESEARCH_CONTEXT_AVAILABLE_VALUE_BRIDGE_NOT_PROVEN" if references else "WITHHELD_NO_TICKER_VALUE_BRIDGE",
        "current_price": price,
        "target_low": None,
        "target_base": None,
        "target_high": None,
        "expected_target_price": None,
        "expected_return": None,
        "horizon_days": None,
        "methods_allowed": PROJECTION_METHODS.get(market, []),
        "research_references": references,
        "reason": "A ticker-specific, pre-registered value bridge has not passed proof. Research references remain visible but are not promoted into a numeric target.",
        "capital_permission": "BLOCKED",
        "market_proof_missing": not bool(proof.get("proof_run_valid")),
    }


def _evidence_summary(evidence: Mapping[str, Any]) -> dict[str, Any]:
    observed = pit = 0; rows: list[dict[str, Any]] = []
    for name, item in evidence.items():
        row = dict(item) if isinstance(item, Mapping) else {}
        state = str(row.get("state") or "NO_DATA")
        if state not in {"NO_DATA", "ROUTE_ONLY", "MISSING"}: observed += 1
        if row.get("point_in_time_eligible") is True: pit += 1
        rows.append({"domain": name, **row})
    return {"observed_domains": observed, "pit_ready_domains": pit, "total_domains": len(rows), "rows": rows}


def _causal_rows(market: str, research: Mapping[str, Any], evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    chains = research.get("chains") or []
    if chains:
        chain = chains[0]
        return [
            {"step": 1, "name": "trigger / origin", "state": "REFERENCE_AVAILABLE", "source": "data/chain_reactions.json", "note": chain.get("trigger_event")},
            {"step": 2, "name": "transmission mechanism", "state": "REFERENCE_AVAILABLE", "source": "data/chain_reactions.json", "note": chain.get("mechanism")},
            {"step": 3, "name": "bottleneck / role", "state": "REFERENCE_AVAILABLE", "source": "data/chain_reactions.json", "note": chain.get("role")},
            {"step": 4, "name": "beneficiary / ticker", "state": "REFERENCE_AVAILABLE", "source": "data/chain_reactions.json", "note": f"{research.get('ticker')} · tier {chain.get('tier')} · step {chain.get('step')}"},
            {"step": 5, "name": "activation clock", "state": str(chain.get("trigger_status") or "REFERENCE"), "source": "data/chain_reactions.json", "note": f"{chain.get('horizon')} · lag {chain.get('horizon_quarters')}"},
            {"step": 6, "name": "rationale", "state": "REFERENCE_AVAILABLE", "source": "data/chain_reactions.json", "note": chain.get("rationale")},
            {"step": 7, "name": "expectations gap", "state": "NOT_PROVEN", "source": "ticker-specific point-in-time expectations required", "note": "Reference map does not establish what is already priced."},
            {"step": 8, "name": "invalidation", "state": "NOT_REGISTERED", "source": "ticker value-bridge request", "note": "Must be frozen before a trade can be considered."},
        ]
    idx_groups = research.get("idx_groups") or []
    if idx_groups:
        group = idx_groups[0]
        return [
            {"step": 1, "name": "controller / group", "state": "REFERENCE_AVAILABLE", "source": "data/ihsg_conglomerates.json", "note": f"{group.get('group_id')} · {group.get('patriarch')}"},
            {"step": 2, "name": "holding / affiliation", "state": "REFERENCE_AVAILABLE", "source": "data/ihsg_conglomerates.json", "note": f"holding: {group.get('holding')} · broker reference: {group.get('broker_affiliate')}"},
            {"step": 3, "name": "observed play-pattern reference", "state": "REFERENCE_ONLY", "source": "data/ihsg_conglomerates.json", "note": " · ".join(group.get("play_patterns") or [])},
            {"step": 4, "name": "free float / broker inventory", "state": "NO_POINT_IN_TIME_DATA", "source": "IDX/broker data required", "note": "Reference relationships cannot replace signed inventory and free-float history."},
            {"step": 5, "name": "fundamental value capture", "state": "NOT_PROVEN", "source": "issuer filings", "note": "Ticker-specific issuer bridge is required."},
            {"step": 6, "name": "invalidation", "state": "NOT_REGISTERED", "source": "ticker value-bridge request", "note": "Must be frozen before a trade can be considered."},
        ]
    rows = []
    evidence_items = list(evidence.items())
    for index, step in enumerate(MARKET_CAUSAL_SEQUENCE.get(market, [])):
        linked = evidence_items[index] if index < len(evidence_items) else (None, None)
        linked_row = linked[1] if isinstance(linked[1], Mapping) else {}
        rows.append({"step": index + 1, "name": step, "evidence_domain": linked[0], "state": linked_row.get("state", "UNMAPPED"), "source": linked_row.get("source"), "note": linked_row.get("note")})
    return rows


def _research_score(research: Mapping[str, Any], evidence_summary: Mapping[str, Any]) -> int:
    score = int(evidence_summary.get("observed_domains") or 0) * 10
    score += 20 if research.get("chains") else 0
    score += 15 if research.get("bottleneck_reference") else 0
    score += 15 if research.get("idx_groups") else 0
    score += 10 if research.get("historical_price_context") else 0
    return score


def build_packets(*, markets: Mapping[str, Any], quotes: Mapping[str, Any], universe: Mapping[str, Any], proof_registry: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    by_market: dict[str, dict[str, Any]] = {m: {} for m in MARKETS}; all_packets: list[dict[str, Any]] = []
    quote_markets = quotes.get("markets") if isinstance(quotes.get("markets"), Mapping) else {}
    for market in MARKETS:
        market_row = markets.get(market) if isinstance(markets.get(market), Mapping) else {}
        evidence = market_row.get("evidence_domains") if isinstance(market_row.get("evidence_domains"), Mapping) else {}
        evidence_summary = _evidence_summary(evidence); proof = _component_for_market(proof_registry, market)
        rows = universe.get(market) if isinstance(universe.get(market), list) else []
        market_quotes = quote_markets.get(market) if isinstance(quote_markets.get(market), Mapping) else {}
        for item in rows:
            ticker = str(item.get("instrument") or "").strip()
            if not ticker: continue
            research = ticker_context(ticker, market)
            quote = dict(market_quotes.get(ticker)) if isinstance(market_quotes.get(ticker), Mapping) else None
            quote_state = _quote_status(quote, market)
            price = float(quote.get("price")) if quote and quote_state["reference_available"] else None
            historical = research.get("historical_price_context") if isinstance(research.get("historical_price_context"), Mapping) else None
            if price is None and historical and historical.get("last_historical_price") is not None:
                quote = {
                    "price": historical.get("last_historical_price"),
                    "provider_timestamp": historical.get("date_max"),
                    "received_at": None,
                    "validation": "HISTORICAL_RESEARCH_REFERENCE",
                    "source": historical.get("source"),
                }
                quote_state = {"state": "HISTORICAL_RESEARCH_REFERENCE", "reference_available": True, "execution_fresh": False, "reason": historical.get("claim_limit")}
                price = float(historical.get("last_historical_price"))
            projection = _projection_from_request(market, ticker) or _projection_blocked(market, price, proof, research)
            projection_valid = projection.get("valid") is True; proof_valid = proof.get("proof_run_valid") is True; execution_fresh = quote_state["execution_fresh"] is True
            permitted = bool(projection_valid and proof_valid and execution_fresh and projection.get("capital_permission") == "LIMITED_PRODUCTION_ELIGIBLE")
            research_available = bool(research and len(research) > 2) or evidence_summary["observed_domains"] > 0
            flow = [{"domain": key, **(dict(evidence.get(key)) if isinstance(evidence.get(key), Mapping) else {"state": "NO_DATA"})} for key in FLOW_KEYS.get(market, ())]
            blockers = []
            if not execution_fresh: blockers.append("CURRENT_EXECUTION_QUOTE_NOT_FRESH")
            if not proof_valid: blockers.append("EXACT_MARKET_PROOF_MISSING")
            if not projection_valid: blockers.append("TICKER_VALUE_BRIDGE_MISSING_OR_INVALID")
            if evidence_summary["pit_ready_domains"] == 0: blockers.append("POINT_IN_TIME_EVIDENCE_INCOMPLETE")
            why = "Instrument is present in the research packet universe. Inclusion is not a recommendation."
            if research.get("chains"):
                c = research["chains"][0]; why = f"Causal-chain reference: {c.get('name')} · {c.get('role')}. Still research-only until expectations, valuation and invalidation are proven."
            elif research.get("idx_groups"):
                g = research["idx_groups"][0]; why = f"IHSG controller/conglomerate reference: {g.get('group_id')}. Relationship context is not broker-flow proof."
            elif research.get("bottleneck_reference"):
                b = research["bottleneck_reference"]; why = f"Bottleneck reference: {b.get('role')} · priority {b.get('priority')}."
            packet = {
                "schema": "warroom.v99.ticker_decision_packet.v1",
                "market": market, "market_label": MARKET_LABELS[market], "ticker": ticker,
                "asset_type": item.get("asset_type"), "provider": item.get("provider"), "provider_symbol": item.get("provider_symbol"),
                "research_only_instrument": bool(item.get("research_only")),
                "data_status": "RESEARCH_CONTEXT_AVAILABLE" if research_available else "DATA_GAP",
                "decision": {
                    "state": "LIMITED_PRODUCTION_ELIGIBLE" if permitted else "RESEARCH_ONLY" if research_available else "NO_DATA",
                    "direction": projection.get("direction") if permitted else None,
                    "conviction": projection.get("calibrated_probability") if permitted else None,
                    "horizon_days": projection.get("horizon_days"),
                    "capital_permission": "LIMITED_PRODUCTION_ELIGIBLE" if permitted else "BLOCKED",
                    "blockers": blockers, "why_included": why,
                },
                "quote": {**(quote or {}), **quote_state},
                "research_context": research,
                "research_context_score": _research_score(research, evidence_summary),
                "research_readiness_score": _research_score(research, evidence_summary),  # compatibility alias; not trade readiness
                "causal_chain": _causal_rows(market, research, evidence),
                "fundamental_value_capture": {
                    "state": "READY" if projection_valid else "RESEARCH_REFERENCE_ONLY" if research_available else "NOT_INSTALLED",
                    "methods_allowed": PROJECTION_METHODS.get(market, []),
                    "projection_reason": projection.get("projection_reason"),
                    "beneficiary_value_capture": projection.get("beneficiary_value_capture"),
                    "bottleneck_claim": projection.get("bottleneck_claim") or (research.get("bottleneck_reference") or {}).get("role") if isinstance(research.get("bottleneck_reference"), Mapping) else None,
                },
                "flow_positioning": flow,
                "projection": projection,
                "risk_execution": {"entry": None, "stop": None, "target": projection.get("expected_target_price"), "expected_shortfall": None, "position_size": 0.0, "order_state": "AWAITING_APPROVED_PACKET" if permitted else "BLOCKED", "manual_export_only": True},
                "proof_data": {"market_proof_valid": proof_valid, "market_proof_state": proof.get("state", "AWAITING_BOUND_PROOF"), "market_proof_reasons": proof.get("proof_run_reasons", []), "evidence": evidence_summary},
            }
            by_market[market][ticker] = packet; all_packets.append(packet)

    # Put the most complete research packets first inside every market.  This affects only UI order;
    # it is not an alpha ranking and never changes capital permission.
    for market, rows in list(by_market.items()):
        by_market[market] = dict(sorted(rows.items(), key=lambda kv: (-int(kv[1].get("research_context_score", 0)), kv[0])))
    watchlist = sorted(all_packets, key=lambda p: (p["decision"]["state"] == "LIMITED_PRODUCTION_ELIGIBLE", p.get("research_context_score", 0), p["proof_data"]["evidence"]["pit_ready_domains"]), reverse=True)
    alpha_center = {
        "schema": "warroom.v99.alpha_center.v1",
        "promoted": [p for p in watchlist if p["decision"]["state"] == "LIMITED_PRODUCTION_ELIGIBLE"],
        "research_watchlist": watchlist,
        "state": "PROMOTED_ALPHA_AVAILABLE" if any(p["decision"]["state"] == "LIMITED_PRODUCTION_ELIGIBLE" for p in watchlist) else "RESEARCH_CONTEXT_AVAILABLE_NO_PROMOTED_ALPHA",
        "ranking_basis": "Causal/reference coverage and data readiness only; never chart performance or price-derived ranking.",
    }
    return by_market, alpha_center
