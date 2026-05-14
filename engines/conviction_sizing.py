"""engines/conviction_sizing.py — Soros/Druckenmiller Conviction Sizing Framework"""
from __future__ import annotations
import math
from typing import Dict, Optional

def calculate_size(ticker: str, row: Dict, gamma: Dict, greek: Dict,
                   boom_bust_stage: str, reflexivity_score: float,
                   portfolio_value: float = 100000) -> Dict:
    base_size_pct = 2.0
    grade = row.get("grade", "C")
    direction = row.get("direction", "NEUTRAL")
    rr = row.get("rr", 1.0) or 1.0
    near_entry = row.get("near_entry", False)

    grade_mult = {"A": 2.5, "A+": 3.0, "B": 1.5, "C": 0.8, "D": 0.3}.get(grade, 1.0)
    rr_mult = 2.0 if rr >= 3.0 else 1.5 if rr >= 2.0 else 0.5 if rr < 1.0 else 1.0
    entry_mult = 1.5 if near_entry else 1.0

    gamma_mult = 1.0
    if gamma.get("ok"):
        reg = gamma.get("regime", "")
        if direction == "LONG" and reg in ("DEEP_POSITIVE", "POSITIVE"):
            gamma_mult = 1.4
        elif direction == "SHORT" and reg in ("DEEP_NEGATIVE", "NEGATIVE"):
            gamma_mult = 1.4
        elif reg in ("DEEP_POSITIVE", "POSITIVE", "DEEP_NEGATIVE", "NEGATIVE"):
            gamma_mult = 1.2

    stage_mult = 1.0
    if boom_bust_stage in ("ACCELERATION", "SURVIVAL"):
        stage_mult = 1.2
    elif boom_bust_stage in ("MOMENT_OF_TRUTH", "TWILIGHT"):
        stage_mult = 0.7
    elif boom_bust_stage in ("TIP_POINT", "CRISIS"):
        stage_mult = 0.4

    ref_mult = 0.7 if abs(reflexivity_score) > 0.5 else 1.0

    raw_pct = base_size_pct * grade_mult * rr_mult * entry_mult * gamma_mult * stage_mult * ref_mult
    final_pct = min(15.0, max(0.5, raw_pct))

    if final_pct >= 10:
        mode = "🐷 PIG MODE"
    elif final_pct >= 5:
        mode = "🔥 SIZE UP"
    elif final_pct >= 2:
        mode = "✅ NORMAL"
    elif final_pct >= 1:
        mode = "⚠️ SMALL"
    else:
        mode = "❌ SKIP"

    dollar = portfolio_value * final_pct / 100

    return {
        "ticker": ticker,
        "size_pct": round(final_pct, 2),
        "size_dollar": round(dollar, 0),
        "mode": mode,
        "base_pct": base_size_pct,
        "multipliers": {
            "grade": grade_mult,
            "rr": rr_mult,
            "entry": entry_mult,
            "gamma": gamma_mult,
            "stage": stage_mult,
            "reflexivity": ref_mult,
        },
        "rationale": f"Grade {grade} × RR {rr:.1f} × Entry {entry_mult:.1f} × Gamma {gamma_mult:.1f} × Stage {stage_mult:.1f} = {final_pct:.1f}%",
    }

def run_sizing(alpha_items: list, gamma_data: Dict, greeks_data: Dict,
               boom_bust: Dict, reflexivity: Dict, portfolio_value: float = 100000) -> Dict:
    stage = boom_bust.get("stage", "INCEPTION")
    scores = reflexivity.get("ticker_scores", {})
    out = {}
    for item in alpha_items:
        t = item.get("ticker", "")
        if not t:
            continue
        gamma = gamma_data.get(t, {}) if gamma_data else {}
        greek = greeks_data.get(t, {}) if greeks_data else {}
        ref_score = scores.get(t, {}).get("reflexivity_score", 0.0) if scores else 0.0
        out[t] = calculate_size(t, item, gamma, greek, stage, ref_score, portfolio_value)
    return out
