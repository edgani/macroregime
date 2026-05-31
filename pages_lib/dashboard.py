"""dashboard.py — Restored from tes.zip original + Tier1Alpha panel moved to TOP."""
import streamlit as st


def render(snap: dict):
    """Entry point — Tier1Alpha is now MERGED into the regime card (no separate panel)."""
    try:
        from pages_lib._dashboard_legacy import render as _legacy_render
    except Exception as e:
        st.error(f"Dashboard legacy module failed to load: {e}")
        _fallback_dashboard(snap)
        return

    prices = snap.get("prices", {}) or {}
    vix_now = snap.get("vix", 20.0)
    if vix_now is None or vix_now == 0:
        try:
            vix_series = prices.get("^VIX")
            if vix_series is not None and len(vix_series) > 0:
                vix_now = float(vix_series.iloc[-1])
        except Exception:
            vix_now = 20.0

    try:
        _legacy_render(snap, prices, vix_now)
    except Exception as e:
        import traceback
        st.error(f"Legacy dashboard error: {e}")
        with st.expander("Traceback"):
            st.code(traceback.format_exc())
        _fallback_dashboard(snap)


def _render_tier1alpha_panel(snap: dict):
    """Tier1Alpha-style 4-signal market structure — COMPACT horizontal strip at top.
    Consolidates the market-structure signals + SPX levels + global quad into one tight block."""
    import streamlit as st

    t1a = snap.get("tier1alpha", {})
    if not t1a:
        try:
            from engines.tier1alpha_model import compute_tier1alpha
            t1a = compute_tier1alpha(snap)
        except Exception:
            t1a = {}

    st.markdown("##### 📐 Market Structure Report (Tier1Alpha-style)")

    if t1a and t1a.get("signals"):
        sigs = t1a["signals"]

        def _sig_color(name, val):
            green = {"gamma_exposure": "Positive", "systematic_flow": "Bullish",
                     "pv_band_rr": "Long", "strategic_allocation": "Risk On"}
            red = {"gamma_exposure": "Negative", "systematic_flow": "Bearish",
                   "pv_band_rr": "Short", "strategic_allocation": "Risk Off"}
            if val == green.get(name): return "#1a7f37"
            if val == red.get(name): return "#cf222e"
            return "#bf8700"

        labels = {
            "gamma_exposure": "SPX Gamma",
            "systematic_flow": "Systematic Flow",
            "pv_band_rr": "PV Band R/R",
            "strategic_allocation": "Strategic Alloc",
        }
        # 4 colored boxes in ONE horizontal row (compact)
        cols = st.columns(4)
        for col, (key, label) in zip(cols, labels.items()):
            sig = sigs.get(key, {})
            val = sig.get("value", "Neutral")
            color = _sig_color(key, val)
            col.markdown(
                f"<div style='background:{color};color:white;padding:8px 6px;"
                f"border-radius:6px;text-align:center;font-weight:700;font-size:0.78rem;'>"
                f"{label}<br><span style='font-size:0.9rem;'>{val}</span></div>",
                unsafe_allow_html=True)

        # SPX levels + Global Quad (Structural/Monthly intentionally omitted —
        # they live in the regime box below; no duplication)
        lv = t1a.get("spx_levels", {})
        gip = snap.get("gip", {})
        if isinstance(gip, dict):
            global_q = gip.get("global_quad") or gip.get("structural_quad") or snap.get("current_quad", "Q3")
        else:
            global_q = getattr(gip, "global_quad", None) or getattr(gip, "structural_quad", None) or "Q3"
        quad_names = {"Q1": "Goldilocks", "Q2": "Reflation", "Q3": "Stagflation", "Q4": "Deflation"}

        m = st.columns(4)
        m[0].metric("SPX Last", f"{lv.get('last_price', 0):,.0f}" if lv.get('last_price') else "—")
        m[1].metric("Upper PV (TRR)", f"{lv.get('upper_pv_band', 0):,.0f}" if lv.get('upper_pv_band') else "—")
        m[2].metric("Lower PV (LRR)", f"{lv.get('lower_pv_band', 0):,.0f}" if lv.get('lower_pv_band') else "—")
        m[3].metric("🌍 Global Quad (Hedgeye)", global_q, quad_names.get(global_q, ""))

        # Compact notes (collapsed)
        with st.expander("ℹ️ Signal notes", expanded=False):
            for key, label in labels.items():
                note = sigs.get(key, {}).get("note", "")
                if note:
                    st.caption(f"**{label}:** {note}")
            if t1a.get("data_quality") == "vix_proxy":
                st.caption("⚠️ Gamma using VIX proxy — SPY options give precise GEX on Rebuild.")
            st.caption(f"Hedgeye GIP: Global economy in **{global_q}** — {quad_names.get(global_q, '')}. "
                       f"(Structural/Monthly/Markov quads di box bawah.)")
    else:
        st.caption("Tier1Alpha signals computing — click Rebuild.")

    st.divider()


def _fallback_dashboard(snap: dict):
    """Fallback minimal dashboard if legacy fails."""
    st.title("🏠 Dashboard (fallback)")
    gip = snap.get("gip", {})
    if isinstance(gip, dict):
        sq = gip.get("structural_quad", "?")
        mq = gip.get("monthly_quad", "?")
    else:
        sq = getattr(gip, "structural_quad", "?")
        mq = getattr(gip, "monthly_quad", "?")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Structural Quad", sq)
    c2.metric("Monthly Quad", mq)
    c3.metric("VIX", f"{(snap.get('vix') or 0):.2f}")
    c4.metric("DXY", f"{(snap.get('dxy') or 0):.2f}")
    health = snap.get("market_health", {})
    score = health.get("score", 50) if isinstance(health, dict) else 50
    c5.metric("Health", f"{score:.0f}/100")
