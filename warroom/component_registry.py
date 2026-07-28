"""warroom/component_registry.py — canonical component output contract (R3).

Every engine output surfaced to the UI is registered here with ONE canonical schema,
so a single engine cannot have two conflicting output versions and every panel can be
traced to source / as-of / freshness / proof status / execution eligibility.

This module ANNOTATES existing compute() outputs; it does not change any formula.
"""
from __future__ import annotations

CANONICAL_FIELDS = [
    "component_id", "market", "instrument", "as_of", "source", "data_state",
    "freshness", "value", "confidence", "horizon", "drivers",
    "disconfirming", "invalidation", "claim_limit", "proof_status",
    "execution_eligible",
]

DATA_STATES = {"CURRENT", "STALE_LAST_KNOWN", "HISTORICAL_REFERENCE", "PARTIAL",
               "NO_DATA", "ERROR", "TEST_FIXTURE"}

PROOF_STATUSES = {"MAPPED", "DATA_ADMITTED", "HISTORICAL_OOS_PASS", "BLIND_LOCKBOX_PASS",
                  "SHADOW_READY", "PROSPECTIVE_PASS", "LIMITED_LIVE_READY",
                  "SYSTEMATIC_LIVE_READY", "RESEARCH_ONLY", "REJECTED", "UNAVAILABLE"}

# proof annotations per component (honest labels; software PASS != alpha proven)
_PROOF = {
    "us_sma10_risk_overlay": "HISTORICAL_OOS_PASS",   # v66 trail; prospective pending
    "crash_meter": "RESEARCH_ONLY",
}


def _data_state(d):
    asof = d.get("data_asof") or {}
    stale = asof.get("stale_days")
    if stale is None:
        return "NO_DATA"
    return "STALE_LAST_KNOWN" if stale > 7 else "CURRENT"


def _comp(component_id, d, market, value, source, confidence=None, horizon=None,
          instrument=None, drivers=None, disconfirming=None, invalidation=None,
          claim_limit=None, proof_status=None, execution_eligible=False):
    asof = d.get("data_asof") or {}
    return {
        "component_id": component_id,
        "market": market,
        "instrument": instrument,
        "as_of": asof.get("date"),
        "source": source,
        "data_state": _data_state(d),
        "freshness": (f"{asof.get('stale_days')}d old" if asof.get("stale_days") is not None else "unknown"),
        "value": value,
        "confidence": confidence,
        "horizon": horizon,
        "drivers": drivers,
        "disconfirming": disconfirming,
        "invalidation": invalidation,
        "claim_limit": claim_limit,
        "proof_status": proof_status or _PROOF.get(component_id, "RESEARCH_ONLY"),
        "execution_eligible": bool(execution_eligible),
    }


def build(d: dict) -> list:
    """Register every compute() output surfaced to the UI. One entry per component."""
    reg = d.get("regime") or {}
    rt = d.get("regime_transition") or {}
    comps = []

    comps.append(_comp("gip_structural_quad", d, "global", reg.get("structural"),
                       "engines.gip_engine", confidence=reg.get("struct_probs"),
                       horizon="structural (6-18mo)",
                       claim_limit="state estimate, not an asset mapping"))
    comps.append(_comp("gip_tactical_quad", d, "global", reg.get("monthly"),
                       "engines.gip_engine", confidence=reg.get("month_probs"),
                       horizon="tactical (1-3mo)",
                       claim_limit="fast-horizon state, mean-reverts"))
    comps.append(_comp("regime_transition", d, "global", rt.get("stage"),
                       "engines.regime_transition_engine",
                       drivers=rt.get("drivers"), horizon="transition window",
                       invalidation="fast horizon re-aligns with structural",
                       claim_limit="ripeness gauge, not a timing guarantee"))
    comps.append(_comp("quad_explainer", d, "global", (d.get("explain") or "")[:200] or None,
                       "engines.quad_explainer",
                       claim_limit="base-rate playbook, conditional not static"))

    cm = d.get("crash_meter") or {}
    comps.append(_comp("crash_meter", d, "global", cm.get("value"),
                       "warroom.crash_meter", horizon="multi (see horizons)",
                       drivers=cm.get("drivers"), disconfirming=cm.get("disconfirming"),
                       invalidation=cm.get("invalidation"), claim_limit=cm.get("claim_limit"),
                       proof_status="RESEARCH_ONLY", execution_eligible=False))

    cb = d.get("crash") or {}
    comps.append(_comp("crash_bottom_pressure", d, "us", cb.get("pressure"),
                       "gcfis.engines.crash_bottom", drivers=list((cb.get("components") or {}).keys())[:6],
                       claim_limit="bottom-pressure reading, tested on US panel"))

    cl = (d.get("crash_lead") or {}).get("crash_lead") or {}
    comps.append(_comp("crash_lead_time", d, "us", cl.get("risk_level"),
                       "warroom.crash_lead", horizon="12-36mo",
                       claim_limit=cl.get("honest_note")))

    ew = d.get("early_warning") or {}
    fg = ew.get("fear_greed") or {}
    comps.append(_comp("fear_greed", d, "us", fg.get("value"),
                       "warroom.early_warning", confidence=fg.get("confidence"),
                       claim_limit="fear leg tested p<0.001; greed leg weak (flagged)"))

    comps.append(_comp("market_health", d, "us",
                       {"breadth": d.get("breadth"), "posture": d.get("posture"), "hmm": d.get("hmm")},
                       "warroom.compute breadth/posture + gcfis.regime_hmm",
                       claim_limit="descriptive state, not a forecast"))

    comps.append(_comp("shock_state", d, "global", d.get("shock_prob"),
                       "warroom.compute (VIX buckets)",
                       claim_limit="bucket label, not a shock probability model"))

    mc = d.get("meters_computed") or {}
    for key in ("trend", "credit", "bubble", "wealth", "liquidity"):
        m = mc.get(key) or {}
        comps.append(_comp(f"meter_{key}", d, "us", m.get("value"),
                           "warroom.meters",
                           claim_limit="price-proxy composite; thresholds are calibratable priors",
                           proof_status="RESEARCH_ONLY" if not m.get("real") else "MAPPED"))

    fs = d.get("funding") or {}
    comps.append(_comp("funding_stress", d, "global", fs.get("score"),
                       "warroom.funding_stress", confidence=fs.get("source"),
                       claim_limit="FRED-backed when keyed; synthetic-flagged otherwise"))

    pol = d.get("policy") or {}
    comps.append(_comp("policy_stance", d, "global", pol.get("stance") or pol.get("label"),
                       "warroom.policy", claim_limit="synthesis of rates/oil/income inputs"))

    carry = (d.get("fx") or {}).get("carry")
    comps.append(_comp("fx_carry", d, "fx",
                       {"stage": (carry or {}).get("stage"), "pairs": len((carry or {}).get("pairs", []) or [])} if carry else None,
                       "engines.fx_carry_engine / feeds.fx_carry",
                       claim_limit="spread minus basis/vol/stress; high yield alone is not a buy",
                       proof_status="RESEARCH_ONLY"))

    chains = d.get("causal_chains") or []
    comps.append(_comp("causal_chains", d, "global", f"{len(chains)} active chains",
                       "warroom.causal_chain + data/chain_reactions.json",
                       claim_limit="mapped transmission paths, outcome evidence varies"))

    ba = d.get("batch_a") or {}
    for key, cid in (("transmission", "transmission"), ("cascade", "cascade"),
                     ("seasonality", "seasonality"), ("frontrun", "front_run"),
                     ("reflexivity", "reflexivity"), ("boombust", "boom_bust")):
        v = ba.get(key)
        comps.append(_comp(cid, d, "global",
                           "populated" if v else None,
                           f"engines.{key}_engine",
                           proof_status="RESEARCH_ONLY" if v else "UNAVAILABLE"))

    conv = d.get("conviction") or []
    comps.append(_comp("alpha_ranking", d, "global", f"{len(conv)} conviction / {d.get('ranked', 0)} ranked",
                       "warroom.compute _rank + engines.alpha_scanner",
                       claim_limit="relative ranking on price proxies; not alpha proof",
                       proof_status="RESEARCH_ONLY"))

    wl = d.get("watchlist") or []
    comps.append(_comp("watch_universe", d, "global", f"{len(wl)} names",
                       "warroom.compute",
                       claim_limit="WATCH is not alpha; zero capital weight"))

    dm = d.get("decision_market") or {}
    n_excl = sum(1 for m in dm.values() for c in (m.get("candidates") or []) if c.get("status"))
    comps.append(_comp("decision_market", d, "global",
                       f"{len(dm)} thesis buckets, {n_excl} gated candidates",
                       "warroom.market_cap_target",
                       claim_limit="MODEL_REQUIRED: no EV ranking until calibrated evidence",
                       proof_status="MAPPED"))

    val = d.get("validation") or {}
    comps.append(_comp("walkforward_gate", d, "global",
                       f"{val.get('passed', 0)}/{val.get('checked', 0)} pass",
                       "warroom.walkforward",
                       claim_limit="historical gate; prospective proof separate"))

    risk = d.get("risk") or {}
    comps.append(_comp("portfolio_risk", d, "global",
                       f"{risk.get('n', 0)} sized positions",
                       "warroom.risk", claim_limit="shadow book only; no live capital"))

    comps.append(_comp("us_sma10_risk_overlay", d, "us", "active (risk cap only, zero alpha weight)",
                       "inherited overlay",
                       claim_limit="US broad-equity risk overlay only; not generalized",
                       proof_status=_PROOF["us_sma10_risk_overlay"]))

    return comps


def validate(components) -> list:
    """Schema validation. Returns list of error strings (empty = pass)."""
    errors = []
    seen = set()
    for c in components:
        cid = c.get("component_id")
        if not cid:
            errors.append("component without component_id")
            continue
        if cid in seen:
            errors.append(f"duplicate component_id: {cid}")
        seen.add(cid)
        for f in CANONICAL_FIELDS:
            if f not in c:
                errors.append(f"{cid}: missing field {f}")
        if c.get("data_state") not in DATA_STATES:
            errors.append(f"{cid}: bad data_state {c.get('data_state')}")
        if c.get("proof_status") not in PROOF_STATUSES:
            errors.append(f"{cid}: bad proof_status {c.get('proof_status')}")
        if c.get("data_state") == "STALE_LAST_KNOWN" and c.get("execution_eligible"):
            errors.append(f"{cid}: stale output must not be execution_eligible")
        if not isinstance(c.get("execution_eligible"), bool):
            errors.append(f"{cid}: execution_eligible must be bool")
    return errors
