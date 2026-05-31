"""regime_transition_engine.py — Quad transition detector."""
def run_regime_transition(gip_result):
    if not gip_result or not isinstance(gip_result, dict):
        return {"transitioning": False}
    current = gip_result.get("current_quad", "Q3")
    nowcast = gip_result.get("nowcast_quad", current)
    probs = gip_result.get("probabilities", {})
    if isinstance(probs, dict) and probs:
        sorted_p = sorted(probs.items(), key=lambda x: -x[1])
        top_prob = sorted_p[0][1] if sorted_p else 0
        runner_up = sorted_p[1][1] if len(sorted_p) > 1 else 0
        conviction = top_prob - runner_up
    else:
        conviction = 0.5
    return {"transitioning": current != nowcast,
            "from": current, "to": nowcast,
            "conviction": round(conviction, 3),
            "label": f"{current} → {nowcast}" if current != nowcast else f"Stable in {current}"}
