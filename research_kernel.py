"""Universal research kernel for War Room OS.

This module does not create alpha or trade permission. It translates the currently loaded
observations into a consistent research contract for every market. Missing evidence remains
explicitly missing. The same reasoning discipline is applied everywhere, while the decision
problem, baseline, counterparties and failure modes remain market-specific.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from current_developments import attach_current_developments
from fx_pair_state import attach_fx_pair_states
from market_capabilities import attach_market_capabilities
from proof_registry import attach_proof_registry, component_status
from regime_tournament import attach_regime_tournament

MARKET_DOCTRINE: dict[str, dict[str, Any]] = {
    "us": {
        "label": "US STOCKS",
        "decision_problem": "Find company-specific value capture and estimate revisions before the market fully reprices them.",
        "baseline": "Price trend + market beta + earnings revisions + liquidity.",
        "counterparties": ["index/passive flow", "dealer hedge", "corporate buyback", "fundamental investor", "forced seller"],
        "critical_conditions": ["direct value capture", "estimate revision durability", "liquidity/capacity", "valuation headroom", "catalyst timing"],
        "failure_modes": ["momentum mislabeled as flow", "good theme / wrong beneficiary", "earnings already priced", "options print was hedge or roll"],
    },
    "idx": {
        "label": "IHSG",
        "decision_problem": "Find liquid long-only opportunities where foreign/controller/broker context and company economics align without mistaking routing for ownership intent.",
        "baseline": "Price trend + liquidity + foreign/sector context; long-only.",
        "counterparties": ["controller", "foreign fund", "broker facilitation", "crossing counterparty", "retail liquidity"],
        "critical_conditions": ["minority-holder value capture", "free-float/liquidity", "controller alignment", "corporate-action integrity", "sector/commodity transmission"],
        "failure_modes": ["broker route mistaken for beneficial owner", "cross trade mistaken for accumulation", "dilution/corporate action", "correct commodity call / wrong company"],
    },
    "crypto": {
        "label": "CRYPTO",
        "decision_problem": "Separate organic adoption and token value capture from subsidy, sybil, wash activity and reflexive leverage while tracking broker-DeFi convergence, tokenized assets, stablecoins, prediction markets and agentic execution.",
        "baseline": "BTC beta + token size + age + liquidity + momentum.",
        "counterparties": ["market maker", "insider/unlock seller", "LP rebalancer", "centralized broker", "token issuer", "airdrop farmer", "leveraged directional trader", "regulatory-constrained participant"],
        "critical_conditions": ["organic activity and retention", "token-required value capture", "unlock/supply control", "venue and collateral liquidity", "legal form / reserves / redemption", "distribution and developer adoption", "wallet/entity attribution and security"],
        "failure_modes": ["transfer mistaken for trade intent", "tokenized exposure mistaken for underlying ownership", "platform captures value but token does not", "subsidized TVL or wash/sybil volume", "fragmented liquidity", "unlock overwhelms demand", "jurisdiction/regulatory break", "agentic execution or smart-contract loss", "crime candle/pump-and-dump"],
    },
    "commodity": {
        "label": "COMMODITIES",
        "decision_problem": "Detect physical tightness and the best tradable expression before benchmark repricing or rapid supply response.",
        "baseline": "Trend + curve/carry + inventory surprise + USD.",
        "counterparties": ["producer hedge", "commercial consumer", "inventory holder", "CTA/speculator", "forced physical seller"],
        "critical_conditions": ["location/grade-specific tightness", "curve confirmation", "inventory quality", "supply-response lag", "demand destruction threshold"],
        "failure_modes": ["financial positioning mistaken for physical shortage", "wrong location/grade", "rapid capacity response", "headline spike mean reverts"],
    },
    "fx": {
        "label": "FX",
        "decision_problem": "Identify the dominant pair-specific driver and when rate, funding, policy or risk regimes have changed.",
        "baseline": "Carry + rate differential + trend + volatility regime.",
        "counterparties": ["corporate hedger", "reserve manager", "real-money fund", "carry fund", "policy/intervention flow"],
        "critical_conditions": ["pair-specific rate/policy differential", "funding regime", "positioning asymmetry", "external balance", "intervention risk"],
        "failure_modes": ["aggregate FX call applied to every pair", "old correlation after regime change", "carry dominates thesis", "intervention/funding shock"],
    },
}

INVALID_DATA_STATES = {"", "NO_DATA", "UNAVAILABLE", "NOT_CONFIGURED", "NOT_ENTITLED", "ERROR", "OFFLINE", "INITIALIZING"}
ACTIONABLE_PREFIXES = ("BUILD LONG", "BUILD SHORT")


def _obj(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _rows(value: Any) -> list:
    return value if isinstance(value, list) else []


def _number(value: Any) -> float | None:
    try:
        value = float(value)
        return value if value == value else None
    except (TypeError, ValueError):
        return None


def _state(value: Any) -> str:
    return str(value or "NO_DATA").upper()


def _setup_action(market_id: str, market: dict, setup: dict) -> str:
    """Translate a setup into its maximum permitted claim.

    Generic OHLCV screens are descriptive controls. They never become WATCH/BUILD actions.
    Market-specific directional labels require an exact-scope promoted selector, which the
    current registry intentionally does not grant.
    """
    raw = str(setup.get("act") or setup.get("ty") or "").upper()
    direction = str(setup.get("dir") or "neutral").lower()
    rr = _number(setup.get("rr"))
    if setup.get("conflicted") or "CONFLICT" in raw:
        return "NO TRADE · CONFLICTED"
    if str(setup.get("liquidity_state") or "").upper() == "BELOW_RESEARCH_FLOOR":
        return "LOW LIQUIDITY · CONTEXT ONLY"
    if rr is not None and rr < 1.5:
        return "NO TRADE · POOR R/R"
    if not bool(setup.get("directional_permission")):
        if market_id == "idx" and direction == "short":
            return "NEGATIVE PRICE CONTEXT · NOT ELIGIBLE FOR NEW LONG"
        if direction == "long":
            return "POSITIVE PRICE CONTEXT"
        if direction == "short":
            return "NEGATIVE PRICE CONTEXT"
        return "MIXED PRICE CONTEXT"
    selector = component_status({
        "us": "us_directional_selector",
        "idx": "ihsg_long_selector",
        "crypto": "crypto_directional_selector",
        "commodity": "commodity_directional_selector",
        "fx": "fx_pair_selector",
    }.get(market_id, "generic_price_context"))
    if not selector.get("predictive_promoted"):
        return "DIRECTIONAL CLAIM WITHHELD"
    return str(setup.get("research_action") or raw or "DIRECTIONAL RESEARCH CONTEXT")


def _best_setup(market_id: str, market: dict) -> dict:
    setups = [x for x in _rows(market.get("setups")) if isinstance(x, dict) and x.get("tk")]
    if not setups:
        return {}
    # Research priority: cleared liquidity first, then component agreement, then descriptive rank.
    # R/R does not rescue a weak/unvalidated selector.
    return sorted(
        setups,
        key=lambda x: (
            1 if str(x.get("liquidity_state") or "").upper() == "ELIGIBLE" else 0,
            int(_number(x.get("agreement_count")) or 0),
            _number(x.get("setup_rank")) or _number(x.get("conv")) or 0,
        ),
        reverse=True,
    )[0]


def _market_alpha(desk: dict, market_id: str) -> list[dict]:
    return [x for x in _rows(desk.get("alpha")) if isinstance(x, dict) and str(x.get("market") or "") == market_id]


def _market_events(desk: dict, market_id: str, tickers: set[str]) -> list[dict]:
    events = []
    for plane in (_obj(desk.get("institutional")), _obj(desk.get("live_intelligence"))):
        for event in _rows(plane.get("events")):
            if not isinstance(event, dict):
                continue
            ticker = str(event.get("ticker") or event.get("symbol") or "").upper()
            if ticker and ticker in tickers:
                events.append(event)
            elif market_id == "crypto" and any(k in str(event.get("event_type") or event.get("dataset") or "").lower() for k in ("crypto", "whale", "onchain")):
                events.append(event)
    return events


def _current_rain(market_id: str, market: dict, breadth: dict, best: dict) -> dict:
    coverage = int(_number(breadth.get("coverage")) or _number(_obj(market.get("funnel")).get("universe")) or 0)
    breadth_state = _state(breadth.get("state"))
    market_state = _state(market.get("data_state"))
    if coverage <= 0 or (breadth_state in INVALID_DATA_STATES and market_state in INVALID_DATA_STATES):
        return {
            "state": "NO_DATA",
            "claim": "No present-state market claim is permitted because the required market observations are unavailable.",
            "evidence": "No loaded market universe.",
        }
    adv = _number(breadth.get("advance_pct"))
    above50 = _number(breadth.get("above_50d_pct"))
    median20 = _number(breadth.get("median_ret_20d_pct"))
    bits = [f"{coverage} loaded names"]
    if adv is not None:
        bits.append(f"{adv:.1f}% advancing")
    if above50 is not None:
        bits.append(f"{above50:.1f}% above 50D")
    if median20 is not None:
        bits.append(f"median 20D {median20:+.1f}%")
    if best:
        bits.append(f"top context {best.get('tk')} / {_setup_action(market_id, market, best)}")
    if adv is not None and above50 is not None and adv >= 55 and above50 >= 50:
        state, claim = "OBSERVED_IMPROVING", "Loaded price breadth is constructive now; this is present-state context, not proof of future excess return."
    elif adv is not None and above50 is not None and adv < 45 and above50 < 50:
        state, claim = "OBSERVED_DETERIORATING", "Loaded price breadth is deteriorating now; this is present-state context, not a crash forecast."
    else:
        state, claim = "OBSERVED_MIXED", "Loaded price breadth is mixed; the system should wait for a more discriminating trigger."
    return {"state": state, "claim": claim, "evidence": " · ".join(bits)}


def _recognition_gap(alpha_rows: list[dict], best: dict) -> dict:
    if not alpha_rows:
        return {"state": "UNASSESSED", "claim": "No structural candidate is linked to this market, so recognition gap and remaining return are unassessed."}
    lead = sorted(alpha_rows, key=lambda x: (_number(x.get("asymmetry")) or 0), reverse=True)[0]
    price_loaded = bool(lead.get("price_loaded"))
    timing = str(lead.get("timing_action") or "NO_TIMING")
    return {
        "state": "RESEARCH_REQUIRED",
        "claim": (
            f"{lead.get('tk')} is the leading structural research candidate ({lead.get('upside') or '?'} headroom class; "
            f"timing {timing}). Headroom is not a target or probability; value capture, valuation and remaining return still require proof."
        ),
        "ticker": lead.get("tk"),
        "price_loaded": price_loaded,
    }


def _condition_matrix(doctrine: dict, desk: dict, market_id: str, market: dict, breadth: dict, alpha_rows: list[dict], events: list[dict]) -> list[dict]:
    data_live = _state(market.get("data_state")) not in INVALID_DATA_STATES and int(_number(_obj(market.get("funnel")).get("universe")) or 0) > 0
    bias_live = _state(market.get("bias_state")) == "LIVE"
    alpha_present = bool(alpha_rows)
    event_present = bool(events)
    rows = []
    for i, condition in enumerate(doctrine["critical_conditions"]):
        if i == 0:
            status = "PARTIAL" if alpha_present else "UNASSESSED"
            evidence = "Structural alpha mapping present." if alpha_present else "No direct value-capture case linked."
        elif i == 1:
            status = "PARTIAL" if data_live else "NO_DATA"
            evidence = "Observed market/price context loaded." if data_live else "Market data unavailable."
        elif i == 2:
            status = "PARTIAL" if event_present else "UNASSESSED"
            evidence = "At least one cross-source event is linked." if event_present else "No independent positioning/event evidence linked."
        elif i == 3:
            status = "PARTIAL" if bias_live else "UNASSESSED"
            evidence = "Market-specific directional model available." if bias_live else "Market-specific directional model incomplete."
        else:
            status = "UNASSESSED"
            evidence = "Requires company/instrument-specific research."
        rows.append({"condition": condition, "status": status, "evidence": evidence, "critical": True})
    return rows


def _edge_decomposition(alpha_rows: list[dict], events: list[dict], best: dict, market: dict) -> dict:
    information = "PARTIAL" if events or best else "UNASSESSED"
    interpretation = "RESEARCH_REQUIRED" if alpha_rows else "UNASSESSED"
    positioning = "PARTIAL" if events else "UNASSESSED"
    timing = "PARTIAL" if best else "NO_SIGNAL"
    expression = "PARTIAL" if best and best.get("tk") else "UNASSESSED"
    execution = "PARTIAL" if best and best.get("e") is not None and best.get("s") is not None else "UNASSESSED"
    return {
        "information": information,
        "interpretation": interpretation,
        "positioning": positioning,
        "timing": timing,
        "expression": expression,
        "execution": execution,
        "durability": "UNASSESSED",
        "note": "No composite edge score is produced. Each dimension must earn evidence independently.",
    }


def _permission(best: dict, market_id: str, market: dict, current_rain: dict, conditions: list[dict]) -> dict:
    action = _setup_action(market_id, market, best) if best else "NO TRADE"
    missing = [x["condition"] for x in conditions if x["status"] in {"NO_DATA", "UNASSESSED"}]
    if current_rain.get("state") == "NO_DATA":
        action = "NO ACTION"
        reason = "Required present-state observations are unavailable."
    else:
        reason = "Current output is descriptive research context. Exact-scope WFA, lockbox and prospective gates have not promoted a selector."
    return {
        "research_action": action,
        "capital_permission": "BLOCKED",
        "reason": reason,
        "missing_critical_evidence": missing,
    }


def build_market_kernel(desk: dict, market_id: str) -> dict:
    doctrine = MARKET_DOCTRINE[market_id]
    market = _obj(_obj(desk.get("markets")).get(market_id))
    breadth = _obj(_obj(desk.get("market_breadth")).get(market_id))
    best = _best_setup(market_id, market)
    alpha_rows = _market_alpha(desk, market_id)
    tickers = {str(best.get("tk") or "").upper()} if best else set()
    tickers.update(str(x.get("tk") or "").upper() for x in alpha_rows if x.get("tk"))
    events = _market_events(desk, market_id, tickers)
    current_rain = _current_rain(market_id, market, breadth, best)
    recognition = _recognition_gap(alpha_rows, best)
    conditions = _condition_matrix(doctrine, desk, market_id, market, breadth, alpha_rows, events)
    action = _permission(best, market_id, market, current_rain, conditions)

    best_action = _setup_action(market_id, market, best) if best else "NO TRADE"
    market_developments = _rows(_obj(_obj(desk.get("current_developments")).get("by_market")).get(market_id))
    fresh_developments = [x for x in market_developments if x.get("freshness") == "FRESH"]
    trigger = (
        f"{best.get('tk')} reference geometry {best.get('e')} / invalidation {best.get('s')} / reference {best.get('t')}"
        if best else "No instrument-specific trigger is currently constructed."
    )
    return {
        "market": market_id,
        "label": doctrine["label"],
        "decision_problem": doctrine["decision_problem"],
        "epistemic_state": {
            "observed": current_rain["state"] != "NO_DATA",
            "inferred": bool(alpha_rows) or _state(market.get("bias_state")) == "LIVE",
            "disputed": False,
            "unknown": bool(action["missing_critical_evidence"]),
        },
        "current_rain": current_rain,
        "structural_pressure": {
            "state": "RESEARCH_REQUIRED" if alpha_rows else "UNASSESSED",
            "claim": (
                f"{len(alpha_rows)} structural candidates are mapped; mechanism and value capture remain case-specific."
                if alpha_rows else "No structural pressure/value-capture case is linked to this market."
            ),
        },
        "current_developments": {
            "state": "REVIEW_REQUIRED" if fresh_developments else "NO_FRESH_DEVELOPMENT",
            "fresh_count": len(fresh_developments),
            "entries": fresh_developments[:12],
            "semantics": "Dated structural changes from primary sources; no automatic direction or trade action.",
        },
        "trigger": {"state": "REFERENCE_GEOMETRY_ONLY" if best else "NO_SIGNAL", "claim": trigger, "action_context": best_action},
        "market_recognition": recognition,
        "study_the_tape": {
            "state": "RESEARCH_REQUIRED",
            "winner_autopsy": "No winner case may be inferred from price similarity alone. Link a point-in-time winner and loser case before promotion.",
            "why_they_won": "UNASSESSED",
            "why_others_failed": doctrine["failure_modes"],
            "condition_persistence": conditions,
        },
        "edge_decomposition": _edge_decomposition(alpha_rows, events, best, market),
        "counterparty_challenge": {
            "state": "RESEARCH_REQUIRED",
            "likely_counterparties": doctrine["counterparties"],
            "why_favorable": "UNASSESSED — explain information, interpretation, horizon, constraint or liquidity-provision advantage.",
            "hard_gate": "No counterparty explanation means no edge claim.",
        },
        "cost_of_staying": {
            "state": "UNASSESSED",
            "costs": ["foregone best alternative", "adverse carry/funding/theta", "thesis decay", "capital lock-up", "lost learning cycles"],
            "value_of_waiting": ["new information", "better price", "lower execution risk", "preserved optionality"],
            "current_choice": "PROBE/WAIT decision must be instrument-specific; no numeric score is invented.",
        },
        "execution": {
            "state": "RESEARCH_ONLY" if best else "NO_SIGNAL",
            "ticker": best.get("tk") if best else None,
            "research_action": action["research_action"],
            "entry_trigger": best.get("e") if best else None,
            "trade_invalidation": best.get("s") if best else None,
            "reference_target": best.get("t") if best else None,
            "thesis_invalidation": "Broken mechanism/value capture or a critical condition that no longer holds.",
            "exit_hierarchy": ["hard risk", "thesis broken", "trade structure broken", "catalyst realized", "expected-return exhausted", "superior alternative", "time stop"],
        },
        "validation": {
            "baseline": doctrine["baseline"],
            "next_cheapest_falsifier": (
                f"Test whether the selected evidence adds point-in-time OOS lift over: {doctrine['baseline']}"
            ),
            "required": ["point-in-time lineage", "strong baseline", "purged/embargoed WFA", "ablation", "cost/capacity", "untouched lockbox", "prospective outcomes"],
            "status": "RESEARCH_ONLY",
            "capital_permission": action["capital_permission"],
            "reason": action["reason"],
        },
    }


def attach_research_kernel(desk: dict) -> dict:
    """Attach or refresh the universal research kernel on a merged desk snapshot."""
    if not isinstance(desk, dict):
        return desk
    result = attach_current_developments(deepcopy(desk))
    result = attach_fx_pair_states(result)
    markets = _obj(result.get("markets"))
    kernels = {}
    for market_id in MARKET_DOCTRINE:
        if market_id in markets or market_id in {"us", "idx", "crypto", "commodity", "fx"}:
            kernels[market_id] = build_market_kernel(result, market_id)
    result = attach_market_capabilities(result)
    result = attach_proof_registry(result)
    result = attach_regime_tournament(result)
    result["research_kernel"] = {
        "version": "4.2",
        "doctrine": [
            "Start from an important decision problem, not an available dataset.",
            "Detect what has already changed before forecasting what may change.",
            "Study historical winners and losers; explain mechanisms, not resemblance.",
            "Record contradictory evidence and uncertainty explicitly.",
            "Explain the rational counterparty and the source of advantage.",
            "Run the cheapest valid falsifier against a strong market-specific baseline.",
            "Ablate complexity and inspect failure piles, not only aggregate metrics.",
            "No prospective evidence means no capital permission.",
            "Fresh official-source changes require human review and never become automatic directional claims.",
            "FX is pair-specific; a price-only state can never become a triggered watch.",
            "Options and Greek modules appear only where product and data capability gates pass.",
            "Generic OHLCV screens are context screens, never directional selectors.",
            "No scenario headroom, probability or EV without point-in-time economic inputs and calibrated probabilities.",
        ],
        "markets": kernels,
        "global_permission": "CAPITAL_BLOCKED",
        "semantics": "Research governance and decision context only; not alpha proof or autonomous trade permission.",
    }
    return result
