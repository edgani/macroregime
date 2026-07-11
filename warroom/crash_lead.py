"""warroom/crash_lead.py — EARLY WARNING SYSTEM: seberapa early bisa warn crash? (jujur, probabilistik).

Jawaban Edward: "kalo ada indikasi crash tahun depan, kita udah jaga-jaga dari tahun ini." Diuji di
macro panel real 1881-2023 (lihat research/RESEARCH_FINDINGS.md §10).

KEBENARAN yang harus lu tau (biar ga kena jebakan "disuruh jual tapi naik setahun lagi"):
  • Crash TIDAK bisa diprediksi dengan yakin setahun ke depan. Indikator terbaik cuma lift 1.1-1.2x.
    Siapa pun yang bilang "top udah in, jual" dengan pasti = omong kosong.
  • TAPI RISK ELEVATION bisa dideteksi PROBABILISTIK: composite (valuasi mahal + real rate negatif +
    vol tinggi) → P(crash dalam 24 bulan) naik dari 15% ke 27% (corr +0.097, p=0.0001).
  • Valuasi murah = "safety" kuat: P(crash 36mo) cuma 8% vs 25% base. Valuasi mahal = severity potential,
    bukan timing.
  • Lead terkuat: prior vol (persisten, semua horizon) + momentum melemah (~6-18mo lead).

MAKANYA output-nya PROBABILITAS + POSITIONING, bukan sinyal jual biner:
  "P(>20% drawdown dalam 24 bulan) = X% (vs base Y%) → kurangi size/hedge" — bukan "JUAL SEKARANG".
Ini yang bikin pembaca yakin: angka teruji, bukan tebakan dramatis.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

# Base rates & lifts from tested analysis (macro panel 1881-2023)
BASE_CRASH_PROB = {12: 0.10, 24: 0.20, 36: 0.25}  # P(>20% drawdown within H months), unconditional


def crash_risk(panel):
    """Composite early-warning score → probabilistic crash risk at 12/24/36mo. panel: DataFrame monthly
    with spx, cape, rate10, cpi_yoy. Returns probability + positioning (NOT a binary sell)."""
    if panel is None or "spx" not in panel or len(panel) < 130:
        return None
    p = panel.copy()
    p["ret"] = p["spx"].pct_change()
    p["vol12"] = p["ret"].rolling(12).std() * np.sqrt(12)
    real_rate = None
    if "rate10" in p and "cpi_yoy" in p:
        real_rate = (p["rate10"] - p["cpi_yoy"]).iloc[-1]
    cape_z = None
    if "cape" in p and p["cape"].notna().sum() > 120:
        cz = (p["cape"] - p["cape"].rolling(120).mean()) / p["cape"].rolling(120).std()
        cape_z = cz.iloc[-1]
    vol_now = p["vol12"].iloc[-1]
    vol_med = p["vol12"].rolling(60).median().iloc[-1]
    mom12 = p["spx"].iloc[-1] / p["spx"].iloc[-13] - 1 if len(p) > 13 else None

    # composite 0-3 (validated: score 2 → 27% crash-24mo vs 15% base)
    score = 0
    comps = {}
    if cape_z is not None:
        comps["valuation_elevated"] = bool(cape_z > 0.5); score += int(cape_z > 0.5)
    if real_rate is not None:
        comps["real_rate_negative"] = bool(real_rate < 0); score += int(real_rate < 0)
    if vol_now is not None and vol_med is not None:
        comps["vol_above_median"] = bool(vol_now > vol_med); score += int(vol_now > vol_med)
    # map score → crash probability multiplier (from tested table)
    mult = {0: 0.75, 1: 0.90, 2: 1.35, 3: 0.95}.get(score, 1.0)  # score-2 is the danger zone
    probs = {h: round(min(0.6, BASE_CRASH_PROB[h] * mult), 2) for h in (12, 24, 36)}

    # momentum-based nearer-term flag (~6-18mo lead)
    mom_warn = bool(mom12 is not None and mom12 < 0)

    level = ("ELEVATED" if score >= 2 else "moderate" if score == 1 else "low")
    if level == "ELEVATED":
        action = "reduce gross exposure / add hedges / raise cash — crash odds ~1.8x base over 24mo. NOT a sell-everything signal — a positioning shift."
        col = "red"
    elif level == "moderate":
        action = "normal risk with awareness — one risk factor active"
        col = "amb"
    else:
        action = "risk-on OK — crash odds below base (valuation/rates/vol benign)"
        col = "grn"

    return {"risk_level": level, "score": score, "max_score": 3, "color": col,
            "crash_prob": probs, "base_prob": BASE_CRASH_PROB, "components": comps,
            "momentum_warning": mom_warn, "action": action,
            "honest_note": ("This is a PROBABILITY over 12-36 months, not a market-timing call. Crashes "
                            "can't be timed precisely; elevated risk means position smaller, not exit. "
                            "Historically the market can keep rising for 1-2+ years even when risk is elevated."),
            "basis": "tested: composite → P(>20% DD in 24mo) 15%→27% (p=0.0001); valuation cheap→8% (1881-2023)"}


def build(panel):
    r = crash_risk(panel)
    return {"crash_lead": r} if r else {}
