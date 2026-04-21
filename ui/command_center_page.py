"""ui/command_center_page.py — Live Opportunities Split Per Market"""
from __future__ import annotations
from typing import Dict
import streamlit as st
import pandas as pd

def render_command_center(snap: Dict) -> None:
    q = snap.get("q", {})
    quad = q.get("quad", "Q?")
    monthly_quad = q.get("monthly_quad", quad)
    conf = q.get("confidence", 0.0)
    divergence = q.get("divergence", "aligned")
    vix = q.get("vix_last", 20.0)
    transition = snap.get("regime_transition", {})
    tickers = snap.get("regime_tickers", {})
    narr = snap.get("narrative_discovery", {})
    btl = snap.get("bottleneck_discovery", {})

    def _h(html: str) -> None: st.markdown(" ".join(html.split()), unsafe_allow_html=True)

    QC = {"Q1":("#1a4d2e","#4ade80"),"Q2":("#5c3d00","#fbbf24"),"Q3":("#5c2b00","#fb923c"),"Q4":("#5c1a1a","#f87171")}
    def qbg(q): return QC.get(q, ("#2d3748","#a0aec0"))[0]
    def qfg(q): return QC.get(q, ("#2d3748","#a0aec0"))[1]

    s_bg, s_fg = qbg(quad), qfg(quad)
    m_bg, m_fg = qbg(monthly_quad), qfg(monthly_quad)
    div_color = "#f85149" if divergence == "divergent" else "#3fb950"
    div_text = "DIVERGEN" if divergence == "divergent" else "ALIGNED"
    div_icon = "⚡" if divergence == "divergent" else "✅"

    horizon = transition.get("front_run_window", "1-2W")
    horiz_label = "1-2W" if horizon in ("now","1-2w","1-2W") else "3-6W" if horizon in ("3-6w","3-6W") else horizon
    horiz_icon = "🕐" if "1-2" in str(horiz_label) else "📅" if "3-6" in str(horiz_label) else "⏳"

    vix_label = "normal" if vix < 20 else "elevated" if vix < 25 else "high"
    vix_color = "#3fb950" if vix < 20 else "#d29922" if vix < 25 else "#f85149"
    cap = snap.get("options_regime", {}).get("vix_sizing_cap", 0.85)
    regime_state = "Relief" if "relief" in str(q.get("operating_regime", "")).lower() else q.get("operating_regime", "—")
    state_color = "#3fb950" if "Relief" in regime_state else "#d29922"

    _h(f"""
    <div style="background:#0d1117;border:1px solid #30363d;border-radius:12px;padding:14px;margin-bottom:14px;">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        <span style="background:{s_bg};color:{s_fg};padding:5px 12px;border-radius:20px;font-size:12px;font-weight:700;">S: {quad}</span>
        <span style="background:{m_bg};color:{m_fg};padding:5px 12px;border-radius:20px;font-size:12px;font-weight:700;">M: {monthly_quad}</span>
        <span style="background:#21262d;color:{div_color};padding:5px 12px;border-radius:20px;font-size:12px;font-weight:700;border:1px solid {div_color}33;">{div_icon} {div_text}</span>
        <span style="background:#21262d;color:#c9d1d9;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid #30363d;">Conf: {conf:.0%}</span>
        <span style="background:#21262d;color:#8b949e;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid #30363d;">{horiz_icon} {horiz_label}</span>
        <span style="background:#21262d;color:{state_color};padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid {state_color}33;">{regime_state}</span>
        <span style="background:#21262d;color:{vix_color};padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid #30363d;">VIX {vix:.1f} ({vix_label}) · cap {cap:.0%}</span>
      </div>
    </div>
    """)

    us_longs = tickers.get("us_longs", [])[:1]
    ihsg_buys = tickers.get("ihsg_buys", [])[:1]
    us_shorts = tickers.get("us_shorts", [])[:1]
    pills = []
    for t in us_longs: pills.append(f'<span style="color:#3fb950;font-weight:700;">▲ {t}</span>')
    for t in ihsg_buys: pills.append(f'<span style="color:#fb923c;font-weight:700;">🇮🇩 {t}</span>')
    for t in us_shorts: pills.append(f'<span style="color:#f85149;font-weight:700;">▼ {t}</span>')
    if pills:
        _h(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;font-size:13px;">{" · ".join(pills)}</div>')

    if conf < 0.25 or divergence == "divergent":
        _h(f"""
        <div style="background:#341a00;border:1px solid #d29922;border-radius:10px;padding:12px;margin-bottom:16px;">
          <div style="color:#d29922;font-size:13px;font-weight:700;">⚠️ TRANSITIONAL — {quad}/{monthly_quad} Conf {conf:.0%} terlalu rendah. Regime belum confirmed.</div>
          <div style="color:#c9d1d9;font-size:12px;margin-top:4px;">Trade monthly signal saja, jangan buka structural positions.</div>
        </div>
        """)

    fw = transition.get("front_run_window", "—")
    if fw != "—":
        st.success(f"**Front-Run Window:** {fw} | {transition.get('front_run_rationale', '—')}")
        early = transition.get("early_warning_signals", [])
        if early:
            c = st.columns(min(len(early), 4))
            for i, e in enumerate(early[:4]):
                with c[i]: st.info(e)
    else:
        st.info("No active front-run window — regime stable.")

    # Live Opportunities — Split 5
    st.markdown('<div style="font-size:16px;font-weight:700;color:#e6edf3;margin:16px 0 10px;">🎯 LIVE OPPORTUNITIES</div>', unsafe_allow_html=True)

    def make_opp_table(title, emoji, color, ticker_list, opp_type):
        if not ticker_list: return
        st.markdown(f"**{emoji} {title}**")
        rows = [{"Ticker": t, "Type": opp_type, "Signal": "▲" if opp_type=="Long" else "▼" if opp_type=="Short" else "⚡"} for t in ticker_list]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    us_longs_full = tickers.get("us_longs", [])[:6]
    us_shorts_full = tickers.get("us_shorts", [])[:4]
    if us_longs_full or us_shorts_full:
        c1, c2 = st.columns(2)
        with c1: make_opp_table("US Longs", "🇺🇸", "#3fb950", us_longs_full, "Long")
        with c2: make_opp_table("US Shorts", "🇺🇸", "#f85149", us_shorts_full, "Short")

    make_opp_table("IHSG", "🇮🇩", "#fb923c", tickers.get("ihsg_buys", [])[:6], "Long")
    make_opp_table("FX", "💱", "#58a6ff", tickers.get("fx_longs", [])[:4], "Long")
    make_opp_table("Commodities", "🛢️", "#fb923c", tickers.get("commodity_longs", [])[:5], "Long")
    make_opp_table("Crypto", "🔐", "#a371f7", tickers.get("crypto_longs", [])[:5], "Long")

    st.markdown("**📰 Narrative & Adaptive Extras**")
    extra_rows = []
    if narr and narr.get("active_narratives"):
        for n in narr["active_narratives"][:2]:
            for b in n.get("primary_beneficiaries", [])[:2]:
                extra_rows.append({"Source": f"📰 {n.get('name', '—')[:12]}", "Ticker": b, "Type": "Narrative"})
    if btl and btl.get("front_run_basket"):
        for item in btl["front_run_basket"][:4]:
            extra_rows.append({"Source": "🔍 Bottleneck", "Ticker": item.get("ticker", "—"), "Type": "Adaptive"})
    if extra_rows:
        st.dataframe(pd.DataFrame(extra_rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No narrative/bottleneck extras")