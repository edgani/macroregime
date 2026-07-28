"""warroom/crash_meter.py — Crash Meter 0-100 decision-severity gauge.

Composes the master-prompt subcomponents from EXISTING compute outputs (no new alpha
formula, no fabricated inputs). Subcomponents whose data does not exist are reported
as NO_DATA — never as 0. The composite is a transparent coverage-weighted mean of the
available subcomponents, labelled as what it is:

  SEVERITY GAUGE, NOT A CALIBRATED PROBABILITY.
  proof_status = RESEARCH_ONLY until R5 calibration (PR-AUC, Brier, false-alarm,
  lead-time, drawdown-capture) passes on prospective evidence.
  execution_eligible = False (capital weight 0).

Prior rejected variant: cusp-fragility predictive crash model (V73-V75, REJECTED).
This gauge does not revive it; it aggregates stress observables.
"""
from __future__ import annotations

COMPONENT_KEYS = [
    "liquidity", "credit", "funding", "leverage", "crowding", "volatility",
    "cross_asset", "macro", "policy", "physical", "carry_unwind", "market_response",
]

_NO_DATA = {"value": None, "state": "NO_DATA", "basis": "feed not wired — not counted"}


def _num(x):
    try:
        v = float(x)
        return v if 0.0 <= v <= 100.0 else None
    except (TypeError, ValueError):
        return None


def _meter_value(mc, key):
    m = (mc or {}).get(key) or {}
    v = _num(m.get("value"))
    if v is None or not m.get("real", True):
        return dict(_NO_DATA)
    return {"value": round(v), "state": "CURRENT", "basis": m.get("status", "price-proxy meter")}


def build(d: dict) -> dict:
    mc = d.get("meters_computed") or {}
    asof = d.get("data_asof") or {}
    subs = {}

    # liquidity / credit / bubble-as-leverage-proxy / wealth are price-proxy meters
    subs["liquidity"] = _meter_value(mc, "liquidity")
    subs["credit"] = _meter_value(mc, "credit")
    subs["leverage"] = dict(_NO_DATA)  # margin-debt / leverage feed not wired

    # funding stress (FRED-backed when available)
    fs = d.get("funding") or {}
    v = _num(fs.get("score"))
    subs["funding"] = ({"value": round(v), "state": "CURRENT", "basis": f"funding stress ({fs.get('source', '?')})"}
                       if v is not None else dict(_NO_DATA))

    # crowding
    cm = d.get("crowd_market") or {}
    v = _num(cm.get("crowding") or cm.get("score") or cm.get("value"))
    subs["crowding"] = ({"value": round(v), "state": "CURRENT", "basis": "market crowding proxy"}
                        if v is not None else dict(_NO_DATA))

    # volatility / options stress from VIX (10..50 -> 0..100)
    vix = d.get("vix")
    if isinstance(vix, (int, float)):
        subs["volatility"] = {"value": round(max(0.0, min(100.0, (float(vix) - 10.0) * 2.5))),
                              "state": "CURRENT", "basis": f"VIX {vix}"}
    else:
        subs["volatility"] = dict(_NO_DATA)

    # cross-asset dislocation from macro_regime risk regime
    mr = d.get("macro_regime") or {}
    rr = mr.get("risk_regime") or {}
    v = _num(rr.get("score"))
    subs["cross_asset"] = ({"value": round(v), "state": "CURRENT",
                            "basis": f"cross-asset risk regime ({rr.get('label', '?')})"}
                           if v is not None else dict(_NO_DATA))

    # macro deterioration: defensive quad + low breadth => stress
    reg = d.get("regime") or {}
    breadth = d.get("breadth")
    if reg.get("structural") and isinstance(breadth, (int, float)):
        quad_stress = {"Quad 1": 15, "Quad 2": 30, "Quad 3": 65, "Quad 4": 80}.get(reg.get("structural"), 50)
        v = 0.6 * quad_stress + 0.4 * max(0.0, min(100.0, 100.0 - float(breadth)))
        subs["macro"] = {"value": round(v), "state": "CURRENT",
                         "basis": f"{reg.get('structural')} + breadth {breadth}%"}
    else:
        subs["macro"] = dict(_NO_DATA)

    # policy shock
    pol = d.get("policy") or {}
    v = _num(pol.get("stress") or pol.get("score"))
    subs["policy"] = ({"value": round(v), "state": "CURRENT", "basis": pol.get("label", "policy synthesis")}
                      if v is not None else dict(_NO_DATA))

    # physical shock (inventory / supply feeds not wired)
    subs["physical"] = dict(_NO_DATA)

    # carry unwind warning from fx carry stress
    carry = (d.get("fx") or {}).get("carry") or {}
    v = _num(carry.get("stress") or carry.get("unwind_risk") or carry.get("stress_score"))
    if v is None and isinstance(carry.get("stage"), str):
        stage_map = {"dormant": 10, "early": 25, "building": 35, "active": 45,
                     "late": 60, "crowded": 70, "exit_warning": 80, "unwind": 95, "unwind_active": 95}
        sv = stage_map.get(carry["stage"].lower().replace(" ", "_").replace("/", "_"))
        if sv is not None:
            subs["carry_unwind"] = {"value": sv, "state": "CURRENT", "basis": f"carry stage {carry['stage']}"}
        else:
            subs["carry_unwind"] = dict(_NO_DATA)
    elif v is not None:
        subs["carry_unwind"] = {"value": round(v), "state": "CURRENT", "basis": "carry stress score"}
    else:
        subs["carry_unwind"] = dict(_NO_DATA)

    # market-response confirmation: greed extreme confirms risk, fear extreme disconfirms
    ew = d.get("early_warning") or {}
    fg = (ew.get("fear_greed") or {})
    v = _num(fg.get("value"))
    subs["market_response"] = ({"value": round(v), "state": "CURRENT",
                                "basis": f"fear-greed {fg.get('state', '?')} (greed=risk)"}
                               if v is not None else dict(_NO_DATA))

    available = {k: s for k, s in subs.items() if s["value"] is not None}
    coverage = len(available)
    composite = round(sum(s["value"] for s in available.values()) / coverage) if coverage else None

    if composite is None:
        severity, color = "NO_DATA", "gry"
    elif composite < 25:
        severity, color = "CALM", "grn"
    elif composite < 45:
        severity, color = "WATCH", "inf"
    elif composite < 65:
        severity, color = "ELEVATED", "amb"
    elif composite < 80:
        severity, color = "SEVERE", "red"
    else:
        severity, color = "EXTREME", "red"

    ordered = sorted(available.items(), key=lambda kv: kv[1]["value"], reverse=True)
    drivers = [{"component": k, "value": s["value"], "basis": s["basis"]} for k, s in ordered[:3]]
    disconfirming = [{"component": k, "value": s["value"], "basis": s["basis"]} for k, s in ordered[-3:] if s["value"] < 40]

    return {
        "value": composite,
        "severity": severity,
        "color": color,
        "coverage": f"{coverage}/{len(COMPONENT_KEYS)} subcomponents live",
        "subcomponents": subs,
        "drivers": drivers,
        "disconfirming": disconfirming,
        "horizons": {"immediate_plumbing": None, "weeks_1_4": None, "months_1_3": None,
                     "structural": None,
                     "note": "per-horizon splits require calibrated history — R5 gate"},
        "as_of": asof.get("date"),
        "data_state": "STALE_LAST_KNOWN" if (asof.get("stale_days") or 0) > 7 else "CURRENT",
        "action_hint": {"CALM": "maintain", "WATCH": "maintain + monitor drivers",
                        "ELEVATED": "trim weakest / tighten stops",
                        "SEVERE": "reduce gross / hedge", "EXTREME": "capital preservation",
                        "NO_DATA": "no action — insufficient evidence"}[severity],
        "invalidation": "de-escalates when funding/credit/volatility subcomponents normalize for 2+ weeks",
        "claim_limit": "Decision-severity gauge, NOT a calibrated crash probability. "
                       "Uncalibrated composite of available stress observables.",
        "proof_status": "RESEARCH_ONLY",
        "execution_eligible": False,
        "false_alarm_context": "unmeasured until prospective calibration (R5/R6)",
    }
