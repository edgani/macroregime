"""intelligence_panel.py

Intelligence Panel — shows USD correlation, global quad, front-run signals, GDPNow.
This is the "FRONT-RUN HEDGEYE" panel.
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
from typing import Dict


def _pill(txt, bg, fg="#fff", size=11):
    return (f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:4px;'
            f'font-size:{size}px;font-weight:600;margin:1px;display:inline-block;">{txt}</span>')


def _mc(label, value, sub="", cls="neu"):
    color = {"good": "#3dbb6c", "warn": "#e5a020", "bad": "#e05252", "neu": "#888"}.get(cls, "#888")
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:8px;padding:8px 12px;margin-bottom:5px;">'
        f'<div style="font-size:9px;font-weight:700;color:#4a5568;letter-spacing:.1em;">{label.upper()}</div>'
        f'<div style="font-size:15px;font-weight:700;color:{color};">{value}</div>'
        + (f'<div style="font-size:10px;opacity:.5;">{sub}</div>' if sub else "") +
        f'</div>', unsafe_allow_html=True,
    )


def render_usd_correlation_panel(snap: Dict) -> None:
    """THE Mythic Variable panel."""
    uc = snap.get("usd_corr", {})
    if not uc or not uc.get("available"):
        st.info("USD Correlation engine loading...")
        return

    usd_trend = uc.get("usd_trend", "neutral")
    regime = uc.get("regime", "unknown")
    mythic = uc.get("mythic_variable_active", False)
    key_signal = uc.get("key_signal", "")

    trend_col = {"bearish": "#e05252", "bullish": "#3dbb6c", "neutral": "#718096"}.get(usd_trend, "#718096")
    regime_labels = {
        "dollar_dominant": ("🎯 DOLLAR DOMINANT", "#e53e3e"),
        "dollar_primary": ("⚡ Dollar Primary", "#dd6b20"),
        "dollar_factor": ("• Dollar Factor", "#e5a020"),
        "dollar_fading": ("↗ Dollar Fading", "#68d391"),
        "dollar_decoupled": ("✓ Dollar Decoupled", "#3dbb6c"),
    }
    r_label, r_color = regime_labels.get(regime, (regime, "#718096"))

    # Banner
    st.markdown(
        f'<div style="background:{r_color}18;border:1.5px solid {r_color};border-radius:8px;'
        f'padding:8px 14px;margin-bottom:8px;">'
        f'<div style="font-size:12px;font-weight:700;color:{r_color};">{r_label}</div>'
        + (f'<div style="font-size:10px;color:#e5a020;font-weight:600;">🎯 MYTHIC VARIABLE ACTIVE — Dollar drives everything</div>' if mythic else "")
        + f'<div style="font-size:11px;color:#a0aec0;margin-top:2px;">{key_signal}</div>'
        f'</div>', unsafe_allow_html=True,
    )

    # Correlation table
    corrs = uc.get("correlations", {})
    important = ["SPX", "BTC", "GOLD", "BRENT", "EEM", "HK", "MEXICO", "JKSE", "VIX"]
    rows = []
    for asset in important:
        d = corrs.get(asset, {})
        if not d:
            continue
        c15 = d.get("corr_15d")
        c30 = d.get("corr_30d")
        action = d.get("action", "neutral")
        conv = d.get("conviction", 0)
        action_col = {"strong_buy": "#3dbb6c", "buy_dip": "#68d391", "overweight": "#e5a020",
                      "avoid_short": "#e05252", "neutral": "#4a5568"}.get(action, "#4a5568")
        rows.append({
            "Asset": asset,
            "15D Corr": f"{c15:.2f}" if c15 is not None else "—",
            "30D Corr": f"{c30:.2f}" if c30 is not None else "—",
            "Action": action.replace("_", " ").upper(),
            "Conv": f"{conv:.0%}",
        })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True, height=280)

    # Front-run signals
    frs = uc.get("front_run_signals", [])
    if frs:
        st.markdown("**⚡ USD Front-Run Signals:**")
        for sig in frs[:4]:
            priority_col = {"high": "#e05252", "medium": "#e5a020"}.get(sig.get("priority"), "#718096")
            st.markdown(
                f'<div style="padding:4px 8px;border-left:2px solid {priority_col};margin-bottom:2px;font-size:11px;color:#a0aec0;">'
                f'{sig["signal"]}</div>', unsafe_allow_html=True,
            )


def render_global_quad_panel(snap: Dict) -> None:
    """Global Quad: 50-country classification."""
    gq = snap.get("global_quad", {})
    if not gq or not gq.get("countries"):
        st.info("Global Quad engine loading...")
        return

    g_quad = gq.get("global_quad", "Q?")
    g_conf = gq.get("global_confidence", 0)
    g_probs = gq.get("global_probs", {})

    quad_colors = {"Q1": "#276749", "Q2": "#b7791f", "Q3": "#c53030", "Q4": "#553030", "Q?": "#4a5568"}
    q_col = quad_colors.get(g_quad, "#4a5568")

    cols = st.columns([1,2])
    with cols[0]:
        st.markdown(
            f'<div style="background:{q_col}22;border:2px solid {q_col};border-radius:8px;'
            f'padding:10px;text-align:center;">'
            f'<div style="font-size:9px;color:#4a5568;font-weight:700;">GLOBAL QUAD</div>'
            f'<div style="font-size:28px;font-weight:800;color:{q_col};">{g_quad}</div>'
            f'<div style="font-size:10px;color:#718096;">{g_conf:.0%} conf</div>'
            f'</div>', unsafe_allow_html=True,
        )
    with cols[1]:
        st.markdown(f'**Why Long HK:** {gq.get("why_long_hong_kong","")[:120]}...')
        st.markdown(f'**Why Avoid IHSG:** {gq.get("why_avoid_indonesia","")[:120]}...')

    # Top longs/shorts
    tl = gq.get("top_longs", [])
    ts = gq.get("top_shorts", [])

    if tl:
        st.markdown("**Global Top Longs:**")
        st.markdown(" ".join(_pill(f"{name} ({etf})", "#1a3a2a") for name, etf, _ in tl[:5]),
                    unsafe_allow_html=True)
    if ts:
        st.markdown("**Global Avoid/Short:**")
        st.markdown(" ".join(_pill(f"{name} ({etf})", "#3a1a1a") for name, etf, _ in ts[:3]),
                    unsafe_allow_html=True)

    # Country table
    countries = gq.get("countries", {})
    rows = []
    for name, d in sorted(countries.items(), key=lambda x: x[1].get("composite_score",0), reverse=True):
        rows.append({
            "Country": name,
            "ETF": d.get("etf",""),
            "Quad": d.get("quad","?"),
            "Score": f"{d.get('composite_score',0):.0%}",
            "Action": d.get("action","?"),
            "1M": f"{d.get('r1m',0)*100:.1f}%" if d.get("r1m") else "—",
            "vs Hedgeye": d.get("our_vs_hedgeye",""),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True, height=400)

    frc = gq.get("front_run_candidates", [])
    if frc:
        st.markdown("**🔮 Front-Run Candidates (pre-transition):**")
        for c in frc[:3]:
            st.markdown(
                f'<div style="font-size:10px;padding:2px 6px;border-left:2px solid #e5a020;color:#a0aec0;">'
                f'<b>{c["country"]} ({c["etf"]})</b> — {c["signal"]}</div>',
                unsafe_allow_html=True,
            )


def render_frontrun_panel(snap: Dict) -> None:
    """Front-Run Engine: Signal + Quad ticker selection."""
    fr = snap.get("frontrun", {})
    if not fr:
        st.info("Front-Run engine loading...")
        return

    # Regime summary
    st.markdown(
        f'<div style="background:#1a202c;border-radius:6px;padding:8px 12px;margin-bottom:8px;'
        f'font-size:11px;color:#a0aec0;">{fr.get("regime_summary","")}</div>',
        unsafe_allow_html=True,
    )

    t1, t2, t3 = st.tabs(["⚡ Front-Run Alerts", "📊 Tickers NOW", "🎭 3 Big Themes"])

    with t1:
        alerts = fr.get("frontrun_alerts", [])
        if not alerts:
            st.info("No high-priority front-run alerts currently.")
        for alert in alerts:
            priority_col = "#e05252" if alert.get("priority") == "high" else "#e5a020"
            st.markdown(
                f'<div style="background:{priority_col}12;border:1px solid {priority_col};'
                f'border-radius:5px;padding:6px 10px;margin-bottom:4px;font-size:11px;">'
                f'<span style="color:{priority_col};font-weight:700;">{alert["alert"]}</span>'
                f' <span style="color:#718096;">Conv: {alert["conviction"]:.0%}</span>'
                f'</div>', unsafe_allow_html=True,
            )

        # Current Hedgeye risk ranges
        pb = fr.get("current_playbook", {})
        rr = pb.get("risk_ranges", {})
        if rr:
            st.markdown("**Hedgeye Risk Ranges (April 20, 2026):**")
            rows = [{"Asset": k, "Range": v["range"], "Signal": v["signal"].upper()}
                    for k, v in rr.items()]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=350)

    with t2:
        col1, col2 = st.columns(2)
        tl = fr.get("top_longs", [])
        ts = fr.get("top_shorts", [])
        with col1:
            st.markdown("**🟢 Top Longs (Signal + Quad aligned):**")
            for tk, conv, trade, trend in tl[:8]:
                t_col = "#3dbb6c" if trade == "bullish" else "#e05252" if trade == "bearish" else "#718096"
                tr_col = "#3dbb6c" if trend == "bullish" else "#e05252" if trend == "bearish" else "#718096"
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:6px;padding:3px 0;">'
                    f'<span style="font-size:12px;font-weight:700;width:50px;">{tk}</span>'
                    f'<span style="font-size:10px;color:{t_col};">TRADE:{trade[:4].upper()}</span>'
                    f'<span style="font-size:10px;color:{tr_col};">TREND:{trend[:4].upper()}</span>'
                    f'<span style="font-size:10px;color:#3dbb6c;">{conv:.0%}</span>'
                    f'</div>', unsafe_allow_html=True,
                )
        with col2:
            st.markdown("**🔴 Top Shorts (Signal + Quad aligned):**")
            for tk, conv, trade, trend in ts[:6]:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:6px;padding:3px 0;">'
                    f'<span style="font-size:12px;font-weight:700;width:50px;">{tk}</span>'
                    f'<span style="font-size:10px;color:#e05252;font-weight:600;">SHORT</span>'
                    f'<span style="font-size:10px;color:#e05252;">{conv:.0%}</span>'
                    f'</div>', unsafe_allow_html=True,
                )

    with t3:
        themes = fr.get("three_structural_themes", [])
        for theme in themes:
            with st.expander(f"📌 {theme['name']} — Stage: {theme.get('stage','?').upper()}"):
                st.markdown(theme["description"])
                tl_t = theme.get("tickers_long", [])
                ts_t = theme.get("tickers_short", [])
                if tl_t:
                    st.markdown("**Long:** " + " ".join(_pill(t, "#1a3a2a") for t in tl_t),
                                unsafe_allow_html=True)
                if ts_t:
                    st.markdown("**Avoid/Short:** " + " ".join(_pill(t, "#3a1a1a") for t in ts_t),
                                unsafe_allow_html=True)
                st.caption(f"🔑 {theme.get('hedgeye_note','')}")


def render_regional_survey_panel(snap: Dict) -> None:
    """Regional Fed Survey composite panel."""
    rs = snap.get("regional_surveys", {})
    if not rs or not rs.get("available"):
        st.info("Regional survey data loading...")
        return

    no = rs.get("new_orders_composite", 0)
    pp = rs.get("prices_paid_composite", 0)
    capex = rs.get("capex_plans_composite", 0)
    spread = rs.get("inflation_spread", 0)

    no_class = rs.get("new_orders_class", {})
    pp_class = rs.get("prices_paid_class", {})
    capex_class = rs.get("capex_class", {})

    cols = st.columns(4)
    with cols[0]:
        _mc("New Orders", f"{no:.0f}", no_class.get("level",""), "good" if no >= 15 else ("warn" if no >= 0 else "bad"))
    with cols[1]:
        _mc("Prices Paid", f"{pp:.0f}", pp_class.get("level",""), "bad" if pp >= 70 else ("warn" if pp >= 55 else "good"))
    with cols[2]:
        _mc("CapEx Plans", f"{capex:.0f}", capex_class.get("level",""), "good" if capex >= 15 else "warn")
    with cols[3]:
        _mc("Price Spread", f"{spread:.0f}", "paid vs received", "bad" if spread >= 15 else ("warn" if spread >= 5 else "good"))

    macro_note = rs.get("macro_note", "")
    macro_col = {"hybrid_q2_q3": "#dd6b20", "q3_confirmed": "#e05252",
                 "q1_signal": "#3dbb6c", "mixed": "#718096"}.get(rs.get("macro_signal",""), "#718096")
    if macro_note:
        st.markdown(
            f'<div style="background:{macro_col}15;border-left:3px solid {macro_col};'
            f'padding:6px 10px;margin:4px 0;font-size:11px;color:#a0aec0;">{macro_note}</div>',
            unsafe_allow_html=True,
        )

    fr_note = rs.get("front_run_note", "")
    if fr_note:
        st.markdown(
            f'<div style="background:#276749;border-radius:5px;padding:6px 10px;'
            f'font-size:11px;color:#68d391;font-weight:600;">{fr_note}</div>',
            unsafe_allow_html=True,
        )


def render_gdpnow_indicator(snap: Dict) -> None:
    """GDPNow forward-looking GDP strip."""
    gn = snap.get("gdpnow", {})
    if not gn or not gn.get("available"):
        st.caption("GDPNow: unavailable")
        return

    est = gn.get("estimate_pct", 0)
    trend = gn.get("growth_trend", "?")
    q_bias = gn.get("q_bias", "?")
    note = gn.get("hedgeye_note", "")
    color = gn.get("color", "#718096")

    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:8px;padding:3px 10px;'
        f'background:{color}15;border:1px solid {color}33;border-radius:6px;">'
        f'<span style="font-size:10px;font-weight:700;color:{color};">GDPNow: {est:.1f}%</span>'
        f'<span style="font-size:10px;color:#718096;">{trend} → {q_bias}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if note:
        st.caption(note)
