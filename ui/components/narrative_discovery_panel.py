"""narrative_discovery_panel.py — Narrative Intelligence Panel

Displays live narrative-driven opportunities — the XNDU-style intelligence layer.
Data arrives as serialized dicts (not NarrativeCase objects).
All access uses .get() for safety.
"""
from __future__ import annotations
import streamlit as st


# ── Style helpers ─────────────────────────────────────────────────────────────

def _stage_badge(stage: str) -> str:
    cfg = {
        "early":     ("#c53030", "⚡ EARLY"),
        "building":  ("#dd6b20", "📈 BUILDING"),
        "mature":    ("#276749", "✅ MATURE"),
        "exhausted": ("#718096", "💀 EXHAUSTED"),
        "watching":  ("#4a5568", "👁 WATCHING"),
    }
    bg, lbl = cfg.get(stage, ("#4a5568", stage.upper() if stage else "UNKNOWN"))
    return f'<span style="background:{bg};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;">{lbl}</span>'


def _pump_badge(pump_risk: float) -> str:
    if pump_risk <= 0.20:
        return '<span style="background:#276749;color:#fff;padding:2px 7px;border-radius:4px;font-size:10px;">🟢 THESIS</span>'
    elif pump_risk <= 0.45:
        return '<span style="background:#b7791f;color:#fff;padding:2px 7px;border-radius:4px;font-size:10px;">🟡 MIXED</span>'
    else:
        return '<span style="background:#c53030;color:#fff;padding:2px 7px;border-radius:4px;font-size:10px;">🔴 HIGH PUMP RISK</span>'


def _conv_bar(conviction: float, width: int = 100) -> str:
    pct = int(min(1.0, max(0.0, conviction)) * width)
    color = "#276749" if conviction >= 0.60 else ("#dd6b20" if conviction >= 0.35 else "#4a5568")
    return (
        f'<div style="display:inline-block;width:{width}px;height:7px;background:#1a202c;border-radius:3px;vertical-align:middle;">'
        f'<div style="width:{pct}px;height:7px;background:{color};border-radius:3px;"></div>'
        f'</div>&nbsp;<span style="font-size:12px;color:#a0aec0;">{pct}%</span>'
    )


def _regime_mult_label(mult: float) -> str:
    if mult >= 0.80:
        return f'<span style="color:#48bb78;font-size:11px;">✅ {mult:.2f}x boost</span>'
    elif mult >= 0.60:
        return f'<span style="color:#fbd38d;font-size:11px;">⚠️ {mult:.2f}x neutral</span>'
    else:
        return f'<span style="color:#fc8181;font-size:11px;">❌ {mult:.2f}x suppressed</span>'


def _pills(tickers: list, color: str = "#2b6cb0") -> str:
    return "".join(
        f'<span style="background:{color};color:#fff;padding:2px 6px;border-radius:3px;font-size:11px;margin:1px;display:inline-block;">{t}</span>'
        for t in (tickers or []) if t
    )


# ── G accessor — safely get field from either dict or object ──────────────────

def _g(item, field: str, default=None):
    """Safe get from dict or object."""
    if isinstance(item, dict):
        return item.get(field, default)
    return getattr(item, field, default)


# ── Main render ───────────────────────────────────────────────────────────────

def render_narrative_discovery_panel(core: dict) -> None:
    """
    Main render function.
    core = snap dict (monolith) or shared_core dict (modular).
    Handles both dict-serialized and raw NarrativeCase objects safely.
    """
    narrative_output = core.get("narrative_discovery") or {}

    if not narrative_output:
        st.markdown(
            '<div style="background:#1a1a2a;border:1px dashed #4a5568;border-radius:8px;padding:20px;text-align:center;">'
            '<div style="font-size:14px;font-weight:700;color:#4a5568;margin-bottom:6px;">📖 Narrative Intelligence Not Active</div>'
            '<div style="font-size:12px;color:#4a5568;">Set <code>ANTHROPIC_API_KEY</code> in secrets.toml to activate Claude narrative analysis.<br>'
            'Without it, keyword fallback still runs but Claude depth analysis is unavailable.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    actives = narrative_output.get("active_narratives") or []
    early_alerts = narrative_output.get("early_stage_alerts") or []
    summary = str(narrative_output.get("summary", ""))

    # ── Header ────────────────────────────────────────────────────────────────
    if summary and "No dominant" not in summary:
        st.info(f"**🎯 {summary}**")

    # ── Early stage alerts ────────────────────────────────────────────────────
    if early_alerts:
        n = len(early_alerts)
        st.markdown(
            f'<div style="background:#c5303022;border:1.5px solid #e53e3e;border-radius:8px;'
            f'padding:10px 14px;margin-bottom:12px;">'
            f'<span style="color:#e53e3e;font-weight:700;font-size:13px;">⚡ EARLY STAGE ALERTS ({n}) — Front-Run Opportunities</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        for alert in early_alerts[:3]:
            # alert is a dict (safely accessed with _g)
            name         = str(_g(alert, "name", "Unknown"))
            stage        = str(_g(alert, "stage", "early"))
            pump_risk    = float(_g(alert, "pump_risk", 0.5))
            action       = str(_g(alert, "action_summary", ""))
            insight      = str(_g(alert, "claude_insight", ""))
            primary      = _g(alert, "primary_beneficiaries", []) or []
            fades        = _g(alert, "what_fades", []) or []
            confirms     = _g(alert, "confirmation_signals", []) or []
            invalidators = _g(alert, "invalidators", []) or []
            conv         = float(_g(alert, "regime_adjusted_conviction", _g(alert, "conviction", 0)))

            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(
                    f'<div style="margin-bottom:4px;">'
                    f'<b style="font-size:13px;">{name}</b>&nbsp;'
                    f'{_stage_badge(stage)}&nbsp;{_pump_badge(pump_risk)}'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'**Conviction:** {_conv_bar(conv)}',
                    unsafe_allow_html=True,
                )
                if action:
                    st.markdown(f"_{action[:120]}_")
                if insight and "pending" not in insight.lower():
                    st.caption(f"🤖 {insight[:100]}")
                if confirms:
                    for c in confirms[:2]:
                        st.markdown(f"✅ {c}")
            with c2:
                if primary:
                    st.markdown("**Buy:**")
                    st.markdown(_pills(primary[:5], "#276749"), unsafe_allow_html=True)
                if fades:
                    st.markdown("**Fade:**")
                    st.markdown(_pills(fades[:3], "#742a2a"), unsafe_allow_html=True)
                if invalidators:
                    st.markdown("**Kill switch:**")
                    for inv in [i for i in invalidators if i][:2]:
                        st.markdown(f'<span style="font-size:10px;color:#718096;">❌ {str(inv)[:45]}</span>', unsafe_allow_html=True)
            st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)

        st.markdown("---")

    # ── All active narratives ─────────────────────────────────────────────────
    if not actives:
        st.caption("No active narratives detected. All keyword scores are neutral or negative.")
        return

    st.markdown(f"#### Active Narratives ({len(actives)} detected)")

    for case in actives[:8]:
        name      = str(_g(case, "name", "Unknown"))
        stage     = str(_g(case, "stage", "watching"))
        conv      = float(_g(case, "regime_adjusted_conviction", 0))
        pump      = float(_g(case, "pump_risk", 0.5))
        mult      = float(_g(case, "regime_multiplier", 1.0))
        cat_type  = str(_g(case, "catalyst_type", "unknown"))
        action    = str(_g(case, "action_summary", ""))
        insight   = str(_g(case, "claude_insight", ""))
        headlines = _g(case, "headlines", []) or []
        primary   = _g(case, "primary_beneficiaries", []) or []
        secondary = _g(case, "secondary_beneficiaries", []) or []
        fades     = _g(case, "what_fades", []) or []
        confirms  = _g(case, "confirmation_signals", []) or []
        invs      = _g(case, "invalidators", []) or []

        expanded = stage == "early" and conv >= 0.40

        with st.expander(
            f"{name}  ·  {int(conv*100)}% conviction  ·  {stage.upper()}",
            expanded=expanded,
        ):
            col1, col2, col3 = st.columns([2, 1.5, 1.5])

            with col1:
                st.markdown(
                    f'{_stage_badge(stage)}&nbsp;{_pump_badge(pump)}&nbsp;{_regime_mult_label(mult)}',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'**Regime-adj conviction:** {_conv_bar(conv)}',
                    unsafe_allow_html=True,
                )
                st.markdown(f'**Catalyst:** `{cat_type}`')
                if action:
                    st.markdown(f"**Action:** {action[:120]}")
                if insight and "pending" not in insight.lower():
                    st.markdown(f'🤖 **Claude:** _{insight[:120]}_')
                if headlines:
                    st.markdown("**Headlines:**")
                    for h in headlines[:2]:
                        title = str(h.get("title", "") if isinstance(h, dict) else h)[:85]
                        link  = h.get("link", "") if isinstance(h, dict) else ""
                        if link:
                            st.markdown(f"  • [{title}]({link})")
                        else:
                            st.markdown(f"  • {title}")

            with col2:
                if primary:
                    st.markdown("**Primary buys:**")
                    st.markdown(_pills(primary[:5], "#276749"), unsafe_allow_html=True)
                if secondary:
                    st.markdown("**Secondary:**")
                    st.markdown(_pills(secondary[:4], "#2b6cb0"), unsafe_allow_html=True)
                if fades:
                    st.markdown("**Fade / reduce:**")
                    st.markdown(_pills(fades[:4], "#742a2a"), unsafe_allow_html=True)

            with col3:
                if confirms:
                    st.markdown("**Confirm via:**")
                    for sig in confirms[:3]:
                        st.markdown(f"  ✅ {sig}")
                if invs:
                    st.markdown("**Invalidators:**")
                    for inv in [i for i in invs if i][:3]:
                        st.markdown(f'  ❌ {str(inv)[:55]}')
