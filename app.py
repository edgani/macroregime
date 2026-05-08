"""app.py — MacroRegime Pro v17.5

Complete rewrite:
  - Compact spacing (no excessive gaps)
  - Consistent font hierarchy (10px label / 12px body / 14px title / 18-22px value)
  - All tables styled uniformly
  - Column proportions balanced
  - No overlapping/timpang tindih
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

st.set_page_config(page_title="MacroRegime Pro", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# ══════════════════════════════════════════════════════════════════════════════
# CSS — compact, consistent
# ══════════════════════════════════════════════════════════════════════════════
CSS = """
<style>
.stApp { background-color: #0B0F19 !important; }

/* Card base */
.mr-card {
    background: linear-gradient(145deg, #1a2332 0%, #141c2b 100%);
    border: 1px solid #1f2b3d;
    border-radius: 8px;
    padding: 14px 16px;
    height: 100%;
}
.mr-card-h {
    font-size: 9px; font-weight: 700; letter-spacing: 1.2px;
    text-transform: uppercase; color: #6B7280; margin-bottom: 8px;
}
.mr-card-v {
    font-size: 22px; font-weight: 800; line-height: 1.1;
    color: #E8ECF0; margin-bottom: 2px;
}
.mr-card-s {
    font-size: 11px; color: #9CA3AF; line-height: 1.4; margin-top: 4px;
}
.mr-card-m {
    font-size: 10px; color: #6B7280; margin-top: 6px;
}

/* Win / metric */
.mr-win {
    background: linear-gradient(145deg, #1a2332 0%, #141c2b 100%);
    border: 1px solid #1f2b3d; border-radius: 8px;
    padding: 12px 14px; text-align: center; height: 100%;
}
.mr-win-l {
    font-size: 9px; color: #6B7280; text-transform: uppercase;
    letter-spacing: 1px; margin-bottom: 4px;
}
.mr-win-v {
    font-size: 20px; font-weight: 800; color: #E8ECF0;
}

/* Grid inside cards */
.mr-g2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 14px; }
.mr-g3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px 14px; }
.mr-g4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px 14px; }
.mr-gi { display: flex; flex-direction: column; }
.mr-gi-l { font-size: 9px; color: #6B7280; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 1px; }
.mr-gi-v { font-size: 15px; font-weight: 700; color: #E8ECF0; }

/* Banner */
.mr-ban { border-radius: 6px; padding: 10px 14px; margin-bottom: 12px; font-size: 12px; line-height: 1.4; }
.mr-ban-g { background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.18); color: #10B981; }
.mr-ban-y { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.18); color: #F59E0B; }
.mr-ban-r { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.18); color: #EF4444; }

/* Alert strip */
.mr-al { border-left: 2px solid; padding: 8px 12px; background: #1a2332;
         border-radius: 0 6px 6px 0; margin-bottom: 4px; font-size: 11px; color: #E8ECF0; }

/* Pick row (Leaderboard) */
.mr-pk { border-left: 2px solid; padding: 10px 14px; background: #1a2332;
         border-radius: 0 8px 8px 0; margin-bottom: 6px; }
.mr-pk-t { font-size: 12px; font-weight: 700; color: #E8ECF0; }
.mr-pk-m { font-size: 11px; color: #9CA3AF; margin-top: 3px; line-height: 1.4; }
.mr-pk-u { font-size: 10px; color: #6B7280; margin-top: 2px; }

/* Scenario card */
.mr-sc { background: linear-gradient(145deg, #1a2332 0%, #141c2b 100%);
        border: 1px solid #1f2b3d; border-radius: 8px; padding: 14px 16px; height: 100%; }
.mr-sc-b { font-size: 10px; font-weight: 700; margin-bottom: 6px; }
.mr-sc-t { font-size: 13px; font-weight: 700; color: #E8ECF0; margin-bottom: 4px; }
.mr-sc-d { font-size: 11px; color: #9CA3AF; line-height: 1.4; margin-bottom: 6px; }
.mr-sc-l { font-size: 10px; line-height: 1.4; }

/* Action box */
.mr-act { background: linear-gradient(145deg, #1a2332 0%, #141c2b 100%);
          border: 1px solid #1f2b3d; border-radius: 8px; padding: 14px 16px; margin-top: 12px; }
.mr-act-r { display: flex; align-items: center; gap: 8px; margin: 4px 0; font-size: 12px; }
.mr-act-t { font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px; white-space: nowrap; }

/* Pills */
.mr-pill { padding: 3px 10px; border-radius: 4px; font-weight: 700; font-size: 11px; }
.mr-parr { color: #6B7280; font-size: 12px; font-weight: 700; }

/* Front-run */
.mr-fr { border-radius: 6px; padding: 10px 14px; margin: 8px 0; font-size: 12px; line-height: 1.4; }

/* Table styling helper */
.mr-th { font-size: 9px !important; text-transform: uppercase !important; letter-spacing: 1px !important;
         background: #1a2332 !important; color: #9CA3AF !important; }
.mr-td { font-size: 11px !important; border-bottom: 1px solid #1f2b3d !important; }
.mr-tr:nth-child(even) { background: #141c2b !important; }

/* Reduce default streamlit gaps */
div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
div[data-testid="stHorizontalBlock"] > div { padding: 0 5px !important; }
.stDataFrame { border-radius: 6px !important; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

QC = {"Q1":"#00D4AA","Q2":"#F59E0B","Q3":"#EF4444","Q4":"#6366F1"}
QN = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}
QNC = {"Q1":"Goldilocks - Growth up Infl down","Q2":"Reflation - Growth up Infl up",
       "Q3":"Stagflation - Growth down Infl up","Q4":"Deflation - Growth down Infl down"}

def qc(q): return QC.get(q,"#9CA3AF")
def qn(q): return QN.get(q,q)
def qnc(q): return QNC.get(q,q)
def fp(v):
    try: return f"{float(v):.1%}" if v is not None and math.isfinite(float(v)) else "-"
    except: return "-"
def ff(v, d=2):
    try: return f"{float(v):.{d}f}" if v is not None and math.isfinite(float(v)) else "-"
    except: return "-"
def _safe_float(v):
    if v is None: return None
    try:
        if isinstance(v, pd.Series): v = v.iloc[0]
        f = float(v)
        return f if math.isfinite(f) else None
    except: return None

def _df_style(df):
    return df.style.set_properties(**{"font-size": "11px", "text-align": "left"})\
                   .set_table_styles([{"selector": "th", "props": [("font-size", "9px"), ("text-transform", "uppercase"),
                                                                    ("letter-spacing", "1px"), ("background-color", "#1a2332"),
                                                                    ("color", "#9CA3AF")]},
                                     {"selector": "td", "props": [("border-bottom", "1px solid #1f2b3d")]},
                                     {"selector": "tbody tr:nth-child(even)", "props": [("background-color", "#141c2b")]}])

# ══════════════════════════════════════════════════════════════════════════════
# qcard / prob / pills
# ══════════════════════════════════════════════════════════════════════════════
def qcard(label, q, conf, sub=""):
    c = qc(q)
    s = f'<div class="mr-card-s">{sub}</div>' if sub else ""
    return f'<div class="mr-card"><div class="mr-card-h">{label}</div><div class="mr-card-v" style="color:{c};">{q}</div><div class="mr-card-s">{qn(q)}</div><div class="mr-card-m">Conf: {conf:.0%}</div>{s}</div>'

def prob_bar(probs, title=""):
    fig = go.Figure()
    for q,p in sorted((probs or {}).items()):
        fig.add_bar(x=[q], y=[p], marker_color=qc(q), text=[f"<b>{p:.0%}</b>"], textposition="outside", name=q)
    fig.update_layout(showlegend=False, height=160, margin=dict(t=20,b=0,l=0,r=0),
                      paper_bgcolor="#111827", plot_bgcolor="#111827",
                      font=dict(color="#E8ECF0", family="JetBrains Mono", size=10),
                      title=dict(text=title, font=dict(size=10, color="#9CA3AF")),
                      yaxis=dict(range=[0,1.1], tickformat=".0%", showgrid=True, gridcolor="#1F2B3D", dtick=0.5),
                      xaxis=dict(showgrid=False), bargap=0.4)
    return fig

def _pills(sq, mq):
    sqc, mqc = qc(sq), qc(mq)
    if sq == mq:
        return f'<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:8px 0;"><span class="mr-pill" style="background:{sqc}18;color:{sqc};">{sq}</span><span class="mr-parr">-></span><span class="mr-pill" style="background:{mqc}18;color:{mqc};">{mq}</span><span style="color:#6B7280;font-size:11px;">Regime <b style="color:{sqc};">{sq}</b> CONFIRMED</span></div>'
    if sq=="Q3" and mq=="Q2":
        return f'<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:8px 0;"><span class="mr-pill" style="background:{sqc}18;color:{sqc};">{sq}</span><span class="mr-parr">-></span><span class="mr-pill" style="background:{mqc}18;color:{mqc};">{mq}</span><span style="color:#6B7280;font-size:11px;">{sq} STRUCT -> {mq} MONTHLY -> <b>Q1</b> ~6wk</span></div>'
    return f'<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:8px 0;"><span class="mr-pill" style="background:{sqc}18;color:{sqc};">{sq}</span><span class="mr-parr">-></span><span class="mr-pill" style="background:{mqc}18;color:{mqc};">{mq}</span><span style="color:#6B7280;font-size:11px;">Struct <b style="color:{sqc};">{sq}</b> -> Monthly <b style="color:{mqc};">{mq}</b></span></div>'

# ══════════════════════════════════════════════════════════════════════════════
# Gamma / Lev / DXY
# ══════════════════════════════════════════════════════════════════════════════
def _gamma(gamma):
    if not gamma or not gamma.get("ok"):
        note = (gamma or {}).get("note","GammaRegimeEngine unavailable")
        return f'<div class="mr-card"><div class="mr-card-h">GAMMA REGIME</div><div class="mr-card-s" style="color:#6B7280;">{note}</div></div>'
    th = _safe_float(gamma.get("throttle")) or 0.0
    r10 = _safe_float(gamma.get("rvol_10d"))
    r21 = _safe_float(gamma.get("rvol_21d"))
    vp = _safe_float(gamma.get("vol_premium"))
    bp = int(_safe_float(gamma.get("bar_pct")) or 50)
    color = str(gamma.get("color","#9CA3AF"))
    label = str(gamma.get("label","Unknown"))
    impl = str(gamma.get("impl",""))
    def f(v,fmt=".1f",s=""): return f"{v:{fmt}}{s}" if v is not None else "-"
    vpc = "#10B981" if (vp is not None and vp > 0) else "#EF4444"
    pw = max(0, min(100, bp-43))
    return (
        f'<div class="mr-card"><div class="mr-card-h">GAMMA REGIME</div>'
        f'<div class="mr-card-v" style="color:{color};font-size:18px;">{label.upper()}</div>'
        f'<div style="width:100%;height:3px;background:#1f2b3d;border-radius:2px;margin:8px 0;overflow:hidden;">'
        f'<div style="width:{pw}%;height:100%;background:{color};border-radius:2px;"></div></div>'
        f'<div class="mr-g2">'
        f'<div class="mr-gi"><span class="mr-gi-l">Throttle</span><span class="mr-gi-v" style="color:{color};">{f(th,"+.1f")}</span></div>'
        f'<div class="mr-gi"><span class="mr-gi-l">Vol Prem</span><span class="mr-gi-v" style="color:{vpc};">{f(vp,"+.1f","%")}</span></div>'
        f'<div class="mr-gi"><span class="mr-gi-l">rVol 10d</span><span class="mr-gi-v">{f(r10,".1f","%")}</span></div>'
        f'<div class="mr-gi"><span class="mr-gi-l">rVol 21d</span><span class="mr-gi-v">{f(r21,".1f","%")}</span></div></div>'
        f'<div class="mr-card-s" style="margin-top:8px;">{impl}</div></div>'
    )

def _lev(lev):
    if not lev or not lev.get("ok"):
        note = (lev or {}).get("note","LeveragedETFEngine unavailable")
        return f'<div class="mr-card"><div class="mr-card-h">LEVERAGED ETF FLOW</div><div class="mr-card-s" style="color:#6B7280;">{note}</div></div>'
    tot = _safe_float(lev.get("total_mcap_b"))
    lo = _safe_float(lev.get("long_exposure_b"))
    sh = _safe_float(lev.get("short_exposure_b"))
    lp = _safe_float(lev.get("long_pct")) or 0
    sp = _safe_float(lev.get("short_pct")) or 0
    op = max(0, round(100-lp-sp, 1))
    ath = bool(_safe_float(lev.get("is_ath")) or 0)
    rb = str(lev.get("rebalancing_pressure","-"))
    tl = lev.get("top_longs",[]); ts = lev.get("top_shorts",[])
    def b(v): return f"${v}B" if v is not None else "-"
    rc = {"HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#10B981"}.get(rb,"#6B7280")
    ath_b = ' <span style="color:#F59E0B;font-size:10px;">ATH</span>' if ath else ""
    tls = " - ".join(f'<b style="color:#10B981;font-size:10px;">{e["ticker"]}</b> <span style="font-size:10px;">${e["aum_b"]}B</span>' for e in tl[:3]) or "-"
    tss = " - ".join(f'<b style="color:#EF4444;font-size:10px;">{e["ticker"]}</b> <span style="font-size:10px;">${e["aum_b"]}B</span>' for e in ts[:3]) or "-"
    return (
        f'<div class="mr-card"><div class="mr-card-h">LEVERAGED ETF FLOW{ath_b}</div>'
        f'<div class="mr-g4">'
        f'<div class="mr-gi"><span class="mr-gi-l">Total</span><span class="mr-gi-v">{b(tot)}</span></div>'
        f'<div class="mr-gi"><span class="mr-gi-l">Long</span><span class="mr-gi-v" style="color:#10B981;">{b(lo)} ({lp:.0f}%)</span></div>'
        f'<div class="mr-gi"><span class="mr-gi-l">Short</span><span class="mr-gi-v" style="color:#EF4444;">{b(sh)} ({sp:.0f}%)</span></div>'
        f'<div class="mr-gi"><span class="mr-gi-l">Other</span><span class="mr-gi-v">{op:.0f}%</span></div></div>'
        f'<div class="mr-card-s" style="margin-top:8px;">Rebal: <b style="color:{rc};">{rb}</b> - '
        f'<span style="color:#10B981;">Longs:</span> {tls} - <span style="color:#EF4444;">Shorts:</span> {tss}</div></div>'
    )

def _dxy_corr(prices, window=15):
    dxy = prices.get("DX-Y.NYB")
    if dxy is None: return {}
    dxy = pd.to_numeric(dxy, errors="coerce").dropna()
    if len(dxy) < window + 2: return {}
    dxy_ret = dxy.pct_change().dropna()
    from config.settings import DXY_CORRELATION_ASSETS
    result = {}
    for label, ticker in DXY_CORRELATION_ASSETS.items():
        s = prices.get(ticker)
        if s is None: continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < window + 2: continue
        asset_ret = s.pct_change().dropna()
        combined = pd.concat([dxy_ret, asset_ret], axis=1, join="inner").dropna()
        combined.columns = ["dxy","asset"]
        if len(combined) >= window:
            corr = float(combined["dxy"].tail(window).corr(combined["asset"].tail(window)))
            if math.isfinite(corr): result[label] = round(corr, 2)
    return result

def _render_dxy(prices, dxy_corr, sq):
    if not dxy_corr:
        st.info("DXY correlation data unavailable."); return
    dxy = prices.get("DX-Y.NYB")
    dxy_trend = "-"
    if dxy is not None:
        dxy = pd.to_numeric(dxy, errors="coerce").dropna()
        if len(dxy) >= 22:
            r21 = float(dxy.iloc[-1]/dxy.iloc[-22]-1)
            dxy_trend = "BEARISH" if r21 < -0.005 else "BULLISH" if r21 > 0.005 else "NEUTRAL"
    st.markdown(
        f'<div class="mr-card"><div class="mr-card-h">KEY $USD CORRELATIONS (15D) - Keith McCullough</div>'
        f'<div style="font-size:11px;color:#9CA3AF;margin-bottom:8px;">DXY Trend: <b style="color:{"#EF4444" if "BEARISH" in dxy_trend else "#10B981" if "BULLISH" in dxy_trend else "#6B7280"};">{dxy_trend}</b>'
        f' - <span style="color:#6B7280;">Neg = USD weakness benefit | Pos = USD strength benefit</span></div></div>',
        unsafe_allow_html=True
    )
    rows = [{"Asset": label, "15D Corr": corr, "Direction": "<- USD bearish" if corr < -0.2 else ("-> USD bullish" if corr > 0.2 else "~ neutral")} for label, corr in dxy_corr.items()]
    st.dataframe(_df_style(pd.DataFrame(rows)).background_gradient(subset=["15D Corr"], cmap="RdYlGn", vmin=-1, vmax=1), hide_index=True, use_container_width=True, height=200)
    btc_corr = dxy_corr.get("Bitcoin", None)
    if btc_corr is not None:
        if "BEARISH" in dxy_trend and btc_corr < -0.3 and sq != "Q4":
            btc_c, btc_msg = "#10B981", f"BTC: DXY Bearish (corr {btc_corr:+.2f}) -> <b>BTC Bullish thesis intact</b>. LONG IBIT."
        elif "BULLISH" in dxy_trend:
            btc_c, btc_msg = "#EF4444", f"BTC: DXY Bullish (corr {btc_corr:+.2f}) -> <b>BTC headwind</b>. Scale back."
        else:
            btc_c, btc_msg = "#6B7280", f"BTC: DXY neutral (corr {btc_corr:+.2f}) -> Watch TREND before sizing."
        st.markdown(f'<div style="margin-top:6px;font-size:11px;color:{btc_c};padding:6px 10px;background:{btc_c}08;border-radius:4px;">{btc_msg}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Options / Alpha
# ══════════════════════════════════════════════════════════════════════════════
def _opt_card(opt, trend="neutral"):
    if not opt or not opt.get("ok"):
        reason = (opt or {}).get("reason","")
        st.caption("No options data" if reason in ("skip_no_options","no_options") else f"Options: {reason or 'unavailable'}")
        return
    sig = opt.get("options_signal","-")
    im = opt.get("implied_move_pct"); iv_pct = opt.get("iv_percentile")
    mp = opt.get("max_pain"); ll = opt.get("long_levels"); sl_data = opt.get("short_levels")
    g_call = opt.get("atm_greeks_call",{}) or {}
    key_puts = opt.get("key_puts",[]); key_calls = opt.get("key_calls",[])
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Signal", sig); c2.metric("Implied Move", f"+/-{im:.1%}" if im else "-")
    c3.metric("IV %ile", f"{iv_pct:.0%}" if iv_pct else "-"); c4.metric("Max Pain", f"${mp:.1f}" if mp else "-")
    gc1,gc2 = st.columns(2)
    with gc1:
        if ll and ll.get("ev_ok"):
            st.markdown(
                f'<div style="background:#10B98108;border:1px solid #10B98122;border-radius:6px;padding:10px;margin-top:6px;">'
                f'<div style="font-size:10px;font-weight:700;color:#10B981;margin-bottom:4px;">LONG SETUP</div>'
                f'<div style="font-size:11px;color:#E8ECF0;line-height:1.5;">Entry: <b>${ll["entry"]:.2f}</b> | TP1: <b>${ll["tp1"]:.2f}</b> | TP2: <b>${ll["tp2"]:.2f}</b><br>'
                f'Stop: ${ll["stop"]:.2f} | R/R: {ll["rr"]:.1f}x | {ll["holding"]}<br>'
                f'<span style="color:#6B7280;">Put support: {" - ".join(f"${k:.1f}" for k in key_puts[:2])}</span></div></div>',
                unsafe_allow_html=True
            )
    with gc2:
        if sl_data and sl_data.get("ev_ok"):
            st.markdown(
                f'<div style="background:#EF444408;border:1px solid #EF444422;border-radius:6px;padding:10px;margin-top:6px;">'
                f'<div style="font-size:10px;font-weight:700;color:#EF4444;margin-bottom:4px;">SHORT SETUP</div>'
                f'<div style="font-size:11px;color:#E8ECF0;line-height:1.5;">Entry: <b>${sl_data["entry"]:.2f}</b> | TP1: <b>${sl_data["tp1"]:.2f}</b> | TP2: <b>${sl_data["tp2"]:.2f}</b><br>'
                f'Stop: ${sl_data["stop"]:.2f} | R/R: {sl_data["rr"]:.1f}x | {sl_data["holding"]}<br>'
                f'<span style="color:#6B7280;">Call resist: {" - ".join(f"${k:.1f}" for k in key_calls[:2])}</span></div></div>',
                unsafe_allow_html=True
            )
    if g_call:
        with st.expander("Greeks (ATM Call)"):
            g1,g2,g3,g4 = st.columns(4)
            g1.metric("Delta", f"{g_call.get('delta','-'):.3f}" if g_call.get('delta') else "-")
            g2.metric("Gamma", f"{g_call.get('gamma','-'):.5f}" if g_call.get('gamma') else "-")
            g3.metric("Theta/day", f"{g_call.get('theta','-'):.3f}" if g_call.get('theta') else "-")
            g4.metric("Vega/1%", f"{g_call.get('vega','-'):.3f}" if g_call.get('vega') else "-")
    if opt.get("oi_heatmap"):
        oi_df = pd.DataFrame(opt["oi_heatmap"][:12]).rename(columns={"strike":"Strike","call_oi":"Call OI","put_oi":"Put OI","net":"Net (C-P)"})
        st.dataframe(_df_style(oi_df[["Strike","Call OI","Put OI","Net (C-P)"]]).background_gradient(subset=["Net (C-P)"],cmap="RdYlGn"), hide_index=True, use_container_width=True, height=160)

def _alpha_card(item, opt_result, v, tr, idx):
    ticker = item.get("ticker",""); sector = item.get("sector","").replace("_"," ").title()
    trend = item.get("trend",""); score = item.get("score",0); ev = item.get("ev",0)
    rf = item.get("regime_fit",0); constr = item.get("constraint",0)
    thesis = item.get("known_thesis","")[:70]; direction = item.get("direction","long")
    trap = item.get("regime_trap",False); px = _safe_float(v.get("px"))
    lrr = _safe_float(tr.get("lrr")); trr = _safe_float(tr.get("trr"))
    stretch = tr.get("stretch","-"); opt_sig = opt_result.get("options_signal","") if opt_result else ""
    tc = "#EF4444" if direction=="short" else "#10B981" if not trap else "#F59E0B"
    trap_warn = ' <span style="color:#F59E0B;font-size:10px;">TRAP</span>' if trap else ""
    with st.expander(f"{'SHORT' if direction=='short' else 'LONG'} {ticker} - {sector} | EV:{ev:.1f} | Score:{score:.0f}{trap_warn}", expanded=(idx < 3)):
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.markdown(
                f'<div style="font-size:11px;color:#E8ECF0;line-height:1.6;">'
                f'<span style="color:{tc};font-weight:700;">{direction.upper()}</span> - {sector} - Constraint {constr:.0%}<br>'
                f'<span style="color:#6B7280;">{thesis}</span><br>'
                f'Trend: {trend} - RF:{rf:.0%} - Stretch:{stretch}<br>'
                f'Px: ${px:.2f if px else "-"} | LRR:<b>{ff(lrr)}</b> | TRR:{ff(trr)}<br>Opt: {opt_sig}</div>',
                unsafe_allow_html=True
            )
        with c2:
            _opt_card(opt_result, trend)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False

with st.sidebar:
    st.markdown("## MacroRegime Pro")
    st.markdown("*Hedgeye GIP - v17.5*")
    st.divider()
    page = st.radio("", ["Dashboard","GIP Model","Risk Ranges","Alpha Center","Leaderboard","Global Quad","IHSG","Narratives","Discovery","Health","Playbook"], label_visibility="collapsed")
    st.divider()
    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"Snapshot: {snapshot_age_str()}")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("Refresh", use_container_width=True): st.session_state.loading=True
    with c2:
        if st.button("Force", use_container_width=True): st.session_state.loading=True; st.session_state.snap=None
    with st.expander("Universe"):
        inc_us = st.checkbox("US Stocks",True); inc_fx = st.checkbox("Forex",True)
        inc_comm = st.checkbox("Commodities",True); inc_cryp = st.checkbox("Crypto",True)
        inc_ihsg = st.checkbox("IHSG",True); inc_opt = st.checkbox("Options Data",True)
    st.divider()
    _s = st.session_state.snap
    if _s and _s.get("ok"):
        _g=_s.get("gip"); _gl=_s.get("global",{})
        _sq=_g.structural_quad if _g else "-"; _mq=_g.monthly_quad if _g else "-"; _gq=_gl.get("global_quad","-") if _gl else "-"
        st.caption(f"{_sq} Struct - {_mq} Monthly - {_gq} Global")
    else: st.caption("- - -")

# ── Load snapshot ─────────────────────────────────────────────────────────────
snap = st.session_state.snap
if snap is None:
    snap = load_snapshot(max_age_hours=6.0)
    if snap and snap.get("ok"): st.session_state.snap=snap

if st.session_state.loading or snap is None:
    from orchestrator import build_snapshot
    pb=st.progress(0.0); pt=st.empty()
    def prog(m,f): pb.progress(f); pt.caption(m)
    snap=build_snapshot(progress_cb=prog, include_us_stocks=inc_us, include_forex=inc_fx, include_commodities=inc_comm, include_crypto=inc_cryp, include_ihsg=inc_ihsg)
    st.session_state.snap=snap; st.session_state.loading=False
    pb.empty(); pt.empty(); st.rerun()

if not snap or not snap.get("ok"): st.error("No snapshot. Click Refresh to rebuild."); st.stop()

# ── Extract ───────────────────────────────────────────────────────────────────
gip=snap.get("gip"); global_=snap.get("global",{}); rr=snap.get("risk_ranges",{})
scen=snap.get("scenarios",{}); narr=snap.get("narratives",{}); disc=snap.get("discovery",{})
transition=snap.get("transition",None); health=snap.get("health",{}); analogs=snap.get("analogs",{})
btk=snap.get("bottleneck",{}); pb_data=snap.get("playbook",{}); prices=snap.get("prices",{})
auto_disc=snap.get("auto_discoveries",{}); fb_eval=snap.get("feedback_eval",{})
gamma_data=snap.get("gamma",{}); lev_data=snap.get("leveraged_etf",{})
sq=gip.structural_quad if gip else "Q3"; mq=gip.monthly_quad if gip else "Q2"
gq=global_.get("global_quad","Q3") if global_ else "Q3"; dxy_corr=_dxy_corr(prices)

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "Dashboard":
    st.markdown(f'<div style="font-size:10px;color:#6B7280;text-align:right;">v17.5 - Built {snap.get("build_time_s",0)}s - Prices:{snap.get("prices_loaded",0)} - FRED:{snap.get("fred_coverage",0)} - RR:{snap.get("price_frames_count",0)}</div>', unsafe_allow_html=True)
    st.markdown("# MacroRegime Pro - Dashboard")

    vbd=health.get("vix_bucket",{}) if health else {}; vb=vbd.get("bucket","-")
    vl=_safe_float(vbd.get("vix_last")) or 0; vn=vbd.get("note",""); vr=vbd.get("risk_mode","-")
    bcls="mr-ban-g" if vb=="Investable" else "mr-ban-y" if vb=="Chop" else "mr-ban-r" if vb=="Defensive" else ""
    if bcls: st.markdown(f'<div class="mr-ban {bcls}"><b>{"INVESTABLE" if vb=="Investable" else "CHOP" if vb=="Chop" else "DEFENSIVE"} BUCKET</b> - VIX {vl:.1f} - {vn} - Risk: {vr}</div>', unsafe_allow_html=True)

    ga_col, dxy_col = st.columns([1, 1.2])
    with ga_col: st.markdown(_gamma(gamma_data), unsafe_allow_html=True)
    with dxy_col: _render_dxy(prices, dxy_corr, sq)

    st.markdown(_lev(lev_data), unsafe_allow_html=True)

    _sq_q2p=(_safe_float((gip.structural_probs or {}).get("Q2",0)) or 0) if gip else 0
    _sq_sub=f"Q2 up {_sq_q2p:.0%}" if (sq=="Q3" and _sq_q2p>0.25) else ""
    c1,c2,c3,c4=st.columns(4)
    with c1: st.markdown(qcard("STRUCTURAL - Climate",sq,gip.structural_conf if gip else 0,_sq_sub),unsafe_allow_html=True)
    with c2:
        _mq_note="Model=Q1 (Hedgeye=Q2)" if mq=="Q1" and sq=="Q3" else ""
        st.markdown(qcard("MONTHLY - Weather",mq,gip.monthly_conf if gip else 0,_mq_note),unsafe_allow_html=True)
    with c3: st.markdown(qcard("GLOBAL - 50 Countries",gq,(_safe_float(global_.get("global_conf")) or 0) if global_ else 0,"GDP-weighted"),unsafe_allow_html=True)
    with c4:
        if gip:
            dc="#10B981" if gip.divergence=="aligned" else "#F59E0B" if gip.divergence=="divergent" else "#EF4444"
            st.markdown(f'<div class="mr-card"><div class="mr-card-h">ALIGNMENT</div><div class="mr-card-v" style="color:{dc};">{gip.divergence.upper()}</div><div class="mr-card-s">{gip.operating_regime}</div><div class="mr-card-m">Flip Risk: {gip.flip_hazard:.0%}</div></div>',unsafe_allow_html=True)

    if fb_eval and fb_eval.get("evaluated",0):
        ev=fb_eval.get("evaluated",0); pr=fb_eval.get("promoted",0); dm=fb_eval.get("demoted",0); wr=(pr/max(ev,1))*100
        w1,w2,w3,w4=st.columns(4)
        w1.markdown(f'<div class="mr-win"><div class="mr-win-l">Evaluated</div><div class="mr-win-v">{ev}</div></div>',unsafe_allow_html=True)
        w2.markdown(f'<div class="mr-win"><div class="mr-win-l">Promoted</div><div class="mr-win-v" style="color:#10B981;">{pr}</div></div>',unsafe_allow_html=True)
        w3.markdown(f'<div class="mr-win"><div class="mr-win-l">Demoted</div><div class="mr-win-v" style="color:#EF4444;">{dm}</div></div>',unsafe_allow_html=True)
        w4.markdown(f'<div class="mr-win"><div class="mr-win-l">Win Rate</div><div class="mr-win-v" style="color:{"#10B981" if wr>50 else "#F59E0B"};">{wr:.0f}%</div></div>',unsafe_allow_html=True)

    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}.get(fw,"#374151")
        fwi={"now":"NOW","1-2w":"SOON","3-6w":"WATCH","not yet":"HOLD"}.get(fw,"HOLD")
        if fw!="not yet": st.markdown(f'<div class="mr-fr" style="background:{fwc}08;border:1px solid {fwc}18;color:{fwc};"><b>FRONT-RUN: {fw.upper()}</b><br><span style="font-size:11px;">{fr}</span></div>',unsafe_allow_html=True)
        st.markdown(_pills(sq,mq),unsafe_allow_html=True)

    if pb_data:
        best5=" - ".join(pb_data.get("best_assets",[])[:6]); worst5=" - ".join(pb_data.get("worst_assets",[])[:5])
        st.markdown(f'<div class="mr-act"><div class="mr-card-h" style="margin-bottom:8px;">QUICK ACTION - {sq} - {mq}</div><div class="mr-act-r"><span class="mr-act-t" style="background:#10B98118;color:#10B981;">LONG</span><span style="color:#E8ECF0;">{best5}</span></div><div class="mr-act-r"><span class="mr-act-t" style="background:#EF444418;color:#EF4444;">AVOID</span><span style="color:#E8ECF0;">{worst5}</span></div><div style="margin-top:6px;font-size:10px;color:#6B7280;">Full detail -> GIP - Alpha - Playbook</div></div>',unsafe_allow_html=True)

    if auto_disc:
        brewing=[c for c in auto_disc.get("candidates",[]) if c.get("stage")=="brewing"]
        if brewing:
            tb=max(brewing,key=lambda x:x.get("confidence",0))
            st.markdown(f'<div style="margin-top:8px;font-size:11px;color:#6B7280;"><b>{len(brewing)}</b> pre-consensus - Top: <b>{tb.get("name","")}</b> -> Discovery</div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GIP MODEL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "GIP Model":
    st.markdown("# GIP Model - Growth - Inflation - Policy")
    st.caption("Hedgeye: YoY rate of change, second derivative.")
    if not gip: st.warning("No GIP data. Refresh."); st.stop()

    cc,cw=st.columns(2)
    with cc: st.markdown(f'<div class="mr-card"><div class="mr-card-h">STRUCTURAL - CLIMATE (Quarterly)</div><div class="mr-card-v" style="color:{qc(sq)};">{sq}</div><div class="mr-card-s">{qnc(sq)}</div><div class="mr-card-m">Conf: {gip.structural_conf:.0%} - Flip: {gip.flip_hazard:.0%} - Coverage: {gip.data_coverage:.0%}</div></div>',unsafe_allow_html=True)
    with cw:
        mq_note="Model=Q1 (Hedgeye=Q2)" if mq=="Q1" and sq=="Q3" else ""
        st.markdown(f'<div class="mr-card"><div class="mr-card-h">MONTHLY - WEATHER (3-6W)</div><div class="mr-card-v" style="color:{qc(mq)};">{mq}</div><div class="mr-card-s">{qnc(mq)}</div><div class="mr-card-m">Conf: {gip.monthly_conf:.0%} - {gip.divergence} - {gip.operating_regime}</div>{f"<div class=mr-card-s style=color:#F59E0B;>{mq_note}</div>" if mq_note else ""}</div>',unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Growth and Inflation Signals")
    f=gip.features; gm=_safe_float(f.get("growth_momentum")) or 0; im=_safe_float(f.get("inflation_momentum")) or 0
    gc2="#10B981" if gm>0 else "#EF4444"; ic2="#10B981" if im<0 else "#EF4444"
    m1,m2,m3,m4=st.columns(4)
    m1.markdown(f'<div class="mr-win"><div class="mr-win-l">Growth Momentum</div><div class="mr-win-v" style="color:{gc2};">{fp(gm)}</div><div style="font-size:10px;color:#6B7280;margin-top:2px;">{"Accel up" if gm>0 else "Decel down"}</div></div>',unsafe_allow_html=True)
    m2.markdown(f'<div class="mr-win"><div class="mr-win-l">Inflation Momentum</div><div class="mr-win-v" style="color:{ic2};">{fp(im)}</div><div style="font-size:10px;color:#6B7280;margin-top:2px;">{"Rising up" if im>0 else "Cooling down"}</div></div>',unsafe_allow_html=True)
    m3.markdown(f'<div class="mr-win"><div class="mr-win-l">Policy Score</div><div class="mr-win-v">{fp(f.get("policy_score"))}</div><div style="font-size:10px;color:#6B7280;margin-top:2px;">{"Dovish" if (_safe_float(f.get("policy_score")) or 0)>0.1 else "Hawkish" if (_safe_float(f.get("policy_score")) or 0)<-0.1 else "Neutral"}</div></div>',unsafe_allow_html=True)
    m4.markdown(f'<div class="mr-win"><div class="mr-win-l">Leading Indicator</div><div class="mr-win-v">{fp(f.get("leading_indicator_composite"))}</div><div style="font-size:10px;color:#6B7280;margin-top:2px;">FRED: {fp(f.get("data_coverage"))}</div></div>',unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Quad Transition Probabilities")
    QWINS={"Q1":"Tech, Small Caps, IBIT","Q2":"Energy, Materials, Commodity FX, IBIT","Q3":"Gold, Silver, Defensives, TLT","Q4":"TLT, Gold, Utilities, Cash"}
    def _tp(probs, cur_q, label, desc):
        if not probs: return
        sp=sorted(probs.items(),key=lambda x:x[1],reverse=True); top_q,top_p=sp[0]
        st.markdown(f'<div style="font-size:11px;color:#6B7280;margin-bottom:4px;"><b>{label}</b> - {desc}</div><div style="font-size:12px;color:#E8ECF0;margin-bottom:6px;">Now: <b>{cur_q}</b> -> Likely: <b style="color:{qc(top_q)};">{top_q}</b> ({top_p:.0%})</div>',unsafe_allow_html=True)
        st.plotly_chart(prob_bar(probs),use_container_width=True,config={"displayModeBar":False})
        if top_q!=cur_q: st.markdown(f'<div style="font-size:10px;color:#6B7280;margin-top:2px;">If {top_q}: <b>{QWINS.get(top_q,"")}</b></div>',unsafe_allow_html=True)
    sq_q2p=_safe_float((gip.structural_probs or {}).get("Q2",0)) or 0
    sq_desc=qnc(sq)+(f" - Q2 up {sq_q2p:.0%}" if sq=="Q3" and sq_q2p>0.25 else "")
    tp1,tp2,tp3=st.columns(3)
    with tp1: _tp(gip.structural_probs,sq,"STRUCTURAL",sq_desc)
    with tp2: _tp(gip.monthly_probs,mq,"MONTHLY",qnc(mq))
    with tp3:
        gprobs=global_.get("global_probs",{}) if global_ else {}
        if gprobs: _tp(gprobs,global_.get("dominant_quad",gq),"GLOBAL","50 Countries")

    if analogs and analogs.get("top_analogs"):
        st.markdown("---")
        st.markdown("### Historical Analogs")
        st.caption(analogs.get("composite_note",""))
        for i,a in enumerate(analogs["top_analogs"]):
            with st.expander(f"{a['label']} - {a.get('similarity',0):.0%}",expanded=(i==0)):
                cc2=st.columns(3)
                cc2[0].markdown(f"**1M:** {a.get('path_1m','')}")
                cc2[1].markdown(f"**3M:** {a.get('path_3m','')}")
                cc2[2].markdown(f"**6M:** {a.get('path_6m','')}")
                st.markdown(f"**Next bias:** {a.get('next_bias','')}")

# ══════════════════════════════════════════════════════════════════════════════
# RISK RANGES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Risk Ranges":
    st.markdown("# Risk Range - TRADE - TREND - TAIL")
    st.caption("LRR = buy zone. TRR = trim zone. TREND break = exit.")
    ar=rr.get("asset_ranges",{})
    if not ar: st.warning("No risk range data. Refresh."); st.stop()

    all_a=sorted([(s,a) for s,v in ar.items() for a in v.get("alerts",[])],key=lambda x:{"CRITICAL":0,"HIGH":1,"MEDIUM":2}.get(x[1].get("priority"),3))
    if all_a:
        st.markdown("### Live Alerts")
        for sym,a in all_a[:20]:
            ic="CRIT" if a["priority"]=="CRITICAL" else "HIGH" if a["priority"]=="HIGH" else "MED"
            bdr="#EF4444" if a["priority"]=="CRITICAL" else "#F59E0B"
            st.markdown(f'<div class="mr-al" style="border-color:{bdr};"><b>[{sym}]</b> {ic}: {a["action"]} {a["duration"]} - {a.get("note","")}</div>',unsafe_allow_html=True)
        st.markdown("---")

    cl1,cl2,cl3=st.columns([1,2,1])
    with cl1: mkt_f=st.selectbox("Market",["All","us_equity","forex","commodity","crypto","ihsg"])
    with cl2: srch=st.text_input("Search ticker","")
    with cl3: show_opt=st.checkbox("Show options",False)

    rows=[]
    for sym,v in ar.items():
        if mkt_f!="All" and v.get("market","")!=mkt_f: continue
        if srch and srch.upper() not in sym.upper(): continue
        tr=v.get("trade",{}); px=_safe_float(v.get("px"))
        rows.append({"Ticker":sym,"Px":ff(px),"LRR":ff(_safe_float(tr.get("lrr"))),"TRR":ff(_safe_float(tr.get("trr"))),
                     "Signal":v.get("composite","-").upper(),"Quality":v.get("quality","-"),"Stretch":tr.get("stretch","-"),
                     "Hurst":ff(_safe_float(v.get("trend",{}).get("hurst"))),"Market":v.get("market","-"),"Trap":"TRAP" if v.get("regime_trap") else ""})
    if rows:
        st.dataframe(_df_style(pd.DataFrame(rows)),hide_index=True,use_container_width=True,height=440)
        if show_opt and rows:
            st.markdown("### Options Overlay (top 5 bullish)")
            from engines.options_engine import OptionsEngine
            opt_eng=OptionsEngine()
            for sym in [r["Ticker"] for r in rows if r["Signal"]=="BULLISH"][:5]:
                v=ar.get(sym,{}); tr=v.get("trade",{}); px=_safe_float(v.get("px")) or 0
                if px>0:
                    st.markdown(f"**{sym}**")
                    opt=opt_eng.analyze(sym,px,_safe_float(tr.get("lrr")),_safe_float(tr.get("trr")),v.get("composite","neutral"))
                    _opt_card(opt,v.get("composite","neutral"))
    else: st.info("No data matches filter. Click Refresh.")

# ══════════════════════════════════════════════════════════════════════════════
# ALPHA CENTER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Alpha Center":
    st.markdown("# Alpha Center - Front-Run - Bottleneck - Options")
    st.caption("Buy best EV+ setups near LRR with options confirmation.")
    if not btk: st.warning("No bottleneck data. Refresh."); st.stop()

    from engines.options_engine import OptionsEngine
    opt_eng=OptionsEngine(); ar=rr.get("asset_ranges",{})
    from config.settings import BOTTLENECK_PROFILES
    def _filter_btk(items):
        filtered=[]
        for item in (items or []):
            sector=item.get("sector","generic")
            profile=BOTTLENECK_PROFILES.get(sector,{})
            constraint=profile.get("constraint",item.get("constraint",0.5))
            if sector in ("staples",) and constraint<0.70: continue
            v=ar.get(item.get("ticker",""),{}); tr=v.get("trade",{})
            if tr.get("stretch","") in ("overbought","extended") and item.get("direction","long")=="long": continue
            filtered.append(item)
        return filtered

    l1_filtered=_filter_btk(btk.get("level_1",[]))
    l2_filtered=_filter_btk(btk.get("level_2",[]))
    s1,s2,s3,s4=st.columns(4)
    s1.markdown(f'<div class="mr-win"><div class="mr-win-l">Level 1 (High EV)</div><div class="mr-win-v" style="color:#10B981;">{len(l1_filtered)}</div></div>',unsafe_allow_html=True)
    s2.markdown(f'<div class="mr-win"><div class="mr-win-l">Level 2 (Building)</div><div class="mr-win-v" style="color:#F59E0B;">{len(l2_filtered)}</div></div>',unsafe_allow_html=True)
    s3.markdown(f'<div class="mr-win"><div class="mr-win-l">Watch (Brewing)</div><div class="mr-win-v" style="color:#6366F1;">{len(btk.get("watch",[]))}</div></div>',unsafe_allow_html=True)
    s4.markdown(f'<div class="mr-win"><div class="mr-win-l">Avoid (Trap)</div><div class="mr-win-v" style="color:#EF4444;">{len(btk.get("avoid",[]))}</div></div>',unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Level 1 - Act Now (Highest EV)")
    st.caption("Structural bottleneck + Bullish TREND + near LRR + options confirmation.")
    if not l1_filtered: st.info("No Level 1 setups. Wait for better setups.")
    else:
        opt_results=opt_eng.batch_analyze([item["ticker"] for item in l1_filtered[:8]],ar)
        for i,item in enumerate(l1_filtered[:8]):
            v=ar.get(item["ticker"],{}); tr=v.get("trade",{})
            _alpha_card(item,opt_results.get(item["ticker"],{}),v,tr,i)

    st.markdown("---")
    with st.expander(f"Level 2 - Building ({len(l2_filtered)})",expanded=False):
        if not l2_filtered: st.info("No Level 2 setups.")
        else:
            opt_results_2=opt_eng.batch_analyze([item["ticker"] for item in l2_filtered[:6]],ar)
            for i,item in enumerate(l2_filtered[:6]):
                v=ar.get(item["ticker"],{}); tr=v.get("trade",{})
                _alpha_card(item,opt_results_2.get(item["ticker"],{}),v,tr,i)

    watch_filtered=[w for w in (btk.get("watch",[]) or []) if w.get("direction")!="long" or ar.get(w.get("ticker",""),{}).get("trade",{}).get("stretch","") not in ("overbought","extended")]
    with st.expander(f"Watch - Brewing ({len(watch_filtered)})",expanded=False):
        if not watch_filtered: st.info("Nothing brewing.")
        else:
            rows_w=[{"Ticker":w["ticker"],"Sector":w["sector"].replace("_"," ").title(),"Trend":w["trend"],"EV":f'{w.get("ev",0):.2f}',"Score":f'{w.get("score",0):.2f}',"Thesis":w.get("known_thesis","")[:55]} for w in watch_filtered[:20]]
            st.dataframe(_df_style(pd.DataFrame(rows_w)),hide_index=True,use_container_width=True,height=min(len(rows_w)*38+40,480))

    with st.expander(f"Avoid - Regime Trap ({len(btk.get('avoid',[]))})",expanded=False):
        avoid_rows=[{"Ticker":a["ticker"],"Sector":a["sector"].replace("_"," ").title(),"Trend":a["trend"],"Score":f'{a.get("score",0):.2f}'} for a in (btk.get("avoid",[]) or [])[:20]]
        if avoid_rows: st.dataframe(_df_style(pd.DataFrame(avoid_rows)),hide_index=True,use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# LEADERBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Leaderboard":
    st.markdown("# Leaderboard - Signal Strength Stocks")
    st.caption("Quality A = Bullish TRADE+TREND near LRR + volume confirm. Min 1%, max 3%.")
    ar=rr.get("asset_ranges",{})
    if not ar: st.warning("No risk range data. Refresh."); st.stop()

    best_set=set(pb_data.get("best_assets",[])); worst_set=set(pb_data.get("worst_assets",[]))
    long_picks=[]; short_picks=[]
    for sym,v in ar.items():
        qual=v.get("quality","none"); comp=v.get("composite","neutral")
        tr=v.get("trade",{}); tn=v.get("trend",{}); px=_safe_float(v.get("px"))
        vol_c=_safe_float(tr.get("volume_confirm")) or 0.5; stretch=tr.get("stretch","neutral"); hurst=_safe_float(tn.get("hurst")) or 0.5
        from config.settings import TICKER_SECTOR; sector=TICKER_SECTOR.get(sym,"generic")
        if qual in ("A","B") and comp=="bullish":
            lrr=_safe_float(tr.get("lrr")); trr=_safe_float(tr.get("trr")); nlrr=stretch in ("oversold","reset_zone")
            if px and lrr and trr and (trr-lrr)>1e-9: pos=(px-lrr)/(trr-lrr); nlrr=pos<=0.35 or nlrr
            if stretch in ("overbought","extended"): continue
            rf=sym in best_set; ra=sym in worst_set
            sc=(50 if qual=="A" else 30)+(25 if nlrr else 0)+(15 if vol_c>0.6 else 0)+(10 if rf else 0)+(-20 if ra else 0)+(5 if hurst>0.5 else 0)
            long_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"stretch":stretch,"vol_c":vol_c,"hurst":hurst,"regime_fit":rf,"score":sc,"note":"Near LRR" if nlrr else f"Stretch: {stretch}","sector":sector})
        if qual in ("short_A","short_B") and comp=="bearish":
            lrr=_safe_float(tr.get("lrr")); trr=_safe_float(tr.get("trr")); ntrr=stretch in ("overbought","extended")
            if px and lrr and trr and (trr-lrr)>1e-9: pos=(px-lrr)/(trr-lrr); ntrr=pos>=0.65 or ntrr
            if stretch in ("oversold","reset_zone"): continue
            rf=sym in worst_set
            sc=(50 if qual=="short_A" else 30)+(25 if ntrr else 0)+(15 if vol_c>0.6 else 0)+(10 if rf else 0)+(5 if hurst>0.5 else 0)
            short_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"stretch":stretch,"vol_c":vol_c,"hurst":hurst,"regime_fit":rf,"score":sc,"note":"Near TRR" if ntrr else f"Stretch: {stretch}","sector":sector})
    long_picks.sort(key=lambda x:-x["score"]); short_picks.sort(key=lambda x:-x["score"])

    s1,s2,s3,s4=st.columns(4)
    s1.markdown(f'<div class="mr-win"><div class="mr-win-l">Bullish Names</div><div class="mr-win-v">{len(long_picks)}</div></div>',unsafe_allow_html=True)
    s2.markdown(f'<div class="mr-win"><div class="mr-win-l">Quality A Longs</div><div class="mr-win-v" style="color:#10B981;">{sum(1 for p in long_picks if p["quality"]=="A")}</div></div>',unsafe_allow_html=True)
    s3.markdown(f'<div class="mr-win"><div class="mr-win-l">Quality A Shorts</div><div class="mr-win-v" style="color:#EF4444;">{sum(1 for p in short_picks if p["quality"]=="short_A")}</div></div>',unsafe_allow_html=True)
    s4.markdown(f'<div class="mr-win"><div class="mr-win-l">Regime Traps</div><div class="mr-win-v" style="color:#F59E0B;">{sum(1 for v in ar.values() if v.get("regime_trap"))}</div></div>',unsafe_allow_html=True)

    st.markdown("---")
    opt_ticker=st.selectbox("Options overlay:",["-"]+[p["ticker"] for p in long_picks[:15]])
    if opt_ticker!="-":
        v=ar.get(opt_ticker,{}); tr_d=v.get("trade",{}); px=_safe_float(v.get("px")) or 0
        if px>0:
            from engines.options_engine import OptionsEngine
            opt_r=OptionsEngine().analyze(opt_ticker,px,_safe_float(tr_d.get("lrr")),_safe_float(tr_d.get("trr")),v.get("composite","neutral"))
            _opt_card(opt_r,v.get("composite","neutral"))

    st.markdown("---")
    st.markdown("### TOP 21 LONG IDEAS")
    for p in long_picks[:21]:
        bc="#00D4AA" if p['regime_fit'] else "#10B981"
        st.markdown(f'<div class="mr-pk" style="border-color:{bc};"><div class="mr-pk-t">{p["ticker"]} ({p["quality"]}) {"OK" if p["regime_fit"] else "CAUTION"} Score {p["score"]:.0f} - {p["sector"].replace("_"," ").title()}</div><div class="mr-pk-m">Px: {ff(p["px"])} - LRR: <b style="color:#10B981;">{ff(p["lrr"])}</b> - TRR: {ff(p["trr"])} - {p["note"]}</div><div class="mr-pk-u">Vol: {fp(p["vol_c"])} - Hurst: {ff(p["hurst"])}</div></div>',unsafe_allow_html=True)
    if not long_picks: st.info("No Quality A/B longs near LRR. Market extended.")

    st.markdown("---")
    st.markdown("### SHORT IDEAS")
    for p in short_picks[:15]:
        st.markdown(f'<div class="mr-pk" style="border-color:#EF4444;"><div class="mr-pk-t">{p["ticker"]} ({p["quality"]}) {"OK" if p["regime_fit"] else "CAUTION"} Score {p["score"]:.0f} - {p["sector"].replace("_"," ").title()}</div><div class="mr-pk-m">Px: {ff(p["px"])} - TRR: <b style="color:#EF4444;">{ff(p["trr"])}</b> - LRR: {ff(p["lrr"])} - {p["note"]}</div><div class="mr-pk-u">Vol: {fp(p["vol_c"])} - Hurst: {ff(p["hurst"])}</div></div>',unsafe_allow_html=True)
    if not short_picks: st.info("No Quality Short setups.")

    with st.expander("Full Signal Table"):
        all_rows=([{"T":p["ticker"],"Side":"LONG","Q":p["quality"],"Sc":f'{p["score"]:.0f}',"Px":ff(p["px"]),"LRR":ff(p["lrr"]),"TRR":ff(p["trr"]),"Stretch":p["stretch"],"RF":"OK" if p["regime_fit"] else "-"} for p in long_picks]+
                  [{"T":p["ticker"],"Side":"SHORT","Q":p["quality"],"Sc":f'{p["score"]:.0f}',"Px":ff(p["px"]),"LRR":ff(p["lrr"]),"TRR":ff(p["trr"]),"Stretch":p["stretch"],"RF":"OK" if p["regime_fit"] else "-"} for p in short_picks])
        if all_rows: st.dataframe(_df_style(pd.DataFrame(all_rows)),hide_index=True,use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL QUAD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Global Quad":
    st.markdown("# Global Quad - 50 Countries")
    st.caption("GIP applied to country ETFs. GDP-weighted.")
    if not global_: st.warning("No global data. Refresh."); st.stop()

    gconf=_safe_float(global_.get("global_conf")) or 0; gprobs=global_.get("global_probs",{}) or {}
    c1,c2=st.columns([1,2.2])
    with c1:
        st.markdown(qcard("GLOBAL QUAD",gq,gconf,"50 Country ETFs"),unsafe_allow_html=True)
        if gprobs:
            st.markdown("<div style='margin-top:6px;'></div>",unsafe_allow_html=True)
            st.plotly_chart(prob_bar(gprobs,"Global Probabilities"),use_container_width=True,config={"displayModeBar":False})
    with c2:
        st.markdown('<div class="mr-card-h" style="margin-bottom:8px;">COUNTRY HEATMAP</div>',unsafe_allow_html=True)
        cq=global_.get("country_quads",{}) or {}; heat=[]
        if cq:
            for country,data in cq.items():
                if isinstance(data,(list,tuple)) and len(data)>=3: etf,quad,conf=str(data[0]),str(data[1]),_safe_float(data[2]) or 0
                elif isinstance(data,dict): etf,quad,conf=str(data.get("etf","")),str(data.get("quad","")),_safe_float(data.get("conf",0)) or 0
                else: continue
                if quad: heat.append({"Country":country,"ETF":etf,"Quad":quad,"Conf":f"{conf:.0%}"})
        if heat:
            df=pd.DataFrame(heat)
            st.dataframe(_df_style(df).map(lambda v:f"color:{QC.get(v,'#9CA3AF')};font-weight:700;",subset=["Quad"]),hide_index=True,height=380,use_container_width=True)
        else:
            st.markdown('<div class="mr-card" style="display:flex;align-items:center;justify-content:center;min-height:160px;"><div class="mr-card-s" style="text-align:center;">Country Quad data unavailable.<br>Click Refresh to load country ETFs.</div></div>',unsafe_allow_html=True)

    st.markdown('<div style="height:10px;"></div>',unsafe_allow_html=True)
    st.markdown('<div class="mr-card-h">EM RECOVERY SIGNAL</div>',unsafe_allow_html=True)
    em_sig=(btk.get("em_recovery",{}) or {}) if btk else {}
    if em_sig:
        conf=_safe_float(em_sig.get("confidence")) or 0
        ec="#10B981" if conf>0.6 else "#F59E0B" if conf>0.4 else "#6B7280"
        st.markdown(f'<div class="mr-card"><div class="mr-card-v" style="color:{ec};font-size:18px;">{em_sig.get("trigger","")}</div><div class="mr-card-s">{em_sig.get("rationale","")}</div><div class="mr-card-m">Confidence: {conf:.0%} - Best: {", ".join(em_sig.get("best",[])[:6])}</div></div>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="mr-card" style="display:flex;align-items:center;justify-content:center;min-height:80px;"><div class="mr-card-s" style="text-align:center;color:#6B7280;">EM recovery signal unavailable.<br>Data appears after bottleneck scan.</div></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# IHSG
# ══════════════════════════════════════════════════════════════════════════════
elif page == "IHSG":
    st.markdown("# IHSG - Indonesia Market")
    st.caption("Local signal + sector thesis. No options data (IHSG options illiquid).")
    from config.settings import IHSG_UNIVERSE, IHSG_BUCKETS
    ar=rr.get("asset_ranges",{}); ihsg={sym:v for sym,v in ar.items() if v.get("market","")=="ihsg"}
    if ihsg:
        rows=[{"Ticker":sym,"Px":ff(_safe_float(v.get("px")),0),"LRR":ff(_safe_float(v.get("trade",{}).get("lrr")),0),
               "TRR":ff(_safe_float(v.get("trade",{}).get("trr")),0),"Signal":v.get("composite","-").upper(),
               "Quality":v.get("quality","-"),"Stretch":v.get("trade",{}).get("stretch","-"),"Trap":"TRAP" if v.get("regime_trap") else ""} for sym,v in ihsg.items()]
        st.dataframe(_df_style(pd.DataFrame(rows)),hide_index=True,use_container_width=True)
    else: st.info("IHSG data unavailable. Enable IHSG and click Refresh.")

    st.markdown("---")
    st.markdown("### Sector Buckets")
    for bucket,tickers in IHSG_BUCKETS.items():
        with st.expander(f"{bucket.replace('_',' ')} ({len(tickers)})"):
            b_rows=[]
            for t in tickers:
                s=prices.get(t)
                if s is None: continue
                s=pd.to_numeric(s,errors="coerce").dropna()
                r1=float(s.iloc[-1]/s.iloc[-22]-1) if len(s)>=22 else 0
                r3=float(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else 0
                b_rows.append({"Ticker":t,"1M":f"{r1:+.1%}","3M":f"{r3:+.1%}"})
            if b_rows: st.dataframe(_df_style(pd.DataFrame(b_rows)),hide_index=True,use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# NARRATIVES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Narratives":
    st.markdown("# Narratives - Thematic Scoring")
    st.caption("Active = confirmed. Building = traction. Brewing = pre-consensus.")
    if not narr: st.warning("Narrative data empty. Click Force to rebuild."); st.stop()
    active=narr.get("active_narratives",[]) or []
    if not active: st.info("Narratives inactive. Click Force to rebuild.")
    for n in sorted(active,key=lambda x:x.get("score",0),reverse=True):
        score=n.get("score",0); sc="#10B981" if score>0.6 else "#F59E0B" if score>0.4 else "#6B7280"
        with st.expander(f"{n.get('name','')} - {score:.0%}"):
            st.markdown(f"**Thesis:** {n.get('thesis','')}")
            st.markdown(f"**Tickers:** {' - '.join(n.get('tickers',[])[:8])}")
            inv=n.get("invalidators",[]); best=n.get("best",[]); worst=n.get("worst",[])
            if inv: st.markdown(f"**Invalidators:** {', '.join(inv[:3])}")
            if best: st.markdown(f"**Best:** {' - '.join(best[:10])}")
            if worst: st.markdown(f"**Worst:** {' - '.join(worst[:10])}")

# ══════════════════════════════════════════════════════════════════════════════
# DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Discovery":
    st.markdown("# Early Discovery - Pre-Consensus")
    st.caption("Autonomy: regime fit + price cluster + supply chain + news NLP.")
    cands=(auto_disc.get("candidates",[]) if auto_disc else [])+ (disc.get("discoveries",[]) if disc else [])
    if not cands: st.info("No discoveries yet. Click Force to rebuild with Autonomy Stack."); st.stop()
    for stage,sc in [("active","#10B981"),("building","#F59E0B"),("brewing","#6366F1")]:
        items=[c for c in cands if c.get("stage")==stage]
        if not items: continue
        st.markdown(f"### {stage.upper()} ({len(items)})")
        for c in items:
            conf=c.get("confidence",c.get("conviction",0)); pump=c.get("pump_risk",0)
            with st.expander(f"{c.get('name','')} - Conf:{conf:.0%} - Pump:{pump:.0%}"):
                st.markdown(f"**Thesis:** {c.get('thesis','')}")
                ben=c.get("beneficiary_tickers",[]); fade=c.get("fade_tickers",[])
                if ben: st.markdown(f"**Beneficiaries:** {' - '.join(ben[:8])}")
                if fade: st.markdown(f"**Fade:** {' - '.join(fade[:5])}")
                cs=c.get("confirmation_signal",""); inv=c.get("invalidators",[])
                if cs: st.markdown(f"**Confirmation:** {cs}")
                if inv: st.markdown(f"**Invalidators:** {', '.join(inv) if isinstance(inv,list) else inv}")

# ══════════════════════════════════════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Health":
    st.markdown("# Market Health - VIX - Breadth - Crash Meter")
    if not health: st.warning("No health data. Refresh."); st.stop()

    vb_d=health.get("vix_bucket",{}); vb_b=vb_d.get("bucket","-")
    bcls="mr-ban-g" if vb_b=="Investable" else "mr-ban-y" if vb_b=="Chop" else "mr-ban-r" if vb_b=="Defensive" else ""
    if bcls: st.markdown(f'<div class="mr-ban {bcls}"><b>VIX BUCKET: {vb_b.upper()}</b> - {vb_d.get("note","")}</div>',unsafe_allow_html=True)

    crash=health.get("crash",{}) or {}
    if crash:
        st.markdown("### Crash Meter")
        for k,v in crash.get("signals",{}).items(): st.progress(float(v),text=f"{k.replace('_',' ').title()}: {v:.0%}")
        st.markdown(f"**State:** {crash.get('state','')} - Score: {_safe_float(crash.get('score',0)):.0%}")
        if crash.get("reasons"): st.markdown("**Reasons:** "+" - ".join(crash["reasons"]))

    breadth=health.get("market_health",{}) or {}
    if breadth:
        st.markdown("### Sector Breadth")
        b1,b2,b3,b4=st.columns(4)
        b1.metric("Score",f"{_safe_float(breadth.get('score')) or 0:.2f}")
        b2.metric("Verdict",breadth.get("verdict","-"))
        b3.metric("Support",f"{breadth.get('positive_sectors_1m',0)}/{breadth.get('total_buckets',0)}")
        b4.metric("EqW Health",f"{_safe_float(breadth.get('eqw_health')) or 0:.2f}")
        for note in (breadth.get("notes") or []): st.markdown(f"- {note}")

    fg=health.get("fear_greed",{}) or {}
    if fg:
        st.markdown("---")
        st.markdown("### Fear and Greed")
        fgs=_safe_float(fg.get("score")) or 50
        fgc="#10B981" if fgs<25 else "#F59E0B" if fgs<55 else "#EF4444"
        st.markdown(f"**Score:** {fgs:.0f}/100 - {fg.get('label','Neutral')}",unsafe_allow_html=True)
        st.progress(fgs/100)

# ══════════════════════════════════════════════════════════════════════════════
# PLAYBOOK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Playbook":
    st.markdown("# Regime Playbook")
    st.caption(f"{sq} Structural - {mq} Monthly - Scored by data, not opinion.")

    if pb_data:
        st.markdown("### Regime Positioning")
        col1,col2=st.columns(2)
        with col1:
            ma=" - ".join(pb_data.get("monthly_adds",[]))
            ma_html=f'<div class="mr-card-s" style="margin-top:6px;">Monthly adds: <b>{ma}</b></div>' if pb_data.get("monthly_adds") else ""
            st.markdown(f'<div class="mr-card"><div class="mr-card-h" style="color:#10B981;">LONG - {sq}</div><div style="font-size:13px;color:#E8ECF0;line-height:1.5;margin-top:4px;">{" - ".join(pb_data.get("best_assets",[]))}</div><div class="mr-card-s">Style: {pb_data.get("style","")}</div><div class="mr-card-s">FX: {pb_data.get("fx","")}</div><div class="mr-card-s">Bonds: {pb_data.get("bonds","")}</div>{ma_html}</div>',unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="mr-card"><div class="mr-card-h" style="color:#EF4444;">AVOID - {sq}</div><div style="font-size:13px;color:#E8ECF0;line-height:1.5;margin-top:4px;">{" - ".join(pb_data.get("worst_assets",[]))}</div><div class="mr-card-s">Hedge: {pb_data.get("hedge","BTAL")}</div><div class="mr-card-s">{pb_data.get("sizing_note","Min 1% - Max 3%")}</div></div>',unsafe_allow_html=True)

    btc_rr=rr.get("asset_ranges",{}).get("IBIT",rr.get("asset_ranges",{}).get("BTC-USD",{}))
    btc_sig=btc_rr.get("composite","-"); btc_c="#10B981" if btc_sig=="bullish" else "#EF4444" if btc_sig=="bearish" else "#6B7280"
    btc_corr_val=dxy_corr.get("Bitcoin","-"); q4_note=" (Q4 EXIT BTC)" if sq=="Q4" else ""
    st.markdown(f'<div style="margin-top:10px;padding:8px 12px;background:#1a2332;border-radius:6px;border-left:2px solid {btc_c};font-size:11px;color:#E8ECF0;"><b>BITCOIN (IBIT):</b> {btc_sig.upper()}{q4_note} - DXY/BTC 15D corr: {btc_corr_val}</div>',unsafe_allow_html=True)

    scenarios_list=scen.get("scenarios",[]) if scen else []
    if scenarios_list:
        st.markdown("---")
        st.markdown("### Scenario Probability Map")
        badges=["BASE","ALT","RISK","TAIL"]; badge_colors=["#10B981","#F59E0B","#EF4444","#6366F1"]
        row1=st.columns(2); row2=st.columns(2); grids=[row1[0],row1[1],row2[0],row2[1]]
        for i,(sc_item,col) in enumerate(zip(scenarios_list[:4],grids)):
            pc=badge_colors[i]; em=sc_item.em_note[:55]+"..." if len(sc_item.em_note)>55 else sc_item.em_note
            with col:
                st.markdown(f'<div class="mr-sc"><div class="mr-sc-b" style="color:{pc};">{badges[i]} P={sc_item.probability:.0%} - Conf={sc_item.confirmation_score:.0%}</div><div class="mr-sc-t">{sc_item.name}</div><div class="mr-sc-d">{sc_item.headline}</div><div class="mr-sc-l" style="color:#10B981;margin-bottom:2px;">Best: {" - ".join(sc_item.best_assets[:4])}</div><div class="mr-sc-l" style="color:#EF4444;margin-bottom:4px;">Avoid: {" - ".join(sc_item.worst_assets[:4])}</div><div style="font-size:9px;color:#6B7280;">{em}</div></div>',unsafe_allow_html=True)
        bc=scen.get("base_case") if scen else None
        if bc and hasattr(bc,"confirmation_triggers"):
            st.markdown("---")
            ct,ci=st.columns(2)
            with ct:
                st.markdown(f"### Confirmation Triggers ({bc.name})")
                for t in getattr(bc,"confirmation_triggers",[]): st.markdown(f"- {t}")
            with ci:
                st.markdown("### Invalidators")
                for inv in getattr(bc,"invalidators",[]): st.markdown(f"- {inv}")

    if gip:
        st.markdown("---")
        st.markdown("### GIP Feature Data")
        f=gip.features
        rows=[["Growth Momentum",fp(f.get("growth_momentum")),"up" if (_safe_float(f.get("growth_momentum")) or 0)>0 else "down"],
              ["Inflation Momentum",fp(f.get("inflation_momentum")),"up" if (_safe_float(f.get("inflation_momentum")) or 0)>0 else "down"],
              ["Policy Score",fp(f.get("policy_score")),""],
              ["Leading Indicator",fp(f.get("leading_indicator_composite")),""],
              ["Data Coverage",fp(f.get("data_coverage")),""],
              ["Flip Hazard",f"{gip.flip_hazard:.0%}",""],
              ["Structural Conf",f"{gip.structural_conf:.0%}",""],
              ["Monthly Conf",f"{gip.monthly_conf:.0%}",""]]
        st.dataframe(_df_style(pd.DataFrame(rows,columns=["Signal","Value","Dir"])),hide_index=True,use_container_width=True)
