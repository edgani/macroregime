"""engines/v38_dashboard_render.py — v38

ONE-LINE INTEGRATION dengan app.py.

Edward cukup tambah 2 baris di tiap page function:
    from engines.v38_dashboard_render import render_v38_complete
    render_v38_complete("us_stocks", snap, prices, st)

Module ini handle SEMUA v38 render:
  - Daily plays (scalp/swing setups)
  - Chain reaction projection per top pick
  - Movement timing per ticker
  - IHSG specialist (konglomerasi + goreng) [kalau market=ihsg]
  - Crypto on-chain proxy [kalau market=crypto]
  - Auto-discovery hook (silent — runs in background)

Graceful degradation: kalau engine v38 belum ada, function silent return.
Tidak akan break app.py existing flow.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# DEFENSIVE IMPORTS — never break app.py
# ═══════════════════════════════════════════════════════════════════════

_ENGINES = {}

try:
    from engines.daily_play_engine import DailyPlayEngine, format_daily_play_markdown
    _ENGINES["daily_play"] = True
except Exception as e:
    logger.warning(f"daily_play_engine not loaded: {e}")
    _ENGINES["daily_play"] = False

try:
    from engines.chain_reaction_engine import get_chain_engine
    _ENGINES["chain_reaction"] = True
except Exception as e:
    logger.warning(f"chain_reaction_engine not loaded: {e}")
    _ENGINES["chain_reaction"] = False

try:
    from engines.movement_timing_engine import MovementTimingDetector, format_movement_regime_markdown
    _ENGINES["movement_timing"] = True
except Exception as e:
    logger.warning(f"movement_timing_engine not loaded: {e}")
    _ENGINES["movement_timing"] = False

try:
    from engines.ihsg_specialist_v38 import get_ihsg_specialist
    _ENGINES["ihsg"] = True
except Exception as e:
    logger.warning(f"ihsg_specialist_v38 not loaded: {e}")
    _ENGINES["ihsg"] = False

try:
    from engines.crypto_onchain_proxy import CryptoOnChainProxy, format_crypto_signal_markdown
    _ENGINES["crypto"] = True
except Exception as e:
    logger.warning(f"crypto_onchain_proxy not loaded: {e}")
    _ENGINES["crypto"] = False

try:
    from engines.ticker_discovery_engine import get_discovery_engine
    _ENGINES["discovery"] = True
except Exception as e:
    logger.warning(f"ticker_discovery_engine not loaded: {e}")
    _ENGINES["discovery"] = False

# v37 Alpha Synthesis (8 hybrid frameworks) — NEW integration
try:
    from engines.alpha_synthesis_v37 import AlphaSynthesisEngine, generate_alpha_primer
    _ENGINES["alpha_synthesis"] = True
except Exception as e:
    logger.warning(f"alpha_synthesis_v37 not loaded: {e}")
    _ENGINES["alpha_synthesis"] = False

# v36 Bottleneck KB v2 — NEW integration
try:
    from engines.bottleneck_kb_v2 import (
        lookup_ticker_in_kb, get_accounts_tracking_ticker, get_account_lens,
        BOTTLENECK_KB_V36, ACCOUNT_THOUGHT_PROCESS_V36,
    )
    _ENGINES["bottleneck_kb_v2"] = True
except Exception as e:
    logger.warning(f"bottleneck_kb_v2 not loaded: {e}")
    _ENGINES["bottleneck_kb_v2"] = False


# ═══════════════════════════════════════════════════════════════════════
# MAIN RENDERER
# ═══════════════════════════════════════════════════════════════════════

def render_v38_complete(market: str, snap: Dict, prices: Dict, st_mod,
                        top_n_for_chain_context: int = 5,
                        max_daily_plays: int = 10) -> None:
    """
    Render all v38 enhancements for a given market page.

    Drop-in: call this at the bottom of any page_*() function in app.py.

    Args:
        market: "us_stocks" | "forex" | "commodities" | "crypto" | "ihsg" | "global"
        snap: orchestrator snapshot dict
        prices: prices dict (or snap.get("prices", {}))
        st_mod: streamlit module (passed as `st`)
        top_n_for_chain_context: how many top tickers to show chain projection for
        max_daily_plays: cap on daily plays displayed
    """
    if not any(_ENGINES.values()):
        return  # No engines loaded, silent return

    try:
        # ── Section 1: Daily Plays (all markets) ──────────────────────
        if _ENGINES["daily_play"]:
            _render_daily_plays(market, snap, prices, st_mod, max_daily_plays)

        # ── Section 2: Market-specific ────────────────────────────────
        if market == "ihsg" and _ENGINES["ihsg"]:
            _render_ihsg_extras(snap, prices, st_mod)
        elif market == "crypto" and _ENGINES["crypto"]:
            _render_crypto_extras(snap, prices, st_mod)

        # ── Section 3: Chain Reaction context for top picks ──────────
        if _ENGINES["chain_reaction"]:
            _render_chain_context_for_actionable(market, snap, prices, st_mod,
                                                  top_n_for_chain_context)

        # ── Section 4 (NEW): Alpha Synthesis v37 — 8 hybrid frameworks ──
        if _ENGINES.get("alpha_synthesis"):
            _render_alpha_synthesis_picks(market, snap, prices, st_mod)

        # ── Section 5 (NEW): Surface existing engines from snap ──────
        _render_engine_snapshots(market, snap, st_mod)

        # ── Section 6: Run auto-discovery silently in background ─────
        if _ENGINES["discovery"] and _ENGINES["chain_reaction"]:
            _run_discovery_silent(snap)

    except Exception as e:
        logger.error(f"v38 render failed for {market}: {e}", exc_info=True)
        # Silent — don't break the page


# ═══════════════════════════════════════════════════════════════════════
# Section 1: Daily Plays
# ═══════════════════════════════════════════════════════════════════════

def _render_daily_plays(market: str, snap: Dict, prices: Dict, st_mod,
                         max_plays: int) -> None:
    """Render daily plays section."""
    st_mod.divider()
    st_mod.markdown("## ⚡ Daily Plays — Scalp & Swing Setups")
    st_mod.caption("v38 · 7 setup types · Filter: R:R≥1.8, Confidence≥60%")

    # Get appropriate universe
    universe = _get_market_universe(market, snap, prices)
    if not universe:
        st_mod.info(f"No universe available for {market}")
        return

    # Run scan
    engine = DailyPlayEngine(market=market)
    plays = engine.scan_universe(universe, snap, prices)

    if not plays:
        st_mod.info(
            "No daily plays meet strict filter right now. "
            "Pasar quiet, ga ada setup yang qualified."
        )
        return

    # Split LONG/SHORT
    longs = [p for p in plays if p.direction == "LONG"][:max_plays]
    shorts = [p for p in plays if p.direction == "SHORT"][:max_plays]

    st_mod.markdown(
        f"**{len(plays)} setups detected** · 🟢 {len(longs)} Long · 🔴 {len(shorts)} Short"
    )

    if longs:
        tab_labels = [f"🟢 Long ({len(longs)})"]
        if shorts:
            tab_labels.append(f"🔴 Short ({len(shorts)})")
        tabs = st_mod.tabs(tab_labels)

        with tabs[0]:
            for play in longs:
                _render_daily_play_card(play, st_mod)
        if shorts and len(tabs) > 1:
            with tabs[1]:
                for play in shorts:
                    _render_daily_play_card(play, st_mod)
    elif shorts:
        st_mod.markdown("### 🔴 Short Setups")
        for play in shorts:
            _render_daily_play_card(play, st_mod)


def _render_daily_play_card(play, st_mod) -> None:
    """Render single daily play as compact card."""
    dir_color = "#3FB950" if play.direction == "LONG" else "#F85149"
    setup_emoji = {
        "GAP_AND_GO": "🚀", "GAP_FILL": "🔄", "SQUEEZE_SETUP": "⚡",
        "MEAN_REVERT_FADE": "🎯", "RANGE_BREAK": "💥",
        "GAMMA_FLIP_PLAY": "🌪️", "MOMENTUM_PULLBACK": "📈",
    }.get(play.setup_type, "🎲")

    reasoning_html = " · ".join(play.reasoning[:3])

    html = f'''<div style="background:#161B22;border:1px solid #30363D;border-left:3px solid {dir_color};
                    border-radius:6px;padding:11px 14px;margin:6px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span style="color:{dir_color};font-weight:800;font-size:1rem;">
                {setup_emoji} {play.ticker} · {play.setup_type}
            </span>
            <span style="background:#21262D;color:#E6EDF3;padding:3px 9px;
                         border-radius:9px;font-size:0.7rem;font-weight:700;">
                R:R {play.risk_reward:.2f} · {play.confidence:.0f}%
            </span>
        </div>
        <div style="font-size:0.75rem;color:#C9D1D9;margin:6px 0;">
            Entry <b>${play.entry:.2f}</b> → T1 <b>${play.target_1:.2f}</b> 
            → T2 <b>${play.target_2:.2f}</b> · Stop <b>${play.stop:.2f}</b> · 
            Size {play.sizing_pct:.1f}% · {play.horizon}
        </div>
        <div style="font-size:0.65rem;color:#8B949E;margin-top:4px;">
            {reasoning_html}
        </div>
        <div style="font-size:0.65rem;color:#A855F7;margin-top:4px;font-style:italic;">
            ↪ {play.execution_notes}
        </div>
    </div>'''
    st_mod.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# Section 2: IHSG Extras
# ═══════════════════════════════════════════════════════════════════════

def _render_ihsg_extras(snap: Dict, prices: Dict, st_mod) -> None:
    """Render IHSG-specific konglomerasi + goreng context."""
    st_mod.divider()
    st_mod.markdown("## 🇮🇩 IHSG Specialist — Konglomerasi & Goreng Phase")
    st_mod.caption("v38 · 21 konglomerasi mapped · 4-phase goreng detector")

    ihsg = get_ihsg_specialist()

    # Hedgeye Quad cross-check
    try:
        quad_check = ihsg.check_indonesia_quad(snap, prices, hedgeye_call="Q4")
        if quad_check:
            match_emoji = "✅" if quad_check.match else "⚠️"
            match_color = "#3FB950" if quad_check.match else "#F0883E"
            st_mod.markdown(
                f'<div style="background:#161B22;border:1px solid #30363D;border-left:3px solid {match_color};'
                f'padding:10px 14px;border-radius:6px;margin:8px 0;">'
                f'<b style="color:{match_color};">{match_emoji} Hedgeye Quad Cross-Check</b><br>'
                f'<span style="font-size:0.8rem;color:#C9D1D9;">'
                f'Our estimate: <b>{quad_check.our_estimate}</b> · '
                f'Hedgeye says: <b>{quad_check.hedgeye_call}</b><br>'
                f'{quad_check.recommendation}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    except Exception as e:
        logger.debug(f"IHSG quad check failed: {e}")

    # Goreng phase detector for top IHSG tickers
    ihsg_tickers = [t for t in prices.keys() if t.endswith(".JK")][:30]
    if not ihsg_tickers:
        st_mod.info("No IHSG tickers in current snap.")
        return

    goreng_signals = []
    for ticker in ihsg_tickers:
        try:
            import pandas as pd
            p = pd.Series(prices.get(ticker, []))
            if len(p) < 30:
                continue
            phase = ihsg.detect_goreng_phase(ticker, p, news_count=0)
            if phase and phase.confidence >= 0.45:
                goreng_signals.append(phase)
        except Exception:
            continue

    # Sort by confidence
    goreng_signals.sort(key=lambda g: g.confidence, reverse=True)

    if goreng_signals:
        st_mod.markdown("### 🍳 Goreng Phase Detector (Top Signals)")
        for sig in goreng_signals[:8]:
            ctx = ihsg.get_conglomerate_context(sig.ticker)
            group_str = f"**{ctx.group}** ({ctx.patriarch})" if ctx else "—"

            phase_color_map = {
                "PHASE_1_AKUMULASI": "#58A6FF",
                "PHASE_2_CORP_ACTION": "#3FB950",
                "PHASE_3_LIQUIDITAS": "#F0883E",
                "PHASE_4_EUFORIA": "#F85149",
            }
            phase_color = phase_color_map.get(sig.current_phase, "#8B949E")
            
            sister_html = ""
            if ctx and ctx.sister_tickers:
                sister_html = f"<br><span style='font-size:0.62rem;color:#8B949E;'>Sister: {', '.join(ctx.sister_tickers[:6])}</span>"

            html = f'''<div style="background:#161B22;border:1px solid #30363D;border-left:3px solid {phase_color};
                            border-radius:6px;padding:10px 13px;margin:6px 0;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="color:#E6EDF3;font-weight:800;font-size:0.95rem;">
                        {sig.ticker}
                    </span>
                    <span style="background:{phase_color}22;color:{phase_color};padding:3px 9px;
                                 border-radius:9px;font-size:0.65rem;font-weight:700;
                                 border:1px solid {phase_color}55;">
                        {sig.current_phase} · {sig.confidence*100:.0f}%
                    </span>
                </div>
                <div style="font-size:0.7rem;color:#C9D1D9;margin-top:5px;">
                    {group_str}{sister_html}
                </div>
                <div style="font-size:0.7rem;color:#A855F7;margin-top:5px;">
                    ↪ <b>{sig.action}</b> · {sig.estimated_phase_duration_remaining}
                </div>
                <div style="font-size:0.62rem;color:#8B949E;margin-top:4px;">
                    {'  ·  '.join(sig.signals_detected[:2])}
                </div>
            </div>'''
            st_mod.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# Section 3: Crypto On-Chain Proxy
# ═══════════════════════════════════════════════════════════════════════

def _render_crypto_extras(snap: Dict, prices: Dict, st_mod) -> None:
    """Render crypto on-chain proxy signals."""
    st_mod.divider()
    st_mod.markdown("## 🪙 Crypto On-Chain Proxy")
    st_mod.caption("v38 · Proxies via price/volume (real on-chain via Glassnode/Nansen unavailable)")

    proxy = CryptoOnChainProxy()
    crypto_tickers = [t for t in prices.keys()
                      if "-USD" in t or t.endswith("USDT") or t in ("BTC", "ETH", "SOL")]
    if not crypto_tickers:
        st_mod.info("No crypto tickers in snap.")
        return

    import pandas as pd
    btc_series = None
    if "BTC-USD" in prices:
        try:
            btc_series = pd.Series(prices["BTC-USD"])
        except Exception:
            pass

    signals = []
    for ticker in crypto_tickers[:20]:
        try:
            p = pd.Series(prices.get(ticker, []))
            if len(p) < 60:
                continue
            sig = proxy.detect(ticker, p, btc_prices=btc_series, snap=snap)
            if sig and sig.proxy_score >= 50:
                signals.append(sig)
        except Exception:
            continue

    signals.sort(key=lambda s: s.proxy_score, reverse=True)

    if not signals:
        st_mod.info("No crypto signals above 50/100 proxy score this snapshot.")
        return

    st_mod.markdown(f"**{len(signals)} signals** above proxy score 50")
    for sig in signals[:10]:
        action_color = {
            "ACCUMULATE": "#3FB950", "RIDE": "#58A6FF",
            "FADE": "#F85149", "AVOID": "#8B949E", "MONITOR": "#F0883E",
        }.get(sig.action, "#8B949E")

        patterns_html = " · ".join(sig.detected_patterns[:2])

        html = f'''<div style="background:#161B22;border:1px solid #30363D;border-left:3px solid {action_color};
                        border-radius:6px;padding:10px 13px;margin:6px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="color:#E6EDF3;font-weight:800;font-size:0.95rem;">
                    🪙 {sig.ticker}
                </span>
                <span style="background:{action_color}22;color:{action_color};padding:3px 9px;
                             border-radius:9px;font-size:0.65rem;font-weight:700;">
                    {sig.action} · {sig.proxy_score:.0f}/100
                </span>
            </div>
            <div style="font-size:0.7rem;color:#C9D1D9;margin-top:5px;">
                Bias: <b>{sig.direction_bias}</b> · Horizon: {sig.horizon}
            </div>
            <div style="font-size:0.65rem;color:#8B949E;margin-top:4px;">
                Whale {sig.whale_activity_score:.0f} · Cycle {sig.cycle_position_score:.0f} · 
                Funding {sig.funding_extreme_score:.0f} · RS {sig.relative_strength_score:.0f}
            </div>
            <div style="font-size:0.65rem;color:#A855F7;margin-top:4px;">
                {patterns_html}
            </div>
        </div>'''
        st_mod.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# Section 4: Chain Reaction Context for Top Picks
# ═══════════════════════════════════════════════════════════════════════

def _render_chain_context_for_actionable(market: str, snap: Dict, prices: Dict,
                                           st_mod, top_n: int) -> None:
    """Render chain reaction projection for top actionable tickers in this market."""
    ce = get_chain_engine()
    if not ce.chains:
        return

    # Get top tickers from composite signals (LONG/SHORT, high confidence)
    composite = snap.get("composite_signals", {}) or {}
    actionable = []
    for ticker, sig in composite.items():
        if not isinstance(sig, dict):
            continue
        if sig.get("direction") in ("LONG", "SHORT") and sig.get("confidence", 0) >= 0.55:
            # Check if ticker is in this market's universe
            if not _matches_market(ticker, market):
                continue
            actionable.append((ticker, sig))

    actionable.sort(key=lambda x: x[1].get("confidence", 0), reverse=True)
    actionable = actionable[:top_n]

    if not actionable:
        return

    # Find which have chain context
    chain_results = []
    rr_all = (snap.get("risk_ranges", {}) or {}).get("asset_ranges", {})
    for ticker, sig in actionable:
        rr = rr_all.get(ticker, {})
        price = float(rr.get("px", 0))
        if price <= 0:
            continue
        proj = ce.project(ticker, price)
        if proj:
            chain_results.append((ticker, sig, proj))

    if not chain_results:
        return

    st_mod.divider()
    st_mod.markdown("## 🔗 Chain Reaction Projection (Top Picks)")
    st_mod.caption("v38 · Forward-looking multiplier scenarios based on chain position")

    for ticker, sig, proj in chain_results:
        # Build chain pills
        chain_pills = "".join([
            f'<span style="background:#58A6FF22;color:#58A6FF;padding:3px 9px;'
            f'border-radius:9px;font-size:0.6rem;margin:1px;border:1px solid #58A6FF55;'
            f'font-weight:700;">{p.chain_name} · T{p.tier}</span>'
            for p in proj.positions[:3]
        ])

        cascade_str = ", ".join(proj.forward_cascade_tickers[:6]) if proj.forward_cascade_tickers else "(end of chain)"

        html = f'''<div style="background:#161B22;border:2px solid #C9A96188;border-radius:8px;
                        padding:13px 16px;margin:8px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                <span style="color:#C9A961;font-weight:800;font-size:1.05rem;">
                    🔗 {ticker} · {sig.get("direction")}
                </span>
                <span style="background:#C9A96133;color:#C9A961;padding:4px 11px;
                             border-radius:11px;font-size:0.7rem;font-weight:800;
                             border:1px solid #C9A96188;">
                    Bull {proj.bull_case_multiplier:.1f}x · Base {proj.base_case_multiplier:.1f}x
                </span>
            </div>
            <div style="margin:6px 0;">{chain_pills}</div>
            <div style="font-size:0.72rem;color:#C9D1D9;margin-top:8px;line-height:1.5;">
                Current: <b>${proj.current_price:,.2f}</b> · 
                Targets: <span style="color:#3FB950;">🟢 ${proj.bull_target:,.2f}</span> · 
                <span style="color:#F0883E;">🟡 ${proj.base_target:,.2f}</span> · 
                <span style="color:#F85149;">🔴 ${proj.bear_target:,.2f}</span><br>
                <span style="color:#8B949E;font-size:0.65rem;">
                    Horizon: {proj.combined_horizon} · 
                    Cascade forward: {cascade_str}
                </span>
            </div>
        </div>'''
        st_mod.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# Section 4 (NEW): Alpha Synthesis v37 — 8 Hybrid Frameworks
# ═══════════════════════════════════════════════════════════════════════

def _render_alpha_synthesis_picks(market: str, snap: Dict, prices: Dict, st_mod) -> None:
    """Render alpha synthesis picks from 8 hybrid frameworks."""
    try:
        engine = AlphaSynthesisEngine()
        universe = _get_market_universe(market, snap, prices)
        if not universe:
            return

        # Scan top 50 tickers (performance cap)
        signals = engine.scan_universe(universe[:50], snap, prices)
        if not signals:
            return

        # Find convergent (2+ frameworks on same ticker)
        convergent = engine.find_convergent_tickers(signals)

        st_mod.divider()
        st_mod.markdown("## ⭐ Alpha Synthesis — 8 Hybrid Frameworks (v37)")
        st_mod.caption(
            f"v37 · {len(signals)} signals across {len(set(s.ticker for s in signals))} tickers · "
            f"{len(convergent)} multi-framework convergent picks (BE THE ALPHA)"
        )

        # Top convergent first (highest conviction)
        if convergent:
            convergent_sorted = sorted(
                convergent.items(),
                key=lambda kv: max(s.conviction for s in kv[1]),
                reverse=True,
            )
            for ticker, sigs in convergent_sorted[:6]:
                _render_alpha_convergent_card(ticker, sigs, st_mod)

        # Single-framework signals (top 5)
        single = [s for s in signals if s.ticker not in convergent]
        if single:
            st_mod.markdown(
                '<div style="font-size:0.7rem;color:#58A6FF;text-transform:uppercase;'
                'font-weight:700;margin:8px 0 4px;letter-spacing:0.5px;">'
                '🔍 Single-Framework Signals'
                '</div>',
                unsafe_allow_html=True,
            )
            for sig in single[:5]:
                _render_alpha_single_card(sig, st_mod)
    except Exception as e:
        logger.debug(f"alpha synthesis render failed: {e}")


def _render_alpha_convergent_card(ticker: str, signals: List, st_mod) -> None:
    """Render multi-framework convergent ticker."""
    import numpy as np
    direction = signals[0].direction
    dir_color = "#3FB950" if direction == "LONG" else "#F85149"
    n_frameworks = len(signals)
    avg_conv = float(np.mean([s.conviction for s in signals]))

    framework_pills = "".join([
        f'<span style="background:#58A6FF22;color:#58A6FF;'
        f'padding:3px 9px;border-radius:9px;font-size:0.6rem;margin:1px;'
        f'border:1px solid #58A6FF55;font-weight:700;">{s.framework}</span>'
        for s in signals
    ])

    # Bottleneck KB context (NEW integration)
    btk_context = ""
    if _ENGINES.get("bottleneck_kb_v2"):
        try:
            btk = lookup_ticker_in_kb(ticker)
            if btk:
                accounts = btk.get("accounts", [])
                btk_context = (
                    f'<div style="font-size:0.62rem;color:#A855F7;margin-top:4px;">'
                    f'📚 Bottleneck KB: {btk.get("bottleneck_id","?")} (tier {btk.get("tier","?")}) · '
                    f'Tracked by: {", ".join(accounts[:3])}'
                    f'</div>'
                )
        except Exception:
            pass

    html = f'''<div style="background:#161B22;border:2px solid #C9A961AA;border-radius:8px;
                padding:12px 14px;margin:6px 0;box-shadow:0 0 15px #C9A96122;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:7px;">
            <span style="color:{dir_color};font-size:1.1rem;font-weight:800;">
                ⭐ {ticker} {direction}
            </span>
            <span style="background:#C9A96133;color:#C9A961;
                         padding:4px 12px;border-radius:11px;font-size:0.7rem;
                         font-weight:800;border:1px solid #C9A96188;">
                {n_frameworks} FRAMEWORKS · {avg_conv:.0f}/100
            </span>
        </div>
        <div style="margin:6px 0;">{framework_pills}</div>
        <div style="font-size:0.7rem;color:#C9D1D9;line-height:1.5;margin-top:6px;
                    background:#0D111766;padding:8px 10px;border-radius:4px;
                    border-left:2px solid #C9A961;">
            {signals[0].thesis[:280]}...
        </div>
        {btk_context}
    </div>'''
    st_mod.markdown(html, unsafe_allow_html=True)


def _render_alpha_single_card(sig, st_mod) -> None:
    """Render single-framework alpha signal."""
    dir_color = "#3FB950" if sig.direction == "LONG" else "#F85149"
    components_str = " · ".join(sig.framework_components[:3])

    html = f'''<div style="background:#161B22;border:1px solid #30363D;border-radius:6px;
                padding:9px 12px;margin:4px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="color:{dir_color};font-weight:800;font-size:0.9rem;">
                {sig.ticker} {sig.direction}
            </span>
            <span style="color:#58A6FF;font-size:0.65rem;font-weight:700;">
                {sig.framework} · {sig.conviction:.0f}
            </span>
        </div>
        <div style="font-size:0.62rem;color:#8B949E;margin-top:3px;">
            {components_str}
        </div>
    </div>'''
    st_mod.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
# Section 5 (NEW): Surface Existing Engines from Snapshot
# ═══════════════════════════════════════════════════════════════════════

def _render_engine_snapshots(market: str, snap: Dict, st_mod) -> None:
    """
    Surface engines that orchestrator builds but page didn't show.

    Shows: discovery_brain, smart_money, capital_rotation, cascade_engine.
    Compact display — doesn't take much vertical space.
    """
    try:
        # Get relevant data
        discovery = snap.get("discovery_brain", {}) or {}
        smart_money = snap.get("smart_money", {}) or {}
        capital_rot = snap.get("capital_rotation", {}) or {}
        cascade = snap.get("cascade_engine", {}) or snap.get("cascade", {}) or {}

        # If nothing to show, return
        if not (discovery or smart_money or capital_rot or cascade):
            return

        st_mod.divider()
        st_mod.markdown("## 🎯 Orchestrator Engine Highlights")
        st_mod.caption("Surfacing existing engines that build in orchestrator but didn't have UI")

        # Build 4-column metric row
        cols = st_mod.columns(4)

        # Discovery Brain
        with cols[0]:
            if isinstance(discovery, dict):
                by_mode = discovery.get("by_mode", {})
                total = sum(len(v) for v in by_mode.values() if isinstance(v, list)) if by_mode else 0
                if total > 0:
                    st_mod.metric(
                        "🔍 Discovery Brain",
                        f"{total} candidates",
                        f"A={len(by_mode.get('adaptive',[]))} R={len(by_mode.get('reactive',[]))} P={len(by_mode.get('proactive',[]))}",
                    )

        # Smart Money
        with cols[1]:
            if isinstance(smart_money, dict):
                consensus = smart_money.get("consensus_picks", [])
                if consensus:
                    st_mod.metric(
                        "💰 Smart Money",
                        f"{len(consensus)} consensus",
                        "13F-tracked",
                    )

        # Capital Rotation
        with cols[2]:
            if isinstance(capital_rot, dict):
                rot_status = capital_rot.get("status", capital_rot.get("validation", ""))
                rot_top = capital_rot.get("dominant_sector", capital_rot.get("top_rotation", ""))
                if rot_status or rot_top:
                    st_mod.metric(
                        "🔄 Capital Rotation",
                        str(rot_status)[:20] if rot_status else "—",
                        str(rot_top)[:20] if rot_top else "",
                    )

        # Cascade Engine
        with cols[3]:
            if isinstance(cascade, dict):
                shocks = cascade.get("active_shocks", 0) or len(cascade.get("shocks", []) or [])
                impacts = cascade.get("total_impacts", 0)
                if shocks > 0:
                    st_mod.metric(
                        "⚡ Cascade Engine",
                        f"{shocks} shocks",
                        f"{impacts} impacts",
                    )

        # ── NEW v38.2: Auto-Discovery v3 (4 previously-orphaned engines now active) ──
        auto_disc = snap.get("auto_discovery", {}) or {}
        if isinstance(auto_disc, dict) and auto_disc:
            st_mod.markdown(
                '<div style="font-size:0.78rem;color:#A855F7;text-transform:uppercase;'
                'font-weight:700;margin:14px 0 6px;letter-spacing:0.5px;">'
                '🧠 Auto-Discovery Brain — 4 Previously-Orphaned Engines Now Active'
                '</div>',
                unsafe_allow_html=True,
            )
            ad_cols = st_mod.columns(4)
            with ad_cols[0]:
                clusters = auto_disc.get("clusters", []) or []
                st_mod.metric("📊 Price Clusters", f"{len(clusters)} themes",
                              "FastDTW similarity" if clusters else "—")
            with ad_cols[1]:
                regime_pred = auto_disc.get("regime_predictions", {}) or auto_disc.get("predictions", {}) or {}
                if isinstance(regime_pred, dict) and regime_pred:
                    next_q = regime_pred.get("predicted_quad_3m") or regime_pred.get("next_quad") or regime_pred.get("most_likely", "—")
                    conf = regime_pred.get("confidence", 0) or regime_pred.get("probability", 0)
                    st_mod.metric("🔮 Regime Predictor (3M)", f"{next_q}",
                                  f"{conf:.0%} conf" if conf else "forward-look")
                else:
                    st_mod.metric("🔮 Regime Predictor", "—", "no prediction")
            with ad_cols[2]:
                leading = auto_disc.get("leading_signals", []) or auto_disc.get("indicators", []) or []
                st_mod.metric("📈 Leading Indicators", f"{len(leading)} signals",
                              "GBM regression" if leading else "—")
            with ad_cols[3]:
                graph_info = auto_disc.get("graph", {}) or auto_disc.get("integration", {}) or {}
                if graph_info:
                    nodes = graph_info.get("nodes", 0) or graph_info.get("n_nodes", 0)
                    st_mod.metric("🕸️ Integration Brain", "ACTIVE", f"{nodes} nodes")
                else:
                    st_mod.metric("🕸️ Integration", "ACTIVE", "v3 brain")

            # Expandable details
            if isinstance(regime_pred, dict) and regime_pred:
                with st_mod.expander("🔮 Regime Predictor — Forward-Looking Quad Detail"):
                    st_mod.json(regime_pred)
            if clusters:
                with st_mod.expander(f"📊 Price Clusters — {len(clusters)} Theme Groups"):
                    for i, cl in enumerate(clusters[:8]):
                        if isinstance(cl, dict):
                            theme = cl.get("theme", cl.get("label", f"Cluster {i+1}"))
                            members = cl.get("tickers", cl.get("members", []))
                            st_mod.markdown(f"- **{theme}**: {', '.join(members[:8])}")
            if leading:
                with st_mod.expander(f"📈 Leading Indicators — {len(leading)} Signals"):
                    for sig in leading[:10]:
                        if isinstance(sig, dict):
                            st_mod.markdown(f"- **{sig.get('name', sig.get('indicator', '?'))}**: "
                                            f"{sig.get('signal', sig.get('value', '?'))}")

        # Discovery Brain expandable details
        if isinstance(discovery, dict) and discovery.get("by_mode"):
            with st_mod.expander("🔍 Discovery Brain — Top Candidates"):
                by_mode = discovery.get("by_mode", {})
                for mode in ("adaptive", "reactive", "proactive"):
                    items = by_mode.get(mode, [])
                    if items:
                        st_mod.markdown(f"**{mode.upper()}** ({len(items)})")
                        for item in items[:5]:
                            if isinstance(item, dict):
                                name = item.get("name", item.get("ticker", "?"))
                                conf = item.get("confidence", 0)
                                thesis = item.get("thesis", "")[:120]
                                st_mod.markdown(f"- **{name}** ({conf:.0%}): {thesis}")
                        st_mod.markdown("")

        # Smart Money consensus picks
        if isinstance(smart_money, dict) and smart_money.get("consensus_picks"):
            with st_mod.expander("💰 Smart Money Consensus Picks"):
                for pick in smart_money.get("consensus_picks", [])[:10]:
                    if isinstance(pick, dict):
                        ticker = pick.get("ticker", "?")
                        n_funds = pick.get("n_funds_buying", pick.get("n_buying", 0))
                        thesis = pick.get("thesis", pick.get("rationale", ""))[:150]
                        st_mod.markdown(f"- **{ticker}** ({n_funds} funds buying): {thesis}")

    except Exception as e:
        logger.debug(f"engine snapshots render failed: {e}")


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _get_market_universe(market: str, snap: Dict, prices: Dict) -> List[str]:
    """Get tickers for a specific market."""
    if not prices:
        prices = snap.get("prices", {}) or {}

    all_tickers = list(prices.keys())

    if market == "us_stocks" or market == "us_equity":
        return [t for t in all_tickers if _is_us_equity(t)]
    elif market == "ihsg":
        return [t for t in all_tickers if t.endswith(".JK")]
    elif market == "crypto":
        return [t for t in all_tickers if "-USD" in t or t.endswith("USDT") or t in ("BTC", "ETH", "SOL")]
    elif market == "forex":
        return [t for t in all_tickers if "=X" in t or t in ("DXY", "DX-Y.NYB")]
    elif market == "commodities":
        return [t for t in all_tickers if t.endswith("=F") or t in ("GLD", "SLV", "USO", "UNG", "DBA", "DBC", "DBP")]
    else:
        return all_tickers[:50]


def _is_us_equity(ticker: str) -> bool:
    """Heuristic for US equity (no special suffix, not crypto/forex/futures/index)."""
    if (ticker.endswith(".JK") or ticker.endswith(".T") or ticker.endswith(".KS") or
        ticker.endswith(".SS") or ticker.endswith(".SZ") or ticker.endswith(".HK") or
        ticker.endswith(".L") or ticker.endswith(".AS") or ticker.endswith(".PA") or
        ticker.endswith(".DE")):
        return False
    if "-USD" in ticker or ticker.endswith("USDT"):
        return False
    if "=X" in ticker or "=F" in ticker:
        return False
    if ticker.startswith("^"):
        return False
    return True


def _matches_market(ticker: str, market: str) -> bool:
    """Check if ticker belongs to given market."""
    if market in ("us_stocks", "us_equity"):
        return _is_us_equity(ticker)
    if market == "ihsg":
        return ticker.endswith(".JK")
    if market == "crypto":
        return "-USD" in ticker or ticker.endswith("USDT")
    if market == "forex":
        return "=X" in ticker
    if market == "commodities":
        return ticker.endswith("=F") or ticker in ("GLD", "SLV", "USO", "UNG", "DBA", "DBC", "DBP")
    return True


def _run_discovery_silent(snap: Dict) -> None:
    """Run ticker discovery in background, silent."""
    try:
        ce = get_chain_engine()
        de = get_discovery_engine()
        current = set((snap.get("prices", {}) or {}).keys())
        de.discover_from_chains(current, ce)
        # Don't print summary — silent operation
    except Exception as e:
        logger.debug(f"Discovery silent failed: {e}")


# ═══════════════════════════════════════════════════════════════════════
# Optional: per-ticker detail bundle (call manually if needed)
# ═══════════════════════════════════════════════════════════════════════

def render_ticker_detail_bundle(ticker: str, snap: Dict, prices: Dict, st_mod) -> None:
    """
    Render comprehensive ticker detail (the example from earlier conversation):
      - Movement timing regime
      - Chain reaction projection
      - Full mechanism + cascade forward
      - Multi-framework convergence reference

    Call this when user expands a specific ticker.
    """
    import pandas as pd

    st_mod.markdown(f"# 🎯 {ticker} — Full Detail")

    p = prices.get(ticker)
    if p is None:
        st_mod.warning(f"No price data for {ticker}")
        return

    try:
        price_series = pd.Series(p)
        if len(price_series) < 30:
            st_mod.warning(f"Insufficient price history for {ticker}")
            return
    except Exception:
        st_mod.warning(f"Price data error for {ticker}")
        return

    # Movement timing
    if _ENGINES["movement_timing"]:
        try:
            detector = MovementTimingDetector()
            rr = (snap.get("risk_ranges", {}) or {}).get("asset_ranges", {}).get(ticker, {})
            composite = (snap.get("composite_signals", {}) or {}).get(ticker, {})
            direction = composite.get("direction", "LONG")
            regime = detector.detect(ticker, price_series, snap, direction)
            if regime:
                st_mod.markdown(format_movement_regime_markdown(regime))
                st_mod.divider()
        except Exception as e:
            logger.debug(f"Movement timing render failed: {e}")

    # Chain reaction
    if _ENGINES["chain_reaction"]:
        try:
            ce = get_chain_engine()
            current_price = float(price_series.iloc[-1])
            proj = ce.project(ticker, current_price)
            if proj:
                st_mod.markdown(ce.format_projection_markdown(proj))
                st_mod.divider()
        except Exception as e:
            logger.debug(f"Chain projection render failed: {e}")

    # IHSG context if applicable
    if ticker.endswith(".JK") and _ENGINES["ihsg"]:
        try:
            ihsg = get_ihsg_specialist()
            ctx = ihsg.get_conglomerate_context(ticker)
            if ctx:
                st_mod.markdown(f"### 🏛️ Konglomerasi: {ctx.group}")
                st_mod.markdown(f"**Patriarch**: {ctx.patriarch}")
                st_mod.markdown(f"**Sector**: {ctx.sector_role}")
                st_mod.markdown(f"**Sister tickers**: {', '.join(ctx.sister_tickers[:10])}")
                if ctx.alliances:
                    st_mod.markdown(f"**Active alliances**: {len(ctx.alliances)}")
                    for a in ctx.alliances:
                        st_mod.markdown(f"- {a.get('name', '?')}")
                st_mod.divider()

            phase = ihsg.detect_goreng_phase(ticker, price_series)
            if phase:
                st_mod.markdown(f"### 🍳 Goreng Phase: {phase.current_phase}")
                st_mod.markdown(f"**Confidence**: {phase.confidence*100:.0f}% · **Action**: `{phase.action}`")
                st_mod.markdown(f"**Duration remaining**: {phase.estimated_phase_duration_remaining}")
                st_mod.markdown("**Signals**:")
                for s in phase.signals_detected:
                    st_mod.markdown(f"- {s}")
                if phase.risk_warnings:
                    st_mod.markdown("**⚠️ Risk warnings**:")
                    for w in phase.risk_warnings:
                        st_mod.markdown(f"- {w}")
        except Exception as e:
            logger.debug(f"IHSG detail render failed: {e}")


__all__ = [
    "render_v38_complete",
    "render_ticker_detail_bundle",
]
