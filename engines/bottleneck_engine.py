"""engines/bottleneck_engine.py v2 — Multi-Asset Bottleneck Scanner

Features:
- Scans ALL loaded tickers (US stocks, forex, commodities, crypto, IHSG)
- Classifies per market + Long/Short direction per quad
- EV ranking: Expected Value = regime_fit × trend_score × constraint × (1 + rs_3m)
- Brewing detection: pre-breakout setups with high constraint + accumulation
- IHSG: long-only, sorted by EV+
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from config.settings import (
    BOTTLENECK_PROFILES, TICKER_SECTOR, QUAD_ASSET_PERFORMANCE,
    MARKET_CLASSIFICATION, QUAD_MARKET_DIRECTION, EM_RECOVERY_SIGNALS,
)

# ── Known bottleneck database (research April 2026) ──────────────────────────
KNOWN_BOTTLENECKS: Dict[str, dict] = {
    "LITE": {"type":"structural","sub":"ai_optics","constraint":0.95,"phase":"level_2",
        "thesis":"ONLY supplier 200G EMLs at volume. NVIDIA $2B committed. InP laser monopoly for CPO. Supply constrained 2027+.",
        "catalyst":"NVIDIA CPO deployment, 1.6T ramp, Q2 guide","tp_type":"structural",
        "risk":"CPO adoption delay; pluggable modules persist"},
    "COHR": {"type":"structural","sub":"ai_optics","constraint":0.90,"phase":"level_2",
        "thesis":"Volume leader 25% market share. NVIDIA $2B committed. CW laser for Spectrum-X and Rubin AI.",
        "catalyst":"CPO contract flow, Rubin deployment","tp_type":"structural","risk":"Broadcom vertical integration"},
    "POET": {"type":"structural","sub":"ai_optics","constraint":0.85,"phase":"level_1",
        "thesis":"Pure-play CPO photonic engine. Small cap, next layer after LITE/COHR. If CPO wins, POET wins.",
        "catalyst":"Customer adoption, foundry partnership","tp_type":"structural","risk":"Pre-revenue binary risk"},
    "ON": {"type":"structural","sub":"ai_power","constraint":0.85,"phase":"level_2",
        "thesis":"EliteSiC M3e: 30% conduction loss reduction. vGaN breakthrough 50% energy savings. AI DC power = new primary driver replacing slowing EV.",
        "catalyst":"AI DC SiC wins, vGaN production ramp","tp_type":"structural",
        "risk":"EV slowdown; WOLF recovery removes pricing umbrella; AI capex plateau"},
    "WOLF": {"type":"structural","sub":"ai_power","constraint":0.75,"phase":"watch",
        "thesis":"Only US large-scale SiC substrate maker. CHIPS Act strategic asset. Distressed = binary optionality.",
        "catalyst":"Govt rescue/acquisition, debt restructuring","tp_type":"structural","risk":"Bankruptcy real risk"},
    "VST": {"type":"structural","sub":"ai_power_infra","constraint":0.87,"phase":"level_2",
        "thesis":"Nuclear baseload = only 24/7 clean power for AI. AI DC purchase agreements. Power infrastructure secular bottleneck.",
        "catalyst":"New AI power purchase agreements","tp_type":"structural","risk":"Regulatory, license renewal"},
    "ETN": {"type":"structural","sub":"ai_power_infra","constraint":0.82,"phase":"level_2",
        "thesis":"Transformers/switchgear lead times 2-3 years. Can't build AI DC without Eaton. Infrastructure you can't rush.",
        "catalyst":"Hyperscaler capex guides, order backlog","tp_type":"structural","risk":"Demand normalization"},
    "GEV": {"type":"structural","sub":"ai_power_infra","constraint":0.80,"phase":"level_1",
        "thesis":"Grid-scale power for AI data centers. Transformer/turbine backlog secular. GE Vernova the picks-and-shovels.",
        "catalyst":"Utility and DC power contracts","tp_type":"structural","risk":"Execution risk post-spinoff"},
    "AMKR": {"type":"structural","sub":"ai_packaging","constraint":0.78,"phase":"level_2",
        "thesis":"Advanced packaging for AI chips. TSMC overflow. CoWoS-adjacent capacity beneficiary.",
        "catalyst":"AI chip volume ramp","tp_type":"structural","risk":"TSMC insources more capacity"},
    "ISRG": {"type":"structural","sub":"healthcare_eq","constraint":0.88,"phase":"level_2",
        "thesis":"Robotic surgery near-monopoly. 8000+ DaVinci installed base. Consumables = recurring. No substitute for trained surgeons.",
        "catalyst":"Procedure volume, FDA approvals, intl expansion","tp_type":"structural","risk":"Competition from CMR/Medtronic"},
    "GLD": {"type":"structural","sub":"precious_metals","constraint":0.78,"phase":"level_2",
        "thesis":"Q3 = best gold regime. Central bank buying record. De-dollarization structural bid. USD TREND bearish (McCullough Apr 2026).",
        "catalyst":"Fed pivot signal, USD breakdown, EM central bank buying","tp_type":"structural","risk":"USD reversal; real yield spike"},
    "LMT": {"type":"structural","sub":"defense","constraint":0.82,"phase":"level_2",
        "thesis":"Defense production bottleneck. NATO 2% GDP = decade-long order book. Missile/munitions can't scale fast enough.",
        "catalyst":"NATO spending, F-35 orders, Ukraine resupply","tp_type":"structural","risk":"Peace negotiations, budget sequestration"},
    "MKSI": {"type":"structural","sub":"ai_optics","constraint":0.75,"phase":"watch",
        "thesis":"Laser systems for SiPh fab expansion. Tower+GF expanding SiPh = MKS capital equipment demand.",
        "catalyst":"SiPh foundry capex announcements","tp_type":"structural","risk":"Cyclical capex slowdown"},
    # Transformer / Switchgear (Screenshot 3 type: Hammond Power Solutions, ETN, etc.)
    "VRT":  {"type":"structural","sub":"transformer_infra","constraint":0.88,"phase":"level_2",
        "thesis":"Vertiv = data center power infrastructure monopoly. Liquid cooling + UPS + power mgmt. AI DC buildout = 10yr order book. CEO called 2026 'breakout year'.",
        "catalyst":"AI DC power density increase, hyperscaler capex guide up","tp_type":"structural",
        "risk":"Valuation stretched; execution risk at scale"},
    "HUBB": {"type":"structural","sub":"transformer_infra","constraint":0.82,"phase":"level_2",
        "thesis":"Hubbell electrical components + switchgear. Data center + grid upgrade = multi-year demand. Similar to ETN but smaller = more upside leverage.",
        "catalyst":"Utility grid upgrade cycle, AI DC power contracts","tp_type":"structural",
        "risk":"Cyclical exposure, not pure AI play"},
    "NVT":  {"type":"structural","sub":"transformer_infra","constraint":0.78,"phase":"level_1",
        "thesis":"nVent Electric = electrical enclosures + thermal management for data centers. AI DC density = thermal bottleneck = nVent's specialty.",
        "catalyst":"AI DC thermal demand, data center density increase","tp_type":"structural",
        "risk":"Less known, limited liquidity"},
    # TAO / Bittensor
    "TAO22974-USD": {"type":"structural","sub":"depin_ai","constraint":0.75,"phase":"level_1",
        "thesis":"Bittensor decentralized AI network. 21M max supply, ~8M circulating. March 2026 surge on subnet expansion. Tokenomics = structural supply constraint.",
        "catalyst":"New subnet launches, institutional discovery, AI narrative amplification","tp_type":"crypto",
        "risk":"High pump_risk=0.70. Binary: adoption or dump. Exit 14d before major unlock."},
    "ACLS": {"type":"structural","sub":"ai_optics","constraint":0.72,"phase":"watch",
        "thesis":"Ion implant for SiPh fabs. Less-known picks-and-shovels for photonics expansion.",
        "catalyst":"Tower/GF SiPh expansion orders","tp_type":"structural","risk":"Limited SiPh-specific revenue"},
    "AEHR": {"type":"structural","sub":"sic_gan","constraint":0.78,"phase":"level_1",
        "thesis":"Wafer-level burn-in test systems for SiC/GaN. Critical for automotive + AI power reliability. FOX systems = monopoly-like positioning in emerging SiC test.",
        "catalyst":"SiC automotive adoption, AI power device test demand","tp_type":"structural",
        "risk":"Cyclical capex; customer concentration (ON Semi)"},
    "MPWR": {"type":"structural","sub":"ai_power","constraint":0.80,"phase":"level_2",
        "thesis":"Power management ICs for AI servers. Monolithic Power = highest efficiency DC-DC for hyperscaler racks. AI DC power = structural demand driver.",
        "catalyst":"AI server volume ramp, hyperscaler DC buildout","tp_type":"structural",
        "risk":"Competition from TI/Analog Devices; China exposure"},
    "FORM": {"type":"structural","sub":"ai_optics","constraint":0.70,"phase":"watch",
        "thesis":"Optical test and measurement for datacom. 800G/1.6T transceiver test demand structural growth.",
        "catalyst":"800G/1.6T ramp, CPO test requirements","tp_type":"structural",
        "risk":"Cyclical test equipment demand"},
    "COHU": {"type":"structural","sub":"ai_packaging","constraint":0.72,"phase":"watch",
        "thesis":"Semiconductor test handlers + vision inspection. AI chip volume = test handler demand.",
        "catalyst":"AI chip volume ramp, advanced packaging inspection","tp_type":"structural",
        "risk":"Cyclical; competition from Advantest/Teradyne"},
}

IHSG_BOTTLENECKS = {
    "ITMG.JK": {"type":"foreign_flow","sub":"coal","phase":"watch","tp_type":"ihsg",
        "thesis":"Highest coal dividend yield. But Q3 structural = commodity cycle peaked. Only trade on foreign net buy + IDR weakness."},
    "INCO.JK": {"type":"structural","sub":"nickel","phase":"watch","tp_type":"ihsg",
        "thesis":"Indonesia ore export ban = pricing power. EV battery secular demand. Low-cost producer."},
    "BBCA.JK": {"type":"defensive","sub":"banking","phase":"level_2","tp_type":"ihsg",
        "thesis":"Highest ROE bank ASEAN. ~50% foreign ownership = foreign flow driven. Defensive in Q3."},
    "TLKM.JK": {"type":"defensive","sub":"telco","phase":"level_2","tp_type":"ihsg",
        "thesis":"Defensive telco. Dividend yield 5%+. Foreign flow anchor in risk-off periods."},
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def _ret(s, n):
    if s is None: return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < n+1: return None
    try: return float(s.iloc[-1]/s.iloc[-n-1]-1)
    except: return None

def _rs(close, bench, n=63):
    if bench is None: return None
    try:
        c = pd.to_numeric(close, errors="coerce").dropna().tail(n)
        b = pd.to_numeric(bench, errors="coerce").dropna().tail(n)
        if len(c) < 20 or len(b) < 20: return None
        cr = c.pct_change().dropna().values
        br = b.pct_change().dropna().values
        if len(cr) != len(br): br = br[-len(cr):] if len(br)>len(cr) else br; cr = cr[-len(br):] if len(cr)>len(br) else cr
        if len(cr) < 5: return None
        return float(np.mean(cr) - np.mean(br))
    except: return None

def _vol_acc(close, n=63):
    try:
        c = pd.to_numeric(close, errors="coerce").dropna().tail(n)
        if len(c) < 30: return 0.0
        v = c.pct_change().dropna().values
        up = v > 0
        uv = float(np.mean(v[up])) if up.any() else float(np.mean(v))
        dv = float(np.mean(v[~up])) if (~up).any() else float(np.mean(v))
        return float(np.clip(0.5*(uv/(abs(dv)+1e-10)), 0., 1.))
    except: return 0.5

def _trend(close, n=63):
    c = pd.to_numeric(close, errors="coerce").dropna().tail(n).values
    if len(c) < 20: return False, False, "insufficient"
    half = max(len(c)//3, 5)
    hh = float(np.max(c[-half:])) > float(np.max(c[:half])) * 1.003
    hl = float(np.min(c[-half:])) > float(np.min(c[:half])) * 1.003
    lh = float(np.max(c[-half:])) < float(np.max(c[:half])) * 0.997
    ll = float(np.min(c[-half:])) < float(np.min(c[:half])) * 0.997
    if hh and hl: return True, True, "uptrend"
    if lh and ll: return False, False, "downtrend"
    return hh, hl, "range"

def _range_pos(close, n=63):
    c = pd.to_numeric(close, errors="coerce").dropna().tail(n)
    if len(c) < 20: return 0.5, "mid_range"
    lo, hi = float(c.min()), float(c.max())
    px = float(c.iloc[-1])
    span = hi - lo
    if span < 1e-9: return 0.5, "mid_range"
    rp = (px - lo) / span
    label = "at_resistance" if rp >= 0.90 else "approaching_breakout" if rp >= 0.75 else "at_support" if rp <= 0.10 else "mid_range"
    return rp, label

def _compute_tp(close, tp_type="structural", trend_lrr=None, trend_trr=None, trade_trr=None):
    c = pd.to_numeric(close, errors="coerce").dropna()
    if len(c) < 5: return {}
    px = float(c.iloc[-1])
    rv21 = float(c.pct_change().dropna().tail(21).std()) if len(c) > 22 else 0.02
    rv63 = float(c.pct_change().dropna().tail(63).std()) if len(c) > 64 else rv21
    hi52 = float(c.tail(252).max()) if len(c) >= 252 else float(c.max())

    if tp_type == "structural":
        t1 = trade_trr if trade_trr and math.isfinite(float(trade_trr)) else px*(1+1.5*rv21*math.sqrt(15))
        t2 = trend_trr if trend_trr and math.isfinite(float(trend_trr)) else px*(1+2.5*rv63*math.sqrt(63))
        t3 = hi52 if hi52 > t2*1.05 else px*(1+4.0*rv63*math.sqrt(63))
        stop = trend_lrr if trend_lrr and math.isfinite(float(trend_lrr)) else px*(1-1.5*rv63)
        rat = "T1=TRADE TRR: trim 25% | T2=TREND TRR: trim 50% | T3=ATH/resistance: trail 25%. EXIT on TREND LRR break."
        sz = "2-4% portfolio. Add 1.5x on breakout above T2."
    elif tp_type == "squeeze":
        t1, t2, t3 = px*1.30, px*1.55, px*2.10
        stop = px*0.88
        rat = "T1=+30% trim 50% | T2=+55% trim 40% | T3=+110% trail 10%. TIME STOP: 5 days."
        sz = "1-2% MAX. Hard -12% stop."
    elif tp_type == "commodity":
        t1 = px*(1+1.0*rv63); t2 = px*(1+2.0*rv63); t3 = hi52
        stop = px*0.85
        rat = "T1=+1σ 63d: trim 33% | T2=+2σ 63d: trim 33% | T3=52w high: trail 34%. -15% hard."
        sz = "1-3% portfolio."
    elif tp_type == "ihsg":
        t1 = trade_trr if trade_trr and math.isfinite(float(trade_trr)) else px*1.12
        t2 = trend_trr if trend_trr and math.isfinite(float(trend_trr)) else px*1.25
        t3 = None; stop = px*0.92
        rat = "T1=TRADE TRR/+12%: trim 50% on foreign net sell | T2=TREND TRR/+25%: trim 50%. Exit 100% on 2x foreign net sell."
        sz = "2-4% portfolio. CRITICAL: watch IDR >1.5% weakness in 2 days = exit."
    elif tp_type == "crypto":
        t1, t2, t3 = px*1.40, px*2.0, None
        stop = px*0.80
        rat = "T1=+40% trim 50% | T2=+100% trim 40%. EXIT 14 DAYS BEFORE unlock. -20% hard."
        sz = "0.5-1% MAX."
    elif tp_type == "forex":
        t1 = px*(1+2.0*rv21); t2 = px*(1+4.0*rv63); t3 = None
        stop = px*(1-2.0*rv63)
        rat = "T1=+2σ 21d: trim 40% | T2=+4σ 63d: trim 40%. EXIT on regime flip signal."
        sz = "1-2% portfolio (leveraged)."
    else:
        t1 = trend_trr or px*1.15; t2 = px*1.30; t3 = None
        stop = trend_lrr or px*0.90
        rat = "Standard TRR exits."; sz = "2-4% portfolio."

    rr = round((t2-px)/(px-stop), 2) if t2 and stop and px > stop else None
    return dict(
        t1=round(t1,4) if t1 else None, t2=round(t2,4) if t2 else None,
        t3=round(t3,4) if t3 else None, stop=round(stop,4) if stop else None,
        rr_ratio=rr, tp_rationale=rat, sizing_note=sz,
    )

# ── Main Engine ──────────────────────────────────────────────────────────────

class BottleneckEngine:
    def run(self, prices, volumes=None, quad_str="Q3", quad_mon="Q2",
            benchmark="SPY", asset_ranges=None, top_n=30):
        volumes = volumes or {}
        bench = prices.get(benchmark)
        qk = quad_str.upper(); qk_mon = quad_mon.upper()

        # Regime direction per market
        directions = QUAD_MARKET_DIRECTION.get(qk, {})
        playbook = QUAD_ASSET_PERFORMANCE.get(quad_str, {})

        all_scored = []
        market_buckets = {"us_equity":[], "forex":[], "commodity":[], "crypto":[], "ihsg":[]}

        for ticker, close in prices.items():
            if ticker == benchmark: continue
            close = pd.to_numeric(close, errors="coerce").dropna()
            kb = KNOWN_BOTTLENECKS.get(ticker, {})
            # FIXED: known bottleneck tickers get minimum 5 days (not 30) so they always appear
            min_days = 5 if kb else 30
            if len(close) < min_days: continue

            market = MARKET_CLASSIFICATION.get(ticker, "us_equity")
            sector = TICKER_SECTOR.get(ticker, "generic")
            prof = BOTTLENECK_PROFILES.get(sector, BOTTLENECK_PROFILES["generic"])
            constraint = float(prof["constraint"])
            kb = KNOWN_BOTTLENECKS.get(ticker, {})

            # Regime fit
            rf_str = float(prof.get(qk, 0.5)); rf_mon = float(prof.get(qk_mon, 0.5))
            regime_fit = 0.65*rf_str + 0.35*rf_mon

            # Trend
            hh, hl, trd = _trend(close, 63)
            trend_score = 1.0 if trd == "uptrend" else 0.5 if trd == "range" else 0.0

            # RS vs benchmark
            rs3 = _rs(close, bench, 63) if bench is not None else None
            rs21 = _rs(close, bench, 21) if bench is not None else None
            rs_score = float(np.clip((rs3 or 0.0)*10.0 + 0.5, 0.0, 1.0)) if rs3 is not None else 0.5

            # Volume accumulation
            acc_s = _vol_acc(close, 63)

            # Range position
            rp, rp_label = _range_pos(close, 63)

            # 52w stats
            hi52 = float(close.tail(252).max()) if len(close) >= 252 else float(close.max())
            lo52 = float(close.tail(252).min()) if len(close) >= 252 else float(close.min())
            px = float(close.iloc[-1])
            pct_from_hi = (px - hi52) / max(hi52, 1e-9)
            pct_from_lo = (px - lo52) / max(lo52, 1e-9)

            # Level classification
            known_phase = kb.get("phase", None)
            btn_type = kb.get("type", "structural")
            if known_phase:
                level = known_phase
            elif trd == "uptrend":
                level = "level_1" if rp_label in ("at_resistance", "approaching_breakout") else "level_2"
            elif trd == "range" and acc_s >= 0.60 and rp >= 0.70:
                level = "level_1"
            elif trd == "downtrend":
                level = "avoid"
            else:
                level = "watch"

            # Regime trap
            regime_trap = (qk in ("Q3","Q4") and btn_type == "squeeze") or (qk == "Q4" and btn_type != "structural")

            # TP
            rr_data = (asset_ranges or {}).get(ticker, {})
            tp = _compute_tp(close, kb.get("tp_type","structural"),
                rr_data.get("trend_lrr"), rr_data.get("trend_trr"), rr_data.get("trade_trr"))

            # Base score
            score = (0.30*constraint + 0.25*regime_fit + 0.20*trend_score + 0.15*rs_score + 0.10*acc_s)
            if level == "avoid": score *= 0.30
            if regime_trap: score *= 0.40
            # FIXED: known bottleneck tickers get MASSIVE score boost so they ALWAYS appear
            if kb: 
                score = min(score + 0.25, 1.0)  # was 0.08, now 0.25
                # Override constraint with known value if generic/low
                constraint = max(constraint, float(kb.get("constraint", 0.70)))
            if pct_from_lo < 0.30 and acc_s >= 0.65 and constraint >= 0.75:
                score = min(score + 0.08, 1.0)
            score = float(np.clip(score, 0.0, 1.0))

            # EV (Expected Value) = regime_fit × trend_score × constraint × (1 + rs_3m)
            ev = regime_fit * trend_score * constraint * (1.0 + (rs3 or 0.0))
            ev = float(np.clip(ev, -2.0, 2.0))

            # Direction: long/short based on quad + trend
            market_dir = directions.get(market, "neutral")
            if market_dir == "long" and trd in ("uptrend", "range"):
                direction = "long"
            elif market_dir == "long" and trd == "downtrend":
                direction = "avoid_long"  # regime says long but trend down = wait
            elif market_dir == "short" and trd == "downtrend":
                direction = "short"
            elif market_dir == "short" and trd in ("uptrend", "range"):
                direction = "avoid_short"  # regime says short but trend up = wait
            else:
                direction = "neutral"

            # IHSG override: long-only
            if market == "ihsg":
                direction = "long" if trd in ("uptrend", "range") else "avoid"

            # KNOWN BOTTLENECK OVERRIDE: structural/defensive plays in Q3 get LONG classification
            # even if market_dir=short. These are the Q3 defensive bottlenecks:
            # GLD, XLV, defense, photonics, healthcare = exceptions to the Q3 short bias
            if kb and btn_type in ("structural", "defensive") and regime_fit >= 0.55:
                if trd in ("uptrend", "range"):
                    direction = "long"
                elif trd == "downtrend":
                    direction = "avoid_long"  # known bottleneck but in downtrend = wait

            item = dict(
                ticker=ticker, market=market, sector=sector, btn_type=btn_type,
                level=level, score=round(score,3), constraint=round(constraint,2),
                regime_fit=round(regime_fit,2), trend=trd, hh=hh, hl=hl,
                acc=round(acc_s,2), rs_3m=round(rs3,4) if rs3 else None,
                rs_1m=round(rs21,4) if rs21 else None, rs_score=round(rs_score,2),
                trend_score=round(trend_score,2), range_pos=round(rp,2),
                range_label=rp_label, pct_from_hi=round(pct_from_hi,3),
                pct_from_lo=round(pct_from_lo,3), px=round(px,4),
                ev=round(ev,3), direction=direction,
                known=bool(kb), known_thesis=kb.get("thesis",""),
                known_catalyst=kb.get("catalyst",""), known_risk=kb.get("risk",""),
                regime_trap=regime_trap, tp=tp,
                rationale=kb.get("thesis","")[:80] if kb else f"{sector}|{trd}|RS {rs3:.1%}" if rs3 else sector,
            )

            all_scored.append(item)
            if market in market_buckets:
                market_buckets[market].append(item)

        # Sort each bucket by EV (descending for long, ascending for short)
        for mkt in market_buckets:
            market_buckets[mkt].sort(key=lambda x: x["ev"], reverse=True)

        # Brewing detection: high constraint + regime fit + accumulation but not yet level_1/2
        brewing = []
        for s in all_scored:
            if s["level"] in ("watch",) and s["constraint"] >= 0.70 and s["regime_fit"] >= 0.60 and s["acc"] >= 0.55:
                brewing.append(s)
        brewing.sort(key=lambda x: x["ev"], reverse=True)

        # EM Recovery signal
        em_key = f"{qk}→{qk_mon}"
        em_signal = EM_RECOVERY_SIGNALS.get(em_key, EM_RECOVERY_SIGNALS.get("Q3→Q2", {}))

        # ON analysis
        on_analysis = {
            "ticker":"ON","is_bottleneck":True,"type":"SiC/GaN structural",
            "why_surged":["EliteSiC M3e: 30% conduction loss reduction","vGaN: 50% energy savings → AI DC power","Wolfspeed distress = ON pricing power","AI DC power = NEW primary driver replacing slowing EV","52+ week SiC lead times = scarcity premium"],
            "current_status":"Level 2 — continuation phase. AI power thesis intact. EV partially weakened.",
            "analogs_now":["ETN (transformer lead times 2-3yr)","VST (nuclear baseload for AI)","GEV (grid-scale power)","MPWR (power mgmt ICs for AI servers)"],
        }

        photonics = {
            "thesis":"NVIDIA $4B ($2B LITE + $2B COHR) March 2026 = confirmed structural bottleneck",
            "supply_chain":[
                {"layer":"InP Lasers","ticker":"LITE","status":"CRITICAL SHORTAGE","note":"Only 200G EML supplier at volume. Lead time 2027+."},
                {"layer":"SiPh Foundry","ticker":"Tower/GF","status":"SEVERE","note":"Tower $650M to 3x capacity — still won't meet demand"},
                {"layer":"CPO Packaging","ticker":"TSMC CoWoS","status":"BOTTLENECK","note":"TSMC only foundry for 3D chip-stacking CPO"},
                {"layer":"Photonic Engine","ticker":"POET","status":"EMERGING","note":"Small cap pure-play CPO. Pre-breakout Level 1."},
            ],
            "next_layer":["POET (CPO engine)","MKSI (laser systems for SiPh expansion)","ACLS (ion implant SiPh)","Tower Semiconductor (TSEM)"],
            "already_run":["LITE basket +35% YTD per Citrini","COHR +23% rev growth FY2025"],
        }

        return dict(
            all_candidates=all_scored[:top_n],
            level_1=[s for s in all_scored if s["level"]=="level_1" and not s["regime_trap"]][:top_n],
            level_2=[s for s in all_scored if s["level"]=="level_2" and not s["regime_trap"]][:top_n],
            watch=[s for s in all_scored if s["level"]=="watch"][:top_n],
            avoid=[s for s in all_scored if s["level"]=="avoid"][:8],
            regime_traps=[s for s in all_scored if s["regime_trap"]][:8],
            brewing=brewing[:15],
            # Per-market sorted
            us_long=[s for s in market_buckets["us_equity"] if s["direction"]=="long"][:top_n],
            us_short=[s for s in market_buckets["us_equity"] if s["direction"]=="short"][:top_n],
            us_avoid=[s for s in market_buckets["us_equity"] if s["direction"] in ("avoid_long","avoid_short","neutral")][:top_n//2],
            forex_long=[s for s in market_buckets["forex"] if s["direction"]=="long"][:top_n],
            forex_short=[s for s in market_buckets["forex"] if s["direction"]=="short"][:top_n],
            commodity_long=[s for s in market_buckets["commodity"] if s["direction"]=="long"][:top_n],
            commodity_short=[s for s in market_buckets["commodity"] if s["direction"]=="short"][:top_n],
            crypto_long=[s for s in market_buckets["crypto"] if s["direction"]=="long"][:top_n],
            crypto_short=[s for s in market_buckets["crypto"] if s["direction"]=="short"][:top_n],
            ihsg_long=[s for s in market_buckets["ihsg"] if s["direction"]=="long"][:top_n],
            ihsg_avoid=[s for s in market_buckets["ihsg"] if s["direction"]=="avoid"][:8],
            # EM
            ihsg_known=IHSG_BOTTLENECKS,
            em_recovery=em_signal,
            on_analysis=on_analysis,
            photonics=photonics,
            playbook=dict(structural=quad_str, monthly=quad_mon,
                best=playbook.get("best",[]), worst=playbook.get("worst",[]),
                sectors_overweight=playbook.get("sectors_overweight",[]),
                sectors_underweight=playbook.get("sectors_underweight",[]),
                style=playbook.get("style",""), fx=playbook.get("fx",""), bonds=playbook.get("bonds",""),
            ),
            meta=dict(universe=len(prices)-1, scored=len(all_scored),
                us_long=len([s for s in market_buckets["us_equity"] if s["direction"]=="long"]),
                us_short=len([s for s in market_buckets["us_equity"] if s["direction"]=="short"]),
                forex_long=len([s for s in market_buckets["forex"] if s["direction"]=="long"]),
                commodity_long=len([s for s in market_buckets["commodity"] if s["direction"]=="long"]),
                crypto_long=len([s for s in market_buckets["crypto"] if s["direction"]=="long"]),
                ihsg_long=len([s for s in market_buckets["ihsg"] if s["direction"]=="long"]),
                brewing_count=len(brewing),
            ),
        )
