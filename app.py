"""app.py — MacroRegime Pro v17

Fixes from v16:
 - Gamma: Series ambiguity error → explicit float() conversion
 - DXY panel: HTML rendering → use st.dataframe + st.metric (no raw HTML)
 - ETF Pro: removed (merged into Alpha Center + Risk Ranges)
 - Monthly Q1 bug: display note when model diverges from Hedgeye manual call
 - Alpha Center: NEW — merged Front-Run + Bottleneck + Options entry/TP/stop
 - Options Engine: integrated across Alpha Center, Risk Ranges™
 - Country Quad: fixed empty display
 - Narratives: added fallback message + retry hint
 - Bottleneck Watch/Avoid: filtered low-constraint items (agri/staples)

Tab structure (11 tabs, no duplication):
 🏠 Dashboard — Status, Gamma, DXY Corr, LevETF, Quads, Quick Action
 📈 GIP Model — Climate/Weather, G/I signals, Transition charts, Analogs
 🎯 Risk Ranges™ — LRR/TRR alerts + full table + options overlay
 ⚡ Alpha Center — Front-Run timing + Bottleneck + Options entry/TP/stop [NEW]
 📊 Leaderboard — Quality A stock picks
 🌍 Global Quad — 50 countries + EM recovery
 🇮🇩 IHSG — Indonesia local stocks + sectors
 📖 Narratives — Thematic scoring
 🔮 Discovery — Pre-consensus AI discoveries
 🏥 Health — VIX, Crash meter, Breadth, Fear & Greed
 📋 Playbook — Full regime action plan + scenarios
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

st.set_page_config(
    page_title="MacroRegime Pro", page_icon="📊",
    layout="wide", initial_sidebar_state="expanded"
)

st.markdown("""<style>
.gamma-deep-pos{color:#10B981;font-weight:700;}
.gamma-pos{color:#34D399;font-weight:600;}
.gamma-trans{color:#F59E0B;font-weight:600;}
.gamma-neg{color:#EF4444;font-weight:600;}
.gamma-deep-neg{color:#B91C1C;font-weight:700;}
.alpha-long{border-left:4px solid #10B981;padding-left:12px;}
.alpha-short{border-left:4px solid #EF4444;padding-left:12px;}
.alpha-watch{border-left:4px solid #F59E0B;padding-left:12px;}
</style>""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
QC = {"Q1":"#00D4AA","Q2":"#F59E0B","Q3":"#EF4444","Q4":"#6366F1"}
QN = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}
QNC = {"Q1":"Goldilocks — Growth↑ Infl↓","Q2":"Reflation — Growth↑ Infl↑",
       "Q3":"Stagflation — Growth↓ Infl↑","Q4":"Deflation — Growth↓ Infl↓"}

def qc(q): return QC.get(q,"#9CA3AF")
def qn(q): return QN.get(q,q)
def qnc(q): return QNC.get(q,q)
def fp(v):
    try: return f"{float(v):.1%}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"
def ff(v, d=2):
    try: return f"{float(v):.{d}f}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"
def _safe_float(v):
    """Convert any value to float safely, return None if impossible."""
    if v is None: return None
    try:
        if isinstance(v, pd.Series): v = v.iloc[0]
        f = float(v)
        return f if math.isfinite(f) else None
    except: return None

def qcard(label, q, conf, sub=""):
    c = qc(q)
    s = f'<div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{sub}</div>' if sub else ""
    return f'''
<div style="background:#1F2B3D;border-radius:8px;padding:14px;text-align:center;">
  <div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;">{label}</div>
  <div style="font-size:28px;font-weight:800;color:{c};margin:6px 0;">{q}</div>
  <div style="font-size:12px;color:#E8ECF0;">{qn(q)}</div>
  <div style="font-size:10px;color:#6B7280;margin-top:4px;">Conf: {conf:.0%}</div>
  {s}
</div>'''

def prob_bar(probs, title=""):
    fig = go.Figure()
    for q,p in sorted((probs or {}).items()):
        fig.add_bar(x=[q],y=[p],marker_color=qc(q),text=[f"<b>{p:.0%}</b>"],textposition="outside",name=q)
    fig.update_layout(showlegend=False,height=200,margin=dict(t=25,b=5,l=0,r=0),
                      paper_bgcolor="#111827",plot_bgcolor="#111827",
                      font=dict(color="#E8ECF0",family="JetBrains Mono"),
                      title=dict(text=title,font=dict(size=11,color="#9CA3AF")),
                      yaxis=dict(range=[0,1.1],tickformat=".0%",showgrid=True,gridcolor="#1F2B3D"),
                      xaxis=dict(showgrid=False),bargap=0.35)
    return fig

def _sequence_pills(sq, mq):
    sqc=qc(sq); mqc=qc(mq)
    p="padding:3px 11px;border-radius:4px;font-weight:700;font-size:12px;"
    arr='→'
    if sq==mq:
        return f'<div style="display:flex;gap:8px;align-items:center;margin:8px 0;"><span style="{p}background:{sqc};color:#fff;">{sq}</span>{arr}<span style="{p}background:{mqc};color:#fff;">{mq}</span><span style="font-size:11px;color:#10B981;">Regime:{sq} CONFIRMED</span><span style="font-size:10px;color:#6B7280;">Structural & Monthly aligned</span></div>'
    if sq=="Q3" and mq=="Q2":
        return f'<div style="display:flex;gap:8px;align-items:center;margin:8px 0;"><span style="{p}background:{sqc};color:#fff;">{sq}</span>{arr}<span style="{p}background:{mqc};color:#fff;">{mq}</span><span style="font-size:11px;color:#F59E0B;">Sequencing:{sq} STRUCT{arr}{mq} MONTHLY{arr}Q1 TARGET</span><span style="font-size:10px;color:#6B7280;">~6wk · watch CPI -50bps</span></div>'
    return f'<div style="display:flex;gap:8px;align-items:center;margin:8px 0;"><span style="{p}background:{sqc};color:#fff;">{sq}</span>{arr}<span style="{p}background:{mqc};color:#fff;">{mq}</span><span style="font-size:11px;color:#6366F1;">Struct:{sq}{arr}Monthly:{mq}</span><span style="font-size:10px;color:#6B7280;">leading → lagging</span></div>'

# ── Gamma panel (FIX: explicit float conversion to prevent Series ambiguity) ──
def _render_gamma(gamma: dict) -> str:
    if not gamma or not gamma.get("ok"):
        note=(gamma or {}).get("note","GammaRegimeEngine belum berjalan — tambahkan ke orchestrator step 14e.")
        return f'<div style="background:#1F2B3D;border-radius:8px;padding:12px;"><b>⚡ GAMMA REGIME</b><br/><span style="color:#9CA3AF;font-size:12px;">{note}</span></div>'
    # FIX: explicit safe float conversion for all values
    th = _safe_float(gamma.get("throttle")) or 0.0
    r10 = _safe_float(gamma.get("rvol_10d"))
    r21 = _safe_float(gamma.get("rvol_21d"))
    vix = _safe_float(gamma.get("vix"))
    vp = _safe_float(gamma.get("vol_premium")) # FIX: was causing Series ambiguity
    bp = int(_safe_float(gamma.get("bar_pct")) or 50)
    color = str(gamma.get("color","#9CA3AF"))
    label = str(gamma.get("label","Unknown"))
    action = str(gamma.get("action","—"))
    impl = str(gamma.get("impl",""))
    regime = str(gamma.get("regime","UNKNOWN"))
    css = {"DEEP_POSITIVE":"gamma-deep-pos","POSITIVE":"gamma-pos","TRANSITION":"gamma-trans",
           "NEGATIVE":"gamma-neg","DEEP_NEGATIVE":"gamma-deep-neg"}.get(regime,"gamma-trans")
    def f(v,fmt=".1f",s=""): return f"{v:{fmt}}{s}" if v is not None else "—"
    # FIX: use _safe_float result (float) not original (possibly Series)
    vpc = "#10B981" if (vp is not None and vp > 0) else "#EF4444"
    pw = max(0, min(100, bp-43))
    return f'''
<div style="background:#1F2B3D;border-radius:8px;padding:14px;">
  <div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;">⚡ GAMMA REGIME — Tier 1 Alpha Approx</div>
  <div style="font-size:22px;font-weight:800;color:{color};margin:6px 0;">{label.upper()}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px;font-size:12px;">
    <div>Throttle (approx)<br/><b style="color:{color};">{f(th,"+.1f")}</b></div>
    <div>rVol 10d<br/><b>{f(r10,".1f","%")}</b></div>
    <div>rVol 21d<br/><b>{f(r21,".1f","%")}</b></div>
    <div>Vol Premium<br/><b style="color:{vpc};">{f(vp,"+.1f","%")}</b></div>
  </div>
  <div style="margin-top:10px;font-size:11px;color:#6B7280;">{impl}</div>
  <div style="margin-top:6px;width:100%;background:#374151;height:6px;border-radius:3px;">
    <div style="width:{pw}%;background:{color};height:6px;border-radius:3px;"></div>
  </div>
</div>'''

def _render_lev(lev: dict) -> str:
    if not lev or not lev.get("ok"):
        note=(lev or {}).get("note","LeveragedETFEngine belum berjalan.")
        return f'<div style="background:#1F2B3D;border-radius:8px;padding:12px;"><b>📊 LEVERAGED ETF FLOW</b><br/><span style="color:#9CA3AF;font-size:12px;">{note}</span></div>'
    tot=_safe_float(lev.get("total_mcap_b")); lo=_safe_float(lev.get("long_exposure_b"))
    sh=_safe_float(lev.get("short_exposure_b")); si=_safe_float(lev.get("single_crypto_b"))
    lp=float(lev.get("long_pct") or 0); sp=float(lev.get("short_pct") or 0)
    op=max(0,round(100-lp-sp,1)); ath=bool(lev.get("is_ath",False))
    rb=str(lev.get("rebalancing_pressure","—"))
    tl=lev.get("top_longs",[]); ts=lev.get("top_shorts",[])
    def b(v): return f"${v}B" if v is not None else "—"
    rc={"HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#10B981"}.get(rb,"#6B7280")
    ath_b=' <span style="color:#F59E0B;">ATH</span>' if ath else ""
    tls=" · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in tl[:3]) or "—"
    tss=" · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in ts[:3]) or "—"
    return f'''
<div style="background:#1F2B3D;border-radius:8px;padding:14px;">
  <div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;">📊 LEVERAGED ETF FLOW{ath_b}</div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:8px;margin-top:10px;font-size:11px;">
    <div>Total<br/><b>{b(tot)}</b></div>
    <div>Long<br/><b style="color:#10B981;">{b(lo)} ({lp:.0f}%)</b></div>
    <div>Short<br/><b style="color:#EF4444;">{b(sh)} ({sp:.0f}%)</b></div>
    <div>Other<br/><b>{op:.0f}%</b></div>
  </div>
  <div style="margin-top:8px;font-size:11px;">Rebal: <b style="color:{rc};">{rb}</b></div>
  <div style="margin-top:6px;font-size:10px;color:#6B7280;">Longs: {tls}</div>
  <div style="margin-top:2px;font-size:10px;color:#6B7280;">Shorts: {tss} · yfinance AUM · cache 6h</div>
</div>'''

# ── DXY Correlations (FIX: use Streamlit native components, not raw HTML bars) ─
def _compute_dxy_corr(prices: dict, window: int = 15) -> dict:
    """15D rolling correlation vs DXY. Returns {label: corr_float}."""
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
            if math.isfinite(corr):
                result[label] = round(corr, 2)
    return result

def _render_dxy_section(prices: dict, dxy_corr: dict, sq: str):
    """
    FIX: Render DXY correlations using native Streamlit components.
    No raw HTML bar divs — was causing source code display bug.
    """
    if not dxy_corr:
        st.info("DXY correlation data belum tersedia. Pastikan DX-Y.NYB loaded.")
        return

    # DXY TREND
    dxy = prices.get("DX-Y.NYB")
    dxy_trend = "—"
    if dxy is not None:
        dxy = pd.to_numeric(dxy, errors="coerce").dropna()
        if len(dxy) >= 22:
            r21 = float(dxy.iloc[-1]/dxy.iloc[-22]-1)
            dxy_trend = "BEARISH 📉" if r21 < -0.005 else "BULLISH 📈" if r21 > 0.005 else "NEUTRAL ↔"

    st.markdown(f"**💱 KEY $USD CORRELATIONS (15D)** — Keith McCullough | DXY Trend: `{dxy_trend}`")
    st.caption("← Negative = benefits from USD weakness | Positive = benefits from USD strength →")

    # Build dataframe for display
    rows = []
    for label, corr in dxy_corr.items():
        direction = "← USD bearish" if corr < -0.2 else ("→ USD bullish" if corr > 0.2 else "~neutral")
        rows.append({"Asset": label, "15D Corr": corr, "Direction": direction})
    df = pd.DataFrame(rows)
    st.dataframe(
        df.style.background_gradient(subset=["15D Corr"], cmap="RdYlGn", vmin=-1, vmax=1),
        hide_index=True, use_container_width=True, height=200
    )

    # BTC implication
    btc_corr = dxy_corr.get("Bitcoin", None)
    if btc_corr is not None:
        btc_c = "#10B981" if ("BEARISH" in dxy_trend and btc_corr < -0.3 and sq != "Q4") else "#EF4444" if "BULLISH" in dxy_trend else "#6B7280"
        if "BEARISH" in dxy_trend and btc_corr < -0.3 and sq != "Q4":
            btc_msg = f"₿ BTC: DXY Bearish TREND (corr {btc_corr:+.2f}) → **BTC Bullish TREND thesis intact**. LONG IBIT."
        elif "BULLISH" in dxy_trend:
            btc_msg = f"₿ BTC: DXY Bullish TREND (corr {btc_corr:+.2f}) → **BTC headwind**. Scale back."
        else:
            btc_msg = f"₿ BTC: DXY neutral (corr {btc_corr:+.2f}) → Watch TREND signal before sizing."
        st.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:10px;margin-top:8px;font-size:12px;color:{btc_c};">{btc_msg}</div>', unsafe_allow_html=True)

# ── Options card renderer ─────────────────────────────────────────────────────
def _render_options_card(opt: dict, trend: str = "neutral"):
    """Show options overlay: entry/TP/stop, Greeks, Max Pain."""
    if not opt or not opt.get("ok"):
        reason = (opt or {}).get("reason","")
        if reason in ("skip_no_options","no_options"):
            st.caption("No options data (futures/FX/IHSG)")
        else:
            st.caption(f"Options: {reason or 'unavailable'}")
        return

    sig = opt.get("options_signal","—")
    sig_color = "#10B981" if "LONG" in sig else "#EF4444" if "SHORT" in sig else "#6B7280"
    im = opt.get("implied_move_pct"); iv_pct = opt.get("iv_percentile")
    mp = opt.get("max_pain"); pc = opt.get("pc_ratio")
    ll = opt.get("long_levels"); sl_data = opt.get("short_levels")
    g_call = opt.get("atm_greeks_call",{}) or {}
    key_puts = opt.get("key_puts",[])
    key_calls = opt.get("key_calls",[])

    with st.container():
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Options Signal", sig)
        c2.metric("Implied Move", f"±{im:.1%}" if im else "—")
        c3.metric("IV Percentile", f"{iv_pct:.0%}" if iv_pct else "—")
        c4.metric("Max Pain", f"${mp:.1f}" if mp else "—")

        gc1,gc2 = st.columns(2)
        with gc1:
            if ll and ll.get("ev_ok"):
                st.markdown(f'''
<div class="alpha-long" style="background:#111827;border-radius:6px;padding:10px;">
  <div style="font-size:10px;color:#10B981;text-transform:uppercase;">✅ LONG SETUP</div>
  <div style="font-size:12px;margin-top:4px;">Entry: <b>${ll["entry"]:.2f}</b> | TP1: <b>${ll["tp1"]:.2f}</b> | TP2: <b>${ll["tp2"]:.2f}</b></div>
  <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">Stop: ${ll["stop"]:.2f} | R/R: {ll["rr"]:.1f}x | {ll["holding"]}</div>
  <div style="font-size:10px;color:#6B7280;margin-top:4px;">Put support: {" · ".join(f"${k:.1f}" for k in key_puts[:2])}</div>
</div>''', unsafe_allow_html=True)
        with gc2:
            if sl_data and sl_data.get("ev_ok"):
                st.markdown(f'''
<div class="alpha-short" style="background:#111827;border-radius:6px;padding:10px;">
  <div style="font-size:10px;color:#EF4444;text-transform:uppercase;">🔴 SHORT SETUP</div>
  <div style="font-size:12px;margin-top:4px;">Entry: <b>${sl_data["entry"]:.2f}</b> | TP1: <b>${sl_data["tp1"]:.2f}</b> | TP2: <b>${sl_data["tp2"]:.2f}</b></div>
  <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">Stop: ${sl_data["stop"]:.2f} | R/R: {sl_data["rr"]:.1f}x | {sl_data["holding"]}</div>
  <div style="font-size:10px;color:#6B7280;margin-top:4px;">Call resist: {" · ".join(f"${k:.1f}" for k in key_calls[:2])}</div>
</div>''', unsafe_allow_html=True)

        if g_call:
            with st.expander("📊 Greeks (ATM Call)"):
                g1,g2,g3,g4 = st.columns(4)
                g1.metric("Delta", f"{g_call.get('delta','—'):.3f}" if g_call.get('delta') else "—")
                g2.metric("Gamma", f"{g_call.get('gamma','—'):.5f}" if g_call.get('gamma') else "—")
                g3.metric("Theta/day", f"{g_call.get('theta','—'):.3f}" if g_call.get('theta') else "—")
                g4.metric("Vega/1%", f"{g_call.get('vega','—'):.3f}" if g_call.get('vega') else "—")
        if opt.get("oi_heatmap"):
            oi_df = pd.DataFrame(opt["oi_heatmap"][:12])
            oi_df = oi_df.rename(columns={"strike":"Strike","call_oi":"Call OI","put_oi":"Put OI","net":"Net (C-P)"})
            st.dataframe(oi_df[["Strike","Call OI","Put OI","Net (C-P)"]].style.background_gradient(subset=["Net (C-P)"],cmap="RdYlGn"),
                         hide_index=True, use_container_width=True, height=180)

# ── Alpha Center card (Bottleneck item + Options overlay) ────────────────────
def _render_alpha_card(item: dict, opt_result: dict, v: dict, tr: dict, idx: int):
    """One alpha card showing bottleneck + RR + options."""
    ticker = item.get("ticker","")
    sector = item.get("sector","").replace("_"," ").title()
    trend = item.get("trend","")
    score = item.get("score",0)
    ev = item.get("ev",0)
    rf = item.get("regime_fit",0)
    constr = item.get("constraint",0)
    thesis = item.get("known_thesis","")[:80]
    direction = item.get("direction","long")
    trap = item.get("regime_trap",False)
    px = _safe_float(v.get("px"))
    lrr = _safe_float(tr.get("lrr"))
    trr = _safe_float(tr.get("trr"))
    stretch = tr.get("stretch","—")
    opt_sig = opt_result.get("options_signal","") if opt_result else ""

    css = "alpha-short" if direction=="short" else "alpha-long" if not trap else "alpha-watch"
    tc = "#EF4444" if direction=="short" else "#10B981" if not trap else "#F59E0B"

    trap_warn = ' ⚠️ REGIME TRAP' if trap else ""

    with st.expander(f"{'🔴' if direction=='short' else '🟢'} **{ticker}** — {sector} | EV: {ev:.2f} | Score: {score:.2f}{trap_warn}", expanded=(idx < 3)):
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.markdown(f'''
<div class="{css}">
  <div style="font-size:10px;color:{tc};text-transform:uppercase;">{'SHORT' if direction=="short" else 'LONG'} · {sector} · Constraint {constr:.0%}</div>
  <div style="font-size:11px;color:#E8ECF0;margin-top:4px;">{thesis}</div>
  <div style="font-size:10px;color:#9CA3AF;margin-top:6px;">Trend: {trend} · RF: {rf:.0%} · Stretch: {stretch}</div>
  <div style="font-size:10px;color:#6B7280;margin-top:4px;">Px: ${px:.2f if px else "—"} | LRR: <b>{ff(lrr)}</b> | TRR: {ff(trr)}</div>
  <div style="font-size:10px;color:#6B7280;margin-top:2px;">Opt: {opt_sig}</div>
</div>''', unsafe_allow_html=True)
        with c2:
            _render_options_card(opt_result, trend)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False

with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.markdown("*Hedgeye GIP · v17 · Autonomy + Options*")
    st.divider()
    page = st.radio("", [
        "🏠 Dashboard",
        "📈 GIP Model",
        "🎯 Risk Ranges™",
        "⚡ Alpha Center",
        "📊 Leaderboard",
        "🌍 Global Quad",
        "🇮🇩 IHSG",
        "📖 Narratives",
        "🔮 Discovery",
        "🏥 Health",
        "📋 Playbook",
    ], label_visibility="collapsed")
    st.divider()
    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"📸 {snapshot_age_str()}")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("🔄 Refresh", use_container_width=True): st.session_state.loading=True
    with c2:
        if st.button("⚡ Force", use_container_width=True):
            st.session_state.loading=True; st.session_state.snap=None
    with st.expander("⚙️ Universe"):
        inc_us = st.checkbox("US Stocks",True)
        inc_fx = st.checkbox("Forex",True)
        inc_comm = st.checkbox("Commodities",True)
        inc_cryp = st.checkbox("Crypto",True)
        inc_ihsg = st.checkbox("IHSG",True)
        inc_opt = st.checkbox("Options Data",True)
    st.divider()
    _s = st.session_state.snap
    if _s and _s.get("ok"):
        _g=_s.get("gip"); _gl=_s.get("global",{})
        _sq=_g.structural_quad if _g else "—"
        _mq=_g.monthly_quad if _g else "—"
        _gq=_gl.get("global_quad","—") if _gl else "—"
        st.caption(f"Hedgeye: {_sq} Struct · {_mq} Monthly · {_gq} Global")
    else:
        st.caption("Hedgeye: — Struct · — Monthly · — Global")

# ── Load snapshot ─────────────────────────────────────────────────────────────
snap = st.session_state.snap
if snap is None:
    snap = load_snapshot(max_age_hours=6.0)
    if snap and snap.get("ok"): st.session_state.snap=snap

if st.session_state.loading or snap is None:
    from orchestrator import build_snapshot
    pb=st.progress(0.0); pt=st.empty()
    def prog(m,f): pb.progress(f); pt.caption(m)
    snap=build_snapshot(progress_cb=prog, include_us_stocks=inc_us, include_forex=inc_fx,
                        include_commodities=inc_comm, include_crypto=inc_cryp, include_ihsg=inc_ihsg)
    st.session_state.snap=snap; st.session_state.loading=False
    pb.empty(); pt.empty(); st.rerun()

if not snap or not snap.get("ok"):
    st.error("❌ No snapshot. Click 🔄 Refresh to rebuild."); st.stop()

# ── Extract ───────────────────────────────────────────────────────────────────
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
mq = gip.monthly_quad if gip else "Q2"
gq = global_.get("global_quad","Q3") if global_ else "Q3"

# Pre-compute DXY correlations
dxy_corr = _compute_dxy_corr(prices)

# ══════════════════════════════════════════════════════════════════════════════
# 🏠 DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown(f'<div style="font-size:10px;color:#6B7280;text-align:right;">v17 · Built {snap.get("build_time_s",0)}s · Prices: {snap.get("prices_loaded",0)} · FRED: {snap.get("fred_coverage",0)} · RR: {snap.get("price_frames_count",0)}</div>', unsafe_allow_html=True)
    st.markdown("# MacroRegime Pro — Dashboard")

    # VIX Bucket
    vbd=health.get("vix_bucket",{}) if health else {}
    vb=vbd.get("bucket","—"); vl=_safe_float(vbd.get("vix_last")) or 0
    vn=vbd.get("note",""); vr=vbd.get("risk_mode","—")
    if vb=="Investable": vh=f'<div style="background:#064E3B;border-radius:8px;padding:12px;"><div style="font-size:10px;color:#10B981;text-transform:uppercase;">🟢 INVESTABLE BUCKET</div><div style="font-size:14px;color:#E8ECF0;margin-top:4px;">VIX {vl:.1f} · {vn}</div><div style="font-size:10px;color:#6B7280;">Risk Mode: {vr}</div></div>'
    elif vb=="Chop": vh=f'<div style="background:#451A03;border-radius:8px;padding:12px;"><div style="font-size:10px;color:#F59E0B;text-transform:uppercase;">🟡 CHOP BUCKET</div><div style="font-size:14px;color:#E8ECF0;margin-top:4px;">VIX {vl:.1f} · {vn}</div><div style="font-size:10px;color:#6B7280;">Risk Mode: {vr}</div></div>'
    elif vb=="Defensive": vh=f'<div style="background:#450A0A;border-radius:8px;padding:12px;"><div style="font-size:10px;color:#EF4444;text-transform:uppercase;">🔴 DEFENSIVE BUCKET</div><div style="font-size:14px;color:#E8ECF0;margin-top:4px;">VIX {vl:.1f} · {vn}</div><div style="font-size:10px;color:#6B7280;">Risk Mode: {vr}</div></div>'
    else: vh=""
    if vh: st.markdown(vh, unsafe_allow_html=True)
    st.markdown("", unsafe_allow_html=True)

    # Gamma + DXY in 2 columns
    ga_col, dxy_col = st.columns([1.2,1])
    with ga_col: st.markdown(_render_gamma(gamma_data), unsafe_allow_html=True)
    with dxy_col:
        st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)
        _render_dxy_section(prices, dxy_corr, sq) # FIX: native Streamlit components
        st.markdown('<div style="height:4px;"></div>', unsafe_allow_html=True)

    # LevETF
    st.markdown(_render_lev(lev_data), unsafe_allow_html=True)

    # Quad Cards
    _sq_q2p = (_safe_float((gip.structural_probs or {}).get("Q2",0)) or 0) if gip else 0
    _sq_sub = f"Q2↑ {_sq_q2p:.0%}" if (sq=="Q3" and _sq_q2p>0.25) else ""
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(qcard("STRUCTURAL — Climate",sq,gip.structural_conf if gip else 0,_sq_sub),unsafe_allow_html=True)
    with c2:
        _mq_note = ""
        if mq=="Q1" and sq=="Q3":
            _mq_note = "⚠ Model=Q1 (Hedgeye manual=Q2)"
        st.markdown(qcard("MONTHLY — Weather",mq,gip.monthly_conf if gip else 0,_mq_note),unsafe_allow_html=True)
    with c3: st.markdown(qcard("GLOBAL — 50 Countries",gq,(_safe_float(global_.get("global_conf")) or 0) if global_ else 0,"GDP-weighted"),unsafe_allow_html=True)
    with c4:
        if gip:
            st.markdown(f'''
<div style="background:#1F2B3D;border-radius:8px;padding:14px;text-align:center;">
  <div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;">ALIGNMENT</div>
  <div style="font-size:18px;font-weight:700;color:#E8ECF0;margin:6px 0;">{gip.divergence.upper()}</div>
  <div style="font-size:11px;color:#6B7280;">{gip.operating_regime}</div>
  <div style="font-size:10px;color:#6B7280;margin-top:4px;">Flip Risk: {gip.flip_hazard:.0%}</div>
</div>''', unsafe_allow_html=True)

    # Win Rate
    if fb_eval and fb_eval.get("evaluated",0):
        ev=fb_eval.get("evaluated",0); pr=fb_eval.get("promoted",0)
        dm=fb_eval.get("demoted",0); wr=(pr/max(ev,1))*100
        st.markdown("",unsafe_allow_html=True)
        w1,w2,w3,w4=st.columns(4)
        w1.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:8px;text-align:center;font-size:11px;">Evaluated<br/><b>{ev}</b></div>',unsafe_allow_html=True)
        w2.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:8px;text-align:center;font-size:11px;">Promoted<br/><b style="color:#10B981;">{pr}</b></div>',unsafe_allow_html=True)
        w3.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:8px;text-align:center;font-size:11px;">Demoted<br/><b style="color:#EF4444;">{dm}</b></div>',unsafe_allow_html=True)
        w4.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:8px;text-align:center;font-size:11px;">Win Rate<br/><b>{wr:.0f}%</b></div>',unsafe_allow_html=True)

    # Front-Run + Sequencing pills (summary only on Dashboard)
    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}.get(fw,"#374151")
        fwi={"now":"🚨","1-2w":"⚡","3-6w":"👀","not yet":"🛑"}.get(fw,"🛑")
        if fw!="not yet":
            st.markdown(f'<div style="background:{fwc}20;border-left:4px solid {fwc};border-radius:4px;padding:10px;margin:8px 0;"><div style="font-size:12px;color:{fwc};font-weight:700;">{fwi} FRONT-RUN: {fw.upper()}</div><div style="font-size:11px;color:#E8ECF0;margin-top:4px;">{fr}</div></div>',unsafe_allow_html=True)
    st.markdown(_sequence_pills(sq,mq),unsafe_allow_html=True)

    # Quick Action
    if pb_data:
        best5=" · ".join(pb_data.get("best_assets",[])[:6])
        worst5=" · ".join(pb_data.get("worst_assets",[])[:5])
        st.markdown(f'''
<div style="background:#1F2B3D;border-radius:8px;padding:14px;margin-top:10px;">
  <div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;margin-bottom:8px;">🎯 QUICK ACTION — {sq} Structural · {mq} Monthly</div>
  <div style="font-size:12px;color:#E8ECF0;">✅ <b>LONG:</b> {best5}</div>
  <div style="font-size:12px;color:#E8ECF0;margin-top:6px;">❌ <b>AVOID:</b> {worst5}</div>
  <div style="font-size:10px;color:#6B7280;margin-top:8px;">Full detail → <b>📈 GIP Model</b> · <b>⚡ Alpha Center</b> · <b>📋 Playbook</b></div>
</div>''', unsafe_allow_html=True)

    # Discovery summary (1-liner)
    if auto_disc:
        brewing=[c for c in auto_disc.get("candidates",[]) if c.get("stage")=="brewing"]
        if brewing:
            tb=max(brewing,key=lambda x:x.get("confidence",0))
            st.markdown(f'<div style="font-size:11px;color:#6366F1;margin-top:8px;">🔮 {len(brewing)} pre-consensus — Top: <b>{tb.get("name","")}</b> → <b>🔮 Discovery</b></div>',unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📈 GIP MODEL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 GIP Model":
    st.markdown("# 📈 GIP Model — Growth · Inflation · Policy")
    st.caption("Hedgeye: YoY rate of change, second derivative. 'Heating up or cooling down?' — 30 data points monthly, 90 quarterly.")
    if not gip: st.warning("No GIP data. Refresh."); st.stop()

    st.markdown("### 🌤 Climate vs. Weather")
    cc,cw=st.columns(2)
    with cc:
        st.markdown(f'''
<div style="background:#1F2B3D;border-radius:8px;padding:14px;">
  <div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;">STRUCTURAL — CLIMATE (Quarterly)</div>
  <div style="font-size:24px;font-weight:800;color:{qc(sq)};margin:6px 0;">{sq}</div>
  <div style="font-size:12px;color:#E8ECF0;">{qnc(sq)}</div>
  <div style="font-size:10px;color:#6B7280;margin-top:8px;">Conf: {gip.structural_conf:.0%} · Flip Risk: {gip.flip_hazard:.0%} · Coverage: {gip.data_coverage:.0%}</div>
</div>''', unsafe_allow_html=True)
    with cw:
        mq_note = ""
        if mq=="Q1" and sq=="Q3":
            mq_note = "⚠ Model computing Q1. Hedgeye manual call = Q2. Check inflation_level weight."
        st.markdown(f'''
<div style="background:#1F2B3D;border-radius:8px;padding:14px;">
  <div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;">MONTHLY — WEATHER (3-6 Week Overlay)</div>
  <div style="font-size:24px;font-weight:800;color:{qc(mq)};margin:6px 0;">{mq}</div>
  <div style="font-size:12px;color:#E8ECF0;">{qnc(mq)}</div>
  <div style="font-size:10px;color:#6B7280;margin-top:8px;">Conf: {gip.monthly_conf:.0%} · {gip.divergence} · {gip.operating_regime}</div>
  {f'<div style="font-size:11px;color:#F59E0B;margin-top:6px;">{mq_note}</div>' if mq_note else ""}
</div>''', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📊 Growth & Inflation Signals")
    f=gip.features; gm=_safe_float(f.get("growth_momentum")) or 0; im=_safe_float(f.get("inflation_momentum")) or 0
    gc2="#10B981" if gm>0 else "#EF4444"; ic2="#10B981" if im<0 else "#EF4444"
    m1,m2,m3,m4=st.columns(4)
    m1.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:10px;text-align:center;"><div style="font-size:10px;color:#9CA3AF;">Growth Momentum</div><div style="font-size:18px;font-weight:700;color:{gc2};margin:4px 0;">{fp(gm)}</div><div style="font-size:10px;color:#6B7280;">{"Accel ↑" if gm>0 else "Decel ↓"}</div></div>',unsafe_allow_html=True)
    m2.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:10px;text-align:center;"><div style="font-size:10px;color:#9CA3AF;">Inflation Momentum</div><div style="font-size:18px;font-weight:700;color:{ic2};margin:4px 0;">{fp(im)}</div><div style="font-size:10px;color:#6B7280;">{"Rising ↑" if im>0 else "Cooling ↓"}</div></div>',unsafe_allow_html=True)
    m3.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:10px;text-align:center;"><div style="font-size:10px;color:#9CA3AF;">Policy Score</div><div style="font-size:18px;font-weight:700;margin:4px 0;">{fp(f.get("policy_score"))}</div><div style="font-size:10px;color:#6B7280;">{"Dovish" if (_safe_float(f.get("policy_score")) or 0)>0.1 else "Hawkish" if (_safe_float(f.get("policy_score")) or 0)<-0.1 else "Neutral"}</div></div>',unsafe_allow_html=True)
    m4.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:10px;text-align:center;"><div style="font-size:10px;color:#9CA3AF;">Leading Indicator</div><div style="font-size:18px;font-weight:700;margin:4px 0;">{fp(f.get("leading_indicator_composite"))}</div><div style="font-size:10px;color:#6B7280;">FRED: {fp(f.get("data_coverage"))}</div></div>',unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📊 Quad Transition Probabilities")
    QWINS={"Q1":"Tech, Small Caps, IBIT","Q2":"Energy, Materials, Commodity FX, IBIT","Q3":"Gold, Silver, Defensives, TLT","Q4":"TLT, Gold, Utilities, Cash"}

    def _tp(probs, cur_q, label, desc):
        if not probs: return
        sp=sorted(probs.items(),key=lambda x:x[1],reverse=True); top_q,top_p=sp[0]
        st.markdown(f'''
<div style="background:#1F2B3D;border-radius:6px;padding:10px;margin-bottom:8px;">
  <div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;">{label} — {desc}</div>
  <div style="font-size:12px;color:#E8ECF0;margin-top:4px;">Currently: <b>{cur_q}</b></div>
  <div style="font-size:11px;color:#6B7280;">Most likely → <b style="color:{qc(top_q)};">{top_q}</b> ({top_p:.0%})</div>
</div>''', unsafe_allow_html=True)
        st.plotly_chart(prob_bar(probs), use_container_width=True, config={"displayModeBar":False})
        if top_q!=cur_q:
            st.markdown(f'<div style="font-size:11px;color:#6366F1;margin-top:4px;">If {top_q}: <b>{QWINS.get(top_q,"")}</b></div>',unsafe_allow_html=True)

    sq_q2p=_safe_float((gip.structural_probs or {}).get("Q2",0)) or 0
    sq_desc=qnc(sq)+(f" · Q2↑ {sq_q2p:.0%}" if sq=="Q3" and sq_q2p>0.25 else "")
    tp1,tp2,tp3=st.columns(3)
    with tp1: _tp(gip.structural_probs,sq,"STRUCTURAL",sq_desc)
    with tp2: _tp(gip.monthly_probs,mq,"MONTHLY",qnc(mq))
    with tp3:
        gprobs=global_.get("global_probs",{}) if global_ else {}
        if gprobs: _tp(gprobs,global_.get("dominant_quad",gq),"GLOBAL","50 Countries")

    st.markdown("---")
    st.markdown("### ⏱ Regime Timing")
    st.markdown(_sequence_pills(sq,mq),unsafe_allow_html=True)
    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}.get(fw,"#374151")
        fwi={"now":"🚨","1-2w":"⚡","3-6w":"👀","not yet":"🛑"}.get(fw,"🛑")
        st.markdown(f'<div style="background:{fwc}20;border-left:4px solid {fwc};border-radius:4px;padding:10px;margin:8px 0;"><div style="font-size:12px;color:{fwc};font-weight:700;">{fwi} FRONT-RUN: {fw.upper()}</div><div style="font-size:11px;color:#E8ECF0;margin-top:4px;">{fr}</div></div>',unsafe_allow_html=True)
        ew=getattr(transition,"early_warning_signals",{})
        if ew:
            st.markdown("#### Early Warning Signals")
            ew_rows=[{"Signal":k.replace("_"," ").title(),"Firing":"✅" if v>=0.5 else "⬜","Score":f"{v:.0f}"} for k,v in sorted(ew.items(),key=lambda x:x[1],reverse=True)]
            st.dataframe(pd.DataFrame(ew_rows),hide_index=True,use_container_width=True,height=280)
            fc=sum(1 for v in ew.values() if v>=0.5)
            st.progress(fc/max(len(ew),1),text=f"Early warning: {fc}/{len(ew)} firing")

    if analogs and analogs.get("top_analogs"):
        st.markdown("---"); st.markdown("### 📚 Historical Analogs")
        st.caption(analogs.get("composite_note",""))
        for i,a in enumerate(analogs["top_analogs"]):
            with st.expander(f"**{a['label']}** — {a.get('similarity',0):.0%}",expanded=(i==0)):
                cc2=st.columns(3)
                cc2[0].markdown(f"**1M:** {a.get('path_1m','')}")
                cc2[1].markdown(f"**3M:** {a.get('path_3m','')}")
                cc2[2].markdown(f"**6M:** {a.get('path_6m','')}")
                st.markdown(f"**Next bias:** {a.get('next_bias','')}")

# ══════════════════════════════════════════════════════════════════════════════
# 🎯 RISK RANGES™
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Risk Ranges™":
    st.markdown("# 🎯 Risk Range™ — TRADE · TREND · TAIL")
    st.caption("**LRR** = buy zone. **TRR** = trim zone. TREND break = exit. Includes options overlay for key tickers.")
    ar=rr.get("asset_ranges",{})
    if not ar: st.warning("No risk range data. Click 🔄 Refresh."); st.stop()

    all_a=sorted([(s,a) for s,v in ar.items() for a in v.get("alerts",[])],
                 key=lambda x:{"CRITICAL":0,"HIGH":1,"MEDIUM":2}.get(x[1].get("priority"),3))
    if all_a:
        st.markdown("### 🔔 Live Alerts")
        for sym,a in all_a[:20]:
            ic="🔴" if a["priority"]=="CRITICAL" else "🟡" if a["priority"]=="HIGH" else "🔵"
            bdr="#EF4444" if a["priority"]=="CRITICAL" else "#F59E0B"
            st.markdown(f'<div style="border-left:3px solid {bdr};padding-left:8px;margin:4px 0;"><div style="font-size:12px;">{ic} <b>[{sym}]</b> {a["action"]} {a["duration"]} — {a.get("note","")}</div></div>',unsafe_allow_html=True)

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
                     "TRADE":v.get("composite","—").upper(),"Quality":v.get("quality","—"),
                     "Stretch":tr.get("stretch","—"),"Hurst":ff(_safe_float(v.get("trend",{}).get("hurst"))),
                     "Market":v.get("market","—"),"Trap":"⚠️" if v.get("regime_trap") else ""})
    if rows:
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True,height=480)
        if show_opt and rows:
            st.markdown("### 📊 Options Overlay (top 5 by signal)")
            from engines.options_engine import OptionsEngine
            opt_eng = OptionsEngine()
            top_tickers = [r["Ticker"] for r in rows if r["TRADE"]=="BULLISH"][:5]
            for sym in top_tickers:
                v = ar.get(sym,{}); tr = v.get("trade",{})
                px = _safe_float(v.get("px")) or 0
                if px > 0:
                    st.markdown(f"**{sym}**")
                    opt = opt_eng.analyze(sym, px, _safe_float(tr.get("lrr")), _safe_float(tr.get("trr")), v.get("composite","neutral"))
                    _render_options_card(opt, v.get("composite","neutral"))
    else:
        st.info("No data matches filter. Click 🔄 Refresh to load all tickers.")

# ══════════════════════════════════════════════════════════════════════════════
# ⚡ ALPHA CENTER — Front-Run + Bottleneck + Options (MERGED)
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Alpha Center":
    st.markdown("# ⚡ Alpha Center — Front-Run · Bottleneck · Options")
    st.caption("Hedgeye: Front-run the Machine. Buy the best EV+ setups near LRR with options confirmation. No near-target entries.")

    # Timing signal
    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}.get(fw,"#374151")
        fwi={"now":"🚨","1-2w":"⚡","3-6w":"👀","not yet":"🛑"}.get(fw,"🛑")
        st.markdown(f'<div style="background:{fwc}20;border-left:4px solid {fwc};border-radius:4px;padding:10px;margin:8px 0;"><div style="font-size:12px;color:{fwc};font-weight:700;">{fwi} FRONT-RUN WINDOW: {fw.upper()}</div><div style="font-size:11px;color:#E8ECF0;margin-top:4px;">{fr}</div></div>',unsafe_allow_html=True)
    st.markdown(_sequence_pills(sq,mq),unsafe_allow_html=True)

    if not btk:
        st.warning("No bottleneck data. Click 🔄 Refresh.")
        st.stop()

    # Load options engine
    from engines.options_engine import OptionsEngine
    opt_eng = OptionsEngine()
    ar = rr.get("asset_ranges",{})

    # Filter: only high-constraint items (exclude low-constraint staples/agri)
    MIN_CONSTRAINT = 0.65 # Hedgeye-quality bottleneck threshold
    from config.settings import BOTTLENECK_PROFILES

    def _filter_btk(items):
        """Remove low-constraint / agri-staples items that don't belong in Alpha Center."""
        filtered = []
        for item in (items or []):
            sector = item.get("sector","generic")
            profile = BOTTLENECK_PROFILES.get(sector,{})
            constraint = profile.get("constraint", item.get("constraint",0.5))
            # Skip agri/low-constraint staples
            if sector in ("staples",) and constraint < 0.70: continue
            # Skip if near target (stretch = overbought/extended)
            v = ar.get(item.get("ticker",""),{}); tr = v.get("trade",{})
            stretch = tr.get("stretch","")
            if stretch in ("overbought","extended") and item.get("direction","long")=="long": continue
            filtered.append(item)
        return filtered

    l1_filtered = _filter_btk(btk.get("level_1",[]))
    l2_filtered = _filter_btk(btk.get("level_2",[]))

    # Stats
    s1,s2,s3,s4=st.columns(4)
    s1.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:10px;text-align:center;font-size:11px;">Level 1 (High EV)<br/><b>{len(l1_filtered)}</b></div>',unsafe_allow_html=True)
    s2.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:10px;text-align:center;font-size:11px;">Level 2 (Building)<br/><b>{len(l2_filtered)}</b></div>',unsafe_allow_html=True)
    s3.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:10px;text-align:center;font-size:11px;">Watch (Brewing)<br/><b>{len(btk.get("watch",[]))}</b></div>',unsafe_allow_html=True)
    s4.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:10px;text-align:center;font-size:11px;">Avoid (Trap)<br/><b>{len(btk.get("avoid",[]))}</b></div>',unsafe_allow_html=True)

    st.markdown("---")

    # Level 1 — ACT NOW
    st.markdown("### ⚡ Level 1 — Act Now (Highest EV)")
    st.caption("Structural bottleneck + Bullish TREND + near LRR + options confirmation. These are the trades.")
    if not l1_filtered:
        st.info("No Level 1 setups after quality filter. Wait for better setups.")
    else:
        l1_tickers = [item["ticker"] for item in l1_filtered[:8]]
        opt_results = opt_eng.batch_analyze(l1_tickers, ar)
        for i,item in enumerate(l1_filtered[:8]):
            v = ar.get(item["ticker"],{}); tr = v.get("trade",{})
            _render_alpha_card(item, opt_results.get(item["ticker"],{}), v, tr, i)

    st.markdown("---")

    # Level 2 — Building
    with st.expander(f"📈 Level 2 — Building ({len(l2_filtered)})", expanded=False):
        if not l2_filtered:
            st.info("No Level 2 setups.")
        else:
            l2_tickers = [item["ticker"] for item in l2_filtered[:6]]
            opt_results_2 = opt_eng.batch_analyze(l2_tickers, ar)
            for i,item in enumerate(l2_filtered[:6]):
                v = ar.get(item["ticker"],{}); tr = v.get("trade",{})
                _render_alpha_card(item, opt_results_2.get(item["ticker"],{}), v, tr, i)

    # Watch — Brewing
    watch_filtered = [w for w in (btk.get("watch",[]) or []) if w.get("direction")!="long" or ar.get(w.get("ticker",""),{}).get("trade",{}).get("stretch","") not in ("overbought","extended")]
    with st.expander(f"👀 Watch — Brewing ({len(watch_filtered)})", expanded=False):
        if not watch_filtered:
            st.info("Nothing brewing right now.")
        else:
            rows_w=[{"Ticker":w["ticker"],"Sector":w["sector"].replace("_"," ").title(),"Trend":w["trend"],
                     "EV":f'{w.get("ev",0):.2f}',"Score":f'{w.get("score",0):.2f}',"Thesis":w.get("known_thesis","")[:60]}
                    for w in watch_filtered[:20]]
            st.dataframe(pd.DataFrame(rows_w),hide_index=True,use_container_width=True,height=min(len(rows_w)*40+50,500))

    # Avoid
    with st.expander(f"🚫 Avoid — Regime Trap ({len(btk.get('avoid',[]))})", expanded=False):
        avoid_rows=[{"Ticker":a["ticker"],"Sector":a["sector"].replace("_"," ").title(),"Trend":a["trend"],"Score":f'{a.get("score",0):.2f}'} for a in (btk.get("avoid",[]) or [])[:20]]
        if avoid_rows: st.dataframe(pd.DataFrame(avoid_rows),hide_index=True,use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 📊 LEADERBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Leaderboard":
    st.markdown("# 📊 The Leaderboard — Signal Strength Stocks")
    st.caption("Quality A = Bullish TRADE+TREND near LRR + volume confirm. Min 1%, max 3%.")
    ar=rr.get("asset_ranges",{})
    if not ar: st.warning("No risk range data. Refresh."); st.stop()

    best_set=set(pb_data.get("best_assets",[])); worst_set=set(pb_data.get("worst_assets",[]))
    long_picks=[]; short_picks=[]
    for sym,v in ar.items():
        qual=v.get("quality","none"); comp=v.get("composite","neutral")
        tr=v.get("trade",{}); tn=v.get("trend",{})
        px=_safe_float(v.get("px")); vol_c=_safe_float(tr.get("volume_confirm")) or 0.5
        stretch=tr.get("stretch","neutral"); hurst=_safe_float(tn.get("hurst")) or 0.5
        from config.settings import TICKER_SECTOR
        sector=TICKER_SECTOR.get(sym,"generic")
        if qual in ("A","B") and comp=="bullish":
            lrr=_safe_float(tr.get("lrr")); trr=_safe_float(tr.get("trr"))
            nlrr=stretch in ("oversold","reset_zone")
            if px and lrr and trr and (trr-lrr)>1e-9:
                pos=(px-lrr)/(trr-lrr); nlrr=pos<=0.35 or nlrr
                # Skip if near target
                if stretch in ("overbought","extended"): continue
                rf=sym in best_set; ra=sym in worst_set
                sc=(50 if qual=="A" else 30)+(25 if nlrr else 0)+(15 if vol_c>0.6 else 0)+(10 if rf else 0)+(-20 if ra else 0)+(5 if hurst>0.5 else 0)
                long_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"stretch":stretch,"vol_c":vol_c,"hurst":hurst,"regime_fit":rf,"score":sc,"note":"Near LRR" if nlrr else f"Stretch: {stretch}","sector":sector})
        if qual in ("short_A","short_B") and comp=="bearish":
            lrr=_safe_float(tr.get("lrr")); trr=_safe_float(tr.get("trr"))
            ntrr=stretch in ("overbought","extended")
            if px and lrr and trr and (trr-lrr)>1e-9:
                pos=(px-lrr)/(trr-lrr); ntrr=pos>=0.65 or ntrr
                if stretch in ("oversold","reset_zone"): continue # Skip if near target
                rf=sym in worst_set
                sc=(50 if qual=="short_A" else 30)+(25 if ntrr else 0)+(15 if vol_c>0.6 else 0)+(10 if rf else 0)+(5 if hurst>0.5 else 0)
                short_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"stretch":stretch,"vol_c":vol_c,"hurst":hurst,"regime_fit":rf,"score":sc,"note":"Near TRR" if ntrr else f"Stretch: {stretch}","sector":sector})

    long_picks.sort(key=lambda x:-x["score"]); short_picks.sort(key=lambda x:-x["score"])

    s1,s2,s3,s4=st.columns(4)
    s1.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:10px;text-align:center;font-size:11px;">Bullish Names<br/><b>{len(long_picks)}</b></div>',unsafe_allow_html=True)
    s2.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:10px;text-align:center;font-size:11px;">Quality A Longs<br/><b>{sum(1 for p in long_picks if p["quality"]=="A")}</b></div>',unsafe_allow_html=True)
    s3.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:10px;text-align:center;font-size:11px;">Quality A Shorts<br/><b>{sum(1 for p in short_picks if p["quality"]=="short_A")}</b></div>',unsafe_allow_html=True)
    s4.markdown(f'<div style="background:#1F2B3D;border-radius:6px;padding:10px;text-align:center;font-size:11px;">Regime Traps<br/><b>{sum(1 for v in ar.values() if v.get("regime_trap"))}</b></div>',unsafe_allow_html=True)

    # Options on selected ticker
    st.markdown("---")
    opt_ticker = st.selectbox("Get options overlay for:", ["—"] + [p["ticker"] for p in long_picks[:15]])
    if opt_ticker != "—":
        v = ar.get(opt_ticker,{}); tr_d = v.get("trade",{})
        px = _safe_float(v.get("px")) or 0
        if px > 0:
            from engines.options_engine import OptionsEngine
            opt_r = OptionsEngine().analyze(opt_ticker, px, _safe_float(tr_d.get("lrr")), _safe_float(tr_d.get("trr")), v.get("composite","neutral"))
            _render_options_card(opt_r, v.get("composite","neutral"))

    st.markdown("---"); st.markdown("### 🟢 TOP 21 LONG IDEAS")
    for p in long_picks[:21]:
        st.markdown(f'''
<div style="background:#1F2B3D;border-radius:6px;padding:10px;margin:4px 0;">
  <div style="font-size:12px;font-weight:700;color:#10B981;">{p["ticker"]} ({p["quality"]}){"✅" if p["regime_fit"] else "⚠️"} Score {p["score"]:.0f} · {p["sector"].replace("_"," ").title()}</div>
  <div style="font-size:11px;color:#E8ECF0;margin-top:4px;">Px: {ff(p["px"])} · LRR: <b>{ff(p["lrr"])}</b> · TRR: {ff(p["trr"])} · {p["note"]}</div>
  <div style="font-size:10px;color:#6B7280;">Vol: {fp(p["vol_c"])} · Hurst: {ff(p["hurst"])}</div>
</div>''', unsafe_allow_html=True)
    if not long_picks: st.info("No Quality A/B longs near LRR. Market extended — wait for pullback.")

    st.markdown("---"); st.markdown("### 🔴 SHORT IDEAS")
    for p in short_picks[:15]:
        st.markdown(f'''
<div style="background:#1F2B3D;border-radius:6px;padding:10px;margin:4px 0;">
  <div style="font-size:12px;font-weight:700;color:#EF4444;">{p["ticker"]} ({p["quality"]}){"✅" if p["regime_fit"] else "⚠️"} Score {p["score"]:.0f} · {p["sector"].replace("_"," ").title()}</div>
  <div style="font-size:11px;color:#E8ECF0;margin-top:4px;">Px: {ff(p["px"])} · TRR: <b>{ff(p["trr"])}</b> · LRR: {ff(p["lrr"])} · {p["note"]}</div>
  <div style="font-size:10px;color:#6B7280;">Vol: {fp(p["vol_c"])} · Hurst: {ff(p["hurst"])}</div>
</div>''', unsafe_allow_html=True)
    if not short_picks: st.info("No Quality Short setups.")

    with st.expander("📋 Full Signal Table"):
        all_rows=([{"T":p["ticker"],"Side":"LONG","Q":p["quality"],"Sc":f'{p["score"]:.0f}',"Px":ff(p["px"]),"LRR":ff(p["lrr"]),"TRR":ff(p["trr"]),"Stretch":p["stretch"],"RF":"✅" if p["regime_fit"] else "—"} for p in long_picks]+
                  [{"T":p["ticker"],"Side":"SHORT","Q":p["quality"],"Sc":f'{p["score"]:.0f}',"Px":ff(p["px"]),"LRR":ff(p["lrr"]),"TRR":ff(p["trr"]),"Stretch":p["stretch"],"RF":"✅" if p["regime_fit"] else "—"} for p in short_picks])
        if all_rows: st.dataframe(pd.DataFrame(all_rows),hide_index=True,use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# 🌍 GLOBAL QUAD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌍 Global Quad":
    st.markdown("# 🌍 Global Quad — 50 Countries")
    st.caption("GIP applied to country ETFs. GDP-weighted.")
    if not global_: st.warning("No global data. Refresh."); st.stop()

    gconf=_safe_float(global_.get("global_conf")) or 0
    gprobs=global_.get("global_probs",{}) or {}
    c1,c2=st.columns([1,1.5])
    with c1:
        st.markdown(qcard("GLOBAL QUAD",gq,gconf,"50 Country ETFs"),unsafe_allow_html=True)
        if gprobs: st.plotly_chart(prob_bar(gprobs,"Global Probabilities"),use_container_width=True,config={"displayModeBar":False})
    with c2:
        st.markdown("### Country Heatmap")
        cq=global_.get("country_quads",{}) or {}
        heat=[]
        if cq:
            for country,data in cq.items():
                if isinstance(data,(list,tuple)) and len(data)>=3: etf,quad,conf=str(data[0]),str(data[1]),_safe_float(data[2]) or 0
                elif isinstance(data,dict): etf,quad,conf=str(data.get("etf","")),str(data.get("quad","")),_safe_float(data.get("conf",0)) or 0
                else: continue
                if quad: heat.append({"Country":country,"ETF":etf,"Quad":quad,"Conf":f"{conf:.0%}"})
        if heat:
            df=pd.DataFrame(heat)
            st.dataframe(df.style.map(lambda v:f"color:{QC.get(v,'#9CA3AF')}",subset=["Quad"]),
                         hide_index=True,height=400,use_container_width=True)
        else:
            st.info("Country Quad data belum tersedia. Click 🔄 Refresh untuk load country ETFs. Pastikan GlobalQuadEngine berjalan di orchestrator.")

    st.markdown("---"); st.markdown("### 🌏 EM Recovery Signal")
    em_sig=(btk.get("em_recovery",{}) or {}) if btk else {}
    if em_sig:
        conf=_safe_float(em_sig.get("confidence")) or 0
        ec="#10B981" if conf>0.6 else "#F59E0B" if conf>0.4 else "#6B7280"
        st.markdown(f'''
<div style="background:{ec}20;border-left:4px solid {ec};border-radius:4px;padding:10px;">
  <div style="font-size:12px;color:{ec};font-weight:700;">{em_sig.get("trigger","")}</div>
  <div style="font-size:11px;color:#E8ECF0;margin-top:4px;">{em_sig.get("rationale","")}</div>
  <div style="font-size:10px;color:#6B7280;margin-top:4px;">Confidence: {conf:.0%} · Best: {", ".join(em_sig.get("best",[])[:6])}</div>
</div>''', unsafe_allow_html=True)
    else: st.info("EM recovery signal belum tersedia.")

# ══════════════════════════════════════════════════════════════════════════════
# 🇮🇩 IHSG
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🇮🇩 IHSG":
    st.markdown("# 🇮🇩 IHSG — Indonesia Market")
    st.caption("Local signal + sector thesis. No options data (IHSG options market tidak liquid).")
    from config.settings import IHSG_UNIVERSE, IHSG_BUCKETS
    ar=rr.get("asset_ranges",{}); ihsg={sym:v for sym,v in ar.items() if v.get("market","")=="ihsg"}

    if ihsg:
        rows=[{"Ticker":sym,"Px":ff(_safe_float(v.get("px")),0),
               "LRR":ff(_safe_float(v.get("trade",{}).get("lrr")),0),
               "TRR":ff(_safe_float(v.get("trade",{}).get("trr")),0),
               "Signal":v.get("composite","—").upper(),"Quality":v.get("quality","—"),
               "Stretch":v.get("trade",{}).get("stretch","—"),
               "Trap":"⚠️" if v.get("regime_trap") else ""} for sym,v in ihsg.items()]
        st.dataframe(pd.DataFrame(rows),hide_index=True,use_container_width=True)
    else:
        st.info("IHSG data belum tersedia. Enable IHSG dan click 🔄 Refresh.")

    st.markdown("---"); st.markdown("### 🏦 Sector Buckets")
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

# ══════════════════════════════════════════════════════════════════════════════
# 📖 NARRATIVES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📖 Narratives":
    st.markdown("# 📖 Narratives — Thematic Scoring")
    st.caption("Active = confirmed. Building = traction. Brewing = pre-consensus.")
    if not narr:
        st.warning("Narrative data kosong. Kemungkinan NarrativeEngine gagal load atau snapshot belum direfresh.")
        st.info("👉 Click **⚡ Force** untuk rebuild snapshot dengan NarrativeEngine.")
        st.stop()
    active=narr.get("active_narratives",[]) or []
    if not active:
        st.info("Narratives belum aktif. Click ⚡ Force untuk rebuild.")
    for n in sorted(active,key=lambda x:x.get("score",0),reverse=True):
        score=n.get("score",0); sc="#10B981" if score>0.6 else "#F59E0B" if score>0.4 else "#6B7280"
        with st.expander(f"**{n.get('name','')}** — {score:.0%}"):
            st.markdown(f"**Thesis:** {n.get('thesis','')}")
            st.markdown(f"**Tickers:** {' · '.join(n.get('tickers',[])[:8])}")
            inv=n.get("invalidators",[]); best=n.get("best",[]); worst=n.get("worst",[])
            if inv: st.markdown(f"**Invalidators:** {', '.join(inv[:3])}")
            if best: st.markdown(f"**Best:** {' · '.join(best[:10])}")
            if worst:st.markdown(f"**Worst:** {' · '.join(worst[:10])}")

# ══════════════════════════════════════════════════════════════════════════════
# 🔮 DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Discovery":
    st.markdown("# 🔮 Early Discovery — Pre-Consensus")
    st.caption("Autonomy engine: regime fit + price cluster + supply chain graph + news NLP.")
    cands=(auto_disc.get("candidates",[]) if auto_disc else [])+ (disc.get("discoveries",[]) if disc else [])
    if not cands:
        st.info("No discoveries yet. Click **⚡ Force** untuk rebuild dengan Autonomy Stack.")
        st.stop()
    for stage,sc in [("active","#10B981"),("building","#F59E0B"),("brewing","#6366F1")]:
        items=[c for c in cands if c.get("stage")==stage]
        if not items: continue
        st.markdown(f"### {stage.upper()} ({len(items)})")
        for c in items:
            conf=c.get("confidence",c.get("conviction",0)); pump=c.get("pump_risk",0)
            with st.expander(f"**{c.get('name','')}** — Conf: {conf:.0%} · Pump: {pump:.0%}"):
                st.markdown(f"**Thesis:** {c.get('thesis','')}")
                ben=c.get("beneficiary_tickers",[]); fade=c.get("fade_tickers",[])
                if ben: st.markdown(f"**Beneficiaries:** {' · '.join(ben[:8])}")
                if fade: st.markdown(f"**Fade:** {' · '.join(fade[:5])}")
                cs=c.get("confirmation_signal",""); inv=c.get("invalidators",[])
                if cs: st.markdown(f"**Confirmation:** {cs}")
                if inv: st.markdown(f"**Invalidators:** {', '.join(inv) if isinstance(inv,list) else inv}")

# ══════════════════════════════════════════════════════════════════════════════
# 🏥 HEALTH
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏥 Health":
    st.markdown("# 🏥 Market Health — VIX · Breadth · Crash Meter")
    if not health: st.warning("No health data. Refresh."); st.stop()
    vb_d=health.get("vix_bucket",{}); vb_b=vb_d.get("bucket","—")
    vb_c={"Investable":"#10B981","Chop":"#F59E0B","Defensive":"#EF4444"}.get(vb_b,"#6B7280")
    st.markdown(f'<div style="background:{vb_c}20;border-left:4px solid {vb_c};border-radius:4px;padding:10px;"><div style="font-size:14px;color:{vb_c};font-weight:700;">VIX BUCKET: {vb_b.upper()}</div><div style="font-size:11px;color:#E8ECF0;margin-top:4px;">{vb_d.get("note","")}</div></div>',unsafe_allow_html=True)

    crash=health.get("crash",{}) or {}
    if crash:
        st.markdown("### Crash Meter")
        for k,v in crash.get("signals",{}).items(): st.progress(float(v),text=f"{k.replace('_',' ').title()}: {v:.0%}")
        st.markdown(f"**State:** {crash.get('state','')} · Score: {_safe_float(crash.get('score',0)):.0%}")
        if crash.get("reasons"): st.markdown("**Reasons:** "+" · ".join(crash["reasons"]))

    breadth=health.get("market_health",{}) or {}
    if breadth:
        st.markdown("### Sector Breadth")
        b1,b2,b3,b4=st.columns(4)
        b1.metric("Score",f"{_safe_float(breadth.get('score')) or 0:.2f}")
        b2.metric("Verdict",breadth.get("verdict","—"))
        b3.metric("Sector Support",f"{breadth.get('positive_sectors_1m',0)}/{breadth.get('total_buckets',0)}")
        b4.metric("EqW Health",f"{_safe_float(breadth.get('eqw_health')) or 0:.2f}")
        for note in (breadth.get("notes") or []): st.markdown(f"• {note}")

    fg=health.get("fear_greed",{}) or {}
    if fg:
        st.markdown("---"); st.markdown("### Fear & Greed")
        fgs=_safe_float(fg.get("score")) or 50
        fgc="#10B981" if fgs<25 else "#F59E0B" if fgs<55 else "#EF4444"
        st.markdown(f"**Score:** {fgs:.0f}/100 — {fg.get('label','Neutral')}",unsafe_allow_html=True)
        st.progress(fgs/100)

# ══════════════════════════════════════════════════════════════════════════════
# 📋 PLAYBOOK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Playbook":
    st.markdown("# 📋 Regime Playbook")
    st.caption(f"**{sq}** Structural · **{mq}** Monthly · Scenarios scored by data, not opinion.")

    if pb_data:
        st.markdown("### 🎯 Regime Positioning")
        col1,col2=st.columns(2)
        with col1:
            st.markdown(f'''
<div style="background:#064E3B20;border-left:4px solid #10B981;border-radius:4px;padding:10px;">
  <div style="font-size:12px;color:#10B981;font-weight:700;">✅ LONG — {sq}</div>
  <div style="font-size:11px;color:#E8ECF0;margin-top:4px;">{" · ".join(pb_data.get("best_assets",[]))}</div>
  <div style="font-size:10px;color:#6B7280;margin-top:6px;">Style: {pb_data.get("style","")}</div>
  <div style="font-size:10px;color:#6B7280;">FX: {pb_data.get("fx","")}</div>
  <div style="font-size:10px;color:#6B7280;">Bonds: {pb_data.get("bonds","")}</div>
  {('<div style="font-size:10px;color:#F59E0B;margin-top:4px;">Monthly adds: ' + " · ".join(pb_data.get("monthly_adds",[])) + '</div>') if pb_data.get("monthly_adds") else ""}
</div>''', unsafe_allow_html=True)
        with col2:
            st.markdown(f'''
<div style="background:#450A0A20;border-left:4px solid #EF4444;border-radius:4px;padding:10px;">
  <div style="font-size:12px;color:#EF4444;font-weight:700;">❌ AVOID — {sq}</div>
  <div style="font-size:11px;color:#E8ECF0;margin-top:4px;">{" · ".join(pb_data.get("worst_assets",[]))}</div>
  <div style="font-size:10px;color:#6B7280;margin-top:6px;">Hedge: {pb_data.get("hedge","BTAL")}</div>
  <div style="font-size:10px;color:#6B7280;">{pb_data.get("sizing_note","Min 1% · Max 3%")}</div>
</div>''', unsafe_allow_html=True)

        # Bitcoin
        btc_rr=rr.get("asset_ranges",{}).get("IBIT",rr.get("asset_ranges",{}).get("BTC-USD",{}))
        btc_sig=btc_rr.get("composite","—")
        btc_c="#10B981" if btc_sig=="bullish" else "#EF4444" if btc_sig=="bearish" else "#6B7280"
        btc_corr_val=dxy_corr.get("Bitcoin","—")
        q4_note=" (Q4 EXCEPTION — Exit BTC)" if sq=="Q4" else ""
        st.markdown(f'''
<div style="background:#1F2B3D;border-radius:6px;padding:10px;margin-top:10px;">
  <div style="font-size:12px;color:{btc_c};font-weight:700;">₿ BITCOIN (IBIT): {btc_sig.upper()}{q4_note} — DXY/BTC 15D corr: {btc_corr_val} · "Any quad other than Q4 = biggest digital asset position."</div>
</div>''', unsafe_allow_html=True)

        # Scenarios
        scenarios_list=scen.get("scenarios",[]) if scen else []
        if scenarios_list:
            st.markdown("---"); st.markdown("### 🔮 Scenario Probability Map")
            badges=["🎯 BASE","🔄 ALT","⚠️ RISK","📌 TAIL"]; badge_colors=["#10B981","#F59E0B","#EF4444","#6366F1"]
            row1=st.columns(2); row2=st.columns(2); grids=[row1[0],row1[1],row2[0],row2[1]]
            for i,(sc_item,col) in enumerate(zip(scenarios_list[:4],grids)):
                pc=badge_colors[i]; em=sc_item.em_note[:60]+"..." if len(sc_item.em_note)>60 else sc_item.em_note
                with col:
                    st.markdown(f'''
<div style="background:{pc}15;border-left:4px solid {pc};border-radius:4px;padding:10px;margin:4px 0;">
  <div style="font-size:11px;color:{pc};font-weight:700;">{badges[i]} P={sc_item.probability:.0%} · Conf={sc_item.confirmation_score:.0%}</div>
  <div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{sc_item.name}</div>
  <div style="font-size:11px;color:#9CA3AF;margin-top:2px;">{sc_item.headline}</div>
  <div style="font-size:10px;color:#6B7280;margin-top:4px;">Best: {" · ".join(sc_item.best_assets[:4])}</div>
  <div style="font-size:10px;color:#6B7280;">Avoid: {" · ".join(sc_item.worst_assets[:4])}</div>
  <div style="font-size:10px;color:#6366F1;margin-top:4px;">🌍 {em}</div>
</div>''', unsafe_allow_html=True)

            bc=scen.get("base_case") if scen else None
            if bc and hasattr(bc,"confirmation_triggers"):
                st.markdown("---"); ct,ci=st.columns(2)
                with ct:
                    st.markdown(f"### ✅ Confirmation Triggers ({bc.name})")
                    for t in getattr(bc,"confirmation_triggers",[]): st.markdown(f"• {t}")
                with ci:
                    st.markdown("### ❌ Invalidators")
                    for inv in getattr(bc,"invalidators",[]): st.markdown(f"• {inv}")

        if gip:
            st.markdown("---"); st.markdown("### 📡 GIP Feature Data")
            f=gip.features
            rows=[["Growth Momentum",fp(f.get("growth_momentum")),"↑" if (_safe_float(f.get("growth_momentum")) or 0)>0 else "↓"],
                  ["Inflation Momentum",fp(f.get("inflation_momentum")),"↑" if (_safe_float(f.get("inflation_momentum")) or 0)>0 else "↓"],
                  ["Policy Score",fp(f.get("policy_score")),""],
                  ["Leading Indicator",fp(f.get("leading_indicator_composite")),""],
                  ["Data Coverage",fp(f.get("data_coverage")),""],
                  ["Flip Hazard",f"{gip.flip_hazard:.0%}",""],
                  ["Structural Conf",f"{gip.structural_conf:.0%}",""],
                  ["Monthly Conf",f"{gip.monthly_conf:.0%}",""]]
            st.dataframe(pd.DataFrame(rows,columns=["Signal","Value","Dir"]),hide_index=True,use_container_width=True)