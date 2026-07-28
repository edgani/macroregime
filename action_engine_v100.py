"""Operational non-technical action engine for War Room OS V10.0.

This module produces current *research actions* and shadow-trading plans from economic,
fundamental, valuation, physical/protocol, positioning and causal evidence.  It does not claim
that those actions are proven alpha.  Systematic live capital remains bound to exact proof.
Current price is used only as a valuation denominator and execution/risk reference.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import statistics
from pathlib import Path
from typing import Any, Iterable, Mapping

HERE = Path(__file__).resolve().parent
UTC = dt.timezone.utc
MARKETS = ("us", "idx", "crypto", "commodity", "fx")


def _finite(value: Any) -> float | None:
    try:
        f = float(value)
        return f if math.isfinite(f) else None
    except Exception:
        return None


def _clip(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _mean(values: Iterable[float | None]) -> float | None:
    rows = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return statistics.fmean(rows) if rows else None


def _median(values: Iterable[float | None]) -> float | None:
    rows = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return statistics.median(rows) if rows else None


def _quantile(values: Iterable[float | None], q: float) -> float | None:
    rows = sorted(float(v) for v in values if v is not None and math.isfinite(float(v)))
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0]
    pos = (len(rows) - 1) * q
    lo = int(math.floor(pos)); hi = int(math.ceil(pos)); frac = pos - lo
    return rows[lo] * (1.0 - frac) + rows[hi] * frac


def _signed_scale(value: float | None, scale: float) -> float | None:
    if value is None or scale <= 0:
        return None
    return _clip(value / scale)


def _inverse_ratio(current: float | None, peer: float | None, *, cap: float = 1.0) -> float | None:
    if current is None or peer is None or current <= 0 or peer <= 0:
        return None
    # Positive when current is cheaper than the peer anchor, negative when more expensive.
    return _clip(math.log(peer / current) / max(0.01, cap))


def _timestamp_age_hours(record: Mapping[str, Any] | None) -> float | None:
    if not isinstance(record, Mapping):
        return None
    for key in ("provider_timestamp", "received_at", "collected_at"):
        try:
            stamp = dt.datetime.fromisoformat(str(record.get(key)).replace("Z", "+00:00")).astimezone(UTC)
            return max(0.0, (dt.datetime.now(UTC) - stamp).total_seconds() / 3600.0)
        except Exception:
            continue
    return None


def quote_state(record: Mapping[str, Any] | None, market: str) -> dict[str, Any]:
    price = _finite((record or {}).get("price")) if isinstance(record, Mapping) else None
    validation = str((record or {}).get("validation") or "") if isinstance(record, Mapping) else ""
    age = _timestamp_age_hours(record)
    if market == "crypto":
        limit = 0.5
    elif market in {"fx", "commodity"}:
        limit = 24.0
    else:
        limit = 36.0
    fresh = bool(price and validation == "VALID_CURRENT_REFERENCE" and age is not None and age <= limit)
    usable = bool(price and validation in {"VALID_CURRENT_REFERENCE", "STALE_LAST_KNOWN_REFERENCE"})
    return {
        "price": price,
        "reference_available": usable,
        "fresh": fresh,
        "age_hours": round(age, 2) if age is not None else None,
        "state": "FRESH" if fresh else "STALE_REFERENCE" if usable else "MISSING",
        "claim_limit": "Price is a valuation denominator and execution/risk reference only.",
    }


def _series(current: Mapping[str, Any], series_id: str) -> Mapping[str, Any]:
    row = (((current.get("macro") or {}).get("series") or {}).get(series_id))
    return row if isinstance(row, Mapping) else {}


def _change(current: Mapping[str, Any], series_id: str, key: str = "pct_change_12") -> float | None:
    return _finite(_series(current, series_id).get(key))


def _level(current: Mapping[str, Any], series_id: str) -> float | None:
    return _finite(_series(current, series_id).get("value"))


def macro_states(current: Mapping[str, Any]) -> dict[str, Any]:
    growth = _mean([
        _signed_scale(_change(current, "INDPRO", "pct_change_12"), 0.06),
        _signed_scale(_change(current, "PAYEMS", "pct_change_12"), 0.04),
    ])
    inflation = _mean([
        _signed_scale(_change(current, "CPIAUCSL", "pct_change_12"), 0.06),
        _signed_scale(_change(current, "PCEPI", "pct_change_12"), 0.05),
    ])
    # Declining RRP/TGA and expanding central-bank assets are interpreted as easier marginal liquidity.
    liquidity = _mean([
        _signed_scale(_change(current, "WALCL", "pct_change_12"), 0.12),
        _signed_scale(-(_change(current, "RRPONTSYD", "pct_change_12") or 0.0), 0.80) if _change(current, "RRPONTSYD", "pct_change_12") is not None else None,
        _signed_scale(-(_change(current, "WTREGEN", "pct_change_12") or 0.0), 0.80) if _change(current, "WTREGEN", "pct_change_12") is not None else None,
    ])
    credit = _mean([
        _signed_scale(-(_change(current, "BAMLH0A0HYM2", "change_3") or 0.0), 1.0) if _change(current, "BAMLH0A0HYM2", "change_3") is not None else None,
    ])
    real_rate = _signed_scale(-(_change(current, "DFII10", "change_3") or 0.0), 0.75) if _change(current, "DFII10", "change_3") is not None else None
    usd = _signed_scale(-(_change(current, "DTWEXBGS", "pct_change_3") or 0.0), 0.05) if _change(current, "DTWEXBGS", "pct_change_3") is not None else None
    risk_assets = _mean([growth, liquidity, credit, real_rate, usd])
    state = "SUPPORTIVE" if (risk_assets or 0.0) >= 0.20 else "RESTRICTIVE" if (risk_assets or 0.0) <= -0.20 else "MIXED"
    return {
        "growth_score": growth, "inflation_score": inflation, "liquidity_score": liquidity,
        "credit_score": credit, "real_rate_relief_score": real_rate, "usd_relief_score": usd,
        "risk_asset_score": risk_assets, "state": state,
        "observed_inputs": sum(v is not None for v in (growth, inflation, liquidity, credit, real_rate, usd)),
        "claim_limit": "Current-vintage macro context; historical release-vintage proof is separate.",
    }


def _equity_peer_table(current: Mapping[str, Any], market: str) -> list[dict[str, float]]:
    rows = (((current.get("fundamentals") or {}).get("markets") or {}).get(market) or {})
    out: list[dict[str, float]] = []
    for ticker, raw in rows.items():
        if not isinstance(raw, Mapping):
            continue
        cap = _finite(raw.get("market_cap")); rev = _finite(raw.get("revenue_ttm")); ni = _finite(raw.get("net_income_ttm")); fcf = _finite(raw.get("free_cash_flow_ttm")); equity = _finite(raw.get("stockholders_equity"))
        if cap is None or cap <= 0:
            continue
        row: dict[str, float] = {"ticker": str(ticker), "market_cap": cap}  # type: ignore[dict-item]
        if rev and rev > 0: row["ps"] = cap / rev
        if ni and ni > 0: row["pe"] = cap / ni
        if fcf and fcf > 0: row["pfcf"] = cap / fcf
        if equity and equity > 0: row["pb"] = cap / equity
        out.append(row)
    return out


def _equity_projection(ticker: str, market: str, fundamental: Mapping[str, Any], peers: list[dict[str, float]], price: float | None) -> dict[str, Any]:
    cap = _finite(fundamental.get("market_cap")); shares = _finite(fundamental.get("shares_outstanding"))
    if cap is None and price and shares:
        cap = price * shares
    if shares is None and cap and price:
        shares = cap / price
    bridges: list[dict[str, Any]] = []
    fields = [("sales", "revenue_ttm", "ps"), ("earnings", "net_income_ttm", "pe"), ("free_cash_flow", "free_cash_flow_ttm", "pfcf"), ("book", "stockholders_equity", "pb")]
    for name, base_key, multiple_key in fields:
        base = _finite(fundamental.get(base_key)); multiples = [p.get(multiple_key) for p in peers if p.get(multiple_key) is not None]
        if base is None or base <= 0 or len(multiples) < 5:
            continue
        q25, q50, q75 = (_quantile(multiples, q) for q in (0.25, 0.50, 0.75))
        if None in (q25, q50, q75):
            continue
        bridges.append({
            "name": f"peer_{name}_bridge", "base_value": base, "multiple_low": q25, "multiple_base": q50, "multiple_high": q75,
            "implied_cap_low": base * float(q25), "implied_cap_base": base * float(q50), "implied_cap_high": base * float(q75),
            "peer_count": len(multiples), "claim_limit": "Cross-sectional current peer anchor; not historical proof or analyst consensus.",
        })
    if not bridges or not shares or shares <= 0 or not price or price <= 0:
        return {"valid": False, "state": "WATCH_VALUE_BRIDGE_INCOMPLETE", "current_price": price, "bridges": bridges, "reason": "Current price, shares and at least one peer value bridge are required."}
    lows = [b["implied_cap_low"] for b in bridges]; bases = [b["implied_cap_base"] for b in bridges]; highs = [b["implied_cap_high"] for b in bridges]
    low_cap, base_cap, high_cap = _median(lows), _median(bases), _median(highs)
    assert low_cap is not None and base_cap is not None and high_cap is not None
    # Keep scenario ranges finite and prevent a single malformed provider field from generating absurd orders.
    low_cap = max(cap * 0.35 if cap else 0.0, min(low_cap, cap * 1.75 if cap else low_cap))
    base_cap = max(cap * 0.45 if cap else 0.0, min(base_cap, cap * 2.25 if cap else base_cap))
    high_cap = max(base_cap, min(high_cap, cap * 3.0 if cap else high_cap))
    target_low, target_base, target_high = low_cap / shares, base_cap / shares, high_cap / shares
    expected = 0.25 * target_low + 0.50 * target_base + 0.25 * target_high
    return {
        "valid": True, "state": "CURRENT_PEER_VALUE_BRIDGE", "current_price": price,
        "target_low": target_low, "target_base": target_base, "target_high": target_high,
        "expected_target_price": expected, "expected_return": expected / price - 1.0,
        "low_return": target_low / price - 1.0, "high_return": target_high / price - 1.0,
        "implied_market_cap_low": low_cap, "implied_market_cap_base": base_cap, "implied_market_cap_high": high_cap,
        "current_market_cap": cap, "bridges": bridges, "horizon_days": 180,
        "calibration_state": "UNPROVEN_CURRENT_RESEARCH_BRIDGE",
        "claim_limit": "Scenario bridge for research/shadow use. It has not passed exact-ticker blind/prospective proof.",
    }


def _equity_components(f: Mapping[str, Any], projection: Mapping[str, Any], research: Mapping[str, Any], macro: Mapping[str, Any]) -> dict[str, Any]:
    rev_yoy = _finite(f.get("revenue_yoy")); ni_yoy = _finite(f.get("net_income_yoy")); rev = _finite(f.get("revenue_ttm")); fcf = _finite(f.get("free_cash_flow_ttm")); debt = _finite(f.get("total_debt")); cash = _finite(f.get("cash")); cap = _finite(f.get("market_cap"))
    quality = _mean([
        _signed_scale(rev_yoy, 0.25), _signed_scale(ni_yoy, 0.35),
        _signed_scale((fcf / rev) if fcf is not None and rev and rev > 0 else None, 0.20),
        _signed_scale(((cash or 0.0) - (debt or 0.0)) / cap if cap and cap > 0 else None, 0.50),
    ])
    expected_return = _finite(projection.get("expected_return")) if projection.get("valid") else None
    valuation = _signed_scale(expected_return, 0.50)
    causal = 0.0
    if research.get("chains"):
        active = any(str(c.get("trigger_status") or "").upper() in {"ACTIVE", "PRE_HALVING_AND_AI_PIVOT", "IN_PROGRESS"} for c in research.get("chains") if isinstance(c, Mapping))
        causal += 0.45 if active else 0.15
    if research.get("bottleneck_reference"): causal += 0.25
    if research.get("idx_groups"): causal += 0.05
    causal = _clip(causal)
    return {"fundamental": quality, "valuation": valuation, "causal": causal, "macro": _finite(macro.get("risk_asset_score")), "flow": None}


def _crypto_projection(ticker: str, network: Mapping[str, Any], all_assets: Mapping[str, Any], price: float | None) -> dict[str, Any]:
    cap = _finite(network.get("market_cap_usd")); supply = _finite(network.get("supply")); fees = _finite(network.get("fees_30d_usd")); revenue = _finite(network.get("revenue_30d_usd"))
    if not cap or not supply or not price:
        return {"valid": False, "state": "WATCH_VALUE_CAPTURE_INCOMPLETE", "current_price": price, "reason": "Market cap, supply and current price are required."}
    peer_ratios: list[float] = []
    for raw in all_assets.values():
        if not isinstance(raw, Mapping): continue
        pcap = _finite(raw.get("market_cap_usd")); pfees = _finite(raw.get("fees_30d_usd")); prev = _finite(raw.get("revenue_30d_usd")); activity = prev if prev and prev > 0 else pfees
        if pcap and activity and activity > 0:
            peer_ratios.append(pcap / (activity * 12.0))
    activity = revenue if revenue and revenue > 0 else fees
    if not activity or len(peer_ratios) < 4:
        return {"valid": False, "state": "WATCH_VALUE_CAPTURE_INCOMPLETE", "current_price": price, "reason": "Usable fees/revenue and at least four peer anchors are required."}
    q25, q50, q75 = (_quantile(peer_ratios, q) for q in (0.25, 0.50, 0.75))
    assert q25 is not None and q50 is not None and q75 is not None
    annual = activity * 12.0
    low_cap = max(cap * 0.30, min(annual * q25, cap * 1.75)); base_cap = max(cap * 0.40, min(annual * q50, cap * 2.25)); high_cap = max(base_cap, min(annual * q75, cap * 3.0))
    low, base, high = low_cap / supply, base_cap / supply, high_cap / supply
    expected = 0.25 * low + 0.50 * base + 0.25 * high
    return {
        "valid": True, "state": "CURRENT_PROTOCOL_VALUE_CAPTURE_BRIDGE", "current_price": price,
        "target_low": low, "target_base": base, "target_high": high, "expected_target_price": expected,
        "expected_return": expected / price - 1.0, "low_return": low / price - 1.0, "high_return": high / price - 1.0,
        "current_market_cap": cap, "implied_market_cap_low": low_cap, "implied_market_cap_base": base_cap, "implied_market_cap_high": high_cap,
        "horizon_days": 180, "peer_count": len(peer_ratios), "calibration_state": "UNPROVEN_CURRENT_RESEARCH_BRIDGE",
        "claim_limit": "Protocol fee/revenue peer bridge for research/shadow use; token value attribution and prospective proof remain required.",
    }


def _crypto_components(network: Mapping[str, Any], projection: Mapping[str, Any], research: Mapping[str, Any], macro: Mapping[str, Any]) -> dict[str, Any]:
    usage = _mean([_signed_scale(_finite(network.get("active_addresses_30d_growth")), 0.35), _signed_scale(_finite(network.get("transactions_30d_growth")), 0.35)])
    valuation = _signed_scale(_finite(projection.get("expected_return")), 0.75) if projection.get("valid") else None
    causal = 0.45 if research.get("chains") else 0.0
    return {"fundamental": usage, "valuation": valuation, "causal": causal, "macro": _finite(macro.get("risk_asset_score")), "flow": None}


def _scenario_projection(price: float | None, score: float | None, market: str) -> dict[str, Any]:
    if not price or score is None:
        return {"valid": False, "state": "WATCH_SCENARIO_INPUT_INCOMPLETE", "current_price": price}
    horizon = 90 if market in {"commodity", "fx"} else 180
    amplitude = 0.18 if market == "commodity" else 0.08
    center = _clip(score) * amplitude
    dispersion = 0.12 if market == "commodity" else 0.05
    low = price * max(0.05, 1.0 + center - dispersion)
    base = price * max(0.05, 1.0 + center)
    high = price * max(0.05, 1.0 + center + dispersion)
    expected = 0.25 * low + 0.50 * base + 0.25 * high
    return {
        "valid": True, "state": "CURRENT_MACRO_PHYSICAL_SCENARIO_BRIDGE", "current_price": price,
        "target_low": low, "target_base": base, "target_high": high, "expected_target_price": expected,
        "expected_return": expected / price - 1.0, "low_return": low / price - 1.0, "high_return": high / price - 1.0,
        "horizon_days": horizon, "calibration_state": "UNPROVEN_CURRENT_RESEARCH_BRIDGE",
        "claim_limit": "Fixed economic/physical scenario translation for research/shadow use; not a calibrated market-price model.",
    }


def _commodity_score(ticker: str, current: Mapping[str, Any], macro: Mapping[str, Any]) -> tuple[float | None, dict[str, Any]]:
    t = ticker.upper()
    growth = _finite(macro.get("growth_score")); usd = _finite(macro.get("usd_relief_score")); real = _finite(macro.get("real_rate_relief_score")); liquidity = _finite(macro.get("liquidity_score"))
    details: dict[str, Any] = {}
    if "GOLD" in t:
        score = _mean([real, usd, liquidity]); details = {"real_rate_relief": real, "usd_relief": usd, "liquidity": liquidity}
    elif "COPPER" in t:
        score = _mean([growth, usd]); details = {"growth": growth, "usd_relief": usd}
    elif "WTI" in t or "BRENT" in t:
        inventory = _signed_scale(-(_change(current, "WCESTUS1", "pct_change_3") or 0.0), 0.08) if _change(current, "WCESTUS1", "pct_change_3") is not None else None
        score = _mean([growth, usd, inventory]); details = {"growth": growth, "usd_relief": usd, "inventory_tightness": inventory}
    elif "NATGAS" in t:
        score = _mean([growth, usd]); details = {"growth": growth, "usd_relief": usd}
    else:
        score = _mean([growth, usd]); details = {"growth": growth, "usd_relief": usd}
    return score, details


def _fx_score(ticker: str, current: Mapping[str, Any], macro: Mapping[str, Any]) -> tuple[float | None, dict[str, Any]]:
    t = ticker.upper().replace("_REFERENCE", "")
    fed = _level(current, "DFF"); usd_relief = _finite(macro.get("usd_relief_score"))
    policy_map = {"EURUSD": _level(current, "ECBDFR"), "GBPUSD": _level(current, "IRSTCI01GBM156N"), "AUDUSD": _level(current, "IRSTCI01AUM156N"), "USDCAD": _level(current, "IRSTCI01CAM156N"), "USDJPY": _level(current, "IRSTCI01JPM156N")}
    foreign = policy_map.get(t)
    diff = None
    if fed is not None and foreign is not None:
        raw = (foreign - fed) / 5.0
        diff = -raw if t.startswith("USD") else raw
    usd_component = (-usd_relief if t.startswith("USD") else usd_relief) if usd_relief is not None else None
    if t == "USDIDR":
        # No Indonesia policy series is bundled in the current minimum route; use USD/global risk context only.
        score = _mean([-(_finite(macro.get("risk_asset_score")) or 0.0), -usd_relief if usd_relief is not None else None])
    else:
        score = _mean([diff, usd_component])
    return score, {"policy_differential_component": diff, "usd_component": usd_component, "pair": t}


def _weighted_score(components: Mapping[str, Any], weights: Mapping[str, float]) -> tuple[float | None, float]:
    used: list[tuple[float, float]] = []
    for key, weight in weights.items():
        value = _finite(components.get(key))
        if value is not None:
            used.append((value, float(weight)))
    if not used:
        return None, 0.0
    total = sum(weight for _, weight in used)
    return sum(value * weight for value, weight in used) / total, total


def _risk_plan(price: float | None, projection: Mapping[str, Any], direction: str, *, equity: float, risk_fraction: float, max_notional_fraction: float) -> dict[str, Any]:
    if not price or not projection.get("valid") or direction not in {"LONG_BIAS", "SHORT_BIAS"}:
        return {"valid": False, "state": "NO_EXECUTABLE_RESEARCH_PLAN", "entry": price, "quantity": 0.0, "notional": 0.0}
    low = _finite(projection.get("target_low")); base = _finite(projection.get("target_base")); high = _finite(projection.get("target_high")); expected = _finite(projection.get("expected_target_price"))
    if None in (low, base, high, expected):
        return {"valid": False, "state": "SCENARIO_TARGETS_MISSING", "entry": price, "quantity": 0.0, "notional": 0.0}
    if direction == "LONG_BIAS":
        target = max(price, float(expected)); scenario_stop = min(price * 0.94, float(low))
        stop = max(price * 0.80, scenario_stop)
        upside = target - price; downside = price - stop
    else:
        target = min(price, float(expected)); scenario_stop = max(price * 1.06, float(high))
        stop = min(price * 1.20, scenario_stop)
        upside = price - target; downside = stop - price
    rr = upside / downside if downside > 0 else None
    risk_budget = max(0.0, equity * risk_fraction)
    qty_risk = risk_budget / downside if downside > 0 else 0.0
    qty_cap = equity * max_notional_fraction / price
    qty = max(0.0, min(qty_risk, qty_cap))
    return {
        "valid": bool(qty > 0 and rr is not None), "state": "RESEARCH_ORDER_PLAN", "side": "BUY" if direction == "LONG_BIAS" else "SELL",
        "entry": price, "stop": stop, "target": target, "scenario_low": low, "scenario_base": base, "scenario_high": high,
        "reward_risk": rr, "risk_budget": risk_budget, "quantity": qty, "notional": qty * price,
        "risk_fraction_of_equity": risk_fraction, "max_notional_fraction": max_notional_fraction,
        "invalidation": "Re-evaluate when the fundamental/physical/protocol assumptions behind the low/high scenario are invalidated; the stop is a hard loss-control reference, not a chart signal.",
    }


def _proof_valid(packet: Mapping[str, Any]) -> bool:
    proof = packet.get("proof_data") if isinstance(packet.get("proof_data"), Mapping) else {}
    return bool(proof.get("market_proof_valid") is True)


def action_for_packet(packet: Mapping[str, Any], current: Mapping[str, Any], policy: Mapping[str, Any], peers: Mapping[str, list[dict[str, float]]], macro: Mapping[str, Any]) -> dict[str, Any]:
    market = str(packet.get("market") or ""); ticker = str(packet.get("ticker") or "")
    quote_raw = ((((current.get("quotes") or {}).get("markets") or {}).get(market) or {}).get(ticker))
    qstate = quote_state(quote_raw if isinstance(quote_raw, Mapping) else None, market)
    price = qstate.get("price")
    research = packet.get("research_context") if isinstance(packet.get("research_context"), Mapping) else {}
    weights = ((policy.get("research_action") or {}).get("weights") or {})
    components: dict[str, Any]; projection: dict[str, Any]
    inputs: dict[str, Any] = {"quote": qstate}
    if market in {"us", "idx"}:
        f = (((current.get("fundamentals") or {}).get("markets") or {}).get(market) or {}).get(ticker)
        fundamental = f if isinstance(f, Mapping) else {}
        projection = _equity_projection(ticker, market, fundamental, peers.get(market, []), price)
        components = _equity_components(fundamental, projection, research, macro)
        inputs["fundamental"] = fundamental
    elif market == "crypto":
        assets = ((current.get("crypto_network") or {}).get("assets") or {})
        network = assets.get(ticker) if isinstance(assets, Mapping) else {}
        network = network if isinstance(network, Mapping) else {}
        projection = _crypto_projection(ticker, network, assets if isinstance(assets, Mapping) else {}, price)
        components = _crypto_components(network, projection, research, macro)
        inputs["protocol"] = network
    elif market == "commodity":
        score, details = _commodity_score(ticker, current, macro)
        projection = _scenario_projection(price, score, market)
        components = {"fundamental": score, "valuation": _signed_scale(_finite(projection.get("expected_return")), 0.25) if projection.get("valid") else None, "causal": 0.15 if research.get("chains") else 0.0, "macro": score, "flow": None}
        inputs["physical_macro"] = details
    else:
        score, details = _fx_score(ticker, current, macro)
        projection = _scenario_projection(price, score, market)
        components = {"fundamental": score, "valuation": _signed_scale(_finite(projection.get("expected_return")), 0.12) if projection.get("valid") else None, "causal": 0.0, "macro": score, "flow": None}
        inputs["relative_macro"] = details
    score, weight_coverage = _weighted_score(components, weights)
    thresholds = (policy.get("research_action") or {}).get("thresholds") or {}
    long_t = float(thresholds.get("long_bias", 0.28)); short_t = float(thresholds.get("short_bias", -0.28))
    minimum_weight = float(thresholds.get("minimum_weight_coverage", 0.45))
    if score is None or weight_coverage < minimum_weight:
        direction = "WATCH"
    elif score >= long_t:
        direction = "LONG_BIAS"
    elif score <= short_t:
        direction = "SHORT_BIAS"
    else:
        direction = "WATCH"
    observed_inputs = sum(_finite(v) is not None for v in components.values())
    data_quality = min(100, int(round(20 * observed_inputs + 20 * min(1.0, weight_coverage))))
    confidence = min(0.85, max(0.0, abs(score or 0.0) * min(1.0, weight_coverage)))
    account = policy.get("account") or {}; equity = float(account.get("equity") or os.getenv("WARROOM_ACCOUNT_EQUITY", "10000"))
    shadow_policy = policy.get("shadow_trading") or {}; risk_fraction = float(shadow_policy.get("risk_fraction", 0.0025)); max_notional = float(shadow_policy.get("max_notional_fraction", 0.10))
    risk = _risk_plan(price, projection, direction, equity=equity, risk_fraction=risk_fraction, max_notional_fraction=max_notional)
    min_quality = int(shadow_policy.get("minimum_data_quality", 55)); min_rr = float(shadow_policy.get("minimum_reward_risk", 1.25)); min_abs_score = float(shadow_policy.get("minimum_absolute_score", 0.28))
    shadow_eligible = bool(qstate.get("fresh") and direction in {"LONG_BIAS", "SHORT_BIAS"} and projection.get("valid") and data_quality >= min_quality and abs(score or 0.0) >= min_abs_score and risk.get("valid") and (_finite(risk.get("reward_risk")) or 0.0) >= min_rr)
    systematic_live = bool(shadow_eligible and _proof_valid(packet))
    exp = policy.get("experimental_manual") or {}
    env_enabled = os.getenv("WARROOM_EXPERIMENTAL_LIVE", "0").lower() in {"1", "true", "yes"}
    env_ack = os.getenv("WARROOM_EXPERIMENTAL_ACK", "") == str(exp.get("required_ack") or "")
    experimental_risk = _risk_plan(price, projection, direction, equity=equity, risk_fraction=float(exp.get("risk_fraction", 0.001)), max_notional_fraction=float(exp.get("max_notional_fraction", 0.05)))
    experimental_manual = bool(shadow_eligible and exp.get("enabled") is True and env_enabled and env_ack and experimental_risk.get("valid"))
    reasons = [f"{k}={round(float(v), 3)}" for k, v in components.items() if _finite(v) is not None]
    blockers: list[str] = []
    if not qstate.get("fresh"): blockers.append("CURRENT_QUOTE_NOT_FRESH")
    if not projection.get("valid"): blockers.append("CURRENT_VALUE_BRIDGE_INCOMPLETE")
    if direction == "WATCH": blockers.append("COMPOSITE_EDGE_BELOW_FIXED_THRESHOLD_OR_DATA_INCOMPLETE")
    if risk.get("valid") and (_finite(risk.get("reward_risk")) or 0) < min_rr: blockers.append("REWARD_RISK_BELOW_SHADOW_MINIMUM")
    if not _proof_valid(packet): blockers.append("SYSTEMATIC_LIVE_PROOF_PENDING")
    return {
        "schema": "warroom.v100.current_action.v1", "generated_at": dt.datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "market": market, "ticker": ticker, "direction": direction, "score": score, "confidence": confidence,
        "data_quality": data_quality, "weight_coverage": weight_coverage, "components": components, "reasons": reasons,
        "projection": projection, "risk_plan": risk, "experimental_manual_risk_plan": experimental_risk, "quote_state": qstate, "inputs": inputs,
        "permissions": {
            "research_action": "ACTIVE" if direction in {"LONG_BIAS", "SHORT_BIAS", "WATCH"} else "UNAVAILABLE",
            "shadow_trading": "ELIGIBLE" if shadow_eligible else "WATCH_ONLY",
            "systematic_live": "ELIGIBLE_REQUIRES_HUMAN_APPROVAL" if systematic_live else "PROOF_GATED",
            "experimental_manual": "ELIGIBLE_REQUIRES_HUMAN_APPROVAL" if experimental_manual else "DISABLED_OR_NOT_ELIGIBLE",
            "auto_submit": False,
        },
        "blockers": blockers,
        "claim_limit": "Current research action, not proven alpha. Shadow results must be collected prospectively; systematic live requires exact proof.",
    }


def load_policy(path: Path = HERE / "V100_ACTION_POLICY.json") -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("account", {})["equity"] = float(os.getenv("WARROOM_ACCOUNT_EQUITY", str((data.get("account") or {}).get("equity") or 10000)))
    data["account"]["currency"] = os.getenv("WARROOM_ACCOUNT_CURRENCY", str(data["account"].get("currency") or "USD"))
    return data


def enrich_packets(packets: Mapping[str, Mapping[str, Any]], current: Mapping[str, Any], policy: Mapping[str, Any] | None = None) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    policy = dict(policy or load_policy()); macro = macro_states(current)
    peers = {m: _equity_peer_table(current, m) for m in ("us", "idx")}
    output: dict[str, dict[str, Any]] = {m: {} for m in MARKETS}; all_rows: list[dict[str, Any]] = []
    for market in MARKETS:
        for ticker, raw in (packets.get(market) or {}).items():
            packet = dict(raw); action = action_for_packet(packet, current, policy, peers, macro)
            packet["schema"] = "warroom.v100.unified_decision_packet.v1"
            packet["current_action"] = action
            packet["decision"] = {
                **dict(packet.get("decision") or {}),
                "state": action["direction"], "direction": action["direction"], "conviction": action["confidence"],
                "research_permission": action["permissions"]["research_action"],
                "shadow_permission": action["permissions"]["shadow_trading"],
                "systematic_live_permission": action["permissions"]["systematic_live"],
                "capital_permission": "MANUAL_REVIEW_REQUIRED" if action["permissions"]["experimental_manual"].startswith("ELIGIBLE") else "PROOF_GATED",
                "blockers": action["blockers"],
            }
            packet["quote"] = {**dict(packet.get("quote") or {}), **action["quote_state"]}
            packet["fundamental_value_capture"] = {**dict(packet.get("fundamental_value_capture") or {}), "state": action["projection"].get("state"), "current_inputs": action["inputs"]}
            packet["projection"] = action["projection"]
            packet["risk_execution"] = {**action["risk_plan"], "shadow_order_state": action["permissions"]["shadow_trading"], "systematic_live_state": action["permissions"]["systematic_live"], "manual_export_only": True}
            packet["proof_data"] = {**dict(packet.get("proof_data") or {}), "current_action_claim": action["claim_limit"]}
            output[market][ticker] = packet; all_rows.append(packet)
        output[market] = dict(sorted(output[market].items(), key=lambda kv: (
            0 if kv[1]["current_action"]["permissions"]["shadow_trading"] == "ELIGIBLE" else 1,
            -abs(float(kv[1]["current_action"].get("score") or 0.0)),
            -int(kv[1]["current_action"].get("data_quality") or 0), kv[0]
        )))
    shadow = [p for p in all_rows if p["current_action"]["permissions"]["shadow_trading"] == "ELIGIBLE"]
    biases = [p for p in all_rows if p["current_action"]["direction"] in {"LONG_BIAS", "SHORT_BIAS"}]
    watch = [p for p in all_rows if p["current_action"]["direction"] == "WATCH"]
    alpha = {
        "schema": "warroom.v100.action_center.v1", "state": "SHADOW_CANDIDATES_AVAILABLE" if shadow else "RESEARCH_ACTIONS_AVAILABLE",
        "shadow_candidates": sorted(shadow, key=lambda p: abs(float(p["current_action"].get("score") or 0)), reverse=True),
        "research_biases": sorted(biases, key=lambda p: abs(float(p["current_action"].get("score") or 0)), reverse=True),
        "research_watchlist": sorted(watch, key=lambda p: int(p["current_action"].get("data_quality") or 0), reverse=True),
        "promoted": [p for p in all_rows if p["current_action"]["permissions"]["systematic_live"].startswith("ELIGIBLE")],
        "ranking_basis": "Fixed current fundamental/value/causal/macro inputs; no chart-derived ranking.",
    }
    return output, {"alpha_center": alpha, "macro_state": macro, "peer_counts": {m: len(v) for m, v in peers.items()}}
