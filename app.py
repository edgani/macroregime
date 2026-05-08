"""app.py — MacroRegime Pro v16 | Hedgeye-Style Dashboard
Enhancements v16:
- Tab struktur → Hedgeye-style: Dashboard / GIP Model / Risk Ranges™ / ETF Pro / Leaderboard / Global Quad
- Dashboard: Gamma Regime + Leveraged ETF Flow panels (computed, zero hardcode)
- Sequencing pills: Q3→Q2→Q1 dari actual sq/mq state
- Monthly label: dynamic dari QN dict, bukan "Weather" hardcode
- Structural: dual-label kalau Q2 prob >25%
- Paper Trade engine: REMOVED
- ETF Pro tab: kombinasi US/FX/Commodity/Crypto dengan Quad-aware positioning
- Leaderboard: Hedgeye "Top 21 Long Ideas" format
- Playbook tab: renamed dari Scenarios, content enriched
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

st.set_page_config(page_title="MacroRegime Pro", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
.vix-investable {background:linear-gradient(90deg,#064e3b,#065f46);border-left:6px solid #10B981;padding:16px;border-radius:8px;}
.vix-chop       {background:linear-gradient(90deg,#451a03,#78350f);border-left:6px solid #F59E0B;padding:16px;border-radius:8px;}
.vix-defensive  {background:linear-gradient(90deg,#450a0a,#7f1d1d);border-left:6px solid #EF4444;padding:16px;border-radius:8px;}
.winrate-card   {background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;}
.signal-A       {background:linear-gradient(90deg,#064e3b,#065f46);border-left:4px solid #10B981;padding:12px;border-radius:6px;margin-bottom:8px;}
.signal-shortA  {background:linear-gradient(90deg,#450a0a,#7f1d1d);border-left:4px solid #EF4444;padding:12px;border-radius:6px;margin-bottom:8px;}
.gamma-deep-pos {background:#052e16;border-left:4px solid #16a34a;padding:14px;border-radius:8px;margin-bottom:10px;}
.gamma-pos      {background:#064e3b;border-left:4px solid #059669;padding:14px;border-radius:8px;margin-bottom:10px;}
.gamma-trans    {background:#451a03;border-left:4px solid #d97706;padding:14px;border-radius:8px;margin-bottom:10px;}
.gamma-neg      {background:#450a0a;border-left:4px solid #dc2626;padding:14px;border-radius:8px;margin-bottom:10px;}
.gamma-deep-neg {background:#3b0000;border-left:4px solid #b91c1c;padding:14px;border-radius:8px;margin-bottom:10px;}
.lev-panel      {background:#1e1b4b;border-left:4px solid #7c3aed;padding:14px;border-radius:8px;margin-bottom:10px;}
.seq-row        {display:flex;align-items:center;gap:8px;padding:10px;background:#111827;border-radius:6px;flex-wrap:wrap;margin-top:8px;margin-bottom:10px;}
.etf-long-card  {background:#052e16;border:1px solid #16a34a;border-radius:6px;padding:10px;margin-bottom:6px;}
.etf-short-card {background:#3b0000;border:1px solid #dc2626;border-radius:6px;padding:10px;margin-bottom:6px;}
</style>""", unsafe_allow_html=True)

# ── Color / Name Maps ─────────────────────────────────────────────────────────
QC = {"Q1":"#00D4AA","Q2":"#F59E0B","Q3":"#EF4444","Q4":"#6366F1"}
QN = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}
# Hedgeye Climate vs Weather labeling
QN_CLIMATE = {"Q1":"Goldilocks (Growth↑ Infl↓)","Q2":"Reflation (Growth↑ Infl↑)",
               "Q3":"Stagflation (Growth↓ Infl↑)","Q4":"Deflation (Growth↓ Infl↓)"}
SC = {"bullish":"#10B981","bearish":"#EF4444","neutral":"#6B7280","mixed":"#F59E0B"}

def qc(q): return QC.get(q,"#9CA3AF")
def qn(q): return QN.get(q,q)
def fp(v):
    try: return f"{v:.1%}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"
def ff(v, d=3):
    try: return f"{v:.{d}f}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"

def qcard(label, q, conf, sub):
    c = qc(q)
    return f'''<div style="background:#111827;border:1px solid {c}44;border-radius:8px;padding:14px;text-align:center;">
    <div style="font-size:10px;color:#9CA3AF;margin-bottom:4px;">{label}</div>
    <div style="font-size:28px;font-weight:800;color:{c};">{q}</div>
    <div style="font-size:12px;color:{c};margin-top:2px;">{QN.get(q,"")}</div>
    <div style="font-size:11px;color:#9CA3AF;margin-top:6px;">Conf: {conf:.0%} · {sub}</div>
    </div>'''

# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS — Dashboard panels (zero hardcode)
# ══════════════════════════════════════════════════════════════════════════════

def _render_gamma_panel(gamma: dict) -> str:
    if not gamma or not gamma.get("ok"):
        note = (gamma or {}).get("note","Engine belum jalan — tambahkan GammaRegimeEngine ke orchestrator step 14e.")
        return f'<div class="gamma-trans"><b style="color:#F59E0B;">⚡ GAMMA REGIME — Tier 1 Alpha Approx</b><div style="font-size:11px;color:#9CA3AF;margin-top:6px;">{note}</div></div>'
    throttle  = gamma.get("throttle") or 0
    rvol_10   = gamma.get("rvol_10d")
    rvol_21   = gamma.get("rvol_21d")
    vix       = gamma.get("vix")
    vprem     = gamma.get("vol_premium")
    bar_pct   = gamma.get("bar_pct") or 50
    color     = gamma.get("color","#9CA3AF")
    label     = gamma.get("label","Unknown")
    action    = gamma.get("action","—")
    impl      = gamma.get("impl","")
    regime    = gamma.get("regime","UNKNOWN")
    direction = gamma.get("throttle_direction","—")
    css = {"DEEP_POSITIVE":"gamma-deep-pos","POSITIVE":"gamma-pos","TRANSITION":"gamma-trans",
           "NEGATIVE":"gamma-neg","DEEP_NEGATIVE":"gamma-deep-neg"}.get(regime,"gamma-trans")
    def _f(v,fmt=".1f",s=""): return f"{v:{fmt}}{s}" if v is not None else "—"
    vpc = "#10B981" if (vprem or 0)>0 else "#EF4444"
    pos_w = max(0,min(100,bar_pct-43))
    return f'''<div class="{css}">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <span style="font-size:13px;font-weight:700;color:{color};">⚡ GAMMA REGIME — Tier 1 Alpha Approx</span>
        <div style="display:flex;gap:6px;align-items:center;">
          <div style="background:{color};color:#000;font-size:11px;font-weight:700;padding:3px 10px;border-radius:4px;">{label.upper()}</div>
          <span style="font-size:10px;color:#6B7280;">{direction}</span>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:10px;">
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Throttle (approx)</div>
          <div style="font-size:20px;font-weight:800;color:{color};">{_f(throttle,"+.1f")}</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">rVol 10d (ann.)</div>
          <div style="font-size:18px;font-weight:700;color:#E8ECF0;">{_f(rvol_10,".1f","%")}</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">rVol 21d</div>
          <div style="font-size:18px;font-weight:700;color:#E8ECF0;">{_f(rvol_21,".1f","%")}</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">VIX (implied)</div>
          <div style="font-size:18px;font-weight:700;color:#E8ECF0;">{_f(vix,".1f")}</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Vol Premium</div>
          <div style="font-size:18px;font-weight:700;color:{vpc};">{_f(vprem,"+.1f","%")}</div>
        </div>
      </div>
      <div style="display:flex;height:8px;border-radius:4px;overflow:hidden;margin-bottom:4px;">
        <div style="width:14%;background:#b91c1c;border-radius:3px 0 0 3px;"></div>
        <div style="width:15%;background:#dc2626;"></div>
        <div style="width:14%;background:#d97706;"></div>
        <div style="width:{100-pos_w}%;background:#1f2937;"></div>
        <div style="width:{pos_w}%;background:#10B981;border-radius:0 3px 3px 0;"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:9px;color:#4B5563;margin-bottom:6px;">
        <span>−105 DEEP NEG</span><span>0 TRANSITION</span><span>+35 DEEP POS</span>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div style="font-size:11px;color:#9CA3AF;flex:1;">{impl}</div>
        <div style="background:#111827;padding:4px 12px;border-radius:4px;margin-left:10px;">
          <span style="font-size:13px;font-weight:800;color:{color};">{action}</span>
        </div>
      </div>
      <div style="font-size:9px;color:#4B5563;margin-top:4px;">Computed dari rVol(SPY)+VIX. Tier 1 Alpha throttle = proprietary.</div>
    </div>'''


def _render_lev_etf_panel(lev: dict) -> str:
    if not lev or not lev.get("ok"):
        note = (lev or {}).get("note","Engine belum jalan — tambahkan LeveragedETFEngine ke orchestrator step 14f.")
        return f'<div class="lev-panel"><b style="color:#a78bfa;">📊 LEVERAGED ETF FLOW</b><div style="font-size:11px;color:#9CA3AF;margin-top:6px;">{note}</div></div>'
    total    = lev.get("total_mcap_b")
    long_b   = lev.get("long_exposure_b")
    short_b  = lev.get("short_exposure_b")
    single_b = lev.get("single_crypto_b")
    long_pct = lev.get("long_pct") or 0
    short_pct= lev.get("short_pct") or 0
    other_pct= max(0, round(100-long_pct-short_pct,1))
    is_ath   = lev.get("is_ath",False)
    rebal    = lev.get("rebalancing_pressure","—")
    top_l    = lev.get("top_longs",[])
    top_s    = lev.get("top_shorts",[])
    def _b(v): return f"${v}B" if v is not None else "—"
    rc = {"HIGH":"#EF4444","MEDIUM":"#F59E0B","LOW":"#10B981"}.get(rebal,"#6B7280")
    ath = '<span style="background:#dc2626;color:#fff;font-size:10px;font-weight:700;padding:2px 7px;border-radius:3px;margin-left:6px;">ATH</span>' if is_ath else ""
    tls = " · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in top_l[:3]) or "—"
    tss = " · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in top_s[:3]) or "—"
    return f'''<div class="lev-panel">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <span style="font-size:13px;font-weight:700;color:#a78bfa;">📊 LEVERAGED ETF FLOW{ath}</span>
        <span style="background:{rc}33;color:{rc};font-size:11px;padding:3px 10px;border-radius:4px;">Rebal Pressure: {rebal}</span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px;">
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Total AUM</div>
          <div style="font-size:20px;font-weight:800;color:#E8ECF0;">{_b(total)}</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Long Exposure</div>
          <div style="font-size:20px;font-weight:800;color:#10B981;">{_b(long_b)}</div>
          <div style="font-size:9px;color:#6B7280;">{long_pct}%</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Short Exposure</div>
          <div style="font-size:20px;font-weight:800;color:#EF4444;">{_b(short_b)}</div>
          <div style="font-size:9px;color:#6B7280;">{short_pct}%</div>
        </div>
        <div style="background:#111827;border-radius:6px;padding:8px;text-align:center;">
          <div style="font-size:9px;color:#6B7280;margin-bottom:2px;">Single/Crypto</div>
          <div style="font-size:20px;font-weight:800;color:#F59E0B;">{_b(single_b)}</div>
        </div>
      </div>
      <div style="display:flex;height:7px;border-radius:4px;overflow:hidden;margin-bottom:5px;gap:1px;">
        <div style="width:{long_pct}%;background:#10B981;border-radius:3px 0 0 3px;"></div>
        <div style="width:{short_pct}%;background:#EF4444;"></div>
        <div style="width:{other_pct}%;background:#F59E0B;border-radius:0 3px 3px 0;"></div>
      </div>
      <div style="font-size:10px;color:#9CA3AF;">
        Top Longs: {tls}<br>Top Shorts: {tss}<br>
        <span style="color:#4B5563;">yfinance totalAssets · Cache 6h · {lev.get("long_etf_count",0)}L + {lev.get("short_etf_count",0)}S ETFs</span>
      </div>
    </div>'''


def _build_sequence_pills(sq: str, mq: str, QC: dict) -> str:
    sqc = QC.get(sq,"#6B7280"); mqc = QC.get(mq,"#6B7280")
    pill = "padding:3px 11px;border-radius:4px;font-weight:700;font-size:12px;"
    arr  = '<span style="color:#6B7280;font-size:18px;">→</span>'
    if sq == mq:
        return f'<div class="seq-row"><span style="color:#9CA3AF;font-size:12px;">Regime:</span><span style="background:{sqc};color:#000;{pill}">{sq} CONFIRMED</span><span style="color:#9CA3AF;font-size:11px;margin-left:4px;">Structural & Monthly aligned — high conviction stay</span></div>'
    if sq=="Q3" and mq=="Q2":
        return f'<div class="seq-row"><span style="color:#9CA3AF;font-size:12px;">Sequencing:</span><span style="background:#dc2626;color:#fff;{pill}">{sq} STRUCT</span>{arr}<span style="background:{mqc};color:#000;{pill}">{mq} MONTHLY NOW</span>{arr}<span style="background:#14532d;color:#4ade80;{pill}border:1px solid #16a34a;">Q1 TARGET</span><span style="color:#4B5563;font-size:10px;margin-left:4px;">~6wk · watch CPI -50bps</span></div>'
    return f'<div class="seq-row"><span style="color:#9CA3AF;font-size:12px;">Struct:</span><span style="background:{sqc};color:#000;{pill}">{sq}</span>{arr}<span style="color:#9CA3AF;font-size:12px;">Monthly:</span><span style="background:{mqc};color:#000;{pill}">{mq}</span><span style="color:#4B5563;font-size:10px;margin-left:4px;">Leading → lagging sequencing</span></div>'


# ── Session state ─────────────────────────────────────────────────────────────
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.markdown("*Hedgeye GIP · v16 · Autonomy*")
    st.divider()
    page = st.radio("", [
        "🏠 Dashboard",
        "📈 GIP Model",
        "🎯 Risk Ranges™",
        "⚡ ETF Pro",
        "📊 Leaderboard",
        "🌍 Global Quad",
        "🇮🇩 IHSG",
        "🔍 Bottleneck",
        "📖 Narratives",
        "🔮 Early Discovery",
        "🏥 Health",
        "📋 Playbook",
    ], label_visibility="collapsed")
    st.divider()
    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"📸 {snapshot_age_str()}")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Refresh", use_container_width=True): st.session_state.loading = True
    with c2:
        if st.button("⚡ Force", use_container_width=True):
            st.session_state.loading = True; st.session_state.snap = None
    with st.expander("⚙️ Universe"):
        inc_us   = st.checkbox("US Stocks", True)
        inc_fx   = st.checkbox("Forex", True)
        inc_comm = st.checkbox("Commodities", True)
        inc_cryp = st.checkbox("Crypto", True)
        inc_ihsg = st.checkbox("IHSG", True)
    st.divider()
    # Dynamic caption — no hardcode
    _snap_cap = st.session_state.snap
    if _snap_cap and _snap_cap.get("ok"):
        _g = _snap_cap.get("gip"); _gl = _snap_cap.get("global",{})
        _sq = _g.structural_quad if _g else "—"
        _mq = _g.monthly_quad if _g else "—"
        _gq = _gl.get("global_quad","—") if _gl else "—"
        st.caption(f"Hedgeye: {_sq} Struct · {_mq} Monthly · {_gq} Global")
    else:
        st.caption("Hedgeye: — Struct · — Monthly · — Global")

# ── Load / build snapshot ─────────────────────────────────────────────────────
snap = st.session_state.snap
if snap is None:
    snap = load_snapshot(max_age_hours=6.0)
    if snap and snap.get("ok"): st.session_state.snap = snap

if st.session_state.loading or snap is None:
    from orchestrator import build_snapshot
    pb = st.progress(0.0); pt = st.empty()
    def prog(m, f): pb.progress(f); pt.caption(m)
    snap = build_snapshot(progress_cb=prog, include_us_stocks=inc_us, include_forex=inc_fx,
                          include_commodities=inc_comm, include_crypto=inc_cryp, include_ihsg=inc_ihsg)
    st.session_state.snap = snap; st.session_state.loading = False
    pb.empty(); pt.empty(); st.rerun()

if not snap or not snap.get("ok"):
    st.error("❌ No snapshot. Click **🔄 Refresh** or **⚡ Force** to rebuild."); st.stop()

# ── Extract ───────────────────────────────────────────────────────────────────
gip        = snap.get("gip")
global_    = snap.get("global", {})
rr         = snap.get("risk_ranges", {})
scen       = snap.get("scenarios", {})
narr       = snap.get("narratives", {})
disc       = snap.get("discovery", {})
transition = snap.get("transition", None)
health     = snap.get("health", {})
analogs    = snap.get("analogs", {})
btk        = snap.get("bottleneck", {})
pb_data    = snap.get("playbook", {})
prices     = snap.get("prices", {})
stress     = snap.get("stress", {})
auto_disc  = snap.get("auto_discoveries", {})
fb_eval    = snap.get("feedback_eval", {})
gamma_data = snap.get("gamma", {})
lev_data   = snap.get("leveraged_etf", {})

sq = gip.structural_quad if gip else "Q3"
mq = gip.monthly_quad    if gip else "Q2"
gq = global_.get("global_quad", "Q3")


# ══════════════════════════════════════════════════════════════════════════════
# 🏠 DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown(f'<div style="font-size:11px;color:#6B7280;">Built {snap.get("build_time_s",0)}s · Prices: {snap.get("prices_loaded",0)} · FRED: {snap.get("fred_coverage",0)} · RR: {snap.get("price_frames_count",0)}</div>', unsafe_allow_html=True)
    st.markdown("# MacroRegime Pro — Dashboard")

    # ── VIX Bucket Banner ────────────────────────────────────────────────────
    vix_bucket_data = health.get("vix_bucket", {}) if health else {}
    vix_b    = vix_bucket_data.get("bucket", "—")
    vix_last = vix_bucket_data.get("vix_last", 0)
    vix_note = vix_bucket_data.get("note", "")
    vix_risk = vix_bucket_data.get("risk_mode", "—")
    if vix_b == "Investable":
        vix_html = f'<div class="vix-investable"><div style="font-size:20px;font-weight:800;color:#10B981;">🟢 INVESTABLE BUCKET</div><div style="font-size:13px;color:#A7F3D0;margin-top:4px;">VIX {vix_last:.1f} · {vix_note}</div><div style="font-size:11px;color:#6B7280;margin-top:4px;">Risk Mode: {vix_risk} — Buy dips when signal searah.</div></div>'
    elif vix_b == "Chop":
        vix_html = f'<div class="vix-chop"><div style="font-size:20px;font-weight:800;color:#F59E0B;">🟡 CHOP BUCKET</div><div style="font-size:13px;color:#FDE68A;margin-top:4px;">VIX {vix_last:.1f} · {vix_note}</div><div style="font-size:11px;color:#6B7280;margin-top:4px;">Risk Mode: {vix_risk} — Trade ranges, kurangi chase breakout.</div></div>'
    elif vix_b == "Defensive":
        vix_html = f'<div class="vix-defensive"><div style="font-size:20px;font-weight:800;color:#EF4444;">🔴 DEFENSIVE BUCKET</div><div style="font-size:13px;color:#FECACA;margin-top:4px;">VIX {vix_last:.1f} · {vix_note}</div><div style="font-size:11px;color:#6B7280;margin-top:4px;">Risk Mode: {vix_risk} — Capital preservation. Sizing jauh lebih kecil.</div></div>'
    else:
        vix_html = ""
    if vix_html:
        st.markdown(vix_html, unsafe_allow_html=True)
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── Gamma Regime (computed, zero hardcode) ────────────────────────────────
    st.markdown(_render_gamma_panel(gamma_data), unsafe_allow_html=True)

    # ── Leveraged ETF Flow (yfinance AUM, zero hardcode) ─────────────────────
    st.markdown(_render_lev_etf_panel(lev_data), unsafe_allow_html=True)

    # ── Quad Cards (dynamic labels) ───────────────────────────────────────────
    _sq_q2p   = (gip.structural_probs or {}).get("Q2", 0) if gip else 0
    _sq_label = f"STRUCTURAL — {QN_CLIMATE.get(sq,'')}" + (f" / Q2↑ {_sq_q2p:.0%}" if sq=="Q3" and _sq_q2p>0.25 else "")
    _mq_label = f"MONTHLY — {QN.get(mq,'')} (Weather)"
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(qcard(_sq_label, sq, gip.structural_conf if gip else 0, "Quarterly — Climate"), unsafe_allow_html=True)
    with c2: st.markdown(qcard(_mq_label, mq, gip.monthly_conf if gip else 0, "3-6 Week — Weather"), unsafe_allow_html=True)
    with c3: st.markdown(qcard("GLOBAL — 50 Countries", gq, global_.get("global_conf",0), "GDP-weighted"), unsafe_allow_html=True)
    with c4:
        if gip:
            dc = qc(sq); flip = gip.flip_hazard
            st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:14px;text-align:center;height:100%;">
            <div style="font-size:11px;color:#9CA3AF;margin-bottom:4px;">ALIGNMENT</div>
            <div style="font-size:22px;font-weight:800;color:{dc};">{gip.divergence.upper()}</div>
            <div style="font-size:12px;color:#9CA3AF;margin-top:4px;">{gip.operating_regime}</div>
            <div style="font-size:11px;color:#E8ECF0;margin-top:8px;">Flip Risk: {flip:.0%}</div>
            </div>''', unsafe_allow_html=True)

    # ── Win Rate / Feedback Loop ──────────────────────────────────────────────
    if fb_eval:
        evaluated = fb_eval.get("evaluated", 0)
        promoted  = fb_eval.get("promoted", 0)
        demoted   = fb_eval.get("demoted", 0)
        win_rate  = (promoted / max(evaluated, 1)) * 100
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        w1, w2, w3, w4 = st.columns(4)
        w1.markdown(f'<div class="winrate-card"><div style="font-size:11px;color:#9CA3AF;">Evaluated</div><div style="font-size:22px;font-weight:800;color:#E8ECF0;">{evaluated}</div></div>', unsafe_allow_html=True)
        w2.markdown(f'<div class="winrate-card"><div style="font-size:11px;color:#9CA3AF;">Promoted ✅</div><div style="font-size:22px;font-weight:800;color:#10B981;">{promoted}</div></div>', unsafe_allow_html=True)
        w3.markdown(f'<div class="winrate-card"><div style="font-size:11px;color:#9CA3AF;">Demoted ❌</div><div style="font-size:22px;font-weight:800;color:#EF4444;">{demoted}</div></div>', unsafe_allow_html=True)
        w4.markdown(f'<div class="winrate-card"><div style="font-size:11px;color:#9CA3AF;">Win Rate</div><div style="font-size:22px;font-weight:800;color:#00D4AA;">{win_rate:.1f}%</div></div>', unsafe_allow_html=True)

    # ── Front-Run Banner + Sequencing Pills ───────────────────────────────────
    if transition:
        fw = transition.front_run_window
        fr = transition.front_run_rationale
        fw_color = {"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}.get(fw,"#374151")
        fw_icon  = {"now":"🚨","1-2w":"⚡","3-6w":"👀","not yet":"🛑"}.get(fw,"🛑")
        if fw != "not yet":
            st.markdown(f'''<div style="background:{fw_color}22;border-left:4px solid {fw_color};padding:12px;border-radius:6px;margin-top:10px;">
            <div style="font-size:14px;font-weight:700;color:{fw_color};">{fw_icon} FRONT-RUN WINDOW: {fw.upper()}</div>
            <div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{fr}</div>
            </div>''', unsafe_allow_html=True)
        # Sequencing pills — computed dari sq/mq state, zero hardcode
        st.markdown(_build_sequence_pills(sq, mq, QC), unsafe_allow_html=True)

    # ── Early Discovery Alert ─────────────────────────────────────────────────
    if auto_disc:
        candidates = auto_disc.get("candidates", [])
        brewing = [c for c in candidates if c.get("stage") == "brewing"]
        if brewing:
            top_brew = max(brewing, key=lambda x: x.get("confidence", 0))
            st.markdown(f'''<div style="background:#6366F122;border-left:4px solid #6366F1;padding:12px;border-radius:6px;margin-top:10px;">
            <div style="font-size:13px;font-weight:700;color:#818CF8;">🔮 EARLY DISCOVERY — {len(brewing)} pre-consensus opportunity detected</div>
            <div style="font-size:12px;color:#E8ECF0;margin-top:4px;">Top: <b>{top_brew.get("name","")}</b> — {top_brew.get("thesis","")[:80]}... → <b>🔮 Early Discovery</b> tab</div>
            </div>''', unsafe_allow_html=True)

    # ── Quad Transition Probabilities ─────────────────────────────────────────
    if gip:
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        st.markdown("### 📊 Quad Transition Probabilities")
        QUAD_NAMES = {"Q1":"Goldilocks (Growth↑ Inflation↓)","Q2":"Reflation (Growth↑ Inflation↑)",
                      "Q3":"Stagflation (Growth↓ Inflation↑)","Q4":"Deflation (Growth↓ Inflation↓)"}
        QUAD_WHAT_WINS = {"Q1":"Cyclicals, Tech, Small Caps","Q2":"Energy, Materials, Commodity FX, TIPS",
                          "Q3":"Gold, USD, Defensives, Short Duration","Q4":"Long Duration (TLT), Gold, Defensives"}

        def _transition_panel(probs, current_q, horizon_label, horizon_desc):
            if not probs: return
            sorted_p = sorted(probs.items(), key=lambda x: x[1], reverse=True)
            top_q, top_p = sorted_p[0]
            top_c = qc(top_q)
            st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;margin-bottom:8px;">
            <div style="font-size:11px;color:#9CA3AF;">{horizon_label} — {horizon_desc}</div>
            <div style="font-size:13px;color:#E8ECF0;margin-top:4px;">Currently: <b>{current_q}</b> — {QUAD_NAMES.get(current_q,"")}</div>
            <div style="font-size:13px;color:#E8ECF0;margin-top:2px;">Most likely → <b style="color:{top_c};">{top_q}</b> ({top_p:.0%})</div>
            </div>''', unsafe_allow_html=True)
            fig = go.Figure()
            for q, p in sorted(probs.items()):
                is_top = (q == top_q)
                fig.add_bar(x=[q], y=[p], marker_color=qc(q),
                    marker_line=dict(width=3 if is_top else 0, color="white"),
                    text=[f" <b>{p:.0%}</b>"], textposition="outside",
                    textfont=dict(size=13, color=qc(q)), name=q)
            fig.update_layout(showlegend=False, height=180, margin=dict(t=10,b=8,l=4,r=4),
                paper_bgcolor="#111827", plot_bgcolor="#111827", font=dict(color="#E8ECF0", family="JetBrains Mono"),
                yaxis=dict(range=[0,1.15], tickformat=".0%", showgrid=True, gridcolor="#1F2B3D", tickfont=dict(size=10)),
                xaxis=dict(showgrid=False, tickfont=dict(size=12, color="#E8ECF0")), bargap=0.3)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
            if top_q != current_q:
                action_map = {
                    ("Q3","Q2"):("Reflation Breakout","Growth stabilizes + inflation stays hot → stay short duration, long commodities/energy"),
                    ("Q3","Q4"):("Deflation Rotation","Inflation cooling → add TLT/duration, gold; reduce energy"),
                    ("Q3","Q1"):("Clean Recovery","Both inflation cools AND growth rebounds → max risk-on"),
                    ("Q2","Q3"):("Stagflation Intensifies","Growth decelerating, inflation sticky → reduce beta, add defensives"),
                    ("Q2","Q1"):("Soft Landing","Growth holds, inflation cools → remain long cyclicals"),
                    ("Q1","Q2"):("Reflation Beginning","Inflation re-accelerates → add energy/materials, trim bonds"),
                    ("Q1","Q4"):("Growth Fatigue","Late-cycle slowdown → rotate to defensives/quality"),
                    ("Q4","Q1"):("Goldilocks Restart","Fed easing + growth recovery → maximum long positioning"),
                    ("Q4","Q3"):("Supply Shock Re-ignition","Oil spike before growth recovers → gold/defense only"),
                }
                key = (current_q, top_q)
                action_title, action_note = action_map.get(key, (f"{current_q}→{top_q}", QUAD_WHAT_WINS.get(top_q,"")))
                st.markdown(f'''<div style="background:#1F2B3D;border-radius:6px;padding:10px;margin-top:6px;">
                <div style="font-size:12px;font-weight:700;color:#F59E0B;">IF {top_q} materializes: {action_title}</div>
                <div style="font-size:11px;color:#9CA3AF;margin-top:2px;">{action_note}</div>
                </div>''', unsafe_allow_html=True)

        # Dynamic labels — zero hardcode
        _sq_q2p = (gip.structural_probs or {}).get("Q2", 0)
        _sq_panel_desc = QN_CLIMATE.get(sq, "Quarterly") + (f" · Q2↑ {_sq_q2p:.0%}" if sq=="Q3" and _sq_q2p>0.25 else "")
        _mq_panel_desc = f"{QN.get(mq,'Monthly')} (Weather)"
        tp1, tp2, tp3 = st.columns(3)
        with tp1: _transition_panel(gip.structural_probs, sq, "STRUCTURAL", _sq_panel_desc)
        with tp2: _transition_panel(gip.monthly_probs,    mq, "MONTHLY",    _mq_panel_desc)
        with tp3:
            gprobs   = global_.get("global_probs", {})
            gq_panel = global_.get("dominant_quad", gq)
            if gprobs: _transition_panel(gprobs, gq_panel, "GLOBAL", "50 Countries · GDP-weighted")

    # ── Regime Playbook Summary ───────────────────────────────────────────────
    st.markdown("---")
    c_pb, c_sig = st.columns([1.3, 1])
    with c_pb:
        st.markdown("### 🎯 Regime Playbook")
        if pb_data:
            st.markdown(f"**✅ LONG**: {' · '.join(pb_data.get('best_assets',[])[:5])}")
            st.markdown(f"**❌ AVOID**: {' · '.join(pb_data.get('worst_assets',[])[:5])}")
            st.markdown(f"📊 Style: {pb_data.get('style','')}")
            st.markdown(f"💱 FX: {pb_data.get('fx','')}")
            st.markdown(f"🏦 Bonds: {pb_data.get('bonds','')}")
            if pb_data.get("monthly_adds"):
                st.markdown(f"⚡ Monthly adds: {' · '.join(pb_data['monthly_adds'])}")
    with c_sig:
        st.markdown("### 📡 GIP Signals")
        if gip:
            f = gip.features
            rows = [
                ["Growth Momentum", fp(f.get("growth_momentum"))],
                ["Inflation Momentum", fp(f.get("inflation_momentum"))],
                ["Policy Score", fp(f.get("policy_score"))],
                ["Leading Indicator", fp(f.get("leading_indicator_composite"))],
                ["Data Coverage", fp(f.get("data_coverage"))],
            ]
            st.dataframe(pd.DataFrame(rows, columns=["Signal","Value"]), hide_index=True, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# 📈 GIP MODEL (was "GIP Regime")
# Hedgeye: "GIP Model — Growth · Inflation · Policy"
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 GIP Model":
    st.markdown("# 📈 GIP Model — Growth · Inflation · Policy")
    st.caption("Hedgeye: YoY RoC second derivative. 'Heating up or cooling down?' — 30 data points monthly, 90 quarterly.")
    if not gip: st.warning("No GIP data. Refresh."); st.stop()

    # Climate vs Weather framing (Hedgeye exact terminology)
    st.markdown("### 🌤️ Climate vs. Weather")
    col_c, col_w = st.columns(2)
    with col_c:
        st.markdown(f'''<div style="background:#111827;border:1px solid {qc(sq)}44;border-radius:8px;padding:16px;">
        <div style="font-size:11px;color:#9CA3AF;margin-bottom:4px;">QUARTERLY QUAD — CLIMATE</div>
        <div style="font-size:32px;font-weight:800;color:{qc(sq)};">{sq}</div>
        <div style="font-size:14px;color:{qc(sq)};margin-top:4px;">{QN_CLIMATE.get(sq,"")}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:8px;">Conf: {gip.structural_conf:.0%} · Anchors core positioning</div>
        <div style="font-size:11px;color:#E8ECF0;margin-top:4px;">Flip Risk: {gip.flip_hazard:.0%} · Coverage: {gip.data_coverage:.0%}</div>
        </div>''', unsafe_allow_html=True)
    with col_w:
        st.markdown(f'''<div style="background:#111827;border:1px solid {qc(mq)}44;border-radius:8px;padding:16px;">
        <div style="font-size:11px;color:#9CA3AF;margin-bottom:4px;">MONTHLY QUAD — WEATHER</div>
        <div style="font-size:32px;font-weight:800;color:{qc(mq)};">{mq}</div>
        <div style="font-size:14px;color:{qc(mq)};margin-top:4px;">{QN_CLIMATE.get(mq,"")}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:8px;">Conf: {gip.monthly_conf:.0%} · 3-6 Week Tactical Overlay</div>
        <div style="font-size:11px;color:#E8ECF0;margin-top:4px;">Divergence: {gip.divergence} · {gip.operating_regime}</div>
        </div>''', unsafe_allow_html=True)

    # G + I Momentum
    st.markdown("---")
    st.markdown("### 📊 Growth & Inflation Rate of Change")
    f = gip.features
    g_mom = f.get("growth_momentum", 0)
    i_mom = f.get("inflation_momentum", 0)
    g_c = "#10B981" if g_mom > 0 else "#EF4444"
    i_c = "#10B981" if i_mom < 0 else "#EF4444"  # Inflation down = good
    gm1, gm2, gm3, gm4 = st.columns(4)
    gm1.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Growth Momentum</div><div style="font-size:24px;font-weight:800;color:{g_c};">{fp(g_mom)}</div><div style="font-size:10px;color:#6B7280;">{"Accelerating ↑" if g_mom>0 else "Decelerating ↓"}</div></div>', unsafe_allow_html=True)
    gm2.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Inflation Momentum</div><div style="font-size:24px;font-weight:800;color:{i_c};">{fp(i_mom)}</div><div style="font-size:10px;color:#6B7280;">{"Rising ↑" if i_mom>0 else "Cooling ↓"}</div></div>', unsafe_allow_html=True)
    gm3.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Policy Score</div><div style="font-size:24px;font-weight:800;color:#E8ECF0;">{fp(f.get("policy_score"))}</div><div style="font-size:10px;color:#6B7280;">{"Dovish" if f.get("policy_score",0)>0.1 else "Hawkish" if f.get("policy_score",0)<-0.1 else "Neutral"}</div></div>', unsafe_allow_html=True)
    gm4.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Leading Indicator</div><div style="font-size:24px;font-weight:800;color:#E8ECF0;">{fp(f.get("leading_indicator_composite"))}</div><div style="font-size:10px;color:#6B7280;">Data Coverage: {fp(f.get("data_coverage"))}</div></div>', unsafe_allow_html=True)

    # Timing signals (merged from old Timing tab)
    st.markdown("---")
    st.markdown("### ⏱️ Regime Timing Signals")
    if transition:
        fw = transition.front_run_window
        fr = transition.front_run_rationale
        ew_sigs = getattr(transition, "early_warning_signals", {})
        fw_color = {"now":"#EF4444","1-2w":"#F59E0B","3-6w":"#6366F1","not yet":"#374151"}.get(fw,"#374151")
        fw_icon  = {"now":"🚨","1-2w":"⚡","3-6w":"👀","not yet":"🛑"}.get(fw,"🛑")
        st.markdown(f'''<div style="background:{fw_color}22;border-left:4px solid {fw_color};padding:12px;border-radius:6px;">
        <div style="font-size:14px;font-weight:700;color:{fw_color};">{fw_icon} FRONT-RUN WINDOW: {fw.upper()}</div>
        <div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{fr}</div>
        </div>''', unsafe_allow_html=True)
        st.markdown(_build_sequence_pills(sq, mq, QC), unsafe_allow_html=True)
        if ew_sigs:
            st.markdown("#### Early Warning Signals")
            ew_rows = [{"Signal": k.replace("_"," ").title(), "Firing": "✅ YES" if v>=0.5 else "⬜ Not yet", "Score": f"{v:.0f}"}
                       for k, v in sorted(ew_sigs.items(), key=lambda x: x[1], reverse=True)]
            st.dataframe(pd.DataFrame(ew_rows), hide_index=True, use_container_width=True, height=300)
            firing_count = sum(1 for v in ew_sigs.values() if v >= 0.5)
            st.progress(firing_count/max(len(ew_sigs),1), text=f"Early warning: {firing_count}/{len(ew_sigs)} signals firing")
    else:
        st.info("Transition engine data tidak tersedia. Refresh.")

    # Historical Analogs
    if analogs and analogs.get("top_analogs"):
        st.markdown("---")
        st.markdown("### 📚 Historical Analogs")
        st.caption(analogs.get("composite_note",""))
        for i, a in enumerate(analogs["top_analogs"]):
            sim = a.get("similarity",0)
            with st.expander(f"**{a['label']}** — Similarity: {sim:.0%}", expanded=(i==0)):
                cc = st.columns(3)
                cc[0].markdown(f"**1M:** {a.get('path_1m','')}")
                cc[1].markdown(f"**3M:** {a.get('path_3m','')}")
                cc[2].markdown(f"**6M:** {a.get('path_6m','')}")
                st.markdown(f"**Next bias:** {a.get('next_bias','')}")
                st.markdown(f"**Impacts:** " + " | ".join([f"{k.upper()}={v}" for k,v in a.get("impacts",{}).items()]))


# ══════════════════════════════════════════════════════════════════════════════
# 🎯 RISK RANGES™
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Risk Ranges™":
    st.markdown("# 🎯 Risk Range™ — TRADE · TREND · TAIL")
    st.caption("Hurst Rescaled Range Analysis. LRR=buy zone. TRR=trim zone. TREND break=exit. McCullough: 'Buy the damn dip in bullish formation.'")
    ar = rr.get("asset_ranges", {})
    if not ar: st.warning("No risk range data. Refresh."); st.stop()

    all_a = sorted(
        [(s, a) for s, v in ar.items() for a in v.get("alerts", [])],
        key=lambda x: {"CRITICAL":0,"HIGH":1,"MEDIUM":2}.get(x[1].get("priority"),3)
    )
    if all_a:
        st.markdown("### 🔔 Live Alerts")
        for sym, a in all_a[:20]:
            ic = "🔴" if a["priority"]=="CRITICAL" else "🟡" if a["priority"]=="HIGH" else "🔵"
            bdr = "#EF4444" if a["priority"]=="CRITICAL" else "#F59E0B"
            st.markdown(f'<div style="background:#1F2B3D;border-left:3px solid {bdr};padding:8px;border-radius:4px;margin-bottom:4px;">{ic} <b>[{sym}]</b> {a["action"]} {a["duration"]} — {a.get("note","")}</div>', unsafe_allow_html=True)

    st.markdown("---")
    mkt_filter = st.selectbox("Filter market", ["All","us_equity","forex","commodity","crypto","ihsg"])
    search = st.text_input("Search ticker", "")
    rows = []
    for sym, v in ar.items():
        if mkt_filter != "All" and v.get("market","") != mkt_filter: continue
        if search and search.upper() not in sym.upper(): continue
        trade = v.get("trade",{}); trend = v.get("trend",{})
        px  = v.get("px", float("nan"))
        lrr = trade.get("lrr", float("nan"))
        trr = trade.get("trr", float("nan"))
        rows.append({
            "Ticker": sym, "Px": ff(px,2),
            "LRR": ff(lrr,2), "TRR": ff(trr,2),
            "TRADE": v.get("composite","—").upper(),
            "TREND": v.get("trend_signal","—").upper() if isinstance(v.get("trend_signal"),str) else "—",
            "Quality": v.get("quality","—"),
            "Stretch": trade.get("stretch","—"),
            "Hurst": ff(trend.get("hurst"),2),
            "Market": v.get("market","—"),
            "Regime Trap": "⚠️" if v.get("regime_trap") else "",
        })
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, use_container_width=True, height=500)
    else:
        st.info("No data matches filter.")


# ══════════════════════════════════════════════════════════════════════════════
# ⚡ ETF PRO (NEW — Hedgeye ETF Pro Plus style)
# Combines: US Sectors, Forex, Commodities, Crypto, Fixed Income
# Quad-aware: Best/Worst per current Quad
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ ETF Pro":
    st.markdown("# ⚡ ETF Pro — Quad-Aware Positioning")
    st.caption(f"Current Quad: **{sq}** Structural · **{mq}** Monthly · Go Anywhere, But Not Everywhere.")

    ar = rr.get("asset_ranges", {})
    best_set  = set(pb_data.get("best_assets", []))
    worst_set = set(pb_data.get("worst_assets", []))

    # ETF playbook from Quad
    st.markdown("### 🎯 Regime Playbook")
    col_l, col_s = st.columns(2)
    with col_l:
        st.markdown(f'<div style="background:#052e16;border-left:4px solid #10B981;padding:12px;border-radius:6px;"><div style="font-size:12px;font-weight:700;color:#10B981;">✅ LONG — {sq} Playbook</div><div style="font-size:13px;color:#E8ECF0;margin-top:6px;">{" · ".join(pb_data.get("best_assets",[])[:8])}</div><div style="font-size:11px;color:#9CA3AF;margin-top:4px;">Style: {pb_data.get("style","")}</div></div>', unsafe_allow_html=True)
    with col_s:
        st.markdown(f'<div style="background:#3b0000;border-left:4px solid #EF4444;padding:12px;border-radius:6px;"><div style="font-size:12px;font-weight:700;color:#EF4444;">❌ AVOID / SHORT — {sq} Playbook</div><div style="font-size:13px;color:#E8ECF0;margin-top:6px;">{" · ".join(pb_data.get("worst_assets",[])[:8])}</div><div style="font-size:11px;color:#9CA3AF;margin-top:4px;">FX: {pb_data.get("fx","")} · Bonds: {pb_data.get("bonds","")}</div></div>', unsafe_allow_html=True)

    # ETF Ideas by asset class
    MARKET_LABELS = {
        "us_equity":"🇺🇸 US Equity","forex":"💱 Forex","commodity":"🛢 Commodities",
        "crypto":"₿ Crypto","ihsg":"🇮🇩 IHSG","bond":"🏦 Fixed Income"
    }
    st.markdown("---")
    st.markdown("### 📋 ETF Ideas — Buy/Sell Levels")
    st.caption("LRR = Low Risk Range (buy zone). TRR = Top Risk Range (trim zone). Bullish TREND = buy dips. Bearish TREND = avoid/short.")

    market_tabs = st.tabs(list(MARKET_LABELS.values()))
    for tab, (mkt, mkt_label) in zip(market_tabs, MARKET_LABELS.items()):
        with tab:
            etf_rows = []
            for sym, v in ar.items():
                if v.get("market","") != mkt: continue
                trade = v.get("trade",{}); trend = v.get("trend",{})
                px  = v.get("px", float("nan"))
                lrr = trade.get("lrr", float("nan"))
                trr = trade.get("trr", float("nan"))
                comp = v.get("composite","neutral")
                qual = v.get("quality","—")
                regime_fit = sym in best_set or any(sym in b for b in best_set)
                regime_avoid = sym in worst_set
                etf_rows.append({
                    "Ticker": sym, "Px": ff(px,2),
                    "LRR (Buy)": ff(lrr,2), "TRR (Trim)": ff(trr,2),
                    "Signal": comp.upper(), "Quality": qual,
                    "Stretch": trade.get("stretch","—"),
                    "Quad Fit": "✅" if regime_fit else ("❌" if regime_avoid else "—"),
                    "Trap": "⚠️" if v.get("regime_trap") else "",
                })
            if etf_rows:
                df_etf = pd.DataFrame(etf_rows)
                # Highlight long/short
                st.dataframe(df_etf, hide_index=True, use_container_width=True, height=400)
                # Top long idea cards
                long_etfs  = [r for r in etf_rows if r["Signal"]=="BULLISH"  and r["Quad Fit"]=="✅"][:3]
                short_etfs = [r for r in etf_rows if r["Signal"]=="BEARISH" and r["Quad Fit"]=="❌"][:3]
                if long_etfs:
                    st.markdown("**Top Long Setups:**")
                    for e in long_etfs:
                        st.markdown(f'<div class="etf-long-card"><b style="color:#10B981;">{e["Ticker"]}</b> · Px {e["Px"]} · LRR <b>{e["LRR (Buy)"]}</b> · TRR {e["TRR (Trim)"]} · {e["Quality"]} · {e["Stretch"]}</div>', unsafe_allow_html=True)
                if short_etfs:
                    st.markdown("**Top Short Setups:**")
                    for e in short_etfs:
                        st.markdown(f'<div class="etf-short-card"><b style="color:#EF4444;">{e["Ticker"]}</b> · Px {e["Px"]} · TRR <b>{e["TRR (Trim)"]}</b> · LRR {e["LRR (Buy)"]} · {e["Quality"]} · {e["Stretch"]}</div>', unsafe_allow_html=True)
            else:
                st.info(f"No {mkt_label} data. Refresh dulu.")


# ══════════════════════════════════════════════════════════════════════════════
# 📊 LEADERBOARD (was "Signal Strength")
# Hedgeye: "The Leaderboard — Top 21 Long Ideas"
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Leaderboard":
    st.markdown("# 📊 The Leaderboard — Signal Strength Stocks")
    st.caption("Hedgeye-style: Quality A = Bullish TRADE+TREND near LRR + volume confirm. Updated weekly (Senin). Min 1% position, max 3%.")

    ar = rr.get("asset_ranges", {})
    if not ar: st.warning("No risk range data. Refresh."); st.stop()

    best_assets  = set(pb_data.get("best_assets", []))
    worst_assets = set(pb_data.get("worst_assets", []))

    long_picks = []; short_picks = []
    for sym, v in ar.items():
        qual = v.get("quality","none"); comp = v.get("composite","neutral")
        trade = v.get("trade",{}); trend = v.get("trend",{})
        px    = v.get("px", float("nan"))
        vol_c = trade.get("volume_confirm", 0.5)
        stretch = trade.get("stretch","neutral")
        hurst_t = trend.get("hurst", 0.5)
        from config.settings import TICKER_SECTOR
        sector = TICKER_SECTOR.get(sym,"generic")
        if qual in ("A","B") and comp == "bullish":
            lrr = trade.get("lrr", float("nan")); trr = trade.get("trr", float("nan"))
            near_lrr = False
            if math.isfinite(px) and math.isfinite(lrr) and math.isfinite(trr) and (trr-lrr)>1e-9:
                pos = (px-lrr)/(trr-lrr); near_lrr = pos<=0.35 or stretch in ("oversold","reset_zone")
            else: near_lrr = stretch in ("oversold","reset_zone")
            regime_fit   = any(sector.replace("_"," ").lower() in b.lower() or b.lower() in sym.lower() for b in best_assets) or sym in best_assets
            regime_avoid = any(sector.replace("_"," ").lower() in w.lower() or w.lower() in sym.lower() for w in worst_assets)
            score = (50 if qual=="A" else 30) + (25 if near_lrr else 0) + (15 if vol_c>0.6 else 0) + (10 if regime_fit else 0) + (-20 if regime_avoid else 0) + (5 if hurst_t>0.5 else 0)
            long_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"stretch":stretch,"vol_c":vol_c,"hurst":hurst_t,"regime_fit":regime_fit,"score":score,"note":"Near LRR" if near_lrr else f"Stretch: {stretch}","sector":sector})
        if qual in ("short_A","short_B") and comp == "bearish":
            lrr = trade.get("lrr", float("nan")); trr = trade.get("trr", float("nan"))
            near_trr = stretch in ("overbought","extended")
            if math.isfinite(px) and math.isfinite(lrr) and math.isfinite(trr) and (trr-lrr)>1e-9:
                pos = (px-lrr)/(trr-lrr); near_trr = pos>=0.65 or stretch in ("overbought","extended")
            regime_fit = any(sector.replace("_"," ").lower() in w.lower() or w.lower() in sym.lower() for w in worst_assets) or sym in worst_assets
            score = (50 if qual=="short_A" else 30) + (25 if near_trr else 0) + (15 if vol_c>0.6 else 0) + (10 if regime_fit else 0) + (5 if hurst_t>0.5 else 0)
            short_picks.append({"ticker":sym,"quality":qual,"px":px,"lrr":lrr,"trr":trr,"stretch":stretch,"vol_c":vol_c,"hurst":hurst_t,"regime_fit":regime_fit,"score":score,"note":"Near TRR" if near_trr else f"Stretch: {stretch}","sector":sector})

    long_picks.sort(key=lambda x: -x["score"])
    short_picks.sort(key=lambda x: -x["score"])

    # Signal count (Hedgeye format: "77 Stocks — 7 Added, 12 Removed")
    total_bullish = len(long_picks); total_bearish = len(short_picks)
    s1,s2,s3,s4 = st.columns(4)
    s1.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Bullish Names</div><div style="font-size:28px;font-weight:800;color:#10B981;">{total_bullish}</div></div>', unsafe_allow_html=True)
    s2.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Quality A Longs</div><div style="font-size:28px;font-weight:800;color:#00D4AA;">{sum(1 for p in long_picks if p["quality"]=="A")}</div></div>', unsafe_allow_html=True)
    s3.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Quality A Shorts</div><div style="font-size:28px;font-weight:800;color:#EF4444;">{sum(1 for p in short_picks if p["quality"]=="short_A")}</div></div>', unsafe_allow_html=True)
    s4.markdown(f'<div class="winrate-card" style="text-align:center;"><div style="font-size:11px;color:#9CA3AF;">Regime Traps</div><div style="font-size:28px;font-weight:800;color:#F59E0B;">{sum(1 for v in ar.values() if v.get("regime_trap"))}</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(f"### 🟢 TOP 21 LONG IDEAS — Quality A / B")
    for p in long_picks[:21]:
        rb = "✅ Regime Fit" if p["regime_fit"] else "⚠️ Neutral"
        st.markdown(f'''<div class="signal-A">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div style="font-size:15px;font-weight:800;color:#10B981;">{p["ticker"]} <span style="font-size:11px;color:#A7F3D0;">({p["quality"]})</span></div>
            <div style="font-size:11px;color:#9CA3AF;">{rb} · Score: {p["score"]:.0f} · {p["sector"].replace("_"," ").title()}</div>
        </div>
        <div style="font-size:12px;color:#E8ECF0;margin-top:4px;">Px: {ff(p["px"],2)} · LRR: <b>{ff(p["lrr"],2)}</b> · TRR: {ff(p["trr"],2)} · {p["note"]}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:2px;">Vol Confirm: {fp(p["vol_c"])} · Hurst: {ff(p["hurst"],2)}</div>
        </div>''', unsafe_allow_html=True)
    if not long_picks: st.info("No Quality A/B long setups. Market may be extended or regime not aligned.")

    st.markdown("---")
    st.markdown("### 🔴 SHORT IDEAS — Quality Short-A / Short-B")
    for p in short_picks[:15]:
        rb = "✅ Regime Fit" if p["regime_fit"] else "⚠️ Neutral"
        st.markdown(f'''<div class="signal-shortA">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div style="font-size:15px;font-weight:800;color:#EF4444;">{p["ticker"]} <span style="font-size:11px;color:#FECACA;">({p["quality"]})</span></div>
            <div style="font-size:11px;color:#9CA3AF;">{rb} · Score: {p["score"]:.0f} · {p["sector"].replace("_"," ").title()}</div>
        </div>
        <div style="font-size:12px;color:#E8ECF0;margin-top:4px;">Px: {ff(p["px"],2)} · TRR: <b>{ff(p["trr"],2)}</b> · LRR: {ff(p["lrr"],2)} · {p["note"]}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:2px;">Vol Confirm: {fp(p["vol_c"])} · Hurst: {ff(p["hurst"],2)}</div>
        </div>''', unsafe_allow_html=True)
    if not short_picks: st.info("No Quality Short-A/B setups.")

    # Full signal table
    st.markdown("---")
    st.markdown("### 📋 Full Signal Table")
    all_rows = [{"Ticker":p["ticker"],"Side":"LONG","Quality":p["quality"],"Score":f'{p["score"]:.0f}',"Px":ff(p["px"],2),"LRR":ff(p["lrr"],2),"TRR":ff(p["trr"],2),"Stretch":p["stretch"],"VolCnf":fp(p["vol_c"]),"Regime":"✅" if p["regime_fit"] else "—"} for p in long_picks[:30]]
    all_rows += [{"Ticker":p["ticker"],"Side":"SHORT","Quality":p["quality"],"Score":f'{p["score"]:.0f}',"Px":ff(p["px"],2),"LRR":ff(p["lrr"],2),"TRR":ff(p["trr"],2),"Stretch":p["stretch"],"VolCnf":fp(p["vol_c"]),"Regime":"✅" if p["regime_fit"] else "—"} for p in short_picks[:20]]
    if all_rows: st.dataframe(pd.DataFrame(all_rows), hide_index=True, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# 🌍 GLOBAL QUAD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌍 Global Quad":
    st.markdown("# 🌍 Global Quad — 50 Countries")
    st.caption("GIP model applied to country ETFs. GDP-weighted. Shows where capital is rotating.")
    if not global_: st.warning("No global data. Refresh."); st.stop()

    gconf  = global_.get("global_conf", 0.0)
    gprobs = global_.get("global_probs", {})
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.markdown(qcard("GLOBAL QUAD", gq, gconf, "50 Country ETFs"), unsafe_allow_html=True)
        st.markdown("### Global Probabilities")
        fig = go.Figure()
        for q, p in sorted((gprobs or {}).items()):
            fig.add_bar(x=[q], y=[p], marker_color=qc(q), text=[f"<b>{p:.0%}</b>"], textposition="outside", name=q)
        fig.update_layout(showlegend=False, height=200, margin=dict(t=10,b=8,l=4,r=4),
            paper_bgcolor="#111827", plot_bgcolor="#111827", font=dict(color="#E8ECF0"),
            yaxis=dict(range=[0,1.15], tickformat=".0%"), xaxis=dict(showgrid=False), bargap=0.3)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    with c2:
        st.markdown("### Country Heatmap")
        heat = []
        for country, data in global_.get("country_quads", {}).items():
            if isinstance(data, (list, tuple)) and len(data) >= 3:
                etf, quad, conf = data[0], data[1], data[2]
            elif isinstance(data, dict):
                etf, quad, conf = data.get("etf",""), data.get("quad",""), data.get("conf",0)
            else: etf, quad, conf = "", "", 0
            heat.append({"Country":country,"ETF":etf,"Quad":quad,"Conf":f"{conf:.0%}"})
        if heat:
            df = pd.DataFrame(heat)
            st.dataframe(df.style.map(lambda v: f"color:{QC.get(v,'#9CA3AF')}", subset=["Quad"]),
                         hide_index=True, height=420, use_container_width=True)
        else: st.info("No country quad data available.")


# ══════════════════════════════════════════════════════════════════════════════
# 🇮🇩 IHSG
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🇮🇩 IHSG":
    st.markdown("# 🇮🇩 IHSG — Indonesia Market")
    st.caption("GIP + Risk Range applied to Indonesia stocks. Quad overlay + CKPN banking risk monitor.")
    ar = rr.get("asset_ranges", {})
    ihsg_tickers = {sym: v for sym, v in ar.items() if v.get("market","") == "ihsg"}
    if not ihsg_tickers: st.info("IHSG data belum tersedia. Enable IHSG checkbox dan Refresh."); st.stop()

    st.markdown("### 📊 IHSG Signal Table")
    rows = []
    for sym, v in ihsg_tickers.items():
        trade = v.get("trade",{}); px = v.get("px",float("nan"))
        rows.append({"Ticker":sym,"Px":ff(px,0),"LRR":ff(trade.get("lrr"),0),"TRR":ff(trade.get("trr"),0),
                     "Signal":v.get("composite","—").upper(),"Quality":v.get("quality","—"),
                     "Stretch":trade.get("stretch","—"),"Trap":"⚠️" if v.get("regime_trap") else ""})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # EM Recovery Signal
    em_sig = btk.get("em_recovery",{}) if btk else {}
    if em_sig:
        conf = em_sig.get("confidence",0)
        ec = "#10B981" if conf>0.6 else "#F59E0B" if conf>0.4 else "#6B7280"
        st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:10px;margin-top:10px;">
        <div style="font-size:12px;font-weight:700;color:{ec};">🌍 EM Recovery Signal: {em_sig.get("trigger","")}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{em_sig.get("rationale","")}</div>
        <div style="font-size:11px;color:#E8ECF0;margin-top:4px;">Confidence: {conf:.0%} · Best: {", ".join(em_sig.get("best",[])[:6])}</div>
        </div>''', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 🔍 BOTTLENECK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Bottleneck":
    st.markdown("# 🔍 Bottleneck Scanner — Supply Chain · Thematic")
    st.caption("Citrini methodology: demand river meets capacity constraint. Second-order thinking. Own the bottleneck, not just the end market.")
    if not btk: st.warning("No bottleneck data. Refresh."); st.stop()

    buckets = btk.get("market_buckets", {})
    for mkt, items in buckets.items():
        if not items: continue
        with st.expander(f"**{mkt.replace('_',' ').upper()}** — {len(items)} signals", expanded=(mkt=="us_equity")):
            for c in items[:12]:
                tc = "#10B981" if c.get("direction")=="long" else "#EF4444" if c.get("direction")=="short" else "#9CA3AF"
                st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:6px;padding:10px;margin-bottom:6px;">
                <div style="font-size:13px;font-weight:700;color:{tc};">{c["ticker"]}</div>
                <div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{c.get("sector","").replace("_"," ").title()}</div>
                <div style="font-size:13px;font-weight:700;color:{tc};margin-top:4px;">{c.get("trend","").upper()}</div>
                <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">Score: {c.get("score",0):.2f} | EV: {c.get("ev",0):.2f}</div>
                {('<div style="font-size:10px;color:#EF4444;margin-top:4px;">⚠️ REGIME TRAP</div>') if c.get("regime_trap") else ""}
                </div>''', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 📖 NARRATIVES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📖 Narratives":
    st.markdown("# 📖 Active Narratives — Thematic Scoring")
    st.caption("Narratives drive markets. Score = conviction × data confirmation × regime alignment.")
    if not narr: st.warning("No narrative data. Refresh."); st.stop()

    active = narr.get("active_narratives", [])
    for n in active:
        score = n.get("score", 0)
        sc = "#10B981" if score > 0.6 else "#F59E0B" if score > 0.4 else "#6B7280"
        invalidators = n.get("invalidators", [])
        with st.expander(f"**{n.get('name','')}** — Score: {score:.0%}", expanded=False):
            st.markdown(f"**Thesis:** {n.get('thesis','')}")
            st.markdown(f"**Tickers:** {' · '.join(n.get('tickers',[])[:8])}")
            if invalidators: st.markdown(f"**Invalidators:** {', '.join(invalidators[:3]) if invalidators else 'None defined'}")
            best = n.get("best",[]); worst = n.get("worst",[])
            if best: st.markdown(f"**Best:** {' · '.join(best[:10])}")
            if worst: st.markdown(f"**Worst:** {' · '.join(worst[:10])}")

    if not active: st.info("Narratives not yet reaching critical mass.")


# ══════════════════════════════════════════════════════════════════════════════
# 🔮 EARLY DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Early Discovery":
    st.markdown("# 🔮 Early Discovery — Pre-Consensus Opportunities")
    st.caption("Autonomy engine: regime fit + price cluster + supply chain graph + news NLP. Brewing = pre-consensus. Active = confirmed.")

    candidates = auto_disc.get("candidates", []) if auto_disc else []
    disc_list  = disc.get("discoveries", []) if disc else []
    all_cands  = candidates + disc_list

    if not all_cands: st.info("No discoveries yet. Refresh with Force build."); st.stop()

    for stage in ["active","building","brewing"]:
        stage_items = [c for c in all_cands if c.get("stage") == stage]
        if not stage_items: continue
        stage_color = {"active":"#10B981","building":"#F59E0B","brewing":"#6366F1"}.get(stage,"#9CA3AF")
        st.markdown(f"### {stage.upper()} ({len(stage_items)})")
        for c in stage_items:
            conf = c.get("confidence",c.get("conviction",0))
            pump = c.get("pump_risk",0)
            with st.expander(f"**{c.get('name','')}** — Conf: {conf:.0%} · Pump Risk: {pump:.0%}", expanded=False):
                st.markdown(f"**Thesis:** {c.get('thesis','')}")
                st.markdown(f"**Category:** {c.get('category','')}")
                ben = c.get("beneficiary_tickers",[]); fade = c.get("fade_tickers",[])
                if ben:  st.markdown(f"**Beneficiaries:** {' · '.join(ben[:8])}")
                if fade: st.markdown(f"**Fade:** {' · '.join(fade[:5])}")
                conf_sig = c.get("confirmation_signal",""); inv = c.get("invalidators",[])
                if conf_sig: st.markdown(f"**Confirmation:** {conf_sig}")
                if inv: st.markdown(f"**Invalidators:** {', '.join(inv) if isinstance(inv,list) else inv}")


# ══════════════════════════════════════════════════════════════════════════════
# 🏥 HEALTH
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏥 Health":
    st.markdown("# 🏥 Market Health — VIX · Breadth · Crash Meter")
    st.caption("VIX bucket + crash meter + sector breadth + Fear & Greed.")
    if not health: st.warning("No health data. Refresh."); st.stop()

    vix_bucket = health.get("vix_bucket") or {}
    vix_b = vix_bucket.get("bucket","unknown")
    vix_color = {"Investable":"#10B981","Chop":"#F59E0B","Defensive":"#EF4444"}.get(vix_b,"#6B7280")
    st.markdown(f'''<div style="background:{vix_color}22;border-left:4px solid {vix_color};padding:12px;border-radius:6px;">
    <div style="font-size:16px;font-weight:800;color:{vix_color};">VIX BUCKET: {vix_b.upper()}</div>
    <div style="font-size:12px;color:#E8ECF0;margin-top:4px;">{vix_bucket.get("note","")}</div>
    </div>''', unsafe_allow_html=True)

    crash_meter = health.get("crash",{})
    if crash_meter:
        st.markdown("### Crash Meter")
        for k, v in crash_meter.get("signals",{}).items():
            st.progress(v, text=f"{k.replace('_',' ').title()}: {v:.0%}")
        st.markdown(f"**State:** {crash_meter.get('state','')} | Score: {crash_meter.get('score',0):.0%}")
        if crash_meter.get("reasons"): st.markdown("**Reasons:** " + " · ".join(crash_meter["reasons"]))

    breadth = health.get("market_health",{})
    if breadth:
        st.markdown("### Sector Breadth")
        st.markdown(f"**Verdict:** {breadth.get('verdict','')} | Score: {breadth.get('score',0):.3f}")
        st.markdown(f"**Sector Support:** {breadth.get('positive_sectors_1m',0)}/{breadth.get('total_buckets',0)} buckets positive 1M")
        if breadth.get("notes"):
            for note in breadth["notes"]: st.markdown(f"• {note}")

    fg = health.get("fear_greed",{})
    if fg:
        st.markdown("---"); st.markdown("### 😰 Fear & Greed")
        fg_score = fg.get("score",50); fg_label = fg.get("label","Neutral")
        fg_col = "#10B981" if fg_score<25 else "#F59E0B" if fg_score<55 else "#EF4444"
        st.markdown(f"**Score:** {fg_score:.0f}/100 — **{fg_label}**")
        st.progress(fg_score/100)


# ══════════════════════════════════════════════════════════════════════════════
# 📋 PLAYBOOK (was "Scenarios")
# Hedgeye: Regime Playbook + Scenario Probability + EM Recovery
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Playbook":
    st.markdown("# 📋 Regime Playbook — Scenarios · EM Recovery · Positioning")
    st.caption(f"Current: **{sq}** Structural · **{mq}** Monthly · Base case + alternative scenarios scored by data, not opinion.")

    # Playbook
    if pb_data:
        st.markdown("### 🎯 Regime Playbook")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f'<div style="background:#052e16;border-left:4px solid #10B981;padding:14px;border-radius:6px;"><div style="font-size:13px;font-weight:700;color:#10B981;">✅ LONG — {sq}</div><div style="font-size:13px;color:#E8ECF0;margin-top:6px;">{" · ".join(pb_data.get("best_assets",[]))}</div><div style="font-size:11px;color:#9CA3AF;margin-top:6px;">Style: {pb_data.get("style","")}<br>FX: {pb_data.get("fx","")}<br>Bonds: {pb_data.get("bonds","")}</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div style="background:#3b0000;border-left:4px solid #EF4444;padding:14px;border-radius:6px;"><div style="font-size:13px;font-weight:700;color:#EF4444;">❌ AVOID</div><div style="font-size:13px;color:#E8ECF0;margin-top:6px;">{" · ".join(pb_data.get("worst_assets",[]))}</div></div>', unsafe_allow_html=True)

    # Scenario cards
    scenarios_list = scen.get("scenarios",[])
    if scenarios_list:
        st.markdown("---")
        st.markdown("### 🔮 Scenario Probability Map")
        badges = ["🎯 BASE","🔄 ALT","⚠️ RISK","📌 TAIL"]
        badge_colors = ["#10B981","#F59E0B","#EF4444","#6366F1"]
        row1 = st.columns(2); row2 = st.columns(2)
        grids = [row1[0], row1[1], row2[0], row2[1]]
        for i, (sc_item, col) in enumerate(zip(scenarios_list[:4], grids)):
            pc = badge_colors[i]
            em_short = sc_item.em_note[:70]+"..." if len(sc_item.em_note)>70 else sc_item.em_note
            with col:
                st.markdown(f'''<div style="background:#111827;border:1px solid #1F2B3D;border-radius:8px;padding:12px;height:100%;">
                <div style="font-size:11px;color:{pc};font-weight:700;">{badges[i]} P={sc_item.probability:.0%} · Conf={sc_item.confirmation_score:.0%}</div>
                <div style="font-size:13px;color:#E8ECF0;margin-top:6px;font-weight:600;">{sc_item.name}</div>
                <div style="font-size:11px;color:#9CA3AF;margin-top:4px;">{sc_item.headline}</div>
                <div style="font-size:11px;color:#E8ECF0;margin-top:4px;">Best: {" · ".join(sc_item.best_assets[:4])}</div>
                <div style="font-size:11px;color:#EF4444;margin-top:2px;">Avoid: {" · ".join(sc_item.worst_assets[:4])}</div>
                <div style="font-size:10px;color:#6B7280;margin-top:6px;">🌍 {em_short}</div>
                </div>''', unsafe_allow_html=True)

    # Invalidation triggers
    bc = scen.get("base_case")
    if bc and hasattr(bc,"confirmation_triggers"):
        st.markdown("---")
        col_t, col_i = st.columns(2)
        with col_t:
            st.markdown(f"### ✅ Confirmation Triggers ({bc.name})")
            for t in bc.confirmation_triggers: st.markdown(f"• {t}")
        with col_i:
            st.markdown(f"### ❌ Invalidators (flip signal)")
            for inv in getattr(bc,"invalidators",[]): st.markdown(f"• {inv}")

    # GIP signals
    st.markdown("---")
    st.markdown("### 📡 GIP Signals")
    if gip:
        f = gip.features
        rows = [["Growth Momentum",fp(f.get("growth_momentum")),f.get("growth_momentum",0)],
                ["Inflation Momentum",fp(f.get("inflation_momentum")),f.get("inflation_momentum",0)],
                ["Policy Score",fp(f.get("policy_score")),f.get("policy_score",0)],
                ["Leading Indicator",fp(f.get("leading_indicator_composite")),f.get("leading_indicator_composite",0)],
                ["Data Coverage",fp(f.get("data_coverage")),f.get("data_coverage",0)]]
        df_sig = pd.DataFrame(rows, columns=["Signal","Value","_raw"])
        st.dataframe(df_sig[["Signal","Value"]], hide_index=True, use_container_width=True)
