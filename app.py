# -*- coding: utf-8 -*-
"""app.py — MacroRegime Pro v18.3 | Client-Ready Dashboard
FIXES: Gamma render, sidebar icons, Alpha Centre table overhaul, ATH scanner, option prominence.
"""
from __future__ import annotations
import math, logging
from typing import Optional, Callable, Dict, List
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="MacroRegime Pro", layout="wide", initial_sidebar_state="expanded")

# ══════════════════════════════════════════════════════════════════════════════
# CSS — Client-ready clean styling
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    .main .block-container { padding: 1.5rem 2.5rem 3rem 2.5rem; max-width: 1400px; }

    /* Typography */
    h1 { font-size: 1.5rem !important; font-weight: 700 !important; letter-spacing: -0.3px; margin-bottom: 0.5rem !important; color: #e6edf3; }
    h2 { font-size: 1.15rem !important; font-weight: 600 !important; margin-top: 1.5rem !important; margin-bottom: 0.75rem !important; color: #e6edf3; border-bottom: 1px solid #30363d; padding-bottom: 0.4rem; }
    h3 { font-size: 1rem !important; font-weight: 600 !important; margin-top: 1rem !important; margin-bottom: 0.5rem !important; color: #c9d1d9; }
    p, div { font-size: 0.85rem !important; color: #c9d1d9; }

    /* Metric Cards */
    .metric-card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; transition: border-color 0.2s; }
    .metric-card:hover { border-color: #484f58; }
    .metric-card h4 { margin: 0 0 6px 0; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.8px; color: #8b949e; font-weight: 600; }
    .metric-card .big { font-size: 1.4rem; font-weight: 700; color: #e6edf3; }
    .metric-card .sub { font-size: 0.78rem; color: #8b949e; margin-top: 4px; line-height: 1.4; }

    /* Tier Cards */
    .tier-card { border-radius: 10px; padding: 12px 16px; margin: 12px 0; border-left: 4px solid; }
    .tier-basi { background: #da36330d; border-color: #da3633; }
    .tier-building { background: #2386360d; border-color: #238636; }
    .tier-chase { background: #9e6a030d; border-color: #9e6a03; }
    .tier-wait { background: #30363d40; border-color: #484f58; }
    .tier-ath { background: #1f6feb0d; border-color: #1f6feb; }
    .tier-title { font-size: 0.85rem; font-weight: 700; margin-bottom: 2px; }
    .tier-desc { font-size: 0.78rem; color: #8b949e; }

    /* Badges */
    .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.3px; }
    .badge-green { background: #23863620; color: #3fb950; border: 1px solid #23863640; }
    .badge-red { background: #da363320; color: #f85149; border: 1px solid #da363340; }
    .badge-yellow { background: #9e6a0320; color: #d29922; border: 1px solid #9e6a0340; }
    .badge-blue { background: #1f6feb20; color: #58a6ff; border: 1px solid #1f6feb40; }
    .badge-gray { background: #30363d; color: #8b949e; border: 1px solid #484f58; }
    .badge-purple { background: #8957e520; color: #a371f7; border: 1px solid #8957e540; }

    /* Tables */
    .stDataFrame { font-size: 0.82rem !important; }
    .stDataFrame th { font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.5px; color: #8b949e !important; background: #161b22 !important; }
    .stDataFrame td { font-size: 0.82rem !important; color: #c9d1d9 !important; }

    /* Expanders */
    div[data-testid="stExpander"] { border: 1px solid #30363d; border-radius: 10px; margin-bottom: 12px; background: #0d1117; }
    div[data-testid="stExpander"] details { border: none !important; }
    div[data-testid="stExpander"] summary { font-size: 0.9rem !important; font-weight: 600 !important; color: #c9d1d9 !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 6px; background: #161b22; padding: 6px; border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 18px; font-size: 0.82rem !important; font-weight: 500 !important; border-radius: 8px; color: #8b949e !important; }
    .stTabs [data-baseweb="tab-highlight"], .stTabs [aria-selected="true"] { background: #1f6feb20 !important; color: #58a6ff !important; font-weight: 600 !important; }

    /* Action Box */
    .action-box { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 16px 20px; margin: 12px 0; }
    .action-box h4 { margin: 0 0 8px 0; font-size: 0.9rem; font-weight: 700; }
    .action-long { color: #3fb950; }
    .action-short { color: #f85149; }

    /* Info boxes */
    .info-box { background: #1f6feb10; border: 1px solid #1f6feb30; border-radius: 10px; padding: 12px 16px; margin: 10px 0; font-size: 0.85rem; }
    .warn-box { background: #9e6a0310; border: 1px solid #9e6a0330; border-radius: 10px; padding: 12px 16px; margin: 10px 0; font-size: 0.85rem; }
    .error-box { background: #da363310; border: 1px solid #da363330; border-radius: 10px; padding: 12px 16px; margin: 10px 0; font-size: 0.85rem; }

    hr { border-color: #30363d; margin: 1.5rem 0; opacity: 0.5; }

    /* Sidebar */
    [data-testid="stSidebar"] .stRadio label { font-size: 0.88rem !important; font-weight: 500 !important; padding: 6px 0 !important; }
    [data-testid="stSidebar"] h2 { font-size: 1.1rem !important; border-bottom: none !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _sf(x):
    if x is None: return None
    try: f=float(x); return f if math.isfinite(f) else None
    except: return None

def ff(x, d=2):
    if x is None: return "—"
    try: f=float(x); return f"{f:,.{d}f}" if math.isfinite(f) else "—"
    except: return "—"

def fp(x):
    if x is None: return "—"
    try: f=float(x); return f"{f:+.1%}" if math.isfinite(f) else "—"
    except: return "—"

def qnc(q):
    return {"Q1":"Goldilocks (Growth up, Inflation down)","Q2":"Reflation / Knife Fights","Q3":"Stagflation","Q4":"Deflation"}.get(q,"—")

def qcard(label, quad, conf, sub=""):
    c={"Q1":"#3fb950","Q2":"#d29922","Q3":"#f85149","Q4":"#58a6ff"}.get(quad,"#8b949e")
    return f"""<div class="metric-card"><h4>{label}</h4><div class="big" style="color:{c}">{quad}</div><div class="sub">Conf: {conf:.0%} {sub}</div></div>"""

def prob_bar(probs, title="Transition Probabilities"):
    if not probs: return go.Figure()
    sp=sorted(probs.items(), key=lambda x:x[1], reverse=True)
    cols=[{"Q1":"#3fb950","Q2":"#d29922","Q3":"#f85149","Q4":"#58a6ff"}.get(q,"#8b949e") for q,_ in sp]
    fig=go.Figure(go.Bar(x=[q for q,_ in sp], y=[v for _,v in sp], marker_color=cols, text=[f"{v:.0%}" for _,v in sp], textposition="outside"))
    fig.update_layout(title=title, showlegend=False, margin=dict(l=20,r=20,t=40,b=20), height=220, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#c9d1d9", yaxis=dict(showgrid=False), xaxis=dict(showgrid=False))
    return fig

def _sequence_pills(sq, mq):
    seq=["Q1","Q2","Q3","Q4"]; out=[]
    for q in seq:
        active=(q==sq or q==mq)
        c={"Q1":"#3fb950","Q2":"#d29922","Q3":"#f85149","Q4":"#58a6ff"}.get(q,"#8b949e")
        out.append(f'<span style="display:inline-block;padding:4px 12px;border-radius:16px;background:{c}20;color:{c};border:1px solid {c}40;font-size:0.78rem;font-weight:600;margin-right:6px">{q}{" ACTIVE" if active else ""}</span>')
    return " ".join(out)

def _rr_levels(px, lrr, trr, direction="long"):
    if px is None or lrr is None or trr is None: return None
    if not all(math.isfinite(x) for x in [px,lrr,trr]): return None
    if trr <= lrr: return None
    band=trr-lrr; pos=(px-lrr)/band
    if direction=="long":
        entry=round(lrr,2); tp1=round(lrr+band*0.55,2); tp2=round(trr,2); stop=round(lrr*0.985,2)
        rr=(tp1-entry)/(entry-stop) if (entry-stop)>0.001 else 0
        can_enter=pos<=0.55; near_target=pos>=0.75; near_entry=pos<=0.35
        action="ENTER NOW" if near_entry else ("CHASE OK" if can_enter else "TAKE PROFIT" if near_target else "WAIT")
        hold="TRADE (1-3w)" if rr<2.5 else "TREND (3M+)"
    else:
        entry=round(trr,2); tp1=round(trr-band*0.55,2); tp2=round(lrr,2); stop=round(trr*1.015,2)
        rr=(entry-tp1)/(stop-entry) if (stop-entry)>0.001 else 0
        can_enter=pos>=0.45; near_target=pos<=0.25; near_entry=pos>=0.65
        action="ENTER NOW" if near_entry else ("CHASE OK" if can_enter else "COVER SHORT" if near_target else "WAIT")
        hold="TRADE (1-3w)"
    return dict(entry=entry,tp1=tp1,tp2=tp2,stop=stop,rr=round(rr,2),pos=round(pos,2),can_enter=can_enter,near_target=near_target,near_entry=near_entry,action=action,hold=hold,extended=pos>0.75)

def _merge_with_options(rl, opt, direction="long"):
    if not opt or not opt.get("ok"): return rl
    lv=opt.get("long_levels") if direction=="long" else opt.get("short_levels")
    if lv and lv.get("ev_ok"):
        rl["entry"]=max(rl["entry"], lv.get("entry", rl["entry"])) if direction=="long" else min(rl["entry"], lv.get("entry", rl["entry"]))
        rl["tp1"]=lv.get("tp1", rl["tp1"]); rl["tp2"]=lv.get("tp2", rl["tp2"])
        if lv.get("stop"): rl["stop"]=lv["stop"]
        if lv.get("rr"): rl["rr"]=lv["rr"]
        rl["max_pain_note"]=lv.get("max_pain_note","")
    return rl

def _compute_dxy_corr(prices):
    result={}; dxy=prices.get("DX-Y.NYB")
    if dxy is None: return result
    dxy=pd.to_numeric(dxy,errors="coerce").dropna()
    if len(dxy)<22: return result
    for label,ticker in {"SPX":"SPY","Brent Oil":"BZ=F","CRB Index":"DBA","Gold":"GLD","Bitcoin":"BTC-USD"}.items():
        combined=pd.DataFrame({"dxy":dxy}).join(pd.DataFrame({"asset":pd.to_numeric(prices.get(ticker, pd.Series(dtype=float)),errors="coerce")}),how="inner")
        if len(combined)<15: continue
        window=15; c=float(combined["dxy"].tail(window).corr(combined["asset"].tail(window)))
        if math.isfinite(c): result[label]=round(c,2)
    return result

def _render_dxy_section(prices,dxy_corr,sq):
    if not dxy_corr: st.info("DXY data belum tersedia."); return
    dxy=prices.get("DX-Y.NYB"); dxy_trend="—"
    if dxy is not None:
        dxy=pd.to_numeric(dxy,errors="coerce").dropna()
        if len(dxy)>=22:
            r21=float(dxy.iloc[-1]/dxy.iloc[-22]-1)
            dxy_trend="BEARISH" if r21<-0.005 else ("BULLISH" if r21>0.005 else "NEUTRAL")
    st.markdown(f"**KEY $USD CORRELATIONS (15D)** | DXY Trend: `{dxy_trend}`")
    st.caption("<-- Negative = benefits from USD weakness | Positive = benefits from USD strength -->")
    rows=[{"Asset":l,"15D Corr":c,"Direction":"<- USD bearish" if c<-0.2 else ("-> USD bullish" if c>0.2 else "~neutral")} for l,c in dxy_corr.items()]
    st.dataframe(pd.DataFrame(rows).style.background_gradient(subset=["15D Corr"],cmap="RdYlGn",vmin=-1,vmax=1), hide_index=True, use_container_width=True, height=195)
    btc_corr=dxy_corr.get("Bitcoin")
    if btc_corr is not None:
        if "BEARISH" in dxy_trend and btc_corr<-0.3 and sq!="Q4":
            msg=f"BTC: DXY Bearish (corr {btc_corr:+.2f}) -> **BTC Bullish TREND intact**. LONG IBIT."
        elif "BULLISH" in dxy_trend:
            msg=f"BTC: DXY Bullish (corr {btc_corr:+.2f}) -> **BTC headwind**. Scale back."
        else:
            msg=f"BTC: DXY neutral (corr {btc_corr:+.2f}) -> Watch TREND signal."
        st.markdown(f'<div class="info-box">{msg}</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GAMMA REGIME RENDER — FIXED v18.3
# ══════════════════════════════════════════════════════════════════════════════
def _render_gamma(gd):
    """Render gamma regime card. Robust parsing for various data shapes."""
    if not gd:
        return '<div class="metric-card"><h4>GAMMA REGIME</h4><div class="big" style="color:#8b949e">UNAVAILABLE</div><div class="sub">Gamma engine not loaded</div></div>'

    # Try multiple key patterns
    regime = gd.get("regime") or gd.get("gamma_regime") or gd.get("status") or "UNKNOWN"
    note = gd.get("note") or gd.get("message") or gd.get("rationale") or ""
    throttle = gd.get("throttle")

    # Normalize regime string
    regime = str(regime).upper().replace(" ", "_")
    if regime in ("", "NONE", "NAN", "NULL"): regime = "UNKNOWN"

    c = "#3fb950" if "LONG" in regime else "#f85149" if "SHORT" in regime else "#d29922" if "FLIP" in regime else "#8b949e"

    # Build sub text
    sub_parts = []
    if throttle: sub_parts.append(f"Throttle: {throttle}")
    if note: sub_parts.append(note[:60])
    sub = " | ".join(sub_parts) if sub_parts else "Gamma exposure approximation"

    return f'<div class="metric-card"><h4>GAMMA REGIME</h4><div class="big" style="color:{c}">{regime.replace("_", " ")}</div><div class="sub">{sub}</div></div>'

def _render_lev(ld):
    if not ld or not ld.get("ok"): return ""
    m=ld.get("total_mcap_b")
    return f'<div class="metric-card"><h4>LEVERAGED ETF AUM</h4><div class="big">${m:.1f}B</div><div class="sub">{ld.get("note","")}</div></div>' if m else ""

# ══════════════════════════════════════════════════════════════════════════════
# UNIVERSAL TICKER TABLE — v18.3 with Option + Gamma integration
# ══════════════════════════════════════════════════════════════════════════════

def _build_alpha_table(items: List[dict], side: str, opt_engine=None, gamma_dict=None) -> pd.DataFrame:
    """Build Alpha Centre table with full option/gamma integration."""
    rows = []
    for item in items:
        ticker = item.get("ticker", "")
        px = _sf(item.get("px"))
        lrr = _sf(item.get("lrr"))
        trr = _sf(item.get("trr"))
        ev = _sf(item.get("ev")) or 0
        rl = _rr_levels(px, lrr, trr, side)

        # Option data
        opt_data = None
        opt_level = "—"; opt_signal = "—"; opt_dte = "—"; opt_iv = "—"
        if opt_engine and px and px > 0 and not ticker.endswith(".JK") and not ticker.startswith("^") and "=F" not in ticker:
            try:
                opt_data = opt_engine.analyze(ticker, px, lrr, trr, item.get("composite", "neutral"))
            except Exception:
                pass

        if opt_data and opt_data.get("ok"):
            opt_level = f"MP:{ff(opt_data.get('max_pain'))}"
            opt_signal = opt_data.get("options_signal", "—")
            dte = opt_data.get("days_to_exp", 0)
            opt_dte = f"{dte}d" if dte else "—"
            opt_iv = fp(opt_data.get("atm_iv"))
            if rl: rl = _merge_with_options(rl, opt_data, side)

        # Gamma data
        gamma_lvl = "—"; gamma_signal = "—"
        if gamma_dict and ticker in gamma_dict:
            gd = gamma_dict[ticker]
            if isinstance(gd, dict):
                gamma_lvl = gd.get("key_level", "—")
                gamma_signal = gd.get("signal", "—")

        # Determine status
        if rl:
            if rl["near_target"]: status = "TAKE PROFIT"; status_cat = "basi"
            elif rl["near_entry"]: status = "ENTER NOW"; status_cat = "building"
            elif rl["can_enter"]: status = "CHASE OK"; status_cat = "chase"
            else: status = "WAIT"; status_cat = "wait"
        else:
            status = "—"; status_cat = "wait"

        # Direction & Rec
        direction = "LONG" if side == "long" else "SHORT"
        rec = f"{direction} {status}"
        if opt_signal != "—": rec += f" | Opt:{opt_signal}"
        if gamma_signal != "—": rec += f" | Gam:{gamma_signal}"

        # Hold duration from option if available
        hold = rl.get("hold", "—") if rl else "—"
        if opt_data and opt_data.get("ok"):
            dte = opt_data.get("days_to_exp", 0)
            if dte <= 14: hold = "SWING (1-2w)"
            elif dte <= 45: hold = "TRADE (1-3w)"
            else: hold = "TREND (2M+)"

        rows.append({
            "Ticker": ticker,
            "Px": ff(px),
            "LRR": ff(lrr),
            "TRR": ff(trr),
            "Entry": ff(rl["entry"]) if rl else "—",
            "TP1": ff(rl["tp1"]) if rl else "—",
            "TP2": ff(rl["tp2"]) if rl else "—",
            "Stop": ff(rl["stop"]) if rl else "—",
            "R/R": ff(rl["rr"]) if rl else "—",
            "Hold": hold[:14],
            "Status": status,
            "StatusCat": status_cat,
            "Opt Level": opt_level,
            "Opt Signal": opt_signal,
            "Gam Level": gamma_lvl,
            "Gam Sig": gamma_signal,
            "Direction": direction,
            "Rec": rec,
            "EV": round(ev, 2),
            "Quality": item.get("quality", "—"),
            "Stretch": item.get("stretch", "—"),
            "Regime": "OK" if item.get("regime_fit") else "WARN",
        })

    df = pd.DataFrame(rows)
    # Sort by EV descending
    if not df.empty and "EV" in df.columns:
        df = df.sort_values("EV", ascending=False)
    return df

# ══════════════════════════════════════════════════════════════════════════════
# HEDGEYE FALLBACK NARRATIVES
# ══════════════════════════════════════════════════════════════════════════════
HEDGEYE_FALLBACK_NARRATIVES = [
    {"name":"Silver Supercycle","score":0.92,"regime":"Q3","quad_bias":"Q3/Q2","thesis":"SLV +143% since May 2025. Dual demand: industrial (AI/EVs) + safe haven (inflation hedge). Supply deficit widens. Hedgeye top pick in Q3.","tickers":["SLV","SI=F","SIL","SILJ","GDXJ","GDX"],"best":["SLV","SILJ","GDXJ"],"worst":["XLK","MAGS"],"invalidators":["Deflation signal (Q4)","DXY sustained Bullish TREND","Global growth collapse"]},
    {"name":"Gold Secular Bull","score":0.88,"regime":"Q3","quad_bias":"Q3/Q4","thesis":"McCullough: 'Single best asset allocation in Q3.' Central bank buying accelerating. De-dollarization structural tailwind. GLD holds through regime shifts.","tickers":["GLD","GC=F","GDX","GDXJ","PPLT","AEM","WPM","FNV","RGLD"],"best":["GLD","GDX","GDXJ"],"worst":["HYG","IWM"],"invalidators":["Q4->Q1 direct transition (gold fades)","Rapid DXY reversal to Bullish TREND"]},
    {"name":"Defense Reshoring","score":0.85,"regime":"ALL","quad_bias":"Q2/Q3","thesis":"NATO 2%+ GDP commitment structural. DOGE doesn't cut defense. Geopolitical premium embedded. ITA + LMT + KTOS secular long regardless of Quad.","tickers":["ITA","LMT","RTX","NOC","KTOS","GD","PLTR","BWXT","SAIC"],"best":["ITA","KTOS","PLTR"],"worst":["XLU"],"invalidators":["Global peace agreement (tail risk)","Budget reconciliation cuts defense (low prob)"]},
    {"name":"AI Power Infrastructure","score":0.83,"regime":"Q1/Q2","quad_bias":"Q1/Q2","thesis":"AI hyperscalers need 24/7 firm power. Nuclear + gas turbines only solution at scale. VST, CEG, GEV securing long-term contracts. Secular regardless of Quad.","tickers":["VST","CEG","GEV","ETN","VRT","NRG","GRID","NEE"],"best":["VST","CEG","GEV"],"worst":["INTC","XLU"],"invalidators":["AI capex cycle pause","Rate spike destroying power project economics"]},
    {"name":"Energy Offense Q2","score":0.80,"regime":"Q2","quad_bias":"Q2","thesis":"Q2 Knife Fights = Energy offense. OIH +oil services operating leverage. BNO/XOP direct commodity price leverage. DAR/MTDR added April 2026.","tickers":["XLE","OIH","BNO","XOP","DAR","MTDR","CL=F","BZ=F"],"best":["OIH","BNO","XOP"],"worst":["XLU","XLP"],"invalidators":["Demand collapse (Q4 signal)","OPEC+ surprise production increase"]},
    {"name":"International Country Rotation","score":0.78,"regime":"Q2","quad_bias":"Q1/Q2","thesis":"JPXN +37% Q1 2026. EIS +21.8% since Nov add. TUR +10.3%. USD bearish TREND = EM tailwind. Hedgeye ETF Pro Plus: diversify away from US concentration.","tickers":["JPXN","EIS","TUR","NORW","EWZ","EWW","EIDO","GLIN"],"best":["JPXN","EIS","TUR"],"worst":["SPY","IWM"],"invalidators":["DXY reversal to Bullish TREND","Global risk-off (Q4)"]},
    {"name":"Housing Rate Sensitivity","score":0.72,"regime":"Q2","quad_bias":"Q1/Q2","thesis":"ITB as 'long duration equity proxy.' If 2s/10s/30s all bearish TREND -> yields fall -> housing stocks win. Hedgeye added ITB to ETF Pro Plus.","tickers":["ITB","XHB","DHI","LEN","PHM","NVR"],"best":["ITB","DHI"],"worst":["XLU"],"invalidators":["30yr mortgage stays above 7%","Growth collapse (Q3->Q4)"]},
    {"name":"Bitcoin Reflation","score":0.75,"regime":"Q1/Q2/Q3","quad_bias":"ANY except Q4","thesis":"Keith May 6 2026: 'Bitcoin Is Back In The Book.' DXY/BTC 15D corr = -0.83. Any quad other than Q4: bitcoin = biggest digital asset position. Bullish TREND signal confirmed.","tickers":["IBIT","FBTC","BTC-USD","MSTR"],"best":["IBIT"],"worst":["MSTY","BITS","BLOK"],"invalidators":["Q4 signal (ONLY exception -- exit BTC)","DXY Bullish TREND reversal"]},
    {"name":"Copper Industrial Demand","score":0.70,"regime":"Q2","quad_bias":"Q2","thesis":"AI data centers + EV transition + grid buildout = secular copper demand. CPER/SLX as industrial metals play. Q2 reflation = commodity offense.","tickers":["CPER","HG=F","SLX","COPX","JJC"],"best":["CPER","SLX"],"worst":["XLU"],"invalidators":["China growth collapse","Q4 demand destruction"]},
    {"name":"Indonesia Commodity Supercycle","score":0.65,"regime":"Q2/Q3","quad_bias":"Q2/Q3","thesis":"EIDO = coal + nickel + CPO + geothermal. Commodity EM in Q2 reflation. PGEO geothermal = renewable + commodity hybrid. OSV sector (WINS/LEAD) = hulu services demand.","tickers":["EIDO","PGEO.JK","ADRO.JK","INCO.JK","MDKA.JK","WINS.JK","NCKL.JK"],"best":["EIDO","PGEO.JK","NCKL.JK"],"worst":["TLKM.JK"],"invalidators":["Global growth collapse (Q4)","CNY devaluation crashing EM commodity prices"]},
]

HEDGEYE_FALLBACK_DISCOVERY = [
    {"name":"AI Photonics Scarcity","category":"bottleneck","stage":"active","confidence":0.88,"thesis":"LITE sole supplier 200G EML lasers. POET co-packaged optics removing TDP limits. COHR 25% CW market share. NVIDIA committed $2B. Constraint = 97% for ai_optics sector.","beneficiary_tickers":["LITE","POET","COHR","CIEN","VIAV"],"fade_tickers":["INTC","SMCI"],"confirmation_signal":"LITE/COHR earnings guidance + NVIDIA capex commentary","invalidators":["China photonics capacity scaling","AI capex cycle pause"]},
    {"name":"SiC Power Semiconductor Monopoly","category":"bottleneck","stage":"active","confidence":0.84,"thesis":"WOLF only US large-scale SiC substrate maker. CHIPS Act strategic asset. 30% conduction loss reduction = AI/EV/defense critical. STM/ON license WOLF technology.","beneficiary_tickers":["WOLF","ON","STM","MPWR"],"fade_tickers":["legacy Si wafer players"],"confirmation_signal":"EV OEM adoption + DOD qualification letters","invalidators":["China SiC subsidies","Margin compression on price pressure"]},
    {"name":"Silver Physical Squeeze","category":"narrative","stage":"building","confidence":0.78,"thesis":"Silver industrial demand (solar panels, AI chip plating) accelerating while mine supply flat. LBMA vault levels declining. SLV +143% since May 2025 -- still NOT consensus.","beneficiary_tickers":["SLV","SILJ","SIL","GDXJ"],"fade_tickers":["MSTY","BLOK"],"confirmation_signal":"LBMA inventory <150M oz + solar installation data beat","invalidators":["India demand collapse","Q4 deflation signal"]},
    {"name":"Japan Yen Structural Weakness -> JPXN","category":"macro_rotation","stage":"active","confidence":0.82,"thesis":"Yen bearish TREND = Japanese exporters win in USD terms. JPXN +37% Q1 2026. Bank of Japan ultra-dovish while Fed pivots. Hedgeye ETF Pro Plus top international long.","beneficiary_tickers":["JPXN","EWJ","DXJ"],"fade_tickers":["YCS","FXY"],"confirmation_signal":"USD/JPY sustained above 145 + BoJ no action","invalidators":["BoJ surprise rate hike above 1%","G7 currency intervention"]},
    {"name":"Indonesia OSV-Hulu Bottleneck","category":"bottleneck","stage":"brewing","confidence":0.65,"thesis":"Pertamina hulu expansion + BUMD gas development = OSV fleet utilization >90%. WINS/LEAD = near-monopoly on domestic offshore supply vessels. No new vessel delivery until 2026.","beneficiary_tickers":["WINS.JK","LEAD.JK","SHIP.JK","ELSA.JK"],"fade_tickers":["BUMI.JK"],"confirmation_signal":"Pertamina capex budget Q2 + OSV day rate >$18k","invalidators":["Pertamina budget freeze","Oil price collapse below $60"]},
]

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — v18.3 with icons
# ══════════════════════════════════════════════════════════════════════════════
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False
if "mq_override" not in st.session_state: st.session_state.mq_override = "Auto"

with st.sidebar:
    st.markdown("## MacroRegime Pro")
    st.markdown("<div style='font-size:0.75rem;color:#8b949e'>Hedgeye GIP | v18.3 | Options + Greeks</div>", unsafe_allow_html=True)
    st.divider()
    page = st.radio("", [
        "Dashboard","GIP Model","Risk Ranges","Alpha Center",
        "Leaderboard","Global Quad","IHSG",
        "Narratives","Discovery","Health","Playbook",
    ], label_visibility="collapsed")
    st.divider()
    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"Snapshot: {snapshot_age_str()}")
    c1,c2=st.columns(2)
    with c1:
        if st.button("Refresh", use_container_width=True): st.session_state.loading=True
    with c2:
        if st.button("Force Rebuild", use_container_width=True):
            st.session_state.loading=True; st.session_state.snap=None
    with st.expander("Universe"):
        inc_us = st.checkbox("US Stocks",True); inc_fx = st.checkbox("Forex",True)
        inc_comm = st.checkbox("Commodities",True); inc_cryp = st.checkbox("Crypto",True)
        inc_ihsg = st.checkbox("IHSG",True)
    with st.expander("Quad Override"):
        mq_ov = st.selectbox("Monthly Quad:",["Auto","Q1","Q2","Q3","Q4"], index=["Auto","Q1","Q2","Q3","Q4"].index(st.session_state.mq_override))
        if mq_ov != st.session_state.mq_override: st.session_state.mq_override = mq_ov
        st.caption("Hedgeye May 2026 = Q2 Monthly")
    st.divider()
    _s=st.session_state.snap
    if _s and _s.get("ok"):
        _g=_s.get("gip"); _gl=_s.get("global",{})
        _sq=_g.structural_quad if _g else "—"; _mq=_g.monthly_quad if _g else "—"
        _gq=_gl.get("global_quad","—") if _gl else "—"
        st.caption(f"{_sq} Struct | {_mq} Monthly | {_gq} Global")
    else: st.caption("Building snapshot...")

# ── Load / Auto-build snapshot ────────────────────────────────────────────────
snap = st.session_state.snap
if snap is None:
    snap = load_snapshot(max_age_hours=6.0)
    if snap and snap.get("ok"): st.session_state.snap = snap

if snap is None or not snap.get("ok") or st.session_state.loading:
    from orchestrator import build_snapshot
    _lbl = "Building MacroRegime Pro snapshot..." if not st.session_state.loading else "Refreshing..."
    with st.spinner(_lbl):
        pb = st.progress(0.0); pt = st.empty()
        def prog(m,f): pb.progress(f); pt.caption(m)
        snap = build_snapshot(progress_cb=prog, include_us_stocks=inc_us, include_forex=inc_fx,
                              include_commodities=inc_comm, include_crypto=inc_cryp, include_ihsg=inc_ihsg)
        st.session_state.snap=snap; st.session_state.loading=False
        pb.empty(); pt.empty(); st.rerun()

if not snap or not snap.get("ok"):
    st.error("Snapshot build failed. Check logs via Manage App -> Logs."); st.stop()

# ── Extract ────────────────────────────────────────────────────────────────────
gip = snap.get("gip")
global_ = snap.get("global",{})
rr = snap.get("risk_ranges",{})
scen = snap.get("scenarios",{})
narr = snap.get("narratives",{})
disc = snap.get("discovery",{})
transition = snap.get("transition",None)
health = snap.get("health",{})
analogs = snap.get("analogs",{})
btk = snap.get("bottleneck",{})
pb_data = snap.get("playbook",{})
prices = snap.get("prices",{})
auto_disc = snap.get("auto_discoveries",{})
fb_eval = snap.get("feedback_eval",{})
gamma_data = snap.get("gamma",{})
lev_data = snap.get("leveraged_etf",{})

sq = gip.structural_quad if gip else "Q3"
mq_raw = gip.monthly_quad if gip else "Q1"
mq = st.session_state.mq_override if st.session_state.mq_override != "Auto" else mq_raw
gq = (global_.get("global_quad","Q3") if global_ else "Q3")

dxy_corr = _compute_dxy_corr(prices)

# Init options engine once
_opt_eng = None; _opt_ok = False
try:
    from engines.options_engine import OptionsEngine
    _opt_eng = OptionsEngine()
    _opt_ok = True
except Exception as _e:
    pass

# Build gamma dict by ticker if available
_gamma_by_ticker = {}
if gamma_data and isinstance(gamma_data, dict):
    # Try extract per-ticker gamma data
    for k, v in gamma_data.items():
        if isinstance(v, dict) and "ticker" in v:
            _gamma_by_ticker[v["ticker"]] = v
        elif k not in ("ok", "regime", "throttle", "note", "source", "message", "rationale"):
            # Maybe k is ticker
            if isinstance(v, dict):
                _gamma_by_ticker[k] = v

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    st.markdown(f'<div style="text-align:right;font-size:0.75rem;color:#8b949e;margin-bottom:4px">v18.3 | {snap.get("build_time_s",0)}s | Prices: {snap.get("prices_loaded",0)} | FRED: {snap.get("fred_coverage",0)} | RR: {snap.get("price_frames_count",0)}</div>', unsafe_allow_html=True)
    st.markdown("# MacroRegime Pro Dashboard")

    vbd=health.get("vix_bucket",{}) if health else {}; vb=vbd.get("bucket","—")
    vl=_sf(vbd.get("vix_last")) or 0; vn=vbd.get("note",""); vr=vbd.get("risk_mode","—")
    if vb=="Investable": vh=f'<div class="badge badge-green">INVESTABLE BUCKET</div> VIX {vl:.1f} | {vn}<br>Risk Mode: {vr}'
    elif vb=="Chop": vh=f'<div class="badge badge-yellow">CHOP BUCKET</div> VIX {vl:.1f} | {vn}<br>Risk Mode: {vr}'
    elif vb=="Defensive": vh=f'<div class="badge badge-red">DEFENSIVE BUCKET</div> VIX {vl:.1f} | {vn}<br>Risk Mode: {vr}'
    else: vh=""
    if vh: st.markdown(vh,unsafe_allow_html=True); st.markdown("",unsafe_allow_html=True)

    ga_col,dxy_col=st.columns([1.2,1])
    with ga_col: st.markdown(_render_gamma(gamma_data),unsafe_allow_html=True)
    with dxy_col:
        st.markdown('<div style="margin-bottom:8px"></div>',unsafe_allow_html=True)
        _render_dxy_section(prices,dxy_corr,sq)
        st.markdown('<div style="margin-bottom:8px"></div>',unsafe_allow_html=True)
    st.markdown(_render_lev(lev_data),unsafe_allow_html=True)

    _sq_q2p=(_sf((gip.structural_probs or {}).get("Q2",0)) or 0) if gip else 0
    _sq_sub=f"Q2 up {_sq_q2p:.0%}" if (sq=="Q3" and _sq_q2p>0.25) else ""
    _mq_note=""
    if mq_raw=="Q1" and mq!="Q1": _mq_note=f"Model={mq_raw} | Override={mq}"
    elif mq_raw=="Q1" and sq=="Q3": _mq_note="Model=Q1 | Hedgeye=Q2"
    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(qcard("STRUCTURAL",sq,gip.structural_conf if gip else 0,_sq_sub),unsafe_allow_html=True)
    with c2: st.markdown(qcard("MONTHLY",mq,gip.monthly_conf if gip else 0,_mq_note),unsafe_allow_html=True)
    with c3: st.markdown(qcard("GLOBAL",gq,(_sf(global_.get("global_conf")) or 0) if global_ else 0,"50 countries"),unsafe_allow_html=True)
    with c4:
        if gip:
            st.markdown(f'<div class="metric-card"><h4>ALIGNMENT</h4><div class="big">{gip.divergence.upper()}</div><div class="sub">{gip.operating_regime}<br>Flip Risk: {gip.flip_hazard:.0%}</div></div>', unsafe_allow_html=True)

    if fb_eval and fb_eval.get("evaluated",0):
        ev=fb_eval.get("evaluated",0); pr=fb_eval.get("promoted",0); dm=fb_eval.get("demoted",0); wr=(pr/max(ev,1))*100
        st.markdown("",unsafe_allow_html=True)
        w1,w2,w3,w4=st.columns(4)
        w1.markdown(f'<div class="metric-card"><h4>Evaluated</h4><div class="big">{ev}</div></div>',unsafe_allow_html=True)
        w2.markdown(f'<div class="metric-card"><h4>Promoted</h4><div class="big" style="color:#3fb950">{pr}</div></div>',unsafe_allow_html=True)
        w3.markdown(f'<div class="metric-card"><h4>Demoted</h4><div class="big" style="color:#f85149">{dm}</div></div>',unsafe_allow_html=True)
        w4.markdown(f'<div class="metric-card"><h4>Win Rate</h4><div class="big">{wr:.0f}%</div></div>',unsafe_allow_html=True)

    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#f85149","1-2w":"#d29922","3-6w":"#58a6ff","not yet":"#484f58"}.get(fw,"#484f58")
        fwi={"now":"NOW","1-2w":"SOON","3-6w":"WATCH","not yet":"HOLD"}.get(fw,"HOLD")
        if fw!="not yet":
            st.markdown(f'<div style="background:{fwc}15;border:1px solid {fwc};border-radius:10px;padding:12px 16px;margin:12px 0"><div style="font-weight:700;color:{fwc};font-size:1rem">{fwi} FRONT-RUN: {fw.upper()}</div><div style="font-size:0.9rem;color:#c9d1d9;margin-top:4px">{fr}</div></div>',unsafe_allow_html=True)
    st.markdown(_sequence_pills(sq,mq),unsafe_allow_html=True)

    if pb_data:
        best5=" | ".join(pb_data.get("best_assets",[])[:6]); worst5=" | ".join(pb_data.get("worst_assets",[])[:5])
        st.markdown(f'<div class="action-box"><div style="font-weight:700;font-size:1.05rem;margin-bottom:8px">QUICK ACTION {sq} Structural | {mq} Monthly</div><div style="color:#3fb950;margin-bottom:4px">LONG: {best5}</div><div style="color:#f85149">AVOID: {worst5}</div><div style="font-size:0.8rem;color:#8b949e;margin-top:6px">Full detail -> Alpha Center | Playbook</div></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GIP MODEL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "GIP Model":
    st.markdown("# GIP Model Growth | Inflation | Policy")
    st.caption("Hedgeye: YoY rate of change, second derivative. 'Heating up or cooling down?'")
    if not gip: st.warning("No GIP data."); st.stop()

    st.markdown("### Climate vs. Weather")
    cc,cw=st.columns(2)
    with cc:
        st.markdown(f'<div class="metric-card"><h4>STRUCTURAL -- CLIMATE</h4><div class="big" style="color:{ {"Q1":"#3fb950","Q2":"#d29922","Q3":"#f85149","Q4":"#58a6ff"}.get(sq,"#8b949e") }">{sq}</div><div class="sub">{qnc(sq)}<br>Conf: {gip.structural_conf:.0%} | Flip: {gip.flip_hazard:.0%} | Coverage: {gip.data_coverage:.0%}</div></div>', unsafe_allow_html=True)
    with cw:
        st.markdown(f'<div class="metric-card"><h4>MONTHLY -- WEATHER</h4><div class="big" style="color:{ {"Q1":"#3fb950","Q2":"#d29922","Q3":"#f85149","Q4":"#58a6ff"}.get(mq,"#8b949e") }">{mq}</div><div class="sub">{qnc(mq)}<br>Conf: {gip.monthly_conf:.0%} | {gip.divergence} | {gip.operating_regime}</div></div>', unsafe_allow_html=True)
    if mq_raw == "Q1":
        st.warning(f"Model={mq_raw} | Override={mq} (Hedgeye manual=Q2). Set via sidebar Quad Override.")

    st.markdown("---"); st.markdown("### G & I Signals")
    f=gip.features; gm=_sf(f.get("growth_momentum")) or 0; im=_sf(f.get("inflation_momentum")) or 0
    gc2="#3fb950" if gm>0 else "#f85149"; ic2="#3fb950" if im<0 else "#f85149"
    m1,m2,m3,m4=st.columns(4)
    m1.markdown(f'<div class="metric-card"><h4>Growth Momentum</h4><div class="big" style="color:{gc2}">{fp(gm)}</div><div class="sub">{"Accel up" if gm>0 else "Decel down"}</div></div>',unsafe_allow_html=True)
    m2.markdown(f'<div class="metric-card"><h4>Inflation Momentum</h4><div class="big" style="color:{ic2}">{fp(im)}</div><div class="sub">{"Rising up" if im>0 else "Cooling down"}</div></div>',unsafe_allow_html=True)
    m3.markdown(f'<div class="metric-card"><h4>Policy Score</h4><div class="big">{fp(f.get("policy_score"))}</div></div>',unsafe_allow_html=True)
    m4.markdown(f'<div class="metric-card"><h4>Leading Indicator</h4><div class="big">{fp(f.get("leading_indicator_composite"))}</div></div>',unsafe_allow_html=True)

    st.markdown("---"); st.markdown("### Transition Probabilities")
    QWINS={"Q1":"Tech, Small Caps, IBIT","Q2":"Energy, Materials, Commodity FX, IBIT","Q3":"Gold, Silver, Defensives","Q4":"TLT, Gold, Utilities, Cash"}
    def _tp(probs,cur_q,label,desc):
        if not probs: return
        sp=sorted(probs.items(),key=lambda x:x[1],reverse=True); top_q,top_p=sp[0]
        st.markdown(f'<div style="margin-bottom:6px"><b>{label}</b> -- {desc}<br>Currently: <b>{cur_q}</b> -> Most likely: <b>{top_q}</b> ({top_p:.0%})</div>', unsafe_allow_html=True)
        st.plotly_chart(prob_bar(probs),use_container_width=True,config={"displayModeBar":False})
        if top_q!=cur_q: st.markdown(f'<div class="info-box">If {top_q}: <b>{QWINS.get(top_q,"")}</b></div>',unsafe_allow_html=True)
    tp1,tp2,tp3=st.columns(3)
    with tp1: _tp(gip.structural_probs,sq,"STRUCTURAL",qnc(sq)[:30])
    with tp2: _tp(gip.monthly_probs,mq,"MONTHLY",qnc(mq)[:30])
    with tp3:
        gprobs=(global_.get("global_probs",{}) or {}) if global_ else {}
        if gprobs: _tp(gprobs,global_.get("dominant_quad",gq),"GLOBAL","50 Countries")

    st.markdown("---"); st.markdown("### Regime Timing")
    st.markdown(_sequence_pills(sq,mq),unsafe_allow_html=True)
    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#f85149","1-2w":"#d29922","3-6w":"#58a6ff","not yet":"#484f58"}.get(fw,"#484f58")
        fwi={"now":"NOW","1-2w":"SOON","3-6w":"WATCH","not yet":"HOLD"}.get(fw,"HOLD")
        st.markdown(f'<div style="background:{fwc}15;border:1px solid {fwc};border-radius:10px;padding:10px 14px;margin-top:10px"><b style="color:{fwc}">{fwi} FRONT-RUN: {fw.upper()}</b><div style="font-size:0.85rem;color:#c9d1d9;margin-top:4px">{fr}</div></div>',unsafe_allow_html=True)
        ew=getattr(transition,"early_warning_signals",{})
        if ew:
            ew_rows=[{"Signal":k.replace("_"," ").title(),"Firing":"YES" if v>=0.5 else "NO","Score":f"{v:.0f}"} for k,v in sorted(ew.items(),key=lambda x:x[1],reverse=True)]
            st.dataframe(pd.DataFrame(ew_rows),hide_index=True,use_container_width=True,height=250)

    if analogs and analogs.get("top_analogs"):
        st.markdown("---"); st.markdown("### Historical Analogs")
        for i,a in enumerate(analogs["top_analogs"]):
            with st.expander(f"**{a['label']}** -- {a.get('similarity',0):.0%}",expanded=(i==0)):
                cc2=st.columns(3); cc2[0].markdown(f"**1M:** {a.get('path_1m','')}"); cc2[1].markdown(f"**3M:** {a.get('path_3m','')}"); cc2[2].markdown(f"**6M:** {a.get('path_6m','')}")
                st.markdown(f"**Next bias:** {a.get('next_bias','')}")

# ══════════════════════════════════════════════════════════════════════════════
# RISK RANGES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Risk Ranges":
    st.markdown("# Risk Range TRADE | TREND | TAIL")
    st.caption("LRR = buy zone. TRR = trim zone. TREND break = exit.")
    ar=rr.get("asset_ranges",{})
    if not ar: st.warning("No RR data. Refresh."); st.stop()

    all_a=sorted([(s,a) for s,v in ar.items() for a in v.get("alerts",[])],key=lambda x:{"CRITICAL":0,"HIGH":1,"MEDIUM":2}.get(x[1].get("priority"),3))
    if all_a:
        st.markdown("### Alerts")
        for sym,a in all_a[:20]:
            ic="[!]" if a["priority"]=="CRITICAL" else "[?]"; bdr="#f85149" if a["priority"]=="CRITICAL" else "#d29922"
            st.markdown(f'<div style="border-left:3px solid {bdr};padding-left:10px;margin:4px 0;font-size:0.9rem">{ic} <b>[{sym}]</b> {a["action"]} {a["duration"]}<br><span style="font-size:0.8rem;color:#8b949e">{a.get("note","")}</span></div>',unsafe_allow_html=True)

    st.markdown("---")
    cl1,cl2=st.columns([1,3])
    with cl1: mkt_f=st.selectbox("Market",["All","us_equity","forex","commodity","crypto","ihsg"])
    with cl2: srch=st.text_input("Search","")
    rows=[]
    for sym,v in ar.items():
        if mkt_f!="All" and v.get("market","")!=mkt_f: continue
        if srch and srch.upper() not in sym.upper(): continue
        tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
        rl=_rr_levels(px,lrr,trr)
        rows.append({"Ticker":sym,"Px":ff(px),"LRR":ff(lrr),"TRR":ff(trr),
                     "Entry":ff(rl["entry"]) if rl else "—","TP1":ff(rl["tp1"]) if rl else "—","Stop":ff(rl["stop"]) if rl else "—",
                     "R/R":ff(rl["rr"]) if rl else "—","Stretch":tr.get("stretch","—"),
                     "Signal":v.get("composite","—").upper(),"Quality":v.get("quality","—"),
                     "Market":v.get("market","—"),"Trap":"[TRAP]" if v.get("regime_trap") else "",
                     "Ext":"[EXT]" if (rl and rl.get("extended")) else ""})
    if rows:
        df_rr=pd.DataFrame(rows)
        st.dataframe(df_rr, hide_index=True, use_container_width=True, height=520,
                     column_config={"Quality": st.column_config.TextColumn("Quality", width="small"),
                                    "Stretch": st.column_config.TextColumn("Stretch", width="small"),
                                    "Market": st.column_config.TextColumn("Market", width="small")})
    else: st.info("No data. Refresh.")

# ══════════════════════════════════════════════════════════════════════════════
# ALPHA CENTER — v18.3 OVERHAUL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Alpha Center":
    st.markdown("# Alpha Center Front-Run | Bottleneck | Options | Gamma")
    st.caption("Every setup shows Entry | TP1 | TP2 | Stop | R/R. Options + Gamma confirmed when available. Sorted by EV (highest first).")

    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#f85149","1-2w":"#d29922","3-6w":"#58a6ff","not yet":"#484f58"}.get(fw,"#484f58")
        fwi={"now":"NOW","1-2w":"SOON","3-6w":"WATCH","not yet":"HOLD"}.get(fw,"HOLD")
        st.markdown(f'<div style="background:{fwc}15;border:1px solid {fwc};border-radius:10px;padding:12px 16px;margin-bottom:12px"><b style="color:{fwc};font-size:1rem">{fwi} FRONT-RUN: {fw.upper()}</b><div style="font-size:0.9rem;color:#c9d1d9;margin-top:4px">{fr}</div></div>',unsafe_allow_html=True)
    st.markdown(_sequence_pills(sq,mq),unsafe_allow_html=True)

    ar=rr.get("asset_ranges",{})

    # Build ALL candidate items from bottleneck + RR fallback
    all_items = []

    # 1. Bottleneck items
    if btk:
        for item in (btk.get("level_1",[]) + btk.get("level_2",[]) + btk.get("watch",[]) + btk.get("avoid",[])):
            ticker = item.get("ticker","")
            v = ar.get(ticker, {})
            tr = v.get("trade", {})
            all_items.append({
                "ticker": ticker,
                "sector": item.get("sector","generic"),
                "px": _sf(v.get("px")),
                "lrr": _sf(tr.get("lrr")),
                "trr": _sf(tr.get("trr")),
                "composite": v.get("composite","neutral"),
                "quality": v.get("quality","none"),
                "stretch": tr.get("stretch","neutral"),
                "regime_fit": item.get("regime_fit",False),
                "direction": item.get("direction","long"),
                "ev": item.get("ev", 0),
                "source": "bottleneck",
            })

    # 2. RR fallback for assets with quality A/B/short_A/short_B not in bottleneck
    btk_tickers = {i["ticker"] for i in all_items}
    for sym, v in ar.items():
        if sym in btk_tickers: continue
        qual=v.get("quality","none")
        if qual in ("A","B","short_A","short_B"):
            tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
            # Estimate EV from RR quality + position
            pos=0.5
            if all(math.isfinite(x) for x in [px,lrr,trr]) and (trr-lrr)>1e-9: pos=(px-lrr)/(trr-lrr)
            ev=0.6 if qual in ("A","short_A") else 0.4
            if pos>0.8: ev-=0.2  # extended penalty
            all_items.append({
                "ticker":sym,"sector":v.get("sector","generic"),"px":px,"lrr":lrr,"trr":trr,
                "composite":v.get("composite","neutral"),"quality":qual,"stretch":tr.get("stretch","neutral"),
                "regime_fit":False,"direction":"long" if v.get("composite")=="bullish" else "short",
                "ev":ev,"source":"rr_quality",
            })

    # Split by direction
    long_items=[i for i in all_items if i["direction"] in ("long","neutral") and i["composite"] in ("bullish","mixed","neutral")]
    short_items=[i for i in all_items if i["direction"] in ("short","avoid") or i["composite"]=="bearish"]

    # Build tables with new format
    df_longs=_build_alpha_table(long_items,"long",_opt_eng,_gamma_by_ticker)
    df_shorts=_build_alpha_table(short_items,"short",_opt_eng,_gamma_by_ticker)

    # ── 3-TIER ALPHA CENTRE ──────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### LONG SETUPS")

    if not df_longs.empty:
        basi=df_longs[df_longs["StatusCat"]=="basi"]
        if not basi.empty:
            st.markdown('<div class="tier-card tier-basi"><div class="tier-title" style="color:#f85149">BASI | TAKE PROFIT</div><div class="tier-desc">Sudah dekat target, jangan chase. Consider partial exit.</div></div>',unsafe_allow_html=True)
            st.dataframe(basi.drop(columns=["StatusCat"]),hide_index=True,use_container_width=True,height=180)

        building=df_longs[df_longs["StatusCat"]=="building"]
        if not building.empty:
            st.markdown('<div class="tier-card tier-building"><div class="tier-title" style="color:#3fb950">BUILDING | ENTER NOW</div><div class="tier-desc">Mendekati entry level, target masih jauh. Best risk/reward.</div></div>',unsafe_allow_html=True)
            st.dataframe(building.drop(columns=["StatusCat"]),hide_index=True,use_container_width=True,height=280)

        chase=df_longs[df_longs["StatusCat"]=="chase"]
        if not chase.empty:
            st.markdown('<div class="tier-card tier-chase"><div class="tier-title" style="color:#d29922">CHASE OK</div><div class="tier-desc">Di tengah range tapi target masih worth it. Tight stop.</div></div>',unsafe_allow_html=True)
            st.dataframe(chase.drop(columns=["StatusCat"]),hide_index=True,use_container_width=True,height=280)

        wait=df_longs[df_longs["StatusCat"]=="wait"]
        if not wait.empty:
            with st.expander(f"WAIT -- {len(wait)} items (extended or no setup)"):
                st.dataframe(wait.drop(columns=["StatusCat"]),hide_index=True,use_container_width=True,height=240)
    else:
        st.info("No long setups available. Market may be extended or bottleneck data empty.")

    st.markdown("---")
    st.markdown("### SHORT SETUPS")
    if not df_shorts.empty:
        basi_s=df_shorts[df_shorts["StatusCat"]=="basi"]
        if not basi_s.empty:
            st.markdown('<div class="tier-card tier-basi"><div class="tier-title" style="color:#3fb950">COVER SHORT</div><div class="tier-desc">Sudah dekat target cover. Consider closing position.</div></div>',unsafe_allow_html=True)
            st.dataframe(basi_s.drop(columns=["StatusCat"]),hide_index=True,use_container_width=True,height=180)
        building_s=df_shorts[df_shorts["StatusCat"]=="building"]
        if not building_s.empty:
            st.markdown('<div class="tier-card tier-building"><div class="tier-title" style="color:#f85149">ENTER SHORT</div><div class="tier-desc">Mendekati entry zone untuk short. Target ke bawah.</div></div>',unsafe_allow_html=True)
            st.dataframe(building_s.drop(columns=["StatusCat"]),hide_index=True,use_container_width=True,height=200)
        chase_s=df_shorts[df_shorts["StatusCat"]=="chase"]
        if not chase_s.empty:
            st.markdown('<div class="tier-card tier-chase"><div class="tier-title" style="color:#d29922">CHASE SHORT</div><div class="tier-desc">Masih bisa dikejar. Tight stop above resistance.</div></div>',unsafe_allow_html=True)
            st.dataframe(chase_s.drop(columns=["StatusCat"]),hide_index=True,use_container_width=True,height=200)
    else:
        st.info("No short setups available.")

    # ── ATH MOMENTUM SCANNER (SNDK-like) ─────────────────────────────────────
    st.markdown("---")
    st.markdown("### ATH Momentum Scanner")
    st.caption("Tickers approaching or breaking All-Time-High with bottleneck + option confirmation. Like SNDK pattern: ATH to ATH.")

    ath_candidates = []
    for sym, v in ar.items():
        s = prices.get(sym)
        if s is None: continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 252: continue
        px = float(s.iloc[-1])
        ath = float(s.max())
        if ath <= 0: continue
        dist_to_ath = (ath - px) / ath
        # Within 5% of ATH and bullish
        if dist_to_ath < 0.05 and v.get("composite") == "bullish":
            tr = v.get("trade", {})
            lrr = _sf(tr.get("lrr")); trr = _sf(tr.get("trr"))
            rl = _rr_levels(px, lrr, trr, "long")
            ev = 0
            # Find bottleneck EV if exists
            for item in all_items:
                if item["ticker"] == sym:
                    ev = item.get("ev", 0)
                    break
            ath_candidates.append({
                "ticker": sym,
                "px": px,
                "ATH": ath,
                "Dist to ATH": f"{dist_to_ath:+.1%}",
                "LRR": ff(lrr),
                "TRR": ff(trr),
                "Entry": ff(rl["entry"]) if rl else "—",
                "TP1": ff(rl["tp1"]) if rl else "—",
                "TP2": ff(rl["tp2"]) if rl else "—",
                "R/R": ff(rl["rr"]) if rl else "—",
                "EV": round(ev, 2),
                "Quality": v.get("quality", "—"),
            })

    if ath_candidates:
        df_ath = pd.DataFrame(ath_candidates).sort_values("EV", ascending=False)
        st.markdown(f'<div class="tier-card tier-ath"><div class="tier-title" style="color:#58a6ff">ATH BREAKOUT CANDIDATES ({len(ath_candidates)})</div><div class="tier-desc">Within 5% of ATH + bullish composite. Sorted by EV.</div></div>', unsafe_allow_html=True)
        st.dataframe(df_ath, hide_index=True, use_container_width=True, height=280)
    else:
        st.info("No ATH breakout candidates. Market may be below recent highs.")

    # Summary metrics
    st.markdown("---")
    s1,s2,s3,s4,s5=st.columns(5)
    s1.markdown(f'<div class="metric-card"><h4>Longs</h4><div class="big">{len(df_longs)}</div></div>',unsafe_allow_html=True)
    s2.markdown(f'<div class="metric-card"><h4>Shorts</h4><div class="big">{len(df_shorts)}</div></div>',unsafe_allow_html=True)
    s3.markdown(f'<div class="metric-card"><h4>Building</h4><div class="big" style="color:#3fb950">{len(df_longs[df_longs["StatusCat"]=="building"])}</div></div>',unsafe_allow_html=True)
    s4.markdown(f'<div class="metric-card"><h4>Basi</h4><div class="big" style="color:#f85149">{len(df_longs[df_longs["StatusCat"]=="basi"])}</div></div>',unsafe_allow_html=True)
    s5.markdown(f'<div class="metric-card"><h4>ATH Scan</h4><div class="big" style="color:#58a6ff">{len(ath_candidates)}</div></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# LEADERBOARD — Same format as Alpha Center
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Leaderboard":
    st.markdown("# Leaderboard Signal Strength Stocks")
    st.caption("Quality A near LRR + volume confirm. Same table format as Alpha Centre.")
    ar=rr.get("asset_ranges",{})
    if not ar: st.warning("No RR data. Refresh."); st.stop()

    best_set=set(pb_data.get("best_assets",[])); worst_set=set(pb_data.get("worst_assets",[]))
    long_picks=[]; short_picks=[]

    for sym,v in ar.items():
        qual=v.get("quality","none"); comp=v.get("composite","neutral")
        tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
        try: from config.settings import TICKER_SECTOR; sector=TICKER_SECTOR.get(sym,"generic")
        except: sector="generic"

        ev=0.6 if qual=="A" else 0.4 if qual=="B" else 0.3
        if qual in ("A","B") and comp=="bullish":
            long_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"composite":comp,"sector":sector,"stretch":tr.get("stretch","neutral"),"regime_fit":sym in best_set,"ev":ev})
        if qual in ("short_A","short_B") and comp=="bearish":
            short_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"composite":comp,"sector":sector,"stretch":tr.get("stretch","neutral"),"regime_fit":sym in worst_set,"ev":ev})

    df_longs=_build_alpha_table(long_picks,"long",_opt_eng,_gamma_by_ticker)
    df_shorts=_build_alpha_table(short_picks,"short",_opt_eng,_gamma_by_ticker)

    s1,s2,s3,s4=st.columns(4)
    s1.markdown(f'<div class="metric-card"><h4>Bullish Names</h4><div class="big">{len(long_picks)}</div></div>',unsafe_allow_html=True)
    s2.markdown(f'<div class="metric-card"><h4>Quality A Longs</h4><div class="big" style="color:#3fb950">{sum(1 for p in long_picks if p["quality"]=="A")}</div></div>',unsafe_allow_html=True)
    s3.markdown(f'<div class="metric-card"><h4>Quality A Shorts</h4><div class="big" style="color:#f85149">{sum(1 for p in short_picks if p["quality"]=="short_A")}</div></div>',unsafe_allow_html=True)
    s4.markdown(f'<div class="metric-card"><h4>Regime Traps</h4><div class="big">{sum(1 for v in ar.values() if v.get("regime_trap"))}</div></div>',unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### TOP 21 LONG IDEAS")
    st.caption("Entry = LRR zone. TP1 = midpoint. TP2 = TRR. Stop = below LRR. R/R target >= 1.5x.")
    if not df_longs.empty:
        display_df=df_longs.drop(columns=["StatusCat"]) if "StatusCat" in df_longs.columns else df_longs
        st.dataframe(display_df.head(21),hide_index=True,use_container_width=True,
                     column_config={"Status": st.column_config.TextColumn("Status",width="medium"),
                                    "Sector": st.column_config.TextColumn("Sector",width="small"),
                                    "Opt Level": st.column_config.TextColumn("Opt Lvl",width="small"),
                                    "Gam Level": st.column_config.TextColumn("Gam Lvl",width="small")})
    else:
        st.info("No Quality A/B longs. Market extended -- wait for pullback to LRR.")

    st.markdown("---")
    st.markdown("### SHORT IDEAS")
    st.caption("Entry = TRR zone (sell the rip). TP1 = midpoint. TP2 = LRR. Stop = above TRR.")
    if not df_shorts.empty:
        display_df_s=df_shorts.drop(columns=["StatusCat"]) if "StatusCat" in df_shorts.columns else df_shorts
        st.dataframe(display_df_s.head(15),hide_index=True,use_container_width=True,
                     column_config={"Status": st.column_config.TextColumn("Status",width="medium"),
                                    "Sector": st.column_config.TextColumn("Sector",width="small")})
    else:
        st.info("No Quality Short setups.")

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL QUAD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Global Quad":
    st.markdown("# Global Quad 50 Countries")
    if not global_: st.warning("No global data. Refresh."); st.stop()
    gconf=_sf(global_.get("global_conf")) or 0; gprobs=global_.get("global_probs",{}) or {}
    c1,c2=st.columns([1,1.5])
    with c1:
        st.markdown(qcard("GLOBAL QUAD",gq,gconf,"50 Country ETFs"),unsafe_allow_html=True)
        if gprobs: st.plotly_chart(prob_bar(gprobs,"Global Probabilities"),use_container_width=True,config={"displayModeBar":False})
    with c2:
        cq=global_.get("country_quads",{}) or {}; heat=[]
        for country,data in cq.items():
            if isinstance(data,(list,tuple)) and len(data)>=3: etf,quad,conf=str(data[0]),str(data[1]),_sf(data[2]) or 0
            elif isinstance(data,dict): etf,quad,conf=str(data.get("etf","")),str(data.get("quad","")),_sf(data.get("conf",0)) or 0
            else: continue
            if quad: heat.append({"Country":country,"ETF":etf,"Quad":quad,"Conf":f"{conf:.0%}"})
        if heat:
            st.dataframe(pd.DataFrame(heat).style.map(lambda v:f"color:{ {'Q1':'#3fb950','Q2':'#d29922','Q3':'#f85149','Q4':'#58a6ff'}.get(v,'#8b949e') }",subset=["Quad"]), hide_index=True, height=420, use_container_width=True)
        else:
            st.info("Country Quad data kosong. Pastikan GlobalQuadEngine berjalan dan click Refresh.")
    st.markdown("---"); st.markdown("### EM Recovery Signal")
    em_sig=(btk.get("em_recovery",{}) or {}) if btk else {}
    if em_sig:
        conf=_sf(em_sig.get("confidence")) or 0; ec="#3fb950" if conf>0.6 else "#d29922" if conf>0.4 else "#8b949e"
        st.markdown(f'<div style="background:{ec}15;border:1px solid {ec};border-radius:10px;padding:12px 16px"><div style="font-weight:700;color:{ec}">{em_sig.get("trigger","")}</div><div style="font-size:0.9rem;color:#c9d1d9;margin-top:4px">{em_sig.get("rationale","")}</div><div style="font-size:0.8rem;color:#8b949e;margin-top:6px">Conf: {conf:.0%} | Best: {", ".join(em_sig.get("best",[])[:6])}</div></div>', unsafe_allow_html=True)
    else: st.info("EM recovery signal belum tersedia.")

# ══════════════════════════════════════════════════════════════════════════════
# IHSG — Auto RR + universal table
# ══════════════════════════════════════════════════════════════════════════════
elif page == "IHSG":
    st.markdown("# IHSG Indonesia Market")
    st.caption("Local signal. No options data (IHSG options market tidak liquid). Risk Range dihitung otomatis via per-ticker fallback.")
    from config.settings import IHSG_UNIVERSE, IHSG_BUCKETS
    ar=rr.get("asset_ranges",{}); ihsg_rr={sym:v for sym,v in ar.items() if v.get("market","")=="ihsg"}

    if ihsg_rr:
        ihsg_items=[]
        for sym, v in ihsg_rr.items():
            tr=v.get("trade",{})
            ihsg_items.append({
                "ticker":sym,"sector":"ihsg","px":_sf(v.get("px")),"lrr":_sf(tr.get("lrr")),"trr":_sf(tr.get("trr")),
                "composite":v.get("composite","neutral"),"quality":v.get("quality","none"),"stretch":tr.get("stretch","neutral"),
                "regime_fit":False,"direction":"long" if v.get("composite")=="bullish" else "short","ev":0,
            })
        df_ihsg=_build_alpha_table(ihsg_items,"long",None,None)
        st.markdown("### IHSG Risk Range Universe")
        st.dataframe(df_ihsg.drop(columns=["StatusCat"]) if "StatusCat" in df_ihsg.columns else df_ihsg,hide_index=True,use_container_width=True,height=420)
    else:
        st.markdown('<div class="warn-box"><b>INFO</b> Risk Range data untuk IHSG sedang dihitung. Fix sudah di-deploy: per-ticker fallback aktif. Click <b>Force Rebuild</b> di sidebar untuk rebuild snapshot.</div>', unsafe_allow_html=True)
        rows=[]
        for sym in IHSG_UNIVERSE:
            s=prices.get(sym)
            if s is None: continue
            s=pd.to_numeric(s,errors="coerce").dropna()
            if s.empty: continue
            px=float(s.iloc[-1])
            r1=float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>=22 else None
            r3=float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else None
            rows.append({"Ticker":sym,"Px":f"{px:.0f}","1M":f"{r1:+.1%}" if r1 else "—","3M":f"{r3:+.1%}" if r3 else "—","Name":IHSG_UNIVERSE.get(sym,sym)})
        if rows:
            st.markdown("### Price Snapshot Fallback")
            st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=400)

    st.markdown("---"); st.markdown("### Sector Buckets")
    for bucket,tickers in IHSG_BUCKETS.items():
        with st.expander(f"**{bucket.replace('_',' ')}** ({len(tickers)})"):
            b_rows=[]
            for t in tickers:
                s=prices.get(t)
                if s is None: continue
                s=pd.to_numeric(s,errors="coerce").dropna()
                r1=float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>=22 else 0
                r3=float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else 0
                b_rows.append({"Ticker":t,"1M":f"{r1:+.1%}","3M":f"{r3:+.1%}"})
            if b_rows: st.dataframe(pd.DataFrame(b_rows),hide_index=True,use_container_width=True)
            else: st.info("Data tidak tersedia. Refresh.")

# ══════════════════════════════════════════════════════════════════════════════
# NARRATIVES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Narratives":
    st.markdown("# Narratives Thematic Scoring")
    st.caption("Active = confirmed. Building = traction. Brewing = pre-consensus.")
    active=(narr.get("active_narratives",[]) or []) if narr else []
    fallback=[n for n in HEDGEYE_FALLBACK_NARRATIVES if sq in n.get("regime","") or mq in n.get("regime","") or n.get("regime","")=="ALL"]
    all_narr=active if active else fallback
    for n in sorted(all_narr, key=lambda x: x.get("score",0), reverse=True):
        score=n.get("score",0); sc="#3fb950" if score>0.6 else "#d29922" if score>0.4 else "#8b949e"
        is_fallback="quad_bias" in n
        tag=" | Hedgeye aligned" if is_fallback else ""
        with st.expander(f"**{n.get('name','')}** -- {score:.0%}{tag}"):
            st.markdown(f"**Thesis:** {n.get('thesis','')}")
            st.markdown(f"**Tickers:** {' | '.join(n.get('tickers',[])[:8])}")
            if n.get("best"): st.markdown(f"**Best:** {' | '.join(n['best'][:6])}")
            if n.get("worst"): st.markdown(f"**Worst:** {' | '.join(n['worst'][:4])}")
            if n.get("invalidators"): st.markdown(f"**Invalidators:** {' | '.join(n['invalidators'][:3])}")
            if is_fallback and n.get("quad_bias"): st.caption(f"Quad bias: {n['quad_bias']}")

# ══════════════════════════════════════════════════════════════════════════════
# DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Discovery":
    st.markdown("# Early Discovery Pre-Consensus")
    st.caption("Autonomy: regime fit + price cluster + supply chain graph + news NLP.")
    cands=(auto_disc.get("candidates",[]) or []) if auto_disc else []
    cands += (disc.get("discoveries",[]) or []) if disc else []
    cands_display=cands if cands else HEDGEYE_FALLBACK_DISCOVERY
    for stage,sc_c in [("active","#3fb950"),("building","#d29922"),("brewing","#58a6ff")]:
        items=[c for c in cands_display if c.get("stage")==stage]
        if not items: continue
        st.markdown(f"### {stage.upper()} ({len(items)})")
        for c in items:
            conf=c.get("confidence",c.get("conviction",0.7))
            with st.expander(f"**{c.get('name','')}** -- Conf: {conf:.0%}"):
                st.markdown(f"**Thesis:** {c.get('thesis','')}")
                ben=c.get("beneficiary_tickers",[]); fade=c.get("fade_tickers",[])
                if ben: st.markdown(f"**Beneficiaries:** {' | '.join(ben[:8])}")
                if fade: st.markdown(f"**Fade:** {' | '.join(fade[:5])}")
                cs=c.get("confirmation_signal",""); inv=c.get("invalidators",[])
                if cs: st.markdown(f"**Confirmation:** {cs}")
                if inv: st.markdown(f"**Invalidators:** {', '.join(inv) if isinstance(inv,list) else inv}")

# ══════════════════════════════════════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Health":
    st.markdown("# Market Health VIX | Breadth | Crash Meter")
    if not health: st.warning("No health data."); st.stop()
    vb_d=health.get("vix_bucket",{}); vb_b=vb_d.get("bucket","—")
    vb_c={"Investable":"#3fb950","Chop":"#d29922","Defensive":"#f85149"}.get(vb_b,"#8b949e")
    st.markdown(f'<div style="background:{vb_c}15;border:1px solid {vb_c};border-radius:10px;padding:12px 16px;margin-bottom:12px"><div style="font-weight:700;color:{vb_c};font-size:1.1rem">VIX BUCKET: {vb_b.upper()}</div><div style="font-size:0.9rem;color:#c9d1d9;margin-top:4px">{vb_d.get("note","")}</div></div>',unsafe_allow_html=True)
    crash=health.get("crash",{}) or {}
    if crash:
        st.markdown("### Crash Meter")
        for k,v in crash.get("signals",{}).items(): st.progress(float(v) if v else 0,text=f"{k.replace('_',' ').title()}: {v:.0%}" if v else k)
        st.markdown(f"**State:** {crash.get('state','')} | Score: {_sf(crash.get('score',0)):.0%}")
    breadth=health.get("market_health",{}) or {}
    if breadth:
        st.markdown("### Breadth")
        b1,b2,b3,b4=st.columns(4)
        b1.metric("Score",f"{_sf(breadth.get('score')) or 0:.2f}"); b2.metric("Verdict",breadth.get("verdict","—"))
        b3.metric("Sector Support",f"{breadth.get('positive_sectors_1m',0)}/{breadth.get('total_buckets',0)}")
        b4.metric("EqW",f"{_sf(breadth.get('eqw_health')) or 0:.2f}")
    fg=health.get("fear_greed",{}) or {}
    if fg:
        st.markdown("---"); fgs=_sf(fg.get("score")) or 50
        fgc="#3fb950" if fgs<25 else "#d29922" if fgs<55 else "#f85149"
        st.markdown(f"**Fear & Greed:** {fgs:.0f}/100 -- {fg.get('label','Neutral')}",unsafe_allow_html=True)
        st.progress(fgs/100)

# ══════════════════════════════════════════════════════════════════════════════
# PLAYBOOK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Playbook":
    st.markdown("# Regime Playbook")
    st.caption(f"**{sq}** Structural | **{mq}** Monthly (override: {st.session_state.mq_override})")
    if pb_data:
        col1,col2=st.columns(2)
        with col1:
            adds=" | ".join(pb_data.get("monthly_adds",[])) if pb_data.get("monthly_adds") else ""
            st.markdown(f'<div style="background:#3fb95015;border:1px solid #3fb950;border-radius:10px;padding:14px 18px"><div style="font-weight:700;color:#3fb950;font-size:1.1rem;margin-bottom:8px">LONG -- {sq}</div><div style="font-size:0.9rem;color:#c9d1d9;line-height:1.5">{" | ".join(pb_data.get("best_assets",[]))}<br><br><b>Style:</b> {pb_data.get("style","")}<br><b>FX:</b> {pb_data.get("fx","")}<br><b>Bonds:</b> {pb_data.get("bonds","")}<br>{("<b>Adds:</b> " + adds + "<br>") if adds else ""}</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div style="background:#f8514915;border:1px solid #f85149;border-radius:10px;padding:14px 18px"><div style="font-weight:700;color:#f85149;font-size:1.1rem;margin-bottom:8px">AVOID -- {sq}</div><div style="font-size:0.9rem;color:#c9d1d9;line-height:1.5">{" | ".join(pb_data.get("worst_assets",[]))}<br><br><b>Hedge:</b> {pb_data.get("hedge","BTAL")}<br>{pb_data.get("sizing_note","Min 1% | Max 3%")}</div></div>', unsafe_allow_html=True)
    btc_rr=rr.get("asset_ranges",{}).get("IBIT",rr.get("asset_ranges",{}).get("BTC-USD",{}))
    btc_sig=btc_rr.get("composite","—")
    btc_c="#3fb950" if btc_sig=="bullish" else "#f85149" if btc_sig=="bearish" else "#8b949e"
    st.markdown(f'<div class="action-box">BTC (IBIT): <span style="color:{btc_c}">{btc_sig.upper()}</span> -- {"Exit (Q4)" if sq=="Q4" else "Signal-dependent via DXY correlation"} | DXY/BTC 15D: {dxy_corr.get("Bitcoin","—")} | "Any quad other than Q4 = long IBIT."</div>', unsafe_allow_html=True)
    scenarios_list=(scen.get("scenarios",[]) or []) if scen else []
    if scenarios_list:
        st.markdown("---"); st.markdown("### Scenarios")
        badges=["[BASE]","[ALT]","[RISK]","[TAIL]"]; badge_colors=["#3fb950","#d29922","#f85149","#58a6ff"]
        row1=st.columns(2); row2=st.columns(2); grids=[row1[0],row1[1],row2[0],row2[1]]
        for i,(sc_item,col) in enumerate(zip(scenarios_list[:4],grids)):
            pc=badge_colors[i]; em=sc_item.em_note[:55]+"..." if len(sc_item.em_note)>55 else sc_item.em_note
            with col:
                st.markdown(f'<div style="background:{pc}15;border:1px solid {pc};border-radius:10px;padding:10px 14px;margin-bottom:8px;height:100%"><div style="font-weight:700;color:{pc};font-size:0.85rem">{badges[i]} P={sc_item.probability:.0%}</div><div style="font-weight:600;color:#c9d1d9;margin:4px 0">{sc_item.name}</div><div style="font-size:0.8rem;color:#8b949e">{sc_item.headline}</div><div style="font-size:0.78rem;color:#c9d1d9;margin-top:4px">Best: {" | ".join(sc_item.best_assets[:3])}<br>Avoid: {" | ".join(sc_item.worst_assets[:3])}</div><div style="font-size:0.75rem;color:#8b949e;margin-top:4px">{em}</div></div>',unsafe_allow_html=True)
    if gip:
        st.markdown("---"); st.markdown("### GIP Signals")
        f=gip.features
        rows=[["Growth Momentum",fp(f.get("growth_momentum")),"up" if (_sf(f.get("growth_momentum")) or 0)>0 else "down"],
              ["Inflation Momentum",fp(f.get("inflation_momentum")),"up" if (_sf(f.get("inflation_momentum")) or 0)>0 else "down"],
              ["Policy Score",fp(f.get("policy_score")),""],["Leading Indicator",fp(f.get("leading_indicator_composite")),""],
              ["Data Coverage",fp(f.get("data_coverage")),""],["Flip Hazard",f"{gip.flip_hazard:.0%}",""],
              ["Structural Conf",f"{gip.structural_conf:.0%}",""],["Monthly Conf",f"{gip.monthly_conf:.0%}",""]]
        st.dataframe(pd.DataFrame(rows,columns=["Signal","Value","Dir"]),hide_index=True,use_container_width=True)
