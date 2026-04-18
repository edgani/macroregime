"""regime_transition_panel.py

Forward-looking regime transition display.
Shows:
- Front-run window (NOW / 1-2w / 3-6w / not yet)
- Top transition paths with probability, timeframe, early warning score
- Named early warning signals currently firing
- Asset implications per path
- What to watch (from Claude news analysis)
"""
from __future__ import annotations
import streamlit as st


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def _window_color(window: str) -> str:
    return {
        "now":    "#e53e3e",   # red  — act now
        "1-2w":   "#dd6b20",   # orange
        "3-6w":   "#d69e2e",   # yellow
        "not yet":"#718096",   # gray
    }.get(window, "#718096")


def _prob_bar(prob: float, width: int = 120) -> str:
    pct = int(min(1.0, max(0.0, prob)) * width)
    color = "#e53e3e" if prob >= 0.35 else ("#dd6b20" if prob >= 0.22 else "#4a5568")
    return (
        f'<div style="display:inline-block;width:{width}px;height:8px;'
        f'background:#2d3748;border-radius:4px;vertical-align:middle;">'
        f'<div style="width:{pct}px;height:8px;background:{color};border-radius:4px;"></div>'
        f'</div>'
    )


def _ew_badge(score: float) -> str:
    pct = int(score * 100)
    if score >= 0.70:
        bg, label = "#c53030", f"🔴 {pct}% EW"
    elif score >= 0.50:
        bg, label = "#c05621", f"🟠 {pct}% EW"
    elif score >= 0.30:
        bg, label = "#b7791f", f"🟡 {pct}% EW"
    else:
        bg, label = "#2d3748", f"⚪ {pct}% EW"
    return (
        f'<span style="background:{bg};color:#fff;padding:2px 7px;'
        f'border-radius:4px;font-size:11px;font-weight:600;">{label}</span>'
    )


def _implication_color(val: str) -> str:
    v = val.lower()
    if any(x in v for x in ["bullish", "up", "bid"]):
        return "#48bb78"
    if any(x in v for x in ["bearish", "down", "fragile", "bearish"]):
        return "#fc8181"
    if any(x in v for x in ["neutral", "mixed", "selective"]):
        return "#fbd38d"
    return "#a0aec0"


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_regime_transition_panel(core: dict) -> None:
    """Render the regime transition / forward radar panel.

    Args:
        core: the full shared_core dict returned by build_shared_core.
    """
    transition = core.get("regime_transition") or {}
    news_state = core.get("news_state") or {}

    if not transition:
        st.info("Regime transition engine not available — check engine wiring.")
        return

    current_quad = transition.get("current_quad", "Q?")
    monthly_quad = transition.get("current_monthly_quad", current_quad)
    most_likely_next = transition.get("most_likely_next", "Q?")
    front_run_window = transition.get("front_run_window", "not yet")
    front_run_rationale = transition.get("front_run_rationale", "")
    leading_composite = float(transition.get("leading_composite", 0.0))
    ew_signals = transition.get("early_warning_signals") or {}
    paths = transition.get("transition_paths") or []

    # News front-run details (from Claude analysis)
    front_run_news = news_state.get("front_run") or {}
    what_to_watch = str(front_run_news.get("what_to_watch", "")) if isinstance(front_run_news, dict) else ""
    news_confidence = float(front_run_news.get("confidence", 0.0)) if isinstance(front_run_news, dict) else 0.0
    claude_analysis = news_state.get("claude_analysis") or {}
    claude_summary = str(claude_analysis.get("summary", "")) if isinstance(claude_analysis, dict) else ""

    # ------------------------------------------------------------------
    # Header: front-run window badge
    # ------------------------------------------------------------------
    win_color = _window_color(front_run_window)
    win_label = {
        "now":    "⚡ FRONT-RUN WINDOW: NOW",
        "1-2w":   "🕐 FRONT-RUN WINDOW: 1–2 WEEKS",
        "3-6w":   "🕒 FRONT-RUN WINDOW: 3–6 WEEKS",
        "not yet":"⏸ NO ACTIVE FRONT-RUN WINDOW",
    }.get(front_run_window, "⏸ NO ACTIVE FRONT-RUN WINDOW")

    st.markdown(
        f'<div style="background:{win_color}22;border:1.5px solid {win_color};'
        f'border-radius:8px;padding:10px 16px;margin-bottom:10px;">'
        f'<span style="color:{win_color};font-weight:700;font-size:15px;">{win_label}</span>'
        f'<br><span style="color:#cbd5e0;font-size:12px;">{front_run_rationale}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # Regime state + leading composite
    # ------------------------------------------------------------------
    col1, col2, col3, col4 = st.columns([1.2, 1.2, 1.2, 2.4])
    with col1:
        st.metric("Structural", current_quad)
    with col2:
        st.metric("Monthly", monthly_quad)
    with col3:
        st.metric("Most Likely Next", most_likely_next)
    with col4:
        leading_pct = int((leading_composite + 1.0) / 2.0 * 100)  # -1..1 → 0..100
        leading_label = (
            "🟢 Leading indicators improving" if leading_composite > 0.10
            else "🔴 Leading indicators deteriorating" if leading_composite < -0.10
            else "⚪ Leading indicators neutral"
        )
        st.metric("Leading Composite", f"{leading_pct}%", help=leading_label)
        st.caption(leading_label)

    # ------------------------------------------------------------------
    # Transition paths table
    # ------------------------------------------------------------------
    if paths:
        st.markdown("#### Transition Paths")
        for path in paths[:4]:
            from_q   = path.get("from_quad", "?")
            to_q     = path.get("to_quad", "?")
            prob     = float(path.get("probability", 0.0))
            ew_score = float(path.get("early_warning_score", 0.0))
            tw       = int(path.get("timeframe_weeks", 0))
            conf     = float(path.get("confidence", 0.0))
            confirm  = path.get("confirmation_needed") or []
            inv      = path.get("invalidators") or []
            impl     = path.get("asset_implications") or {}

            with st.expander(
                f"{from_q} → {to_q}   {int(prob*100)}% probability   "
                f"~{tw}w timeframe   {int(ew_score*100)}% early warnings firing",
                expanded=(ew_score >= 0.50),
            ):
                r1, r2 = st.columns([3, 2])
                with r1:
                    st.markdown(
                        _prob_bar(prob) + f'  <span style="font-size:13px;font-weight:600;">{int(prob*100)}% transition probability</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        _ew_badge(ew_score) + f'  <span style="font-size:12px;color:#a0aec0;">{int(ew_score*100)}% of early warning signals firing</span>',
                        unsafe_allow_html=True,
                    )
                    st.caption(f"Confidence: {int(conf*100)}%   |   Est. timeframe: {tw} weeks")

                    if confirm:
                        st.markdown("**Confirmation needed:**")
                        for c in confirm[:3]:
                            st.markdown(f"  ✅ {c}")

                    if inv:
                        st.markdown("**Invalidators:**")
                        for iv in inv[:3]:
                            st.markdown(f"  ❌ {iv}")

                with r2:
                    if impl:
                        st.markdown("**Asset implications:**")
                        for asset_class, view in list(impl.items())[:6]:
                            color = _implication_color(view)
                            label = view[:60] if len(view) > 60 else view
                            st.markdown(
                                f'<div style="margin-bottom:3px;">'
                                f'<span style="color:#a0aec0;font-size:11px;">{asset_class.upper()}: </span>'
                                f'<span style="color:{color};font-size:11px;">{label}</span>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

    # ------------------------------------------------------------------
    # Early warning signals currently firing
    # ------------------------------------------------------------------
    if ew_signals:
        st.markdown("#### Early Warning Signal Dashboard")
        firing = {k: v for k, v in ew_signals.items() if v >= 0.5}
        dormant = {k: v for k, v in ew_signals.items() if v < 0.5}

        col_fire, col_dorm = st.columns(2)
        with col_fire:
            st.markdown(f"**🔴 Firing ({len(firing)})**")
            for sig, val in sorted(firing.items(), key=lambda x: -x[1]):
                label = sig.replace("_", " ").title()
                st.markdown(
                    f'<div style="background:#c53030;border-radius:4px;padding:3px 8px;'
                    f'margin-bottom:3px;font-size:12px;color:#fff;">✓ {label}</div>',
                    unsafe_allow_html=True,
                )
        with col_dorm:
            st.markdown(f"**⚪ Not Yet ({len(dormant)})**")
            for sig, val in sorted(dormant.items(), key=lambda x: -x[1]):
                label = sig.replace("_", " ").title()
                st.markdown(
                    f'<div style="background:#2d3748;border-radius:4px;padding:3px 8px;'
                    f'margin-bottom:3px;font-size:12px;color:#718096;">○ {label}</div>',
                    unsafe_allow_html=True,
                )

    # ------------------------------------------------------------------
    # Claude news intelligence
    # ------------------------------------------------------------------
    if claude_summary or what_to_watch:
        st.markdown("#### 🤖 News Intelligence (Claude)")
        if claude_summary:
            st.info(f"**Regime implication:** {claude_summary}")
        if what_to_watch and news_confidence >= 0.35:
            conf_pct = int(news_confidence * 100)
            st.warning(
                f"**Watch next:** {what_to_watch}  \n"
                f"_Claude confidence: {conf_pct}%_"
            )
        elif not claude_summary:
            st.caption("Set `ANTHROPIC_API_KEY` to enable Claude semantic news analysis.")
