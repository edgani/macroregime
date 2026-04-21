"""ui/command_center_page.py — Card-Based Live Opportunities"""
from __future__ import annotations
from typing import Dict
import streamlit as st

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

    # Regime Pills
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

    # Top ticker pills
    us_longs = tickers.get("us_longs", [])[:1]
    ihsg_buys = tickers.get("ihsg_buys", [])[:1]
    us_shorts = tickers.get("us_shorts", [])[:1]
    pills = []
    for t in us_longs: pills.append(f'<span style="color:#3fb950;font-weight:700;">▲ {t}</span>')
    for t in ihsg_buys: pills.append(f'<span style="color:#fb923c;font-weight:700;">🇮🇩 {t}</span>')
    for t in us_shorts: pills.append(f'<span style="color:#f85149;font-weight:700;">▼ {t}</span>')
    if pills:
        _h(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;font-size:13px;">{" · ".join(pills)}</div>')

    # Transitional Banner
    if conf < 0.25 or divergence == "divergent":
        _h(f"""
        <div style="background:#341a00;border:1px solid #d29922;border-radius:10px;padding:12px;margin-bottom:16px;">
          <div style="color:#d29922;font-size:13px;font-weight:700;">⚠️ TRANSITIONAL — {quad}/{monthly_quad} Conf {conf:.0%} terlalu rendah. Regime belum confirmed.</div>
          <div style="color:#c9d1d9;font-size:12px;margin-top:4px;">Trade monthly signal saja, jangan buka structural positions.</div>
        </div>
        """)

    # Front-Run Window
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

    # ═══════════════════════════════════════════════════════════════════════
    # LIVE OPPORTUNITIES — Card-Based (no tables)
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown('<div style="font-size:16px;font-weight:700;color:#e6edf3;margin:16px 0 10px;">🎯 LIVE OPPORTUNITIES</div>', unsafe_allow_html=True)

    def render_card_group(title, emoji, tickers_list, color, border_color):
        if not tickers_list: return
        _h(f"""
        <div style="background:#161b22;border:1px solid {border_color};border-radius:10px;padding:10px;margin-bottom:8px;">
          <div style="font-size:12px;font-weight:700;color:#8b949e;margin-bottom:6px;">{emoji} {title}</div>
          <div style="display:flex;gap:6px;flex-wrap:wrap;">
        """)
        for t in tickers_list:
            _h(f'<span style="background:#0d1117;color:{color};padding:4px 10px;border-radius:6px;font-size:12px;font-weight:700;border:1px solid {border_color};">{t}</span>')
        _h("</div></div>")

    # 5 markets
    render_card_group("US Longs", "🇺🇸", tickers.get("us_longs", [])[:6], "#3fb950", "#1a4d2e")
    render_card_group("US Shorts", "🇺🇸", tickers.get("us_shorts", [])[:4], "#f85149", "#5c1a1a")
    render_card_group("IHSG", "🇮🇩", tickers.get("ihsg_buys", [])[:6], "#fb923c", "#5c2b00")
    render_card_group("FX", "💱", tickers.get("fx_longs", [])[:4], "#58a6ff", "#1a3a5c")
    render_card_group("Commodities", "🛢️", tickers.get("commodity_longs", [])[:5], "#fb923c", "#5c2b00")
    render_card_group("Crypto", "🔐", tickers.get("crypto_longs", [])[:5], "#a371f7", "#3c1a5c")

    # Narrative + Bottleneck extras (compact pills)
    st.markdown('<div style="font-size:14px;font-weight:700;color:#e6edf3;margin:12px 0 8px;">📰 Narrative & Adaptive Extras</div>', unsafe_allow_html=True)
    extra_pills = []
    if narr and narr.get("active_narratives"):
        for n in narr["active_narratives"][:2]:
            for b in n.get("primary_beneficiaries", [])[:2]:
                extra_pills.append(f'<span style="background:#21262d;color:#fb923c;padding:3px 8px;border-radius:4px;font-size:11px;">📰 {n.get("name","")[:10]}: {b}</span>')
    if btl and btl.get("front_run_basket"):
        for item in btl["front_run_basket"][:4]:
            extra_pills.append(f'<span style="background:#21262d;color:#58a6ff;padding:3px 8px;border-radius:4px;font-size:11px;">🔍 {item.get("ticker","—")}</span>')
    if extra_pills:
        _h(f'<div style="display:flex;gap:6px;flex-wrap:wrap;">' + "".join(extra_pills) + '</div>')
    else:
        st.caption("No extras")