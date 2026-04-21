"""ui/command_center_v4.py — Adaptive Discovery UI"""
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

    vix_bucket = "🟢" if vix < 19 else "🟡" if vix < 29 else "🔴"

    st.markdown("## ⚡ COMMAND CENTER")

    # ── Regime Banner ──
    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 2])
    with c1:
        st.metric("Structural", quad, f"Conf: {conf:.0%}")
    with c2:
        st.metric("Monthly", monthly_quad, "🔥 Divergent" if divergence == "divergent" else "✅ Aligned")
    with c3:
        st.metric("Global", global_quad)
    with c4:
        flip = q.get("flip_hazard", 0)
        st.metric("Flip Hazard", f"{flip:.0%}", "Watch" if flip > 0.5 else "Stable")
    with c5:
        st.metric("VIX", f"{vix:.1f}", f"{vix_bucket} {'Investable' if vix < 19 else 'Chop' if vix < 29 else 'Defensive'}")

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
    else:
        st.info("No transition signals.")

    # ── Narrative Plays ──
    st.markdown("---")
    st.subheader("📰 NARRATIVE PLAYS")
    narr = snap.get("narrative_discovery", {})
    if narr and narr.get("active_narratives"):
        for n in narr["active_narratives"][:3]:
            stage = n.get("stage", "—")
            stage_emoji = {"early": "🌱", "building": "🔥", "mature": "♟️", "exhausted": "💀"}.get(stage, "◆")
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(
                    f"{stage_emoji} **{n.get('name', '—')}** — {stage} "
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

    # ── Adaptive Bottleneck Discovery ──
    st.markdown("---")
    st.subheader("🔍 ADAPTIVE BOTTLENECK SCAN — Auto-Discovered")
    btl = snap.get("bottleneck_discovery", {})
    if btl:
        method = btl.get("discovery_method", "unknown")
        st.caption(f"Discovery method: **{method}** | Scanned all available tickers | No hardcoded library")

        # Summary
        if btl.get("summary"):
            st.info(btl["summary"])

        # Active Sectors
        if btl.get("active_sectors"):
            st.markdown("**📊 Auto-Discovered Sectors**")
            for sector in btl["active_sectors"][:4]:
                with st.container():
                    cols = st.columns([3, 2, 2, 2])
                    with cols[0]:
                        st.markdown(f"**{sector.get('sector_name', '—')}**")
                        st.caption(f"Stage: {sector.get('stage', '—')}")
                    with cols[1]:
                        st.metric("Bottleneck Score", f"{sector.get('bottleneck_score', 0):.2f}")
                    with cols[2]:
                        st.metric("SPY Corr", f"{sector.get('spy_correlation', 0):.2f}")
                    with cols[3]:
                        st.metric("Vol Z-Score", f"{sector.get('avg_volume_zscore', 0):.2f}")

                    tickers = sector.get("tickers", [])
                    markets = sector.get("markets", [])
                    if tickers:
                        st.markdown("Tickers: " + " · ".join(f"`{t}`" for t in tickers[:8]))
                    if markets:
                        st.caption(f"Markets: {', '.join(markets)}")

        # Leader Tickers
        if btl.get("leader_tickers"):
            st.markdown("**🏆 Momentum Leaders**")
            leaders = btl["leader_tickers"][:8]
            if leaders:
                df_leaders = pd.DataFrame(leaders)
                display_cols = ["ticker", "market", "regime", "score", "r1m", "r3m", "volume_zscore"]
                df_display = df_leaders[[c for c in display_cols if c in df_leaders.columns]]
                st.dataframe(df_display, use_container_width=True, hide_index=True)

        # Supply Chain
        if btl.get("supply_chain_chains"):
            st.markdown("**⛓️ Supply Chain Lead-Lag**")
            for chain in btl["supply_chain_chains"][:2]:
                st.markdown(f"*{chain.get('sector', '—')}*:")
                for rel in chain.get("lead_lag_relationships", [])[:3]:
                    st.markdown(
                        f"  → `{rel.get('upstream', '—')}` leads `{rel.get('downstream', '—')}` "
                        f"by {rel.get('lag_days', 0)}d (corr: {rel.get('correlation', 0):.2f})"
                    )

        # Cross-Market
        if btl.get("cross_market_opportunities"):
            st.markdown("**🌍 Cross-Market Arbitrage**")
            for opp in btl["cross_market_opportunities"][:2]:
                st.markdown(
                    f"**{opp.get('theme', '—')}** — Score: {opp.get('bottleneck_score', 0):.2f}"
                )
                by_market = opp.get("tickers_by_market", {})
                for market, tickers in by_market.items():
                    st.markdown(f"  {market}: " + ", ".join(f"`{t}`" for t in tickers))

        # Front-Run Basket
        if btl.get("front_run_basket"):
            st.markdown("**🎯 Adaptive Front-Run Basket**")
            basket = btl["front_run_basket"][:10]
            if basket:
                cols = ["ticker", "market", "sector", "conviction", "stage", "r1m", "r3m", "volume_zscore", "position_size", "source"]
                df = pd.DataFrame([{k: item.get(k, "—") for k in cols} for item in basket])
                st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Bottleneck discovery loading...")

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
            all_tickers.append({
                "ticker": item.get("ticker", "—"),
                "source": "Adaptive",
                "side": item.get("sector", ""),
                "conviction": item.get("conviction", 0),
                "position_size": item.get("position_size", ""),
            })

    if narr and narr.get("active_narratives"):
        for n in narr["active_narratives"][:3]:
            for b in n.get("primary_beneficiaries", [])[:3]:
                all_tickers.append({
                    "ticker": b,
                    "source": "Narrative",
                    "side": n.get("name", ""),
                    "conviction": n.get("regime_adjusted_conviction", 0),
                })

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
