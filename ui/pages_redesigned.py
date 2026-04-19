"""pages_redesigned.py — Consolidated 5-tab architecture

REPLACES the old 8-tab structure:
  Old: Command Center | Radar | Health | Playbook | Markets | Narrative Lab | Risk | Diagnostics
  New: ⚡ Command Center | 📊 Regime Intel | 🎯 Strategy | 🌐 Markets | ⚠️ Risk & Diag

Design principles:
  - Every panel earns its spot (no duplication)
  - NOW vs FRONT-RUN visible in Markets
  - Consistent visual language across all tabs
  - Compact but scannable
  - Mobile-readable metric cards
"""
from __future__ import annotations
import math
import streamlit as st
import pandas as pd
from typing import Dict, List, Optional

# ── shared style helpers ───────────────────────────────────────────────────────

def _mc(label: str, value: str, sub: str = "", cls: str = "neu") -> None:
    color = {"good": "#3dbb6c", "warn": "#e5a020", "bad": "#e05252", "neu": "#888"}.get(cls, "#888")
    st.markdown(
        f'<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);'
        f'border-radius:8px;padding:10px 12px;margin-bottom:5px;">'
        f'<div style="font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;'
        f'opacity:.4;margin-bottom:2px;">{label}</div>'
        f'<div style="font-size:17px;font-weight:700;color:{color};line-height:1.2;">{value}</div>'
        f'{"<div style=font-size:11px;opacity:.5;margin-top:2px>" + sub + "</div>" if sub else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _section(title: str) -> None:
    st.markdown(
        f'<div style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;'
        f'opacity:.35;padding:8px 0 4px;border-bottom:1px solid rgba(255,255,255,0.06);'
        f'margin-bottom:8px;">{title}</div>',
        unsafe_allow_html=True,
    )


def _bar(label: str, val: float, note: str = "", good_high: bool = True) -> None:
    val = max(0.0, min(1.0, val))
    fill = val if good_high else 1.0 - val
    color = "#3dbb6c" if fill >= 0.62 else ("#e5a020" if fill >= 0.38 else "#e05252")
    pct = f"{val:.0%}"
    st.markdown(
        f'<div style="margin-bottom:5px;">'
        f'<div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px;">'
        f'<span style="opacity:.7;">{label}</span>'
        f'<span style="color:{color};font-family:monospace;">{pct} {note}</span></div>'
        f'<div style="background:rgba(255,255,255,0.07);height:5px;border-radius:3px;">'
        f'<div style="width:{val*100:.0f}%;background:{color};height:100%;border-radius:3px;"></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _qb(q: str) -> str:
    cfg = {
        "Q1": ("#d4edda","#155724"),
        "Q2": ("#fff3cd","#856404"),
        "Q3": ("#ffeeba","#7d4e00"),
        "Q4": ("#f8d7da","#721c24"),
    }
    bg, fg = cfg.get(q, ("#e2e3e5","#495057"))
    return f'<span style="background:{bg};color:{fg};padding:3px 10px;border-radius:12px;font-weight:700;font-size:11px;">{q}</span>'


def _pill(t: str, bg: str = "#1a3a2a", fg: str = "#fff") -> str:
    return f'<span style="background:{bg};color:{fg};padding:2px 7px;border-radius:3px;font-size:11px;margin:1px;display:inline-block;font-weight:600;">{t}</span>'


def _pills(tickers: list, bg: str = "#1a3a2a") -> str:
    return " ".join(_pill(t, bg) for t in (tickers or []) if t)


def _pct(v) -> str:
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return "—"
    return f"{v:+.1%}" if isinstance(v, float) else str(v)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — REGIME INTEL (merged Radar + Health, no duplicates)
# WHY: macro backdrop, health signals, analog
# ══════════════════════════════════════════════════════════════════════════════

def page_regime_intel(snap: dict) -> None:
    q = snap["q"]; f = snap["f"]; rot = snap["rotation"]
    analog = snap.get("analog", {}); prices = snap.get("prices", {})
    rt = snap.get("regime_transition", {})
    opt = snap.get("options_regime", {})

    s_quad = q["quad"]; m_quad = q["monthly_quad"]; div = q["divergence"]
    conf = q["confidence"]; fh = q["flip_hazard"]; meta_desc = {
        "Q1": "Growth ↑  Inflation ↓ — Goldilocks",
        "Q2": "Growth ↑  Inflation ↑ — Reflation",
        "Q3": "Growth ↓  Inflation ↑ — Stagflation",
        "Q4": "Growth ↓  Inflation ↓ — Deflation Risk",
    }.get(s_quad, "Unknown")

    # ── Page title — clearly different from Command Center ────────────────────
    g_acc = q.get("growth_acc", True); i_acc = q.get("infl_acc", False)

    # Data quality banner first
    ps = f.get("_proxy_share", 1.0); src_q = f.get("macro_source_quality", 0.0)

    st.markdown(
        f'<div style="margin-bottom:10px;">' +
        f'<div style="font-size:11px;font-weight:700;color:#718096;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px;">📊 REGIME INTEL — Why the regime is what it is</div>' +
        f'<div style="font-size:12px;color:#4a5568;">Analytical depth layer. Not for action — for understanding the backdrop. Use Command Center for trades.</div>' +
        f'</div>',
        unsafe_allow_html=True
    )

    if ps > 0.60:
        st.warning(f"⚠️ Macro data quality {src_q:.0%} — FRED limited. Regime signal reliability reduced.")
    elif div == "divergent":
        st.info(f"🔄 **Structural {s_quad} vs Monthly {m_quad}** — Structural = big-picture regime. Monthly = what's happening right now inside that regime. Watch monthly for near-term trades, structural for 3m+ positioning.")

    # ── SUB-TABS: Macro | Health | Analog | Indicators ──────────────────────
    t1, t2, t3, t4 = st.tabs(["📈 Macro & Regime", "📡 Market Health", "🕰️ Analog & Next", "🔑 Raw Indicators"])

    # ── Macro & Regime ────────────────────────────────────────────────────────
    with t1:
        col_a, col_b = st.columns(2)

        with col_a:
            _section("REGIME PROBABILITIES")
            probs = q.get("probs", {}); m_probs = q.get("monthly_probs", {})
            for qk in ["Q1","Q2","Q3","Q4"]:
                p = probs.get(qk, 0.0); pm = m_probs.get(qk, 0.0)
                is_active = qk == s_quad; is_monthly = qk == m_quad and not is_active
                fc = "#3dbb6c" if is_active else ("#e5a020" if is_monthly else "rgba(255,255,255,0.25)")
                marker = "●" if is_active else ("◉" if is_monthly else "○")
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0;">'
                    f'<span style="font-size:11px;width:32px;color:{fc};font-family:monospace;">{marker} {qk}</span>'
                    f'<div style="flex:1;background:rgba(255,255,255,0.07);height:{"7px" if is_active else "5px"};border-radius:3px;">'
                    f'<div style="width:{p*100:.0f}%;background:{fc};height:100%;border-radius:3px;"></div></div>'
                    f'<span style="font-size:11px;width:30px;text-align:right;color:{fc};font-family:monospace;">{p:.0%}</span>'
                    f'<span style="font-size:10px;width:26px;opacity:.35;font-family:monospace;">{pm:.0%}M</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.caption(f"Next: **{q.get('next_quad','?')}** · Duration: {q.get('duration_mat',0):.0%} · Deepness: {q.get('deepness',0):.0%}")

            _section("MACRO RoC INTERNALS — What's driving the regime")
            # This is the actual second-derivative math. Not shown in Command Center.
            # Positive RoC = accelerating. Negative = decelerating.
            roc_rows = [
                ("INDPRO level", f.get("indpro_yoy", float("nan")), f.get("indpro_acc"), "IP YoY"),
                ("INDPRO Δ RoC", f.get("indpro_roc_3m", float("nan")), None, "Accel/decel"),
                ("CPI level", f.get("cpi_yoy", float("nan")), f.get("cpi_acc"), "Headline CPI YoY"),
                ("CPI Δ RoC", f.get("cpi_roc_3m", float("nan")), None, "CPI accel/decel"),
                ("ISM Δ3M", f.get("ism_3m_delta", float("nan")), None, "Demand pipeline"),
                ("Leading composite ★", f.get("leading_indicator_composite", 0.0), None, "Forward signal"),
                ("Inflation shock", f.get("m_shock", f.get("inflation_shock", 0.0)), None, "Supply spike"),
                ("Policy score", f.get("policy_score", 0.0), None, "+cut / -hike"),
            ]
            for lbl, val, acc, note in roc_rows:
                try:
                    v = float(val) if val is not None else float("nan")
                    if not math.isfinite(v): continue
                    if "level" in lbl or "CPI level" in lbl or "INDPRO level" in lbl:
                        vc = "#3dbb6c" if acc is True else ("#e05252" if acc is False else "#a0aec0")
                    else:
                        vc = "#3dbb6c" if v > 0.003 else ("#e05252" if v < -0.003 else "#e5a020")
                    fmt = f"{v:+.3f}" if abs(v) < 1 else f"{v:+.2f}"
                    acc_s = " ▲" if acc is True else (" ▼" if acc is False else "")
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;padding:2px 0;border-bottom:1px solid rgba(255,255,255,0.04);">'
                        f'<div><span style="font-size:11px;color:#a0aec0;">{lbl}</span>'
                        f'<span style="font-size:9px;color:#4a5568;margin-left:4px;">{note}</span></div>'
                        f'<span style="font-size:12px;font-weight:700;font-family:monospace;color:{vc};">{fmt}{acc_s}</span></div>',
                        unsafe_allow_html=True
                    )
                except Exception:
                    pass
                    st.markdown(f'<span style="font-size:10px;color:#4a5568;">❌ {sig}</span>', unsafe_allow_html=True)

        with col_b:
            route_snap = snap.get("route",{}); rm = route_snap.get("primary_meta",{}); alt_m = route_snap.get("alt_meta",{})
            _section("ROUTE STATE")
            rc = rm.get("color","#888")
            st.markdown(
                f'<div style="border:1.5px solid {rc};border-radius:10px;padding:10px 12px;margin-bottom:8px;">'
                f'<div style="font-size:9px;font-weight:700;letter-spacing:.1em;color:{rc};text-transform:uppercase;margin-bottom:3px;">ACTIVE ROUTE</div>'
                f'<div style="font-size:17px;font-weight:700;">{rm.get("emoji","")} {rm.get("label","?")}</div>'
                f'<div style="font-size:11px;opacity:.7;margin-top:3px;">{rm.get("desc","")[:80]}</div>'
                f'<div style="margin-top:5px;font-size:10px;"><b style="color:{rc};">Best:</b> {", ".join(rm.get("long",[])[:3])}</div>'
                f'<div style="font-size:10px;"><b style="color:#e05252;">Avoid:</b> {", ".join(rm.get("avoid",[])[:2])}</div>'
                f'<div style="font-size:10px;opacity:.5;margin-top:3px;">✓ {rm.get("confirm","")[:55]} · ✗ {rm.get("invalidate","")[:45]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown(f'Alt: **{alt_m.get("emoji","")} {alt_m.get("label","?")}** — {alt_m.get("desc","")[:50]}')

            _section("NEWS CATALYST")
            news_snap = snap.get("news_overlay",{})
            if news_snap:
                nc = {"bad":"#e05252","warn":"#e5a020","good":"#3dbb6c","neu":"rgba(255,255,255,0.3)"}.get(news_snap.get("cls","neu"),"#888")
                st.markdown(
                    f'<div style="padding:6px 10px;border-radius:6px;border:1px solid {nc}44;background:{nc}10;font-size:11px;">'
                    f'<b style="color:{nc};">{news_snap.get("label","")}</b><br>{news_snap.get("desc","")[:80]}'
                    f'<br><span style="opacity:.6;">War/Oil: {news_snap.get("war_oil",0):.0%} · Policy: {news_snap.get("policy_pressure",0):.0%} · Relief: {news_snap.get("relief",0):.0%}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Next macro events
            UPCOMING_EVENTS = snap.get("_upcoming_events", [])
            if UPCOMING_EVENTS:
                _section("NEXT CATALYSTS")
                for ev in UPCOMING_EVENTS[:3]:
                    fam_col = {"inflation":"#e05252","labor":"#e5a020","growth":"#e5a020","policy":"#e05252"}.get(ev.get("family",""),"#888")
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.05);">'
                        f'<span style="font-size:11px;font-weight:600;color:{fam_col};">{ev.get("title","")[:35]}</span>'
                        f'<span style="font-size:10px;opacity:.5;font-family:monospace;">{ev.get("countdown","")}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    # ── Market Health ─────────────────────────────────────────────────────────
    with t2:
        h = snap.get("h",{}); cr = snap.get("crash",{}); most_hated = snap.get("most_hated_rally",{})

        top_row = st.columns(4)
        with top_row[0]:
            _mc("Trade Environment", h.get("trade_state","?").title(), "breadth+credit+USD",
                "good" if h.get("trade_state")=="supportive" else ("bad" if h.get("trade_state")=="hostile" else "warn"))
        with top_row[1]:
            vix = f.get("vix_last",20.0)
            vix_b = "Investable" if vix<19 else ("Chop" if vix<29 else "Defensive")
            _mc("VIX", f"{vix:.1f}", vix_b, "good" if vix<19 else ("bad" if vix>28 else "warn"))
        with top_row[2]:
            hy = f.get("hy_oas",float("nan"))
            _mc("HY Spread", f"{hy:.0f}bps" if math.isfinite(hy) else "—", f"1M Δ: {f.get('hy_oas_1m',0):+.0f}bps",
                "good" if (math.isfinite(hy) and hy<350) else ("bad" if (math.isfinite(hy) and hy>500) else "warn"))
        with top_row[3]:
            sc = cr.get("crash_score",0)
            _mc("Crash Meter", f"{sc:.0%}", cr.get("state","?"),
                "good" if sc<0.35 else ("bad" if sc>0.65 else "warn"))

        st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            _section("BREADTH")
            _bar("Sectors above 50-DMA", h.get("sec_support",0.5), f"({h.get('sec_above50',5)}/11)")
            _bar("Small cap health (IWM)", h.get("iwm_trend",0.5))
            _bar("Equal-weight vs cap-weight", max(0,min(1,0.5+h.get("eqw_vs_cw",0)*5)), f"{_pct(h.get('eqw_vs_cw',0))} 3M diff")
            _bar("Broad breadth", h.get("breadth",0.5))
            _bar("Narrow leadership (inv)", 1-h.get("narrow_leadership",0.5), good_high=True)

        with col2:
            _section("CREDIT & VOLATILITY")
            ig = f.get("ig_oas", float("nan"))
            _bar("HY credit health", max(0,min(1,1-(hy-250)/500)) if math.isfinite(hy) else 0.5, f"{hy:.0f}bps" if math.isfinite(hy) else "proxy")
            _bar("IG credit health", max(0,min(1,1-(ig-50)/200)) if math.isfinite(ig) else 0.5, f"{ig:.0f}bps" if math.isfinite(ig) else "n/a")
            _bar("VIX health", max(0,min(1,1-(vix-13)/25)), f"VIX {vix:.1f}")
            vr = f.get("vix_vxv_ratio",float("nan"))
            _bar("Term structure", max(0,min(1,1-(vr-0.85)/0.25)) if math.isfinite(vr) else 0.5, f.get("vix_term_state",""))
            _bar("Credit+Vol composite", h.get("tail",0.5))

        if opt:
            _section("VIX TERM STRUCTURE (OptionsEngine)")
            ts_state = opt.get("term_structure_state","?")
            ts_slope = opt.get("term_structure_slope",0)
            ts_col = "#3dbb6c" if ts_state=="contango" else ("#e05252" if ts_state=="backwardation" else "#e5a020")
            confirm = opt.get("options_regime_confirm","neutral")
            st.markdown(
                f'<div style="display:flex;gap:8px;margin-bottom:6px;">'
                f'<span style="color:{ts_col};font-weight:700;">{ts_state.upper()}</span>'
                f'<span style="opacity:.5;">slope: {ts_slope:+.1f}pts</span>'
                f'<span style="margin-left:auto;color:{"#3dbb6c" if "risk_on" in confirm else "#e05252" if "risk_off" in confirm else "#e5a020"};">{confirm.replace("_"," ").title()}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Yield curve
        sp = f.get("spread_2s10s",float("nan"))
        _section("YIELD CURVE")
        col_y1, col_y2, col_y3 = st.columns(3)
        with col_y1: _mc("2s10s", f"{sp:+.2f}%" if math.isfinite(sp) else "—", f.get("yield_curve_state",""))
        with col_y2: _mc("10s30s", f"{f.get('spread_10s30s',float('nan')):+.2f}%" if math.isfinite(f.get('spread_10s30s',float('nan'))) else "—")
        with col_y3:
            uninverting = f.get("yield_curve_uninverting",False)
            _mc("2s10s 3M Δ", f"{f.get('spread_2s10s_3m',float('nan')):+.2f}%" if math.isfinite(f.get('spread_2s10s_3m',float('nan'))) else "—",
                "⚠️ Uninverting = recession risk" if uninverting else "", "warn" if uninverting else "neu")

        # Sector leadership table
        if prices:
            _section("SECTOR LEADERSHIP (vs SPY 3M)")
            SECS = {"XLE":"Energy","XLF":"Fin","XLI":"Indust","XLB":"Materials","XLK":"Tech",
                    "XLV":"Health","XLY":"Cons.D","XLP":"Cons.S","XLU":"Util","XLRE":"RE","XLC":"Comm"}
            from utils.math_utils import clamp01 as clamp01_

            def ret_n_(s, n):
                if s is None or len(s) < n+1: return float("nan")
                try:
                    b = float(s.iloc[-(n+1)]); e = float(s.iloc[-1])
                    return float(e/b-1) if b != 0 else float("nan")
                except: return float("nan")

            spy3 = ret_n_(prices.get("SPY"), 63)
            rows = []
            for tk, name in SECS.items():
                s = prices.get(tk)
                r3 = ret_n_(s, 63); r1 = ret_n_(s, 21)
                rel = (r3 - spy3) if (math.isfinite(r3) and math.isfinite(spy3)) else float("nan")
                rows.append({"Sector": name, "1M": _pct(r1), "3M": _pct(r3), "vs SPY": _pct(rel)})
            rows.sort(key=lambda r: float(r["vs SPY"].replace("%","").replace("—","0").replace("+","")) if r["vs SPY"]!="—" else -999, reverse=True)
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True, height=320)

        # Checklists compact
        chk = snap.get("checklists",{})
        if chk.get("global"):
            with st.expander("✅ Global trading checklist", expanded=False):
                for item in chk["global"][:12]:
                    try:
                        label, score, note = item[0], float(item[1]), str(item[2]) if len(item)>2 else ""
                        ok_col = "#3dbb6c" if score >= 0.62 else ("#e05252" if score <= 0.38 else "#e5a020")
                        icon = "✓" if score >= 0.62 else ("✗" if score <= 0.38 else "~")
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.04);">' +
                            f'<span style="font-size:11px;color:#a0aec0;">{str(label)}</span>' +
                            f'<span style="color:{ok_col};font-size:11px;font-weight:700;">{icon} {score:.0%}</span></div>',
                            unsafe_allow_html=True
                        )
                        if note:
                            st.markdown(f'<span style="font-size:10px;color:#4a5568;">{note}</span>', unsafe_allow_html=True)
                    except Exception:
                        pass

    # ── Analog & Next ─────────────────────────────────────────────────────────
    with t3:
        col_an, col_next = st.columns([1.1, 0.9])
        with col_an:
            _section("HISTORICAL ANALOG")
            a = analog
            sim = a.get("similarity",0); sim_col = "#3dbb6c" if sim>=0.65 else ("#e5a020" if sim>=0.45 else "#e05252")
            st.markdown(
                f'<div style="padding:10px;border-radius:8px;border:1px solid {sim_col}44;background:{sim_col}08;margin-bottom:8px;">'
                f'<div style="font-size:15px;font-weight:700;">{a.get("label","?")}</div>'
                f'<div style="font-size:11px;opacity:.6;">Similarity: <b style="color:{sim_col};">{sim:.0%}</b></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            path_cols = st.columns(3)
            with path_cols[0]: _mc("1M Path", a.get("path_1m","—"))
            with path_cols[1]: _mc("3M Path", a.get("path_3m","—"))
            with path_cols[2]: _mc("6M Path", a.get("path_6m","—"))
            if a.get("next_bias"):
                st.info(f"**Next bias:** {a['next_bias']}")
            impacts = a.get("impacts",{})
            if impacts:
                st.markdown("**Market impacts:**")
                for mkt, view in impacts.items():
                    v_col = "#3dbb6c" if any(x in str(view).lower() for x in ["bull","up","positive"]) else \
                            "#e05252" if any(x in str(view).lower() for x in ["bear","down","negative"]) else "#e5a020"
                    st.markdown(f'<span style="font-size:11px;"><b>{mkt.upper()}:</b> <span style="color:{v_col};">{view}</span></span><br>', unsafe_allow_html=True)

            # New: v11 RegimeTransitionEngine paths
            if paths:
                _section("TRANSITION PATHS (probability-weighted)")
                for p in paths[:3]:
                    pval = float(p.get("probability",0)); ew = float(p.get("early_warning_score",0))
                    from_q = p.get("from_quad","?"); to_q = p.get("to_quad","?"); tw = p.get("timeframe_weeks",0)
                    p_col = "#e53e3e" if pval>=0.35 else ("#dd6b20" if pval>=0.22 else "#4a5568")
                    st.markdown(
                        f'<div style="display:flex;gap:8px;align-items:center;padding:5px 0;border-bottom:1px solid rgba(255,255,255,0.05);">'
                        f'<span style="font-weight:700;font-size:12px;">{from_q}→{to_q}</span>'
                        f'<span style="color:{p_col};font-family:monospace;font-size:11px;">{int(pval*100)}%</span>'
                        f'<span style="opacity:.5;font-size:10px;">~{tw}w</span>'
                        f'<div style="flex:1;background:#1a202c;height:5px;border-radius:3px;">'
                        f'<div style="width:{int(ew*100)}%;height:5px;background:{p_col};border-radius:3px;"></div></div>'
                        f'<span style="font-size:10px;opacity:.6;">{int(ew*100)}% EW</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    confirms = p.get("confirmation_needed",[])
                    if confirms:
                        st.markdown(f'<span style="font-size:10px;color:#718096;">→ {confirms[0][:60]}</span>', unsafe_allow_html=True)

        with col_next:
            _section("MACRO CALENDAR (next events)")
            news_snap = snap.get("news_overlay",{})
            events = news_snap.get("events",[]) if news_snap else []
            for ev in events[:6]:
                impact = ev.get("impact","watch")
                ev_col = {"high":"#e05252","medium":"#e5a020","watch":"#718096"}.get(impact,"#718096")
                st.markdown(
                    f'<div style="padding:5px 8px;border-left:3px solid {ev_col};margin-bottom:5px;">'
                    f'<div style="display:flex;justify-content:space-between;font-size:11px;">'
                    f'<b>{ev.get("label","")[:35]}</b>'
                    f'<span style="font-family:monospace;opacity:.5;">{ev.get("countdown","")}</span>'
                    f'</div>'
                    f'<div style="font-size:10px;color:{ev_col};">{impact.upper()}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            _section("ROTATION FLOW")
            _bar("EM/IHSG rotation", rot.get("em_score",0.5))
            _bar("US breadth", rot.get("us_breadth",0.5) if rot.get("us_breadth") else snap.get("h",{}).get("breadth",0.5))
            petro = rot.get("petro_score",0.0)
            if petro > 0.45:
                st.warning(f"⚡ **Petrodollar branch active** ({petro:.0%}). Coal exporters can outperform even in Q3.")

    # ── Raw Indicators ────────────────────────────────────────────────────────
    with t4:
        rows = [
            ("── GROWTH ──","",""),
            ("Industrial Production YoY", _pct(f.get("indpro_yoy")), "▲" if f.get("indpro_acc") else "▼"),
            ("Payrolls YoY", _pct(f.get("payrolls_yoy")), "▲" if f.get("payrolls_acc") else "▼"),
            ("Retail Sales YoY", _pct(f.get("retail_yoy")), ""),
            ("ISM Manufacturing", f"{f.get('ism_last',float('nan')):.1f}" if math.isfinite(f.get('ism_last',float('nan'))) else "—", ""),
            ("Unemployment Rate", f"{f.get('unrate',float('nan')):.1f}%" if math.isfinite(f.get('unrate',float('nan'))) else "—", f"3M Δ: {f.get('unrate_3m_delta',0):+.2f}"),
            ("Housing Starts YoY", _pct(f.get("housing_yoy",float("nan"))), ""),
            ("Leading Indicator Composite ★", f"{f.get('leading_indicator_composite',0):+.3f}", "NEW: forward-looking signal"),
            ("── INFLATION ──","",""),
            ("CPI YoY", _pct(f.get("cpi_yoy")), "▲" if f.get("cpi_acc") else "▼"),
            ("Core PCE YoY ★", _pct(f.get("corepce_yoy")), "▲" if f.get("corepce_acc") else "▼"),
            ("Headline-Core Gap ★", _pct(f.get("headline_core_gap")), "+ve = energy/supply-driven"),
            ("5Y Breakeven", f"{f.get('breakeven',float('nan')):.2f}" if math.isfinite(f.get('breakeven',float('nan'))) else "—", ""),
            ("Monthly Inflation Shock ★", f"{f.get('m_shock',0):.3f}", "Short-term supply shock signal"),
            ("── POLICY ──","",""),
            ("Fed Funds Rate", f"{f.get('policy_rate',float('nan')):.2f}%" if math.isfinite(f.get('policy_rate',float('nan'))) else "—", f"3M Δ: {f.get('policy_rate_3m',0):+.2f}"),
            ("Policy Score ★", f"{f.get('policy_score',0):+.3f}", "+ve = cutting/dovish, -ve = hiking"),
            ("Liquidity Score ★", f"{f.get('liq_score',0):+.3f}", "DXY + TLT derived"),
            ("2s10s Yield Curve ★", f"{f.get('spread_2s10s',float('nan')):+.2f}%" if math.isfinite(f.get('spread_2s10s',float('nan'))) else "—", f.get("yield_curve_state","")),
            ("── CREDIT & VOL ──","",""),
            ("HY OAS", f"{f.get('hy_oas',float('nan')):.0f}bps" if math.isfinite(f.get('hy_oas',float('nan'))) else "—", f"1M Δ: {f.get('hy_oas_1m',0):+.0f}bps"),
            ("IG OAS ★", f"{f.get('ig_oas',float('nan')):.0f}bps" if math.isfinite(f.get('ig_oas',float('nan'))) else "—", f"1M Δ: {f.get('ig_oas_1m',0):+.0f}bps"),
            ("VIX / Term Structure ★", f"{f.get('vix_last',20):.1f}", f.get("vix_term_state","")),
            ("── QUAD INTERNALS ★ ──","",""),
            ("Growth Core (RoC-adjusted)", f"{q.get('g_core',0):+.3f}", "+ve = accelerating"),
            ("Inflation Core (RoC-adjusted)", f"{q.get('i_core',0):+.3f}", "+ve = rising"),
            ("Slowdown Flags", f"{q.get('slowdown_flags',0):.0%}", "% of 4 slowdown signals active"),
            ("Data Coverage", f"{f.get('data_coverage',0):.0%}", "Input quality"),
        ]
        st.dataframe(pd.DataFrame(rows, columns=["Indicator","Value","Note"]),
                     use_container_width=True, hide_index=True, height=560)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — STRATEGY (merged Playbook + Narrative Lab + Scenarios)
# WHAT: what to do, in what order, and why
# ══════════════════════════════════════════════════════════════════════════════

def page_strategy(snap: dict) -> None:
    q = snap["q"]; rot = snap["rotation"]; sc = snap["scenarios"]; pb = snap["playbooks"]
    s_quad = q["quad"]

    at = snap.get("asset_translation",{}); route = snap.get("route",{}); route_label = route.get("primary_meta",{}).get("label","?")

    st.markdown(
        f'<div style="font-size:18px;font-weight:800;margin-bottom:2px;">🎯 Strategy — {route_label} ({s_quad})</div>'
        f'<div style="font-size:11px;opacity:.5;margin-bottom:12px;">What to do, in what priority, and when to exit</div>',
        unsafe_allow_html=True,
    )

    t1, t2, t3, t4 = st.tabs(["📋 Playbook", "🔬 Scenarios", "📖 Narratives", "🌐 Cross-Asset"])

    # ── Playbook ──────────────────────────────────────────────────────────────
    with t1:
        # Asset Translation
        if at:
            _section(f"ASSET TRANSLATION — LONG / WATCH / AVOID ({s_quad})")
            at_cols = st.columns(len(at))
            for col, (mkt, setups) in zip(at_cols, at.items()):
                with col:
                    st.markdown(f"**{mkt}**")
                    for setup in setups[:3]:
                        bias = setup.get("bias",""); tickers = setup.get("tickers",[])
                        bc = "good" if "LONG" in bias else ("bad" if "AVOID" in bias or "SHORT" in bias else "warn")
                        bc_col = "#3dbb6c" if bc=="good" else ("#e05252" if bc=="bad" else "#e5a020")
                        st.markdown(
                            f'<div style="border-left:2px solid {bc_col};padding:3px 6px;margin:3px 0;">'
                            f'<span style="color:{bc_col};font-weight:700;font-size:10px;">{bias}</span><br>'
                            f'<span style="font-size:11px;">{setup.get("setup","")[:40]}</span><br>'
                            f'<span style="font-size:10px;opacity:.5;">{", ".join(str(t) for t in tickers[:3])}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

        # Policy playbooks
        _section("POLICY PLAYBOOKS")
        pb_sorted = sorted(pb, key=lambda x: x.get("hypothesis",0), reverse=True)
        for p in pb_sorted:
            hypo = p.get("hypothesis",0); evid = p.get("evidence",0)
            pc = "#3dbb6c" if hypo < 0.35 else ("#e5a020" if hypo < 0.55 else "#e05252")
            st.markdown(
                f'<div style="padding:8px 10px;background:rgba(255,255,255,0.02);border-left:3px solid {pc}55;border-radius:0 6px 6px 0;margin-bottom:5px;">'
                f'<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
                f'<b style="font-size:12px;">{p.get("name","")}</b>'
                f'<span style="font-size:11px;color:{pc};font-family:monospace;">H: {hypo:.0%} · E: {evid:.0%}</span>'
                f'</div>'
                f'<div style="font-size:11px;opacity:.75;">{p.get("desc","")[:100]}</div>'
                f'<div style="font-size:10px;opacity:.4;margin-top:3px;">✗ {" · ".join(p.get("invalidators",[])[:2])}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Scenarios ─────────────────────────────────────────────────────────────
    with t2:
        # News-adaptive scenarios from v11 engine
        what_if = snap.get("what_if_matrix",{}) or sc  # prefer v11 if available
        _section(f"SCENARIO TREE — {q.get('operating',s_quad)}")
        st.caption("Probability-weighted branches from current regime. Higher prob = more likely market path.")
        for name, case in list(what_if.items())[:8]:
            if isinstance(case, dict):
                p = case.get("probability", 0)
                winners = case.get("winners", [])
                losers = case.get("losers", [])
                invalidators = case.get("invalidators", [])
            else:
                p = 0; winners = []; losers = []; invalidators = []
            p_col = "#3dbb6c" if p < 0.15 else ("#e5a020" if p < 0.30 else "#e05252")
            label_short = name[:55]
            with st.expander(f"{label_short}  ·  {p:.0%}", expanded=False):
                col_s, col_f = st.columns(2)
                with col_s:
                    st.markdown("**Winners:**")
                    for w in winners[:3]: st.markdown(f"  ✅ {w}")
                with col_f:
                    st.markdown("**Losers:**")
                    for l in losers[:3]: st.markdown(f"  ❌ {l}")
                if invalidators:
                    st.markdown("**Invalidators:** " + " · ".join(str(i) for i in invalidators[:2]))

    # ── Narratives ────────────────────────────────────────────────────────────
    with t3:
        from ui.components.narrative_discovery_panel import render_narrative_discovery_panel
        render_narrative_discovery_panel(snap)

    # ── Cross-Asset Heatmap ───────────────────────────────────────────────────
    with t4:
        prices = snap.get("prices",{})
        _section("CROSS-ASSET RETURNS HEATMAP")
        ASSETS = {
            "US Equity (SPY)":"SPY","Growth (QQQ)":"QQQ","Small Cap (IWM)":"IWM",
            "Long Bond (TLT)":"TLT","Credit (HYG)":"HYG","Gold (GLD)":"GLD",
            "Oil (CL=F)":"CL=F","Copper":"HG=F","USD (UUP)":"UUP","EM (EEM)":"EEM",
            "IHSG":"^JKSE","BTC":"BTC-USD","ETH":"ETH-USD",
        }

        def ret_n_(s, n):
            if s is None or len(s) < n+1: return float("nan")
            try:
                b = float(s.iloc[-(n+1)]); e = float(s.iloc[-1])
                return float(e/b-1) if b != 0 else float("nan")
            except: return float("nan")

        heat = []
        for name, tk in ASSETS.items():
            s = prices.get(tk)
            heat.append({
                "Asset": name,
                "1W": _pct(ret_n_(s,5)),
                "1M": _pct(ret_n_(s,21)),
                "3M": _pct(ret_n_(s,63)),
                "6M": _pct(ret_n_(s,126)),
                "1Y": _pct(ret_n_(s,252)),
            })
        st.dataframe(pd.DataFrame(heat), use_container_width=True, hide_index=True, height=460)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — MARKETS (NOW plays + FRONT-RUN plays per market)
# WHERE: specific tickers, each market has NOW + FRONT-RUN split
# ══════════════════════════════════════════════════════════════════════════════

def page_markets_v2(snap: dict) -> None:
    q = snap["q"]; f = snap["f"]; prices = snap.get("prices",{}); rot = snap["rotation"]
    ih = snap["ihsg"]; s_quad = q["quad"]; m_quad = q["monthly_quad"]
    tickers = snap.get("regime_tickers",{})
    rt = snap.get("regime_transition",{})
    fw = rt.get("front_run_window","not yet")
    bei = snap.get("bei_flow",{})
    broker = snap.get("broker_flow",{})
    broker_conf = snap.get("broker_confirm",{})

    # Get transition path for front-run label
    paths = rt.get("transition_paths",[])
    tr_from = paths[0].get("from_quad", s_quad) if paths else s_quad
    tr_to = paths[0].get("to_quad","?") if paths else "?"
    tr_label = f"{tr_from}→{tr_to}" if paths else "No transition"
    tr_ew = int(float(paths[0].get("early_warning_score",0))*100) if paths else 0
    fw_col = {"now":"#e53e3e","1-2w":"#dd6b20","3-6w":"#d69e2e","not yet":"#4a5568"}.get(fw,"#4a5568")

    # Front-run signal header
    if fw in ("now","1-2w"):
        fr_picks = tickers.get("front_run_picks",[])
        fr_str = " · ".join([p.get("ticker","") for p in fr_picks[:6] if isinstance(p,dict) and p.get("ticker")])
        st.markdown(
            f'<div style="background:{fw_col}18;border:1.5px solid {fw_col};border-radius:8px;'
            f'padding:8px 14px;margin-bottom:10px;font-size:12px;">'
            f'<span style="color:{fw_col};font-weight:700;">⚡ FRONT-RUN WINDOW: {fw.upper()} · {tr_label} ({tr_ew}% EW)</span><br>'
            f'<span style="color:#e2e8f0;">{fr_str}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    t_ihsg, t_us, t_fx, t_comm, t_crypto = st.tabs(["🇮🇩 IHSG","🇺🇸 US Stocks","💱 FX","🛢️ Commodities","🔐 Crypto"])

    # ── Helper: render NOW/FRONT-RUN dual column ──────────────────────────────
    def _now_fr_header(market: str, now_label: str, fr_signal: str = "") -> None:
        st.markdown(
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px;">'
            f'<div style="background:#0d2818;border:1px solid #276749;border-radius:6px;padding:7px 10px;">'
            f'<div style="font-size:9px;font-weight:700;color:#48bb78;letter-spacing:.1em;">▲ NOW — {now_label}</div></div>'
            f'<div style="background:{fw_col}18;border:1px solid {fw_col};border-radius:6px;padding:7px 10px;">'
            f'<div style="font-size:9px;font-weight:700;color:{fw_col};letter-spacing:.1em;">⚡ FRONT-RUN — {tr_label}</div>'
            + (f'<div style="font-size:9px;color:#718096;margin-top:1px;">{fr_signal[:45]}</div>' if fr_signal else "")
            + f'</div></div>',
            unsafe_allow_html=True,
        )

    # Get front-run data
    try:
        from config.regime_ticker_registry import TRANSITION_FRONT_RUN
        tr_key = f"{tr_from}→{tr_to}"
        tr_data = TRANSITION_FRONT_RUN.get(tr_key, {})
    except Exception:
        tr_data = {}

    def ret_n_(s, n):
        if s is None or len(s) < n+1: return float("nan")
        try:
            b = float(s.iloc[-(n+1)]); e = float(s.iloc[-1])
            return float(e/b-1) if b != 0 else float("nan")
        except: return float("nan")

    # ── IHSG ──────────────────────────────────────────────────────────────────
    with t_ihsg:
        score = ih["ihsg_score"]; sc_col = "#3dbb6c" if score>=0.60 else ("#e5a020" if score>=0.47 else "#e05252")
        top_cols = st.columns(4)
        with top_cols[0]: _mc("IHSG Score", f"{score:.0%}", ih["exec_mode"], "good" if score>=0.60 else ("bad" if score<0.47 else "warn"))
        with top_cols[1]:
            jk = ih["jkse_1m"]
            _mc("^JKSE 1M", _pct(jk), f"3M: {_pct(ih['jkse_3m'])}", "good" if (math.isfinite(jk) and jk>0) else ("bad" if (math.isfinite(jk) and jk<-0.02) else "warn"))
        with top_cols[2]:
            idr = ih["usd_idr_1m"]
            _mc("USD/IDR 1M", _pct(idr), "↑ IDR lemah = bad", "bad" if (math.isfinite(idr) and idr>0.02) else ("good" if (math.isfinite(idr) and idr<-0.01) else "warn"))
        with top_cols[3]:
            # BEI foreign flow
            if bei and bei.get("available"):
                net = float(bei.get("net_rp_billion",0))
                flow_state = bei.get("flow_state",{})
                trend = flow_state.get("trend","neutral")
                fl_col = "good" if "inflow" in trend else ("bad" if "outflow" in trend else "warn")
                _mc("Foreign Flow", flow_state.get("label","—"), f"Net Rp {net:+.0f}B", fl_col)
            else:
                _mc("Foreign Flow", ih.get("flow_state","?"), f"Score: {ih.get('foreign_flow',0):.0%}")

        st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)

        # NOW vs FRONT-RUN
        fr_ihsg_signal = tr_data.get("signal","Enter when IDR < 16k + oil bid + foreign flow positive")[:55]
        _now_fr_header("IHSG", s_quad, fr_ihsg_signal)

        now_ihsg = tickers.get("ihsg_buys",[])[:6]
        fr_ihsg = tr_data.get("ihsg_buy", tickers.get("ihsg_buys",[])[:3])[:4]

        col_now, col_fr = st.columns(2)
        with col_now:
            st.markdown(_pills(now_ihsg, "#1a3a2a"), unsafe_allow_html=True)
        with col_fr:
            st.markdown(_pills(fr_ihsg, "#3a2a0a"), unsafe_allow_html=True)

        # Broker flow confluence
        if broker.get("connected"):
            market_action = broker.get("market_action","neutral")
            buys = broker.get("buys",[])[:4]; sells = broker.get("sells",[])[:4]
            action_col = {"accumulation":"#48bb78","distribution":"#e53e3e","neutral":"#718096","mixed":"#f6ad55"}.get(market_action,"#718096")
            conf_status = broker_conf.get("status","") if broker_conf else ""
            conf_detail = broker_conf.get("detail","") if broker_conf else ""
            conf_col = {"double_conviction":"#48bb78","contradiction":"#e53e3e","partial_confirm":"#f6ad55"}.get(conf_status,"#718096")
            st.markdown(
                f'<div style="background:#1a1a2a;border:1px solid #21262d;border-radius:6px;padding:8px 10px;margin-top:6px;">'
                f'<span style="font-size:10px;font-weight:700;letter-spacing:.1em;color:#718096;">BROKER FLOW (AFL)</span><br>'
                f'<span style="color:{action_col};font-weight:700;font-size:12px;">{market_action.upper()}</span>'
                + (f' · <span style="color:{conf_col};font-size:11px;">{conf_detail[:50]}</span>' if conf_detail else "")
                + '<br><span style="font-size:11px;">🟢 ' + " ".join(_pill(t,"#1a3a2a") for t in buys) + '</span>'
                + ('<br><span style="font-size:11px;">🔴 ' + " ".join(_pill(t,"#3a1a1a") for t in sells) + '</span>' if sells else "")
                + '</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # IHSG stock rankings
        _section("IHSG STOCK RANKINGS (1M momentum)")
        if ih.get("stock_rows"):
            df = pd.DataFrame([{k:v for k,v in r.items() if not k.startswith("_")} for r in ih["stock_rows"]])
            st.dataframe(df, use_container_width=True, hide_index=True, height=320)

        # Spillover chain + quad impact
        col_s, col_q = st.columns(2)
        with col_s:
            _section("SPILLOVER CHAIN")
            IHSG_BUCKETS_LOCAL = snap.get("_ihsg_buckets",{})
            top_s = ih["top_sector"]; spill = ih["spill_ihsg"]
            roles = ["Leader","Beneficiary 2","Breadth follower","Defensif"]
            for i, fam in enumerate(spill):
                role = roles[i] if i < len(roles) else ""
                r_col = ["#3dbb6c","#e5a020","#888","#e05252"][min(i,3)]
                st.markdown(
                    f'<div style="display:flex;gap:6px;margin-bottom:3px;align-items:center;">'
                    f'<span style="font-size:10px;opacity:.4;width:16px;">{i+1}.</span>'
                    f'<span style="color:{r_col};font-weight:600;font-size:11px;">{fam}</span>'
                    f'<span style="font-size:10px;opacity:.4;">{role}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        with col_q:
            _section("MACRO IMPACT ON IHSG")
            impact_map = {
                "Q1": ("✅ Kondusif","Asing masuk, bank dan consumer cyclical lead."),
                "Q2": ("⚡ Mixed-bullish","Coal/logam/CPO outperform. Watch IDR."),
                "Q3": ("⚠️ Tertekan","USD kuat, asing keluar. Hanya coal exporter tahan."),
                "Q4": ("🔴 Defensif","Asing keluar EM. Hold TLKM/ICBP/KLBF."),
            }
            label, desc = impact_map.get(s_quad, ("?",""))
            st.markdown(f'<b style="font-size:13px;">{label}</b>', unsafe_allow_html=True)
            st.caption(desc)

    # ── US STOCKS ─────────────────────────────────────────────────────────────
    with t_us:
        us_longs = tickers.get("us_longs",[])[:6]
        us_shorts = tickers.get("us_shorts",[])[:4]
        fr_us_long = tr_data.get("us_long", us_longs[:3])[:4]
        fr_us_short = tr_data.get("us_short",[])[:3]
        fr_us_signal = tr_data.get("signal","")[:60]

        _now_fr_header("US", s_quad, fr_us_signal)
        col_now, col_fr = st.columns(2)
        with col_now:
            st.markdown("**Long:**")
            st.markdown(_pills(us_longs, "#1a3a2a"), unsafe_allow_html=True)
            if us_shorts:
                st.markdown("**Short:**")
                st.markdown(_pills(us_shorts, "#3a1a1a"), unsafe_allow_html=True)
        with col_fr:
            st.markdown("**Long (front-run):**")
            st.markdown(_pills(fr_us_long, "#3a2a0a"), unsafe_allow_html=True)
            if fr_us_short:
                st.markdown("**Short (front-run):**")
                st.markdown(_pills(fr_us_short, "#3a1a1a"), unsafe_allow_html=True)

        st.markdown("---")
        _section("US SECTOR LEADERSHIP (vs SPY 3M)")
        SECS = {"XLE":"Energy","XLF":"Fin","XLI":"Indust","XLB":"Mat","XLK":"Tech","XLV":"Health","XLY":"Cons.D","XLP":"Cons.S","XLU":"Util","XLRE":"RE","XLC":"Comm"}
        spy3 = ret_n_(prices.get("SPY"),63)
        sec_rows = []
        for tk, name in SECS.items():
            s = prices.get(tk); r3 = ret_n_(s,63); r1 = ret_n_(s,21)
            rel = (r3-spy3) if (math.isfinite(r3) and math.isfinite(spy3)) else float("nan")
            regime_play = "▲ NOW" if any(name.lower() in t.lower() for t in us_longs) else ("▼ SHORT" if any(name.lower() in t.lower() for t in us_shorts) else "")
            sec_rows.append({"Sector":name,"1M":_pct(r1),"3M":_pct(r3),"vs SPY":_pct(rel),"Play":regime_play})
        sec_rows.sort(key=lambda r: float(r["vs SPY"].replace("%","").replace("—","0").replace("+","")) if r["vs SPY"]!="—" else -999, reverse=True)
        st.dataframe(pd.DataFrame(sec_rows), use_container_width=True, hide_index=True, height=340)

        _section("US SPILLOVER CHAIN")
        spill_us = rot.get("spill_us",[]); top_us = rot.get("top_us_bucket","?")
        st.markdown(f"**Leader: {top_us}**")
        US_BUCKETS_LOCAL = snap.get("_us_buckets",{})
        roles = ["Leader","Spillover 2","Breadth follower","Hedge"]
        for i, fam in enumerate(spill_us[:4]):
            r_col = ["#3dbb6c","#e5a020","#888","#e05252"][min(i,3)]
            st.markdown(f'<span style="color:{r_col};font-size:11px;font-weight:600;">{i+1}. {fam}</span> <span style="opacity:.4;font-size:10px;">— {roles[i] if i<len(roles) else ""}</span>', unsafe_allow_html=True)

    # ── FX ────────────────────────────────────────────────────────────────────
    with t_fx:
        fx_longs = tickers.get("fx_longs",[])[:4]
        fx_shorts = tickers.get("fx_shorts",[])[:3]
        fr_fx = tr_data.get("fx_long", fx_longs[:2])[:3]
        fr_fx_signal = tr_data.get("signal","")[:55]

        _now_fr_header("FX", s_quad, fr_fx_signal)
        col_now, col_fr = st.columns(2)
        with col_now:
            st.markdown("**Long:**")
            st.markdown(_pills(fx_longs, "#1a3a2a"), unsafe_allow_html=True)
            if fx_shorts:
                st.markdown("**Short:**")
                st.markdown(_pills(fx_shorts, "#3a1a1a"), unsafe_allow_html=True)
        with col_fr:
            st.markdown("**Long (front-run):**")
            st.markdown(_pills(fr_fx, "#3a2a0a"), unsafe_allow_html=True)

        st.markdown("---")
        FX_PAIRS = ["EURUSD=X","GBPUSD=X","AUDUSD=X","NZDUSD=X","JPY=X","CHF=X","IDR=X","CNH=X","SGD=X","CAD=X"]
        FX_NAMES = {"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","AUDUSD=X":"AUD/USD","NZDUSD=X":"NZD/USD","JPY=X":"USD/JPY","CHF=X":"USD/CHF","IDR=X":"USD/IDR","CNH=X":"USD/CNH","SGD=X":"USD/SGD","CAD=X":"USD/CAD"}
        _section("FX PERFORMANCE")
        fx_rows = []
        for tk in FX_PAIRS:
            s = prices.get(tk); r1 = ret_n_(s,21); r3 = ret_n_(s,63)
            play = "▲ LONG" if tk in fx_longs else ("▼ SHORT" if tk in fx_shorts else "")
            fr_play = "⚡ FR" if tk in fr_fx else ""
            fx_rows.append({"Pair":FX_NAMES.get(tk,tk),"1M":_pct(r1),"3M":_pct(r3),"Now":play,"Front-Run":fr_play})
        st.dataframe(pd.DataFrame(fx_rows), use_container_width=True, hide_index=True, height=360)

    # ── COMMODITIES ───────────────────────────────────────────────────────────
    with t_comm:
        comm_longs = tickers.get("commodity_longs",[])[:5]
        comm_shorts = tickers.get("commodity_shorts",[])[:3]
        fr_comm = tr_data.get("commodity_long", comm_longs[:3])[:4]
        fr_comm_short = tr_data.get("commodity_short",[])[:2]
        fr_comm_signal = tr_data.get("signal","")[:55]

        _now_fr_header("Commodities", s_quad, fr_comm_signal)
        col_now, col_fr = st.columns(2)
        with col_now:
            st.markdown("**Long:**")
            st.markdown(_pills(comm_longs, "#1a3a2a"), unsafe_allow_html=True)
            if comm_shorts:
                st.markdown("**Short:**")
                st.markdown(_pills(comm_shorts, "#3a1a1a"), unsafe_allow_html=True)
        with col_fr:
            st.markdown("**Long (front-run):**")
            st.markdown(_pills(fr_comm, "#3a2a0a"), unsafe_allow_html=True)
            if fr_comm_short:
                st.markdown("**Short (front-run):**")
                st.markdown(_pills(fr_comm_short, "#3a1a1a"), unsafe_allow_html=True)

        st.markdown("---")
        COMM_TICKERS = {"GC=F":"Gold","SI=F":"Silver","HG=F":"Copper","CL=F":"WTI Oil","BZ=F":"Brent","NG=F":"Nat Gas","ZC=F":"Corn","ZW=F":"Wheat","ZS=F":"Soybeans"}
        _section("COMMODITY RETURNS")
        comm_rows = []
        for tk, name in COMM_TICKERS.items():
            s = prices.get(tk); r1 = ret_n_(s,21); r3 = ret_n_(s,63)
            play = "▲" if tk in comm_longs else ("▼" if tk in comm_shorts else "")
            fr_play = "⚡" if tk in fr_comm else ""
            comm_rows.append({"Commodity":name,"Ticker":tk,"1M":_pct(r1),"3M":_pct(r3),"Now":play,"FR":fr_play})
        st.dataframe(pd.DataFrame(comm_rows), use_container_width=True, hide_index=True, height=320)

    # ── CRYPTO ────────────────────────────────────────────────────────────────
    with t_crypto:
        cry_longs = tickers.get("crypto_longs",[])[:5]
        cry_shorts = tickers.get("crypto_shorts",[])[:4]
        fr_cry = cry_longs[:2] if fw in ("now","1-2w") else []

        _now_fr_header("Crypto", s_quad, "Long BTC/ETH when VIX < 18 + regime front-run window active")
        col_now, col_fr = st.columns(2)
        with col_now:
            st.markdown("**Long:**")
            st.markdown(_pills(cry_longs, "#1a3a2a"), unsafe_allow_html=True)
            if cry_shorts:
                st.markdown("**Short:**")
                st.markdown(_pills(cry_shorts, "#3a1a1a"), unsafe_allow_html=True)
        with col_fr:
            if fr_cry:
                st.markdown("**Front-run accumulate:**")
                st.markdown(_pills(fr_cry, "#3a2a0a"), unsafe_allow_html=True)
            else:
                st.markdown(f'<span style="color:#4a5568;font-size:11px;">No front-run crypto play (window: {fw})</span>', unsafe_allow_html=True)

        st.markdown("---")
        CRYPTO_TICKERS = ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","ADA-USD","AVAX-USD","LINK-USD","DOGE-USD"]
        CRYPTO_NAMES = {"BTC-USD":"Bitcoin","ETH-USD":"Ethereum","SOL-USD":"Solana","BNB-USD":"BNB","XRP-USD":"XRP","ADA-USD":"Cardano","AVAX-USD":"Avalanche","LINK-USD":"Chainlink","DOGE-USD":"Dogecoin"}
        _section("CRYPTO RETURNS")
        cry_rows = []
        for tk in CRYPTO_TICKERS:
            s = prices.get(tk); r1 = ret_n_(s,21); r7 = ret_n_(s,7)
            play = "▲" if tk in cry_longs else ("▼" if tk in cry_shorts else "")
            cry_rows.append({"Token":CRYPTO_NAMES.get(tk,tk),"7D":_pct(r7),"1M":_pct(r1),"Play":play})
        st.dataframe(pd.DataFrame(cry_rows), use_container_width=True, hide_index=True, height=300)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — RISK & DIAGNOSTICS (merged Risk + Diag)
# SAFETY: crash, sizing, data quality — not duplicating health
# ══════════════════════════════════════════════════════════════════════════════

def page_risk_diag(snap: dict) -> None:
    cr = snap["crash"]; f = snap["f"]; q = snap["q"]
    opt = snap.get("options_regime",{})

    t1, t2 = st.tabs(["⚠️ Risk & Sizing", "🔬 Diagnostics"])

    with t1:
        sc = cr["crash_score"]; ro = cr["risk_off"]
        col_c = "#e05252" if sc>=0.65 else ("#e5a020" if sc>=0.42 else "#3dbb6c")
        col_r = "#e05252" if ro>=0.65 else ("#e5a020" if ro>=0.42 else "#3dbb6c")

        top_cols = st.columns(4)
        with top_cols[0]: _mc("Crash Meter", f"{sc:.0%}", cr["state"], "good" if sc<0.35 else ("bad" if sc>=0.65 else "warn"))
        with top_cols[1]: _mc("Risk-Off Meter", f"{ro:.0%}", cr.get("div_state","?"), "good" if ro<0.35 else ("bad" if ro>=0.65 else "warn"))
        with top_cols[2]: _mc("Execution Mode", cr["exec_mode"], f"Score: {cr['exec_score']:.0%}")
        with top_cols[3]:
            vix = f.get("vix_last",20.0)
            vix_cap = float(opt.get("vix_sizing_cap",0.85)) if opt else (1.0 if vix<19 else (0.60 if vix<29 else 0.30))
            _mc("Position Cap (VIX)", f"{vix_cap:.0%}", opt.get("vix_bucket","?") if opt else ("Investable" if vix<19 else "Reduced"), "good" if vix_cap>=0.85 else ("bad" if vix_cap<0.40 else "warn"))

        if cr.get("reasons") or cr.get("crash_reasons"):
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                if cr.get("reasons"):
                    _section("RISK-OFF FLAGS")
                    for r in cr["reasons"][:5]: st.markdown(f"- {r}")
            with col_r2:
                if cr.get("crash_reasons"):
                    _section("CRASH-SPECIFIC FLAGS")
                    for r in cr["crash_reasons"][:5]: st.markdown(f"- {r}")

        st.markdown("---")
        _section("POSITION SIZING GUIDE (KELLY + REGIME + VIX)")
        s_quad = q["quad"]
        regime_p = {
            "Q1": {"base":8,"max":15,"stop":7,"rr":"2.5:1","hold":"10-12w"},
            "Q2": {"base":7,"max":12,"stop":8,"rr":"2.2:1","hold":"8-10w"},
            "Q3": {"base":4,"max":8, "stop":6,"rr":"1.8:1","hold":"5-6w"},
            "Q4": {"base":5,"max":10,"stop":9,"rr":"2.0:1","hold":"6-8w"},
        }.get(s_quad, {"base":5,"max":10,"stop":7,"rr":"2:1","hold":"8w"})

        conf = q.get("confidence",0.5)
        fw = snap.get("regime_transition",{}).get("front_run_window","not yet")
        vix_cap = float(opt.get("vix_sizing_cap",0.85)) if opt else 1.0

        adj_base = regime_p["base"] * vix_cap * (0.85 + 0.30*conf) * (0.60 if fw=="now" else 1.0)
        kelly_win = min(0.75, 0.45 + 0.30*conf)
        rr_num = float(regime_p["rr"].split(":")[0])
        kelly_raw = max(0, (kelly_win*rr_num - (1-kelly_win)) / rr_num)
        kelly_adj = kelly_raw * 0.50

        siz_cols = st.columns(4)
        with siz_cols[0]: _mc("Base size", f"{adj_base:.1f}%", f"Regime: {regime_p['base']}% × VIX × conviction")
        with siz_cols[1]: _mc("Max size", f"{int(regime_p['max']*vix_cap)}%", f"VIX cap: {vix_cap:.0%}")
        with siz_cols[2]: _mc("Stop loss", f"{regime_p['stop']}%", "from entry point")
        with siz_cols[3]: _mc("R:R target", regime_p["rr"], f"Kelly ½: {kelly_adj:.0%}")

        # Kelly adjustments table
        adj_rows = []
        for label, mult, effect in [
            (f"Regime {s_quad}", f"{[0.55,0.70,1.0,1.10,1.20].get(3,1.0):.2f}x", "Size multiplier"),
            (f"VIX {opt.get('vix_bucket','?') if opt else '?'}", f"{vix_cap:.0%}", "VIX-based cap"),
            (f"Confidence {conf:.0%}", f"{0.85+0.30*conf:.2f}x", "Conviction weight"),
            (f"Front-run window: {fw}", "0.60x" if fw=="now" else "1.00x", "Pre-confirmation penalty"),
        ]:
            adj_rows.append({"Factor":label,"Multiplier":mult,"Effect":effect})
        st.dataframe(pd.DataFrame(adj_rows), use_container_width=True, hide_index=True, height=180)

        # Entry/Exit guidance
        _section("ENTRY / EXIT GUIDANCE")
        entry_map = {
            "Q1": {"entry":"Scale in 3 tranches over 2-3 weeks as ISM/claims confirm","stop":"Exit if ISM < 49 for 2m or inflation re-accel > 4%","partial":"Trim 30% at +25%; trim more if VIX spikes > 22"},
            "Q2": {"entry":"Enter early on oil bid + ISM > 52; scale in over 2 weeks","stop":"Exit if oil reverses > 12% from peak or ISM breaks 50","partial":"Trim energy at +30% from entry"},
            "Q3": {"entry":"Scale in 5 tranches slowly — high uncertainty, fast moves","stop":"Exit IMMEDIATELY if oil drops > 10% or Fed signals pivot","partial":"Any confirmed de-escalation = trim 50%"},
            "Q4": {"entry":"Wait for pullback 3-5% before entering; scale over 4 weeks","stop":"Exit if growth data surprises to upside or ISM > 51","partial":"TLT at +15% from entry — trim duration"},
        }
        guide = entry_map.get(s_quad,{})
        if guide:
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                _mc("Entry strategy", guide.get("entry","?")[:60])
                _mc("Partial exit trigger", guide.get("partial","?")[:60])
            with col_e2:
                _mc("Full exit trigger", guide.get("stop","?")[:60])
                hold_weeks = regime_p.get("hold","?")
                _mc("Max hold period", str(hold_weeks))

    with t2:
        ps = f.get("_proxy_share",1.0); fl = int(f.get("_fred_loaded",0)); ft = int(f.get("_fred_total",0))
        src_q = f.get("macro_source_quality",0.0)
        cov = f.get("data_coverage",0.0)

        diag_cols = st.columns(4)
        with diag_cols[0]: _mc("FRED coverage", f"{fl}/{ft}", "real macro series", "good" if fl>ft*0.7 else ("bad" if fl<ft*0.3 else "warn"))
        with diag_cols[1]: _mc("Proxy share", f"{ps:.0%}", "% using price fallback", "good" if ps<0.3 else ("bad" if ps>0.6 else "warn"))
        with diag_cols[2]: _mc("Data coverage", f"{cov:.0%}", "composite quality score", "good" if cov>=0.7 else ("bad" if cov<0.4 else "warn"))
        with diag_cols[3]: _mc("Macro source", f"{src_q:.0%}", "overall reliability", "good" if src_q>=0.7 else ("bad" if src_q<0.4 else "warn"))

        # Quad internals
        _section("QUAD INTERNALS")
        quad_data = [
            ("Structural quad", q.get("quad","?")),
            ("Monthly quad", q.get("monthly_quad","?")),
            ("Divergence", q.get("divergence","?")),
            ("Confidence", f"{q.get('confidence',0):.0%}"),
            ("Flip hazard", f"{q.get('flip_hazard',0):.0%}"),
            ("Deepness", f"{q.get('deepness',0):.0%}"),
            ("Duration maturity", f"{q.get('duration_mat',0):.0%}"),
            ("Growth core (adj)", f"{q.get('g_core',0):+.3f}"),
            ("Inflation core", f"{q.get('i_core',0):+.3f}"),
            ("Policy core", f"{q.get('p_core',0):+.3f}"),
            ("Slowdown flags", f"{q.get('slowdown_flags',0):.0%}"),
            ("Regime prior mode", f.get("prior_mode","off")),
        ]
        q_df = pd.DataFrame(quad_data, columns=["Field","Value"])
        st.dataframe(q_df, use_container_width=True, hide_index=True, height=360)

        # Proxy keys used
        proxy_keys = f.get("proxy_used_keys",[])
        if proxy_keys:
            st.warning(f"Proxy fallback active for: {', '.join(proxy_keys[:8])}")
