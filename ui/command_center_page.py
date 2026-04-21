"""ui/command_center_page.py"""
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
    most_hated = snap.get("most_hated_rally", {})
    prices = snap.get("prices", {})

    st.markdown("## ⚡ COMMAND CENTER")

    # ── Regime Banner ──
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Structural", quad, f"Conf: {conf:.0%}")
    with c2:
        st.metric("Monthly", monthly_quad, "Divergent" if divergence == "divergent" else "Aligned")
    with c3:
        st.metric("Global", global_quad, "Composite")
    with c4:
        st.metric("Flip Hazard", f"{q.get('flip_hazard', 0):.0%}", "Watch" if q.get('flip_hazard', 0) > 0.5 else "Stable")

    if divergence == "divergent":
        st.warning(f"🔄 Divergence: Structural {quad} vs Monthly {monthly_quad}. Monthly = trigger, Structural = 3M+ positioning.")

    # ── Front-Run Checklist ──
    st.markdown("---")
    st.subheader("🎯 FRONT-RUN CHECKLIST")
    transition = snap.get("regime_transition", {})
    if transition:
        st.markdown(f"**Window:** {transition.get('front_run_window', '—')}")
        st.markdown(f"**Rationale:** {transition.get('front_run_rationale', '—')}")
        early = transition.get("early_warning_signals", [])
        if early:
            st.markdown("**Early Warnings:**")
            for e in early[:4]:
                st.markdown(f"- {e}")

    # ── Narrative Plays ──
    st.markdown("---")
    st.subheader("📰 NARRATIVE PLAYS")
    narr = snap.get("narrative_discovery", {})
    if narr and narr.get("active_narratives"):
        for n in narr["active_narratives"][:3]:
            stage_emoji = {"early": "🌱", "building": "🔥", "mature": "♟️", "exhausted": "💀"}.get(n.get("stage", ""), "◆")
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(
                    f"{stage_emoji} **{n.get('name', '—')}** — {n.get('stage', '—')} "
                    f"· Conviction: {n.get('regime_adjusted_conviction', 0):.0%} "
                    f"· Regime fit: {n.get('regime_multiplier', 1.0):.2f}x"
                )
                st.caption(n.get("action_summary", ""))
                if n.get("claude_insight"):
                    st.caption(f"🧠 {n.get('claude_insight', '')}")
            with col_b:
                bens = n.get("primary_beneficiaries", [])
                for b in bens[:4]:
                    st.markdown(f"`{b}`")
    else:
        st.info("No active narratives. Regime-driven mode.")

    # ── Bottleneck Discovery ──
    st.markdown("---")
    st.subheader("⛓️ SUPPLY CHAIN BOTTLENECKS")
    btl = snap.get("bottleneck_discovery", {})
    if btl and btl.get("active_bottlenecks"):
        for b in btl["active_bottlenecks"][:3]:
            st.markdown(
                f"**{b.get('category', '—')}** — {b.get('stage', '—')} "
                f"· Score: {b.get('composite_score', 0):.2f} "
                f"· Regime fit: {b.get('regime_alignment', 1.0):.2f}x"
            )
            leads = b.get("lead_tickers", [])
            if leads:
                st.markdown("Lead tickers: " + " · ".join(f"`{t}`" for t in leads))

        if btl.get("front_run_basket"):
            st.markdown("**🎯 Front-Run Basket**")
            df = pd.DataFrame(btl["front_run_basket"][:8])
            st.dataframe(
                df[["ticker", "market", "bottleneck", "layer", "conviction", "stage"]],
                use_container_width=True,
                hide_index=True,
            )

        if btl.get("cross_market_chains"):
            st.markdown("**🔗 Cross-Market Chains**")
            for chain in btl["cross_market_chains"][:2]:
                chain_str = " → ".join(
                    f"{c['layer']} ({c['leader']})" for c in chain.get("chain", [])
                )
                st.markdown(f"*{chain['category']}*: {chain_str}")
    else:
        st.info("No active bottlenecks detected.")

    # ── Master Ticker Board ──
    st.markdown("---")
    st.subheader("📋 MASTER TICKER BOARD — NOW vs FRONT-RUN")

    all_tickers = []

    rt = snap.get("regime_tickers", {})
    if rt:
        for side, tickers in [
            ("US Longs", rt.get("us_longs", [])),
            ("US Shorts", rt.get("us_shorts", [])),
            ("IHSG Buys", rt.get("ihsg_buys", [])),
            ("FX Longs", rt.get("fx_longs", [])),
            ("Commodity Longs", rt.get("commodity_longs", [])),
            ("Crypto Longs", rt.get("crypto_longs", [])),
        ]:
            for t in tickers:
                all_tickers.append({"ticker": t, "source": "Regime", "side": side})

    if btl and btl.get("front_run_basket"):
        for item in btl["front_run_basket"][:6]:
            all_tickers.append(
                {
                    "ticker": item["ticker"],
                    "source": "Bottleneck",
                    "side": item["bottleneck"],
                    "conviction": item.get("conviction", 0),
                }
            )

    if narr and narr.get("active_narratives"):
        for n in narr["active_narratives"][:3]:
            for b in n.get("primary_beneficiaries", [])[:3]:
                all_tickers.append(
                    {
                        "ticker": b,
                        "source": "Narrative",
                        "side": n.get("name", ""),
                        "conviction": n.get("regime_adjusted_conviction", 0),
                    }
                )

    if all_tickers:
        df_board = pd.DataFrame(all_tickers)
        st.dataframe(df_board, use_container_width=True, hide_index=True)
    else:
        st.info("Ticker board building...")

    # ── Rally Monitor ──
    if most_hated:
        st.markdown("---")
        st.subheader("📈 MOST HATED RALLY MONITOR")
        clear = most_hated.get("clear_count", 0)
        st.progress(clear / 4.0, text=f"{clear}/4 checklist items clear")
        st.markdown(f"**Stage:** {most_hated.get('stage', 'monitor')} · **Action:** {most_hated.get('action', 'Selective')}")
