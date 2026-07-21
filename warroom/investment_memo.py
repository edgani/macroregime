"""Company research inventory, not an automated investment recommendation."""
from __future__ import annotations
import json
import os

_REF = None


def _ref():
    global _REF
    if _REF is None:
        try:
            with open(os.path.join(os.path.dirname(__file__), "..", "data", "bottleneck_reference.json"), encoding="utf-8") as f:
                _REF = json.load(f)
        except Exception:
            _REF = {}
    return _REF


def memo(ticker, price=None, market_cap=None, fair_value=None):
    del fair_value
    ref = _ref()
    tk = (ticker or "").upper()
    out = {
        "ticker": tk,
        "status": "RESEARCH_INVENTORY",
        "capital_permission": "BLOCKED",
        "expected_market_cap": None,
        "convexity": None,
        "alpha_tier": "UNASSESSED",
        "decision": None,
    }

    rec = next((r for r in ref.get("consensus_heatmap", []) if (r.get("ticker") or "").upper() == tk), None)
    if rec:
        out.update({
            "role": rec.get("role"),
            "layer": rec.get("layer"),
            "research_stars": rec.get("stars"),
            "priority": rec.get("priority"),
            "research_stars_note": "curated research metadata; not probability or sizing",
        })

    try:
        from warroom import knowledge_graph as KG
        node = next((n for n, tks in KG.NODE_TICKERS.items() if tk in tks), None)
        if node:
            out["chain_node"] = node
            nb = KG.node_neighbors(node)
            out["supply_drivers"] = [u["from"] for u in nb.get("upstream", [])][:5]
            out["demand_drivers"] = [d["to"] for d in nb.get("downstream", [])][:5]
            bc = KG.beta_chain(node, 3)
            out["exposure_candidates"] = (
                [b["ticker"] for b in bc.get("primary", [])] +
                [b["ticker"] for b in bc.get("second_derivative", [])]
            )[:6]
    except Exception:
        pass

    from warroom import market_cap_target as MC
    model = MC.build(tk, price, market_cap, 60)
    out["valuation_model"] = {
        "status": model.get("status"),
        "permission": model.get("permission"),
        "reason": model.get("reason"),
        "required_evidence": model.get("required_evidence"),
    }

    cats = [c for c in ref.get("catalyst_timeline", []) if (c.get("ticker") or "").upper() == tk]
    if cats:
        out["catalysts"] = [
            {"quarter": c.get("quarter"), "event": c.get("event"), "priority": c.get("priority")}
            for c in cats
        ]

    out["invalidation"] = (
        "Define company-specific invalidation for demand, supply response, pricing power, "
        "value capture, balance-sheet capacity and market recognition before promotion."
    )
    out["next_falsifier"] = (
        "Reproduce one company-level value-capture bridge using point-in-time filings and compare "
        "it with a strong market-specific baseline."
    )
    out["_completeness"] = _completeness(out)
    return out


def _completeness(m):
    fields = ["role", "chain_node", "supply_drivers", "demand_drivers", "catalysts", "invalidation", "next_falsifier"]
    have = sum(bool(m.get(f)) for f in fields)
    return {
        "filled": have,
        "total": len(fields),
        "pct": round(have / len(fields) * 100),
        "note": "research inventory completeness; not confidence, probability or expected return",
    }


def memo_batch(tickers, prices=None, fair_values=None):
    prices = prices or {}
    fair_values = fair_values or {}
    return {
        t: memo(t, prices.get(t), (fair_values.get(t) or {}).get("market_cap"), fair_values.get(t))
        for t in tickers
    }
