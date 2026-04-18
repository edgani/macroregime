"""narrative_discovery_panel.py

Displays live narrative intelligence — the "more dewa than Hedgeye" layer.

Shows:
- Top active narratives with regime-adjusted conviction
- Early stage alerts (front-run opportunities)
- Specific tickers per narrative with action summary
- Claude insight per narrative
- Pump risk classification
"""
from __future__ import annotations
import streamlit as st


def _stage_badge(stage: str) -> str:
    cfg = {
        "early":     ("#c53030", "⚡ EARLY"),
        "building":  ("#dd6b20", "📈 BUILDING"),
        "mature":    ("#276749", "✅ MATURE"),
        "exhausted": ("#718096", "💀 EXHAUSTED"),
        "watching":  ("#4a5568", "👁 WATCHING"),
        "invalid":   ("#742a2a", "❌ INVALID"),
    }
    bg, label = cfg.get(stage, ("#4a5568", stage.upper()))
    return f'<span style="background:{bg};color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:700;">{label}</span>'


def _pump_badge(pump_risk: float) -> str:
    if pump_risk <= 0.20:
        return '<span style="background:#276749;color:#fff;padding:2px 7px;border-radius:4px;font-size:10px;">🟢 THESIS-DRIVEN</span>'
    elif pump_risk <= 0.45:
        return '<span style="background:#b7791f;color:#fff;padding:2px 7px;border-radius:4px;font-size:10px;">🟡 MIXED</span>'
    else:
        return '<span style="background:#c53030;color:#fff;padding:2px 7px;border-radius:4px;font-size:10px;">🔴 HIGH PUMP RISK</span>'


def _conviction_bar(conviction: float, width: int = 100) -> str:
    pct = int(min(1.0, max(0.0, conviction)) * width)
    color = "#276749" if conviction >= 0.60 else ("#dd6b20" if conviction >= 0.35 else "#4a5568")
    return (
        f'<div style="display:inline-block;width:{width}px;height:7px;background:#2d3748;border-radius:3px;vertical-align:middle;">'
        f'<div style="width:{pct}px;height:7px;background:{color};border-radius:3px;"></div>'
        f'</div>&nbsp;<span style="font-size:12px;color:#cbd5e0;">{int(conviction*100)}%</span>'
    )


def _regime_mult_label(mult: float) -> str:
    if mult >= 0.80:
        return f'<span style="color:#48bb78;font-size:11px;">✅ {mult:.2f}x regime boost</span>'
    elif mult >= 0.60:
        return f'<span style="color:#fbd38d;font-size:11px;">⚠️ {mult:.2f}x regime neutral</span>'
    else:
        return f'<span style="color:#fc8181;font-size:11px;">❌ {mult:.2f}x regime suppressed</span>'


def _ticker_pills(tickers: list, color: str = "#2b6cb0") -> str:
    pills = "".join(
        f'<span style="background:{color};color:#fff;padding:2px 6px;border-radius:3px;font-size:11px;margin:1px;display:inline-block;">{t}</span>'
        for t in tickers
    )
    return pills


def render_narrative_discovery_panel(core: dict) -> None:
    """Main render function. core = shared_core dict."""
    narrative_output = core.get("narrative_discovery") or {}

    if not narrative_output:
        st.info("Narrative discovery not active — ensure load_narrative_signals() is wired into build_snapshot.")
        return

    active = narrative_output.get("active_narratives") or []
    top = narrative_output.get("top_conviction")
    early_alerts = narrative_output.get("early_stage_alerts") or []
    summary = str(narrative_output.get("summary", ""))

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------
    if summary:
        st.info(f"**🎯 {summary}**")

    # ------------------------------------------------------------------
    # Early stage alerts — the front-run section
    # ------------------------------------------------------------------
    if early_alerts:
        st.markdown(
            '<div style="background:#742a2a22;border:1.5px solid #e53e3e;border-radius:8px;padding:10px 14px;margin-bottom:10px;">'
            f'<span style="color:#e53e3e;font-weight:700;">⚡ EARLY STAGE ALERTS ({len(early_alerts)}) — Front-Run Opportunities</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        for alert in early_alerts[:3]:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(
                    f'**{alert.name}** &nbsp; {_stage_badge(alert.stage)} &nbsp; {_pump_badge(alert.pump_risk)}',
                    unsafe_allow_html=True,
                )
                st.markdown(f'_{alert.action_summary}_')
                if alert.claude_insight and "Analysis pending" not in alert.claude_insight:
                    st.caption(f"🤖 {alert.claude_insight}")
            with c2:
                st.markdown("**Buy:**")
                st.markdown(_ticker_pills(alert.primary_beneficiaries[:4], "#276749"), unsafe_allow_html=True)
                if alert.what_fades:
                    st.markdown("**Fade:**")
                    st.markdown(_ticker_pills(alert.what_fades[:3], "#742a2a"), unsafe_allow_html=True)
        st.markdown("---")

    # ------------------------------------------------------------------
    # All active narratives
    # ------------------------------------------------------------------
    if not active:
        st.caption("No active narratives detected at the moment.")
        return

    st.markdown(f"#### Active Narratives ({len(active)} detected)")

    for case in active[:8]:
        with st.expander(
            f"{case.name}  |  {int(case.regime_adjusted_conviction*100)}% conviction  |  {case.stage.upper()}",
            expanded=(case.stage == "early" and case.regime_adjusted_conviction >= 0.40),
        ):
            col1, col2, col3 = st.columns([2, 1.5, 1.5])

            with col1:
                st.markdown(
                    f'{_stage_badge(case.stage)} &nbsp; {_pump_badge(case.pump_risk)} &nbsp; {_regime_mult_label(case.regime_multiplier)}',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'**Regime-adjusted conviction:** {_conviction_bar(case.regime_adjusted_conviction)}',
                    unsafe_allow_html=True,
                )
                st.markdown(f'**Catalyst type:** `{case.catalyst_type}`')
                st.markdown(f'**Action:** {case.action_summary}')
                if case.claude_insight and "pending" not in case.claude_insight:
                    st.markdown(f'🤖 **Claude:** _{case.claude_insight}_')

                if case.headlines:
                    st.markdown("**Supporting headlines:**")
                    for h in case.headlines[:2]:
                        title = h.get("title", "")[:90]
                        link = h.get("link", "")
                        if link:
                            st.markdown(f"  • [{title}]({link})")
                        else:
                            st.markdown(f"  • {title}")

            with col2:
                if case.primary_beneficiaries:
                    st.markdown("**Primary buys:**")
                    st.markdown(_ticker_pills(case.primary_beneficiaries[:5], "#276749"), unsafe_allow_html=True)
                if case.secondary_beneficiaries:
                    st.markdown("**Secondary:**")
                    st.markdown(_ticker_pills(case.secondary_beneficiaries[:4], "#2b6cb0"), unsafe_allow_html=True)
                if case.what_fades:
                    st.markdown("**Fade / reduce:**")
                    st.markdown(_ticker_pills(case.what_fades[:4], "#742a2a"), unsafe_allow_html=True)

            with col3:
                if case.confirmation_signals:
                    st.markdown("**Confirm via:**")
                    for sig in case.confirmation_signals[:3]:
                        st.markdown(f"  ✅ {sig}")
                if case.invalidators:
                    st.markdown("**Invalidators:**")
                    for inv in [i for i in case.invalidators if i][:3]:
                        st.markdown(f"  ❌ {inv[:60]}")
