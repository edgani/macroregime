"""Broker-route flow context, not beneficial-owner or intent inference.

This module describes observable buy/sell pressure by broker route.  It deliberately
avoids labels such as "building long", "panic selling", "distribution", or
"smart money" because broker codes do not identify the economic owner and may
contain crossings, facilitation, market making, controller transfers, or hedges.
"""
from __future__ import annotations


def _context_label(net: float, gross: float, ng: float, agg_share: float, pass_share: float) -> str:
    if gross <= 0:
        return "INACTIVE"
    if abs(ng) < 0.15:
        return "BALANCED_FLOW_CONTEXT"
    side = "BUY" if net > 0 else "SELL"
    style = "AGGRESSIVE" if agg_share >= 0.55 else "PASSIVE" if pass_share >= 0.60 else "MIXED"
    return f"{style}_NET_{side}_CONTEXT"


def run_broker_flow(brokers: list[dict], price_down: bool = True) -> dict:
    """Summarise route-level flow without claiming owner identity or intent.

    Input rows: ``broker, agg_buy, pass_buy, agg_sell, pass_sell, is_foreign?``.
    ``price_down`` is retained for API compatibility but is not used to infer intent.
    """
    del price_down
    if not brokers:
        return {
            "ok": False,
            "reason": "no broker flow data",
            "beneficial_owner": "UNVERIFIED",
            "intent": "UNVERIFIED",
        }

    rows: list[dict] = []
    for b in brokers:
        ab = float(b.get("agg_buy", 0) or 0)
        pb = float(b.get("pass_buy", 0) or 0)
        as_ = float(b.get("agg_sell", 0) or 0)
        ps = float(b.get("pass_sell", 0) or 0)
        buy, sell = ab + pb, as_ + ps
        net, gross = buy - sell, buy + sell
        ng = net / gross if gross else 0.0
        agg_share = (ab + as_) / gross if gross else 0.0
        pass_share = (pb + ps) / gross if gross else 0.0
        rows.append({
            **b,
            "net": net,
            "gross": gross,
            "ng": ng,
            "agg_share": agg_share,
            "pass_share": pass_share,
            "label": _context_label(net, gross, ng, agg_share, pass_share),
        })

    total_net = sum(r["net"] for r in rows)
    total_gross = sum(r["gross"] for r in rows)
    total_ng = total_net / total_gross if total_gross else 0.0
    if abs(total_ng) < 0.10:
        verdict = "BALANCED_FLOW_CONTEXT"
        sign = 0
    elif total_net > 0:
        verdict = "NET_BUY_CONTEXT"
        sign = 1
    else:
        verdict = "NET_SELL_CONTEXT"
        sign = -1

    gmax = max((r["gross"] for r in rows), default=0.0) or 1.0
    compact = []
    for r in rows:
        compact.append({
            "broker": r.get("broker", "?"),
            "label": r["label"],
            "net": round(float(r["net"]), 1),
            "ng": round(float(r["ng"]), 2),
            "size_pct": round(float(r["gross"] / gmax), 2),
            "is_foreign_route": bool(r.get("is_foreign")),
            "beneficial_owner": "UNVERIFIED",
            "intent": "UNVERIFIED",
        })

    return {
        "ok": True,
        "route_net": round(float(total_net), 1),
        "route_net_gross_ratio": round(float(total_ng), 3),
        "flow_sign": sign,
        "verdict": verdict,
        "beneficial_owner": "UNVERIFIED",
        "intent": "UNVERIFIED",
        "crossing": "UNKNOWN",
        "facilitation": "UNKNOWN",
        "note": (
            "Broker-route context only. It does not establish beneficial owner, "
            "accumulation/distribution, panic, or trade intent."
        ),
        "brokers": compact,
    }
