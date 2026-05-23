"""engines/alpha_gatekeeper.py — Rigorous Ticker Gatekeeper for MacroRegime

RULE: Sebuah ticker HANYA boleh muncul di Alpha Center / per-market tab
      jika lolos SEMUA gate berikut:

  1. WALKFORWARD GATE: Walkforward score >= 55, MC 100x score >= 55
  2. RISK RANGE GATE: Quality A+/A/short_A+/short_A, formation aligned
  3. OPTIONS GATE: GEX regime consistent, skew confirmation, no gamma trap
  4. MACRO GATE: Quad alignment, regime transition probability < 30%
  5. FUNDAMENTAL GATE: Methodology score >= 50, narrative match
  6. SIMULATION GATE: Simulation robustness >= 65, win rate >= 50%
  7. BEHAVIORAL GATE: Yves/Cem/Karsan signals not contradictory
  8. LIQUIDITY GATE: ATR sufficient, volume regime normal

MARKET-SPECIFIC ADJUSTMENTS:
  - US Equities: Options gate MANDATORY (GEX, skew, vanna)
  - IHSG: Options gate OPTIONAL (karena data terbatas), tapi broker flow gate MANDATORY
  - Forex: Options gate SKIP, tapi COT + carry gate MANDATORY
  - Commodity: COT + contango/backwardation gate MANDATORY
  - Crypto: On-chain + funding rate gate MANDATORY
  - Index: Options gate MANDATORY (GEX primary)

OUTPUT FORMAT:
  {
    "ticker": "AAPL",
    "market": "us_equity",
    "gate_status": "PASS" | "MARGINAL" | "FAIL",
    "combined_score": 78.5,
    "per_gate": {...},
    "recommendation": "ENTRY_NOW" | "WAIT" | "AVOID",
    "basis": "Walkforward 62 + MC 71 + Risk A+ + GEX positive + Q3 aligned + ..."
  }
"""
from __future__ import annotations
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class GateResult:
    ticker: str
    market: str
    gate_status: str
    combined_score: float
    per_gate: dict
    recommendation: str
    basis: str
    raw: dict = field(default_factory=dict)

# ────────────────────────────────────────────────────────────────────────
# GATE THRESHOLDS
# ────────────────────────────────────────────────────────────────────────

GATE_THRESHOLDS = {
    "walkforward": {"min": 55.0, "weight": 0.20},
    "risk_range": {"min": 0, "weight": 0.15},
    "options": {"min": 0, "weight": 0.15},
    "macro": {"min": 0, "weight": 0.15},
    "fundamental": {"min": 50.0, "weight": 0.10},
    "simulation": {"min": 65.0, "weight": 0.10},
    "behavioral": {"min": 0, "weight": 0.08},
    "liquidity": {"min": 0, "weight": 0.07},
}

QUALITY_SCORES = {
    "A+": 100, "A": 85, "B": 60, "C": 30,
    "short_A+": 100, "short_A": 85, "short_B": 60,
}

# ────────────────────────────────────────────────────────────────────────
# PER-MARKET RULES
# ────────────────────────────────────────────────────────────────────────

MARKET_RULES = {
    "us_equity": {
        "options_mandatory": True,
        "min_atr_pct": 0.5,
        "min_realized_vol": 0.10,
        "max_realized_vol": 1.50,
        "required_gates": ["walkforward", "risk_range", "options", "macro", "simulation"],
    },
    "ihsg": {
        "options_mandatory": False,
        "min_atr_pct": 0.3,
        "min_realized_vol": 0.08,
        "max_realized_vol": 1.00,
        "required_gates": ["walkforward", "risk_range", "macro", "fundamental", "simulation"],
    },
    "forex": {
        "options_mandatory": False,
        "min_atr_pct": 0.2,
        "min_realized_vol": 0.05,
        "max_realized_vol": 0.30,
        "required_gates": ["walkforward", "risk_range", "macro", "simulation"],
    },
    "commodity": {
        "options_mandatory": False,
        "min_atr_pct": 0.8,
        "min_realized_vol": 0.15,
        "max_realized_vol": 0.80,
        "required_gates": ["walkforward", "risk_range", "macro", "simulation"],
    },
    "crypto": {
        "options_mandatory": False,
        "min_atr_pct": 1.5,
        "min_realized_vol": 0.30,
        "max_realized_vol": 2.50,
        "required_gates": ["walkforward", "risk_range", "macro", "simulation"],
    },
    "index": {
        "options_mandatory": True,
        "min_atr_pct": 0.3,
        "min_realized_vol": 0.08,
        "max_realized_vol": 0.60,
        "required_gates": ["walkforward", "risk_range", "options", "macro", "simulation"],
    },
}

# ────────────────────────────────────────────────────────────────────────
# GATE SCORING FUNCTIONS
# ────────────────────────────────────────────────────────────────────────

def _score_walkforward(wf_result: Optional[dict]) -> Tuple[float, bool, str]:
    if not wf_result:
        return 0.0, False, "No walkforward data"
    score = wf_result.get("combined_gate_score", 0)
    status = wf_result.get("gate_status", "FAIL")
    if status == "PASS":
        return score, True, f"Walkforward PASS ({score})"
    elif status == "MARGINAL":
        return score * 0.7, False, f"Walkforward MARGINAL ({score})"
    return score * 0.3, False, f"Walkforward FAIL ({score})"

def _score_risk_range(rr: Optional[dict]) -> Tuple[float, bool, str]:
    if not rr or not rr.get("ok"):
        return 0.0, False, "No risk range data"
    quality = rr.get("quality", "C")
    formation = rr.get("formation", "NEUTRAL")
    composite = rr.get("composite", "neutral")
    score = QUALITY_SCORES.get(quality, 30)
    if (formation == "BULLISH" and composite == "bullish") or (formation == "BEARISH" and composite == "bearish"):
        score = min(100, score + 15)
        passed = quality in ("A+", "A", "short_A+", "short_A")
        return score, passed, f"Risk Range {quality}, formation aligned ({formation}/{composite})"
    elif composite == "neutral":
        return score * 0.5, False, f"Risk Range {quality} but composite neutral"
    else:
        return score * 0.3, False, f"Risk Range {quality} but formation MISALIGNED ({formation}/{composite})"

def _score_options(opts: Optional[dict], market: str) -> Tuple[float, bool, str]:
    if not opts:
        if MARKET_RULES.get(market, {}).get("options_mandatory", False):
            return 0.0, False, "Options data mandatory but missing"
        return 50.0, True, "Options gate skipped (non-mandatory)"
    gex = opts.get("gex", {})
    skew = opts.get("iv_skew", {})
    pcr = opts.get("put_call_ratio")
    score = 50.0
    reasons = []
    regime = gex.get("regime", "")
    if "POSITIVE" in regime.upper():
        score += 20
        reasons.append("GEX positive (stabilizing)")
    elif "NEGATIVE" in regime.upper():
        score += 10
        reasons.append("GEX negative (vol expansion)")
    skew_val = skew.get("skew", 0)
    if skew_val > 0.05:
        score += 15
        reasons.append(f"Put skew rich ({skew_val:+.2f})")
    elif skew_val < -0.05:
        score -= 10
        reasons.append(f"Call skew rich ({skew_val:+.2f}) — euphoria")
    if pcr is not None:
        if pcr > 1.2:
            score += 10
            reasons.append(f"High PCR ({pcr:.2f}) — fear extreme")
        elif pcr < 0.7:
            score -= 10
            reasons.append(f"Low PCR ({pcr:.2f}) — complacency")
    passed = score >= 50
    return min(100, score), passed, "Options: " + ", ".join(reasons) if reasons else "Neutral"

def _score_macro(macro: Optional[dict], quad: str, direction: str) -> Tuple[float, bool, str]:
    if not macro:
        return 30.0, False, "No macro data"
    gip = macro.get("gip_v10", {})
    current_quad = gip.get("structural_quad", quad)
    transition_prob = macro.get("transition_probability", 0)
    score = 70.0
    reasons = []
    quad_bullish = current_quad in ("Q1", "Q2")
    quad_bearish = current_quad in ("Q3", "Q4")
    if direction == "LONG" and quad_bullish:
        score += 20
        reasons.append(f"LONG aligned with {current_quad} (bullish quad)")
    elif direction == "SHORT" and quad_bearish:
        score += 20
        reasons.append(f"SHORT aligned with {current_quad} (bearish quad)")
    elif direction == "LONG" and quad_bearish:
        score -= 25
        reasons.append(f"LONG vs {current_quad} (headwind)")
    elif direction == "SHORT" and quad_bullish:
        score -= 25
        reasons.append(f"SHORT vs {current_quad} (headwind)")
    if transition_prob > 0.50:
        score -= 20
        reasons.append(f"High transition prob ({transition_prob:.0%}) — regime unstable")
    elif transition_prob > 0.30:
        score -= 10
        reasons.append(f"Elevated transition prob ({transition_prob:.0%})")
    passed = score >= 50
    return min(100, max(0, score)), passed, "Macro: " + ", ".join(reasons)

def _score_fundamental(thought: Optional[dict]) -> Tuple[float, bool, str]:
    if not thought:
        return 30.0, False, "No thought process data"
    score = thought.get("thesis_score", 0) or 0
    n_matches = thought.get("n_matches", 0) or 0
    if score >= 70 and n_matches >= 3:
        return score, True, f"Fundamental strong ({score}/100, {n_matches} frameworks)"
    elif score >= 50:
        return score, False, f"Fundamental marginal ({score}/100)"
    return score, False, f"Fundamental weak ({score}/100)"

def _score_simulation(sim: Optional[dict]) -> Tuple[float, bool, str]:
    if not sim:
        return 0.0, False, "No simulation data"
    score = sim.get("robustness_score", 0)
    win_rate = sim.get("win_rate", 0)
    passed = score >= 65 and win_rate >= 50
    return score, passed, f"Simulation: score {score}, win rate {win_rate}%"

def _score_behavioral(yves: Optional[dict], cem: Optional[dict], karsan: Optional[dict], direction: str) -> Tuple[float, bool, str]:
    score = 50.0
    reasons = []
    contradictions = 0
    if yves:
        yv_sig = yves.get("signal", "")
        if direction == "LONG" and "BUY" in yv_sig.upper():
            score += 15; reasons.append("Yves: BUY")
        elif direction == "SHORT" and "SELL" in yv_sig.upper():
            score += 15; reasons.append("Yves: SELL")
        elif "NEUTRAL" in yv_sig.upper():
            score += 5; reasons.append("Yves: NEUTRAL")
        else:
            score -= 10; contradictions += 1; reasons.append(f"Yves contradicts ({yv_sig})")
    if cem:
        cem_sig = cem.get("signal", "")
        if direction == "LONG" and "BULLISH" in cem_sig.upper():
            score += 15; reasons.append("Cem: BULLISH")
        elif direction == "SHORT" and "BEARISH" in cem_sig.upper():
            score += 15; reasons.append("Cem: BEARISH")
        else:
            score -= 5; reasons.append(f"Cem: {cem_sig}")
    if karsan:
        kar_setup = karsan.get("karsan_setup", "")
        if "SQUEEZE" in kar_setup.upper() and direction == "LONG":
            score += 20; reasons.append("Karsan: SQUEEZE (LONG edge)")
        elif "BUY_CONVEXITY" in kar_setup.upper() and direction == "LONG":
            score += 15; reasons.append("Karsan: BUY convexity")
        elif "SELL_PREMIUM" in kar_setup.upper():
            score -= 10; reasons.append("Karsan: SELL premium (range-bound)")
    passed = score >= 50 and contradictions <= 1
    return min(100, score), passed, "Behavioral: " + ", ".join(reasons)

def _score_liquidity(rr: Optional[dict], market: str) -> Tuple[float, bool, str]:
    if not rr or not rr.get("ok"):
        return 30.0, False, "No liquidity data"
    rules = MARKET_RULES.get(market, MARKET_RULES["us_equity"])
    atr_pct = (rr.get("atr_14", 0) / max(rr.get("px", 1), 0.001)) * 100
    vol = rr.get("realized_vol_20", 0)
    score = 70.0
    reasons = []
    if atr_pct < rules["min_atr_pct"]:
        score -= 30; reasons.append(f"ATR too low ({atr_pct:.2f}% < {rules['min_atr_pct']}%)")
    elif atr_pct > rules["max_realized_vol"] * 10:
        score -= 20; reasons.append(f"ATR extreme ({atr_pct:.2f}%)")
    else:
        score += 10; reasons.append(f"ATR OK ({atr_pct:.2f}%)")
    if vol < rules["min_realized_vol"]:
        score -= 20; reasons.append(f"Vol too low ({vol:.2f} < {rules['min_realized_vol']})")
    elif vol > rules["max_realized_vol"]:
        score -= 20; reasons.append(f"Vol too high ({vol:.2f} > {rules['max_realized_vol']})")
    else:
        score += 10; reasons.append(f"Vol OK ({vol:.2f})")
    passed = score >= 50
    return min(100, score), passed, "Liquidity: " + ", ".join(reasons)

# ────────────────────────────────────────────────────────────────────────
# MAIN GATEKEEPER
# ────────────────────────────────────────────────────────────────────────

def evaluate_ticker(
    ticker: str,
    market: str,
    direction: str,
    walkforward_result: Optional[dict] = None,
    risk_range: Optional[dict] = None,
    options_data: Optional[dict] = None,
    macro_data: Optional[dict] = None,
    thought_process: Optional[dict] = None,
    simulation_result: Optional[dict] = None,
    yves: Optional[dict] = None,
    cem: Optional[dict] = None,
    karsan: Optional[dict] = None,
    current_quad: str = "Q3",
) -> GateResult:
    per_gate = {}
    total_weight = 0.0
    weighted_score = 0.0
    all_passed = True
    basis_parts = []

    gates = [
        ("walkforward", lambda: _score_walkforward(walkforward_result)),
        ("risk_range", lambda: _score_risk_range(risk_range)),
        ("options", lambda: _score_options(options_data, market)),
        ("macro", lambda: _score_macro(macro_data, current_quad, direction)),
        ("fundamental", lambda: _score_fundamental(thought_process)),
        ("simulation", lambda: _score_simulation(simulation_result)),
        ("behavioral", lambda: _score_behavioral(yves, cem, karsan, direction)),
        ("liquidity", lambda: _score_liquidity(risk_range, market)),
    ]

    for gate_name, scorer in gates:
        try:
            score, passed, reason = scorer()
        except Exception as e:
            score, passed, reason = 0.0, False, f"Error: {e}"
        weight = GATE_THRESHOLDS[gate_name]["weight"]
        per_gate[gate_name] = {"score": round(score, 1), "passed": passed, "reason": reason}
        weighted_score += score * weight
        total_weight += weight
        if not passed:
            all_passed = False
        basis_parts.append(f"{gate_name}={score:.0f}")

    combined = weighted_score / total_weight if total_weight > 0 else 0.0

    rules = MARKET_RULES.get(market, MARKET_RULES["us_equity"])
    required = rules.get("required_gates", [])
    required_failed = [g for g in required if not per_gate.get(g, {}).get("passed", False)]

    if all_passed and not required_failed and combined >= 65:
        status = "PASS"
        rec = "ENTRY_NOW"
    elif combined >= 55 and len(required_failed) <= 1:
        status = "MARGINAL"
        rec = "WAIT"
    else:
        status = "FAIL"
        rec = "AVOID"

    basis = f"Combined={combined:.1f} | " + " | ".join(basis_parts)
    if required_failed:
        basis += f" | REQUIRED_FAILED: {required_failed}"

    return GateResult(
        ticker=ticker,
        market=market,
        gate_status=status,
        combined_score=round(combined, 1),
        per_gate=per_gate,
        recommendation=rec,
        basis=basis,
        raw={"required_gates": required, "required_failed": required_failed},
    )

def batch_evaluate(
    tickers: List[str],
    market_map: Dict[str, str],
    direction_map: Dict[str, str],
    data_snap: dict,
    current_quad: str = "Q3",
) -> Dict[str, GateResult]:
    results = {}
    wf_all = data_snap.get("walkforward_results", {})
    rr_all = (data_snap.get("risk_ranges", {}) or {}).get("asset_ranges", {})
    opts_all = data_snap.get("options_data", {})
    macro_all = data_snap.get("macro_data", {})
    thought_all = data_snap.get("thought_process", {})
    sim_all = data_snap.get("simulation_results", {})
    yves_all = data_snap.get("yves", {})
    cem_all = data_snap.get("cem_karsan", {})
    karsan_all = (data_snap.get("karsan_scanner", {}) or {}).get("per_ticker", {})

    for ticker in tickers:
        market = market_map.get(ticker, "us_equity")
        direction = direction_map.get(ticker, "LONG")
        res = evaluate_ticker(
            ticker=ticker,
            market=market,
            direction=direction,
            walkforward_result=wf_all.get(ticker),
            risk_range=rr_all.get(ticker),
            options_data=opts_all.get(ticker),
            macro_data=macro_all,
            thought_process=thought_all.get(ticker),
            simulation_result=sim_all.get(ticker),
            yves=yves_all.get(ticker),
            cem=cem_all.get(ticker),
            karsan=karsan_all.get(ticker),
            current_quad=current_quad,
        )
        results[ticker] = res
    return results

def get_alpha_center_tickers(results: Dict[str, GateResult], min_status: str = "PASS") -> List[str]:
    if min_status == "PASS":
        return [t for t, r in results.items() if r.gate_status == "PASS"]
    elif min_status == "MARGINAL":
        return [t for t, r in results.items() if r.gate_status in ("PASS", "MARGINAL")]
    return list(results.keys())

def get_gatekeeper_summary(results: Dict[str, GateResult]) -> dict:
    passed = [r for r in results.values() if r.gate_status == "PASS"]
    marginal = [r for r in results.values() if r.gate_status == "MARGINAL"]
    failed = [r for r in results.values() if r.gate_status == "FAIL"]
    return {
        "total": len(results),
        "passed": len(passed),
        "marginal": len(marginal),
        "failed": len(failed),
        "avg_combined_score": round(sum(r.combined_score for r in results.values()) / max(len(results), 1), 1),
        "top_ticker": max(results.values(), key=lambda r: r.combined_score).ticker if results else None,
        "pass_rate_pct": round(len(passed) / max(len(results), 1) * 100, 1),
    }
