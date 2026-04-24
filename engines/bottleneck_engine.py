"""engines/bottleneck_engine.py — Full Bottleneck Engine with TP Logic"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from config.settings import BOTTLENECK_PROFILES, TICKER_SECTOR, QUAD_ASSET_PERFORMANCE

# ── Verified bottleneck database (research April 2026) ───────────────────────
KNOWN_BOTTLENECKS: Dict[str, dict] = {
    # PHOTONICS / CPO — NVIDIA $4B March 2026 confirmed
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
    # ON SEMICONDUCTOR — SiC/GaN power
    "ON": {"type":"structural","sub":"ai_power","constraint":0.85,"phase":"level_2",
        "thesis":"EliteSiC M3e: 30% conduction loss reduction. vGaN breakthrough 50% energy savings. AI DC power = new primary driver replacing slowing EV. SiC lead times 52+ weeks. Wolfspeed distress = ON pricing power.",
        "catalyst":"AI DC SiC wins, vGaN production ramp","tp_type":"structural",
        "risk":"EV slowdown; WOLF recovery removes pricing umbrella; AI capex plateau"},
    "WOLF": {"type":"structural","sub":"ai_power","constraint":0.75,"phase":"watch",
        "thesis":"Only US large-scale SiC substrate maker. CHIPS Act strategic asset. Distressed = binary optionality.",
        "catalyst":"Govt rescue/acquisition, debt restructuring","tp_type":"structural","risk":"Bankruptcy real risk"},
    # AI Power Infrastructure
    "VST": {"type":"structural","sub":"ai_power_infra","constraint":0.87,"phase":"level_2",
        "thesis":"Nuclear baseload = only 24/7 clean power for AI. AI DC purchase agreements. Power infrastructure secular bottleneck.",
        "catalyst":"New AI power purchase agreements","tp_type":"structural","risk":"Regulatory, license renewal"},
    "ETN": {"type":"structural","sub":"ai_power_infra","constraint":0.82,"phase":"level_2",
        "thesis":"Transformers/switchgear lead times 2-3 years. Can't build AI DC without Eaton. Infrastructure you can't rush.",
        "catalyst":"Hyperscaler capex guides, order backlog","tp_type":"structural","risk":"Demand normalization"},
    "GEV": {"type":"structural","sub":"ai_power_infra","constraint":0.80,"phase":"level_1",
        "thesis":"Grid-scale power for AI data centers. Transformer/turbine backlog secular. GE Vernova the picks-and-shovels.",
        "catalyst":"Utility and DC power contracts","tp_type":"structural","risk":"Execution risk post-spinoff"},
    # Advanced Packaging (CoWoS bottleneck)
    "AMKR": {"type":"structural","sub":"ai_packaging","constraint":0.78,"phase":"level_2",
        "thesis":"Advanced packaging for AI chips. TSMC overflow. CoWoS-adjacent capacity beneficiary.",
        "catalyst":"AI chip volume ramp","tp_type":"structural","risk":"TSMC insources more capacity"},
    # Healthcare Q3 defensive bottleneck
    "ISRG": {"type":"structural","sub":"healthcare_eq","constraint":0.88,"phase":"level_2",
        "thesis":"Robotic surgery near-monopoly. 8000+ DaVinci installed base. Consumables = recurring. No substitute for trained surgeons.",
        "catalyst":"Procedure volume, FDA approvals, intl expansion","tp_type":"structural","risk":"Competition from CMR/Medtronic"},
    # Gold Q3
    "GLD": {"type":"structural","sub":"precious_metals","constraint":0.78,"phase":"level_2",
        "thesis":"Q3 = best gold regime. Central bank buying record. De-dollarization structural bid. USD TREND bearish (McCullough Apr 2026).",
        "catalyst":"Fed pivot signal, USD breakdown, EM central bank buying","tp_type":"structural","risk":"USD reversal; real yield spike"},
    # Defense
    "LMT": {"type":"structural","sub":"defense","constraint":0.82,"phase":"level_2",
        "thesis":"Defense production bottleneck. NATO 2% GDP = decade-long order book. Missile/munitions can't scale fast enough.",
        "catalyst":"NATO spending, F-35 orders, Ukraine resupply","tp_type":"structural","risk":"Peace negotiations, budget sequestration"},
    # Next-layer photonics
    "MKSI": {"type":"structural","sub":"ai_optics","constraint":0.75,"phase":"watch",
        "thesis":"Laser systems for SiPh fab expansion. Tower+GF expanding SiPh = MKS capital equipment demand.",
        "catalyst":"SiPh foundry capex announcements","tp_type":"structural","risk":"Cyclical capex slowdown"},
    "ACLS": {"type":"structural","sub":"ai_optics","constraint":0.72,"phase":"watch",
        "thesis":"Ion implant for SiPh fabs. Less-known picks-and-shovels for photonics expansion.",
        "catalyst":"Tower/GF SiPh expansion orders","tp_type":"structural","risk":"Limited SiPh-specific revenue"},
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

def _ret(s,n):
    if s is None: return None
    s=pd.to_numeric(s,errors="coerce").dropna()
    if len(s)<n+1: return None
    base=float(s.iloc[-n-1])
    if not math.isfinite(base) or abs(base)<1e-10: return None
    r=float(s.iloc[-1]/base-1)
    return r if math.isfinite(r) else None

def _rs(close,bench,n=63):
    a=_ret(close,n); b=_ret(bench,n)
    if a is None or b is None: return None
    return a-b

def _acc(close,volume,n=40):
    try:
        c=pd.to_numeric(close,errors="coerce").dropna().tail(n).values
        v=pd.to_numeric(volume,errors="coerce").dropna().tail(n).values if volume is not None else None
        if v is None or len(c)<10 or len(v)<10: return 0.5
        nn=min(len(c),len(v)); c=c[-nn:]; v=v[-nn:]
        ret=np.diff(c)/(c[:-1]+1e-10); vv=v[1:]
        if len(ret)<4: return 0.5
        up=ret>0; dn=ret<0
        uv=float(np.mean(vv[up])) if up.any() else float(np.mean(vv))
        dv=float(np.mean(vv[dn])) if dn.any() else float(np.mean(vv))
        return float(np.clip(0.5*(uv/(dv+1e-10)),0.,1.))
    except: return 0.5

def _trend(close,n=63):
    c=pd.to_numeric(close,errors="coerce").dropna().tail(n).values
    if len(c)<20: return False,False,"insufficient"
    half=max(len(c)//3,5)
    hh=float(np.max(c[-half:]))>float(np.max(c[:half]))*1.003
    hl=float(np.min(c[-half:]))>float(np.min(c[:half]))*1.003
    lh=float(np.max(c[-half:]))<float(np.max(c[:half]))*0.997
    ll=float(np.min(c[-half:]))<float(np.min(c[:half]))*0.997
    return hh,hl,"uptrend" if (hh and hl) else "downtrend" if (lh and ll) else "range"

def _compute_tp(close,tp_type="structural",trend_lrr=None,trend_trr=None,trade_trr=None):
    c=pd.to_numeric(close,errors="coerce").dropna()
    if c.empty: return {}
    px=float(c.iloc[-1])
    rv21=float(c.pct_change().dropna().tail(21).std()) if len(c)>22 else 0.02
    rv63=float(c.pct_change().dropna().tail(63).std()) if len(c)>64 else rv21
    hi52=float(c.tail(252).max()) if len(c)>=252 else float(c.max())

    if tp_type=="structural":
        t1=trade_trr if trade_trr and math.isfinite(float(trade_trr)) else px*(1+1.5*rv21*math.sqrt(15))
        t2=trend_trr if trend_trr and math.isfinite(float(trend_trr)) else px*(1+2.5*rv63*math.sqrt(63))
        t3=hi52 if hi52>t2*1.05 else px*(1+4.0*rv63*math.sqrt(63))
        stop=trend_lrr if trend_lrr and math.isfinite(float(trend_lrr)) else px*(1-1.5*rv63)
        rat="T1=TRADE TRR: trim 25% | T2=TREND TRR: trim 50% | T3=ATH/resistance: trail 25%. EXIT on TREND LRR break."
        sz="2-4% portfolio. Add 1.5x on breakout above T2 (Hedgeye 150-200bps breakout rule)."
    elif tp_type=="squeeze":
        t1=px*1.30; t2=px*1.55; t3=px*2.10; stop=px*0.88
        rat="T1=+30% trim 50% | T2=+55% trim 40% | T3=+110% trail 10%. TIME STOP: 5 days. SI exhaustion = exit."
        sz="1-2% MAX. Hard -12% stop. Time stop: exit if no breakout in 5 days."
    elif tp_type=="commodity":
        t1=px*(1+1.0*rv63); t2=px*(1+2.0*rv63); t3=hi52; stop=px*0.85
        rat="T1=+1σ 63d: trim 33% | T2=+2σ 63d or curve flip to contango: trim 33% | T3=52w high: trail 34%. -15% hard."
        sz="1-3% portfolio. Commodity bottleneck = higher vol, size smaller."
    elif tp_type=="ihsg":
        t1=trade_trr if trade_trr and math.isfinite(float(trade_trr)) else px*1.12
        t2=trend_trr if trend_trr and math.isfinite(float(trend_trr)) else px*1.25
        t3=None; stop=px*0.92
        rat="T1=TRADE TRR or +12%: trim 50% on any foreign net sell signal | T2=TREND TRR or +25%: trim 50%. Exit 100% on 2 consecutive foreign net sell days."
        sz="2-4% portfolio. CRITICAL: watch IDR — if IDR weakens >1.5% in 2 days, exit."
    elif tp_type=="crypto":
        t1=px*1.40; t2=px*2.0; t3=None; stop=px*0.80
        rat="T1=+40% trim 50% | T2=+100% trim 40%. EXIT 14 DAYS BEFORE major vesting unlock. -20% hard stop."
        sz="0.5-1% MAX. Highest risk tier. Exchange reserve drain = confirm; exchange reserve normalizing = exit."
    else:
        t1=trend_trr or px*1.15; t2=px*1.30; t3=None; stop=trend_lrr or px*0.90
        rat="Standard TRR exits."; sz="2-4% portfolio."

    rr=round((t2-px)/(px-stop),2) if t2 and stop and px>stop else None
    return dict(t1=round(t1,4) if t1 else None, t2=round(t2,4) if t2 else None,
                t3=round(t3,4) if t3 else None, stop=round(stop,4) if stop else None,
                rr_ratio=rr, tp_rationale=rat, sizing_note=sz)

class BottleneckEngine:
    def run(self,prices,volumes=None,quad_str="Q3",quad_mon="Q2",
            benchmark="SPY",asset_ranges=None,min_rs=-0.10,top_n=25):
        volumes=volumes or {}; bench=prices.get(benchmark)
        qk=quad_str.upper(); qk_mon=quad_mon.upper()
        regime_allows={"Q1":{"structural":True,"squeeze":True,"commodity":False,"ihsg":True,"crypto":True},
                       "Q2":{"structural":True,"squeeze":True,"commodity":True,"ihsg":True,"crypto":True},
                       "Q3":{"structural":True,"squeeze":False,"commodity":True,"ihsg":True,"crypto":False},
                       "Q4":{"structural":False,"squeeze":False,"commodity":False,"ihsg":False,"crypto":False}
                       }.get(qk,{"structural":True})
        playbook=QUAD_ASSET_PERFORMANCE.get(quad_str,{}); scored=[]

        for ticker,close in prices.items():
            if ticker==benchmark: continue
            close=pd.to_numeric(close,errors="coerce").dropna()
            if len(close)<30: continue
            sector=TICKER_SECTOR.get(ticker,"generic")
            prof=BOTTLENECK_PROFILES.get(sector,BOTTLENECK_PROFILES["generic"])
            constraint=float(prof["constraint"])
            kb=KNOWN_BOTTLENECKS.get(ticker,{})
            known_phase=kb.get("phase",None); known_tp=kb.get("tp_type","structural")
            rf_str=float(prof.get(qk,0.5)); rf_mon=float(prof.get(qk_mon,0.5))
            regime_fit=0.65*rf_str+0.35*rf_mon
            btn_type=kb.get("type","structural")
            rs3=_rs(close,bench,63) if bench is not None else None
            rs21=_rs(close,bench,21) if bench is not None else None
            if rs3 is not None and rs3<min_rs and not kb: continue
            rs_score=float(np.clip(0.5+3.0*(rs3 or 0.0),0.0,1.0))
            vol_s=volumes.get(ticker)
            hh,hl,trd=_trend(close,63)
            trend_score=float(np.clip(0.5+(0.4 if hh else -0.1)+(0.4 if hl else -0.1),0.0,1.0))
            acc_s=_acc(close,vol_s,40)
            c60=close.tail(60).values
            rp=(float(c60[-1])-float(np.min(c60)))/max(float(np.max(c60))-float(np.min(c60)),1e-9)
            rp_label="at_resistance" if rp>=0.90 else "approaching_breakout" if rp>=0.75 else "at_support" if rp<=0.10 else "mid_range"
            hi52=float(close.tail(252).max()) if len(close)>=252 else float(close.max())
            lo52=float(close.tail(252).min()) if len(close)>=252 else float(close.min())
            pct_from_hi=(float(close.iloc[-1])-hi52)/max(hi52,1e-9)
            pct_from_lo=(float(close.iloc[-1])-lo52)/max(lo52,1e-9)
            if known_phase: level=known_phase
            elif trd=="uptrend": level="level_1" if rp_label in ("at_resistance","approaching_breakout") else "level_2"
            elif trd=="range" and acc_s>=0.60 and rp>=0.70: level="level_1"
            elif trd=="downtrend": level="avoid"
            else: level="watch"
            regime_trap=(qk in ("Q3","Q4") and btn_type=="squeeze") or (qk=="Q4" and btn_type!="structural")
            rr_data=(asset_ranges or {}).get(ticker,{})
            tp=_compute_tp(close,known_tp,rr_data.get("trend_lrr"),rr_data.get("trend_trr"),rr_data.get("trade_trr"))
            score=(0.30*constraint+0.25*regime_fit+0.20*trend_score+0.15*rs_score+0.10*acc_s)
            if level=="avoid": score*=0.30
            if regime_trap: score*=0.40
            if kb: score=min(score+0.08,1.0)
            if pct_from_lo<0.30 and acc_s>=0.65 and constraint>=0.75: score=min(score+0.08,1.0)
            score=float(np.clip(score,0.0,1.0))
            px=float(close.iloc[-1])
            scored.append(dict(
                ticker=ticker,sector=sector,btn_type=btn_type,level=level,
                score=round(score,3),constraint=round(constraint,2),
                regime_fit=round(regime_fit,2),trend=trd,hh=hh,hl=hl,
                acc=round(acc_s,2),rs_3m=round(rs3,4) if rs3 else None,
                rs_1m=round(rs21,4) if rs21 else None,rs_score=round(rs_score,2),
                trend_score=round(trend_score,2),range_pos=round(rp,2),range_label=rp_label,
                pct_from_hi=round(pct_from_hi,3),pct_from_lo=round(pct_from_lo,3),px=round(px,4),
                known=bool(kb),known_thesis=kb.get("thesis",""),known_catalyst=kb.get("catalyst",""),
                known_risk=kb.get("risk",""),regime_trap=regime_trap,tp=tp,
                rationale=kb.get("thesis","")[:80] if kb else f"{sector}|{trd}|RS {rs3:.1%}" if rs3 else sector,
            ))

        scored.sort(key=lambda x:x["score"],reverse=True)

        on_analysis={"ticker":"ON","is_bottleneck":True,"type":"SiC/GaN structural",
            "why_surged":["EliteSiC M3e: 30% conduction loss reduction → 800V EV traction","vGaN: 50% energy savings → AI DC power supply","Wolfspeed distress = ON pricing power","AI DC power = NEW primary driver replacing slowing EV","52+ week SiC lead times = scarcity premium"],
            "current_status":"Level 2 — continuation phase. AI power thesis intact. EV partially weakened.",
            "analogs_now":["ETN (transformer lead times 2-3yr)","VST (nuclear baseload for AI)","GEV (grid-scale power)","MPWR (power mgmt ICs for AI servers)"],
        }
        photonics={"thesis":"NVIDIA $4B ($2B LITE + $2B COHR) March 2026 = confirmed structural bottleneck",
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
            all_candidates=scored[:top_n],
            level_1=[s for s in scored if s["level"]=="level_1" and not s["regime_trap"]][:top_n],
            level_2=[s for s in scored if s["level"]=="level_2" and not s["regime_trap"]][:top_n],
            watch=[s for s in scored if s["level"]=="watch"][:top_n],
            avoid=[s for s in scored if s["level"]=="avoid"][:8],
            regime_traps=[s for s in scored if s["regime_trap"]][:8],
            ihsg_known=IHSG_BOTTLENECKS,
            on_analysis=on_analysis,
            photonics=photonics,
            playbook=dict(structural=quad_str,monthly=quad_mon,
                best=playbook.get("best",[]),worst=playbook.get("worst",[]),
                sectors_overweight=playbook.get("sectors_overweight",[]),
                sectors_underweight=playbook.get("sectors_underweight",[]),
                style=playbook.get("style",""),fx=playbook.get("fx",""),bonds=playbook.get("bonds",""),
            ),
            regime_filter=regime_allows,
            meta=dict(universe=len(prices)-1,scored=len(scored)),
        )
