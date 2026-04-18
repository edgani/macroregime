"""command_center_page.py

THE unified decision cockpit. All critical information in one view.
No more clicking between tabs to piece together the picture.

Layout:
┌─────────────────────────────────────────────────────────────────┐
│  STATUS STRIP: Regime | Front-Run | News | VIX | Best Picks     │
└─────────────────────────────────────────────────────────────────┘
┌────────────┬────────────────────────┬───────────────────────────┐
│  REGIME    │  TRANSITION RADAR      │  NARRATIVE INTELLIGENCE   │
│  CARD      │  (early warning)       │  (XNDU-style plays)       │
└────────────┴────────────────────────┴───────────────────────────┘
┌──────────────────────────────────────────────────────────────────┐
│  MASTER TICKER BOARD (all 5 markets in one table)                │
└──────────────────────────────────────────────────────────────────┘
┌─────────────────────┬──────────────────────┬────────────────────┐
│  TOP SCENARIOS      │  NEWS INTELLIGENCE   │  SIZING GUIDE      │
└─────────────────────┴──────────────────────┴────────────────────┘
┌──────────────────────────────────────────────────────────────────┐
│  FRONT-RUN DETAIL + POSITION LIFECYCLE                           │
└──────────────────────────────────────────────────────────────────┘
"""
from __future__ import annotations
import streamlit as st
import pandas as pd


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

def _qb(quad: str) -> str:
    colors = {
        "Q1": ("🟢", "#276749", "#d4edda", "#155724"),
        "Q2": ("🟡", "#b7791f", "#fff3cd", "#856404"),
        "Q3": ("🟠", "#c05621", "#ffeeba", "#7d4e00"),
        "Q4": ("🔴", "#c53030", "#f8d7da", "#721c24"),
    }
    em, border, bg, fg = colors.get(quad, ("⚪", "#718096", "#e2e3e5", "#495057"))
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;'
        f'background:{bg};color:{fg};border:1px solid {border};font-weight:700;font-size:12px;">'
        f'{em} {quad}</span>'
    )


def _fw_badge(window: str) -> str:
    cfg = {
        "now":    ("#e53e3e", "⚡ FRONT-RUN: NOW"),
        "1-2w":   ("#dd6b20", "🕐 FRONT-RUN: 1-2W"),
        "3-6w":   ("#d69e2e", "🕒 FRONT-RUN: 3-6W"),
        "not yet":("#718096", "⏸ NO WINDOW"),
    }
    color, label = cfg.get(window, ("#718096", "⏸ NO WINDOW"))
    return (
        f'<span style="background:{color}22;border:1px solid {color};color:{color};'
        f'padding:3px 10px;border-radius:10px;font-weight:700;font-size:11px;">{label}</span>'
    )


def _news_badge(state: str) -> str:
    cfg = {
        "war_oil":                ("#e53e3e", "🔥 War/Oil"),
        "policy_pressure":        ("#dd6b20", "📈 Policy Pressure"),
        "credit_stress":          ("#c53030", "💀 Credit Stress"),
        "deescalation_confirmed": ("#276749", "✅ De-escal Confirmed"),
        "deescalation_watch":     ("#d69e2e", "👁 De-escal Watch"),
        "oil_shock_fading":       ("#b7791f", "📉 Oil Fading"),
        "quiet":                  ("#4a5568", "💤 Quiet"),
    }
    color, label = cfg.get(state, ("#4a5568", state.replace("_", " ").title()))
    return (
        f'<span style="background:{color}22;border:1px solid {color};color:{color};'
        f'padding:2px 8px;border-radius:8px;font-size:11px;font-weight:600;">{label}</span>'
    )


def _pct(v: float) -> str:
    return f"{v:.0%}"


def _pill(text: str, color: str = "#2b6cb0") -> str:
    return (
        f'<span style="background:{color};color:#fff;padding:2px 7px;'
        f'border-radius:3px;font-size:11px;margin:1px;display:inline-block;">{text}</span>'
    )


def _pills(tickers: list, color: str) -> str:
    return "".join(_pill(t, color) for t in tickers if t)


# ---------------------------------------------------------------------------
# Sub-sections
# ---------------------------------------------------------------------------

def _render_status_strip(core: dict) -> None:
    regime = core.get("regime", {})
    rt = core.get("regime_transition", {})
    news = core.get("news_state", {})
    tickers = core.get("regime_tickers", {})
    opt = core.get("options_regime", {})

    quad = regime.get("structural_quad", regime.get("current_quad", "Q?"))
    monthly = regime.get("monthly_quad", quad)
    conf = float(regime.get("structural_confidence", regime.get("confidence", 0.5)))
    fw = rt.get("front_run_window", "not yet")
    ns = news.get("state", "quiet")
    vix_b = opt.get("vix_bucket", "normal") if opt else "normal"
    vix_v = opt.get("vix_spot", 0.0) if opt else 0.0

    best_us_long = (tickers.get("us_longs") or ["—"])[0]
    best_ihsg = (tickers.get("ihsg_buys") or ["—"])[0]
    best_us_short = (tickers.get("us_shorts") or ["—"])[0]
    ta = rt.get("transition_alert", "")

    vix_color = {"goldilocks": "#276749", "normal": "#718096", "elevated": "#dd6b20", "stress": "#e53e3e", "crisis": "#c53030"}.get(vix_b, "#718096")

    strip = (
        f'<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;'
        f'padding:10px 14px;border-radius:10px;background:rgba(255,255,255,0.03);'
        f'border:1px solid rgba(255,255,255,0.08);margin-bottom:12px;font-size:12px;">'
        f'{_qb(quad)}'
        f'{"&nbsp;/" + _qb(monthly) if monthly != quad else ""}'
        f'<span style="color:#718096;">|</span>'
        f'<span>Conf: <b>{_pct(conf)}</b></span>'
        f'<span style="color:#718096;">|</span>'
        f'{_fw_badge(fw)}'
        f'<span style="color:#718096;">|</span>'
        f'{_news_badge(ns)}'
        f'<span style="color:#718096;">|</span>'
        f'<span style="color:{vix_color};">VIX: <b>{vix_v:.1f}</b> ({vix_b})</span>'
        f'<span style="color:#718096;">|</span>'
        f'<span>▲ <b>{best_us_long}</b> · 🇮🇩 <b>{best_ihsg}</b></span>'
        f'<span style="color:#718096;">|</span>'
        f'<span>▼ <b>{best_us_short}</b></span>'
        + (f'<span style="color:#718096;">|</span><span style="color:#e53e3e;font-weight:700;">⚡ {ta[:80]}</span>' if ta else '')
        + '</div>'
    )
    st.markdown(strip, unsafe_allow_html=True)


def _render_regime_card(core: dict) -> None:
    regime = core.get("regime", {})
    quad = regime.get("structural_quad", regime.get("current_quad", "Q?"))
    monthly = regime.get("monthly_quad", quad)
    next_q = regime.get("structural_next_quad", regime.get("next_quad", "?"))
    conf = float(regime.get("structural_confidence", regime.get("confidence", 0.5)))
    fh = float(regime.get("flip_hazard", 0.3))
    probs = regime.get("structural_probs", regime.get("probs", {}))
    g_core = float(regime.get("g_core", 0.0))
    i_core = float(regime.get("i_core", 0.0))
    divergence = regime.get("divergence_state", "aligned")

    quad_meta = {
        "Q1": ("Goldilocks", "Growth↑ Inflation↓", "#276749"),
        "Q2": ("Reflation", "Growth↑ Inflation↑", "#b7791f"),
        "Q3": ("Stagflation", "Growth↓ Inflation↑", "#c05621"),
        "Q4": ("Deflation Risk", "Growth↓ Inflation↓", "#c53030"),
    }
    label, description, color = quad_meta.get(quad, ("Unknown", "", "#718096"))

    st.markdown(
        f'<div style="background:{color}18;border-left:4px solid {color};border-radius:8px;padding:12px 14px;">'
        f'<div style="font-size:22px;font-weight:800;color:{color};">{quad} — {label}</div>'
        f'<div style="font-size:12px;color:#a0aec0;">{description}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**Confidence:** {_pct(conf)} &nbsp; **Flip hazard:** {_pct(fh)} &nbsp; **Next likely:** {next_q}", unsafe_allow_html=True)
    if divergence == "divergent":
        st.markdown(f"⚠️ Monthly divergence: **{monthly}** inside Structural **{quad}**")

    # Probability bars
    if probs:
        for q, p in sorted(probs.items(), key=lambda x: -x[1]):
            c = {"Q1":"#276749","Q2":"#b7791f","Q3":"#c05621","Q4":"#c53030"}.get(q,"#718096")
            pct_w = int(p * 100)
            st.markdown(
                f'<div style="margin:3px 0;display:flex;align-items:center;gap:8px;">'
                f'<span style="width:24px;font-size:11px;font-weight:700;color:{c};">{q}</span>'
                f'<div style="flex:1;background:#2d3748;height:8px;border-radius:4px;">'
                f'<div style="width:{pct_w}%;height:8px;background:{c};border-radius:4px;"></div></div>'
                f'<span style="font-size:11px;color:#a0aec0;width:32px;">{pct_w}%</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Growth / Inflation axes
    g_bar = "▲" if g_core > 0 else "▼"
    i_bar = "▲" if i_core > 0 else "▼"
    g_color = "#48bb78" if g_core > 0 else "#fc8181"
    i_color = "#fc8181" if i_core > 0 else "#48bb78"
    st.markdown(
        f'<span style="color:{g_color};">{g_bar} Growth: {g_core:+.3f}</span>'
        f'&nbsp;&nbsp;<span style="color:{i_color};">{i_bar} Inflation: {i_core:+.3f}</span>',
        unsafe_allow_html=True,
    )


def _render_transition_radar(core: dict) -> None:
    rt = core.get("regime_transition", {})
    fw = rt.get("front_run_window", "not yet")
    rationale = rt.get("front_run_rationale", "")
    paths = rt.get("transition_paths", [])
    ew_signals = rt.get("early_warning_signals", {})

    fw_color = {"now":"#e53e3e","1-2w":"#dd6b20","3-6w":"#d69e2e","not yet":"#4a5568"}.get(fw,"#4a5568")
    st.markdown(
        f'<div style="background:{fw_color}18;border:1px solid {fw_color};border-radius:8px;padding:8px 12px;margin-bottom:8px;">'
        f'<span style="color:{fw_color};font-weight:700;font-size:13px;">{_fw_badge(fw)}</span><br>'
        f'<span style="font-size:11px;color:#a0aec0;">{rationale[:120]}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Top transition path
    if paths:
        p = paths[0]
        ew_pct = int(p.get("early_warning_score", 0) * 100)
        prob_pct = int(p.get("probability", 0) * 100)
        tw = p.get("timeframe_weeks", 0)
        st.markdown(
            f'**{p.get("from_quad","?")} → {p.get("to_quad","?")}** &nbsp; '
            f'{prob_pct}% prob &nbsp; ~{tw}w &nbsp; {ew_pct}% EW',
        )
        # EW signal badges
        firing = [k.replace("_", " ").title() for k, v in ew_signals.items() if v >= 0.5]
        dormant_n = len([k for k, v in ew_signals.items() if v < 0.5])
        if firing:
            st.markdown(
                "🔴 **Firing:** " + " ".join(_pill(s, "#c53030") for s in firing[:4]),
                unsafe_allow_html=True,
            )
        if dormant_n:
            st.caption(f"⚪ {dormant_n} signals not yet active")

        if p.get("confirmation_needed"):
            st.markdown("**Confirm via:** " + " · ".join(p["confirmation_needed"][:2]))


def _render_narrative_block(core: dict) -> None:
    narr = core.get("narrative_discovery", {})
    actives = narr.get("active_narratives", [])
    early = narr.get("early_stage_alerts", [])

    if not actives:
        st.caption("No active narratives detected.")
        return

    # Show top 2 narratives compactly
    for n in actives[:2]:
        stage = n.get("stage", "")
        conv = float(n.get("regime_adjusted_conviction", 0))
        pump = float(n.get("pump_risk", 0.5))
        name = str(n.get("name", ""))
        action = str(n.get("action_summary", ""))
        primary = n.get("primary_beneficiaries", [])
        insight = str(n.get("claude_insight", ""))

        stage_color = {"early":"#e53e3e","building":"#dd6b20","mature":"#276749"}.get(stage,"#4a5568")
        pump_label = "🟢 Thesis" if pump <= 0.25 else ("🟡 Mixed" if pump <= 0.50 else "🔴 High pump risk")

        st.markdown(
            f'<div style="border-left:3px solid {stage_color};padding-left:8px;margin-bottom:8px;">'
            f'<span style="color:{stage_color};font-weight:700;font-size:11px;">{stage.upper()} · {int(conv*100)}% conv</span>'
            f'<span style="float:right;font-size:10px;">{pump_label}</span><br>'
            f'<b style="font-size:12px;">{name}</b><br>'
            f'<span style="font-size:11px;color:#a0aec0;">{action[:100]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if primary:
            st.markdown(_pills(primary[:4], "#276749"), unsafe_allow_html=True)
        if insight and "pending" not in insight:
            st.caption(f"🤖 {insight[:100]}")


def _render_master_ticker_board(core: dict) -> None:
    tickers = core.get("regime_tickers", {})
    regime = core.get("regime", {})
    quad = regime.get("structural_quad", regime.get("current_quad", "Q?"))
    fw = core.get("regime_transition", {}).get("front_run_window", "not yet")

    fr_picks = tickers.get("front_run_picks", [])
    fr_tickers = {p["ticker"] for p in fr_picks if isinstance(p, dict)} if fr_picks else set()

    rows = []
    markets = [
        ("🇺🇸 US", tickers.get("us_longs", []), tickers.get("us_shorts", []), "long/short"),
        ("🇮🇩 IHSG", tickers.get("ihsg_buys", []), [], "buy only"),
        ("💱 FX", tickers.get("fx_longs", []), tickers.get("fx_shorts", []), "long/short"),
        ("🛢 Commodities", tickers.get("commodity_longs", []), tickers.get("commodity_shorts", []), "long/short"),
        ("🔐 Crypto", tickers.get("crypto_longs", []), tickers.get("crypto_shorts", []), "long/short"),
    ]
    for market, longs, shorts, mtype in markets:
        rows.append({
            "Market": market,
            "▲ LONG / BUY": " · ".join(longs[:5]),
            "▼ SHORT / REDUCE": " · ".join(shorts[:4]) if shorts else "—",
            "Mode": mtype,
        })
    df = pd.DataFrame(rows)

    # Front-run alert bar
    if fw == "now" and fr_picks:
        fr_tickers_str = " · ".join([p.get("ticker","") for p in fr_picks[:5] if isinstance(p, dict)])
        st.markdown(
            f'<div style="background:#c5303022;border:1px solid #e53e3e;border-radius:6px;'
            f'padding:6px 12px;margin-bottom:6px;font-size:12px;">'
            f'<span style="color:#e53e3e;font-weight:700;">⚡ FRONT-RUN PICKS ({quad} → transition): </span>'
            f'<span style="color:#feb2b2;">{fr_tickers_str}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_scenarios_compact(core: dict) -> None:
    wim = core.get("what_if_matrix", {}) or {}
    if not wim:
        st.caption("No scenarios loaded.")
        return
    rows = []
    for name, data in list(wim.items())[:6]:
        if isinstance(data, dict):
            rows.append({
                "Scenario": name[:55],
                "Prob": f"{float(data.get('p', 0)):.0%}",
                "Winners": ", ".join((data.get("winners") or [])[:2]),
                "Invalidator": (data.get("invalidators") or ["—"])[0][:45],
            })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=220)


def _render_news_intel(core: dict) -> None:
    news = core.get("news_state", {})
    display = str(news.get("display_state", "Quiet"))
    summary = str(news.get("summary", ""))
    war_h = float(news.get("war_oil_hazard", 0.0))
    pol_h = float(news.get("policy_pressure_hazard", 0.0))
    relief_h = float(news.get("relief_hazard", 0.0))
    credit_h = float(news.get("credit_stress_hazard", 0.0))
    front_run = news.get("front_run") or {}
    what_watch = str(front_run.get("what_to_watch", "")) if isinstance(front_run, dict) else ""
    headlines = news.get("headlines", [])

    st.markdown(f"**State:** {display}")
    if summary:
        st.info(summary)

    for label, val, color in [
        ("War/Oil", war_h, "#e53e3e"),
        ("Policy", pol_h, "#dd6b20"),
        ("Credit", credit_h, "#c53030"),
        ("Relief", relief_h, "#276749"),
    ]:
        pct = int(val * 100)
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:6px;margin:2px 0;">'
            f'<span style="font-size:10px;width:48px;color:#a0aec0;">{label}</span>'
            f'<div style="flex:1;background:#2d3748;height:6px;border-radius:3px;">'
            f'<div style="width:{pct}%;height:6px;background:{color};border-radius:3px;"></div></div>'
            f'<span style="font-size:10px;width:28px;color:{color};">{pct}%</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if what_watch:
        st.warning(f"**👁 Watch:** {what_watch}")

    if headlines:
        with st.expander("Headlines", expanded=False):
            for h in headlines[:5]:
                title = str(h.get("title",""))[:80]
                link = h.get("link","")
                if link:
                    st.markdown(f"• [{title}]({link})")
                else:
                    st.markdown(f"• {title}")


def _render_sizing_guide(core: dict) -> None:
    rt = core.get("regime_transition", {})
    regime = core.get("regime", {})
    opt = core.get("options_regime", {}) or {}
    sizing = core.get("position_sizing", {}) or {}

    quad = regime.get("structural_quad", regime.get("current_quad", "Q?"))
    fw = rt.get("front_run_window", "not yet")
    vix_bucket = opt.get("vix_bucket", "normal")
    vix_cap = float(opt.get("vix_sizing_cap", 0.85))

    # Regime base size
    regime_sizes = {"Q1": ("8%", "15%"), "Q2": ("7%", "12%"), "Q3": ("4%", "8%"), "Q4": ("5%", "10%")}
    base, max_sz = regime_sizes.get(quad, ("5%", "10%"))

    fw_adj = "60% of base" if fw in ("now",) else "100% of base"
    vix_adj = f"{int(vix_cap*100)}% cap (VIX {vix_bucket})"

    stop_map = {"Q1": "7%", "Q2": "8%", "Q3": "6%", "Q4": "9%"}
    stop = stop_map.get(quad, "7%")

    rr_map = {"Q1": "2.5:1", "Q2": "2.2:1", "Q3": "1.8:1", "Q4": "2.0:1"}
    rr = rr_map.get(quad, "2:1")

    st.markdown(f"**Regime:** `{quad}` sizing rules")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Base size", base)
        st.metric("Max size", max_sz)
        st.metric("Stop loss", stop)
    with col2:
        st.metric("R:R target", rr)
        st.metric("VIX adj", vix_adj)
        st.metric("Front-run adj", fw_adj)

    if vix_bucket in ("stress", "crisis"):
        st.error("🚨 High VIX — defensive sizing only")
    elif vix_bucket == "elevated":
        st.warning("⚠️ Elevated VIX — reduce size")
    elif vix_bucket == "goldilocks":
        st.success("✅ VIX Goldilocks — full sizing permitted")


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_command_center(snapshot: dict) -> None:
    """
    Main entry. snapshot = the full app snapshot dict.
    Works with both monolith snap dict and modular shared_core dict.
    """
    # Handle both monolith (snap has 'q', 'f' etc) and modular (snap has 'shared_core')
    if "shared_core" in snapshot:
        core = snapshot["shared_core"]
    else:
        # Monolith compatibility shim
        core = {
            "regime": snapshot.get("q", {}),
            "regime_transition": snapshot.get("regime_transition", {}),
            "news_state": snapshot.get("news_overlay", snapshot.get("news_state", {})),
            "regime_tickers": snapshot.get("regime_tickers", {}),
            "narrative_discovery": snapshot.get("narrative_discovery", {}),
            "options_regime": snapshot.get("options_regime", {}),
            "what_if_matrix": snapshot.get("what_if_matrix", {}),
            "position_sizing": snapshot.get("position_sizing", {}),
        }

    st.title("🧭 Command Center")
    st.caption("Everything you need to make a decision — in one view.")

    # --- STATUS STRIP ---
    _render_status_strip(core)

    # --- ROW 1: Regime | Transition | Narrative ---
    col1, col2, col3 = st.columns([1.1, 1.2, 1.2], gap="medium")
    with col1:
        st.markdown("#### Regime")
        _render_regime_card(core)
    with col2:
        st.markdown("#### Transition Radar")
        _render_transition_radar(core)
    with col3:
        st.markdown("#### Narrative Intelligence")
        _render_narrative_block(core)

    st.markdown("---")

    # --- ROW 2: Master Ticker Board ---
    st.markdown("#### Master Ticker Board — All Markets")
    _render_master_ticker_board(core)

    st.markdown("---")

    # --- ROW 3: Scenarios | News | Sizing ---
    c1, c2, c3 = st.columns([1.3, 1.3, 1.0], gap="medium")
    with c1:
        st.markdown("#### Scenario Tree")
        _render_scenarios_compact(core)
    with c2:
        st.markdown("#### News Intelligence")
        _render_news_intel(core)
    with c3:
        st.markdown("#### Position Sizing Guide")
        _render_sizing_guide(core)
