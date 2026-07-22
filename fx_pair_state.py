"""Pair-specific FX research states.

The output is deliberately not one aggregate FX long/short call. Each pair receives a separate
orientation, evidence coverage, trigger/invalidation context, event-risk gate and research action.
Price-only states never become triggered watches and capital permission always remains blocked.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from proof_registry import component_status

PAIR_ALIASES = {
    "EURUSD": "EURUSD=X", "EURUSD=X": "EURUSD=X",
    "GBPUSD": "GBPUSD=X", "GBPUSD=X": "GBPUSD=X",
    "AUDUSD": "AUDUSD=X", "AUDUSD=X": "AUDUSD=X",
    "NZDUSD": "NZDUSD=X", "NZDUSD=X": "NZDUSD=X",
    "USDJPY": "USDJPY=X", "USDJPY=X": "USDJPY=X",
    "USDCAD": "USDCAD=X", "USDCAD=X": "USDCAD=X",
    "USDCHF": "USDCHF=X", "USDCHF=X": "USDCHF=X",
    "USDIDR": "USDIDR=X", "USDIDR=X": "USDIDR=X",
    "DX-Y.NYB": "DX-Y.NYB",
}


def _obj(x: Any) -> dict:
    return x if isinstance(x, dict) else {}


def _rows(x: Any) -> list:
    return x if isinstance(x, list) else []


def _num(x: Any) -> float | None:
    try:
        n = float(x)
        return n if n == n else None
    except (TypeError, ValueError):
        return None


def _canon(value: Any) -> str:
    raw = str(value or "").upper().replace("/", "").replace("-", "")
    if raw.endswith("=X"):
        raw = raw[:-2]
    return PAIR_ALIASES.get(raw, PAIR_ALIASES.get(str(value or "").upper(), str(value or "").upper()))


def _sign_from_price(row: dict) -> tuple[int, str, list[str]]:
    r20 = _num(row.get("ret_20d"))
    r5 = _num(row.get("ret_5d"))
    above20 = row.get("above_20d")
    above50 = row.get("above_50d")
    votes: list[int] = []
    evidence: list[str] = []
    if r20 is not None:
        votes.append(1 if r20 > 0.35 else -1 if r20 < -0.35 else 0)
        evidence.append(f"20D {r20:+.2f}%")
    if r5 is not None:
        votes.append(1 if r5 > 0.15 else -1 if r5 < -0.15 else 0)
        evidence.append(f"5D {r5:+.2f}%")
    if above20 is not None:
        votes.append(1 if bool(above20) else -1)
        evidence.append(f"above20={bool(above20)}")
    if above50 is not None:
        votes.append(1 if bool(above50) else -1)
        evidence.append(f"above50={bool(above50)}")
    score = sum(votes)
    sign = 1 if score >= 2 else -1 if score <= -2 else 0
    return sign, "PRICE_TREND", evidence


def _carry_lookup(desk: dict) -> dict:
    candidates = [
        _obj(_obj(desk.get("feeds")).get("fx_carry")),
        _obj(_obj(desk.get("fx")).get("carry")),
        _obj(_obj(_obj(desk.get("full_live_data")).get("fx")).get("carry")),
    ]
    for block in candidates:
        pairs = _obj(block.get("pairs"))
        if pairs:
            return {_canon(k): v for k, v in pairs.items() if isinstance(v, dict)}
    return {}


def _carry_sign(row: dict | None) -> tuple[int, list[str]]:
    if not row:
        return 0, []
    bias = str(row.get("bias") or "NEUTRAL").upper()
    sign = 1 if "LONG" in bias else -1 if "SHORT" in bias else 0
    evidence = []
    if row.get("carry_diff") is not None:
        evidence.append(f"carry {row.get('carry_diff'):+.2f}pp")
    if row.get("carry_3m_change") is not None:
        evidence.append(f"3M Δ {row.get('carry_3m_change'):+.2f}pp")
    if bias:
        evidence.append(bias)
    return sign, evidence


def _setup_lookup(desk: dict) -> dict:
    market = _obj(_obj(desk.get("markets")).get("fx"))
    out = {}
    for row in _rows(market.get("setups")):
        if isinstance(row, dict) and row.get("tk"):
            out[_canon(row.get("tk"))] = row
    return out


def _fresh_event_risk(desk: dict, pair: str) -> list[dict]:
    dev = _obj(desk.get("current_developments"))
    rows = _rows(_obj(dev.get("by_market")).get("fx"))
    pair = _canon(pair)
    out = []
    for row in rows:
        if row.get("freshness") == "STALE" or row.get("source_verification") != "HUMAN_REVIEWED":
            continue
        title = str(row.get("title") or "").upper()
        category = str(row.get("category") or "").upper()
        watch = " ".join(str(x) for x in _rows(row.get("watch"))).upper()
        if pair == "USDIDR=X" and any(x in f"{title} {category} {watch}" for x in ("BANK INDONESIA", "BI-RATE", "JISDOR", "INDONESIA")):
            out.append(row)
        elif pair != "USDIDR=X" and category in {"PAIR_EVENT_RISK", "CENTRAL_BANK_EVENT"}:
            out.append(row)
    return out


def build_fx_pair_states(desk: dict) -> dict:
    breadth = _obj(_obj(desk.get("market_breadth")).get("fx"))
    constituents = {_canon(x.get("ticker")): x for x in _rows(breadth.get("constituents")) if isinstance(x, dict) and x.get("ticker")}
    setup_map = _setup_lookup(desk)
    carry_map = _carry_lookup(desk)
    pairs = sorted(set(constituents) | set(setup_map) | set(carry_map))
    rows = []
    for pair in pairs:
        price = constituents.get(pair)
        setup = setup_map.get(pair, {})
        carry = carry_map.get(pair)
        event_risk = _fresh_event_risk(desk, pair)
        price_sign, _, price_evidence = _sign_from_price(price) if price else (0, "NO_PRICE", [])
        carry_sign, carry_evidence = _carry_sign(carry)
        drivers = []
        if price:
            drivers.append({"driver": "price", "sign": price_sign, "state": "OBSERVED", "evidence": price_evidence})
        if carry and carry_evidence:
            drivers.append({"driver": "carry/rate differential", "sign": carry_sign, "state": "OBSERVED_OR_DERIVED", "evidence": carry_evidence})

        nonzero = [x["sign"] for x in drivers if x["sign"]]
        long_votes = sum(1 for x in nonzero if x > 0)
        short_votes = sum(1 for x in nonzero if x < 0)
        independent = len(drivers)
        conflict = long_votes and short_votes

        selector_promoted = bool(component_status("fx_pair_selector").get("predictive_promoted"))
        if not price:
            orientation, state, action = "BLOCKED", "NO_PRICE_DATA", "NO ACTION"
            reason = "No current pair-price observation."
        elif event_risk:
            orientation, state, action = "NEUTRAL", "EVENT_RISK_WAIT", "WAIT / REASSESS AFTER EVENT"
            reason = "Fresh policy/market-structure event risk can invalidate the current pair path."
        elif conflict:
            orientation, state, action = "NEUTRAL", "DRIVER_CONFLICT", "NO TRADE · DRIVER CONFLICT"
            reason = "Price and independent rate/carry evidence disagree."
        elif independent == 1:
            orientation = "LONG" if price_sign > 0 else "SHORT" if price_sign < 0 else "NEUTRAL"
            state = f"PRICE_ONLY_{orientation}" if orientation != "NEUTRAL" else "PRICE_ONLY_NEUTRAL"
            action = ("POSITIVE PRICE CONTEXT · NO TRADE" if orientation == "LONG" else
                      "NEGATIVE PRICE CONTEXT · NO TRADE" if orientation == "SHORT" else
                      "MIXED PRICE CONTEXT · NO TRADE")
            reason = "Direction is only price context; no independent macro/positioning confirmation."
        elif long_votes >= 2:
            orientation, state = "LONG", "MULTI_DRIVER_LONG_CONTEXT"
            action = "DIRECTIONAL RESEARCH CONTEXT · NO TRADE"
            reason = "Price and carry/rate differential agree, but the exact-scope FX selector is not promoted."
        elif short_votes >= 2:
            orientation, state = "SHORT", "MULTI_DRIVER_SHORT_CONTEXT"
            action = "DIRECTIONAL RESEARCH CONTEXT · NO TRADE"
            reason = "Price and carry/rate differential agree, but the exact-scope FX selector is not promoted."
        else:
            orientation, state, action = "NEUTRAL", "NO_SIGNAL", "NO TRADE"
            reason = "Available drivers do not form a directional pair state."

        # Reference geometry is shown for research, but cannot promote an unvalidated selector.
        setup_valid = bool(setup) and setup.get("e") is not None and setup.get("s") is not None
        directional_permission = bool(selector_promoted and independent >= 2 and setup_valid and not event_risk and not conflict)
        if directional_permission and orientation in {"LONG", "SHORT"}:
            state = f"TRIGGERED_RESEARCH_{orientation}"
            action = f"TRIGGERED RESEARCH {orientation}"
            reason += " Exact-scope selector promotion exists; capital still requires human approval."

        rows.append({
            "pair": pair,
            "orientation": orientation,
            "state": state,
            "research_action": action,
            "capital_permission": "BLOCKED",
            "directional_permission": directional_permission,
            "selector_state": component_status("fx_pair_selector").get("state"),
            "reason": reason,
            "driver_coverage": independent,
            "driver_total": 4,
            "drivers": drivers,
            "event_risks": [{"title": x.get("title"), "date": x.get("date"), "category": x.get("category")} for x in event_risk],
            "entry_trigger": setup.get("e"),
            "trade_invalidation": setup.get("s"),
            "reference_target": setup.get("t"),
            "rr": setup.get("rr"),
            "freshness": "CURRENT" if price else "NO_DATA",
            "semantics": "Pair-specific research state; not an autonomous order or calibrated probability.",
        })

    actionable = [x for x in rows if x.get("directional_permission")]
    watches = [x for x in rows if x["state"] in {"MULTI_DRIVER_LONG_CONTEXT", "MULTI_DRIVER_SHORT_CONTEXT"}]
    return {
        "state": "LIVE" if rows else "NO_DATA",
        "pairs": rows,
        "triggered_count": len(actionable),
        "watch_count": len(watches),
        "semantics": "There is no single FX long/short state. Pair orientation is descriptive until the exact-scope FX selector passes WFA, lockbox and prospective gates.",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def attach_fx_pair_states(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    out = deepcopy(desk)
    out["fx_pair_states"] = build_fx_pair_states(out)
    return out
