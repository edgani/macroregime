"""Pair-specific FX research states.

The output is deliberately not one aggregate FX long/short call. Each pair receives a separate
orientation, evidence coverage, trigger/invalidation context, event-risk gate and research action.
Price-only states never become triggered watches and capital permission always remains blocked.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

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
        if row.get("freshness") != "FRESH":
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

        if not price:
            orientation, state, action = "BLOCKED", "NO_PRICE_DATA", "NO ACTION"
            reason = "No current pair-price observation."
        elif event_risk:
            orientation, state, action = "NEUTRAL", "EVENT_RISK_WAIT", "WAIT / REASSESS AFTER EVENT"
            reason = "Fresh policy/market-structure event risk can invalidate the current pair path."
        elif conflict:
            orientation, state, action = "NEUTRAL", "DRIVER_CONFLICT", "NO TRADE / TWO-SIDED WATCH"
            reason = "Price and independent rate/carry evidence disagree."
        elif independent == 1:
            orientation = "LONG" if price_sign > 0 else "SHORT" if price_sign < 0 else "NEUTRAL"
            state = f"PRICE_ONLY_{orientation}" if orientation != "NEUTRAL" else "PRICE_ONLY_NEUTRAL"
            action = f"WATCH {orientation} · PRICE ONLY" if orientation != "NEUTRAL" else "NO TRADE · PRICE ONLY"
            reason = "Direction is only price context; no independent macro/positioning confirmation."
        elif long_votes >= 2:
            orientation, state, action = "LONG", "WATCH_LONG", "WATCH LONG"
            reason = "Price and carry/rate differential agree; still research-only and not prospectively promoted."
        elif short_votes >= 2:
            orientation, state, action = "SHORT", "WATCH_SHORT", "WATCH SHORT"
            reason = "Price and carry/rate differential agree; still research-only and not prospectively promoted."
        else:
            orientation, state, action = "NEUTRAL", "NO_SIGNAL", "NO TRADE"
            reason = "Available drivers do not form a directional pair state."

        # A setup can upgrade a two-driver watch to triggered watch, never a price-only state.
        setup_valid = bool(setup) and bool(setup.get("valid", True)) and not setup.get("warn")
        raw_action = str(setup.get("act") or "").upper()
        setup_direction = 1 if "LONG" in raw_action or "BUY" in raw_action else -1 if "SHORT" in raw_action or "SELL" in raw_action else 0
        orientation_sign = 1 if orientation == "LONG" else -1 if orientation == "SHORT" else 0
        if independent >= 2 and setup_valid and setup_direction and setup_direction == orientation_sign and state in {"WATCH_LONG", "WATCH_SHORT"}:
            state = f"TRIGGERED_WATCH_{orientation}"
            action = f"TRIGGERED WATCH {orientation}"
            reason += " Price trigger is valid, but capital remains blocked."

        rows.append({
            "pair": pair,
            "orientation": orientation,
            "state": state,
            "research_action": action,
            "capital_permission": "BLOCKED",
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

    actionable = [x for x in rows if x["state"].startswith("TRIGGERED_WATCH")]
    watches = [x for x in rows if x["state"] in {"WATCH_LONG", "WATCH_SHORT"}]
    return {
        "state": "LIVE" if rows else "NO_DATA",
        "pairs": rows,
        "triggered_count": len(actionable),
        "watch_count": len(watches),
        "semantics": "There is no single FX long/short state. Every pair is scored separately and price-only direction cannot trigger a trade watch.",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def attach_fx_pair_states(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    out = deepcopy(desk)
    out["fx_pair_states"] = build_fx_pair_states(out)
    return out
