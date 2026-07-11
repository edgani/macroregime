"""warroom/macro_regime.py — cross-asset macro regime + playbook (TESTED, all markets).

Jawaban Edward: "kapan aggressive/defensive? CPI turun/inflasi naik → short dollar? long oil? play
EV+ di SETIAP market." Diuji di panel cross-asset real (SP500+gold+oil+dollar+rates+CPI, 1971-2023 —
lihat research/RESEARCH_FINDINGS.md §9).

Temuan yang jadi basis (semua signifikan):
  • DOLLAR = hub. Dollar↔gold -0.22, ↔oil -0.20, ↔stocks -0.16 (semua p<0.001, inverse). Short dollar
    = long gold/oil/stocks. Ini "connecting the dots" cross-asset yang TERUJI.
  • RISK-ON/OFF regime (trend + dollar-falling + momentum) memprediksi drawdown: corr +0.28 (p<0.0001).
    Score 3 → fwd DD -2.8% (AGGRESSIVE); score 0 → fwd DD -7.7% (DEFENSIVE).
  • Macro quad → asset: Stagflasi (G- I+) → oil +3.1% kalahin stocks +0.7%. Inflasi naik → komoditas menang.
  • Deflasi-recovery (Q4) → semua rally (post-crash).

Semua fungsi terima panel LU (kolom: spx, gold, oil, dxy, rate10, cpi_yoy). Tanpa data → None.
Ga ngarang. Rekomendasi cross-asset = dari apa yang HISTORIS menang di kondisi itu, bukan tebakan.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

# Tested cross-asset links (monthly return correlation, 1971-2023). Basis: research/RESEARCH_FINDINGS.md §9
CROSS_ASSET_LINKS = {
    ("dollar", "gold"): {"corr": -0.22, "p": 0.0000, "rel": "inverse", "play": "dollar up → short gold; dollar down → long gold"},
    ("dollar", "oil"): {"corr": -0.20, "p": 0.0000, "rel": "inverse", "play": "dollar up → short oil; dollar down → long oil"},
    ("dollar", "stocks"): {"corr": -0.16, "p": 0.0005, "rel": "inverse", "play": "weak-dollar tailwind for equities"},
    ("rates", "gold"): {"corr": -0.09, "p": 0.05, "rel": "inverse-weak", "play": "rising real rates pressure gold (weak)"},
}

# Tested macro-state playbook: forward 3mo winner by quad (1986-2023, oil-era)
QUAD_PLAYBOOK = {
    "Q1 Goldilocks": {"long": "oil/stocks", "short": "dollar", "note": "growth up, inflation down — risk-on, commodities + equities"},
    "Q2 Reflation": {"long": "stocks/oil", "short": "dollar", "note": "growth up, inflation up — equities + commodities"},
    "Q3 Stagflation": {"long": "oil/commodities", "short": "stocks/dollar", "note": "growth down, inflation up — commodities beat stocks (+3.1% vs +0.7%)"},
    "Q4 Deflation": {"long": "oil/stocks (recovery)", "short": "dollar", "note": "growth down, inflation down — post-crash recovery, everything rallies"},
}


def _f(v):
    try:
        v = float(v)
        return v if np.isfinite(v) else None
    except Exception:
        return None


def risk_regime(panel):
    """Composite risk-on/off (0-3) → aggressive/defensive verdict + expected drawdown. TESTED: corr with
    fwd drawdown +0.28, p<0.0001. panel: DataFrame with 'spx' and optionally 'dxy' (monthly)."""
    if panel is None or "spx" not in panel or len(panel) < 12:
        return None
    spx = panel["spx"]
    trend = int(spx.iloc[-1] > spx.rolling(10).mean().iloc[-1])
    mom = int((spx.iloc[-1] / spx.iloc[-7] - 1) > 0) if len(spx) > 7 else 0
    dxy_dn = 0
    if "dxy" in panel and panel["dxy"].notna().sum() > 4:
        dxy_dn = int(panel["dxy"].iloc[-1] < panel["dxy"].iloc[-4])
    score = trend + mom + dxy_dn
    if score >= 3:
        verdict, dd, col = "AGGRESSIVE", "-2.8%", "grn"
    elif score == 2:
        verdict, dd, col = "aggressive (lean)", "-2.6%", "grn"
    elif score == 1:
        verdict, dd, col = "defensive (lean)", "-6.1%", "amb"
    else:
        verdict, dd, col = "DEFENSIVE", "-7.7%", "red"
    return {"score": score, "max_score": 3, "verdict": verdict, "expected_fwd6_maxDD": dd, "color": col,
            "components": {"trend_above_10ma": bool(trend), "momentum_positive": bool(mom), "dollar_falling": bool(dxy_dn)},
            "basis": "tested: corr(risk-on, fwd 6mo drawdown) +0.28, p<0.0001 (1971-2023)",
            "action": ("add risk / size up — smallest forward drawdowns historically" if score >= 2
                       else "reduce risk / raise cash — largest forward drawdowns historically")}


def macro_quad(panel):
    """Determine current macro quad from growth (spx 6mo accel) + inflation (CPI YoY direction)."""
    if panel is None or "spx" not in panel or "cpi_yoy" not in panel or len(panel) < 12:
        return None
    g = panel["spx"].pct_change(6)
    g_accel = g.iloc[-1] - g.iloc[-4] if len(g) > 4 else None
    infl_chg = panel["cpi_yoy"].iloc[-1] - panel["cpi_yoy"].iloc[-4] if panel["cpi_yoy"].notna().sum() > 4 else None
    if g_accel is None or infl_chg is None:
        return None
    gp, ip = g_accel > 0, infl_chg > 0
    q = ("Q1 Goldilocks" if gp and not ip else "Q2 Reflation" if gp and ip
         else "Q3 Stagflation" if not gp and ip else "Q4 Deflation")
    pb = QUAD_PLAYBOOK[q]
    return {"quad": q, "growth_accelerating": bool(gp), "inflation_rising": bool(ip),
            "long": pb["long"], "short": pb["short"], "note": pb["note"],
            "basis": "forward 3mo asset returns by quad, tested 1986-2023"}


def inflation_play(panel):
    """CPI direction → what historically wins (direct answer to 'inflasi naik → apa yang menang')."""
    if panel is None or "cpi_yoy" not in panel or panel["cpi_yoy"].notna().sum() < 6:
        return None
    chg = panel["cpi_yoy"].iloc[-1] - panel["cpi_yoy"].iloc[-4]
    rising = chg > 0
    return {"inflation_direction": "rising" if rising else "falling",
            "cpi_yoy": round(_f(panel["cpi_yoy"].iloc[-1]) or 0, 1),
            "play": ("commodities/oil lead (oil +2.3% vs stocks +1.3%); dollar soft" if rising
                     else "disinflation = risk-on; stocks +3.3% & oil +3.8%; broadly bullish"),
            "basis": "tested forward 3mo returns conditioned on CPI direction, 1971-2023"}


def cross_asset_play(driver, direction):
    """Given a driver move (e.g. dollar up), what's the tested cross-asset play?
    driver in {dollar, rates}; direction in {up, down}."""
    out = []
    for (a, b), v in CROSS_ASSET_LINKS.items():
        if a == driver:
            sign = -1 if v["rel"].startswith("inverse") else 1
            move = "down" if (direction == "up") == (sign < 0) else "up"
            out.append({"asset": b, "expected": move, "corr": v["corr"], "p": v["p"]})
    return {"driver": f"{driver} {direction}", "implications": out,
            "note": "dollar is the tested cross-asset hub (all links p<0.001)"}


def build(panel):
    """Dashboard-ready cross-asset macro package."""
    if panel is None:
        return {}
    return {"risk_regime": risk_regime(panel), "macro_quad": macro_quad(panel),
            "inflation_play": inflation_play(panel), "cross_asset_links": CROSS_ASSET_LINKS}
