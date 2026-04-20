"""command_center_page.py  — v11 GODMODE REDESIGN

THE decision cockpit. EVERYTHING a trader needs in ONE screen.
Zero noise. Maximum signal.

Layout:
┌──────────────────────────────────── STATUS BAR ──────────────────────────────────────────┐
│ [Q1 Goldilocks][M:Q2] [⚡FRONT-RUN: NOW] [War/Oil 67%] [VIX 18.2 normal] [VIX cap 100%] │
│ ⚡ TRANSITION ALERT: Q1→Q2 EW 70% — Buy XLE/FCX before ISM > 53 confirms               │
└──────────────────────────────────────────────────────────────────────────────────────────┘

ROW 1 (3 cols):
┌──────────────────┬──────────────────────────┬─────────────────────────────────────────────┐
│   REGIME CARD    │   FRONT-RUN CHECKLIST    │   NARRATIVE INTELLIGENCE                    │
│   Q1 Goldilocks  │   Q4→Q1  ████████░ 75%  │   ⚡ Quantum Photonics (EARLY)              │
│   M: Q2          │   ✅ ISM > 50 (Apr 2)    │   IONQ, QUBT — pre-institutional            │
│   Conf: 67%      │   ✅ Claims down 3w      │   ─────────────────────────                 │
│   Flip: 28%      │   ✅ Growth mom +         │   📈 AI Chip Supply (BUILDING)              │
│                  │   ❌ Fed pivot needed     │   NVDA, AVGO, AMAT                          │
└──────────────────┴──────────────────────────┴─────────────────────────────────────────────┘

ROW 2:
┌─────────────────────────────── MASTER TICKER BOARD ─────────────────────────────────────┐
│  Market    │  NOW (Regime: Q1)              │  FRONT-RUN (⚡ Q1→Q2 transition)           │
│  🇺🇸 US    │  NVDA · META · IWM · JPM      │  XLE · FCX · CAT [enter when ISM > 53]    │
│  🇮🇩 IHSG  │  BBCA · BMRI · ASII            │  ADRO · PTBA [enter when IDR < 16k]       │
│  💱 FX     │  EUR · AUD · IDR               │  AUD · CAD [enter when oil bid > 5%]      │
│  🛢 Commo  │  HG · SI                       │  CL · HG [enter when breakevens > 2.5%]   │
│  🔐 Crypto │  BTC · ETH · SOL               │  ETH · ARB [enter when VIX < 18]          │
└─────────────────────────────────────────────────────────────────────────────────────────┘

ROW 3 (4 cols):
┌─────────────────┬──────────────────┬──────────────────┬────────────────────────────────┐
│  NEWS INTEL     │  IHSG FLOW       │  BROKER FLOW     │  POSITION SIZING               │
│  Relief 77%     │  Net: +Rp 245B   │  🟢 BBCA akkum   │  Base: 7% | Stop: 7%           │
│  War/Oil 45%    │  🟢 Inflow trend │  🔴 BSDE dist.   │  Kelly: 12% | R:R 2.5:1        │
└─────────────────┴──────────────────┴──────────────────┴────────────────────────────────┘
"""
from __future__ import annotations
import streamlit as st
import pandas as pd
from typing import Dict, List, Optional

# ─── colour system ────────────────────────────────────────────────────────────

_QUAD_COLORS = {
    "Q1": {"bg": "#1a3a2a", "border": "#276749", "text": "#68d391", "label": "Goldilocks", "desc": "Growth ↑  Inflation ↓"},
    "Q2": {"bg": "#3a2a0a", "border": "#b7791f", "text": "#f6ad55", "label": "Reflation", "desc": "Growth ↑  Inflation ↑"},
    "Q3": {"bg": "#3a1a0a", "border": "#c05621", "text": "#fc8181", "label": "Stagflation", "desc": "Growth ↓  Inflation ↑"},
    "Q4": {"bg": "#2a1a1a", "border": "#c53030", "text": "#feb2b2", "label": "Deflation Risk", "desc": "Growth ↓  Inflation ↓"},
    "Q?": {"bg": "#1a1a2a", "border": "#4a5568", "text": "#a0aec0", "label": "Unknown", "desc": "Insufficient data"},
}

def _qc(q: str) -> Dict:
    return _QUAD_COLORS.get(q, _QUAD_COLORS["Q?"])

def _pill(t: str, bg: str = "#2b6cb0", fg: str = "#fff", size: int = 11) -> str:
    return f'<span style="background:{bg};color:{fg};padding:2px 7px;border-radius:3px;font-size:{size}px;margin:1px;display:inline-block;font-weight:600;">{t}</span>'

def _pills(tickers: list, bg: str = "#2b6cb0") -> str:
    return " ".join(_pill(t, bg) for t in tickers if t)

def _bar(val: float, color: str = "#276749", width: int = 100, height: int = 6) -> str:
    pct = int(min(1.0, max(0.0, val)) * width)
    return (f'<div style="display:inline-block;width:{width}px;height:{height}px;background:#1a202c;border-radius:3px;vertical-align:middle;">'
            f'<div style="width:{pct}px;height:{height}px;background:{color};border-radius:3px;"></div></div>')

def _pct(v: float) -> str:
    return f"{int(v*100)}%"

# ─── helpers to read from monolith snap dict ──────────────────────────────────

def _q(snap: dict) -> dict:
    return snap.get("q", {})

def _f(snap: dict) -> dict:
    return snap.get("f", {})

def _news(snap: dict) -> dict:
    return snap.get("news_overlay", {})

def _rt(snap: dict) -> dict:
    return snap.get("regime_transition", {})

def _tickers(snap: dict) -> dict:
    return snap.get("regime_tickers", {})

def _narr(snap: dict) -> dict:
    return snap.get("narrative_discovery", {})

def _opt(snap: dict) -> dict:
    return snap.get("options_regime", {})

def _bei(snap: dict) -> dict:
    return snap.get("bei_flow", {})

def _broker(snap: dict) -> dict:
    return snap.get("broker_flow", {})

def _broker_conf(snap: dict) -> dict:
    return snap.get("broker_confirm", {})

# ─── STATUS BAR ───────────────────────────────────────────────────────────────

def _render_status_bar(snap: dict) -> None:
    q = _q(snap); rt = _rt(snap); news = _news(snap)
    tickers = _tickers(snap); opt = _opt(snap)

    quad = q.get("quad", "Q?")
    monthly = q.get("monthly_quad", quad)
    conf = q.get("confidence", 0.0)
    fw = rt.get("front_run_window", "not yet")
    ta = rt.get("transition_alert", "")
    war_h = float(news.get("war_oil", 0.0))
    relief_h = float(news.get("relief", 0.0))
    vix = float(opt.get("vix_spot", 0.0)) if opt else float(_f(snap).get("vix_last", 0.0))
    vix_b = opt.get("vix_bucket", "normal") if opt else "normal"
    vix_cap = float(opt.get("vix_sizing_cap", 0.85)) if opt else 0.85

    qc = _qc(quad)
    qc_m = _qc(monthly)
    fw_cfg = {
        "now":    ("#e53e3e", "⚡ FRONT-RUN: NOW"),
        "1-2w":   ("#dd6b20", "🕐 1-2W"),
        "3-6w":   ("#d69e2e", "🕒 3-6W"),
        "not yet":("#4a5568", "⏸ NO WINDOW"),
    }
    fw_color, fw_label = fw_cfg.get(fw, ("#4a5568", "⏸"))
    vix_color = {"goldilocks":"#48bb78","normal":"#a0aec0","elevated":"#f6ad55","stress":"#fc8181","crisis":"#e53e3e"}.get(vix_b,"#a0aec0")

    dominant_news = "War/Oil" if war_h > relief_h and war_h > 0.4 else ("Relief" if relief_h > 0.5 else "Quiet")
    news_color = "#e53e3e" if dominant_news == "War/Oil" else ("#48bb78" if dominant_news == "Relief" else "#4a5568")

    best_long = (tickers.get("us_longs") or ["—"])[0]
    best_ihsg = (tickers.get("ihsg_buys") or ["—"])[0]
    best_short = (tickers.get("us_shorts") or ["—"])[0]

    # Divergence label
    div = q.get("divergence", "aligned")
    div_color = "#dd6b20" if div == "divergent" else "#4a5568"
    div_label = "⚡ DIVERGEN" if div == "divergent" else "ALIGNED"

    # Status bar — ALWAYS show S and M separately
    st.markdown(
        f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:8px;padding:10px 16px;'
        f'background:#0d1117;border:1px solid #21262d;border-radius:10px;margin-bottom:6px;font-size:12px;">'
        f'<span style="font-size:9px;color:#4a5568;font-weight:700;">S:</span>'
        f'<span style="background:{qc["bg"]};border:1px solid {qc["border"]};color:{qc["text"]};'
        f'padding:3px 10px;border-radius:12px;font-weight:700;">{quad}</span>'
        f'<span style="font-size:9px;color:#4a5568;font-weight:700;">M:</span>'
        f'<span style="background:{qc_m["bg"]};border:1px solid {qc_m["border"]};color:{qc_m["text"]};'
        f'padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;">{monthly}</span>'
        f'<span style="font-size:9px;color:{div_color};font-weight:700;padding:1px 6px;border:1px solid {div_color}44;border-radius:4px;">{div_label}</span>'
        + (f'<span style="color:#4a5568;">|</span>')
        + f'<span style="color:#4a5568;">|</span>'
        f'<span style="color:#a0aec0;">Conf: <b style="color:#e2e8f0;">{_pct(conf)}</b></span>'
        f'<span style="color:#4a5568;">|</span>'
        f'<span style="background:{fw_color}22;border:1px solid {fw_color};color:{fw_color};'
        f'padding:2px 9px;border-radius:8px;font-weight:700;font-size:11px;">{fw_label}</span>'
        f'<span style="color:#4a5568;">|</span>'
        f'<span style="color:{news_color};font-weight:600;">{dominant_news}</span>'
        f'<span style="color:#4a5568;">|</span>'
        f'<span style="color:{vix_color};">VIX <b>{vix:.1f}</b> ({vix_b}) · cap {int(vix_cap*100)}%</span>'
        f'<span style="color:#4a5568;">|</span>'
        f'<span>▲ <b style="color:#68d391;">{best_long}</b> · 🇮🇩 <b style="color:#68d391;">{best_ihsg}</b>'
        f' · ▼ <b style="color:#fc8181;">{best_short}</b></span>'
        + (f'<div style="width:100%;margin-top:4px;padding:4px 6px;background:{fw_color}18;border-radius:6px;'
           f'color:{fw_color};font-size:11px;font-weight:600;">⚡ {ta[:120]}</div>' if ta else "")
        + '</div>',
        unsafe_allow_html=True,
    )

# ─── ROW 1: Regime Card ───────────────────────────────────────────────────────

def _render_regime_card(snap: dict) -> None:
    q = _q(snap)
    quad = q.get("quad", "Q?")
    monthly = q.get("monthly_quad", quad)
    next_q = q.get("next_quad", "?")
    conf = q.get("confidence", 0.0)
    fh = q.get("flip_hazard", 0.3)
    probs = q.get("probs", {})
    g_core = q.get("g_core", 0.0)
    i_core = q.get("i_core", 0.0)
    g_acc = q.get("growth_acc", True)
    i_acc = q.get("infl_acc", False)
    div = q.get("divergence", "aligned")
    deepness = q.get("deepness", 0.5)

    qc = _qc(quad)
    qc_m = _qc(monthly)

    div = q.get("divergence","aligned")
    is_div = div == "divergent"
    qc_m2 = _qc(monthly)
    is_transitional = q.get("transitional", False)
    t_label = q.get("transitional_label", quad)

    # Transitional warning — when confidence < 20% and spread < 8%
    if is_transitional:
        st.markdown(
            f'<div style="background:#e5202018;border:1.5px solid #e52020;border-radius:6px;padding:5px 10px;margin-bottom:6px;">' +
            f'<span style="color:#e52020;font-weight:700;font-size:11px;">⚠️ TRANSITIONAL — {t_label}</span> ' +
            f'<span style="font-size:10px;color:#718096;">Confidence {conf:.0%} terlalu rendah. Regime belum confirmed. Trade monthly signal saja, jangan buka structural positions.</span>' +
            f'</div>',
            unsafe_allow_html=True,
        )

    # Always show both S (structural, big-picture) and M (monthly, current conditions)
    st.markdown(
        f'<div style="background:{qc["bg"]};border-left:4px solid {qc["border"]};'
        f'border-radius:8px;padding:12px 16px;margin-bottom:8px;">'
        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">'
        f'<div>'
        f'<div style="font-size:10px;font-weight:700;color:#4a5568;letter-spacing:.1em;">STRUCTURAL (3m+ horizon)</div>'
        f'<div style="font-size:22px;font-weight:800;color:{qc["text"]};">{quad} — {qc["label"]}</div>'
        f'<div style="color:#718096;font-size:11px;">{qc["desc"]}</div>'
        f'</div>'
        f'<div style="width:1px;background:#21262d;align-self:stretch;margin:0 4px;"></div>'
        f'<div>'
        f'<div style="font-size:10px;font-weight:700;color:#4a5568;letter-spacing:.1em;">MONTHLY (current)</div>'
        f'<div style="font-size:22px;font-weight:800;color:{qc_m2["text"]};">{monthly}</div>'
        f'<div style="font-size:11px;color:{"#dd6b20" if is_div else "#4a5568"};">'
        f'{"⚡ Divergent — monthly leading" if is_div else "Aligned with structural"}'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        color_conf = "#48bb78" if conf >= 0.55 else ("#f6ad55" if conf >= 0.35 else "#fc8181")
        st.markdown(f'<div style="font-size:11px;color:#718096;">Confidence</div>'
                    f'<div style="font-size:20px;font-weight:700;color:{color_conf};">{_pct(conf)}</div>',
                    unsafe_allow_html=True)
    with c2:
        fh_color = "#fc8181" if fh >= 0.55 else ("#f6ad55" if fh >= 0.35 else "#48bb78")
        st.markdown(f'<div style="font-size:11px;color:#718096;">Flip hazard</div>'
                    f'<div style="font-size:20px;font-weight:700;color:{fh_color};">{_pct(fh)}</div>',
                    unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div style="font-size:11px;color:#718096;">Next likely</div>'
                    f'<div style="font-size:20px;font-weight:700;color:{_qc(next_q)["text"]};">{next_q}</div>',
                    unsafe_allow_html=True)

    # Divergence banner — only when divergent (card already shows labels)
    if div == "divergent":
        m_meta = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation Risk"}.get(monthly,monthly)
        s_meta = {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation Risk"}.get(quad,quad)
        st.markdown(
            f'<div style="background:#dd6b2018;border:1px solid #dd6b20;border-radius:6px;'
            f'padding:5px 10px;margin:4px 0 8px;font-size:11px;">'
            f'⚡ <b>Divergence active:</b> Structural <b style="color:{qc["text"]};">{quad} {s_meta}</b> '
            f'vs Monthly <b style="color:{qc_m["text"]};">{monthly} {m_meta}</b>. '
            f'Monthly = near-term trade, Structural = 3m+ positioning.</div>',
            unsafe_allow_html=True,
        )

    # Probability bars
    if probs:
        st.markdown('<div style="margin-top:6px;">', unsafe_allow_html=True)
        for qq, p in sorted(probs.items(), key=lambda x: -x[1]):
            c = _qc(qq)
            pct_w = int(p * 100)
            active = qq == quad
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:6px;margin:3px 0;">'
                f'<span style="width:22px;font-size:11px;font-weight:{"800" if active else "500"};color:{c["text"]};">{qq}</span>'
                f'<div style="flex:1;background:#1a202c;height:{"9px" if active else "6px"};border-radius:3px;border:{"1px solid " + c["border"] if active else "none"};">'
                f'<div style="width:{pct_w}%;height:100%;background:{c["border"]};border-radius:3px;"></div></div>'
                f'<span style="font-size:11px;color:{"#e2e8f0" if active else "#718096"};width:32px;text-align:right;font-weight:{"700" if active else "400"};">{pct_w}%</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # Growth/inflation axes
    g_arrow = "▲" if g_acc else "▼"
    i_arrow = "▲" if i_acc else "▼"
    g_clr = "#48bb78" if g_acc else "#fc8181"
    i_clr = "#fc8181" if i_acc else "#48bb78"
    st.markdown(
        f'<div style="margin-top:8px;display:flex;gap:12px;">'
        f'<span style="color:{g_clr};font-size:12px;">{g_arrow} Growth: {g_core:+.3f}</span>'
        f'<span style="color:{i_clr};font-size:12px;">{i_arrow} Inflation: {i_core:+.3f}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ─── ROW 1: Front-Run Checklist ───────────────────────────────────────────────

def _render_frontrun_checklist(snap: dict) -> None:
    rt = _rt(snap)
    fw = rt.get("front_run_window", "not yet")
    rationale = rt.get("front_run_rationale", "")
    paths = rt.get("transition_paths", [])
    ew_signals = rt.get("early_warning_signals", {})
    leading = float(rt.get("leading_composite", 0.0))

    fw_cfg = {
        "now":    ("#e53e3e", "⚡ AKTIF SEKARANG"),
        "1-2w":   ("#dd6b20", "🕐 1–2 MINGGU"),
        "3-6w":   ("#d69e2e", "🕒 3–6 MINGGU"),
        "not yet":("#4a5568", "⏸ BELUM AKTIF"),
    }
    fw_color, fw_label_text = fw_cfg.get(fw, ("#4a5568", "⏸ BELUM"))

    st.markdown(
        f'<div style="background:{fw_color}18;border:1.5px solid {fw_color};border-radius:8px;padding:10px 12px;margin-bottom:8px;">'
        f'<span style="color:{fw_color};font-size:13px;font-weight:800;">FRONT-RUN WINDOW: {fw_label_text}</span><br>'
        f'<span style="color:#a0aec0;font-size:11px;">{rationale[:110] if rationale else "No active transition"}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Leading indicator composite bar
    lead_pct = int((leading + 1.0) / 2.0 * 100)
    lead_color = "#48bb78" if leading > 0.10 else ("#fc8181" if leading < -0.10 else "#718096")
    lead_label = "📈 Improving" if leading > 0.10 else ("📉 Deteriorating" if leading < -0.10 else "⚪ Neutral")
    st.markdown(
        f'<div style="margin-bottom:6px;">'
        f'<div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px;">'
        f'<span style="color:#718096;">Leading Indicator</span><span style="color:{lead_color};">{lead_label}</span></div>'
        f'{_bar(lead_pct/100, lead_color, 100, 7)}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Top transition path with checklist
    if paths:
        p = paths[0]
        from_q = p.get("from_quad", "?"); to_q = p.get("to_quad", "?")
        ew_score = float(p.get("early_warning_score", 0))
        prob = float(p.get("probability", 0))
        tw = int(p.get("timeframe_weeks", 0))
        confirms = p.get("confirmation_needed", [])

        # Progress bar for EW score
        ew_pct = int(ew_score * 100)
        ew_color = "#e53e3e" if ew_score >= 0.70 else ("#dd6b20" if ew_score >= 0.50 else "#d69e2e")

        st.markdown(
            f'<div style="border:1px solid #21262d;border-radius:6px;padding:8px 10px;">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
            f'<span style="font-size:12px;font-weight:700;color:#e2e8f0;">{from_q} → {to_q}</span>'
            f'<span style="font-size:11px;color:#718096;">{int(prob*100)}% prob · ~{tw}w</span>'
            f'</div>'
            f'<div style="margin-bottom:6px;">'
            f'<div style="display:flex;justify-content:space-between;font-size:10px;margin-bottom:2px;">'
            f'<span style="color:#718096;">Early warnings firing</span><span style="color:{ew_color};font-weight:700;">{ew_pct}%</span></div>'
            f'<div style="background:#1a202c;height:8px;border-radius:4px;">'
            f'<div style="width:{ew_pct}%;height:8px;background:{ew_color};border-radius:4px;"></div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Named signal checklist
        if ew_signals:
            firing_sigs = {k: v for k, v in ew_signals.items() if v >= 0.5}
            pending_sigs = {k: v for k, v in ew_signals.items() if v < 0.5}
            for sig, _ in list(firing_sigs.items())[:4]:
                label = sig.replace("_", " ").title()
                st.markdown(f'<div style="font-size:11px;color:#48bb78;margin:1px 0;">✅ {label}</div>', unsafe_allow_html=True)
            for sig, _ in list(pending_sigs.items())[:3]:
                label = sig.replace("_", " ").title()
                st.markdown(f'<div style="font-size:11px;color:#4a5568;margin:1px 0;">❌ {label}</div>', unsafe_allow_html=True)

        # What's still needed
        if confirms:
            st.markdown(f'<div style="margin-top:5px;font-size:10px;color:#718096;font-weight:600;">NEEDS:</div>', unsafe_allow_html=True)
            for c in confirms[:2]:
                st.markdown(f'<div style="font-size:10px;color:#a0aec0;margin:1px 0;">→ {c[:55]}</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.caption("No active transition detected. Regime stable.")

# ─── ROW 1: Narrative Intelligence ───────────────────────────────────────────

def _render_narrative_block(snap: dict) -> None:
    narr = _narr(snap)
    actives = narr.get("active_narratives", [])
    early = narr.get("early_stage_alerts", [])

    if not actives:
        st.markdown(
            '<div style="background:#1a1a2a;border:1px solid #4a5568;border-radius:8px;padding:14px;text-align:center;">'
            '<span style="color:#4a5568;font-size:12px;">No active narratives detected<br>'
            '<span style="font-size:10px;">Set ANTHROPIC_API_KEY to enable Claude narrative analysis</span></span>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    for narr_item in actives[:3]:
        stage = narr_item.get("stage", "")
        conv = float(narr_item.get("regime_adjusted_conviction", 0))
        pump = float(narr_item.get("pump_risk", 0.5))
        name = str(narr_item.get("name", ""))[:40]
        action = str(narr_item.get("action_summary", ""))[:100]
        primary = narr_item.get("primary_beneficiaries", [])[:4]
        insight = str(narr_item.get("claude_insight", ""))

        stage_cfg = {
            "early":     ("#e53e3e", "⚡ EARLY"),
            "building":  ("#dd6b20", "📈 BUILDING"),
            "mature":    ("#276749", "✅ MATURE"),
            "exhausted": ("#4a5568", "💀 EXHAUSTED"),
        }
        s_color, s_label = stage_cfg.get(stage, ("#4a5568", stage.upper()))
        pump_label = "🟢" if pump <= 0.25 else ("🟡" if pump <= 0.50 else "🔴")

        st.markdown(
            f'<div style="border-left:3px solid {s_color};padding:8px 10px;'
            f'background:#0d1117;border-radius:0 6px 6px 0;margin-bottom:6px;">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
            f'<span style="color:{s_color};font-size:10px;font-weight:700;">{s_label}</span>'
            f'<span style="font-size:10px;color:#718096;">{pump_label} {int(conv*100)}% conv</span>'
            f'</div>'
            f'<div style="font-size:12px;font-weight:700;color:#e2e8f0;margin-bottom:3px;">{name}</div>'
            f'<div style="font-size:11px;color:#a0aec0;margin-bottom:4px;">{action}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if primary:
            st.markdown(_pills(primary, "#276749"), unsafe_allow_html=True)
        if insight and "pending" not in insight:
            st.caption(f"🤖 {insight[:80]}")

# ─── ROW 2: Master Ticker Board ───────────────────────────────────────────────

def _render_master_ticker_board(snap: dict) -> None:
    q = _q(snap)
    tickers = _tickers(snap)
    rt = _rt(snap)

    quad = q.get("quad", "Q?")
    monthly = q.get("monthly_quad", quad)
    fw = rt.get("front_run_window", "not yet")
    paths = rt.get("transition_paths", [])

    fr_picks = tickers.get("front_run_picks", [])
    fr_tickers = {p.get("ticker", "") for p in fr_picks if isinstance(p, dict)} if fr_picks else set()

    # Top transition for front-run label
    if paths:
        p0 = paths[0]
        tr_label = f"→{p0.get('to_quad','?')} ({int(p0.get('early_warning_score',0)*100)}% EW)"
        tr_signals = p0.get("confirmation_needed", [])
        tr_signal = tr_signals[0][:50] if tr_signals else ""
    else:
        tr_label = "No active transition"
        tr_signal = ""

    # Front-run alert strip
    if fw in ("now", "1-2w") and fr_picks:
        fr_str = " · ".join([p.get("ticker", "") for p in fr_picks[:5] if isinstance(p, dict) and p.get("ticker")])
        fw_color = "#e53e3e" if fw == "now" else "#dd6b20"
        st.markdown(
            f'<div style="background:{fw_color}18;border:1px solid {fw_color};border-radius:6px;'
            f'padding:6px 12px;margin-bottom:6px;font-size:12px;display:flex;gap:8px;align-items:center;">'
            f'<span style="color:{fw_color};font-weight:700;">⚡ FRONT-RUN {tr_label}:</span>'
            f'<span style="color:#e2e8f0;">{fr_str}</span>'
            + (f'<span style="color:#718096;font-size:10px;margin-left:auto;">Entry: {tr_signal}</span>' if tr_signal else "")
            + '</div>',
            unsafe_allow_html=True,
        )

    # Table header
    st.markdown(
        '<div style="display:grid;grid-template-columns:120px 1fr 1fr;gap:0;border:1px solid #21262d;border-radius:8px;overflow:hidden;">'
        '<div style="padding:8px 10px;background:#161b22;font-size:11px;font-weight:700;color:#718096;">Market</div>'
        f'<div style="padding:8px 10px;background:#0d2818;font-size:11px;font-weight:700;color:#48bb78;">▲ NOW · {quad}</div>'
        f'<div style="padding:8px 10px;background:#1a1a0d;font-size:11px;font-weight:700;color:#f6ad55;">⚡ FRONT-RUN {tr_label}</div>',
        unsafe_allow_html=True,
    )

    # Get front-run specific tickers per market from transition path
    tr_from = paths[0].get("from_quad", quad) if paths else quad
    tr_to = paths[0].get("to_quad", "?") if paths else "?"

    # Import transition front-run registry
    try:
        from config.regime_ticker_registry import TRANSITION_FRONT_RUN, US_TICKERS, IHSG_TICKERS, FX_TICKERS, COMMODITY_TICKERS, CRYPTO_TICKERS
        tr_key = f"{tr_from}→{tr_to}"
        tr_data = TRANSITION_FRONT_RUN.get(tr_key, {})
    except Exception:
        tr_data = {}

    markets = [
        ("🇺🇸 US", tickers.get("us_longs", [])[:5], tickers.get("us_shorts", [])[:3],
         tr_data.get("us_long", tickers.get("us_longs", [])[:3]),
         tr_data.get("us_short", [])),
        ("🇮🇩 IHSG", tickers.get("ihsg_buys", [])[:5], [],
         tr_data.get("ihsg_buy", tickers.get("ihsg_buys", [])[:3]), []),
        ("💱 FX", tickers.get("fx_longs", [])[:4], tickers.get("fx_shorts", [])[:3],
         tr_data.get("fx_long", tickers.get("fx_longs", [])[:2]), []),
        ("🛢 Commodities", tickers.get("commodity_longs", [])[:4], tickers.get("commodity_shorts", [])[:3],
         tr_data.get("commodity_long", tickers.get("commodity_longs", [])[:2]),
         tr_data.get("commodity_short", [])),
        ("🔐 Crypto", tickers.get("crypto_longs", [])[:4], tickers.get("crypto_shorts", [])[:3],
         tickers.get("crypto_longs", [])[:2], []),
    ]

    for i, (market, longs, shorts, fr_l, fr_s) in enumerate(markets):
        bg = "#0d1117" if i % 2 == 0 else "#111823"
        border_top = "border-top:1px solid #21262d;"

        # NOW column: longs (green) + shorts (red)
        now_html = _pills(longs, "#1a3a2a") + ("&nbsp;·&nbsp;" + _pills(shorts, "#3a1a1a") if shorts else "")

        # FRONT-RUN column: different tickers with entry signal
        fr_signal = tr_data.get("signal", "")[:55] if tr_data else ""
        fr_html = _pills(fr_l, "#3a2a0a")
        if fr_s:
            fr_html += "&nbsp;short:&nbsp;" + _pills(fr_s, "#3a1a1a")
        if fr_signal and i == 0:
            fr_html += f'<br><span style="font-size:9px;color:#718096;margin-top:2px;display:block;">{fr_signal}</span>'

        _now = now_html if now_html else '<span style="color:#4a5568;">—</span>'
        _fr  = fr_html  if fr_html  else '<span style="color:#4a5568;">—</span>'
        st.markdown(
            f'<div style="display:grid;grid-template-columns:120px 1fr 1fr;gap:0;{border_top}">'
            f'<div style="padding:7px 10px;background:{bg};font-size:11px;font-weight:600;color:#a0aec0;">{market}</div>'
            f'<div style="padding:7px 10px;background:{bg};font-size:11px;">{_now}</div>'
            f'<div style="padding:7px 10px;background:{bg};font-size:11px;">{_fr}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

# ─── ROW 3: News / BEI / Broker / Sizing ─────────────────────────────────────

def _render_news_compact(snap: dict) -> None:
    news = _news(snap)
    state = str(news.get("state", "quiet"))
    label = str(news.get("label", "Quiet"))
    war_h = float(news.get("war_oil", 0.0))
    pol_h = float(news.get("policy_pressure", 0.0))
    relief_h = float(news.get("relief", 0.0))
    events = news.get("events", [])

    state_color = "#e53e3e" if "War" in label else ("#48bb78" if "Relief" in label else "#718096")
    clean_label = label.replace("⚔️ Event-Lite: ", "").replace("🕊️ Event-Lite: ", "").replace("📋 Event-Lite: ", "").replace("😶 Event-Lite: ", "")

    st.markdown(f'<div style="font-size:12px;font-weight:700;color:{state_color};margin-bottom:6px;">{clean_label[:45]}</div>', unsafe_allow_html=True)

    for lbl, val, color in [("War/Oil", war_h, "#e53e3e"), ("Policy", pol_h, "#dd6b20"), ("Relief", relief_h, "#48bb78")]:
        pct = int(val * 100)
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:6px;margin:2px 0;">'
            f'<span style="font-size:10px;width:44px;color:#718096;">{lbl}</span>'
            f'<div style="flex:1;background:#1a202c;height:5px;border-radius:3px;">'
            f'<div style="width:{pct}%;height:5px;background:{color};border-radius:3px;"></div></div>'
            f'<span style="font-size:10px;width:26px;text-align:right;color:{color};">{pct}%</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if events:
        top_ev = events[0]
        impact = top_ev.get("impact", "watch")
        ev_color = "#e53e3e" if impact == "high" else ("#f6ad55" if impact == "medium" else "#718096")
        st.markdown(
            f'<div style="margin-top:6px;padding:5px 8px;background:#1a1a2a;border-radius:5px;">'
            f'<span style="font-size:10px;color:{ev_color};font-weight:700;">{impact.upper()}</span>'
            f'<span style="font-size:10px;color:#a0aec0;"> {top_ev.get("label","")[:35]} · {top_ev.get("countdown","")}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_bei_flow(snap: dict) -> None:
    bei = _bei(snap)
    if not bei or not bei.get("available"):
        st.markdown('<div style="color:#4a5568;font-size:12px;">IHSG Foreign Flow<br><span style="font-size:10px;">Data N/A — IDX API or EIDO proxy unavailable</span></div>', unsafe_allow_html=True)
        return

    net = float(bei.get("net_rp_billion", 0.0))
    flow_state = bei.get("flow_state", {})
    trend = str(flow_state.get("trend", "neutral"))
    label = str(flow_state.get("label", "⚪ Neutral"))
    net_5d = float(flow_state.get("net_5d_rp_billion", 0.0))
    implication = str(flow_state.get("ihsg_implication", ""))
    source = str(bei.get("source", ""))

    trend_color = "#48bb78" if "inflow" in trend else ("#fc8181" if "outflow" in trend else "#718096")
    net_sign = "+" if net >= 0 else ""

    st.markdown(
        f'<div style="margin-bottom:4px;">'
        f'<span style="font-size:14px;font-weight:700;color:{trend_color};">{label}</span>'
        f'&nbsp;<span style="font-size:10px;color:#718096;">({source.replace("_"," ")})</span>'
        f'</div>'
        f'<div style="font-size:18px;font-weight:700;color:{trend_color};">Rp {net_sign}{net:.0f}B</div>'
        f'<div style="font-size:11px;color:#718096;">5D net: Rp {net_5d:+.0f}B</div>',
        unsafe_allow_html=True,
    )
    if implication:
        st.caption(implication[:70])


def _render_broker_flow(snap: dict) -> None:
    broker = _broker(snap)
    conf = _broker_conf(snap)

    if not broker.get("connected"):
        note = broker.get("note", "AFL not connected")
        st.markdown(
            f'<div style="background:#1a1a2a;border:1px dashed #4a5568;border-radius:6px;padding:10px;">'
            f'<div style="font-size:11px;font-weight:700;color:#4a5568;">Broker Flow (AFL Bridge)</div>'
            f'<div style="font-size:10px;color:#4a5568;margin-top:4px;">{note}<br>'
            f'Write .cache/broker_flow.json from AFL to connect</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    market_action = broker.get("market_action", "neutral")
    buys = broker.get("buys", [])[:4]
    sells = broker.get("sells", [])[:4]
    hi_conv = broker.get("high_conviction", [])
    sig_count = broker.get("signal_count", 0)

    action_cfg = {
        "accumulation": ("#48bb78", "🟢 Akumulasi"),
        "distribution":  ("#e53e3e", "🔴 Distribusi"),
        "neutral":       ("#718096", "⚪ Neutral"),
        "mixed":         ("#f6ad55", "🟡 Mixed"),
    }
    act_color, act_label = action_cfg.get(market_action, ("#718096", market_action.title()))

    st.markdown(f'<div style="font-size:13px;font-weight:700;color:{act_color};">{act_label}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:10px;color:#718096;">{sig_count} signals</div>', unsafe_allow_html=True)

    if buys:
        st.markdown(_pills(buys, "#1a3a2a"), unsafe_allow_html=True)
    if sells:
        st.markdown("short: " + _pills(sells, "#3a1a1a"), unsafe_allow_html=True)

    # Broker × macro confirmation
    if conf:
        status = conf.get("status", "unavailable")
        detail = conf.get("detail", "")
        conf_cfg = {
            "double_conviction": ("#48bb78", "✅✅ DOUBLE CONVICTION"),
            "contradiction":     ("#e53e3e", "⚠️ KONTRADIKSI"),
            "partial_confirm":   ("#f6ad55", "✓ Partial"),
            "no_overlap":        ("#718096", "— No overlap"),
        }
        cc_color, cc_label = conf_cfg.get(status, ("#718096", status))
        st.markdown(
            f'<div style="margin-top:5px;padding:4px 7px;background:#1a202c;border-radius:4px;">'
            f'<span style="color:{cc_color};font-size:10px;font-weight:700;">{cc_label}</span><br>'
            f'<span style="color:#718096;font-size:10px;">{detail[:55]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_sizing_compact(snap: dict) -> None:
    q = _q(snap); opt = _opt(snap)
    quad = q.get("quad", "Q?")
    vix_b = opt.get("vix_bucket", "normal") if opt else "normal"
    vix_cap = float(opt.get("vix_sizing_cap", 0.85)) if opt else 0.85
    conf = q.get("confidence", 0.5)
    rt = _rt(snap)
    fw = rt.get("front_run_window", "not yet")

    # Regime base params
    regime_p = {
        "Q1": {"base": 8, "max": 15, "stop": 7, "rr": "2.5:1"},
        "Q2": {"base": 7, "max": 12, "stop": 8, "rr": "2.2:1"},
        "Q3": {"base": 4, "max": 8,  "stop": 6, "rr": "1.8:1"},
        "Q4": {"base": 5, "max": 10, "stop": 9, "rr": "2.0:1"},
    }.get(quad, {"base": 5, "max": 10, "stop": 7, "rr": "2:1"})

    # Apply adjustments
    adj_base = regime_p["base"] * vix_cap
    adj_base = adj_base * (0.60 if fw == "now" else 1.0)  # Front-run = smaller initial
    adj_base = adj_base * (0.85 + 0.30 * conf)

    kelly_win = min(0.75, 0.45 + 0.30 * conf)
    kelly_raw = (kelly_win * float(regime_p["rr"].split(":")[0]) - (1-kelly_win)) / float(regime_p["rr"].split(":")[0])
    kelly_adj = max(0, kelly_raw) * 0.50

    vix_color = {"goldilocks":"#48bb78","normal":"#a0aec0","elevated":"#f6ad55","stress":"#fc8181","crisis":"#e53e3e"}.get(vix_b,"#a0aec0")
    fr_note = "⚡ Front-run: 60% of base" if fw == "now" else ""

    metrics = [
        ("Base size", f"{adj_base:.1f}%"),
        ("Max size", f"{int(regime_p['max'] * vix_cap)}%"),
        ("Stop loss", f"{regime_p['stop']}%"),
        ("R:R target", regime_p["rr"]),
        ("Kelly ½", f"{kelly_adj:.0%}"),
        (f"VIX ({vix_b})", f"{int(vix_cap*100)}% cap"),
    ]
    for label, val in metrics:
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid #21262d;">'
            f'<span style="font-size:11px;color:#718096;">{label}</span>'
            f'<span style="font-size:12px;font-weight:700;color:#e2e8f0;">{val}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Crash meter inline
    cr = snap.get("crash", {})
    crash_sc = float(cr.get("crash_score", 0))
    crash_state = cr.get("state", "🟢 CALM")
    cnn_fg = cr.get("cnn_fear_greed", None)
    iwm_ath = float(cr.get("iwm_ath_distance", 0))
    crash_col = "#e53e3e" if crash_sc >= 0.65 else ("#e5a020" if crash_sc >= 0.42 else "#3dbb6c")

    st.markdown(
        f'<div style="margin-top:6px;padding:5px 8px;background:#1a202c;border:1px solid #21262d;border-radius:6px;">' +
        f'<div style="display:flex;justify-content:space-between;align-items:center;">' +
        f'<span style="font-size:10px;font-weight:700;color:#718096;">CRASH METER</span>' +
        f'<span style="font-size:12px;font-weight:700;color:{crash_col};">{crash_state} {crash_sc:.0%}</span>' +
        f'</div>' +
        f'<div style="background:#1a202c;height:5px;border-radius:3px;margin:3px 0;">' +
        f'<div style="width:{int(crash_sc*100)}%;height:5px;background:{crash_col};border-radius:3px;"></div>' +
        f'</div>' +
        (f'<div style="display:flex;gap:8px;font-size:10px;">' +
         f'<span style="color:#718096;">CNN F&G: <b style="color:{("#e05252" if cnn_fg<0.25 else "#f6ad55" if cnn_fg>0.75 else "#48bb78")};">{int(cnn_fg*100)}</b></span>' +
         f'<span style="color:#718096;">IWM ATH: <b style="color:{("#e05252" if iwm_ath>0.4 else "#f6ad55" if iwm_ath>0.2 else "#48bb78")};"> -{int(iwm_ath*100)}%</b></span>' +
         f'</div>' if cnn_fg is not None else
         f'<div style="font-size:10px;color:#718096;">IWM ATH dist: <b style="color:{("#e05252" if iwm_ath>0.4 else "#f6ad55" if iwm_ath>0.2 else "#48bb78")};"> -{int(iwm_ath*100)}%</b></div>') +
        f'</div>',
        unsafe_allow_html=True,
    )

    if vix_b in ("stress", "crisis"):
        st.markdown('<div style="background:#c5303022;border:1px solid #c53030;border-radius:4px;padding:4px 8px;margin-top:4px;font-size:10px;color:#fc8181;font-weight:700;">🚨 HIGH VIX — DEFENSIVE ONLY</div>', unsafe_allow_html=True)
    if fr_note:
        st.markdown(f'<div style="background:#dd6b2022;border-radius:4px;padding:4px 8px;margin-top:4px;font-size:10px;color:#dd6b20;">{fr_note}</div>', unsafe_allow_html=True)

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def render_command_center(snap: dict) -> None:
    """Main entry point. snap = the full monolith load_all() dict."""
    st.markdown(
        '<div style="margin-bottom:12px;">'
        '<span style="font-size:22px;font-weight:800;color:#e2e8f0;">⚡ Command Center</span>&nbsp;'
        '<span style="font-size:12px;color:#4a5568;">Decision cockpit — everything to trade, nothing extra</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # STATUS BAR
    _render_status_bar(snap)

    # ROW 1
    col1, col2, col3 = st.columns([1.1, 1.1, 1.0], gap="small")
    with col1:
        st.markdown('<div style="font-size:11px;font-weight:700;color:#718096;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px;">REGIME</div>', unsafe_allow_html=True)
        _render_regime_card(snap)
    with col2:
        st.markdown('<div style="font-size:11px;font-weight:700;color:#718096;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px;">FRONT-RUN CHECKLIST</div>', unsafe_allow_html=True)
        _render_frontrun_checklist(snap)
    with col3:
        st.markdown('<div style="font-size:11px;font-weight:700;color:#718096;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px;">NARRATIVE PLAYS</div>', unsafe_allow_html=True)
        _render_narrative_block(snap)

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # ROW 2
    st.markdown('<div style="font-size:11px;font-weight:700;color:#718096;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px;">MASTER TICKER BOARD — NOW vs FRONT-RUN</div>', unsafe_allow_html=True)
    _render_master_ticker_board(snap)

    st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

    # ROW 3
    c1, c2, c3, c4 = st.columns([1.2, 1.0, 1.0, 1.0], gap="small")
    with c1:
        st.markdown('<div style="font-size:11px;font-weight:700;color:#718096;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px;">NEWS CATALYST</div>', unsafe_allow_html=True)
        _render_news_compact(snap)
    with c2:
        st.markdown('<div style="font-size:11px;font-weight:700;color:#718096;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px;">IHSG FOREIGN FLOW</div>', unsafe_allow_html=True)
        _render_bei_flow(snap)
    with c3:
        st.markdown('<div style="font-size:11px;font-weight:700;color:#718096;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px;">BROKER FLOW (AFL)</div>', unsafe_allow_html=True)
        _render_broker_flow(snap)
    with c4:
        st.markdown('<div style="font-size:11px;font-weight:700;color:#718096;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px;">POSITION SIZING</div>', unsafe_allow_html=True)
        _render_sizing_compact(snap)
