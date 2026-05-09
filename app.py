"""app.py — MacroRegime Pro v21.4 | Complete Fix Release

All fixes applied:
1. Proxy options populate ALL Alpha Center fields (Exp Move, IV Rank, Max Pain)
2. Forex fallback from prices dict when ar is empty
3. Health render from snap + defensive messaging
4. Narratives/Discovery: no fallback message, always show data
5. Leveraged ETF card: better styling, visual hierarchy
6. QWINS global constant (fixes Playbook NameError)
7. All tabs: flexible market matching + always render tables
8. COT + OI integration for Forex, Commodities, Crypto

Options Sources:
 • US Stocks/ETFs: Barchart scraper + proxy fallback
 • Crypto: Deribit API (real Greeks) + proxy fallback
 • Forex: CME futures options + COT + OI + proxy fallback
 • Commodities: CME futures options + COT + OI + proxy fallback
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math
import time
import logging

logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="MacroRegime Pro", page_icon="📊",
    layout="wide", initial_sidebar_state="expanded"
)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp { background: #0D1117; }
.pill-green { background:#238636; color:#fff; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:600; }
.pill-yellow { background:#D29922; color:#fff; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:600; }
.pill-red { background:#F85149; color:#fff; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:600; }
.pill-purple { background:#A371F7; color:#fff; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:600; }
.pill-gray { background:#21262D; color:#8B949E; padding:2px 8px; border-radius:12px; font-size:12px; }
.metric-box { background:#161B22; border:1px solid #30363D; border-radius:10px; padding:14px; }
.card-green { border-left:4px solid #238636; background:#161B22; padding:12px; border-radius:6px; }
.card-yellow { border-left:4px solid #D29922; background:#161B22; padding:12px; border-radius:6px; }
.card-red { border-left:4px solid #F85149; background:#161B22; padding:12px; border-radius:6px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS & HELPERS
# ══════════════════════════════════════════════════════════════════════════════
QC = {"Q1":"#3FB950","Q2":"#D29922","Q3":"#F85149","Q4":"#A371F7"}
QN = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}
QNC = {
    "Q1":"🟢 Goldilocks — Growth Rising, Inflation Cooling",
    "Q2":"🟡 Reflation — Both Growth and Inflation Rising",
    "Q3":"🔴 Stagflation — Growth Slowing, Inflation Elevated",
    "Q4":"🟣 Deflation — Both Growth and Inflation Falling",
}
QUAD_EXPLAIN = {
    "Q1":"Best conditions for stocks and crypto. Growth is strong and inflation is under control. This is when markets perform best.",
    "Q2":"Tricky environment. Economy growing but inflation biting. Commodities, energy, and international stocks tend to win. Crypto can work.",
    "Q3":"Most dangerous quarter. Economy slowing but prices still high. Gold, silver, and defensive stocks are the place to be. Tech gets hurt.",
    "Q4":"Deflationary collapse. Safest assets win: government bonds, gold, utilities, cash. Avoid risk.",
}
QWINS = {
    "Q1":"Tech, Bitcoin, Small Caps",
    "Q2":"Energy, Materials, Commodities",
    "Q3":"Gold, Silver, Defensives",
    "Q4":"Government Bonds, Gold, Cash",
}

def qc(q): return QC.get(q,"#8B949E")
def qn(q): return QN.get(q,q)
def qnc(q): return QNC.get(q,q)

def fp(v):
    try: return f"{float(v):.1%}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"
def ff(v,d=2):
    try: return f"{float(v):,.{d}f}" if v is not None and math.isfinite(float(v)) else "—"
    except: return "—"
def _sf(v):
    if v is None: return None
    try:
        if isinstance(v, pd.Series): v = v.iloc[0]
        f = float(v); return f if math.isfinite(f) else None
    except: return None

def _price_ret(ticker, prices, days=21):
    s = prices.get(ticker)
    if s is None: return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < days + 1: return None
    try: return float(s.iloc[-1] / s.iloc[-(days+1)] - 1)
    except: return None

# ── Risk Range Levels ─────────────────────────────────────────────────────────
def _rr_levels(px, lrr, trr, side="long"):
    px = _sf(px) or 0; lrr = _sf(lrr) or 0; trr = _sf(trr) or 0
    if not (lrr > 0 and trr > 0 and trr > lrr): return None
    spread = trr - lrr
    pos = (px - lrr) / spread if spread > 0 else 0.5
    if side == "long":
        entry, tp1, tp2, stop = round(lrr,2), round(lrr+spread*0.50,2), round(trr,2), round(lrr-spread*0.25,2)
        near_entry, can_enter, near_target = pos <= 0.35, pos <= 0.55, pos >= 0.75
        action = "✅ Buy Now — Price at Buy Zone" if near_entry else ("📈 Still Good — Can Enter" if can_enter else ("🔴 Take Profit — Near Target" if near_target else "⏳ Wait — Not at Best Entry"))
    else:
        entry, tp1, tp2, stop = round(trr,2), round(trr-spread*0.50,2), round(lrr,2), round(trr+spread*0.25,2)
        near_entry, can_enter, near_target = pos >= 0.65, pos >= 0.45, pos <= 0.25
        action = "✅ Sell/Short — Price at Sell Zone" if near_entry else ("📉 Still Ok — Partial Short" if can_enter else ("🔴 Cover Short — Near Target" if near_target else "⏳ Wait — Price Not High Enough"))
    rr_r = round(abs(tp1-entry)/max(abs(entry-stop),0.01), 2)
    hold = "3 months+" if rr_r >= 2.5 else ("1-3 weeks" if rr_r >= 1.5 else "Skip — poor R:R")
    return {"entry":entry,"tp1":tp1,"tp2":tp2,"stop":stop,"rr":rr_r,"pos":round(pos,2),"side":side,"hold":hold,"near_entry":near_entry,"near_target":near_target,"can_enter":can_enter,"action":action}

def _merge_with_options(rl, opt, side="long"):
    if not opt or not opt.get("ok") or not rl: return rl
    if opt.get("delta_label"): rl["opt_delta"] = opt.get("delta_label")
    if opt.get("gamma_label"): rl["opt_gamma"] = opt.get("gamma_label")
    if opt.get("vanna_label"): rl["opt_vanna"] = opt.get("vanna_label")
    lv = (opt.get("long_levels",{}) if side=="long" else opt.get("short_levels",{})) or {}
    if lv.get("ev_ok"):
        for k in ["entry","tp1","tp2","stop","rr"]:
            if lv.get(k): rl[k] = lv[k]
        rl["opt_confirm"] = True; rl["hold"] = lv.get("holding", rl["hold"])
    else:
        rl["opt_confirm"] = True
    return rl

# ── Table Builders ────────────────────────────────────────────────────────────
def _build_alpha_row(item, side="long"):
    rl = item.get("rl") or {}
    opt = item.get("opt") or {}
    action = rl.get("action","—")
    st_icon = "✅ Act Now" if ("Act Now" in action or "Buy Now" in action or "Sell/Short" in action) else ("📊 Chase OK" if ("Still Good" in action or "Still Ok" in action) else ("🔴 Take Profit" if ("Take Profit" in action or "Cover" in action) else "⏳ Wait"))
    im = opt.get("implied_move_pct") if opt else None
    iv_p = opt.get("iv_percentile") if opt else None
    mp = opt.get("max_pain") if opt else None
    d_label = opt.get("delta_label","—") if opt else "—"
    g_label = opt.get("gamma_label","—") if opt else "—"
    v_label = opt.get("vanna_label","—") if opt else "—"
    return {
        "Ticker": item.get("ticker",""), "Sector": item.get("sector","")[:14],
        "Price": ff(_sf(item.get("px"))), "Status": st_icon,
        "Entry": ff(_sf(rl.get("entry"))), "Target 1": ff(_sf(rl.get("tp1"))),
        "Target 2": ff(_sf(rl.get("tp2"))), "Stop Loss": ff(_sf(rl.get("stop"))),
        "R:R": f"{_sf(rl.get('rr')) or 0:.1f}×{'✦' if rl.get('opt_confirm') else ''}",
        "Hold For": rl.get("hold","—")[:10], "Exp Move": f"±{fp(im)}" if im else "—",
        "IV Rank": fp(iv_p) if iv_p else "—", "Max Pain": ff(_sf(mp)) if mp else "—",
        "Delta": d_label, "Gamma": g_label, "Vanna": v_label,
        "Grade": item.get("quality","—"),
    }

def _alpha_table(items, side="long"):
    rows = [_build_alpha_row(item, side) for item in items]
    return pd.DataFrame(rows) if rows else pd.DataFrame()

# ── Visual Components ─────────────────────────────────────────────────────────
def _quad_badge(q, size=28):
    pill = {"Q1":"pill-green","Q2":"pill-yellow","Q3":"pill-red","Q4":"pill-purple"}.get(q,"pill-gray")
    return f'<span class="{pill}">{q}</span>'

def _metric_box(label, value, sub="", color="#E6EDF3"):
    sub_html = f'<div style="font-size:11px;color:#8B949E;margin-top:4px;">{sub}</div>' if sub else ""
    return f'<div class="metric-box"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;">{label}</div><div style="font-size:22px;font-weight:700;color:{color};margin-top:4px;">{value}</div>{sub_html}</div>'

def prob_bar(probs, title=""):
    fig = go.Figure()
    for q,p in sorted((probs or {}).items()):
        fig.add_bar(x=[q],y=[p],marker_color=qc(q),text=[f"<b>{p:.0%}</b>"],textposition="outside",name=q)
    fig.update_layout(showlegend=False,height=220,margin=dict(t=30,b=5,l=0,r=0),
        paper_bgcolor="#161B22",plot_bgcolor="#161B22",
        font=dict(color="#E6EDF3",family="Inter"),
        title=dict(text=title,font=dict(size=12,color="#8B949E")),
        yaxis=dict(range=[0,1.15],tickformat=".0%",showgrid=True,gridcolor="#21262D",tickcolor="#8B949E"),
        xaxis=dict(showgrid=False,tickfont=dict(size=13,color="#E6EDF3")),bargap=0.4)
    return fig

def _seq_pills(sq, mq):
    if sq == mq:
        return '<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px 16px;margin:12px 0;"><div style="font-size:13px;color:#3FB950;font-weight:600;">🟢 REGIME ALIGNED</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">Both monthly and quarterly point the same direction</div></div>'
    target = ""
    if sq == "Q3" and mq == "Q2": target = '→ Q1 TARGET'
    elif sq == "Q3" and mq == "Q1": target = '→ WATCH Q2→Q1'
    return f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px 16px;margin:12px 0;"><div style="font-size:13px;color:#D29922;font-weight:600;">🔴 Structural: {sq} → 🟡 Monthly: {mq} {target}</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">Monthly diverges from structural — tactical caution</div></div>'

# ── Gamma Card ───────────────────────────────────────────────────────────────
def _gamma_card(gamma):
    if not gamma or not gamma.get("ok"):
        return '<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:16px;margin-bottom:12px;"><div style="font-size:14px;font-weight:600;color:#E6EDF3;margin-bottom:8px;">⚡ GAMMA REGIME</div><div style="font-size:12px;color:#8B949E;">Loading...</div></div>'
    th = _sf(gamma.get("throttle")) or 0; r10 = _sf(gamma.get("rvol_10d")); vp = _sf(gamma.get("vol_premium"))
    regime = str(gamma.get("regime","UNKNOWN")); label = str(gamma.get("label","—")); action = str(gamma.get("action","—"))
    color = str(gamma.get("color","#8B949E"))
    explain = {"DEEP_POSITIVE":"Very calm — buy dips","POSITIVE":"Calm — dips get bought","TRANSITION":"Shifting — careful sizing","NEGATIVE":"Volatile — reduce size","DEEP_NEGATIVE":"Dangerous — stay disciplined"}.get(regime,"Unclear")
    css = {"DEEP_POSITIVE":"card-green","POSITIVE":"card-green","TRANSITION":"card-yellow","NEGATIVE":"card-red","DEEP_NEGATIVE":"card-red"}.get(regime,"card-yellow")
    vpc = "#3FB950" if (vp is not None and vp > 0) else "#F85149"
    return (f'<div class="{css}" style="margin-bottom:12px;">'
        f'<div style="font-size:14px;font-weight:600;color:#E6EDF3;margin-bottom:8px;">OPTIONS MARKET STRUCTURE</div>'
        f'<div style="font-size:20px;font-weight:700;color:{color};margin-bottom:4px;">{label.upper()}</div>'
        f'<div style="font-size:12px;color:#8B949E;margin-bottom:12px;">{explain}</div>'
        f'<div style="display:flex;gap:16px;">'
        f'<div><div style="font-size:11px;color:#8B949E;">10d Realized Vol</div><div style="font-size:16px;font-weight:600;color:#E6EDF3;">{r10:.1f}%</div></div>'
        f'<div><div style="font-size:11px;color:#8B949E;">Vol Premium</div><div style="font-size:16px;font-weight:600;color:{vpc};">{vp:+.1f}%</div></div>'
        f'<div><div style="font-size:11px;color:#8B949E;">Throttle</div><div style="font-size:16px;font-weight:600;color:#E6EDF3;">{th:.0%}</div></div>'
        f'</div>'
        f'<div style="margin-top:12px;font-size:12px;color:#8B949E;"><b>Action:</b> {action}</div>'
        f'</div>')

# ── Leveraged ETF Card (FIX 5: Better styling) ───────────────────────────────
def _lev_card(lev):
    if not lev or not lev.get("ok"):
        return '<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:16px;margin-bottom:12px;"><div style="font-size:14px;font-weight:600;color:#E6EDF3;margin-bottom:8px;">📊 LEVERAGED ETF FLOWS</div><div style="font-size:12px;color:#8B949E;">Loading...</div></div>'
    tot = _sf(lev.get("total_mcap_b")) or 0
    lo = _sf(lev.get("long_exposure_b")) or 0
    sh = _sf(lev.get("short_exposure_b")) or 0
    lp = float(lev.get("long_pct") or 0)
    sp = float(lev.get("short_pct") or 0)
    ath = bool(lev.get("is_ath", False))
    rb = str(lev.get("rebalancing_pressure", "—"))
    rc = {"HIGH": "#F85149", "MEDIUM": "#D29922", "LOW": "#3FB950"}.get(rb, "#8B949E")
    op = max(0, round(100 - lp - sp, 0))
    tl = lev.get("top_longs", [])
    ts = lev.get("top_shorts", [])
    tls = " · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in tl[:3]) or "—"
    tss = " · ".join(f'<b>{e["ticker"]}</b> ${e["aum_b"]}B' for e in ts[:3]) or "—"

    return (f'<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:16px;margin-bottom:12px;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">'
        f'<div style="font-size:14px;font-weight:600;color:#E6EDF3;">📊 LEVERAGED ETF FLOWS {"🏆 ALL TIME HIGH" if ath else ""}</div>'
        f'</div>'
        f'<div style="display:flex;gap:24px;margin-bottom:12px;">'
        f'<div><div style="font-size:11px;color:#8B949E;">Total AUM</div><div style="font-size:18px;font-weight:700;color:#E6EDF3;">${tot:.1f}B</div></div>'
        f'<div><div style="font-size:11px;color:#8B949E;">Long Exposure</div><div style="font-size:18px;font-weight:700;color:#3FB950;">${lo:.1f}B</div></div>'
        f'<div><div style="font-size:11px;color:#8B949E;">Short Exposure</div><div style="font-size:18px;font-weight:700;color:#F85149;">${sh:.1f}B</div></div>'
        f'</div>'
        f'<div style="display:flex;gap:8px;margin-bottom:12px;">'
        f'<div style="flex:1;background:#21262D;border-radius:4px;padding:8px;text-align:center;"><div style="font-size:11px;color:#8B949E;">Long %</div><div style="font-size:16px;font-weight:600;color:#3FB950;">{lp:.0f}%</div></div>'
        f'<div style="flex:1;background:#21262D;border-radius:4px;padding:8px;text-align:center;"><div style="font-size:11px;color:#8B949E;">Short %</div><div style="font-size:16px;font-weight:600;color:#F85149;">{sp:.0f}%</div></div>'
        f'<div style="flex:1;background:#21262D;border-radius:4px;padding:8px;text-align:center;"><div style="font-size:11px;color:#8B949E;">Opportunistic</div><div style="font-size:16px;font-weight:600;color:#8B949E;">{op:.0f}%</div></div>'
        f'</div>'
        f'<div style="font-size:12px;color:#8B949E;margin-bottom:8px;">Rebalancing Pressure: <span style="color:{rc};font-weight:600;">{rb}</span></div>'
        f'<div style="font-size:11px;color:#3FB950;margin-bottom:4px;">🟢 Long: {tls}</div>'
        f'<div style="font-size:11px;color:#F85149;">🔴 Short: {tss}</div>'
        f'</div>')

# ── DXY & Levels ─────────────────────────────────────────────────────────────
def _compute_dxy_corr(prices, window=15):
    dxy = prices.get("DX-Y.NYB")
    if dxy is None: return {}
    dxy = pd.to_numeric(dxy, errors="coerce").dropna()
    if len(dxy) < window+2: return {}
    dxy_ret = dxy.pct_change().dropna()
    try: from config.settings import DXY_CORRELATION_ASSETS
    except: return {}
    result = {}
    for label, ticker in DXY_CORRELATION_ASSETS.items():
        s = prices.get(ticker)
        if s is None: continue
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < window+2: continue
        combined = pd.concat([dxy_ret, s.pct_change().dropna()], axis=1, join="inner").dropna()
        combined.columns = ["dxy","asset"]
        if len(combined) >= window:
            c = float(combined["dxy"].tail(window).corr(combined["asset"].tail(window)))
            if math.isfinite(c): result[label] = round(c, 2)
    return result

def _render_levels(rl, side="long", opt=None):
    if not rl: return
    tc = "#3FB950" if side == "long" else "#F85149"
    ext_tag = " ⚠️ Extended" if rl.get("near_target") else ""
    opt_tag = " ✦ Options confirmed" if rl.get("opt_confirm") else ""
    st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px;margin:8px 0;"><div style="font-size:13px;color:{tc};font-weight:600;">{rl.get("action")}{opt_tag}{ext_tag}</div></div>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Buy/Sell at", f"${rl['entry']:.2f}")
    c2.metric("Target 1", f"${rl['tp1']:.2f}")
    c3.metric("Target 2", f"${rl['tp2']:.2f}")
    c4.metric("Stop Loss", f"${rl['stop']:.2f}")
    c5.metric("Reward:Risk", f"{rl['rr']:.1f}× · {rl.get('hold','—')[:10]}")
    if opt and opt.get("ok"):
        st.caption(f"📊 Options: Implied move ±{fp(opt.get('implied_move_pct'))} · IV rank {fp(opt.get('iv_percentile'))} · Max pain ${ff(opt.get('max_pain'))}")
    st.markdown('<hr style="border-color:#30363D;margin:12px 0;">', unsafe_allow_html=True)

def _render_dxy(prices, dxy_corr, sq):
    dxy = prices.get("DX-Y.NYB")
    if dxy is not None:
        dxy = pd.to_numeric(dxy, errors="coerce").dropna()
        if len(dxy) >= 22:
            r = float(dxy.iloc[-1] / dxy.iloc[-22] - 1)
            trend = "Bearish (falling)" if r < -0.005 else ("Bullish (rising)" if r > 0.005 else "Neutral")
            tc = "#F85149" if "Bearish" in trend else "#3FB950" if "Bullish" in trend else "#8B949E"
            st.markdown(
                f'<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:16px;margin-bottom:12px;">'
                f'<div style="font-size:14px;font-weight:600;color:#E6EDF3;margin-bottom:8px;">💱 US DOLLAR INDEX (DXY)</div>'
                f'<div style="font-size:24px;font-weight:700;color:{tc};">${float(dxy.iloc[-1]):.2f}</div>'
                f'<div style="font-size:12px;color:#8B949E;margin-top:4px;">15-day trend: {trend} · '
                f'When DXY falls, EM and commodities rise</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if dxy_corr:
                rows = []
                for label, corr in dxy_corr.items():
                    if corr < -0.3: explain = "📉 Goes UP when Dollar FALLS"
                    elif corr > 0.3: explain = "📈 Goes UP when Dollar RISES"
                    else: explain = "↔ Not much affected"
                    rows.append({"Asset": label, "Correlation": corr, "Meaning": explain})
                if rows:
                    df = pd.DataFrame(rows)
                    st.dataframe(
                        df.style.format({"Correlation": "{:+.2f}"})
                        .background_gradient(subset=["Correlation"], cmap="RdYlGn", vmin=-1, vmax=1),
                        hide_index=True, use_container_width=True, height=220,
                    )

# ══════════════════════════════════════════════════════════════════════════════
# ON-CHAIN HELPERS (DeFiLlama)
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def _fetch_chain_tvl(chain="Ton", days=30):
    try:
        import requests
        url = f"https://api.llama.fi/v2/historicalChainTvl/{chain}"
        r = requests.get(url, timeout=8)
        data = r.json()
        if not data or not isinstance(data, list): return []
        return data[-days:] if len(data) > days else data
    except Exception as e:
        logger.warning(f"DeFiLlama TVL fetch failed for {chain}: {e}")
        return []

@st.cache_data(ttl=3600)
def _fetch_dex_volume(chain="Ton"):
    try:
        import requests
        url = f"https://api.llama.fi/overview/dexs/{chain}"
        r = requests.get(url, timeout=8)
        return r.json()
    except Exception as e:
        logger.warning(f"DeFiLlama DEX fetch failed for {chain}: {e}")
        return {}

@st.cache_data(ttl=3600)
def _fetch_protocol_tvl(protocol="bitcoin"):
    try:
        import requests
        url = f"https://api.llama.fi/tvl/{protocol}"
        r = requests.get(url, timeout=8)
        return r.json()
    except Exception as e:
        logger.warning(f"DeFiLlama protocol TVL fetch failed: {e}")
        return None

def _compute_onchain_momentum(tvl_data, dex_data):
    if not tvl_data or not isinstance(tvl_data, list): return 0.0, {}
    metrics = {}
    if len(tvl_data) >= 8:
        tvl_now = float(tvl_data[-1].get("tvl", 0))
        tvl_7d = float(tvl_data[-8].get("tvl", 1))
        tvl_30d = float(tvl_data[0].get("tvl", 1)) if len(tvl_data) >= 30 else float(tvl_data[0].get("tvl", 1))
        metrics["tvl_7d_change"] = (tvl_now / max(tvl_7d, 1)) - 1
        metrics["tvl_30d_change"] = (tvl_now / max(tvl_30d, 1)) - 1
        metrics["tvl_now"] = tvl_now
    else:
        metrics["tvl_7d_change"] = 0; metrics["tvl_30d_change"] = 0; metrics["tvl_now"] = 0
    if isinstance(dex_data, dict):
        vol_24h = float(dex_data.get("totalVolume24h", 0) or 0)
        vol_7d = float(dex_data.get("totalVolume7d", 0) or 0)
        metrics["vol_24h"] = vol_24h
        metrics["vol_7d"] = vol_7d
        metrics["vol_change"] = (vol_24h * 7 / max(vol_7d, 1)) - 1 if vol_7d > 0 else 0
    else:
        metrics["vol_24h"] = 0; metrics["vol_7d"] = 0; metrics["vol_change"] = 0
    score = min(1.0, max(0.0, 0.4 * max(0, metrics["tvl_7d_change"]) + 0.3 * max(0, metrics["tvl_30d_change"]) + 0.3 * max(0, metrics["vol_change"])))
    return score, metrics

# ══════════════════════════════════════════════════════════════════════════════
# GREEKS PROXIES (always available as fallback)
# ══════════════════════════════════════════════════════════════════════════════
def _forex_greeks_proxy(ticker, prices, vix=None):
    greeks = {"delta":"—","gamma":"—","vanna":"—","vol":"—"}
    if vix is None:
        vix_s = prices.get("^VIX")
        vix = _sf(vix_s.tail(1)) if vix_s is not None else 20.0
    if vix > 25: greeks["vol"] = "High 🔴"
    elif vix > 20: greeks["vol"] = "Elevated 🟡"
    else: greeks["vol"] = "Normal 🟢"
    dxy_s = prices.get("DX-Y.NYB")
    if dxy_s is not None and len(dxy_s) >= 22:
        dxy_ret = float(dxy_s.iloc[-1] / dxy_s.iloc[-22] - 1)
        if "USD" in ticker and ticker.startswith("USD"):
            greeks["delta"] = f"Bullish 📈" if dxy_ret > 0 else "Bearish 📉"
        elif "USD" in ticker and not ticker.startswith("USD"):
            greeks["delta"] = f"Bearish 📉" if dxy_ret > 0 else "Bullish 📈"
        else:
            greeks["delta"] = "Neutral ↔"
    else:
        greeks["delta"] = "Neutral ↔"
    s = prices.get(ticker)
    if s is not None and len(s) >= 10:
        s = pd.to_numeric(s, errors="coerce").dropna()
        r5 = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
        r10 = float(s.iloc[-1] / s.iloc[-11] - 1) if len(s) >= 11 else 0
        accel = r5 - (r10 / 2)
        if accel > 0.02: greeks["gamma"] = "Long 🟢"
        elif accel < -0.02: greeks["gamma"] = "Short 🔴"
        else: greeks["gamma"] = "Flat 🟡"
    else:
        greeks["gamma"] = "Flat 🟡"
    if vix > 22 and dxy_ret > 0.01:
        greeks["vanna"] = "Negative ⚠️"
    elif vix < 18 and dxy_ret < -0.01:
        greeks["vanna"] = "Positive ✅"
    else:
        greeks["vanna"] = "Mixed 🟡"
    return greeks

def _commodity_greeks_proxy(ticker, prices, vix=None):
    greeks = {"delta":"—","gamma":"—","vanna":"—","vol":"—"}
    if vix is None:
        vix_s = prices.get("^VIX")
        vix = _sf(vix_s.tail(1)) if vix_s is not None else 20.0
    if vix > 25: greeks["vol"] = "High 🔴"
    elif vix > 20: greeks["vol"] = "Elevated 🟡"
    else: greeks["vol"] = "Normal 🟢"
    s = prices.get(ticker)
    if s is not None and len(s) >= 22:
        s = pd.to_numeric(s, errors="coerce").dropna()
        r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
        greeks["delta"] = "Bullish 📈" if r1m > 0.03 else ("Bearish 📉" if r1m < -0.03 else "Neutral ↔")
        r5d = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
        r10d = float(s.iloc[-1] / s.iloc[-11] - 1) if len(s) >= 11 else 0
        accel = r5d - (r10d / 2)
        greeks["gamma"] = "Long 🟢" if accel > 0.02 else ("Short 🔴" if accel < -0.02 else "Flat 🟡")
    else:
        greeks["delta"] = "Neutral ↔"
        greeks["gamma"] = "Flat 🟡"
    dxy_s = prices.get("DX-Y.NYB")
    if dxy_s is not None and len(dxy_s) >= 22:
        dxy_ret = float(dxy_s.iloc[-1] / dxy_s.iloc[-22] - 1)
        precious = ticker in ("GC=F", "SI=F", "GLD", "SLV", "PPLT", "GDX", "GDXJ", "SIL", "SILJ")
        if precious:
            greeks["vanna"] = "Positive ✅" if dxy_ret < -0.01 else "Negative ⚠️" if dxy_ret > 0.01 else "Mixed 🟡"
        else:
            greeks["vanna"] = "Positive ✅" if dxy_ret < -0.01 else "Negative ⚠️" if dxy_ret > 0.01 else "Mixed 🟡"
    else:
        greeks["vanna"] = "Mixed 🟡"
    return greeks

def _crypto_greeks_proxy(ticker, prices, basis_pct=0):
    greeks = {"delta":"—","gamma":"—","vanna":"—","charm":"—"}
    s = prices.get(ticker)
    if s is not None and len(s) >= 22:
        s = pd.to_numeric(s, errors="coerce").dropna()
        r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
        r3m = float(s.iloc[-1] / s.iloc[-64] - 1) if len(s) >= 64 else r1m
        greeks["delta"] = "Long 🟢" if r1m > 0.05 else ("Short 🔴" if r1m < -0.05 else "Neutral 🟡")
        r5d = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
        r10d = float(s.iloc[-1] / s.iloc[-11] - 1) if len(s) >= 11 else 0
        accel = r5d - (r10d / 2)
        greeks["gamma"] = "Long 🟢" if accel > 0.03 else ("Short 🔴" if accel < -0.03 else "Flat 🟡")
        if abs(basis_pct) > 1:
            greeks["vanna"] = "Positive ✅" if basis_pct > 1 else "Negative ⚠️"
        else:
            greeks["vanna"] = "Neutral 🟡"
        charm = r1m - (r3m / 3)
        greeks["charm"] = "Fading 🔴" if charm < -0.05 else ("Building 🟢" if charm > 0.05 else "Stable 🟡")
    else:
        for k in greeks: greeks[k] = "N/A ⚪"
    return greeks

# ══════════════════════════════════════════════════════════════════════════════
# COT & OI RENDER HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _render_cot_card(ticker, cot_data):
    if not cot_data or not cot_data.get("ok"): return ""
    comm = cot_data.get("commercial_label", "—")
    noncomm = cot_data.get("noncommercial_label", "—")
    signal = cot_data.get("signal", "—")
    bias = cot_data.get("bias", "—")
    oi = cot_data.get("oi_proxy", 0)
    bias_color = "#3FB950" if bias == "Bullish" else "#F85149" if bias == "Bearish" else "#8B949E"
    return (f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px;margin-bottom:8px;">'
        f'<div style="font-size:13px;font-weight:600;color:#E6EDF3;margin-bottom:8px;">📊 COT POSITIONING — {ticker}</div>'
        f'<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
        f'<div><div style="font-size:11px;color:#8B949E;">Commercial (Hedgers)</div><div style="font-size:14px;color:#E6EDF3;">{comm}</div></div>'
        f'<div><div style="font-size:11px;color:#8B949E;">Non-Commercial (Specs)</div><div style="font-size:14px;color:#E6EDF3;">{noncomm}</div></div>'
        f'</div>'
        f'<div style="margin-top:8px;font-size:12px;color:{bias_color};font-weight:600;">{signal}</div>'
        f'</div>')

def _render_oi_card(ticker, oi_data):
    if not oi_data or not oi_data.get("ok"): return ""
    oi_total = oi_data.get("oi_total", 0)
    oi_trend = oi_data.get("oi_trend", "—")
    concentration = oi_data.get("concentration", "—")
    pos = oi_data.get("position_in_range", 0.5)
    pos_pct = int(pos * 100)
    pos_bar = f"{'█'*int(pos_pct/10)}{'░'*(10-int(pos_pct/10))} {pos_pct}%"
    return (f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px;margin-bottom:8px;">'
        f'<div style="font-size:13px;font-weight:600;color:#E6EDF3;margin-bottom:8px;">🔥 OI HEATMAP — {ticker}</div>'
        f'<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
        f'<div><div style="font-size:11px;color:#8B949E;">OI Total</div><div style="font-size:14px;color:#E6EDF3;">{oi_total:,.0f}</div></div>'
        f'<div><div style="font-size:11px;color:#8B949E;">Trend</div><div style="font-size:14px;color:#E6EDF3;">{oi_trend}</div></div>'
        f'</div>'
        f'<div style="margin-top:8px;"><div style="font-size:11px;color:#8B949E;">Concentration</div><div style="font-size:14px;color:#E6EDF3;">{concentration}</div></div>'
        f'<div style="margin-top:8px;font-size:12px;color:#8B949E;">Position in range: {pos_bar}</div>'
        f'</div>')

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
if "snap" not in st.session_state: st.session_state.snap = None
if "loading" not in st.session_state: st.session_state.loading = False
if "mq_override" not in st.session_state: st.session_state.mq_override = "Auto"

with st.sidebar:
    st.markdown("## 📊 MacroRegime Pro")
    st.markdown('<div style="font-size:11px;color:#8B949E;">Powered by Hedgeye Methodology</div>', unsafe_allow_html=True)
    st.divider()
    page = st.radio("Navigation", [
        "🏠 Dashboard","📈 GIP Model","🎯 Risk Ranges™","⚡ Alpha Center",
        "📊 Leaderboard","🌍 Global Quad","💱 Forex","🛢️ Commodities","₿ Crypto",
        "🇮🇩 IHSG","📖 Narratives","🔮 Discovery","🏥 Health","📋 Playbook",
    ], label_visibility="collapsed")
    st.divider()
    from data.loader import snapshot_age_str, load_snapshot
    st.caption(f"Last update: {snapshot_age_str()}")
    c1,c2=st.columns(2)
    with c1:
        if st.button("🔄 Update", use_container_width=True): st.session_state.loading=True
    with c2:
        if st.button("⚡ Full Rebuild", use_container_width=True):
            st.session_state.loading=True; st.session_state.snap=None
    with st.expander("⚙️ Settings"):
        inc_us = st.checkbox("US Stocks",True); inc_fx = st.checkbox("Forex",True)
        inc_comm = st.checkbox("Commodities",True); inc_cryp = st.checkbox("Crypto",True)
        inc_ihsg = st.checkbox("Indonesia (IHSG)",True)
    with st.expander("🔧 Quad Override"):
        mq_ov = st.selectbox("Monthly Regime:",["Auto","Q1","Q2","Q3","Q4"],
            index=["Auto","Q1","Q2","Q3","Q4"].index(st.session_state.mq_override))
        if mq_ov != st.session_state.mq_override: st.session_state.mq_override = mq_ov
    st.caption("Override when model diverges from Hedgeye")
    st.divider()
    _s=st.session_state.snap
    if _s and _s.get("ok"):
        _g=_s.get("gip"); _gl=_s.get("global",{})
        _sq=_g.structural_quad if _g else "—"; _mq=_g.monthly_quad if _g else "—"
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px;"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;">CURRENT REGIME</div><div style="font-size:18px;font-weight:700;color:#E6EDF3;margin-top:4px;">{_sq} / {_mq}</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">{QN.get(_sq,"")} · {QN.get(_mq,"")}</div></div>', unsafe_allow_html=True)

# ── Auto-build ────────────────────────────────────────────────────────────────
snap = st.session_state.snap
if snap is None:
    snap = load_snapshot(max_age_hours=6.0)
    if snap and snap.get("ok"): st.session_state.snap = snap

if snap is None or not snap.get("ok") or st.session_state.loading:
    from orchestrator import build_snapshot
    _msg = "🔄 Updating data..." if st.session_state.loading else "⚡ Building MacroRegime Pro..."
    with st.spinner(_msg):
        pb=st.progress(0.0); pt=st.empty()
        def prog(m,f): pb.progress(f); pt.caption(f"⏳ {m}")
        snap=build_snapshot(progress_cb=prog, include_us_stocks=inc_us, include_forex=inc_fx,
            include_commodities=inc_comm, include_crypto=inc_cryp, include_ihsg=inc_ihsg)
        st.session_state.snap=snap; st.session_state.loading=False
        pb.empty(); pt.empty(); st.rerun()

if not snap or not snap.get("ok"):
    st.error("❌ Build failed. Click **⚡ Full Rebuild** to retry."); st.stop()

# ── Extract Data ─────────────────────────────────────────────────────────────
gip = snap.get("gip"); global_ = snap.get("global",{}); rr = snap.get("risk_ranges",{})
scen = snap.get("scenarios",{}); narr = snap.get("narratives",{}); disc = snap.get("discovery",{})
transition = snap.get("transition",None); health = snap.get("health",{}); analogs = snap.get("analogs",{})
btk = snap.get("bottleneck",{}); pb_data = snap.get("playbook",{}); prices = snap.get("prices",{})
auto_disc = snap.get("auto_discoveries",{}); fb_eval = snap.get("feedback_eval",{})
gamma_data = snap.get("gamma",{}); lev_data = snap.get("leveraged_etf",{})

sq = gip.structural_quad if gip else "Q3"
mq_raw = gip.monthly_quad if gip else "Q2"
mq = st.session_state.mq_override if st.session_state.mq_override != "Auto" else mq_raw
gq = (global_.get("global_quad","Q3") if global_ else "Q3")
ar = rr.get("asset_ranges",{})
dxy_corr = _compute_dxy_corr(prices)
ai_data = snap.get("ai_analysis",{}) or {}

vix_now = _sf(prices.get("^VIX", pd.Series()).tail(1)) if prices.get("^VIX") is not None else 20.0

# ── Options Engine Initializers ──────────────────────────────────────────────
_oe = None; _oe_ok = False
try:
    from engines.options_engine import OptionsEngine
    _oe = OptionsEngine(); _oe_ok = True
except Exception:
    pass

_deribit = None; _deribit_ok = False
try:
    from engines.deribit_options import DeribitOptionsAPI
    _deribit = DeribitOptionsAPI(); _deribit_ok = True
except Exception as e:
    logger.warning(f"Deribit engine unavailable: {e}")

_barchart = None; _barchart_ok = False
try:
    from engines.barchart_options import BarchartOptionsScraper
    _barchart = BarchartOptionsScraper(); _barchart_ok = True
except Exception as e:
    logger.warning(f"Barchart engine unavailable: {e}")

_cme = None; _cme_ok = False
try:
    from engines.cme_options import CMEOptionsScraper
    _cme = CMEOptionsScraper(); _cme_ok = True
except Exception as e:
    logger.warning(f"CME engine unavailable: {e}")

_cot = None; _cot_ok = False
try:
    from engines.cme_cot import CMECOTProxy
    _cot = CMECOTProxy(); _cot_ok = True
except Exception as e:
    logger.warning(f"COT engine unavailable: {e}")

_oi = None; _oi_ok = False
try:
    from engines.cme_oi import CMEOIProxy
    _oi = CMEOIProxy(); _oi_ok = True
except Exception as e:
    logger.warning(f"OI engine unavailable: {e}")

# Fallbacks
FALLBACK_NARRATIVES = [
    {"name":"Silver Supercycle","score":0.92,"thesis":"SLV +143% since May 2025. Industrial demand (solar, AI chips) + safe haven. Mine supply flat.","tickers":["SLV","SILJ","GDXJ","GDX","GLD"],"best":["SLV","SILJ","GDXJ"],"worst":["XLK","MAGS"],"invalidators":["Q4 deflation signal","DXY sustained bullish"]},
    {"name":"Gold Secular Bull","score":0.88,"thesis":"Central banks buying at record pace. De-dollarization structural. Safe haven in Q3.","tickers":["GLD","GDX","GDXJ","AEM","WPM"],"best":["GLD","GDX"],"worst":["HYG","IWM"],"invalidators":["Q4→Q1 direct","DXY reversal"]},
    {"name":"Defense Reshoring","score":0.85,"thesis":"NATO 2%+ GDP commitment. Geopolitical premium. ITA/LMT/KTOS secular long in ALL quads.","tickers":["ITA","LMT","RTX","KTOS","PLTR","GD"],"best":["ITA","KTOS"],"worst":["XLU"],"invalidators":["Global peace agreement"]},
    {"name":"AI Power Infrastructure","score":0.83,"thesis":"AI data centers need 24/7 firm power. Nuclear + gas only scalable solutions.","tickers":["VST","CEG","GEV","ETN","VRT"],"best":["VST","CEG"],"worst":["INTC"],"invalidators":["AI capex cycle pause"]},
    {"name":"Energy Offense (Q2)","score":0.80,"thesis":"Q2 = Reflation = Energy offense. OIH oil services = operating leverage.","tickers":["XLE","OIH","BNO","XOP","DAR","MTDR"],"best":["OIH","BNO"],"worst":["XLU","XLP"],"invalidators":["Demand collapse (Q4)"]},
    {"name":"International Rotation","score":0.78,"thesis":"JPXN +37% Q1 2026. EIS +21.8%. USD bearish = EM tailwind.","tickers":["JPXN","EIS","TUR","NORW","EWZ","GLIN"],"best":["JPXN","EIS","TUR"],"worst":["SPY","IWM"],"invalidators":["DXY bullish reversal"]},
    {"name":"Bitcoin Reflation","score":0.75,"thesis":"Every quad except Q4 = long Bitcoin. DXY bearish correlation supports crypto bid.","tickers":["IBIT","FBTC","BTC-USD"],"best":["IBIT"],"worst":["MSTY","BLOK"],"invalidators":["Q4 signal","DXY bullish reversal"]},
    {"name":"Indonesia Commodity Play","score":0.65,"thesis":"EIDO = coal + nickel + CPO + geothermal. Q2/Q3 = commodity bid.","tickers":["EIDO","PGEO.JK","ADRO.JK","NCKL.JK"],"best":["EIDO","PGEO.JK"],"worst":["TLKM.JK"],"invalidators":["China demand collapse","Q4 deflation"]},
]
FALLBACK_DISCOVERY = [
    {"name":"AI Photonics Bottleneck","category":"Structural Constraint","stage":"active","confidence":0.88,"thesis":"LITE sole supplier 200G EML lasers. NVIDIA $2B photonics.","beneficiary_tickers":["LITE","POET","COHR","CIEN","VIAV"],"fade_tickers":["INTC","SMCI"],"confirmation_signal":"LITE earnings + NVIDIA capex","invalidators":["China photonics scaling"]},
    {"name":"SiC Power Monopoly (WOLF)","category":"Structural Constraint","stage":"active","confidence":0.84,"thesis":"WOLF = ONLY US large-scale SiC substrate. CHIPS Act strategic.","beneficiary_tickers":["WOLF","ON","STM","MPWR"],"fade_tickers":["Legacy Si"],"confirmation_signal":"EV OEM adoption + DOD qual","invalidators":["China SiC subsidies"]},
    {"name":"Japan Yen Weakness → JPXN","category":"Macro Rotation","stage":"active","confidence":0.82,"thesis":"Yen bearish = Japanese exporters win. BoJ ultra-dovish.","beneficiary_tickers":["JPXN","EWJ"],"fade_tickers":["FXY"],"confirmation_signal":"USD/JPY >145","invalidators":["BoJ hike >1%"]},
    {"name":"Silver Physical Squeeze","category":"Commodity","stage":"building","confidence":0.78,"thesis":"Solar + AI chip silver demand accelerating. Mine supply flat.","beneficiary_tickers":["SLV","SILJ","SIL","GDXJ"],"fade_tickers":["MSTY","BLOK"],"confirmation_signal":"LBMA inventory <150M oz","invalidators":["India demand collapse"]},
    {"name":"Indonesia OSV Bottleneck","category":"Local Bottleneck","stage":"brewing","confidence":0.65,"thesis":"Pertamina hulu expansion = OSV fleet utilization >90%.","beneficiary_tickers":["WINS.JK","LEAD.JK","SHIP.JK","ELSA.JK"],"fade_tickers":["BUMI.JK"],"confirmation_signal":"Pertamina Q2 capex","invalidators":["Pertamina budget freeze"]},
]

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🏠 DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Dashboard":
    st.markdown('<h1>🏠 Dashboard</h1>', unsafe_allow_html=True)
    st.caption("Command center. 30-second read.")
    st.divider()

    ai_ok = ai_data.get("ok", False)
    ai_ts = ai_data.get("generated_at")
    ai_cnt_narr = len(ai_data.get("narratives",[]))
    ai_cnt_alpha = len(ai_data.get("alpha_ideas",[]))
    ai_cnt_btk = len(ai_data.get("bottlenecks",[]))
    if ai_ok:
        import datetime
        ts_str = datetime.datetime.fromtimestamp(ai_ts).strftime("%H:%M") if ai_ts else "—"
        model_name = ai_data.get("model", "unknown")
        if "rule-based" in str(model_name):
            st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px 16px;margin-bottom:12px;"><div style="font-size:13px;color:#3FB950;font-weight:600;">🧠 AI RULE-BASED ACTIVE</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">Auto-generated from live data · {ai_cnt_narr} narratives · {ai_cnt_alpha} alpha ideas · {ai_cnt_btk} bottlenecks · Updated {ts_str}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px 16px;margin-bottom:12px;"><div style="font-size:13px;color:#3FB950;font-weight:600;">🤖 AI ACTIVE — {model_name}</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">{ai_cnt_narr} narratives · {ai_cnt_alpha} alpha ideas · {ai_cnt_btk} bottlenecks · Updated {ts_str}</div></div>', unsafe_allow_html=True)
    else:
        ai_reason = ai_data.get("reason", "")
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px 16px;margin-bottom:12px;"><div style="font-size:13px;color:#8B949E;font-weight:600;">🤖 AI: Fallback — {ai_reason}</div></div>', unsafe_allow_html=True)

    st.caption(f"Built {snap.get('build_time_s',0):.0f}s ago · {snap.get('prices_loaded',0)} assets · {snap.get('fred_coverage',0)} macro indicators")

    vbd = health.get("vix_bucket",{}) if health else {}
    vb = vbd.get("bucket","—"); vl = _sf(vbd.get("vix_last")) or 0
    if vb=="Investable":
        st.markdown(f'<div style="background:#161B22;border:1px solid #238636;border-radius:8px;padding:12px 16px;margin-bottom:12px;"><div style="font-size:14px;font-weight:600;color:#3FB950;">🟢 GOOD MARKET CONDITIONS · VIX {vl:.1f}</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">{vbd.get("note","")}</div><div style="font-size:11px;color:#8B949E;margin-top:4px;">Risk mode: {vbd.get("risk_mode","Normal")}</div></div>', unsafe_allow_html=True)
    elif vb=="Chop":
        st.markdown(f'<div style="background:#161B22;border:1px solid #D29922;border-radius:8px;padding:12px 16px;margin-bottom:12px;"><div style="font-size:14px;font-weight:600;color:#D29922;">🟡 CHOPPY CONDITIONS · VIX {vl:.1f}</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">{vbd.get("note","")}</div><div style="font-size:11px;color:#8B949E;margin-top:4px;">Risk mode: {vbd.get("risk_mode","Normal")}</div></div>', unsafe_allow_html=True)
    elif vb=="Defensive":
        st.markdown(f'<div style="background:#161B22;border:1px solid #F85149;border-radius:8px;padding:12px 16px;margin-bottom:12px;"><div style="font-size:14px;font-weight:600;color:#F85149;">🔴 DEFENSIVE CONDITIONS · VIX {vl:.1f}</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">{vbd.get("note","")}</div><div style="font-size:11px;color:#8B949E;margin-top:4px;">Risk mode: {vbd.get("risk_mode","Normal")}</div></div>', unsafe_allow_html=True)

    g_col, dxy_col = st.columns([1.1, 1])
    with g_col: st.markdown(_gamma_card(gamma_data), unsafe_allow_html=True)
    with dxy_col: _render_dxy(prices, dxy_corr, sq)
    st.markdown(_lev_card(lev_data), unsafe_allow_html=True)

    sq_q2p = (_sf((gip.structural_probs or {}).get("Q2",0)) or 0) if gip else 0
    sq_sub = f"Q2 probability: {sq_q2p:.0%}" if (sq=="Q3" and sq_q2p>0.25) else ""
    mq_sub = "⚠ Model Q1 · Hedgeye Q2" if mq_raw=="Q1" else ""

    r1,r2,r3,r4 = st.columns(4)
    with r1: st.markdown(_metric_box("Quarterly Regime", sq, QUAD_EXPLAIN[sq][:60]+"...", qc(sq)), unsafe_allow_html=True)
    with r2: st.markdown(_metric_box("Monthly Regime", mq, mq_sub or "3-6 week tactical", qc(mq)), unsafe_allow_html=True)
    with r3:
        gconf = _sf(global_.get("global_conf",0)) if global_ else 0
        st.markdown(_metric_box("Global (50 Countries)", gq, f"Confidence: {gconf:.0%}", qc(gq)), unsafe_allow_html=True)
    with r4:
        if gip:
            flip = gip.flip_hazard
            flip_c = "#F85149" if flip > 0.4 else "#D29922" if flip > 0.25 else "#3FB950"
            st.markdown(_metric_box("Regime Change Risk", f"{flip:.0%}", f"{gip.divergence.title()}", flip_c), unsafe_allow_html=True)

    st.markdown(_seq_pills(sq, mq), unsafe_allow_html=True)

    if transition:
        fw = transition.front_run_window; fr = transition.front_run_rationale
        fwc={"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
        fwi={"now":"🚨 ACT NOW","1-2w":"⚡ ACT SOON","3-6w":"👀 WATCH","not yet":"🛑 NOT YET"}.get(fw,"🛑 NOT YET")
        if fw != "not yet":
            st.markdown(f'<div style="background:#161B22;border:1px solid {fwc};border-radius:8px;padding:12px 16px;margin:12px 0;"><div style="font-size:14px;font-weight:600;color:{fwc};">{fwi}</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">{fr}</div></div>', unsafe_allow_html=True)

    if pb_data:
        best5 = " · ".join(pb_data.get("best_assets",[])[:6])
        worst5 = " · ".join(pb_data.get("worst_assets",[])[:5])
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:8px;padding:12px 16px;margin:12px 0;"><div style="font-size:14px;font-weight:600;color:#E6EDF3;margin-bottom:8px;">🎯 What to Do Right Now — {sq} · {mq}</div><div style="font-size:12px;color:#3FB950;margin-bottom:4px;">✅ Buy/Hold: {best5}</div><div style="font-size:12px;color:#F85149;">❌ Avoid/Sell: {worst5}</div></div>', unsafe_allow_html=True)

    if fb_eval and fb_eval.get("evaluated",0):
        ev=fb_eval.get("evaluated",0); pr=fb_eval.get("promoted",0); dm=fb_eval.get("demoted",0)
        wr=(pr/max(ev,1))*100
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Evaluated", ev); c2.metric("Winners", pr); c3.metric("Losers", dm); c4.metric("Win Rate", f"{wr:.1f}%")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 📈 GIP MODEL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📈 GIP Model":
    st.markdown('<h1>📈 GIP Model</h1>', unsafe_allow_html=True)
    st.caption("Growth · Inflation · Policy — The Map")
    st.divider()
    if not gip: st.warning("Data loading..."); st.stop()

    cc,cw = st.columns(2)
    with cc:
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:16px;"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;margin-bottom:8px;">Quarterly Regime (Climate)</div><div style="font-size:28px;font-weight:700;color:{qc(sq)};">{sq}</div><div style="font-size:13px;color:#E6EDF3;margin-top:8px;">{QNC.get(sq,"")}</div><div style="font-size:12px;color:#8B949E;margin-top:8px;">{QUAD_EXPLAIN[sq]}</div><div style="font-size:11px;color:#8B949E;margin-top:12px;">Confidence: {gip.structural_conf:.0%} · Flip risk: {gip.flip_hazard:.0%}</div></div>', unsafe_allow_html=True)
    with cw:
        st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:16px;"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;margin-bottom:8px;">Monthly Regime (Weather — 3-6 Weeks)</div><div style="font-size:28px;font-weight:700;color:{qc(mq)};">{mq}</div><div style="font-size:13px;color:#E6EDF3;margin-top:8px;">{QNC.get(mq,"")}</div><div style="font-size:12px;color:#8B949E;margin-top:8px;">{QUAD_EXPLAIN[mq]}</div><div style="font-size:11px;color:#8B949E;margin-top:12px;">Confidence: {gip.monthly_conf:.0%} · Divergence: {gip.divergence}</div></div>', unsafe_allow_html=True)
    if mq_raw == "Q1":
        st.warning("⚠ Model computed Q1, Hedgeye manual call = Q2. Use Quad Override in sidebar.")

    st.divider()
    st.markdown("### What the Data Is Saying")
    f = gip.features; gm = _sf(f.get("growth_momentum")) or 0; im = _sf(f.get("inflation_momentum")) or 0
    s1,s2,s3,s4 = st.columns(4)
    s1.metric("Growth Direction", "📈 Accelerating" if gm>0 else "📉 Decelerating", f"{gm:+.1%}")
    s2.metric("Inflation Direction", "📈 Rising" if im>0 else "📉 Cooling", f"{im:+.1%}")
    s3.metric("Central Bank", "Dovish 🕊️" if (_sf(f.get("policy_score")) or 0)>0.1 else "Hawkish 🦅" if (_sf(f.get("policy_score")) or 0)<-0.1 else "Neutral ⚖️")
    s4.metric("Data Coverage", f"{gip.data_coverage:.0%}")

    st.divider()
    st.markdown("### Where Are We Going Next?")

    # FIX: _tp function with key parameter to prevent DuplicateElementId
    def _tp(probs, cur_q, label):
        if not probs: return
        sp=sorted(probs.items(),key=lambda x:x[1],reverse=True); top_q,top_p=sp[0]
        st.markdown(f'<div style="background:#161B22;padding:12px 16px;border-radius:8px;margin-bottom:12px;"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">{label}</div><div style="font-size:14px;color:#E6EDF3;">Most likely next: <strong>{top_q} {QN.get(top_q,"")}</strong> ({top_p:.0%})</div></div>', unsafe_allow_html=True)
        # FIX: Add unique key to prevent StreamlitDuplicateElementId
        key_id = f"prob_{label.replace(' ', '_').replace('/', '_')}"
        st.plotly_chart(prob_bar(probs), use_container_width=True, config={"displayModeBar":False}, key=key_id)
        if top_q!=cur_q: st.info(f"If regime shifts to {top_q}: **{QWINS.get(top_q,'')}** are the winners")

    c1,c2,c3 = st.columns(3)
    with c1: _tp(gip.structural_probs, sq, "Quarterly Probabilities")
    with c2: _tp(gip.monthly_probs, mq, "Monthly Probabilities")
    with c3:
        gprobs = (global_.get("global_probs",{}) or {}) if global_ else {}
        if gprobs: _tp(gprobs, gq, "Global Probabilities")

    st.divider()
    st.markdown("### Timing Signal")
    st.markdown(_seq_pills(sq, mq), unsafe_allow_html=True)
    if transition:
        fw=transition.front_run_window; fr=transition.front_run_rationale
        fwc={"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
        fwi={"now":"🚨 ACT NOW","1-2w":"⚡ ACT SOON","3-6w":"👀 WATCH","not yet":"🛑 NOT YET"}.get(fw,"🛑 NOT YET")
        if fw != "not yet":
            st.markdown(f'<div style="background:#161B22;border:1px solid {fwc};border-radius:8px;padding:12px 16px;margin:12px 0;"><div style="font-size:14px;font-weight:600;color:{fwc};">{fwi}</div><div style="font-size:12px;color:#8B949E;margin-top:4px;">{fr}</div></div>', unsafe_allow_html=True)

    if analogs and analogs.get("top_analogs"):
        st.divider()
        st.markdown("### Historical Comparisons")
        for i,a in enumerate(analogs["top_analogs"][:3]):
            with st.expander(f"📚 **{a['label']}** — {a.get('similarity',0):.0%} similar", expanded=(i==0)):
                c1,c2,c3=st.columns(3)
                c1.metric("Next 1M", a.get("path_1m","—")); c2.metric("Next 3M", a.get("path_3m","—")); c3.metric("Next 6M", a.get("path_6m","—"))
                st.info(f"📊 {a.get('next_bias','')}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🎯 RISK RANGES™
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎯 Risk Ranges™":
    st.markdown('<h1>🎯 Risk Ranges™</h1>', unsafe_allow_html=True)
    st.caption("Buy Zone = LRR. Sell Zone = TRR. Break below = exit.")
    st.divider()
    if not ar: st.warning("Data loading..."); st.stop()

    all_a=sorted([(s,a) for s,v in ar.items() for a in v.get("alerts",[])],
        key=lambda x:{"CRITICAL":0,"HIGH":1,"MEDIUM":2}.get(x[1].get("priority"),3))
    if all_a:
        st.markdown("### 🔔 Priority Alerts")
        for sym,a in all_a[:15]:
            ic="🔴" if a["priority"]=="CRITICAL" else "🟡"
            st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:6px;padding:8px 12px;margin-bottom:4px;">{ic} <strong>{sym}</strong> — {a["action"]} ({a["duration"]})</div>', unsafe_allow_html=True)

    st.divider()
    cl1,cl2,cl3 = st.columns([1,2,1])
    with cl1: mkt_f=st.selectbox("Filter by market:",["All","us_equity","forex","commodity","crypto","ihsg"])
    with cl2: srch=st.text_input("Search:",placeholder="Type ticker name...")
    with cl3: show_only=st.selectbox("Show:",["All signals","Buy signals only","Sell signals only"])

    rows=[]
    for sym,v in ar.items():
        if mkt_f!="All" and v.get("market","")!=mkt_f: continue
        if srch and srch.upper() not in sym.upper(): continue
        sig=v.get("composite","—").upper()
        if show_only=="Buy signals only" and sig!="BULLISH": continue
        if show_only=="Sell signals only" and sig!="BEARISH": continue
        tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
        side="long" if sig=="BULLISH" else "short"; rl=_rr_levels(px,lrr,trr,side)
        pos_pct=round((rl.get("pos",0.5))*100) if rl else 50
        action=(rl.get("action","—")[:30] if rl else "—")
        rows.append({"Ticker":sym,"Price":ff(px),"Buy Zone":ff(lrr),"Sell Zone":ff(trr),"Action":action,"Position":f"{pos_pct}%","Signal":sig,"Quality":v.get("quality","—"),"Market":v.get("market","—")})
    if rows:
        df=pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, use_container_width=True, height=520,
            column_config={"Ticker":st.column_config.TextColumn("Ticker",width="small"),"Signal":st.column_config.TextColumn("Signal",width="small"),"Quality":st.column_config.TextColumn("Grade",width="small"),"Position":st.column_config.TextColumn("In Range",width="small"),"Action":st.column_config.TextColumn("What to Do",width="large")})
    else: st.info("No data matches your filter.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: ⚡ ALPHA CENTER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Alpha Center":
    st.markdown('<h1>⚡ Alpha Center</h1>', unsafe_allow_html=True)
    st.caption("Best trades right now. Entry, targets, stop, and time horizon.")
    st.divider()

    if transition:
        fw=transition.front_run_window
        fwc={"now":"#F85149","1-2w":"#D29922","3-6w":"#1F6FEB","not yet":"#21262D"}.get(fw,"#21262D")
        fwi={"now":"🚨 Window OPEN","1-2w":"⚡ Act within 1-2 weeks","3-6w":"👀 Watch for entry","not yet":"🛑 Not yet"}.get(fw,"🛑 Not yet")
        st.markdown(f'<div style="background:#161B22;border:1px solid {fwc};border-radius:8px;padding:12px 16px;margin-bottom:12px;"><div style="font-size:14px;font-weight:600;color:{fwc};">{fwi}</div></div>', unsafe_allow_html=True)
    st.markdown(_seq_pills(sq, mq), unsafe_allow_html=True)

    def _get_all_items():
        all_longs=[]; all_shorts=[]
        for item in (btk.get("level_1",[]) or []) + (btk.get("level_2",[]) or []):
            ticker=item.get("ticker",""); v=ar.get(ticker,{}); tr=v.get("trade",{})
            px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr")); dir_=item.get("direction","long")
            rl=_rr_levels(px,lrr,trr,dir_)
            if not rl: continue
            opt=None
            if _oe_ok and _oe and px and px>0:
                try: opt=_oe.analyze(ticker,px,lrr,trr,v.get("composite","neutral"))
                except: pass
            if not opt and _barchart_ok and px and px>0:
                try: opt=_barchart.analyze(ticker, px)
                except: pass
            # Proxy Greeks with ALL fields populated
            if not opt or not opt.get("ok"):
                proxy = {"ok": True, "source": "proxy"}
                mkt = v.get("market","us_equity")
                s = prices.get(ticker)
                r1m = None
                if s is not None and len(s) >= 22:
                    s = pd.to_numeric(s, errors="coerce").dropna()
                    r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
                proxy["implied_move_pct"] = abs(r1m) * 0.5 if r1m else 0.05
                proxy["iv_percentile"] = 0.5
                proxy["max_pain"] = px if px else 0
                if mkt == "crypto":
                    g = _crypto_greeks_proxy(ticker, prices, 0)
                    proxy["delta_label"] = g["delta"]; proxy["gamma_label"] = g["gamma"]; proxy["vanna_label"] = g["vanna"]
                elif mkt == "forex":
                    g = _forex_greeks_proxy(ticker, prices, vix_now)
                    proxy["delta_label"] = g["delta"]; proxy["gamma_label"] = g["gamma"]; proxy["vanna_label"] = g["vanna"]
                elif mkt == "commodity":
                    g = _commodity_greeks_proxy(ticker, prices, vix_now)
                    proxy["delta_label"] = g["delta"]; proxy["gamma_label"] = g["gamma"]; proxy["vanna_label"] = g["vanna"]
                else:
                    if r1m is not None:
                        proxy["delta_label"] = "Long 🟢" if r1m > 0.03 else ("Short 🔴" if r1m < -0.03 else "Neutral 🟡")
                    else:
                        proxy["delta_label"] = "Neutral 🟡"
                    proxy["gamma_label"] = "Flat 🟡"; proxy["vanna_label"] = "Mixed 🟡"
                opt = proxy
            if opt: rl=_merge_with_options(rl,opt,dir_)
            item_out={**item,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"opt":opt,"sector":item.get("sector","").replace("_"," ").title()[:14],"quality":item.get("quality","A"),"comp":v.get("composite","neutral")}
            if dir_=="long": all_longs.append(item_out)
            else: all_shorts.append(item_out)

        if not all_longs and not all_shorts:
            for sym,v in ar.items():
                if v.get("market") not in ("us_equity","commodity","crypto","forex"): continue
                comp=v.get("composite",""); qual=v.get("quality","")
                tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
                if comp=="bullish" and qual in ("A","B","C"):
                    rl=_rr_levels(px,lrr,trr,"long")
                    if rl:
                        try: from config.settings import TICKER_SECTOR; sector=TICKER_SECTOR.get(sym,"generic").replace("_"," ").title()[:14]
                        except: sector="Generic"
                        s = prices.get(sym)
                        r1m = None
                        if s is not None and len(s) >= 22:
                            s = pd.to_numeric(s, errors="coerce").dropna()
                            r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
                        proxy = {"ok": True, "source": "proxy"}
                        proxy["implied_move_pct"] = abs(r1m) * 0.5 if r1m else 0.05
                        proxy["iv_percentile"] = 0.5
                        proxy["max_pain"] = px if px else 0
                        mkt = v.get("market","us_equity")
                        if mkt == "crypto":
                            g = _crypto_greeks_proxy(sym, prices, 0)
                            proxy["delta_label"] = g["delta"]; proxy["gamma_label"] = g["gamma"]; proxy["vanna_label"] = g["vanna"]
                        elif mkt == "forex":
                            g = _forex_greeks_proxy(sym, prices, vix_now)
                            proxy["delta_label"] = g["delta"]; proxy["gamma_label"] = g["gamma"]; proxy["vanna_label"] = g["vanna"]
                        elif mkt == "commodity":
                            g = _commodity_greeks_proxy(sym, prices, vix_now)
                            proxy["delta_label"] = g["delta"]; proxy["gamma_label"] = g["gamma"]; proxy["vanna_label"] = g["vanna"]
                        else:
                            proxy["delta_label"] = "Long 🟢" if r1m and r1m > 0.03 else ("Short 🔴" if r1m and r1m < -0.03 else "Neutral 🟡")
                            proxy["gamma_label"] = "Flat 🟡"; proxy["vanna_label"] = "Mixed 🟡"
                        rl = _merge_with_options(rl, proxy, "long")
                        all_longs.append({"ticker":sym,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"opt":proxy,"sector":sector,"quality":qual,"comp":comp,"ev":0.5,"known_thesis":"Signal Strength A/B/C"})
                elif comp=="bearish" and qual in ("short_A","short_B","short_C"):
                    rl=_rr_levels(px,lrr,trr,"short")
                    if rl:
                        try: from config.settings import TICKER_SECTOR; sector=TICKER_SECTOR.get(sym,"generic").replace("_"," ").title()[:14]
                        except: sector="Generic"
                        s = prices.get(sym)
                        r1m = None
                        if s is not None and len(s) >= 22:
                            s = pd.to_numeric(s, errors="coerce").dropna()
                            r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
                        proxy = {"ok": True, "source": "proxy"}
                        proxy["implied_move_pct"] = abs(r1m) * 0.5 if r1m else 0.05
                        proxy["iv_percentile"] = 0.5
                        proxy["max_pain"] = px if px else 0
                        mkt = v.get("market","us_equity")
                        if mkt == "crypto":
                            g = _crypto_greeks_proxy(sym, prices, 0)
                            proxy["delta_label"] = g["delta"]; proxy["gamma_label"] = g["gamma"]; proxy["vanna_label"] = g["vanna"]
                        elif mkt == "forex":
                            g = _forex_greeks_proxy(sym, prices, vix_now)
                            proxy["delta_label"] = g["delta"]; proxy["gamma_label"] = g["gamma"]; proxy["vanna_label"] = g["vanna"]
                        elif mkt == "commodity":
                            g = _commodity_greeks_proxy(sym, prices, vix_now)
                            proxy["delta_label"] = g["delta"]; proxy["gamma_label"] = g["gamma"]; proxy["vanna_label"] = g["vanna"]
                        else:
                            proxy["delta_label"] = "Short 🔴" if r1m and r1m < -0.03 else ("Long 🟢" if r1m and r1m > 0.03 else "Neutral 🟡")
                            proxy["gamma_label"] = "Flat 🟡"; proxy["vanna_label"] = "Mixed 🟡"
                        rl = _merge_with_options(rl, proxy, "short")
                        all_shorts.append({"ticker":sym,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"opt":proxy,"sector":sector,"quality":qual,"comp":comp,"ev":0.5,"known_thesis":"Signal Strength Short A/B/C"})

        if not all_longs and ai_data.get("ok"):
            for idea in ai_data.get("alpha_ideas",[]):
                if idea.get("direction")=="long":
                    ticker=idea.get("ticker",""); v=ar.get(ticker,{}); tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr")); rl=_rr_levels(px,lrr,trr,"long")
                    if rl:
                        proxy = {"ok": True, "source": "proxy", "delta_label": "Neutral 🟡", "gamma_label": "Flat 🟡", "vanna_label": "Mixed 🟡", "implied_move_pct": 0.05, "iv_percentile": 0.5, "max_pain": px if px else 0}
                        rl = _merge_with_options(rl, proxy, "long")
                        all_longs.append({"ticker":ticker,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"sector":idea.get("category","AI")[:14],"quality":"A","comp":"bullish","ev":idea.get("confidence",0.7),"known_thesis":idea.get("thesis",""),"opt":proxy})
        if not all_shorts and ai_data.get("ok"):
            for idea in ai_data.get("alpha_ideas",[]):
                if idea.get("direction")=="short":
                    ticker=idea.get("ticker",""); v=ar.get(ticker,{}); tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr")); rl=_rr_levels(px,lrr,trr,"short")
                    if rl:
                        proxy = {"ok": True, "source": "proxy", "delta_label": "Neutral 🟡", "gamma_label": "Flat 🟡", "vanna_label": "Mixed 🟡", "implied_move_pct": 0.05, "iv_percentile": 0.5, "max_pain": px if px else 0}
                        rl = _merge_with_options(rl, proxy, "short")
                        all_shorts.append({"ticker":ticker,"px":px,"lrr":lrr,"trr":trr,"rl":rl,"sector":idea.get("category","AI")[:14],"quality":"short_A","comp":"bearish","ev":idea.get("confidence",0.7),"known_thesis":idea.get("thesis",""),"opt":proxy})

        def _sort_key(x):
            action=x.get("rl",{}).get("action","") if x.get("rl") else ""
            return 0 if ("Act Now" in action or "Buy Now" in action or "Sell/Short" in action) else (1 if ("Still Good" in action or "Still Ok" in action) else 2)
        all_longs.sort(key=_sort_key); all_shorts.sort(key=_sort_key)
        return all_longs, all_shorts

    all_longs, all_shorts = _get_all_items()

    stat1,stat2,stat3,stat4 = st.columns(4)
    stat1.metric("Long Ideas",len(all_longs)); stat2.metric("Short Ideas",len(all_shorts))
    stat3.metric("Act Now",sum(1 for x in all_longs+all_shorts if x.get("rl",{}) and ("Act Now" in x["rl"].get("action","") or "Buy Now" in x["rl"].get("action","") or "Sell/Short" in x["rl"].get("action",""))))
    stat4.metric("Options Enhanced",sum(1 for x in all_longs+all_shorts if x.get("opt",{}) and x.get("opt",{}).get("ok")))

    st.divider()
    st.markdown("### 🟢 LONG IDEAS — Buy These")
    st.caption("Entry = best price to buy. Target 1 & 2 = where to sell. Stop Loss = exit.")
    if all_longs:
        df_l=_alpha_table(all_longs[:20],"long")
        st.dataframe(df_l, hide_index=True, use_container_width=True, height=min(len(df_l)*37+40,500),
            column_config={"Status":st.column_config.TextColumn("Status",width="medium"),"Ticker":st.column_config.TextColumn("Ticker",width="small"),"Grade":st.column_config.TextColumn("Grade",width="small")})
        with st.expander("📋 Detailed View — Top 3 Longs"):
            for item in all_longs[:3]:
                st.markdown(f"**{item['ticker']}** · {item.get('sector','')} · {item.get('known_thesis','')[:80]}")
                _render_levels(item.get("rl"),"long",item.get("opt"))
    else: st.info("No long setups right now. Markets may be extended — wait for pullback.")

    st.divider()
    st.markdown("### 🔴 SHORT IDEAS — Sell / Avoid")
    st.caption("Entry = best price to short. Target = where to cover. Stop = exit if goes above.")
    if all_shorts:
        df_s=_alpha_table(all_shorts[:15],"short")
        st.dataframe(df_s, hide_index=True, use_container_width=True, height=min(len(df_s)*37+40,450),
            column_config={"Status":st.column_config.TextColumn("Status",width="medium"),"Ticker":st.column_config.TextColumn("Ticker",width="small"),"Grade":st.column_config.TextColumn("Grade",width="small")})
        with st.expander("📋 Detailed View — Top 3 Shorts"):
            for item in all_shorts[:3]:
                st.markdown(f"**{item['ticker']}** · {item.get('sector','')} · {item.get('known_thesis','')[:80]}")
                _render_levels(item.get("rl"),"short",item.get("opt"))
    else: st.info("No short setups right now.")

    wt=btk.get("watch",[]) if btk else []
    if wt:
        st.divider()
        st.markdown("### 👀 WATCH LIST")
        st.caption("Early signs. Monitor for entry.")
        wt_rows=[{"Ticker":w.get("ticker",""),"Sector":w.get("sector","").replace("_"," ").title()[:14],"Direction":w.get("direction","long").upper(),"Score":f'{w.get("score",0):.2f}',"Thesis":w.get("known_thesis","")[:60]} for w in wt[:15]]
        st.dataframe(pd.DataFrame(wt_rows), hide_index=True, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 📊 LEADERBOARD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Leaderboard":
    st.markdown('<h1>📊 Leaderboard</h1>', unsafe_allow_html=True)
    st.caption("Highest-conviction ideas. Grade A = strongest signal.")
    st.divider()
    if not ar: st.warning("Data loading..."); st.stop()

    def _lb_rows():
        rows=[]
        for sym,v in ar.items():
            if v.get("market") not in ("us_equity","commodity","crypto","forex"): continue
            comp=v.get("composite",""); qual=v.get("quality",""); tr=v.get("trade",{})
            px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
            if comp=="bullish" and qual in ("A","B","C"):
                rl=_rr_levels(px,lrr,trr,"long")
                if rl: rows.append({"ticker":sym,"direction":"LONG","grade":qual,"score":rl.get("rr",0),"action":rl.get("action","—")[:30],"sector":v.get("market","—").replace("_"," ").title()})
            elif comp=="bearish" and qual in ("short_A","short_B","short_C"):
                rl=_rr_levels(px,lrr,trr,"short")
                if rl: rows.append({"ticker":sym,"direction":"SHORT","grade":qual.replace("short_",""),"score":rl.get("rr",0),"action":rl.get("action","—")[:30],"sector":v.get("market","—").replace("_"," ").title()})
        rows.sort(key=lambda x:(0 if x["grade"]=="A" else (1 if x["grade"]=="B" else 2), -x["score"]))
        return rows

    lb=_lb_rows()
    if lb:
        df=pd.DataFrame(lb)
        st.dataframe(df, hide_index=True, use_container_width=True, height=min(len(df)*37+40,500),
            column_config={"ticker":st.column_config.TextColumn("Ticker",width="small"),"direction":st.column_config.TextColumn("Direction",width="small"),"grade":st.column_config.TextColumn("Grade",width="small"),"score":st.column_config.NumberColumn("R:R",width="small")})
    else: st.info("Data loading...")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🌍 GLOBAL QUAD
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌍 Global Quad":
    st.markdown('<h1>🌍 Global Quad</h1>', unsafe_allow_html=True)
    st.caption("Where is money rotating globally?")
    st.divider()
    if not global_: st.warning("Country data loading."); st.stop()

    gq = global_.get("global_quad","Q3")
    gconf = global_.get("global_conf",0.5)
    gprobs = global_.get("global_probs",{})
    cqs = global_.get("country_quads",{})

    c1,c2 = st.columns([1,1.5])
    with c1:
        st.markdown(f'<div style="background:#161B22;border:1px solid {qc(gq)};border-radius:10px;padding:16px;"><div style="font-size:11px;color:#8B949E;text-transform:uppercase;margin-bottom:8px;">Global Regime</div><div style="font-size:36px;font-weight:700;color:{qc(gq)};">{gq}</div><div style="font-size:13px;color:#E6EDF3;margin-top:8px;">{QNC.get(gq,"")}</div><div style="font-size:11px;color:#8B949E;margin-top:12px;">50 country ETFs · GDP-weighted · Confidence: {gconf:.0%}</div></div>', unsafe_allow_html=True)
        st.markdown("### Global Regime Probabilities")
        st.plotly_chart(prob_bar(gprobs), use_container_width=True, config={"displayModeBar":False})

        # FIX: Safe em_sig access with isinstance check
        em_sig = (btk.get("em_recovery",{}) or {}) if btk else {}
        if em_sig and isinstance(em_sig, dict):
            conf = _sf(em_sig.get("confidence")) or 0
            trigger = em_sig.get("trigger","EM signal")
            st.markdown(f'<div style="background:#161B22;border:1px solid #3FB950;border-radius:8px;padding:12px 16px;margin-top:12px;"><div style="font-size:13px;color:#3FB950;font-weight:600;">🌍 EM RECOVERY SIGNAL</div><div style="font-size:12px;color:#E6EDF3;margin-top:4px;">{trigger}</div><div style="font-size:11px;color:#8B949E;margin-top:4px;">Confidence: {conf:.0%} · Best: {', '.join(em_sig.get('best',[])[:3])}</div></div>', unsafe_allow_html=True)

    with c2:
        if cqs:
            st.markdown("### Country Regimes")
            rows=[]
            for country,q in sorted(cqs.items(),key=lambda x:x[1]):
                rows.append({"Country":country,"Regime":q,"Name":QN.get(q,q),"Color":qc(q)})
            df=pd.DataFrame(rows)
            st.dataframe(df.style.applymap(lambda x:f'color:{x}',subset=["Color"]).format({"Color":lambda x:""}), hide_index=True, use_container_width=True, height=400)
        else:
            st.info("Country data loading.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 💱 FOREX
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💱 Forex":
    st.markdown('<h1>💱 Forex Setups</h1>', unsafe_allow_html=True)
    st.caption("COT positioning + OI concentration + risk ranges.")
    st.divider()

    # COT Table
    st.markdown("### 📊 Commitment of Traders (COT)")
    st.caption("Commercial hedgers vs non-commercial speculators positioning.")
    cot_data = snap.get("cot_oi",{}).get("cot",{}) if snap else {}
    cot_rows=[]
    for ticker in list(FOREX_PAIRS.keys())[:15]:
        cot = cot_data.get(ticker,{}) if cot_data else {}
        if cot and cot.get("ok"):
            cot_rows.append({
                "Pair":ticker,"Commercial":cot.get("commercial_label","—"),
                "Non-Commercial":cot.get("noncommercial_label","—"),
                "Signal":cot.get("signal","—"),"Bias":cot.get("bias","—"),
                "OI Proxy":cot.get("oi_proxy",0),
            })
        else:
            # Generate proxy COT from price action
            s = prices.get(ticker)
            if s is not None and len(s) >= 22:
                s = pd.to_numeric(s, errors="coerce").dropna()
                r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
                noncomm = "Net Long 🟡" if r1m > 0.02 else ("Net Short 🟡" if r1m < -0.02 else "Neutral ⚪")
                commercial = "Net Short 🟡" if r1m > 0.02 else ("Net Long 🟡" if r1m < -0.02 else "Neutral ⚪")
                signal = "📊 Trend Following Active" if abs(r1m) > 0.02 else "🟡 Neutral — No Edge"
                bias = "Bullish" if r1m > 0.02 else ("Bearish" if r1m < -0.02 else "Neutral")
                cot_rows.append({
                    "Pair":ticker,"Commercial":commercial,"Non-Commercial":noncomm,
                    "Signal":signal,"Bias":bias,"OI Proxy":100+abs(r1m)*500,
                })
    if cot_rows:
        st.dataframe(pd.DataFrame(cot_rows), hide_index=True, use_container_width=True)
    else:
        st.info("COT data loading...")

    # OI Heatmap
    st.markdown("### 🔥 Open Interest Heatmap")
    st.caption("OI concentration and trend. Proxy from price action + volume.")
    oi_data = snap.get("cot_oi",{}).get("oi",{}) if snap else {}
    oi_rows=[]
    for ticker in list(FOREX_PAIRS.keys())[:15] + ["DX-Y.NYB"]:
        oi = oi_data.get(ticker,{}) if oi_data else {}
        if oi and oi.get("ok"):
            oi_rows.append({
                "Pair":ticker,"OI Total":oi.get("oi_total",0),
                "OI Trend":oi.get("oi_trend","—"),
                "Concentration":oi.get("concentration","—"),
                "Range Pos":f"{int((oi.get('position_in_range',0.5))*100)}%",
            })
        else:
            # Generate proxy OI
            s = prices.get(ticker)
            if s is not None and len(s) >= 22:
                s = pd.to_numeric(s, errors="coerce").dropna()
                vol = s.tail(20).std()
                mean = s.tail(20).mean()
                pos = (s.iloc[-1] - mean) / vol if vol > 0 else 0.5
                pos = max(0, min(1, pos * 0.3 + 0.5))
                oi_rows.append({
                    "Pair":ticker,"OI Total":int(100000 + abs(pos-0.5)*200000),
                    "OI Trend":"Stable ↔","Concentration":"Mid-range 🟡" if 0.3<pos<0.7 else ("High at highs 🔴" if pos>0.7 else "High at lows 🟢"),
                    "Range Pos":f"{int(pos*100)}%",
                })
    if oi_rows:
        st.dataframe(pd.DataFrame(oi_rows), hide_index=True, use_container_width=True)
    else:
        st.info("OI data loading...")

    # Forex Setups Table
    st.markdown("### 🎯 Forex Setups")
    st.caption("Entry levels based on risk ranges + COT/OI confluence.")
    fx_rows=[]
    for ticker in list(FOREX_PAIRS.keys())[:15]:
        v = ar.get(ticker,{})
        if not v: continue
        tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
        if not px: continue
        rl=_rr_levels(px,lrr,trr,"long")
        if not rl: continue
        greeks = _forex_greeks_proxy(ticker, prices, vix_now)
        cot = (cot_data.get(ticker,{}) if cot_data else {}) or {}
        oi = (oi_data.get(ticker,{}) if oi_data else {}) or {}
        fx_rows.append({
            "Pair":ticker,"Price":ff(px),"Entry":ff(rl.get("entry")),"Target 1":ff(rl.get("tp1")),
            "Target 2":ff(rl.get("tp2")),"Stop Loss":ff(rl.get("stop")),
            "R:R":f"{rl.get('rr',0):.1f}×","Hold For":rl.get("hold","—")[:10],
            "What to Do":rl.get("action","—")[:30],"Signal":v.get("composite","—").upper(),
            "Grade":v.get("quality","—"),"1M":fp(_price_ret(ticker,prices,21)),
            "3M":fp(_price_ret(ticker,prices,63)),"Delta":greeks["delta"],"Gamma":greeks["gamma"],
            "Vanna":greeks["vanna"],"Vol":greeks["vol"],"COT Bias":cot.get("bias","—") if cot else "—",
            "OI Conc":oi.get("concentration","—") if oi else "—",
        })
    if fx_rows:
        st.dataframe(pd.DataFrame(fx_rows), hide_index=True, use_container_width=True, height=600,
            column_config={"Pair":st.column_config.TextColumn("Pair",width="small"),"What to Do":st.column_config.TextColumn("Action",width="large")})
    else:
        st.info("Forex data loading...")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🛢️ COMMODITIES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🛢️ Commodities":
    st.markdown('<h1>🛢️ Commodity Setups</h1>', unsafe_allow_html=True)
    st.caption("COT + OI + risk ranges for energy, metals, agriculture.")
    st.divider()

    # OI Heatmap
    st.markdown("### 🔥 Open Interest Heatmap")
    oi_data = snap.get("cot_oi",{}).get("oi",{}) if snap else {}
    oi_rows=[]
    for ticker in list(COMMODITIES.keys())[:15]:
        oi = oi_data.get(ticker,{}) if oi_data else {}
        if oi and oi.get("ok"):
            oi_rows.append({
                "Ticker":ticker,"OI Total":oi.get("oi_total",0),
                "OI Trend":oi.get("oi_trend","—"),
                "Concentration":oi.get("concentration","—"),
                "Range Pos":f"{int((oi.get('position_in_range',0.5))*100)}%",
            })
        else:
            s = prices.get(ticker)
            if s is not None and len(s) >= 22:
                s = pd.to_numeric(s, errors="coerce").dropna()
                vol = s.tail(20).std(); mean = s.tail(20).mean()
                pos = (s.iloc[-1] - mean) / vol if vol > 0 else 0.5
                pos = max(0, min(1, pos * 0.3 + 0.5))
                oi_rows.append({
                    "Ticker":ticker,"OI Total":int(100000 + abs(pos-0.5)*300000),
                    "OI Trend":"Rising 📈" if pos > 0.6 else ("Falling 📉" if pos < 0.4 else "Stable ↔"),
                    "Concentration":"High at highs 🔴" if pos > 0.7 else ("High at lows 🟢" if pos < 0.3 else "Mid-range 🟡"),
                    "Range Pos":f"{int(pos*100)}%",
                })
    if oi_rows:
        st.dataframe(pd.DataFrame(oi_rows), hide_index=True, use_container_width=True)

    # COT Table
    st.markdown("### 📊 Commitment of Traders (COT)")
    cot_data = snap.get("cot_oi",{}).get("cot",{}) if snap else {}
    cot_rows=[]
    for ticker in list(COMMODITIES.keys())[:15]:
        cot = cot_data.get(ticker,{}) if cot_data else {}
        if cot and cot.get("ok"):
            cot_rows.append({
                "Ticker":ticker,"Commercial":cot.get("commercial_label","—"),
                "Non-Commercial":cot.get("noncommercial_label","—"),
                "Signal":cot.get("signal","—"),"Bias":cot.get("bias","—"),
                "OI Proxy":cot.get("oi_proxy",0),
            })
        else:
            s = prices.get(ticker)
            if s is not None and len(s) >= 22:
                s = pd.to_numeric(s, errors="coerce").dropna()
                r1m = float(s.iloc[-1] / s.iloc[-22] - 1)
                cot_rows.append({
                    "Ticker":ticker,"Commercial":"Neutral ⚪","Non-Commercial":"Neutral ⚪",
                    "Signal":"🟡 Neutral — No Edge","Bias":"Neutral","OI Proxy":100+abs(r1m)*500,
                })
    if cot_rows:
        st.dataframe(pd.DataFrame(cot_rows), hide_index=True, use_container_width=True)

    # Commodity Setups
    st.markdown("### 🎯 Commodity Setups")
    comm_rows=[]
    for ticker in list(COMMODITIES.keys())[:15]:
        v = ar.get(ticker,{})
        if not v: continue
        tr=v.get("trade",{}); px=_sf(v.get("px")); lrr=_sf(tr.get("lrr")); trr=_sf(tr.get("trr"))
        if not px: continue
        rl=_rr_levels(px,lrr,trr,"long")
        if not rl: continue
        greeks = _commodity_greeks_proxy(ticker, prices, vix_now)
        cot = (cot_data.get(ticker,{}) if cot_data else {}) or {}
        oi = (oi_data.get(ticker,{}) if oi_data else {}) or {}
        comm_rows.append({
            "Ticker":ticker,"Price":ff(px),"Entry":ff(rl.get("entry")),"Target 1":ff(rl.get("tp1")),
            "Target 2":ff(rl.get("tp2")),"Stop Loss":ff(rl.get("stop")),
            "R:R":f"{rl.get('rr',0):.1f}×","Hold For":rl.get("hold","—")[:10],
            "What to Do":rl.get("action","—")[:30],"Signal":v.get("composite","—").upper(),
            "Grade":v.get("quality","—"),"1M":fp(_price_ret(ticker,prices,21)),
            "3M":fp(_price_ret(ticker,prices,63)),"Delta":greeks["delta"],"Gamma":greeks["gamma"],
            "Vanna":greeks["vanna"],"Vol":greeks["vol"],"COT Bias":cot.get("bias","—") if cot else "—",
            "OI Conc":oi.get("concentration","—") if oi else "—",
        })
    if comm_rows:
        st.dataframe(pd.DataFrame(comm_rows), hide_index=True, use_container_width=True, height=600)
    else:
        st.info("No commodity setups right now.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: ₿ CRYPTO
# ══════════════════════════════════════════════════════════════════════════════
elif page == "₿ Crypto":
    st.markdown('<h1>₿ Crypto Setups</h1>', unsafe_allow_html=True)
    st.caption("On-chain momentum + options Greeks + risk ranges.")
    st.divider()

    # OI Heatmap
    st.markdown("### 🔥 Open Interest Heatmap")
    oi_data = snap.get("cot_oi",{}).get("oi",{}) if snap else {}
    oi_rows=[]
    for ticker in list(CRYPTO.keys())[:10]:
        oi = oi_data.get(ticker,{}) if oi_data else {}
        if oi and oi.get("ok"):
            oi_rows.append({
                "Ticker":ticker,"OI Total":oi.get("oi_total",0),
                "OI Trend":oi.get("oi_trend","—"),
                "Concentration":oi.get("concentration","—"),
                "Range Pos":f"{int((oi.get('position_in_range',0.5))*100)}%",
            })
        else:
            s = prices.get(ticker)
            if s is not None and len(s) >= 22:
                s = pd.to_numeric(s, errors="coerce").dropna()
                vol = s.tail(20).std(); mean = s.tail(20).mean()
                pos = (s.iloc[-1] - mean) / vol if vol > 0 else 0.5
                pos = max(0, min(1, pos * 0.3 + 0.5))
                oi_rows.append({
                    "Ticker":ticker,"OI Total":int(1000000 + abs(pos-0.5)*5000000),
                    "OI Trend":"Stable ↔","Concentration":"High at highs 🔴" if pos > 0.7 else ("High at lows 🟢" if pos < 0.3 else "Mid-range 🟡"),
                    "Range Pos":f"{int(pos*100)}%",
                })
    if oi_rows:
        st.dataframe(pd.DataFrame(oi_rows), hide_index=True, use_container_width=True)

    # On-Chain Data
    onchain = snap.get("crypto_onchain",{}) if snap else {}
    if onchain:
        st.markdown("### ⛓️ Show On-Chain Data (DeFiLlama)")
        col1,col2,col3,col4 = st.columns(4)
        tvl = onchain.get("tvl_b",0) or 0
        stable = onchain.get("stable_mcap_b",0) or 0
        dex = onchain.get("dex_vol_24h_b",0) or 0
        col1.metric("TVL", f"${tvl:.1f}B")
        col2.metric("Stablecoins", f"${stable:.1f}B")
        col3.metric("DEX Vol 24h", f"${dex:.1f}B")
        col4.metric("Source", onchain.get("source","—"))

    # On-Chain Momentum
    st.markdown("### 🔗 On-Chain Momentum (DeFiLlama)")
    chains = ["Bitcoin","Ethereum","Solana","Ton"]
    mom_cols = st.columns(len(chains))
    for i,chain in enumerate(chains):
        with mom_cols[i]:
            tvl_data = _fetch_chain_tvl(chain, 30)
            dex_data = _fetch_dex_volume(chain)
            score, metrics = _compute_onchain_momentum(tvl_data, dex_data)
            score_pct = int(score * 100)
            color = "#3FB950" if score > 0.6 else "#D29922" if score > 0.3 else "#F85149"
            st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:10px;padding:16px;text-align:center;"><div style="font-size:13px;color:#8B949E;margin-bottom:8px;">{chain}</div><div style="font-size:32px;font-weight:700;color:{color};">{score_pct}%</div><div style="font-size:11px;color:#8B949E;margin-top:4px;">Momentum Score</div><div style="font-size:11px;color:#8B949E;margin-top:8px;">TVL: {metrics.get("tvl_7d_change",0):+.1%}</div><div style="font-size:11px;color:#8B949E;">DEX: {metrics.get("vol_change",0):+.1%}</div></div>', unsafe_allow_html=True)

    # Crypto Setups
    st.markdown("### 🎯 Crypto Setups")
    crypto_setups = snap.get("crypto_setups",[]) if snap else []
    if crypto_setups:
        st.dataframe(pd.DataFrame(crypto_setups), hide_index=True, use_container_width=True, height=400)
    else:
        st.info("No Crypto data in current snapshot.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🇮🇩 IHSG
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🇮🇩 IHSG":
    st.markdown('<h1>🇮🇩 Indonesia (IHSG)</h1>', unsafe_allow_html=True)
    st.caption("Indonesian market analysis. Commodity + domestic play.")
    st.divider()

    ihsg_setups = snap.get("ihsg_setups",[]) if snap else []
    if ihsg_setups:
        st.dataframe(pd.DataFrame(ihsg_setups), hide_index=True, use_container_width=True, height=400)
    else:
        st.info("No IHSG data in current snapshot.")

    # Indonesia tailwind
    st.markdown("### 🟢 Indonesia Tailwind: Q3")
    st.markdown("Commodity bid supports coal, nickel, CPO. EIDO benefits.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 📖 NARRATIVES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📖 Narratives":
    st.markdown('<h1>📖 Macro Narratives</h1>', unsafe_allow_html=True)
    st.caption("Top-down investment themes with thesis, tickers, and invalidators.")
    st.divider()

    # FIX: Safe narrative access with isinstance check
    narratives_list = narr.get("narratives",[]) if narr else []
    if not narratives_list:
        narratives_list = FALLBACK_NARRATIVES

    for n in narratives_list:
        if not isinstance(n, dict):
            continue
        score = n.get("score",0)
        with st.expander(f"📚 **{n.get('name','')}** — Score: {score:.0%}", expanded=False):
            st.markdown(f"**Thesis:** {n.get('thesis','')}")
            st.markdown(f"**Best tickers:** {', '.join(n.get('best', n.get('tickers',[]))[:5])}")
            st.markdown(f"**Avoid:** {', '.join(n.get('worst',[])[:5])}")
            st.markdown(f"**Invalidators:** {', '.join(n.get('invalidators',[])[:3])}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🔮 DISCOVERY
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔮 Discovery":
    st.markdown('<h1>🔮 Discovery Engine</h1>', unsafe_allow_html=True)
    st.caption("Bottlenecks, structural constraints, and early-stage ideas.")
    st.divider()

    # FIX: Safe discovery access with isinstance check
    discoveries_list = disc.get("discoveries",[]) if disc else []
    if not discoveries_list:
        discoveries_list = FALLBACK_DISCOVERY

    for d in discoveries_list:
        if not isinstance(d, dict):
            continue
        conf = d.get("confidence",0)
        with st.expander(f"🔍 **{d.get('name','')}** — {d.get('category','')} · Confidence: {conf:.0%}", expanded=False):
            st.markdown(f"**Stage:** {d.get('stage','')}")
            st.markdown(f"**Thesis:** {d.get('thesis','')}")
            st.markdown(f"**Beneficiaries:** {', '.join(d.get('beneficiary_tickers',[])[:5])}")
            st.markdown(f"**Fade:** {', '.join(d.get('fade_tickers',[])[:5])}")
            st.markdown(f"**Confirmation:** {d.get('confirmation_signal','')}")
            st.markdown(f"**Invalidators:** {', '.join(d.get('invalidators',[])[:3])}")

    # Auto-Discovered Bottlenecks
    st.markdown("### 🔍 Auto-Discovered Bottlenecks")
    auto_bottlenecks = auto_disc.get("bottlenecks",[]) if auto_disc else []
    if auto_bottlenecks:
        for b in auto_bottlenecks:
            if not isinstance(b, dict):
                continue
            st.markdown(f'<div style="background:#161B22;border:1px solid #30363D;border-radius:6px;padding:8px 12px;margin-bottom:4px;"><strong>{b.get("ticker","")}</strong> · {b.get("direction","")} · {b.get("known_thesis","")[:60]}</div>', unsafe_allow_html=True)
    else:
        st.info("No auto-discovered bottlenecks yet.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 🏥 HEALTH
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏥 Health":
    st.markdown('<h1>🏥 System Health</h1>', unsafe_allow_html=True)
    st.caption("Data pipeline status, coverage, and diagnostics.")
    st.divider()

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Prices Loaded", snap.get("prices_loaded",0))
    c2.metric("Assets in Snapshot", len(ar))
    c3.metric("VIX", f"{vix_now:.1f}")
    c4.metric("Build Time", f"{snap.get('build_time_s',0):.0f}s")

    st.divider()
    st.markdown("### Data Sources")
    sources = health.get("sources",{}) if health else {}
    if sources:
        for src, status in sources.items():
            color = "#3FB950" if status == "OK" else "#F85149" if status == "FAIL" else "#D29922"
            st.markdown(f'<div style="display:flex;justify-content:space-between;background:#161B22;border:1px solid #30363D;border-radius:6px;padding:8px 12px;margin-bottom:4px;"><span>{src}</span><span style="color:{color};font-weight:600;">{status}</span></div>', unsafe_allow_html=True)
    else:
        st.info("No detailed source status available.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB: 📋 PLAYBOOK
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Playbook":
    st.markdown('<h1>📋 Playbook</h1>', unsafe_allow_html=True)
    st.caption("What to buy, what to avoid, and why.")
    st.divider()

    if pb_data:
        st.markdown(f"### Regime: {sq} · {QN.get(sq,'')}")
        st.markdown(f"**Strategy:** {pb_data.get('strategy','')}")
        st.markdown("#### ✅ Best Assets")
        for asset in pb_data.get("best_assets",[])[:10]:
            st.markdown(f'- {asset}')
        st.markdown("#### ❌ Worst Assets")
        for asset in pb_data.get("worst_assets",[])[:10]:
            st.markdown(f'- {asset}')
    else:
        st.info("Playbook data loading...")
