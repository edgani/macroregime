"""ui/command_center_page.py — Merged Opportunity Board"""
from __future__ import annotations
from typing import Dict
import streamlit as st
import pandas as pd

def render_command_center(snap: Dict) -> None:
    q = snap.get("q", {})
    f = snap.get("f", {})
    quad = q.get("quad", "Q?")
    monthly_quad = q.get("monthly_quad", quad)
    conf = q.get("confidence", 0.0)
    divergence = q.get("divergence", "aligned")
    vix = q.get("vix_last", 20.0)
    transition = snap.get("regime_transition", {})
    tickers = snap.get("regime_tickers", {})
    narr = snap.get("narrative_discovery", {})
    btl = snap.get("bottleneck_discovery", {})
    prices = snap.get("prices", {})

    def _h(html: str) -> None:
        st.markdown(" ".join(html.split()), unsafe_allow_html=True)

    QC = {"Q1": ("#1a4d2e", "#4ade80"), "Q2": ("#5c3d00", "#fbbf24"), "Q3": ("#5c2b00", "#fb923c"), "Q4": ("#5c1a1a", "#f87171")}
    def qbg(q): return QC.get(q, ("#2d3748", "#a0aec0"))[0]
    def qfg(q): return QC.get(q, ("#2d3748", "#a0aec0"))[1]

    s_bg, s_fg = qbg(quad), qfg(quad)
    m_bg, m_fg = qbg(monthly_quad), qfg(monthly_quad)
    div_color = "#f85149" if divergence == "divergent" else "#3fb950"
    div_text = "DIVERGEN" if divergence == "divergent" else "ALIGNED"
    div_icon = "⚡" if divergence == "divergent" else "✅"

    horizon = transition.get("front_run_window", "1-2W")
    horiz_label = "1-2W" if horizon in ("now", "1-2w", "1-2W") else "3-6W" if horizon in ("3-6w", "3-6W") else horizon
    horiz_icon = "🕐" if "1-2" in str(horiz_label) else "📅" if "3-6" in str(horiz_label) else "⏳"

    vix_label = "normal" if vix < 20 else "elevated" if vix < 25 else "high"
    vix_color = "#3fb950" if vix < 20 else "#d29922" if vix < 25 else "#f85149"
    cap = snap.get("options_regime", {}).get("vix_sizing_cap", 0.85)
    regime_state = "Relief" if "relief" in str(q.get("operating_regime", "")).lower() else q.get("operating_regime", "—")
    state_color = "#3fb950" if "Relief" in regime_state else "#d29922"

    # ── Regime Pills ──
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

    # ── Ticker Pills ──
    us_longs = tickers.get("us_longs", [])[:1]
    ihsg_buys = tickers.get("ihsg_buys", [])[:1]
    us_shorts = tickers.get("us_shorts", [])[:1]
    pills = []
    for t in us_longs: pills.append(f'<span style="color:#3fb950;font-weight:700;">▲ {t}</span>')
    for t in ihsg_buys: pills.append(f'<span style="color:#fb923c;font-weight:700;">🇮🇩 {t}</span>')
    for t in us_shorts: pills.append(f'<span style="color:#f85149;font-weight:700;">▼ {t}</span>')
    if pills:
        _h(f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;font-size:13px;">{" · ".join(pills)}</div>')

    # ── Transitional Banner ──
    if conf < 0.25 or divergence == "divergent":
        _h(f"""
        <div style="background:#341a00;border:1px solid #d29922;border-radius:10px;padding:12px;margin-bottom:16px;">
          <div style="color:#d29922;font-size:13px;font-weight:700;margin-bottom:4px;">⚠️ TRANSITIONAL — {quad}/{monthly_quad} Conf {conf:.0%} terlalu rendah. Regime belum confirmed.</div>
          <div style="color:#c9d1d9;font-size:12px;">Trade monthly signal saja, jangan buka structural positions.</div>
        </div>
        """)

    # ═════════════════════════════════════════════════════════════════
    # MERGED: Live Opportunities (Front-Run + Narrative + Bottleneck)
    # ═════════════════════════════════════════════════════════════════
    st.markdown('<div style="font-size:16px;font-weight:700;color:#e6edf3;margin:16px 0 10px;">🎯 LIVE OPPORTUNITIES</div>', unsafe_allow_html=True)

    # Front-run window
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

    # Narrative + Bottleneck basket merge
    opp_rows = []
    
    # From narratives
    if narr and narr.get("active_narratives"):
        for n in narr["active_narratives"][:4]:
            stage = n.get("stage", "—")
            emoji = {"early": "🌱", "building": "🔥", "mature": "♟️", "exhausted": "💀"}.get(stage, "◆")
            for b in n.get("primary_beneficiaries", [])[:3]:
                opp_rows.append({
                    "Source": f"{emoji} {n.get('name', '—')[:20]}",
                    "Ticker": b,
                    "Stage": stage,
                    "Conv": f"{n.get('regime_adjusted_conviction', 0):.0%}",
                    "Type": "Narrative",
                })

    # From bottleneck basket
    if btl and btl.get("front_run_basket"):
        for item in btl["front_run_basket"][:8]:
            opp_rows.append({
                "Source": "🔍 Bottleneck",
                "Ticker": item.get("ticker", "—"),
                "Stage": item.get("stage", "—"),
                "Conv": f"{item.get('conviction', 0):.0%}" if isinstance(item.get('conviction'), (int, float)) else str(item.get('conviction', '—')),
                "Type": "Adaptive",
            })

    # From regime tickers
    if tickers:
        for side, lst in [("▲ US Long", "us_longs"), ("🇮🇩 IHSG", "ihsg_buys"), ("▼ US Short", "us_shorts")]:
            for t in tickers.get(lst, [])[:3]:
                opp_rows.append({"Source": side, "Ticker": t, "Stage": "now", "Conv": "—", "Type": "Regime"})

    if opp_rows:
        df_opp = pd.DataFrame(opp_rows)
        st.dataframe(df_opp, use_container_width=True, hide_index=True)
    else:
        st.info("No opportunities detected.")

    # ═════════════════════════════════════════════════════════════════
    # MERGED: Market Heatmap (from old Markets tab)
    # ═════════════════════════════════════════════════════════════════
    st.markdown('<div style="font-size:16px;font-weight:700;color:#e6edf3;margin:16px 0 10px;">🌍 MARKET HEATMAP</div>', unsafe_allow_html=True)
    
    if prices:
        ASSETS = {
            "SPY": "US Equity", "QQQ": "Growth", "IWM": "Small Cap",
            "TLT": "Long Bond", "HYG": "Credit", "GLD": "Gold",
            "CL=F": "Oil", "HG=F": "Copper", "UUP": "USD", "EEM": "EM",
            "^JKSE": "IHSG", "BTC-USD": "BTC", "ETH-USD": "ETH",
        }
        def ret_n(s, n):
            if s is None or len(s) < n+1: return float("nan")
            try:
                b = float(s.iloc[-(n+1)]); e = float(s.iloc[-1])
                return float(e/b-1) if b != 0 else float("nan")
            except: return float("nan")
        
        heat = []
        for tk, name in ASSETS.items():
            s = prices.get(tk)
            if s is not None:
                heat.append({
                    "Asset": name, "Ticker": tk,
                    "1W": f"{ret_n(s, 5):+.1%}" if ret_n(s, 5) == ret_n(s, 5) else "—",
                    "1M": f"{ret_n(s, 21):+.1%}" if ret_n(s, 21) == ret_n(s, 21) else "—",
                    "3M": f"{ret_n(s, 63):+.1%}" if ret_n(s, 63) == ret_n(s, 63) else "—",
                })
        if heat:
            st.dataframe(pd.DataFrame(heat), use_container_width=True, hide_index=True)

    # ═════════════════════════════════════════════════════════════════
    # MERGED: Sector Leadership (compact)
    # ═════════════════════════════════════════════════════════════════
    st.markdown('<div style="font-size:16px;font-weight:700;color:#e6edf3;margin:16px 0 10px;">📊 SECTOR LEADERSHIP</div>', unsafe_allow_html=True)
    SECS = {"XLE": "Energy", "XLF": "Fin", "XLI": "Ind", "XLB": "Mat", "XLK": "Tech", "XLV": "Health", "XLY": "Con.D", "XLP": "Con.S", "XLU": "Util", "XLRE": "RE", "XLC": "Comm"}
    spy3 = ret_n(prices.get("SPY"), 63)
    sec_rows = []
    for tk, name in SECS.items():
        s = prices.get(tk)
        if s is not None and len(s) > 63:
            r3 = ret_n(s, 63)
            rel = (r3 - spy3) if spy3 == spy3 and r3 == r3 else float("nan")
            sec_rows.append({"Sector": name, "3M": f"{r3:+.1%}" if r3 == r3 else "—", "vs SPY": f"{rel:+.1%}" if rel == rel else "—"})
    if sec_rows:
        sec_rows.sort(key=lambda r: float(r["vs SPY"].replace("%", "").replace("—", "0").replace("+", "")) if r["vs SPY"] != "—" else -999, reverse=True)
        st.dataframe(pd.DataFrame(sec_rows[:8]), use_container_width=True, hide_index=True)

    # ═════════════════════════════════════════════════════════════════
    # Adaptive Bottleneck Detail (optional expander)
    # ═════════════════════════════════════════════════════════════════
    if btl:
        with st.expander("🔍 Full Adaptive Bottleneck Scan", expanded=False):
            st.caption(f"Method: {btl.get('discovery_method', 'unknown')}")
            if btl.get("summary"): st.info(btl["summary"])
            if btl.get("active_sectors"):
                for sector in btl["active_sectors"][:5]:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 1, 1])
                        with c1:
                            st.markdown(f"**{sector.get('sector_name', '—')}** · {sector.get('stage', '—')}")
                            st.caption(f"{', '.join(sector.get('tickers', [])[:6])}")
                        with c2: st.metric("Score", f"{sector.get('bottleneck_score', 0):.2f}")
                        with c3: st.metric("Vol Z", f"{sector.get('avg_volume_zscore', 0):.2f}")

    # ═════════════════════════════════════════════════════════════════
    # Master Ticker Board (compact)
    # ═════════════════════════════════════════════════════════════════
    st.markdown('<div style="font-size:16px;font-weight:700;color:#e6edf3;margin:16px 0 10px;">📋 MASTER BOARD</div>', unsafe_allow_html=True)
    all_tickers = []
    if tickers:
        for side, key in [("Long", "us_longs"), ("Short", "us_shorts"), ("IHSG", "ihsg_buys"), ("FX", "fx_longs"), ("Comm", "commodity_longs"), ("Crypto", "crypto_longs")]:
            for t in tickers.get(key, [])[:4]:
                all_tickers.append({"Ticker": t, "Side": side, "Source": "Regime"})
    if btl and btl.get("front_run_basket"):
        for item in btl["front_run_basket"][:6]:
            all_tickers.append({"Ticker": item.get("ticker", "—"), "Side": item.get("sector", "—"), "Source": "Adaptive"})
    if all_tickers:
        st.dataframe(pd.DataFrame(all_tickers), use_container_width=True, hide_index=True)
    else:
        st.info("Building board...")