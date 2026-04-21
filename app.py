"""MacroRegime Pro v10.4 — Markets Tab: Per-Market Split Tables"""
from __future__ import annotations
import os
import sys
from typing import Dict
from datetime import datetime, timezone

import streamlit as st
import pandas as pd

st.set_page_config(page_title="MacroRegime Pro", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path: sys.path.insert(0, SCRIPT_DIR)

from orchestration.build_snapshot import build_snapshot
from ui.command_center_page import render_command_center
from ui.theme import _inject_theme

_inject_theme()

@st.cache_data(ttl=300, show_spinner="Building macro snapshot...")
def _load_snapshot():
    try: return build_snapshot()
    except Exception as e: st.error(f"Snapshot failed: {e}"); return _empty_snapshot()

def _empty_snapshot() -> Dict:
    return {"q": {"quad":"Q?","structural_quad":"Q?","monthly_quad":"Q?","global_quad":"Q?","confidence":0,"divergence":"unknown","operating_regime":"—","vix_last":20.0,"structural_probs":{},"monthly_probs":{},"g_core":0,"i_core":0,"p_core":0},"f":{},"fred_meta":{"loaded":0,"missing":24},"regime_tickers":{},"top_drivers":[],"narrative_discovery":{},"bottleneck_discovery":{},"most_hated_rally":{},"regime_transition":{},"prices":{}}

snap = _load_snapshot()
q = snap.get("q", {}) or _empty_snapshot()["q"]
f = snap.get("f", {})
quad = q.get("quad","Q?")
structural_quad = q.get("structural_quad", quad)
monthly_quad = q.get("monthly_quad", quad)
global_quad = q.get("global_quad", quad)
conf = q.get("confidence", 0.0)
divergence = q.get("divergence", "aligned")
vix = q.get("vix_last", 20.0)
operating_regime = q.get("operating_regime", "—")

def _h(html: str) -> None: st.markdown(" ".join(html.split()), unsafe_allow_html=True)

QC = {"Q1":("#1a4d2e","#4ade80"),"Q2":("#5c3d00","#fbbf24"),"Q3":("#5c2b00","#fb923c"),"Q4":("#5c1a1a","#f87171")}
def _qbg(q_): return QC.get(q_, ("#2d3748","#a0aec0"))[0]
def _qfg(q_): return QC.get(q_, ("#2d3748","#a0aec0"))[1]

# ── Header ──
_h(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="font-size:32px;">🧭</div>
    <div>
      <div style="font-size:24px;font-weight:800;color:#e6edf3;letter-spacing:-0.5px;">MacroRegime <span style="color:#58a6ff;">Pro</span></div>
      <div style="font-size:11px;color:#8b949e;margin-top:2px;">v10.4 · Markets Split · Per-Market Tables</div>
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:11px;color:#8b949e;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</div>
    <div style="font-size:11px;color:#f85149;margin-top:2px;">🔴 S:{structural_quad} · M:{monthly_quad} · G:{global_quad}</div>
  </div>
</div>
""")

# ── Regime Card ──
s_bg, s_fg = _qbg(structural_quad), _qfg(structural_quad)
m_bg, m_fg = _qbg(monthly_quad), _qfg(monthly_quad)
g_bg, g_fg = _qbg(global_quad), _qfg(global_quad)

tickers = snap.get("regime_tickers", {})
best_long = tickers.get("us_longs", ["—"])[0] if tickers.get("us_longs") else "—"
best_short = tickers.get("us_shorts", ["—"])[0] if tickers.get("us_shorts") else "—"
best_ihsg = tickers.get("ihsg_buys", [""])[0] if tickers.get("ihsg_buys") else ""

risk_state = snap.get("crash", {}).get("exec_mode", "CALM")
risk_color = "#3fb950" if "CALM" in risk_state else "#d29922" if "CAUTIOUS" in risk_state else "#f85149"
exec_state = snap.get("regime_transition", {}).get("front_run_window", "Wait")
exec_color = "#3fb950" if "now" in exec_state.lower() else "#d29922"
rally = snap.get("most_hated_rally", {})
rally_clear = rally.get("clear_count", 0)
rally_total = rally.get("total", 4)

_h(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:14px;padding:16px;margin-bottom:14px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;">
    <span style="background:{s_bg};color:{s_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">S:{structural_quad}</span>
    <span style="background:{m_bg};color:{m_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">M:{monthly_quad}</span>
    <span style="background:{g_bg};color:{g_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">G:{global_quad}</span>
    <span style="color:#8b949e;font-size:13px;">{operating_regime}</span>
    <span style="margin-left:auto;color:#fb923c;font-size:13px;font-weight:600;">🔥 {operating_regime}</span>
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
    <span>Conf: <span style="color:#f85149;font-weight:600;">{conf:.0%} (Low-Conviction)</span></span>
    <span>Growth: <span style="color:#3fb950;">▲</span></span>
    <span>Inflasi: <span style="color:#f85149;">▼</span></span>
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
    <span>▲ Best Long: <span style="color:#3fb950;font-weight:600;">{best_long}</span></span>
    <span>▼ Best Short: <span style="color:#f85149;font-weight:600;">{best_short}</span></span>
    {f'<span>🇮🇩 IHSG: <span style="color:#fb923c;font-weight:600;">{best_ihsg}</span></span>' if best_ihsg else ''}
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
    <span>Risk: <span style="color:{risk_color};">🟢 {risk_state}</span></span>
    <span>Exec: <span style="color:{exec_color};">🟡 {exec_state}</span></span>
    <span>Rally: {rally_clear}/{rally_total} clear</span>
  </div>
  <div style="display:flex;align-items:center;justify-content:space-between;font-size:11px;color:#8b949e;margin-top:8px;border-top:1px solid #30363d;padding-top:8px;">
    <span>🕊️ Event-Lite: Relief / De-escalation</span>
    <span>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</span>
  </div>
</div>
""")

top_drivers = snap.get("top_drivers", [])
if top_drivers:
    parts = [f"{d.get('name', d.get('label', '—'))}: {d.get('score', 0):.0%}" for d in top_drivers[:3]]
    parts.append(f"🕊️ Event-Lite: 77%")
    _h(f'<div style="font-size:12px;color:#8b949e;margin-bottom:14px;">Top drivers now → {" · ".join(parts)}</div>')

# ── 4 Tabs ──
tabs = st.tabs(["⚡ Command Center", "🌍 Markets", "📊 Regime Deep Dive", "⚠️ Risk & Diag"])

with tabs[0]:
    render_command_center(snap)

with tabs[1]:
    # ═══════════════════════════════════════════════════════════════════════
    # MARKETS TAB — Per-Market Split Tables + Overview
    # ═══════════════════════════════════════════════════════════════════════
    prices = snap.get("prices", {})
    transition = snap.get("regime_transition", {})
    fw = transition.get("front_run_window", "—")
    tr_label = f"{structural_quad}→{q.get('next_quad', '?')}" if q.get('next_quad') else "No transition"
    narr = snap.get("narrative_discovery", {})
    btl = snap.get("bottleneck_discovery", {})

    def ret_n(s, n):
        if s is None or len(s) < n+1: return float("nan")
        try:
            b = float(s.iloc[-(n+1)]); e = float(s.iloc[-1])
            return float(e/b-1) if b != 0 else float("nan")
        except: return float("nan")

    def build_rows(ticker_list, names_map):
        rows = []
        for tk in ticker_list:
            s = prices.get(tk)
            name = names_map.get(tk, tk)
            if s is not None:
                r1 = ret_n(s, 21); r3 = ret_n(s, 63)
                rows.append({"Ticker": tk, "Name": name, "1M": f"{r1:+.1%}" if r1==r1 else "—", "3M": f"{r3:+.1%}" if r3==r3 else "—"})
            else:
                rows.append({"Ticker": tk, "Name": name, "1M": "—", "3M": "—"})
        return rows

    # Front-run banner
    if fw in ("now", "1-2 weeks", "1-2w", "1-2W"):
        _h(f"""
        <div style="background:#1a3a2a;border:1px solid #3fb950;border-radius:10px;padding:12px;margin-bottom:16px;">
          <div style="color:#3fb950;font-size:13px;font-weight:700;">⚡ FRONT-RUN WINDOW: {fw.upper()} · {tr_label}</div>
          <div style="color:#c9d1d9;font-size:12px;margin-top:4px;">{transition.get('front_run_rationale', '—')}</div>
        </div>
        """)

    # ── Market sub-tabs ──
    mkt_tabs = st.tabs(["🇺🇸 US Stocks", "🇮🇩 IHSG", "💱 FX", "🛢️ Commodities", "🔐 Crypto", "📊 Overview"])

    # ══════ 🇺🇸 US STOCKS ══════
    with mkt_tabs[0]:
        us_longs = tickers.get("us_longs", [])
        us_shorts = tickers.get("us_shorts", [])
        fr_us_long = us_longs[:3] if fw in ("now", "1-2 weeks") else []
        fr_us_short = us_shorts[:2] if fw in ("now", "1-2 weeks") else []

        col_long, col_short = st.columns(2)
        with col_long:
            st.markdown("**📍 NOW — LONG**")
            if us_longs:
                for t in us_longs: _h(f'<div style="color:#3fb950;font-weight:700;margin:2px 0;">▲ {t}</div>')
            else: st.caption("No longs")
        with col_short:
            st.markdown("**📍 NOW — SHORT**")
            if us_shorts:
                for t in us_shorts: _h(f'<div style="color:#f85149;font-weight:700;margin:2px 0;">▼ {t}</div>')
            else: st.caption("No shorts")

        if fr_us_long or fr_us_short:
            st.divider()
            c_fr_l, c_fr_s = st.columns(2)
            with c_fr_l:
                st.markdown("**⚡ FRONT-RUN — ACCUMULATE**")
                for t in fr_us_long: _h(f'<div style="color:#d29922;font-weight:700;margin:2px 0;">⚡ {t}</div>')
            with c_fr_s:
                st.markdown("**⚡ FRONT-RUN — FADE**")
                for t in fr_us_short: _h(f'<div style="color:#f85149;font-weight:700;margin:2px 0;">⚡ {t}</div>')

        # Long Table
        if us_longs:
            st.markdown("**Long Table**")
            long_names = {"SPY":"S&P 500","QQQ":"Nasdaq","IWM":"Russell 2K","XLE":"Energy","XLK":"Tech","XLF":"Finance","XLI":"Industrials","XLB":"Materials","XLV":"Health","XLY":"Consumer","XLP":"Staples","XLU":"Utilities","XLRE":"REITs","SPLV":"Low Vol","TLT":"Long Bond","GLD":"Gold"}
            df_long = pd.DataFrame(build_rows(us_longs, long_names))
            if not df_long.empty:
                st.dataframe(df_long, use_container_width=True, hide_index=True)

        # Short Table
        if us_shorts:
            st.markdown("**Short Table**")
            short_names = {"SPY":"S&P 500","QQQ":"Nasdaq","IWM":"Russell 2K","XLE":"Energy","XLK":"Tech","XLF":"Finance","XLI":"Industrials","XLB":"Materials","XLV":"Health","XLY":"Consumer","XLP":"Staples","XLU":"Utilities","XLRE":"REITs","SPLV":"Low Vol","TLT":"Long Bond","GLD":"Gold"}
            df_short = pd.DataFrame(build_rows(us_shorts, short_names))
            if not df_short.empty:
                st.dataframe(df_short, use_container_width=True, hide_index=True)

    # ══════ 🇮🇩 IHSG ══════
    with mkt_tabs[1]:
        ihsg_longs = tickers.get("ihsg_buys", [])
        fr_ihsg = ihsg_longs[:3] if fw in ("now", "1-2 weeks") else []

        st.markdown("**📍 NOW — LONG (IHSG Long Only)**")
        if ihsg_longs:
            for t in ihsg_longs: _h(f'<div style="color:#3fb950;font-weight:700;margin:2px 0;">▲ {t}</div>')
        else: st.caption("No IHSG buys")

        if fr_ihsg:
            st.divider()
            st.markdown("**⚡ FRONT-RUN — ACCUMULATE**")
            for t in fr_ihsg: _h(f'<div style="color:#d29922;font-weight:700;margin:2px 0;">⚡ {t}</div>')

        if ihsg_longs:
            ihsg_names = {"BBCA.JK":"BCA","BBRI.JK":"BRI","ASII.JK":"Astra","TLKM.JK":"Telkom","ADRO.JK":"Adaro","ANTM.JK":"Antam","PTBA.JK":"Bukit Asam","ITMG.JK":"Indomining","INCO.JK":"Vale","KLBF.JK":"Kalbe"}
            df_ihsg = pd.DataFrame(build_rows(ihsg_longs, ihsg_names))
            if not df_ihsg.empty:
                st.dataframe(df_ihsg, use_container_width=True, hide_index=True)

    # ══════ 💱 FX ══════
    with mkt_tabs[2]:
        fx_longs = tickers.get("fx_longs", [])
        fr_fx = fx_longs[:2] if fw in ("now", "1-2 weeks") else []

        st.markdown("**📍 NOW — LONG**")
        if fx_longs:
            for t in fx_longs: _h(f'<div style="color:#3fb950;font-weight:700;margin:2px 0;">▲ {t}</div>')
        else: st.caption("No FX longs")

        if fr_fx:
            st.divider()
            st.markdown("**⚡ FRONT-RUN — ACCUMULATE**")
            for t in fr_fx: _h(f'<div style="color:#d29922;font-weight:700;margin:2px 0;">⚡ {t}</div>')

        if fx_longs:
            fx_names = {"EURUSD=X":"EUR/USD","USDJPY=X":"USD/JPY","AUDUSD=X":"AUD/USD","USDIDR=X":"USD/IDR","UUP":"DXY"}
            df_fx = pd.DataFrame(build_rows(fx_longs, fx_names))
            if not df_fx.empty:
                st.dataframe(df_fx, use_container_width=True, hide_index=True)

    # ══════ 🛢️ COMMODITIES ══════
    with mkt_tabs[3]:
        comm_longs = tickers.get("commodity_longs", [])
        fr_comm = comm_longs[:3] if fw in ("now", "1-2 weeks") else []

        st.markdown("**📍 NOW — LONG**")
        if comm_longs:
            for t in comm_longs: _h(f'<div style="color:#3fb950;font-weight:700;margin:2px 0;">▲ {t}</div>')
        else: st.caption("No commodity longs")

        if fr_comm:
            st.divider()
            st.markdown("**⚡ FRONT-RUN — ACCUMULATE**")
            for t in fr_comm: _h(f'<div style="color:#d29922;font-weight:700;margin:2px 0;">⚡ {t}</div>')

        if comm_longs:
            comm_names = {"CL=F":"WTI Oil","GC=F":"Gold","HG=F":"Copper","SI=F":"Silver","NG=F":"Nat Gas","BZ=F":"Brent","URA":"Uranium"}
            df_comm = pd.DataFrame(build_rows(comm_longs, comm_names))
            if not df_comm.empty:
                st.dataframe(df_comm, use_container_width=True, hide_index=True)

    # ══════ 🔐 CRYPTO ══════
    with mkt_tabs[4]:
        cry_longs = tickers.get("crypto_longs", [])
        fr_cry = cry_longs[:2] if fw in ("now", "1-2 weeks") and vix < 22 else []

        st.markdown("**📍 NOW — LONG**")
        if cry_longs:
            for t in cry_longs: _h(f'<div style="color:#3fb950;font-weight:700;margin:2px 0;">▲ {t}</div>')
        else: st.caption("No crypto longs")

        if fr_cry:
            st.divider()
            st.markdown("**⚡ FRONT-RUN — ACCUMULATE**")
            for t in fr_cry: _h(f'<div style="color:#d29922;font-weight:700;margin:2px 0;">⚡ {t}</div>')

        if cry_longs:
            cry_names = {"BTC-USD":"Bitcoin","ETH-USD":"Ethereum","SOL-USD":"Solana","XRP-USD":"XRP"}
            df_cry = pd.DataFrame(build_rows(cry_longs, cry_names))
            if not df_cry.empty:
                st.dataframe(df_cry, use_container_width=True, hide_index=True)

    # ══════ 📊 OVERVIEW ══════
    with mkt_tabs[5]:
        # Heatmap
        st.markdown('<div style="font-size:16px;font-weight:700;color:#e6edf3;margin-bottom:10px;">🌍 CROSS-MARKET HEATMAP</div>', unsafe_allow_html=True)
        if prices:
            ASSETS = {"SPY":"US Equity","QQQ":"Growth","IWM":"Small Cap","TLT":"Long Bond","HYG":"Credit","GLD":"Gold","CL=F":"Oil","HG=F":"Copper","UUP":"USD","EEM":"EM","^JKSE":"IHSG","BTC-USD":"BTC","ETH-USD":"ETH"}
            heat = []
            for tk, name in ASSETS.items():
                s = prices.get(tk)
                if s is not None:
                    heat.append({"Asset": name, "Ticker": tk, "1M": f"{ret_n(s,21):+.1%}" if ret_n(s,21)==ret_n(s,21) else "—", "3M": f"{ret_n(s,63):+.1%}" if ret_n(s,63)==ret_n(s,63) else "—"})
            if heat: st.dataframe(pd.DataFrame(heat), use_container_width=True, hide_index=True)

        # Sector
        st.markdown('<div style="font-size:16px;font-weight:700;color:#e6edf3;margin:16px 0 10px;">📊 SECTOR LEADERSHIP</div>', unsafe_allow_html=True)
        SECS = {"XLE":"Energy","XLF":"Fin","XLI":"Ind","XLB":"Mat","XLK":"Tech","XLV":"Health","XLY":"Con.D","XLP":"Con.S","XLU":"Util","XLRE":"RE","XLC":"Comm"}
        spy3 = ret_n(prices.get("SPY"), 63)
        sec_rows = []
        for tk, name in SECS.items():
            s = prices.get(tk)
            if s is not None and len(s) > 63:
                r3 = ret_n(s, 63); rel = (r3 - spy3) if spy3==spy3 and r3==r3 else float("nan")
                sec_rows.append({"Sector": name, "3M": f"{r3:+.1%}" if r3==r3 else "—", "vs SPY": f"{rel:+.1%}" if rel==rel else "—"})
        if sec_rows:
            sec_rows.sort(key=lambda r: float(r["vs SPY"].replace("%","").replace("—","0").replace("+","")) if r["vs SPY"]!="—" else -999, reverse=True)
            st.dataframe(pd.DataFrame(sec_rows[:8]), use_container_width=True, hide_index=True)

        # Bottleneck
        st.markdown('<div style="font-size:16px;font-weight:700;color:#e6edf3;margin:16px 0 10px;">🔍 ADAPTIVE BOTTLENECK SCAN</div>', unsafe_allow_html=True)
        if btl:
            st.caption(f"Method: **{btl.get('discovery_method', 'unknown')}**")
            if btl.get("summary"): st.info(btl["summary"])
            if btl.get("active_sectors"):
                for sector in btl["active_sectors"][:5]:
                    with st.container(border=True):
                        sc1, sc2, sc3 = st.columns([3, 1, 1])
                        with sc1:
                            stage_color = {"mature":"red","building":"orange","early":"green"}.get(sector.get("stage"), "gray")
                            st.markdown(f"**{sector.get('sector_name', '—')}** · :{stage_color}[{sector.get('stage', '—')}]")
                            st.caption(f"{', '.join(sector.get('tickers', [])[:8])}")
                        with sc2: st.metric("Score", f"{sector.get('bottleneck_score', 0):.2f}")
                        with sc3: st.metric("Vol Z", f"{sector.get('avg_volume_zscore', 0):.2f}")
            if btl.get("front_run_basket"):
                st.markdown("**Front-Run Basket**")
                basket = btl["front_run_basket"][:12]
                if basket:
                    cols = ["ticker","market","sector","conviction","stage","r1m","r3m","volume_zscore","position_size","source"]
                    df_b = pd.DataFrame([{k: item.get(k, "—") for k in cols} for item in basket])
                    st.dataframe(df_b, use_container_width=True, hide_index=True)
        else: st.info("No bottleneck data")

        # Master Board
        st.markdown('<div style="font-size:16px;font-weight:700;color:#e6edf3;margin:16px 0 10px;">📋 MASTER TICKER BOARD</div>', unsafe_allow_html=True)
        all_tickers = []
        if tickers:
            for side, key in [("Long", "us_longs"), ("Short", "us_shorts"), ("IHSG", "ihsg_buys"), ("FX", "fx_longs"), ("Comm", "commodity_longs"), ("Crypto", "crypto_longs")]:
                for t in tickers.get(key, [])[:4]:
                    all_tickers.append({"Ticker": t, "Side": side, "Source": "Regime"})
        if btl and btl.get("front_run_basket"):
            for item in btl["front_run_basket"][:6]:
                all_tickers.append({"Ticker": item.get("ticker", "—"), "Side": item.get("sector", "—"), "Source": "Adaptive"})
        if narr and narr.get("active_narratives"):
            for n in narr["active_narratives"][:3]:
                for b in n.get("primary_beneficiaries", [])[:3]:
                    all_tickers.append({"Ticker": b, "Side": n.get("name", "—")[:15], "Source": "Narrative"})
        if all_tickers:
            st.dataframe(pd.DataFrame(all_tickers), use_container_width=True, hide_index=True)
        else: st.info("Building board...")

with tabs[2]:
    show_raw = st.toggle("Show raw regime state JSON", value=False)
    if show_raw: st.markdown("**Regime State**"); st.json(q)
    st.markdown("**Structural Probabilities**")
    probs = q.get("structural_probs", {}); m_probs = q.get("monthly_probs", {})
    if probs:
        for k in ["Q1","Q2","Q3","Q4"]:
            p = probs.get(k, 0.0); mp = m_probs.get(k, 0.0) if m_probs else 0.0
            is_s = k == structural_quad; is_m = k == monthly_quad and not is_s
            label = f"{'●' if is_s else '◉' if is_m else '○'} {k}: S={p:.0%} M={mp:.0%}"
            st.progress(p, text=label)
    else: st.info("No probability data")
    st.divider(); st.markdown("**Raw Macro Indicators**")
    rows = []
    for lbl, key, note in [("INDPRO YoY","indpro_yoy","▲" if f.get("indpro_acc") else "▼"),("CPI YoY","cpi_yoy","▲" if f.get("cpi_acc") else "▼"),("Core PCE","corepce_yoy","▲" if f.get("corepce_acc") else "▼"),("VIX","vix_last",""),("HY OAS","hy_oas",f"Δ1M: {f.get('hy_oas_1m',0):+.0f}bps"),("Policy Score","policy_score","+ve=cutting")]:
        val = f.get(key)
        if val is not None:
            try:
                v = float(val) if not isinstance(val, bool) else float("nan")
                if v == v: rows.append({"Indicator": lbl, "Value": f"{v:+.2f}" if abs(v) < 100 else f"{v:.2f}", "Note": note})
            except: pass
    if rows: st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("⚠️ Risk & Diagnostics")
    fred_meta = snap.get("fred_meta", {})
    if fred_meta:
        loaded = fred_meta.get("loaded", 0); missing = fred_meta.get("missing", 0)
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("FRED Loaded", f"{loaded}/{loaded+missing}")
        with c2: st.metric("Real Share", f"{fred_meta.get('real_share', 0):.0%}")
        with c3: st.metric("API Key", "✅" if fred_meta.get("api_key_present") else "❌")
        if missing > 0:
            mk = fred_meta.get("missing_keys", [])
            if mk: st.warning(f"Missing: {', '.join(mk[:10])}")
    else: st.error("FRED metadata unavailable")
    if rally:
        st.divider(); st.markdown("**Most Hated Rally — Checklist Detail**")
        st.caption(f"Stage: {rally.get('stage', '?')} | Action: {rally.get('action', '?')}")
        for item in rally.get("checklist", []):
            ok = item.get("value", False)
            icon = "✅" if ok else "⬜"
            color = "#3fb950" if ok else "#8b949e"
            raw = item.get("raw", 0)
            _h(f'<div style="color:{color};font-size:13px;margin:4px 0;">{icon} {item.get("item", "—")} <span style="color:#8b949e;">(raw: {raw:.4f})</span></div>')
        if rally_clear >= 4: st.success("All 4 checklist items cleared")
        else: st.info(f"Only {rally_clear}/4 cleared — not fully confirmed")
    if f.get("_proxy_warning"):
        st.error(f"🚨 {f['_proxy_warning']}")
        st.info("Fix: Set FRED_API_KEY in Streamlit secrets or env var.")