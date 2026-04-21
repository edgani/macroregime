"""ui/command_center_page.py — Dark Card Command Center (v10 visual)"""
from __future__ import annotations
from typing import Dict

import streamlit as st
import pandas as pd

def render_command_center(snap: Dict) -> None:
    q = snap.get("q", {})
    f = snap.get("f", {})
    quad = q.get("quad", "Q?")
    monthly_quad = q.get("monthly_quad", quad)
    global_quad = q.get("global_quad", quad)
    conf = q.get("confidence", 0.0)
    divergence = q.get("divergence", "aligned")
    vix = q.get("vix_last", 20.0)
    most_hated = snap.get("most_hated_rally", {})
    transition = snap.get("regime_transition", {})
    tickers = snap.get("regime_tickers", {})

    # ── Color helpers ──
    QC = {
        "Q1": ("#1a4d2e", "#4ade80"),
        "Q2": ("#5c3d00", "#fbbf24"),
        "Q3": ("#5c2b00", "#fb923c"),
        "Q4": ("#5c1a1a", "#f87171"),
    }
    def qbg(q): return QC.get(q, ("#2d3748", "#a0aec0"))[0]
    def qfg(q): return QC.get(q, ("#2d3748", "#a0aec0"))[1]

    # ── Regime Pills Row ──
    s_bg, s_fg = qbg(quad), qfg(quad)
    m_bg, m_fg = qbg(monthly_quad), qfg(monthly_quad)
    div_color = "#f85149" if divergence == "divergent" else "#3fb950"
    div_text = "DIVERGEN" if divergence == "divergent" else "ALIGNED"
    div_icon = "⚡" if divergence == "divergent" else "✅"
    
    # Time horizon
    horizon = transition.get("front_run_window", "1-2W")
    if horizon in ("now", "1-2w", "1-2W"):
        horiz_label = "1-2W"
        horiz_icon = "🕐"
    elif horizon in ("3-6w", "3-6W"):
        horiz_label = "3-6W"
        horiz_icon = "📅"
    else:
        horiz_label = horizon
        horiz_icon = "⏳"

    # VIX label
    vix_label = "normal" if vix < 20 else "elevated" if vix < 25 else "high"
    vix_color = "#3fb950" if vix < 20 else "#d29922" if vix < 25 else "#f85149"
    cap = snap.get("options_regime", {}).get("vix_sizing_cap", 0.85)
    
    # Relief / regime state
    regime_state = "Relief" if "relief" in str(q.get("operating_regime", "")).lower() else q.get("operating_regime", "—")
    state_color = "#3fb950" if "Relief" in regime_state else "#d29922"

    st.markdown(
        f"""
        <div style="background:#0d1117;border:1px solid #30363d;border-radius:12px;padding:14px;margin-bottom:14px;">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <span style="background:{s_bg};color:{s_fg};padding:5px 12px;border-radius:20px;font-size:12px;font-weight:700;">
                    S: {quad}
                </span>
                <span style="background:{m_bg};color:{m_fg};padding:5px 12px;border-radius:20px;font-size:12px;font-weight:700;">
                    M: {monthly_quad}
                </span>
                <span style="background:#21262d;color:{div_color};padding:5px 12px;border-radius:20px;font-size:12px;font-weight:700;border:1px solid {div_color}33;">
                    {div_icon} {div_text}
                </span>
                <span style="background:#21262d;color:#c9d1d9;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid #30363d;">
                    Conf: {conf:.0%}
                </span>
                <span style="background:#21262d;color:#8b949e;padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid #30363d;">
                    {horiz_icon} {horiz_label}
                </span>
                <span style="background:#21262d;color:{state_color};padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid {state_color}33;">
                    {regime_state}
                </span>
                <span style="background:#21262d;color:{vix_color};padding:5px 12px;border-radius:20px;font-size:12px;font-weight:600;border:1px solid #30363d;">
                    VIX {vix:.1f} ({vix_label}) · cap {cap:.0%}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Ticker Pills ──
    us_longs = tickers.get("us_longs", [])[:1]
    ihsg_buys = tickers.get("ihsg_buys", [])[:1]
    us_shorts = tickers.get("us_shorts", [])[:1]
    
    ticker_pills = []
    for t in us_longs:
        ticker_pills.append(f'<span style="color:#3fb950;font-weight:700;">▲ {t}</span>')
    for t in ihsg_buys:
        ticker_pills.append(f'<span style="color:#fb923c;font-weight:700;">🇮🇩 {t}</span>')
    for t in us_shorts:
        ticker_pills.append(f'<span style="color:#f85149;font-weight:700;">▼ {t}</span>')
    
    if ticker_pills:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;font-size:13px;">' +
            " · ".join(ticker_pills) +
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Realtime Transitional Banner ──
    if conf < 0.25 or divergence == "divergent":
        st.markdown(
            f"""
            <div style="background:#341a00;border:1px solid #d29922;border-radius:10px;padding:12px;margin-bottom:16px;">
                <div style="color:#d29922;font-size:13px;font-weight:700;margin-bottom:4px;">
                    ⚠️ TRANSITIONAL — {quad}/{monthly_quad} Confidence {conf:.0%} terlalu rendah. Regime belum confirmed.
                </div>
                <div style="color:#c9d1d9;font-size:12px;">
                    Trade monthly signal saja, jangan buka structural positions.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Front-Run Checklist ──
    st.markdown('<div style="font-size:16px;font-weight:700;color:#e6edf3;margin-bottom:10px;">🎯 FRONT-RUN CHECKLIST</div>', unsafe_allow_html=True)
    if transition and transition.get("front_run_window") != "—":
        st.success(f"**Window:** {transition.get('front_run_window', '—')} | **Rationale:** {transition.get('front_run_rationale', '—')}")
        early = transition.get("early_warning_signals", [])
        if early:
            cols = st.columns(len(early))
            for i, e in enumerate(early):
                with cols[i]:
                    st.info(e)
    else:
        st.info("No transition signals — regime stable.")

    # ── Narrative Plays ──
    st.divider()
    st.markdown('<div style="font-size:16px;font-weight:700;color:#e6edf3;margin-bottom:10px;">📰 NARRATIVE PLAYS</div>', unsafe_allow_html=True)
    narr = snap.get("narrative_discovery", {})
    if narr and narr.get("active_narratives"):
        for n in narr["active_narratives"][:4]:
            stage = n.get("stage", "—")
            emoji = {"early": "🌱", "building": "🔥", "mature": "♟️", "exhausted": "💀", "watching": "👀"}.get(stage, "◆")
            with st.container(border=True):
                col_a, col_b = st.columns([4, 1])
                with col_a:
                    st.markdown(f"{emoji} **{n.get('name', '—')}** · *{stage}* · Conviction: **{n.get('regime_adjusted_conviction', 0):.0%}** · Regime fit: **{n.get('regime_multiplier', 1.0):.2f}x**")
                    st.caption(n.get("action_summary", ""))
                    if n.get("claude_insight"):
                        st.caption(f"🧠 {n.get('claude_insight', '')}")
                with col_b:
                    bens = n.get("primary_beneficiaries", [])
                    for b in bens[:5]:
                        st.markdown(f"`{b}`")
    else:
        st.info("No active narratives. Regime-driven mode.")

    # ── Adaptive Bottleneck ──
    st.divider()
    st.markdown('<div style="font-size:16px;font-weight:700;color:#e6edf3;margin-bottom:10px;">🔍 ADAPTIVE BOTTLENECK SCAN</div>', unsafe_allow_html=True)
    btl = snap.get("bottleneck_discovery", {})
    if btl:
        method = btl.get("discovery_method", "unknown")
        st.caption(f"Method: **{method}** | Scanned all tickers | No hardcoded library")
        if btl.get("summary"):
            st.info(btl["summary"])

        if btl.get("active_sectors"):
            st.markdown("**📊 Auto-Discovered Sectors**")
            for sector in btl["active_sectors"][:5]:
                with st.container(border=True):
                    sc1, sc2, sc3, sc4 = st.columns([3, 1, 1, 1])
                    with sc1:
                        stage_color = {"mature": "red", "building": "orange", "early": "green"}.get(sector.get("stage"), "gray")
                        st.markdown(f"**{sector.get('sector_name', '—')}** · :{stage_color}[{sector.get('stage', '—')}]")
                        st.caption(f"Tickers: {', '.join(sector.get('tickers', [])[:8])}")
                        st.caption(f"Markets: {', '.join(sector.get('markets', []))}")
                    with sc2:
                        st.metric("Score", f"{sector.get('bottleneck_score', 0):.2f}")
                    with sc3:
                        st.metric("SPY Corr", f"{sector.get('spy_correlation', 0):.2f}")
                    with sc4:
                        st.metric("Vol Z", f"{sector.get('avg_volume_zscore', 0):.2f}")

        if btl.get("front_run_basket"):
            st.markdown("**🎯 Adaptive Front-Run Basket**")
            basket = btl["front_run_basket"][:12]
            if basket:
                cols = ["ticker", "market", "sector", "conviction", "stage", "r1m", "r3m", "volume_zscore", "position_size", "source"]
                df_b = pd.DataFrame([{k: item.get(k, "—") for k in cols} for item in basket])
                st.dataframe(df_b, use_container_width=True, hide_index=True)
    else:
        st.info("Bottleneck discovery loading...")

    # ── Master Ticker Board ──
    st.divider()
    st.markdown('<div style="font-size:16px;font-weight:700;color:#e6edf3;margin-bottom:10px;">📋 MASTER TICKER BOARD</div>', unsafe_allow_html=True)
    all_tickers = []
    if tickers:
        for side, tickers_list in [
            ("US Longs", tickers.get("us_longs", [])), ("US Shorts", tickers.get("us_shorts", [])),
            ("IHSG Buys", tickers.get("ihsg_buys", [])), ("FX Longs", tickers.get("fx_longs", [])),
            ("Commodity Longs", tickers.get("commodity_longs", [])), ("Crypto Longs", tickers.get("crypto_longs", [])),
        ]:
            for t in tickers_list:
                all_tickers.append({"ticker": t, "source": "Regime", "side": side})

    if btl and btl.get("front_run_basket"):
        for item in btl["front_run_basket"][:8]:
            all_tickers.append({
                "ticker": item.get("ticker", "—"), "source": "Adaptive",
                "side": item.get("sector", ""), "conviction": item.get("conviction", 0),
                "position_size": item.get("position_size", ""),
            })

    narr = snap.get("narrative_discovery", {})
    if narr and narr.get("active_narratives"):
        for n in narr["active_narratives"][:3]:
            for b in n.get("primary_beneficiaries", [])[:3]:
                all_tickers.append({
                    "ticker": b, "source": "Narrative", "side": n.get("name", ""),
                    "conviction": n.get("regime_adjusted_conviction", 0),
                })

    if all_tickers:
        df_board = pd.DataFrame(all_tickers)
        st.dataframe(df_board, use_container_width=True, hide_index=True)
    else:
        st.info("Building ticker board...")

    # ── Rally Monitor ──
    if most_hated:
        st.divider()
        st.markdown('<div style="font-size:16px;font-weight:700;color:#e6edf3;margin-bottom:10px;">📈 MOST HATED RALLY MONITOR</div>', unsafe_allow_html=True)
        clear = most_hated.get("clear_count", 0)
        st.progress(clear / 4.0, text=f"{clear}/4 checklist items clear")
        st.markdown(f"**Stage:** {most_hated.get('stage', 'monitor')} · **Action:** {most_hated.get('action', 'Selective')}")