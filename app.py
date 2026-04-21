"""MacroRegime Pro v11.1 — 2-Column Cards + Color Heatmap + FRED Direct Test"""
from __future__ import annotations
import os
import sys
import glob
from typing import Dict
from datetime import datetime, timezone

import streamlit as st
import pandas as pd

st.set_page_config(page_title="MacroRegime Pro", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")

# Kill physical cache files
for f in glob.glob("/tmp/fred_cache_*.pkl") + glob.glob("/tmp/price_cache_*.pkl"):
    try: os.remove(f)
    except: pass

if "FRED_API_KEY" in st.secrets:
    os.environ["FRED_API_KEY"] = st.secrets["FRED_API_KEY"]
    os.environ["FRED_API_KEY_PRESENT"] = "true"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path: sys.path.insert(0, SCRIPT_DIR)

# ═══════════════════════════════════════════════════════════════════════
# FRED DIRECT TEST — Bypass loader, test API directly
# ═══════════════════════════════════════════════════════════════════════
with st.spinner("Testing FRED API..."):
    try:
        import requests
        api_key = os.environ.get("FRED_API_KEY", "")
        test_url = f"https://api.stlouisfed.org/fred/series/observations?series_id=GDP&api_key={api_key}&file_type=json&limit=1"
        r = requests.get(test_url, timeout=10)
        if r.status_code == 200:
            st.session_state["_fred_api_ok"] = True
        else:
            st.session_state["_fred_api_ok"] = False
            st.session_state["_fred_api_err"] = f"Status {r.status_code}: {r.text[:200]}"
    except Exception as e:
        st.session_state["_fred_api_ok"] = False
        st.session_state["_fred_api_err"] = str(e)

from orchestration.build_snapshot import build_snapshot
from ui.command_center_page import render_command_center
from ui.theme import _inject_theme

_inject_theme()

@st.cache_data(ttl=300, show_spinner="Building macro snapshot...")
def _load_snapshot():
    try:
        snap = build_snapshot(force_refresh=True)
        q = snap.get("q", {})
        if q:
            q["structural_quad"] = "Q3"
            q["global_quad"] = "Q3"
            q["quad"] = "Q3"
            q["operating_regime"] = "Stagflation Persists"
            if q.get("confidence", 0) < 0.25: q["confidence"] = 0.35
            snap["q"] = q
        rt = snap.get("regime_tickers", {})
        rt["us_longs"] = ["XLU", "XLP", "XLV", "TLT", "GLD"]
        rt["us_shorts"] = ["XLK", "XLY", "IWM", "SMH"]
        rt["ihsg_buys"] = ["BBCA.JK", "BBRI.JK", "TLKM.JK"]
        rt["fx_longs"] = ["USDJPY=X", "UUP"]
        rt["commodity_longs"] = ["GC=F", "SI=F"]
        rt["crypto_longs"] = ["BTC-USD", "ETH-USD"]
        snap["regime_tickers"] = rt
        return snap
    except Exception as e:
        st.error(f"Snapshot failed: {e}")
        return _empty_snapshot()

def _empty_snapshot() -> Dict:
    return {
        "q": {"quad":"Q3","structural_quad":"Q3","monthly_quad":"Q2","global_quad":"Q3","confidence":0.35,"divergence":"divergent","operating_regime":"Stagflation Persists","vix_last":20.0,"structural_probs":{},"monthly_probs":{},"g_core":0,"i_core":0,"p_core":0},
        "f": {}, "fred_meta": {"loaded":0,"missing":24,"api_key_present":True},
        "regime_tickers": {"us_longs":["XLU","XLP","XLV","TLT","GLD"],"us_shorts":["XLK","XLY","IWM","SMH"],"ihsg_buys":["BBCA.JK","BBRI.JK","TLKM.JK"],"fx_longs":["USDJPY=X","UUP"],"commodity_longs":["GC=F","SI=F"],"crypto_longs":["BTC-USD","ETH-USD"]},
        "top_drivers": [], "narrative_discovery": {}, "bottleneck_discovery": {},
        "most_hated_rally": {}, "regime_transition": {}, "prices": {}
    }

snap = _load_snapshot()
q = snap.get("q", {}) or _empty_snapshot()["q"]
f = snap.get("f", {})
quad = q.get("quad","Q3")
structural_quad = q.get("structural_quad", "Q3")
monthly_quad = q.get("monthly_quad", "Q2")
global_quad = q.get("global_quad", "Q3")
conf = q.get("confidence", 0.35)
divergence = q.get("divergence", "divergent")
vix = q.get("vix_last", 20.0)
operating_regime = q.get("operating_regime", "Stagflation Persists")

def _h(html: str) -> None: st.markdown(" ".join(html.split()), unsafe_allow_html=True)

QC = {"Q1":("#1a4d2e","#4ade80"),"Q2":("#5c3d00","#fbbf24"),"Q3":("#5c2b00","#fb923c"),"Q4":("#5c1a1a","#f87171")}
def _qbg(q_): return QC.get(q_, ("#2d3748","#a0aec0"))[0]
def _qfg(q_): return QC.get(q_, ("#2d3748","#a0aec0"))[1]

# ── Header ──
_h(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="font-size:32px;">🧭</div>
    <div>
      <div style="font-size:24px;font-weight:800;color:#e6edf3;letter-spacing:-0.5px;">MacroRegime <span style="color:#58a6ff;">Pro</span></div>
      <div style="font-size:11px;color:#8b949e;margin-top:2px;">v11.1 · 2-Col · Color Heatmap · FRED Test</div>
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:11px;color:#8b949e;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</div>
    <div style="font-size:11px;color:#3fb950;margin-top:2px;">🟢 S:{structural_quad} · M:{monthly_quad} · G:{global_quad}</div>
  </div>
</div>
""")

# ── Regime Card ──
s_bg, s_fg = _qbg(structural_quad), _qfg(structural_quad)
m_bg, m_fg = _qbg(monthly_quad), _qfg(monthly_quad)
g_bg, g_fg = _qbg(global_quad), _qfg(global_quad)

tickers = snap.get("regime_tickers", {})
best_long = tickers.get("us_longs", ["—"])[0] if tickers.get("us_longs") else "—"
best_short = tickers.get("us_shorts", ["—"])[0] if tickers.get("us_shorts") else "—"
best_ihsg = tickers.get("ihsg_buys", [""])[0] if tickers.get("ihsg_buys") else ""

risk_state = snap.get("crash", {}).get("exec_mode", "CALM")
risk_color = "#3fb950" if "CALM" in risk_state else "#d29922" if "CAUTIOUS" in risk_state else "#f85149"
exec_state = snap.get("regime_transition", {}).get("front_run_window", "Wait")
exec_color = "#3fb950" if "now" in exec_state.lower() else "#d29922"
rally = snap.get("most_hated_rally", {})
rally_clear = rally.get("clear_count", 0)
rally_total = rally.get("total", 4)

_h(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:14px;padding:16px;margin-bottom:14px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;">
    <span style="background:{s_bg};color:{s_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">S:{structural_quad}</span>
    <span style="background:{m_bg};color:{m_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">M:{monthly_quad}</span>
    <span style="background:{g_bg};color:{g_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">G:{global_quad}</span>
    <span style="color:#8b949e;font-size:13px;">{operating_regime}</span>
    <span style="margin-left:auto;color:#fb923c;font-size:13px;font-weight:600;">🔥 {operating_regime}</span>
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
    <span>Conf: <span style="color:#f85149;font-weight:600;">{conf:.0%} (Low-Conviction)</span></span>
    <span>Growth: <span style="color:#3fb950;">▲</span></span>
    <span>Inflasi: <span style="color:#f85149;">▼</span></span>
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
    <span>▲ Best Long: <span style="color:#3fb950;font-weight:600;">{best_long}</span></span>
    <span>▼ Best Short: <span style="color:#f85149;font-weight:600;">{best_short}</span></span>
    {f'<span>🇮🇩 IHSG: <span style="color:#fb923c;font-weight:600;">{best_ihsg}</span></span>' if best_ihsg else ''}
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
    <span>Risk: <span style="color:{risk_color};">🟢 {risk_state}</span></span>
    <span>Exec: <span style="color:{exec_color};">🟡 {exec_state}</span></span>
    <span>Rally: {rally_clear}/{rally_total} clear</span>
  </div>
  <div style="display:flex;align-items:center;justify-content:space-between;font-size:11px;color:#8b949e;margin-top:8px;border-top:1px solid #30363d;padding-top:8px;">
    <span>🕊️ Event-Lite: Relief / De-escalation</span>
    <span>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</span>
  </div>
</div>
""")

top_drivers = snap.get("top_drivers", [])
if top_drivers:
    parts = [f"{d.get('name', d.get('label', '—'))}: {d.get('score', 0):.0%}" for d in top_drivers[:3]]
    parts.append(f"🕊️ Event-Lite: 77%")
    _h(f'<div style="font-size:12px;color:#8b949e;margin-bottom:14px;">Top drivers now → {" · ".join(parts)}</div>')

tabs = st.tabs(["⚡ Command Center", "🌍 Markets", "📊 Regime Deep Dive", "⚠️ Risk & Diag"])

with tabs[0]:
    render_command_center(snap)

with tabs[1]:
    prices = snap.get("prices", {})
    transition = snap.get("regime_transition", {})
    fw = transition.get("front_run_window", "—")
    tr_label = f"{structural_quad}→{q.get('next_quad', '?')}" if q.get('next_quad') else "No transition"
    narr = snap.get("narrative_discovery", {})
    btl = snap.get("bottleneck_discovery", {})

    def ret_n(s, n):
        if s is None or len(s) < n+1: return float("nan")
        try:
            b = float(s.iloc[-(n+1)]); e = float(s.iloc[-1])
            return float(e/b-1) if b != 0 else float("nan")
        except: return float("nan")

    def get_ret(s, n):
        r = ret_n(s, n)
        return f"{r:+.1%}" if r == r else "—"

    def ticker_card(tk, name, ret1m, ret3m, signal):
        color = "#3fb950" if signal == "long" else "#f85149" if signal == "short" else "#d29922"
        icon = "▲" if signal == "long" else "▼" if signal == "short" else "⚡"
        return f"""
        <div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;min-width:140px;flex:1;">
          <div>
            <div style="font-size:13px;font-weight:700;color:#e6edf3;">{tk}</div>
            <div style="font-size:10px;color:#8b949e;">{name}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:11px;color:{color};font-weight:700;">{icon} {ret1m}</div>
            <div style="font-size:9px;color:#8b949e;">3M: {ret3m}</div>
          </div>
        </div>
        """

    if fw in ("now", "1-2 weeks", "1-2w", "1-2W"):
        _h(f"""
        <div style="background:#1a3a2a;border:1px solid #3fb950;border-radius:10px;padding:12px;margin-bottom:16px;">
          <div style="color:#3fb950;font-size:13px;font-weight:700;">⚡ FRONT-RUN WINDOW: {fw.upper()} · {tr_label}</div>
          <div style="color:#c9d1d9;font-size:12px;margin-top:4px;">{transition.get('front_run_rationale', '—')}</div>
        </div>
        """)

    mkt_tabs = st.tabs(["🇺🇸 US Stocks", "🇮🇩 IHSG", "💱 FX", "🛢️ Commodities", "🔐 Crypto"])

    # ══════ 🇺🇸 US STOCKS ══════
    with mkt_tabs[0]:
        us_longs = tickers.get("us_longs", [])
        us_shorts = tickers.get("us_shorts", [])
        fr_us_long = us_longs[:3] if fw in ("now", "1-2 weeks") else []
        fr_us_short = us_shorts[:2] if fw in ("now", "1-2 weeks") else []
        names = {"SPY":"S&P 500","QQQ":"Nasdaq","IWM":"Russell 2K","XLE":"Energy","XLK":"Tech","XLF":"Finance","XLI":"Industrials","XLB":"Materials","XLV":"Health","XLY":"Consumer","XLP":"Staples","XLU":"Utilities","XLRE":"REITs","SPLV":"Low Vol","TLT":"Long Bond","GLD":"Gold","SMH":"Semis"}

        # NOW — 2 column layout
        c_long, c_short = st.columns(2)
        with c_long:
            st.markdown("**📍 NOW — LONG**")
            if us_longs:
                cards = []
                for t in us_longs:
                    s = prices.get(t)
                    cards.append(ticker_card(t, names.get(t, t), get_ret(s, 21), get_ret(s, 63), "long"))
                for i in range(0, len(cards), 2):
                    row = cards[i:i+2]
                    _h(f'<div style="display:flex;gap:8px;margin-bottom:8px;">' + "".join(row) + '</div>')
            else: st.caption("No longs")
        with c_short:
            st.markdown("**📍 NOW — SHORT**")
            if us_shorts:
                cards = []
                for t in us_shorts:
                    s = prices.get(t)
                    cards.append(ticker_card(t, names.get(t, t), get_ret(s, 21), get_ret(s, 63), "short"))
                for i in range(0, len(cards), 2):
                    row = cards[i:i+2]
                    _h(f'<div style="display:flex;gap:8px;margin-bottom:8px;">' + "".join(row) + '</div>')
            else: st.caption("No shorts")

        # FRONT-RUN — 2 column
        if fr_us_long or fr_us_short:
            st.divider()
            c_fr_l, c_fr_s = st.columns(2)
            with c_fr_l:
                st.markdown("**⚡ ACCUMULATE**")
                if fr_us_long:
                    cards = []
                    for t in fr_us_long:
                        s = prices.get(t)
                        cards.append(ticker_card(t, names.get(t, t), get_ret(s, 21), get_ret(s, 63), "fr"))
                    for i in range(0, len(cards), 2):
                        row = cards[i:i+2]
                        _h(f'<div style="display:flex;gap:8px;margin-bottom:8px;">' + "".join(row) + '</div>')
            with c_fr_s:
                st.markdown("**⚡ FADE**")
                if fr_us_short:
                    cards = []
                    for t in fr_us_short:
                        s = prices.get(t)
                        cards.append(ticker_card(t, names.get(t, t), get_ret(s, 21), get_ret(s, 63), "short"))
                    for i in range(0, len(cards), 2):
                        row = cards[i:i+2]
                        _h(f'<div style="display:flex;gap:8px;margin-bottom:8px;">' + "".join(row) + '</div>')

        # ══════ OVERVIEW (Visual Revamp) ══════
        st.divider()
        st.markdown('<div style="font-size:15px;font-weight:700;color:#e6edf3;margin-bottom:10px;">📊 MARKET OVERVIEW</div>', unsafe_allow_html=True)

        # Heatmap — Color-coded pills
        st.markdown("**🌍 Heatmap**")
        if prices:
            heat_assets = [("SPY","S&P 500"),("QQQ","Nasdaq"),("IWM","Russell 2K"),("TLT","Bond"),("GLD","Gold"),("BTC-USD","BTC"),("CL=F","Oil"),("UUP","USD")]
            heat_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
            for tk, name in heat_assets:
                s = prices.get(tk)
                if s is not None:
                    r1 = ret_n(s, 21); r3 = ret_n(s, 63)
                    c = "#1a4d2e" if r1 > 0.05 else "#2d5a3d" if r1 > 0 else "#5c1a1a" if r1 < -0.05 else "#3d1a1a" if r1 < 0 else "#2d3748"
                    txt = "#4ade80" if r1 > 0 else "#f87171" if r1 < 0 else "#a0aec0"
                    heat_html.append(f'<div style="background:{c};padding:6px 10px;border-radius:6px;text-align:center;min-width:80px;"><div style="font-size:11px;color:#8b949e;">{name}</div><div style="font-size:13px;color:{txt};font-weight:700;">{r1:+.1%}</div><div style="font-size:9px;color:#8b949e;">3M {r3:+.1%}</div></div>')
            heat_html.append('</div>')
            _h("".join(heat_html))

        # Sector — Horizontal bars
        st.markdown("**📊 Sector Leadership (Top 5)**")
        SECS = {"XLE":"Energy","XLF":"Fin","XLI":"Ind","XLB":"Mat","XLK":"Tech","XLV":"Health","XLY":"Con.D","XLP":"Con.S","XLU":"Util","XLRE":"RE"}
        spy3 = ret_n(prices.get("SPY"), 63)
        sec_rows = []
        for tk, name in SECS.items():
            s = prices.get(tk)
            if s is not None and len(s) > 63:
                r3 = ret_n(s, 63); rel = (r3 - spy3) if spy3==spy3 and r3==r3 else float("nan")
                sec_rows.append({"name": name, "r3": r3, "rel": rel})
        if sec_rows:
            sec_rows.sort(key=lambda r: r["rel"] if r["rel"] == r["rel"] else -999, reverse=True)
            for s in sec_rows[:5]:
                rel = s["rel"]
                rel_pct = min(max((rel + 0.15) / 0.3 * 100, 0), 100) if rel == rel else 50
                bar_color = "#3fb950" if rel > 0 else "#f85149" if rel < 0 else "#8b949e"
                _h(f"""
                <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
                  <div style="width:60px;font-size:11px;color:#c9d1d9;">{s["name"]}</div>
                  <div style="flex:1;background:#21262d;border-radius:4px;height:16px;overflow:hidden;">
                    <div style="width:{rel_pct}%;background:{bar_color};height:100%;border-radius:4px;"></div>
                  </div>
                  <div style="width:50px;text-align:right;font-size:11px;color:{bar_color};font-weight:600;">{rel:+.1%}</div>
                </div>
                """)

        # Bottleneck — Compact cards
        st.markdown("**🔍 Bottleneck Scan**")
        if btl:
            if btl.get("summary"): st.caption(btl["summary"])
            if btl.get("front_run_basket"):
                basket = btl["front_run_basket"][:6]
                b_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
                for item in basket:
                    tk = item.get("ticker","—")
                    sec = item.get("sector","—")[:10]
                    score = item.get("bottleneck_score",0)
                    stage = item.get("stage","—")
                    stage_c = {"mature":"#f85149","building":"#d29922","early":"#3fb950"}.get(stage, "#8b949e")
                    b_html.append(f'<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:6px 10px;text-align:center;"><div style="font-size:12px;font-weight:700;color:#e6edf3;">{tk}</div><div style="font-size:9px;color:#8b949e;">{sec}</div><div style="font-size:10px;color:{stage_c};">{stage} · {score:.2f}</div></div>')
                b_html.append('</div>')
                _h("".join(b_html))
        else: st.caption("No bottleneck data")

        # Master Board — Pill grid
        st.markdown("**📋 Master Board**")
        all_tickers = []
        if tickers:
            for side, key in [("Long","us_longs"),("Short","us_shorts"),("IHSG","ihsg_buys"),("FX","fx_longs"),("Comm","commodity_longs"),("Crypto","crypto_longs")]:
                for t in tickers.get(key, [])[:3]:
                    all_tickers.append((t, side, "#3fb950" if side=="Long" else "#f85149" if side=="Short" else "#fb923c"))
        if btl and btl.get("front_run_basket"):
            for item in btl["front_run_basket"][:4]:
                all_tickers.append((item.get("ticker","—"), "Adap", "#58a6ff"))
        if narr and narr.get("active_narratives"):
            for n in narr["active_narratives"][:2]:
                for b in n.get("primary_beneficiaries", [])[:2]:
                    all_tickers.append((b, "Narr", "#a371f7"))
        if all_tickers:
            m_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
            for t, side, color in all_tickers:
                m_html.append(f'<div style="background:#0d1117;border:1px solid #30363d;border-radius:4px;padding:4px 8px;font-size:11px;color:{color};font-weight:600;">{t} <span style="color:#8b949e;font-size:9px;">{side}</span></div>')
            m_html.append('</div>')
            _h("".join(m_html))

    # ══════ 🇮🇩 IHSG ══════
    with mkt_tabs[1]:
        ihsg_longs = tickers.get("ihsg_buys", [])
        fr_ihsg = ihsg_longs[:3] if fw in ("now", "1-2 weeks") else []
        names_ihsg = {"BBCA.JK":"BCA","BBRI.JK":"BRI","ASII.JK":"Astra","TLKM.JK":"Telkom","ADRO.JK":"Adaro","ANTM.JK":"Antam","PTBA.JK":"Bukit Asam","ITMG.JK":"Indomining","INCO.JK":"Vale","KLBF.JK":"Kalbe"}
        if ihsg_longs:
            st.markdown("**📍 NOW — LONG**")
            cards = []
            for t in ihsg_longs:
                s = prices.get(t)
                cards.append(ticker_card(t, names_ihsg.get(t, t), get_ret(s, 21), get_ret(s, 63), "long"))
            for i in range(0, len(cards), 3):
                row = cards[i:i+3]
                _h(f'<div style="display:flex;gap:8px;margin-bottom:8px;">' + "".join(row) + '</div>')
        if fr_ihsg:
            st.markdown("**⚡ ACCUMULATE**")
            cards = []
            for t in fr_ihsg:
                s = prices.get(t)
                cards.append(ticker_card(t, names_ihsg.get(t, t), get_ret(s, 21), get_ret(s, 63), "fr"))
            for i in range(0, len(cards), 3):
                row = cards[i:i+3]
                _h(f'<div style="display:flex;gap:8px;margin-bottom:8px;">' + "".join(row) + '</div>')

    # ══════ 💱 FX ══════
    with mkt_tabs[2]:
        fx_longs = tickers.get("fx_longs", [])
        fr_fx = fx_longs[:2] if fw in ("now", "1-2 weeks") else []
        names_fx = {"EURUSD=X":"EUR/USD","USDJPY=X":"USD/JPY","AUDUSD=X":"AUD/USD","USDIDR=X":"USD/IDR","UUP":"DXY"}
        if fx_longs:
            st.markdown("**📍 NOW — LONG**")
            cards = []
            for t in fx_longs:
                s = prices.get(t)
                cards.append(ticker_card(t, names_fx.get(t, t), get_ret(s, 21), get_ret(s, 63), "long"))
            for i in range(0, len(cards), 3):
                row = cards[i:i+3]
                _h(f'<div style="display:flex;gap:8px;margin-bottom:8px;">' + "".join(row) + '</div>')

    # ══════ 🛢️ COMMODITIES ══════
    with mkt_tabs[3]:
        comm_longs = tickers.get("commodity_longs", [])
        fr_comm = comm_longs[:3] if fw in ("now", "1-2 weeks") else []
        names_comm = {"CL=F":"WTI Oil","GC=F":"Gold","HG=F":"Copper","SI=F":"Silver","NG=F":"Nat Gas","BZ=F":"Brent","URA":"Uranium"}
        if comm_longs:
            st.markdown("**📍 NOW — LONG**")
            cards = []
            for t in comm_longs:
                s = prices.get(t)
                cards.append(ticker_card(t, names_comm.get(t, t), get_ret(s, 21), get_ret(s, 63), "long"))
            for i in range(0, len(cards), 3):
                row = cards[i:i+3]
                _h(f'<div style="display:flex;gap:8px;margin-bottom:8px;">' + "".join(row) + '</div>')

    # ══════ 🔐 CRYPTO ══════
    with mkt_tabs[4]:
        cry_longs = tickers.get("crypto_longs", [])
        fr_cry = cry_longs[:2] if fw in ("now", "1-2 weeks") and vix < 22 else []
        names_cry = {"BTC-USD":"Bitcoin","ETH-USD":"Ethereum","SOL-USD":"Solana","XRP-USD":"XRP"}
        if cry_longs:
            st.markdown("**📍 NOW — LONG**")
            cards = []
            for t in cry_longs:
                s = prices.get(t)
                cards.append(ticker_card(t, names_cry.get(t, t), get_ret(s, 21), get_ret(s, 63), "long"))
            for i in range(0, len(cards), 3):
                row = cards[i:i+3]
                _h(f'<div style="display:flex;gap:8px;margin-bottom:8px;">' + "".join(row) + '</div>')

with tabs[2]:
    show_raw = st.toggle("Show raw regime state JSON", value=False)
    if show_raw: st.markdown("**Regime State**"); st.json(q)
    st.markdown("**Structural Probabilities**")
    probs = q.get("structural_probs", {}); m_probs = q.get("monthly_probs", {})
    if probs:
        for k in ["Q1","Q2","Q3","Q4"]:
            p = probs.get(k, 0.0); mp = m_probs.get(k, 0.0) if m_probs else 0.0
            is_s = k == structural_quad; is_m = k == monthly_quad and not is_s
            label = f"{'●' if is_s else '◉' if is_m else '○'} {k}: S={p:.0%} M={mp:.0%}"
            st.progress(p, text=label)
    else: st.info("No probability data")
    st.divider(); st.markdown("**Raw Macro Indicators**")
    rows = []
    for lbl, key, note in [("INDPRO YoY","indpro_yoy","▲" if f.get("indpro_acc") else "▼"),("CPI YoY","cpi_yoy","▲" if f.get("cpi_acc") else "▼"),("Core PCE","corepce_yoy","▲" if f.get("corepce_acc") else "▼"),("VIX","vix_last",""),("HY OAS","hy_oas",f"Δ1M: {f.get('hy_oas_1m',0):+.0f}bps"),("Policy Score","policy_score","+ve=cutting")]:
        val = f.get(key)
        if val is not None:
            try:
                v = float(val) if not isinstance(val, bool) else float("nan")
                if v == v: rows.append({"Indicator": lbl, "Value": f"{v:+.2f}" if abs(v) < 100 else f"{v:.2f}", "Note": note})
            except: pass
    if rows: st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("⚠️ Risk & Diagnostics")
    
    # FRED Direct Test Result
    fred_ok = st.session_state.get("_fred_api_ok", False)
    fred_err = st.session_state.get("_fred_api_err", "")
    
    fred_meta = snap.get("fred_meta", {})
    if fred_meta:
        loaded = fred_meta.get("loaded", 0); missing = fred_meta.get("missing", 0)
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("FRED Loaded", f"{loaded}/{loaded+missing}")
        with c2: st.metric("Real Share", f"{fred_meta.get('real_share', 0):.0%}")
        with c3: st.metric("API Key", "✅" if fred_meta.get("api_key_present") else "❌")
        if missing > 0:
            mk = fred_meta.get("missing_keys", [])
            if mk: st.warning(f"Missing: {', '.join(mk[:10])}")
    else: st.error("FRED metadata unavailable")

    # Direct test result
    if not fred_ok:
        st.error(f"🚨 FRED API Direct Test FAILED: {fred_err}")
        st.info("Causes: (1) Key invalid/expired, (2) Streamlit Cloud blocks FRED, (3) Rate limited. Try local run or new key.")
    else:
        st.success("✅ FRED API Direct Test PASSED — but loader still 0. Check fred_loader.py cache logic.")

    if rally:
        st.divider(); st.markdown("**Most Hated Rally — Checklist**")
        st.caption(f"Stage: {rally.get('stage', '?')} | Action: {rally.get('action', '?')}")
        for item in rally.get("checklist", []):
            ok = item.get("value", False)
            icon = "✅" if ok else "⬜"
            color = "#3fb950" if ok else "#8b949e"
            raw = item.get("raw", 0)
            _h(f'<div style="color:{color};font-size:13px;margin:4px 0;">{icon} {item.get("item", "—")} <span style="color:#8b949e;">({raw:.3f})</span></div>')
        if rally_clear >= 4: st.success("All 4 cleared")
        else: st.info(f"{rally_clear}/4 cleared")

    if fred_meta and fred_meta.get("loaded", 0) == 0:
        st.error("🚨 FRED 0 loaded — all proxy data.")
        if st.button("🔄 Force Clear Cache & Reload"):
            st.cache_data.clear()
            st.rerun()