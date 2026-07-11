"""warroom/thesis_playbook.py — Thesis Engine + Playbook + Why-Now/Why-Not/Wait (audit gaps, consolidated).

Nyatuin beberapa gap decision-experience dari audit lu jadi SATU modul (bukan 5 engine terpisah — sesuai
aturan lu jangan bikin monster):

  • THESIS CARD (#1 audit doc-6): hypothesis, evidence, mechanism, beneficiaries, probability, horizon,
    KPI, invalidation. Jawaban "kenapa gw harus percaya ini".
  • PLAYBOOK (#7 audit doc-8): regime/event → historical playbook fase-per-fase (War → Phase 1 Oil/Gold/
    Defense → Phase 2 Inflation → ...). Ga perlu mikir ulang.
  • WHY NOW / WHY NOT / WAIT: kenapa sekarang, kenapa jangan, atau tunggu.
  • DEVIL'S ADVOCATE: sistem sendiri bantah thesis lu (kenapa bisa gagal).

Semua grounded ke tested macro (RESEARCH_FINDINGS §9-10) + knowledge graph + structural knowledge.
Playbook fase = pola historis terdokumentasi, ditandai (bukan klaim presisi).
"""
from __future__ import annotations

# THESIS LIBRARY — curated active theses (from your research). Each has the full card structure.
THESES = {
    "AI Capex Cycle": {
        "hypothesis": "AI capex grows >25%/yr through 2028, cascading down the compute + power supply chain",
        "evidence": ["Hyperscaler capex guides (MSFT/META/GOOG/AMZN)", "HBM sold out", "power interconnect queues"],
        "mechanism": "AI capex → HBM → Advanced Packaging → Power → Transformer → Cooling",
        "beneficiaries": ["MU", "AVGO", "ETN", "GEV", "VRT", "COHR"],
        "probability": 0.78, "horizon": "2026-2028",
        "kpi": ["hyperscaler capex growth", "HBM ASP", "power demand", "CoWoS capacity"],
        "invalidation": "hyperscaler capex cut, or AI ROI disappoints → capex freeze",
        "status": "ACTIVE"},
    "Power / Electrification": {
        "hypothesis": "Structural power shortage (AI + electrification + aging grid) drives multi-year capex",
        "evidence": ["transformer lead times 2+ yrs", "utility capex up", "nuclear restart", "grid age"],
        "mechanism": "Power demand → Transformer → Copper → Utility → Nuclear → Uranium",
        "beneficiaries": ["ETN", "GEV", "POWL", "VRT", "CEG"],
        "probability": 0.74, "horizon": "2025-2030",
        "kpi": ["transformer backlog", "utility capex", "power prices", "interconnection queue"],
        "invalidation": "demand slows (recession) or supply catches up faster than expected",
        "status": "ACTIVE"},
    "Memory / HBM": {
        "hypothesis": "HBM supply stays tight vs AI demand → pricing power + margin expansion for memory",
        "evidence": ["HBM sold out through next year", "limited suppliers", "TSV/packaging bottleneck"],
        "mechanism": "AI → HBM demand → DRAM/TSV bottleneck → memory ASP up → margins up",
        "beneficiaries": ["MU"],
        "probability": 0.68, "horizon": "2026-2027",
        "kpi": ["HBM ASP", "DRAM inventory", "Samsung HBM qualification"],
        "invalidation": "Samsung catches up on HBM → oversupply → margin compression",
        "status": "ACTIVE"},
}

# PLAYBOOK LIBRARY — regime/event → historical phase-by-phase playbook
PLAYBOOKS = {
    "War / Geopolitics": {"phases": [
        ("Phase 1 (shock)", "Oil, Gold, Defense rally; risk-off"),
        ("Phase 2 (pass-through)", "Freight + inflation rise; commodities lead"),
        ("Phase 3 (policy)", "Rates react; dollar strength"),
        ("Phase 4 (demand hit)", "Growth/consumer weaken; banks/property lag")],
     "tested": "cross-asset links tested (dollar hub, p<0.001); phase timing is historical pattern"},
    "Inflation Rising": {"phases": [
        ("Phase 1", "Commodities + oil lead (tested: oil +2.3% vs stocks +1.3%)"),
        ("Phase 2", "Rates rise; rate-sensitive sectors lag"),
        ("Phase 3", "Dollar firms; gold mixed"),
        ("Phase 4", "Growth slows if rates overshoot")],
     "tested": "inflation→commodity edge tested (RESEARCH_FINDINGS §9)"},
    "Disinflation": {"phases": [
        ("Phase 1", "Risk-on: stocks +3.3%, oil +3.8% (tested)"),
        ("Phase 2", "Rates fall; growth/tech lead"),
        ("Phase 3", "Dollar softens; EM + gold benefit")],
     "tested": "disinflation risk-on tested (§9)"},
    "Fed Easing / QE": {"phases": [
        ("Phase 1", "Liquidity up → risk assets, small-cap, crypto"),
        ("Phase 2", "Dollar down → gold, oil, EM"),
        ("Phase 3", "Growth recovers; cyclicals lead")],
     "tested": "dollar→gold/oil/stocks links tested (p<0.001)"},
    "Crash / Risk-off": {"phases": [
        ("Phase 1", "Raise cash; reduce beta (risk-regime score → defensive)"),
        ("Phase 2", "Hedge; quality + low-vol outperform"),
        ("Phase 3 (capitulation)", "Panic-bottom setup → contrarian BUY (tested: fwd63 +6% p<0.001)"),
        ("Phase 4 (recovery)", "RS top-decile names lead the bounce")],
     "tested": "panic-bottom + risk-regime tested (§7, §9)"},
}


def thesis_card(name):
    return THESES.get(name)


def thesis_library():
    return [{"name": k, "status": v["status"], "probability": v["probability"], "horizon": v["horizon"]}
            for k, v in THESES.items()]


def playbook(regime_or_event):
    pb = PLAYBOOKS.get(regime_or_event)
    return {"scenario": regime_or_event, **pb} if pb else None


def all_playbooks():
    return list(PLAYBOOKS.keys())


def why_now(theme, macro_regime=None):
    """Kenapa SEKARANG — align thesis dengan kondisi macro saat ini (tested regime)."""
    reasons = []
    t = next((v for k, v in THESES.items() if theme.lower() in k.lower()), None)
    if t:
        reasons += [f"thesis active: {t['hypothesis'][:60]}"]
        reasons += [f"KPI to watch: {', '.join(t['kpi'][:2])}"]
    if macro_regime:
        rr = (macro_regime.get("risk_regime") or {})
        if rr.get("verdict"):
            reasons.append(f"risk regime {rr['verdict']} (tested: predicts drawdown)")
        ip = (macro_regime.get("inflation_play") or {})
        if ip.get("play"):
            reasons.append(f"macro: {ip['play'][:50]}")
    return {"theme": theme, "why_now": reasons or ["no specific catalyst aligned right now"],
            "note": "'why now' = thesis + current tested macro regime alignment"}


def why_not(ticker, convexity=None, valuation_pct=None):
    """Kenapa JANGAN — the anti-case. Crowding, valuation, small reward."""
    flags = []
    if convexity and convexity.get("ev_pct") is not None and convexity["ev_pct"] < 20:
        flags.append(f"low expected reward (EV {convexity['ev_pct']:+.0f}%)")
    if valuation_pct and valuation_pct > 85:
        flags.append(f"valuation stretched ({valuation_pct:.0f}th percentile)")
    if convexity and (convexity.get("tail_ratio") or 2) < 1.2:
        flags.append("poor asymmetry (downside ~ upside)")
    return {"ticker": ticker, "why_not": flags or ["no major red flags on tested metrics"],
            "verdict": "WAIT / avoid" if flags else "no disqualifier",
            "note": "'why not' is checked before any accumulation — no name passes on hype alone"}


def devils_advocate(theme):
    """Sistem sendiri bantah thesis lu — kenapa bisa GAGAL (pre-mortem)."""
    t = next((v for k, v in THESES.items() if theme.lower() in k.lower()), None)
    base = t["invalidation"] if t else "demand assumption wrong"
    generic = ["consensus already positioned → edge decayed", "capex cycle turns to oversupply (Marathon-style)",
               "a cheaper 2nd-derivative play captures more of the move", "regime shift (rates/liquidity) breaks the setup"]
    return {"theme": theme, "how_this_fails": [base] + generic,
            "note": "Devil's advocate: the system argues AGAINST the thesis. If it survives these, conviction is earned."}
