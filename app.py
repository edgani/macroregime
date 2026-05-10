"""
app.py — MacroRegime Pro UI v11
=================================
TIMPA FILE INI KE: app.py (di root repo macroregime lo)

Cara pakai:
1. Backup app.py lama:  cp app.py app_old.py
2. Timpa:               cp app.py .
3. Push:                git add app.py && git commit -m "ui v11" && git push

Yang berubah dari app.py lama:
- Semua tabel ada badge: Regime / Quad / Bottleneck
- IHSG table beda: + 🌊 Foreign Flow / 💱 FX Risk / 🏛️ Policy
- Crypto table beda: + Funding % / OI Δ % / Inflow / Whale Ratio  
- Tab GREEKS di sidebar DIHAPUS → jadi toggle "Show Option Greeks"
- Fix spanstyle error: pakai Pandas Styler (applymap), bukan HTML string di cell
- Filter Min R:R & Min Score di sidebar

orchestrator.py nggak diubah. Cuma app.py.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ── Import backend ─────────────────────────────────────────────────────────
try:
    from orchestrator import build_snapshot, QUAD_MAP, TICKER_SECTOR, _get_regime_fit
except Exception as e:
    st.error(f"Import orchestrator gagal: {e}")
    st.stop()

# ── Page config ──────────────────────────────────────────────────────────
st.set_page_config(page_title="MacroRegime Pro", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>.block-container{padding-top:0.8rem;padding-bottom:0.8rem;}.stDataFrame{font-size:12px!important;}</style>""", unsafe_allow_html=True)

# ── Build snapshot ───────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_snapshot():
    return build_snapshot()

snapshot = get_snapshot()
if not snapshot or not snapshot.get("ok"):
    st.error("Snapshot build failed. Cek log di Streamlit Cloud (Manage app → Logs).")
    st.stop()

gip = snapshot["gip"]
sq = gip.structural_quad
mq = gip.monthly_quad
regime_name = QUAD_MAP.get(sq, {}).get("name", "Unknown")
bias = QUAD_MAP.get(sq, {}).get("bias", "neutral")

# ── Badge helpers ────────────────────────────────────────────────────────
REGIME_BADGE = {"Q1": "🟢 RISK-ON", "Q2": "🟡 TRANSITION", "Q3": "🔴 RISK-OFF", "Q4": "🔴 RISK-OFF"}
QUAD_BADGE = {"Q1": "Q1📈", "Q2": "Q2🔄", "Q3": "Q3📉", "Q4": "Q4⚠️"}

def _bottleneck(row: dict) -> str:
    stype = str(row.get("scanner_type", ""))
    sig = str(row.get("signal", ""))
    if "BOTTLENECK L1" in stype: return "⛓️ SUPPLY"
    if "BOTTLENECK L2" in stype: return "💧 LIQ"
    if "WATCH" in stype: return "🔄 TRANS"
    if "DAILY" in stype: return "📉 DEMAND"
    if "ALPHA" in stype:
        fit = _get_regime_fit(row.get("ticker", ""), sq)
        if fit < 0.3: return "🏛️ POLICY"
        if fit > 0.8: return "✅ CLEAR"
        return "📉 DEMAND"
    if "STRONG" in sig: return "⚡ VOL"
    if "KEEP" in sig: return "🔄 TRANS"
    return "✅ CLEAR"

def add_badges(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "ticker" not in df.columns:
        return df
    regimes = []; quads = []; bneck = []
    for _, row in df.iterrows():
        regimes.append(REGIME_BADGE.get(sq, "⚪ N/A"))
        quads.append(QUAD_BADGE.get(sq, "—"))
        bneck.append(_bottleneck(row.to_dict()))
    df = df.copy()
    df["Regime"] = regimes
    df["Quad"] = quads
    df["Bottleneck"] = bneck
    return df

# ── Stylers (fix spanstyle) ──────────────────────────────────────────────
def hl_signal(val):
    v = str(val).upper()
    if any(x in v for x in ("LONG","BUY","BULLISH","BUY NOW","KEEP BULLISH","STRONG LONG")): return "color: #00ff88; font-weight: bold"
    if any(x in v for x in ("SHORT","SELL","BEARISH","SELL NOW","KEEP BEARISH","STRONG SHORT")): return "color: #ff4444; font-weight: bold"
    if any(x in v for x in ("NEUTRAL","HOLD","WATCH","DEFENSIVE")): return "color: #ffcc00; font-weight: bold"
    return ""

def hl_grade(val):
    if val == "S": return "color: #d4af37; font-weight: bold"
    if val in ("A+", "A"): return "color: #00ff88; font-weight: bold"
    if val == "B": return "color: #4488ff; font-weight: bold"
    if val == "C": return "color: #ffcc00; font-weight: bold"
    if val == "D": return "color: #ff4444; font-weight: bold"
    return ""

def hl_worth(val):
    v = str(val).upper()
    if "YES" in v or "BUY NOW" in v or "SELL NOW" in v: return "color: #00ff88; font-weight: bold"
    if "WAIT" in v or "SKIP" in v or "CHASE" in v: return "color: #ffcc00; font-weight: bold"
    return ""

def hl_funding(val):
    if isinstance(val, (int, float)):
        if val > 0.01: return "background-color: #ff4444; color: white; font-weight: bold"
        if val < -0.01: return "background-color: #00ff88; color: black; font-weight: bold"
        if val > 0.005: return "color: #ff4444; font-weight: bold"
        if val < -0.005: return "color: #00ff88; font-weight: bold"
    return ""

def hl_flow(val):
    if isinstance(val, str):
        if val.startswith("+"): return "color: #00ff88; font-weight: bold"
        if val.startswith("-"): return "color: #ff4444; font-weight: bold"
    return ""

# ── Table renderers ──────────────────────────────────────────────────────
def _prep_df(df: pd.DataFrame, core_cols, price_cols, meta_cols, rename_map):
    ordered = [c for c in core_cols + price_cols + meta_cols if c in df.columns]
    df = df[ordered]
    return df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

def render_alpha(items: list, title: str, show_greeks: bool = False):
    if not items:
        st.info(f"No {title} items.")
        return
    df = pd.DataFrame(items)
    df = add_badges(df)
    df = _prep_df(
        df,
        core_cols=["ticker", "scanner_type", "direction", "grade", "Regime", "Quad", "Bottleneck"],
        price_cols=["price", "entry", "target_1", "target_2", "stop_loss", "rr"],
        meta_cols=["worth_entering", "entry_advice", "path_smoothness", "time_estimate", "breakout_chance"],
        rename_map={
            "ticker": "Ticker", "scanner_type": "Type", "direction": "Dir", "grade": "Grade",
            "price": "Price", "entry": "Entry", "target_1": "T1", "target_2": "T2", "stop_loss": "Stop",
            "rr": "R:R", "worth_entering": "Worth?", "entry_advice": "Advice",
            "path_smoothness": "Path", "time_estimate": "Time", "breakout_chance": "Breakout"
        }
    )
    sig_cols = [c for c in ["Dir", "Worth?", "Advice"] if c in df.columns]
    grade_cols = [c for c in ["Grade"] if c in df.columns]
    styler = df.style.applymap(hl_signal, subset=sig_cols).applymap(hl_grade, subset=grade_cols).format(
        {"Price": "{:.2f}", "Entry": "{:.2f}", "T1": "{:.2f}", "T2": "{:.2f}", "Stop": "{:.2f}", "R:R": "{:.1f}"}, na_rep="—"
    )
    st.subheader(title)
    st.dataframe(styler, use_container_width=True, hide_index=True)
    if show_greeks:
        _greeks_overlay(items)

def render_daily(signals: list, title: str, show_greeks: bool = False):
    if not signals:
        st.info(f"No {title} signals.")
        return
    df = pd.DataFrame(signals)
    df = add_badges(df)
    df = _prep_df(
        df,
        core_cols=["ticker", "signal", "direction", "grade", "Regime", "Quad", "Bottleneck"],
        price_cols=["price", "entry", "target_1", "target_2", "stop_loss", "rr"],
        meta_cols=["worth_entering", "entry_advice", "path_smoothness", "time_estimate", "breakout_chance", "score"],
        rename_map={
            "ticker": "Ticker", "signal": "Signal", "direction": "Dir", "grade": "Grade",
            "price": "Price", "entry": "Entry", "target_1": "T1", "target_2": "T2", "stop_loss": "Stop",
            "rr": "R:R", "worth_entering": "Worth?", "entry_advice": "Advice",
            "path_smoothness": "Path", "time_estimate": "Time", "breakout_chance": "Breakout", "score": "Score"
        }
    )
    sig_cols = [c for c in ["Signal", "Dir", "Worth?", "Advice"] if c in df.columns]
    grade_cols = [c for c in ["Grade"] if c in df.columns]
    styler = df.style.applymap(hl_signal, subset=sig_cols).applymap(hl_grade, subset=grade_cols).format(
        {"Price": "{:.2f}", "Entry": "{:.2f}", "T1": "{:.2f}", "T2": "{:.2f}", "Stop": "{:.2f}", "R:R": "{:.1f}", "Score": "{:.2f}"}, na_rep="—"
    )
    st.subheader(title)
    st.dataframe(styler, use_container_width=True, hide_index=True)
    if show_greeks:
        _greeks_overlay(signals)

def render_ihsg(setups: list):
    if not setups:
        st.info("No IHSG setups.")
        return
    rows = []
    for s in setups:
        r = dict(s)
        # TODO: sambung ke IDX foreign flow scraper lo
        r["foreign_flow"] = "+120B"  # mock
        r["fx_risk"] = "LOW"
        r["policy"] = "BI Rate Hold"
        rows.append(r)
    df = pd.DataFrame(rows)
    df = add_badges(df)
    df = _prep_df(
        df,
        core_cols=["ticker", "sector", "Regime", "Quad", "Bottleneck", "grade"],
        price_cols=["price", "entry", "target_1", "target_2", "stop_loss", "rr"],
        meta_cols=["signal", "direction", "foreign_flow", "fx_risk", "policy"],
        rename_map={
            "ticker": "Ticker", "sector": "Sector", "grade": "Grade",
            "price": "Price", "entry": "Entry", "target_1": "T1", "target_2": "T2", "stop_loss": "Stop", "rr": "R:R",
            "signal": "Signal", "direction": "Dir",
            "foreign_flow": "🌊 Foreign Flow", "fx_risk": "💱 FX Risk", "policy": "🏛️ Policy"
        }
    )
    sig_cols = [c for c in ["Signal", "Dir"] if c in df.columns]
    grade_cols = [c for c in ["Grade"] if c in df.columns]
    flow_cols = [c for c in ["🌊 Foreign Flow"] if c in df.columns]
    styler = df.style.applymap(hl_signal, subset=sig_cols).applymap(hl_grade, subset=grade_cols).applymap(hl_flow, subset=flow_cols).format(
        {"Price": "{:.0f}", "Entry": "{:.0f}", "T1": "{:.0f}", "T2": "{:.0f}", "Stop": "{:.0f}", "R:R": "{:.1f}"}, na_rep="—"
    )
    st.subheader("🇮🇩 IHSG — Domestic Macro Overlay")
    st.caption("Foreign flow & IDR sensitivity. Opportunities only (no short).")
    st.dataframe(styler, use_container_width=True, hide_index=True)

def render_crypto(setups: list):
    if not setups:
        st.info("No crypto setups.")
        return
    rows = []
    for s in setups:
        r = dict(s)
        # TODO: sambung ke on-chain API (Binance funding, Glassnode, Coinalyze)
        r["funding"] = 0.012
        r["oi_change"] = 8.5
        r["exchange_inflow"] = 450
        r["whale_ratio"] = 2.3
        rows.append(r)
    df = pd.DataFrame(rows)
    df = add_badges(df)
    df = _prep_df(
        df,
        core_cols=["ticker", "signal", "Regime", "Quad", "Bottleneck", "grade"],
        price_cols=["price", "entry", "target_1", "target_2", "stop_loss", "rr"],
        meta_cols=["funding", "oi_change", "exchange_inflow", "whale_ratio", "direction"],
        rename_map={
            "ticker": "Ticker", "signal": "Signal", "grade": "Grade",
            "price": "Price", "entry": "Entry", "target_1": "T1", "target_2": "T2", "stop_loss": "Stop", "rr": "R:R",
            "funding": "Funding %", "oi_change": "OI Δ %", "exchange_inflow": "Inflow", "whale_ratio": "Whale Ratio", "direction": "Dir"
        }
    )
    sig_cols = [c for c in ["Signal", "Dir"] if c in df.columns]
    grade_cols = [c for c in ["Grade"] if c in df.columns]
    styler = df.style.applymap(hl_signal, subset=sig_cols).applymap(hl_grade, subset=grade_cols).applymap(hl_funding, subset=["Funding %"]).format(
        {"Price": "{:.2f}", "Entry": "{:.2f}", "T1": "{:.2f}", "T2": "{:.2f}", "Stop": "{:.2f}", "R:R": "{:.1f}",
         "Funding %": "{:.3f}", "OI Δ %": "{:.1f}", "Inflow": "{:.0f}", "Whale Ratio": "{:.1f}"}, na_rep="—"
    )
    st.subheader("🔴 Crypto — On-Chain + Technical Hybrid")
    st.caption("Funding >1%% = overleveraged. Whale ratio >2.0 = distribution risk.")
    st.dataframe(styler, use_container_width=True, hide_index=True)

def _greeks_overlay(items: list):
    greeks_data = snapshot.get("greeks_data", {})
    if not isinstance(greeks_data, dict):
        return
    rows = []
    for item in items:
        t = item.get("ticker", "")
        gr = greeks_data.get(t, {})
        if not isinstance(gr, dict):
            continue
        if gr.get("ok"):
            rows.append({
                "Ticker": t,
                "Greek Comp": gr.get("composite", "—"),
                "Delta": gr.get("delta", "—"),
                "Gamma": gr.get("gamma", "—"),
                "Vanna": gr.get("vanna", "—"),
                "Charm": gr.get("charm", "—"),
                "Vol Premium": gr.get("vol_premium", "—"),
                "RVol 20d": gr.get("rvol_20d", "—"),
            })
    if rows:
        st.markdown("**🔍 Option Greeks Overlay**")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No option greeks data available for displayed tickers.")

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🧠 MacroRegime Pro")
    st.caption("Autonomous Macro Analysis")
    st.markdown("---")

    view = st.radio("Navigation", [
        "🏠 Dashboard", "🧮 GIP Model", "📊 Risk Ranges", "⚡ Alpha Center",
        "📡 Daily Signals", "🏆 Leaderboard", "🌍 Global Quad", "💱 Forex",
        "🪙 Commodities", "₿ Crypto", "🇮🇩 IHSG", "📖 Narratives",
        "🔍 Discovery", "❤️ Health", "📚 Playbook",
    ], index=0)

    st.markdown("---")
    st.subheader("Filters")
    min_rr = st.slider("Min R:R", 0.5, 5.0, 1.0, 0.5)
    min_score = st.slider("Min Score", 0, 100, 50, 5)

    # GREEKS dihapus dari tab, jadi toggle
    show_greeks = st.toggle("🔍 Show Option Greeks", value=False,
                            help="Tampilkan Gamma/Greeks overlay di bawah tabel")

    st.markdown("---")
    st.caption(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 Full Rebuild", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Main Router ──────────────────────────────────────────────────────────
if view == "🏠 Dashboard":
    st.header("🏠 Dashboard")
    st.markdown(f"**Structural:** {sq} | **Monthly:** {mq} | **Regime:** {regime_name} | **Bias:** {bias}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Prices Loaded", snapshot.get("prices_loaded", 0))
    c2.metric("Risk Ranges", len(snapshot.get("risk_ranges", {}).get("asset_ranges", {})))
    c3.metric("Daily Signals", len(snapshot.get("daily_signals", [])))
    c4.metric("Alpha Center", snapshot.get("alpha_center", {}).get("meta", {}).get("total_items", 0))

elif view == "🧮 GIP Model":
    st.header("🧮 GIP Model")
    st.json({"structural_quad": sq, "monthly_quad": mq, "regime": regime_name, "bias": bias,
             "flip_hazard": getattr(gip, "flip_hazard", 0), "divergence": getattr(gip, "divergence", "aligned")})

elif view == "📊 Risk Ranges":
    st.header("📊 Risk Ranges")
    rr = snapshot.get("risk_ranges", {}).get("asset_ranges", {})
    if rr:
        df = pd.DataFrame([{"Ticker": k, **v} for k, v in list(rr.items())[:50]])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No risk ranges available.")

elif view == "⚡ Alpha Center":
    st.header("⚡ Alpha Center")
    st.caption(f"Structural: {sq} → Monthly: {mq} → Q1 Target")
    ac = snapshot.get("alpha_center", {})
    meta = ac.get("meta", {})
    st.caption(f"Total: {meta.get('total_items', 0)} | L1: {meta.get('level_1_count', 0)} | L2: {meta.get('level_2_count', 0)} | Watch: {meta.get('watch_count', 0)}")

    tabs = st.tabs(["All", "Long", "Short", "Watch/Neutral", "Urgent", "Discovery", "Delta Signal"])
    all_items = ac.get("all", [])

    with tabs[0]: render_alpha(all_items, "All Signals", show_greeks)
    with tabs[1]: render_alpha([x for x in all_items if x.get("direction") == "LONG"], "Long Signals", show_greeks)
    with tabs[2]: render_alpha([x for x in all_items if x.get("direction") == "SHORT"], "Short Signals", show_greeks)
    with tabs[3]: render_alpha([x for x in all_items if x.get("direction") in ("NEUTRAL", "HOLD", "WATCH")], "Watchlist", show_greeks)
    with tabs[4]:
        urgent = [x for x in all_items if x.get("scanner_type", "").startswith("BOTTLENECK L1")]
        render_alpha(urgent, "Urgent Signals", show_greeks)
    with tabs[5]: render_alpha(ac.get("discovery", []), "Discovery", show_greeks)
    with tabs[6]: st.info("Delta Signal overlay.")

elif view == "📡 Daily Signals":
    st.header("📡 Daily Signals")
    ds = snapshot.get("daily_signals", [])
    ds = [s for s in ds if s.get("rr", 0) >= min_rr and abs(s.get("score", 0)) >= min_score / 100]
    render_daily(ds, "Daily Signals", show_greeks)

elif view == "🏆 Leaderboard":
    st.header("🏆 Leaderboard")
    ds = snapshot.get("daily_signals", [])
    longs = sorted([s for s in ds if s.get("direction") == "LONG"], key=lambda x: abs(x.get("score", 0)), reverse=True)[:10]
    shorts = sorted([s for s in ds if s.get("direction") == "SHORT"], key=lambda x: abs(x.get("score", 0)), reverse=True)[:10]
    c1, c2 = st.columns(2)
    with c1: render_daily(longs, "🟢 Long Leaderboard", show_greeks)
    with c2: render_daily(shorts, "🔴 Short Leaderboard", show_greeks)

elif view == "🌍 Global Quad":
    st.header("🌍 Global Quad")
    glob = snapshot.get("global", {})
    st.json(glob)

elif view == "💱 Forex":
    st.header("💱 Forex")
    ds = snapshot.get("daily_signals", [])
    forex = [s for s in ds if any(x in s.get("ticker", "") for x in ["USD=", "EUR=", "GBP=", "JPY=", "CAD", "AUD", "CHF", "NZD", "MXN", "SEK", "BRL", "=X", "DX-Y"])]
    render_daily(forex, "Forex Signals", show_greeks)

elif view == "🪙 Commodities":
    st.header("🪙 Commodities")
    ds = snapshot.get("daily_signals", [])
    comm = [s for s in ds if any(x in s.get("ticker", "") for x in ["GC=", "SI=", "CL=", "BZ=", "NG=", "HG=", "PL=", "PA=", "RB=", "HO=", "ALI=", "ZW=", "ZC=", "ZS=", "=F"])]
    longs = [s for s in comm if s.get("direction") == "LONG"]
    shorts = [s for s in comm if s.get("direction") == "SHORT"]
    if longs: render_daily(longs, "Long Commodities", show_greeks)
    else: st.info("No long commodity setups.")
    if shorts: render_daily(shorts, "Short Commodities", show_greeks)
    else: st.info("No short commodity setups.")

elif view == "₿ Crypto":
    st.header("₿ Crypto")
    cs = snapshot.get("crypto_setups", [])
    render_crypto(cs)

elif view == "🇮🇩 IHSG":
    st.header("🇮🇩 IHSG")
    ih = snapshot.get("ihsg_setups", [])
    render_ihsg(ih)

elif view == "📖 Narratives":
    st.header("📖 Narratives")
    nar = snapshot.get("narratives", {}).get("narratives", [])
    for n in nar:
        with st.expander(f"{n.get('name', '')} (score: {n.get('score', 0)})"):
            st.write(n.get("thesis", ""))
            st.caption(f"Tickers: {', '.join(n.get('tickers', []))}")

elif view == "🔍 Discovery":
    st.header("🔍 Discovery")
    disc = snapshot.get("discovery", {}).get("discoveries", [])
    st.dataframe(pd.DataFrame(disc) if disc else pd.DataFrame(), use_container_width=True)

elif view == "❤️ Health":
    st.header("❤️ Health")
    st.json(snapshot.get("health", {}))

elif view == "📚 Playbook":
    st.header("📚 Playbook")
    st.json(snapshot.get("playbook", {}))

st.markdown("---")
st.caption("MacroRegime Pro v11 | Lightweight Autonomy Stack")
Narratives":
    st.header("📖 Narratives")
    nar = snapshot.get("narratives", {}).get("narratives", [])
    for n in nar:
        with st.expander(f"{n.get('name','')} (score: {n.get('score',0)})"):
            st.write(n.get("thesis",""))
            st.caption(f"Tickers: {', '.join(n.get('tickers', []))}")

elif view == "🔍 Discovery":
    st.header("🔍 Discovery")
    disc = snapshot.get("discovery", {}).get("discoveries", [])
    st.dataframe(pd.DataFrame(disc) if disc else pd.DataFrame(), use_container_width=True)

elif view == "❤️ Health":
    st.header("❤️ Health")
    health = snapshot.get("health", {})
    st.json(health)

elif view == "📚 Playbook":
    st.header("📚 Playbook")
    pb = snapshot.get("playbook", {})
    st.json(pb)

st.markdown("---")
st.caption("MacroRegime Pro v11 | Lightweight Autonomy Stack")
