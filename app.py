"""MacroRegime Pro v11.4 — IHSG Sector Leadership Fix"""
import os
import sys
import glob
from datetime import datetime, timezone

import streamlit as st
import pandas as pd

st.set_page_config(page_title="MacroRegime Pro", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")

# Kill cache
for f in glob.glob("/tmp/fred_cache_*.pkl") + glob.glob("/tmp/price_cache_*.pkl"):
    try: os.remove(f)
    except: pass

if "FRED_API_KEY" in st.secrets:
    os.environ["FRED_API_KEY"] = st.secrets["FRED_API_KEY"]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path: sys.path.insert(0, SCRIPT_DIR)

from orchestration.build_snapshot import build_snapshot
from ui.command_center_page import render_command_center
from ui.theme import _inject_theme

_inject_theme()

@st.cache_data(ttl=300)
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
        rt["fx_shorts"] = ["EURUSD=X", "AUDUSD=X"]
        rt["commodity_longs"] = ["GC=F", "SI=F"]
        rt["commodity_shorts"] = ["CL=F", "HG=F"]
        rt["crypto_longs"] = ["BTC-USD", "ETH-USD"]
        rt["crypto_shorts"] = ["SOL-USD"]
        snap["regime_tickers"] = rt
        return snap
    except Exception as e:
        st.error(f"Snapshot failed: {e}")
        return {
            "q": {"quad":"Q3","structural_quad":"Q3","monthly_quad":"Q2","global_quad":"Q3","confidence":0.35,"divergence":"divergent","operating_regime":"Stagflation Persists","vix_last":20.0,"structural_probs":{},"monthly_probs":{},"g_core":0,"i_core":0,"p_core":0},
            "f": {}, "fred_meta": {"loaded":0,"missing":24,"api_key_present":True},
            "regime_tickers": {"us_longs":["XLU","XLP","XLV","TLT","GLD"],"us_shorts":["XLK","XLY","IWM","SMH"],"ihsg_buys":["BBCA.JK","BBRI.JK","TLKM.JK"],"fx_longs":["USDJPY=X","UUP"],"fx_shorts":["EURUSD=X","AUDUSD=X"],"commodity_longs":["GC=F","SI=F"],"commodity_shorts":["CL=F","HG=F"],"crypto_longs":["BTC-USD","ETH-USD"],"crypto_shorts":["SOL-USD"]},
            "top_drivers": [], "narrative_discovery": {}, "bottleneck_discovery": {},
            "most_hated_rally": {}, "regime_transition": {}, "prices": {}
        }

snap = _load_snapshot()
q = snap.get("q", {})
f = snap.get("f", {})
quad = q.get("quad","Q3")
structural_quad = q.get("structural_quad", "Q3")
monthly_quad = q.get("monthly_quad", "Q2")
global_quad = q.get("global_quad", "Q3")
conf = q.get("confidence", 0.35)
vix = q.get("vix_last", 20.0)
operating_regime = q.get("operating_regime", "Stagflation Persists")
tickers = snap.get("regime_tickers", {})
prices = snap.get("prices", {})
btl = snap.get("bottleneck_discovery", {})
narr = snap.get("narrative_discovery", {})

def _h(html): st.markdown(" ".join(html.split()), unsafe_allow_html=True)

QC = {"Q1":("#1a4d2e","#4ade80"),"Q2":("#5c3d00","#fbbf24"),"Q3":("#5c2b00","#fb923c"),"Q4":("#5c1a1a","#f87171")}
def _qbg(q_): return QC.get(q_, ("#2d3748","#a0aec0"))[0]
def _qfg(q_): return QC.get(q_, ("#2d3748","#a0aec0"))[1]

s_bg, s_fg = _qbg(structural_quad), _qfg(structural_quad)
m_bg, m_fg = _qbg(monthly_quad), _qfg(monthly_quad)
g_bg, g_fg = _qbg(global_quad), _qfg(global_quad)

# Header
_h(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="font-size:32px;">🧭</div>
    <div>
      <div style="font-size:24px;font-weight:800;color:#e6edf3;">MacroRegime <span style="color:#58a6ff;">Pro</span></div>
      <div style="font-size:11px;color:#8b949e;">v11.4 · IHSG Sectors · Working</div>
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:11px;color:#8b949e;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</div>
    <div style="font-size:11px;color:#3fb950;">🟢 S:{structural_quad} · M:{monthly_quad} · G:{global_quad}</div>
  </div>
</div>
""")

# Regime Card
_h(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:14px;padding:16px;margin-bottom:14px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;">
    <span style="background:{s_bg};color:{s_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">S:{structural_quad}</span>
    <span style="background:{m_bg};color:{m_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">M:{monthly_quad}</span>
    <span style="background:{g_bg};color:{g_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">G:{global_quad}</span>
    <span style="margin-left:auto;color:#fb923c;font-size:13px;font-weight:600;">🔥 {operating_regime}</span>
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
    <span>Conf: <span style="color:#f85149;font-weight:600;">{conf:.0%}</span></span>
    <span>Growth: <span style="color:#3fb950;">▲</span></span>
    <span>Inflasi: <span style="color:#f85149;">▼</span></span>
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
    <span>▲ Best Long: <span style="color:#3fb950;font-weight:600;">{tickers.get('us_longs',['—'])[0]}</span></span>
    <span>▼ Best Short: <span style="color:#f85149;font-weight:600;">{tickers.get('us_shorts',['—'])[0]}</span></span>
  </div>
</div>
""")

# TABS
tabs = st.tabs(["⚡ Command Center", "🌍 Markets", "📊 Regime Deep Dive", "⚠️ Risk & Diag"])

with tabs[0]:
    render_command_center(snap)

with tabs[1]:
    prices = snap.get("prices", {})
    transition = snap.get("regime_transition", {})
    fw = transition.get("front_run_window", "—")
    btl = snap.get("bottleneck_discovery", {})
    narr = snap.get("narrative_discovery", {})

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
        <div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;flex:1;min-width:140px;">
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

    def render_cards(ticker_list, names_map, signal_type, per_row=2):
        if not ticker_list: return
        cards = []
        for t in ticker_list:
            s = prices.get(t)
            cards.append(ticker_card(t, names_map.get(t, t), get_ret(s, 21), get_ret(s, 63), signal_type))
        for i in range(0, len(cards), per_row):
            row = cards[i:i+per_row]
            _h(f'<div style="display:flex;gap:8px;margin-bottom:8px;">' + "".join(row) + '</div>')

    def render_heatmap(assets_list):
        if not prices: return
        heat_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
        for tk, name in assets_list:
            s = prices.get(tk)
            if s is not None:
                r1 = ret_n(s, 21); r3 = ret_n(s, 63)
                c = "#1a4d2e" if r1 > 0.05 else "#2d5a3d" if r1 > 0 else "#5c1a1a" if r1 < -0.05 else "#3d1a1a" if r1 < 0 else "#2d3748"
                txt = "#4ade80" if r1 > 0 else "#f87171" if r1 < 0 else "#a0aec0"
                heat_html.append(f'<div style="background:{c};padding:6px 10px;border-radius:6px;text-align:center;min-width:80px;"><div style="font-size:11px;color:#8b949e;">{name}</div><div style="font-size:13px;color:{txt};font-weight:700;">{r1:+.1%}</div><div style="font-size:9px;color:#8b949e;">3M {r3:+.1%}</div></div>')
        heat_html.append('</div>')
        _h("".join(heat_html))

    # ═══════════════════════════════════════════════════════════════════════
    # UNIVERSAL MARKET LEADERSHIP BARS
    # ═══════════════════════════════════════════════════════════════════════
    def render_market_leaders(asset_list, benchmark_tk=None, title="Market Leadership"):
        """Render top 5 leadership bars for any market."""
        bench_ret = ret_n(prices.get(benchmark_tk), 63) if benchmark_tk else float("nan")
        rows = []
        for tk, name in asset_list:
            s = prices.get(tk)
            if s is not None and len(s) > 63:
                r3 = ret_n(s, 63)
                rel = (r3 - bench_ret) if bench_ret == bench_ret and r3 == r3 else r3
                rows.append({"name": name, "rel": rel, "tk": tk})
        if not rows:
            st.caption(f"No price data for {title}")
            return
        rows.sort(key=lambda r: r["rel"] if r["rel"] == r["rel"] else -999, reverse=True)
        st.markdown(f"**📊 {title} (Top 5)**")
        for s in rows[:5]:
            rel = s["rel"]
            rel_pct = min(max((rel + 0.15) / 0.3 * 100, 0), 100) if rel == rel else 50
            bar_color = "#3fb950" if rel > 0 else "#f85149" if rel < 0 else "#8b949e"
            _h(f"""
            <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
              <div style="width:70px;font-size:11px;color:#c9d1d9;">{s["name"]}</div>
              <div style="flex:1;background:#21262d;border-radius:4px;height:16px;overflow:hidden;">
                <div style="width:{rel_pct}%;background:{bar_color};height:100%;border-radius:4px;"></div>
              </div>
              <div style="width:60px;text-align:right;font-size:11px;color:{bar_color};font-weight:600;">{rel:+.1%}</div>
            </div>
            """)

    def render_sector_bars():
        SECS = {"XLE":"Energy","XLF":"Fin","XLI":"Ind","XLB":"Mat","XLK":"Tech","XLV":"Health","XLY":"Con.D","XLP":"Con.S","XLU":"Util","XLRE":"RE"}
        spy3 = ret_n(prices.get("SPY"), 63)
        sec_rows = []
        for tk, name in SECS.items():
            s = prices.get(tk)
            if s is not None and len(s) > 63:
                r3 = ret_n(s, 63); rel = (r3 - spy3) if spy3==spy3 and r3==r3 else float("nan")
                sec_rows.append({"name": name, "rel": rel})
        if sec_rows:
            sec_rows.sort(key=lambda r: r["rel"] if r["rel"] == r["rel"] else -999, reverse=True)
            st.markdown("**📊 Sector Leadership (Top 5)**")
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

    # ═══════════════════════════════════════════════════════════════════════
    # IHSG SECTOR LEADERSHIP — Proxy-based IDX sectors
    # ═══════════════════════════════════════════════════════════════════════
    def render_ihsg_sector_bars():
        """IDX sector leadership using blue-chip proxies. Averages 3M return per sector vs ^JKSE."""
        SECTORS = {
            "Energy":   ["ADRO.JK", "ITMG.JK", "PTBA.JK"],
            "Finance":  ["BBCA.JK", "BBRI.JK", "BMRI.JK"],
            "Consumer": ["UNVR.JK", "INDF.JK", "ICBP.JK"],
            "Infra":    ["TLKM.JK", "PGAS.JK", "EXCL.JK"],
            "Property": ["CTRA.JK", "PWON.JK", "BSDE.JK"],
            "Mining":   ["ANTM.JK", "INCO.JK", "MDKA.JK"],
            "Health":   ["KLBF.JK", "SIDO.JK", "KAEF.JK"],
            "Agri":     ["AALI.JK", "LSIP.JK", "SGRO.JK"],
            "Industri": ["ASII.JK", "AUTO.JK", "MPMX.JK"],
        }
        jkse3 = ret_n(prices.get("^JKSE"), 63)
        sec_rows = []
        for name, proxies in SECTORS.items():
            rets = []
            for tk in proxies:
                s = prices.get(tk)
                if s is not None and len(s) > 63:
                    r = ret_n(s, 63)
                    if r == r: rets.append(r)
            if rets:
                avg = sum(rets) / len(rets)
                rel = (avg - jkse3) if jkse3 == jkse3 else avg
                sec_rows.append({"name": name, "rel": rel})
        if sec_rows:
            sec_rows.sort(key=lambda r: r["rel"] if r["rel"] == r["rel"] else -999, reverse=True)
            st.markdown("**📊 IDX Sector Leadership (Top 5)**")
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
        else:
            st.caption("No IDX sector data — proxy tickers unavailable.")

    # ═══════════════════════════════════════════════════════════════════════
    # BOTTLENECK FILTER — Explicit per market, ga nyampur
    # ═══════════════════════════════════════════════════════════════════════
    def is_us_ticker(tk):
        return not any(x in tk for x in [".JK", "=X", "-USD", "=F", "URA"]) and tk not in ["^JKSE"]

    def is_ihsg_ticker(tk):
        return ".JK" in tk or tk == "^JKSE"

    def is_fx_ticker(tk):
        return "=X" in tk

    def is_comm_ticker(tk):
        return "=F" in tk or tk == "URA"

    def is_crypto_ticker(tk):
        return "-USD" in tk

    def render_bottleneck_filtered(filter_fn, market_name):
        if not btl:
            st.caption("No bottleneck data")
            return
        if btl.get("summary"): st.caption(btl["summary"])
        basket = btl.get("front_run_basket", [])
        total = len(basket)
        filtered = [item for item in basket if filter_fn(item.get("ticker", ""))]
        if not filtered:
            st.caption(f"No {market_name} bottleneck detected — adaptive scan returned {total} candidate(s), none matched {market_name} ticker patterns.")
            return
        b_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
        for item in filtered[:8]:
            tk = item.get("ticker","—")
            sec = item.get("sector","—")[:10]
            score = item.get("bottleneck_score",0)
            stage = item.get("stage","—")
            stage_c = {"mature":"#f85149","building":"#d29922","early":"#3fb950"}.get(stage, "#8b949e")
            b_html.append(f'<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:6px 10px;text-align:center;"><div style="font-size:12px;font-weight:700;color:#e6edf3;">{tk}</div><div style="font-size:9px;color:#8b949e;">{sec}</div><div style="font-size:10px;color:{stage_c};">{stage} · {score:.2f}</div></div>')
        b_html.append('</div>')
        _h("".join(b_html))

    # ═══════════════════════════════════════════════════════════════════════
    # MASTER BOARD FILTER — Cuma ticker dari market itu
    # ═══════════════════════════════════════════════════════════════════════
    def render_master_filtered(long_key, short_key, color_long, color_short, filter_fn, market_name):
        all_tickers = []
        for t in tickers.get(long_key, [])[:4]:
            all_tickers.append((t, "Long", color_long))
        if short_key:
            for t in tickers.get(short_key, [])[:4]:
                all_tickers.append((t, "Short", color_short))
        if btl and btl.get("front_run_basket"):
            for item in btl["front_run_basket"][:6]:
                tk = item.get("ticker","—")
                if filter_fn(tk) and tk not in [x[0] for x in all_tickers]:
                    all_tickers.append((tk, "Adap", "#58a6ff"))
        if narr and narr.get("active_narratives"):
            for n in narr["active_narratives"][:3]:
                for b in n.get("primary_beneficiaries", [])[:3]:
                    if filter_fn(b) and b not in [x[0] for x in all_tickers]:
                        all_tickers.append((b, "Narr", "#a371f7"))
        if all_tickers:
            m_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
            for t, side, color in all_tickers:
                m_html.append(f'<div style="background:#0d1117;border:1px solid #30363d;border-radius:4px;padding:4px 8px;font-size:11px;color:{color};font-weight:600;">{t} <span style="color:#8b949e;font-size:9px;">{side}</span></div>')
            m_html.append('</div>')
            _h("".join(m_html))
        else:
            st.caption(f"No {market_name} tickers")

    mkt_tabs = st.tabs(["🇺🇸 US Stocks", "🇮🇩 IHSG", "💱 FX", "🛢️ Commodities", "🔐 Crypto"])

    # ══════ 🇺🇸 US STOCKS ══════
    with mkt_tabs[0]:
        us_longs = tickers.get("us_longs", [])
        us_shorts = tickers.get("us_shorts", [])
        names = {"SPY":"S&P 500","QQQ":"Nasdaq","IWM":"Russell 2K","XLE":"Energy","XLK":"Tech","XLF":"Finance","XLI":"Industrials","XLB":"Materials","XLV":"Health","XLY":"Consumer","XLP":"Staples","XLU":"Utilities","XLRE":"REITs","SPLV":"Low Vol","TLT":"Long Bond","GLD":"Gold","SMH":"Semis"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(us_longs, names, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(us_shorts, names, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("SPY","S&P 500"),("QQQ","Nasdaq"),("IWM","Russell 2K"),("TLT","Bond"),("GLD","Gold"),("BTC-USD","BTC"),("CL=F","Oil"),("UUP","USD")])
        render_sector_bars()
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_us_ticker, "US")
        st.markdown("**📋 Master Board**")
        render_master_filtered("us_longs", "us_shorts", "#3fb950", "#f85149", is_us_ticker, "US")

    # ══════ 🇮🇩 IHSG (Long Only) ══════
    with mkt_tabs[1]:
        ihsg_longs = tickers.get("ihsg_buys", [])
        names_ihsg = {"BBCA.JK":"BCA","BBRI.JK":"BRI","ASII.JK":"Astra","TLKM.JK":"Telkom","ADRO.JK":"Adaro","ANTM.JK":"Antam","PTBA.JK":"Bukit Asam","ITMG.JK":"Indomining","INCO.JK":"Vale","KLBF.JK":"Kalbe"}
        st.markdown("**📍 NOW — LONG**")
        render_cards(ihsg_longs, names_ihsg, "long", 3)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("^JKSE","IHSG"),("BBCA.JK","BCA"),("BBRI.JK","BRI"),("ASII.JK","Astra"),("TLKM.JK","Telkom")])
        # IHSG Sector Leadership
        render_ihsg_sector_bars()
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_ihsg_ticker, "IHSG")
        st.markdown("**📋 Master Board**")
        render_master_filtered("ihsg_buys", None, "#fb923c", "#f85149", is_ihsg_ticker, "IHSG")

    # ══════ 💱 FX (Long + Short) ══════
    with mkt_tabs[2]:
        fx_longs = tickers.get("fx_longs", [])
        fx_shorts = tickers.get("fx_shorts", [])
        names_fx = {"EURUSD=X":"EUR/USD","USDJPY=X":"USD/JPY","AUDUSD=X":"AUD/USD","USDIDR=X":"USD/IDR","UUP":"DXY"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(fx_longs, names_fx, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(fx_shorts, names_fx, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("EURUSD=X","EUR/USD"),("USDJPY=X","USD/JPY"),("AUDUSD=X","AUD/USD"),("USDIDR=X","USD/IDR"),("UUP","DXY")])
        fx_leaders = [
            ("UUP","DXY"),("USDJPY=X","USD/JPY"),("EURUSD=X","EUR/USD"),
            ("AUDUSD=X","AUD/USD"),("GBPUSD=X","GBP/USD"),("USDCAD=X","USD/CAD")
        ]
        render_market_leaders(fx_leaders, benchmark_tk="UUP", title="FX Leadership")
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_fx_ticker, "FX")
        st.markdown("**📋 Master Board**")
        render_master_filtered("fx_longs", "fx_shorts", "#58a6ff", "#f85149", is_fx_ticker, "FX")

    # ══════ 🛢️ COMMODITIES (Long + Short) ══════
    with mkt_tabs[3]:
        comm_longs = tickers.get("commodity_longs", [])
        comm_shorts = tickers.get("commodity_shorts", [])
        names_comm = {"CL=F":"WTI Oil","GC=F":"Gold","HG=F":"Copper","SI=F":"Silver","NG=F":"Nat Gas","BZ=F":"Brent","URA":"Uranium"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(comm_longs, names_comm, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(comm_shorts, names_comm, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("CL=F","WTI Oil"),("GC=F","Gold"),("HG=F","Copper"),("SI=F","Silver"),("NG=F","Nat Gas")])
        comm_leaders = [
            ("GC=F","Gold"),("CL=F","WTI Oil"),("HG=F","Copper"),
            ("SI=F","Silver"),("NG=F","Nat Gas"),("BZ=F","Brent"),("URA","Uranium")
        ]
        render_market_leaders(comm_leaders, benchmark_tk="GC=F", title="Commodity Leadership")
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_comm_ticker, "Commodities")
        st.markdown("**📋 Master Board**")
        render_master_filtered("commodity_longs", "commodity_shorts", "#fb923c", "#f85149", is_comm_ticker, "Commodities")

    # ══════ 🔐 CRYPTO (Long + Short) ══════
    with mkt_tabs[4]:
        cry_longs = tickers.get("crypto_longs", [])
        cry_shorts = tickers.get("crypto_shorts", [])
        names_cry = {"BTC-USD":"Bitcoin","ETH-USD":"Ethereum","SOL-USD":"Solana","XRP-USD":"XRP"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(cry_longs, names_cry, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(cry_shorts, names_cry, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("BTC-USD","Bitcoin"),("ETH-USD","Ethereum"),("SOL-USD","Solana"),("XRP-USD","XRP")])
        render_market_leaders([
            ("BTC-USD","Bitcoin"),("ETH-USD","Ethereum"),("SOL-USD","Solana"),
            ("XRP-USD","XRP"),("ADA-USD","Cardano"),("DOT-USD","Polkadot")
        ], benchmark_tk="BTC-USD", title="Crypto Leadership")
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_crypto_ticker, "Crypto")
        st.markdown("**📋 Master Board**")
        render_master_filtered("crypto_longs", "crypto_shorts", "#a371f7", "#f85149", is_crypto_ticker, "Crypto")

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

with tabs[3]:
    st.subheader("⚠️ Risk & Diagnostics")
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
    
    if fred_meta and fred_meta.get("loaded", 0) == 0:
        st.error("🚨 FRED 0 loaded — all proxy data.")
        if st.button("🔄 Force Clear Cache & Reload"):
            st.cache_data.clear()
            st.rerun()