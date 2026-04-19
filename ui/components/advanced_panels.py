"""advanced_panels.py — All new feature panels in one file

Contains:
- render_data_freshness_strip()    — data quality indicator per series
- render_backtest_panel()          — historical quad performance
- render_intraday_panel()          — real-time regime update
- render_position_tracker()        — active trade lifecycle
- render_afl_bridge_panel()        — AFL bandarmologi setup + status
"""
from __future__ import annotations
import math
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional


# ── Helpers ──────────────────────────────────────────────────────────────────

def _pill(text: str, bg: str, fg: str = "#fff", size: int = 11) -> str:
    return (f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:4px;'
            f'font-size:{size}px;font-weight:600;margin:1px;display:inline-block;">{text}</span>')

def _bar(label: str, val: float, color: str = "#276749", width: int = 100) -> str:
    pct = int(min(1.0, max(0.0, val)) * width)
    return (f'<div style="display:flex;align-items:center;gap:6px;margin:2px 0;">'
            f'<span style="font-size:11px;color:#a0aec0;width:120px;">{label}</span>'
            f'<div style="width:{width}px;background:#1a202c;height:6px;border-radius:3px;">'
            f'<div style="width:{pct}px;height:6px;background:{color};border-radius:3px;"></div></div>'
            f'<span style="font-size:10px;color:{color};width:32px;">{int(val*100)}%</span>'
            f'</div>')

def _mc(label: str, value: str, sub: str = "", cls: str = "neu") -> None:
    color = {"good":"#3dbb6c","warn":"#e5a020","bad":"#e05252","neu":"#888"}.get(cls,"#888")
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:8px;padding:8px 12px;margin-bottom:5px;">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;opacity:.4;margin-bottom:2px;">{label}</div>'
        f'<div style="font-size:16px;font-weight:700;color:{color};">{value}</div>'
        f'{"<div style=font-size:10px;opacity:.5;margin-top:2px>" + sub + "</div>" if sub else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. DATA FRESHNESS STRIP
# ═══════════════════════════════════════════════════════════════════════════

def render_data_freshness_strip(snap: dict) -> None:
    """Compact data freshness indicator — shows in status bar."""
    df = snap.get("data_freshness", {})
    if not df:
        return
    
    label = df.get("freshness_label", "Unknown")
    color = df.get("freshness_color", "#718096")
    conf = float(df.get("overall_confidence", 0.5))
    stale = int(df.get("stale_count", 0))
    missing = int(df.get("missing_count", 0))
    warning = df.get("warning_text")
    
    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:8px;padding:3px 10px;'
        f'background:{color}18;border:1px solid {color}44;border-radius:6px;">'
        f'<span style="font-size:10px;font-weight:700;color:{color};">◉ DATA: {label.upper()}</span>'
        f'<span style="font-size:10px;color:#718096;">{conf:.0%} confidence</span>'
        + (f'<span style="font-size:10px;color:#e05252;">{stale} stale</span>' if stale > 0 else "")
        + (f'<span style="font-size:10px;color:#fc8181;">{missing} missing</span>' if missing > 0 else "")
        + f'</div>',
        unsafe_allow_html=True,
    )
    if warning:
        st.warning(f"⚠️ {warning}")


def render_data_freshness_detail(snap: dict) -> None:
    """Full data freshness breakdown table."""
    df = snap.get("data_freshness", {})
    if not df:
        st.info("Data freshness engine not available.")
        return
    
    series = df.get("series", {})
    if not series:
        return
    
    rows = []
    for name, info in sorted(series.items()):
        status = info.get("status", "?")
        score = float(info.get("score", 0))
        age = info.get("age_days")
        latest = info.get("latest", "—")
        data_type = info.get("type", "?")
        
        status_color = {"live":"#3dbb6c","fresh":"#68d391","aging":"#f6ad55","stale":"#fc8181","missing":"#e53e3e","error":"#e53e3e"}.get(status,"#718096")
        
        rows.append({
            "Series": name,
            "Type": data_type.upper(),
            "Status": status.upper(),
            "Age (days)": str(age) if age is not None else "—",
            "Latest": latest,
            "Score": f"{score:.0%}",
        })
    
    df_table = pd.DataFrame(rows)
    st.dataframe(df_table, use_container_width=True, hide_index=True, height=420)


# ═══════════════════════════════════════════════════════════════════════════
# 2. BACKTEST PANEL
# ═══════════════════════════════════════════════════════════════════════════

def render_backtest_panel(snap: dict) -> None:
    """Historical quad performance backtest results."""
    bt = snap.get("backtest_data", {})
    q = snap.get("q", {})
    current_quad = q.get("quad", "Q?")
    
    if not bt:
        st.info("Backtest computing... Results will appear after first full data load.")
        st.caption("Backtest uses 8 years of price history to compute historical returns per quad regime.")
        return
    
    st.markdown(
        '<div style="font-size:12px;color:#4a5568;margin-bottom:10px;">'
        'Historical performance when this exact regime occurred in the past. '
        'Uses price-based quad classification (SPY + TLT RoC) vs forward returns.</div>',
        unsafe_allow_html=True,
    )
    
    # Tab per quad
    tabs = st.tabs(["Q1 Goldilocks", "Q2 Reflation", "Q3 Stagflation", "Q4 Deflation"])
    quad_labels = ["Q1", "Q2", "Q3", "Q4"]
    
    for tab, quad in zip(tabs, quad_labels):
        with tab:
            qd = bt.get(quad, {})
            if not qd:
                st.caption(f"Insufficient historical data for {quad}.")
                continue
            
            n = qd.get("n_periods", 0)
            dur = qd.get("avg_duration_weeks", 0)
            bias = qd.get("confidence_bias", "?")
            best = qd.get("best_assets", [])
            worst = qd.get("worst_assets", [])
            is_current = quad == current_quad
            
            bias_col = {"reliable":"#3dbb6c","noisy":"#e5a020","unreliable":"#e05252"}.get(bias,"#718096")
            
            if is_current:
                st.markdown(
                    f'<div style="background:#276749;border-radius:6px;padding:5px 10px;margin-bottom:6px;">'
                    f'<span style="color:#68d391;font-weight:700;font-size:11px;">● CURRENT REGIME</span></div>',
                    unsafe_allow_html=True,
                )
            
            col1, col2, col3 = st.columns(3)
            with col1: _mc("Historical periods", str(n), "instances found")
            with col2: _mc("Avg duration", f"{dur:.0f}w", "typical regime length")
            with col3: _mc("Signal quality", bias.title(), "reliability of pattern", "good" if bias=="reliable" else ("warn" if bias=="noisy" else "bad"))
            
            # Best/worst performers table
            asset_returns = qd.get("asset_returns", {})
            if asset_returns:
                rows = []
                for tk, info in sorted(asset_returns.items(), key=lambda x: x[1].get("mean_3m_pct",0), reverse=True):
                    r3m = info.get("mean_3m_pct", 0)
                    hit = info.get("hit_rate_pct", 0)
                    sharpe = info.get("sharpe", 0)
                    n_samp = info.get("n", 0)
                    name = info.get("name", tk)
                    
                    rows.append({
                        "Asset": name,
                        "Ticker": tk,
                        "Avg 3M Return": f"{r3m:+.1f}%",
                        "Hit Rate": f"{hit:.0f}%",
                        "Sharpe (3M)": f"{sharpe:+.2f}",
                        "N": n_samp,
                    })
                
                df_bt = pd.DataFrame(rows)
                st.dataframe(df_bt, use_container_width=True, hide_index=True, height=340)
                
                if best:
                    st.markdown("**Historical winners:** " + " ".join(
                        _pill(tk, "#1a3a2a") for tk in best
                    ), unsafe_allow_html=True)
                if worst:
                    st.markdown("**Historical losers:** " + " ".join(
                        _pill(tk, "#3a1a1a") for tk in worst
                    ), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# 3. INTRADAY REGIME PANEL
# ═══════════════════════════════════════════════════════════════════════════

def render_intraday_panel(snap: dict) -> None:
    """Intraday regime update — real-time probability shifts."""
    intraday = snap.get("intraday", {})
    q = snap.get("q", {})
    
    if not intraday:
        st.info("Intraday engine not available.")
        return
    
    regime = intraday.get("intraday_regime", "neutral")
    strength = intraday.get("signal_strength", "noise")
    summary = intraday.get("summary", "")
    action = intraday.get("action_note", "")
    
    regime_cfg = {
        "risk_on":       ("#276749", "✅ Risk-On Tape"),
        "risk_off":      ("#c53030", "🚨 Risk-Off Tape"),
        "inflationary":  ("#c05621", "🔥 Inflationary Impulse"),
        "deflationary":  ("#2b6cb0", "🧊 Deflationary Pressure"),
        "neutral":       ("#4a5568", "⚪ Neutral / Noise"),
    }
    r_color, r_label = regime_cfg.get(regime, ("#4a5568", "Neutral"))
    
    strength_cfg = {"strong":"⚡","moderate":"•","weak":"·","noise":"○"}
    s_icon = strength_cfg.get(strength, "•")
    
    st.markdown(
        f'<div style="background:{r_color}18;border:1.5px solid {r_color};border-radius:8px;'
        f'padding:10px 14px;margin-bottom:10px;">'
        f'<div style="font-size:14px;font-weight:700;color:{r_color};">'
        f'{s_icon} {r_label} — {strength.upper()}</div>'
        f'<div style="font-size:11px;color:#a0aec0;margin-top:4px;">{summary}</div>'
        + (f'<div style="font-size:11px;color:#f6ad55;margin-top:4px;font-weight:600;">{action}</div>' if action else "")
        + '</div>',
        unsafe_allow_html=True,
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Intraday signals:**")
        for label, val, good_high in [
            ("Risk-On", intraday.get("risk_on",0), True),
            ("Inflation Pressure", intraday.get("inflation_pressure",0), False),
            ("Flight to Safety", intraday.get("flight_to_safety",0), False),
            ("Credit Stress", intraday.get("credit_stress",0), False),
        ]:
            v = float(val)
            color = ("#3dbb6c" if (v >= 0.6 and good_high) or (v < 0.4 and not good_high)
                     else "#e05252" if (v < 0.4 and good_high) or (v >= 0.6 and not good_high)
                     else "#e5a020")
            st.markdown(_bar(label, v, color), unsafe_allow_html=True)
    
    with col2:
        st.markdown("**Intraday price moves:**")
        moves = [
            ("SPY 1D", intraday.get("spy_1d",0), True),
            ("TLT 1D", intraday.get("tlt_1d",0), True),
            ("Oil 1D", intraday.get("oil_1d",0), None),
            ("VIX 1D (pts)", intraday.get("vix_1d",0)/30, False),
            ("HYG 1D", intraday.get("hyg_1d",0), True),
        ]
        for label, val, good_pos in moves:
            v = float(val)
            if good_pos is True:
                c = "#3dbb6c" if v > 0 else "#e05252"
            elif good_pos is False:
                c = "#e05252" if v > 0 else "#3dbb6c"
            else:
                c = "#e5a020"
            pct_str = f"{v*100:+.2f}%" if label != "VIX 1D (pts)" else f"{intraday.get('vix_1d',0):+.1f}pts"
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:2px 0;">'
                f'<span style="font-size:11px;color:#a0aec0;">{label}</span>'
                f'<span style="font-size:12px;font-weight:700;color:{c};">{pct_str}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    
    # Probability shifts
    st.markdown("**Regime probability shifts from intraday:**")
    q_probs = q.get("probs", {})
    for quad_k in ["Q1","Q2","Q3","Q4"]:
        base = float(q_probs.get(quad_k, 0.25))
        shift_key = f"{quad_k.lower()}_shift"
        shift = float(intraday.get(shift_key, 0))
        adjusted = min(1.0, max(0.0, base + shift))
        shift_color = "#3dbb6c" if shift > 0.02 else "#e05252" if shift < -0.02 else "#718096"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:6px;margin:2px 0;">'
            f'<span style="font-size:11px;width:24px;font-family:monospace;">{quad_k}</span>'
            f'<div style="width:80px;background:#1a202c;height:5px;border-radius:3px;">'
            f'<div style="width:{int(base*80)}px;height:5px;background:#4a5568;border-radius:3px;"></div></div>'
            f'<div style="width:80px;background:#1a202c;height:5px;border-radius:3px;">'
            f'<div style="width:{int(adjusted*80)}px;height:5px;background:{shift_color};border-radius:3px;"></div></div>'
            f'<span style="font-size:10px;color:{shift_color};font-family:monospace;">{shift:+.1%}</span>'
            f'<span style="font-size:10px;color:#718096;">{base:.0%} → {adjusted:.0%}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════
# 4. POSITION TRACKER
# ═══════════════════════════════════════════════════════════════════════════

def render_position_tracker(snap: dict) -> None:
    """Active position lifecycle tracker with add/close UI."""
    from engines.position_tracker_engine import add_position, close_position
    
    pos_data = snap.get("positions", {})
    active = pos_data.get("active", [])
    exit_sigs = pos_data.get("exit_signals", [])
    history = pos_data.get("history", [])
    
    # Exit signal alerts (top priority)
    if exit_sigs:
        st.markdown(f"### 🚨 Exit Signals ({len(exit_sigs)})")
        for sig in exit_sigs:
            urgency = sig.get("urgency", "hold")
            urg_col = {"act_now":"#e53e3e","watch":"#dd6b20","hold":"#4a5568"}.get(urgency,"#4a5568")
            action = sig.get("action","?").replace("_"," ").upper()
            st.markdown(
                f'<div style="background:{urg_col}18;border:1px solid {urg_col};border-radius:6px;'
                f'padding:8px 12px;margin-bottom:5px;">'
                f'<div style="display:flex;justify-content:space-between;">'
                f'<span style="color:{urg_col};font-weight:700;">{sig.get("ticker","")} — {action}</span>'
                f'<span style="font-size:10px;color:#718096;">{urgency.upper()}</span>'
                f'</div>'
                f'<div style="font-size:11px;color:#a0aec0;margin-top:2px;">{sig.get("reason","")[:80]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown("---")
    
    # Active positions table
    t1, t2, t3 = st.tabs(["📊 Active Positions", "➕ Add Position", "📜 History"])
    
    with t1:
        if not active:
            st.info("No active positions tracked. Add positions in the 'Add Position' tab.")
        else:
            rows = []
            for p in active:
                pnl = float(p.get("pnl_pct", 0))
                exit_sc = float(p.get("exit_signal_score", 0))
                rows.append({
                    "Ticker": p.get("ticker","?"),
                    "Mkt": p.get("market","?")[:4],
                    "Side": p.get("side","?").upper(),
                    "Entry": f"{p.get('entry_price',0):.2f}",
                    "Now": f"{p.get('current_price',0):.2f}",
                    "P&L %": f"{pnl:+.1f}%",
                    "Days": p.get("days_held",0),
                    "Stop": f"{p.get('stop_price',0):.2f}",
                    "Target": f"{p.get('target_price',0):.2f}",
                    "Exit Sig": f"{exit_sc:.0%}",
                    "Quad": p.get("entry_quad","?"),
                })
            
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True, height=300)
            
            # Quick close
            st.markdown("**Close position:**")
            cl1, cl2, cl3 = st.columns([2,2,1])
            with cl1:
                pos_options = {f"{p.get('ticker','')} ({p.get('side','')} #{p.get('id',0)})": p.get("id",0) for p in active}
                selected = st.selectbox("Select position", list(pos_options.keys()), label_visibility="collapsed")
            with cl2:
                close_px = st.number_input("Close price", min_value=0.0, value=0.0, label_visibility="collapsed")
            with cl3:
                if st.button("Close ✓", type="primary"):
                    pid = pos_options.get(selected, 0)
                    if pid and close_px > 0:
                        close_position(pid, close_px, "manual")
                        st.success(f"Position {selected} closed at {close_px}")
                        st.rerun()
    
    with t2:
        st.markdown("#### Add New Position")
        c1, c2 = st.columns(2)
        with c1:
            ticker = st.text_input("Ticker (e.g. ADRO.JK, BTC-USD, XLE)", "")
            market = st.selectbox("Market", ["ihsg","us","fx","commodities","crypto"])
            side = st.selectbox("Side", ["long","short"])
            entry_q = snap.get("q",{}).get("quad","Q?")
            entry_quad = st.text_input("Entry quad", entry_q)
        with c2:
            entry_price = st.number_input("Entry price", min_value=0.0, value=0.0)
            size_pct = st.number_input("Size % (portfolio)", min_value=0.0, max_value=100.0, value=5.0)
            stop_pct = st.number_input("Stop loss %", min_value=0.0, max_value=50.0, value=7.0)
            target_pct = st.number_input("Target %", min_value=0.0, max_value=500.0, value=20.0)
        notes = st.text_area("Notes / thesis", "")
        
        if st.button("➕ Add Position", type="primary"):
            if ticker and entry_price > 0:
                pid = add_position(
                    ticker=ticker.strip().upper(),
                    market=market, side=side,
                    entry_price=entry_price,
                    entry_quad=entry_quad,
                    size_pct=size_pct,
                    stop_pct=stop_pct,
                    target_pct=target_pct,
                    notes=notes,
                )
                st.success(f"Position added: {ticker} #{pid}")
                st.rerun()
            else:
                st.error("Enter ticker and entry price")
    
    with t3:
        if not history:
            st.info("No closed positions yet.")
        else:
            rows = []
            for p in history:
                pnl = p.get("pnl_pct")
                rows.append({
                    "Ticker": p.get("ticker","?"),
                    "Side": str(p.get("side","?")).upper(),
                    "Entry": f"{p.get('entry_price',0):.2f}",
                    "Close": f"{p.get('close_price',0):.2f}" if p.get("close_price") else "—",
                    "P&L %": f"{pnl:+.1f}%" if pnl is not None else "—",
                    "Reason": p.get("close_reason","?"),
                    "Date": str(p.get("closed_at",""))[:10],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=300)


# ═══════════════════════════════════════════════════════════════════════════
# 5. AFL BRIDGE PANEL
# ═══════════════════════════════════════════════════════════════════════════

def render_afl_bridge_panel(snap: dict) -> None:
    """AFL bandarmologi bridge — setup instructions and status."""
    from data.afl_bridge import validate_broker_flow_file, get_setup_instructions
    
    broker = snap.get("broker_flow", {})
    status = validate_broker_flow_file()
    
    if status.get("valid"):
        n = status.get("n_signals", 0)
        action = status.get("market_action", "?")
        ts = status.get("timestamp", "")[:16]
        st.success(f"✅ AFL Connected — {n} signals · {action} · Updated: {ts}")
    else:
        reason = status.get("reason", "Unknown")
        st.warning(f"⚠️ AFL Not Connected — {reason}")
    
    t1, t2 = st.tabs(["📋 Setup Guide", "💻 AFL Code Template"])
    
    with t1:
        instructions = get_setup_instructions()
        st.markdown(instructions)
        
        st.markdown("#### Hengky Adinata Bandarmologi — Key Signals")
        st.markdown("""
| Signal | What it means | Action |
|--------|--------------|--------|
| `bid_queue_depth > 0.65` | Strong demand, thin offer | Accumulation likely |
| `offer_thin = True` | Easy markup | Buyer in control |
| `days_accumulating >= 3` | Multi-day pattern | More reliable signal |
| `unusual_activity = True` | Volume > 2x avg | Big player active |
| `net_broker_score > 0.5` | Strong net buy | High conviction |
| **Double conviction** | Broker + Macro align | Highest entry quality |
        """)
    
    with t2:
        st.markdown("Copy this code into your AmiBroker AFL formula:")
        from data.afl_bridge import get_afl_code_template
        try:
            afl_code = get_afl_code_template()
            st.code(afl_code, language="text")
        except Exception:
            st.info("AFL code template available in `data/afl_bridge.py`")
