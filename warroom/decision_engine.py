"""Structural decision-map interface, fail-closed for ticker selection.

The knowledge graph can map mechanisms and candidate exposure, but it cannot by
itself identify a 'best equity', expected return, position direction or sizing.
Those claims require company-specific value capture, pricing, costs and validated
market-specific evidence.
"""
from __future__ import annotations


def _kg():
    from warroom import knowledge_graph as KG
    return KG


THEME_NODE = {
    "AI": "AI/Compute", "Power": "Power", "Memory": "HBM", "Cooling": "Cooling",
    "Optics": "Optics/Photonics", "Defense": "Defense", "Nuclear": "Nuclear",
    "Networking": "Networking",
}


def decide_theme(theme, prices=None, fair_values=None):
    del prices, fair_values
    KG = _kg()
    node = THEME_NODE.get(theme, theme)
    chain = KG.beta_chain(node, max_hops=3) if hasattr(KG, "beta_chain") else None
    if not chain:
        return {
            "theme": theme,
            "status": "NO_MAP",
            "permission": "CAPITAL_BLOCKED",
            "error": f"no chain for '{theme}' in knowledge graph",
            "available": list(THEME_NODE.keys()),
        }

    candidates = []
    seen = set()
    for order_key, order_n in (("primary", 1), ("second_derivative", 2), ("third_derivative", 3)):
        for item in chain.get(order_key) or []:
            tk = item.get("ticker")
            if not tk or tk in seen:
                continue
            seen.add(tk)
            candidates.append({
                "ticker": tk,
                "order": order_n,
                "node": item.get("node"),
                "graph_confidence": item.get("confidence"),
                "edge_status": "STRUCTURAL_MAP_ONLY",
                "value_capture_status": "UNASSESSED",
                "pricing_status": "UNASSESSED",
                "remaining_return": None,
                "capital_permission": "BLOCKED",
            })

    mech_nodes = [node]
    for key in ("primary", "second_derivative", "third_derivative"):
        mech_nodes.extend(
            list(dict.fromkeys(i.get("node") for i in chain.get(key) or [] if i.get("node")))[:2]
        )

    return {
        "theme": theme,
        "entry_node": node,
        "best_equity": None,
        "alternative": None,
        "research_inventory": candidates,
        "mechanism": [{"node": n} for n in dict.fromkeys(mech_nodes)][:6],
        "invalidation": (
            f"Re-test the {node} causal path if demand, scarcity, qualification constraints, "
            "pricing power or downstream value capture reverse."
        ),
        "status": "RESEARCH_INVENTORY",
        "permission": "CAPITAL_BLOCKED",
        "data_complete": False,
        "note": (
            "The graph identifies exposure candidates, not a best trade. Company-level value "
            "capture, pricing, counterparty, timing, baseline lift and prospective evidence are required."
        ),
    }


def decide_all_themes(prices=None, fair_values=None):
    return {t: decide_theme(t, prices, fair_values) for t in THEME_NODE}


def shock_to_decision(shock_node, direction="up", prices=None):
    del prices
    KG = _kg()
    prop = KG.propagate(shock_node, direction=direction, max_hops=4) if hasattr(KG, "propagate") else None
    if not prop:
        return {"shock": shock_node, "status": "NO_MAP", "permission": "CAPITAL_BLOCKED"}
    exposures = []
    for step in prop.get("chain") or []:
        for tk in step.get("tickers", []):
            exposures.append({
                "ticker": tk,
                "via": step.get("node"),
                "order": step.get("order"),
                "economic_exposure": "POSITIVE" if step.get("move") == "↑" else "NEGATIVE",
                "graph_confidence": step.get("confidence"),
                "tested": step.get("tested"),
                "trade_direction": None,
                "permission": "CAPITAL_BLOCKED",
            })
    return {
        "shock": f"{shock_node} {direction}",
        "propagation": prop.get("chain"),
        "research_exposures": exposures[:12],
        "status": "STRUCTURAL_MAP_ONLY",
        "permission": "CAPITAL_BLOCKED",
        "note": "Causal exposure is not an entry, expected return or trade recommendation.",
    }
