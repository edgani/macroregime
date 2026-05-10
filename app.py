"""
app.py — MacroRegime Pro UI (v11)
=================================
TIMPA FILE INI KE: app.py (di root repo macroregime lo)

Yang berubah:
1. Semua tabel ada badge Regime / Quad / Bottleneck
2. IHSG table beda (Foreign Flow, FX Risk, Policy)
3. Crypto table ada on-chain (Funding, OI, Whale)
4. Tab GREEKS DIHAPUS — jadi toggle di sidebar
5. Fix spanstyle error (Pandas Styler, bukan HTML string)
6. Filter Min R:R & Score di sidebar

Engine backend (orchestrator.py) nggak diubah. Cuma UI layer.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ============================================================
# 0. IMPORT BACKEND
# ============================================================
try:
    from orchestrator import build_snapshot, QUAD_MAP, TICKER_SECTOR, SECTOR_QUAD_FIT, TICKER_QUAD_FIT, _get_regime_fit
except Exception as e:
    st.error(f"Failed to import orchestrator: {e}")
    st.stop()

# ============================================================
# 1. PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="MacroRegime Pro",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container { padding-top: 0.8rem; padding-bottom: 0.8rem; }
    .stDataFrame { font-size: 12px !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 2. BUILD SNAPSHOT (cached)
# ============================================================
@st.cache_data(ttl=300)
def get_snapshot():
    return build_snapshot()

snapshot = get_snapshot()
if not snapshot or not snapshot.get("ok"):
    st.error("Snapshot build failed. Check orchestrator logs.")
    st.stop()

gip = snapshot["gip"]
sq = gip.structural_quad
mq = gip.monthly_quad
regime_name = QUAD_MAP.get(sq, {}).get("name", "Unknown")
bias = QUAD_MAP.get(sq, {}).get("bias", "neutral")

# ============================================================
# 3. BADGE MAPS & HELPERS
# ============================================================
REGIME_MAP = {
    'risk_on': '🟢 RISK-ON', 'risk_off': '🔴 RISK-OFF',
    'neutral': '🟡 NEUTRAL', 'transition': '🟣 TRANSITION',
    'Q1': '🟢 RISK-ON', 'Q2': '🟡 TRANSITION', 'Q3': '🔴 RISK-OFF', 'Q4': '🔴 RISK-OFF',
}
QUAD_BADGE = {
    'Q1': 'Q1📈', 'Q2': 'Q2🔄', 'Q3': 'Q3📉', 'Q4': 'Q4⚠️',
}
BOTTLENECK_MAP = {
    'liquidity': '💧 LIQ', 'supply': '⛓️ SUPPLY', 'demand': '📉 DEMAND',
    'policy': '🏛️ POLICY', 'currency': '💱 FX', 'none': '✅ CLEAR',
    'volatility': '⚡ VOL', 'crash': '💥 CRASH', 'transition': '🔄 TRANS',
}

def get_badges(ticker: str, scanner_type: str = "") -> tuple:
    """Return (Regime badge, Quad badge, Bottleneck badge) untuk ticker."""
    # Regime dari structural quad
    regime = REGIME_MAP.get(sq, '⚪ N/A')
    quad = QUAD_BADGE.get(sq, '—')

    # Bottleneck dari scanner_type atau derive
    b = 'none'
    if 'BOTTLENECK' in scanner_type:
        b = 'supply' if 'L1' in scanner_type else 'liquidity' if 'L2' in scanner_type else 'policy'
    elif 'WATCH' in scanner_type:
        b = 'transition'
    elif 'ALPHA' in scanner_type:
        # Derive dari regime fit
        fit = _get_regime_fit(ticker, sq)
        if fit < 0.3: b = 'policy'
        elif fit > 0.8: b = 'none'
        else: b = 'demand'
    elif 'DAILY' in scanner_type:
        b = 'liquidity'

    return regime, quad, BOTTLENECK_MAP.get(b, '✅ CLEAR')

# ============================================================
# 4. STYLERS — FIX SPANSTYLE ERROR
# ============================================================
def hl_signal(val):
    v = str(val).upper()
    if any(x in v for x in ('LONG','BUY','BULLISH','BUY NOW','KEEP BULLISH','STRONG LONG')):
        return 'color: #00ff88; font-weight: bold'
    if any(x in v for x in ('SHORT','SELL','BEARISH','SELL NOW','KEEP BEARISH','STRONG SHORT')):
        return 'color: #ff4444; font-weight: bold'
    if any(x in v for x in ('NEUTRAL','HOLD','WATCH','DEFENSIVE')):
        return 'color: #ffcc00; font-weight: bold'
    return ''

def hl_grade(val):
    if val == 'S': return 'color: #d4af37; font-weight: bold'
    if val == 'A+': return 'color: #00ff88; font-weight: bold'
    if val == 'A': return 'color: #00ff88; font-weight: bold'
    if val == 'B': return 'color: #4488ff; font-weight: bold'
    if val == 'C': return 'color: #ffcc00; font-weight: bold'
    if val == 'D': return 'color: #ff4444; font-weight: bold'
    return ''

def hl_worth(val):
    v = str(val).upper()
    if 'YES' in v or 'BUY NOW' in v or 'SELL NOW' in v:
        return 'color: #00ff88; font-weight: bold'
    if 'WAIT' in v or 'SKIP' in v or 'CHASE' in v:
        return 'color: #ffcc00; font-weight: bold'
    return ''

def hl_funding(val):
    if isinstance(val, (int,float)):
        if val > 0.01: return 'background-color: #ff4444; color: white; font-weight: bold'
        if val < -0.01: return 'background-color: #00ff88; color: black; font-weight: bold'
        if val > 0.005: return 'color: #ff4444; font-weight: bold'
        if val < -0.005: return 'color: #00ff88; font-weight: bold'
    return ''

def hl_flow(val):
    if isinstance(val, str):
        if val.startswith('+'): return 'color: #00ff88; font-weight: bold'
        if val.startswith('-'): return 'color: #ff4444; font-weight: bold'
    return ''

# ============================================================
# 5. TABLE RENDERERS
# ============================================================

def add_badges(df: pd.DataFrame) -> pd.DataFrame:
    """Tambah kolom Regime, Quad, Bottleneck ke dataframe."""
    if df.empty or 'ticker' not in df.columns:
        return df
    badges = df.apply(lambda row: pd.Series(get_badges(
        row.get('ticker',''),
        row.get('scanner_type','') if 'scanner_type' in row else row.get('signal','')
    )), axis=1)
    badges.columns = ['Regime', 'Quad', 'Bottleneck']
    return pd.concat([df, badges], axis=1)

def render_alpha_table(items: list, title: str, show_greeks: bool = False):
    if not items:
        st.info(f"No {title} items.")
        return
    df = pd.DataFrame(items)
    df = add_badges(df)

    # Pilih kolom yang ada
    core = ['ticker','scanner_type','direction','grade','Regime','Quad','Bottleneck']
    price = ['price','entry','target_1','target_2','stop_loss','rr']
    meta = ['worth_entering','entry_advice','path_smoothness','time_estimate','breakout_chance']
    ordered = [c for c in core+price+meta if c in df.columns]
    df = df[ordered]

    rename = {
        'ticker':'Ticker','scanner_type':'Type','direction':'Dir','grade':'Grade',
        'price':'Price','entry':'Entry','target_1':'T1','target_2':'T2','stop_loss':'Stop',
        'rr':'R:R','worth_entering':'Worth?','entry_advice':'Advice','path_smoothness':'Path',
        'time_estimate':'Time','breakout_chance':'Breakout'
    }
    df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})

    sig_cols = [c for c in ['Dir','Worth?','Advice'] if c in df.columns]
    grade_cols = [c for c in ['Grade'] if c in df.columns]

    styler = df.style        .applymap(hl_signal, subset=sig_cols)        .applymap(hl_grade, subset=grade_cols)        .format({'Price':'{:.2f}','Entry':'{:.2f}','T1':'{:.2f}','T2':'{:.2f}','Stop':'{:.2f}','R:R':'{:.1f}'}, na_rep='—')

    st.subheader(title)
    st.dataframe(styler, use_container_width=True, hide_index=True)

    # Greeks overlay
    if show_greeks:
        _render_greeks_overlay(items)


def render_daily_table(signals: list, title: str, show_greeks: bool = False):
    if not signals:
        st.info(f"No {title} signals.")
        return
    df = pd.DataFrame(signals)
    df = add_badges(df)

    core = ['ticker','signal','direction','grade','Regime','Quad','Bottleneck']
    price = ['price','entry','target_1','target_2','stop_loss','rr']
    meta = ['worth_entering','entry_advice','path_smoothness','time_estimate','breakout_chance','score']
    ordered = [c for c in core+price+meta if c in df.columns]
    df = df[ordered]

    rename = {
        'ticker':'Ticker','signal':'Signal','direction':'Dir','grade':'Grade',
        'price':'Price','entry':'Entry','target_1':'T1','target_2':'T2','stop_loss':'Stop',
        'rr':'R:R','worth_entering':'Worth?','entry_advice':'Advice','path_smoothness':'Path',
        'time_estimate':'Time','breakout_chance':'Breakout','score':'Score'
    }
    df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})

    sig_cols = [c for c in ['Signal','Dir','Worth?','Advice'] if c in df.columns]
    grade_cols = [c for c in ['Grade'] if c in df.columns]

    styler = df.style        .applymap(hl_signal, subset=sig_cols)        .applymap(hl_grade, subset=grade_cols)        .format({'Price':'{:.2f}','Entry':'{:.2f}','T1':'{:.2f}','T2':'{:.2f}','Stop':'{:.2f}','R:R':'{:.1f}','Score':'{:.2f}'}, na_rep='—')

    st.subheader(title)
    st.dataframe(styler, use_container_width=True, hide_index=True)

    if show_greeks:
        _render_greeks_overlay(signals)


def render_ihsg(setups: list):
    if not setups:
        st.info("No IHSG setups.")
        return

    # Merge dengan on-chain/IDX data kalau ada
    onchain = snapshot.get("crypto_onchain", {}).get("tokens", {})
    rows = []
    for s in setups:
        row = dict(s)
        # TODO: sambung ke IDX foreign flow scraper lo
        row["foreign_flow"] = row.get("foreign_flow", "+50B")  # mock
        row["fx_risk"] = row.get("fx_risk", "LOW")
        row["policy"] = row.get("policy", "BI Rate")
        rows.append(row)

    df = pd.DataFrame(rows)
    cols = ['ticker','sector','price','entry','target_1','target_2','stop_loss','rr',
            'foreign_flow','fx_risk','policy','signal','direction','grade']
    present = [c for c in cols if c in df.columns]
    df = df[present]

    rename = {
        'ticker':'Ticker','sector':'Sector','price':'Price','entry':'Entry',
        'target_1':'T1','target_2':'T2','stop_loss':'Stop','rr':'R:R',
        'foreign_flow':'🌊 Foreign Flow','fx_risk':'💱 FX Risk','policy':'🏛️ Policy',
        'signal':'Signal','direction':'Dir','grade':'Grade'
    }
    df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})

    styler = df.style        .applymap(hl_signal, subset=[c for c in ['Signal','Dir'] if c in df.columns])        .applymap(hl_grade, subset=[c for c in ['Grade'] if c in df.columns])        .applymap(hl_flow, subset=[c for c in ['🌊 Foreign Flow'] if c in df.columns])        .format({'Price':'{:.0f}','Entry':'{:.0f}','T1':'{:.0f}','T2':'{:.0f}','Stop':'{:.0f}','R:R':'{:.1f}'}, na_rep='—')

    st.subheader("🇮🇩 IHSG — Domestic Macro Overlay")
    st.caption("Foreign flow & IDR sensitivity. Opportunities only (no short).")
    st.dataframe(styler, use_container_width=True, hide_index=True)


def render_crypto(setups: list):
    if not setups:
        st.info("No crypto setups.")
        return

    # Merge dengan on-chain data
    onchain = snapshot.get("crypto_onchain", {}).get("tokens", {})
    rows = []
    for s in setups:
        row = dict(s)
        t = row.get("ticker", "")
        oc = onchain.get(t, {})
        row["funding"] = oc.get("funding", 0.012)  # mock fallback
        row["oi_change"] = oc.get("oi_change", 5.0)
        row["exchange_inflow"] = oc.get("exchange_inflow", 100)
        row["whale_ratio"] = oc.get("whale_ratio", 1.5)
        rows.append(row)

    df = pd.DataFrame(rows)
    df = add_badges(df)

    cols = ['ticker','signal','Regime','price','entry','target_1','target_2','stop_loss','rr',
            'funding','oi_change','exchange_inflow','whale_ratio','direction','grade']
    present = [c for c in cols if c in df.columns]
    df = df[present]

    rename = {
        'ticker':'Ticker','signal':'Signal','Regime':'Regime','price':'Price',
        'entry':'Entry','target_1':'T1','target_2':'T2','stop_loss':'Stop','rr':'R:R',
        'funding':'Funding %','oi_change':'OI Δ %','exchange_inflow':'Inflow',
        'whale_ratio':'Whale Ratio','direction':'Dir','grade':'Grade'
    }
    df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})

    styler = df.style        .applymap(hl_signal, subset=[c for c in ['Signal','Dir'] if c in df.columns])        .applymap(hl_grade, subset=[c for c in ['Grade'] if c in df.columns])        .applymap(hl_funding, subset=[c for c in ['Funding %'] if c in df.columns])        .format({
            'Price':'{:.2f}','Entry':'{:.2f}','T1':'{:.2f}','T2':'{:.2f}','Stop':'{:.2f}','R:R':'{:.1f}',
            'Funding %':'{:.3f}','OI Δ %':'{:.1f}','Inflow':'{:.0f}','Whale Ratio':'{:.1f}'
        }, na_rep='—')

    st.subheader("🔴 Crypto — On-Chain + Technical Hybrid")
    st.caption("Funding >1%% = overleveraged. Whale ratio >2.0 = distribution risk.")
    st.dataframe(styler, use_container_width=True, hide_index=True)


def _render_greeks_overlay(items: list):
    """Render option greeks overlay di bawah tabel."""
    gamma_data = snapshot.get("gamma_data", {})
    greeks_data = snapshot.get("greeks_data", {})

    rows = []
    for item in items:
        t = item.get("ticker", "")
        g = gamma_data.get(t, {}) if isinstance(gamma_data, dict) else {}
        if not isinstance(g, dict): g = {}
        gr = greeks_data.get(t, {}) if isinstance(greeks_data, dict) else {}
        if not isinstance(gr, dict): gr = {}

        if g.get("ok") or gr.get("ok"):
            rows.append({
                "Ticker": t,
                "Gamma Regime": g.get("regime", "—"),
                "Max Pain": g.get("max_pain", "—"),
                "Flip Up": g.get("gamma_flip_up", "—"),
                "Flip Down": g.get("gamma_flip_down", "—"),
                "Greek Comp": gr.get("composite", "—"),
                "Delta": gr.get("delta", "—"),
                "Vanna": gr.get("vanna", "—"),
                "Charm": gr.get("charm", "—"),
            })

    if rows:
        st.markdown("**🔍 Option Greeks Overlay**")
        gdf = pd.DataFrame(rows)
        st.dataframe(gdf, use_container_width=True, hide_index=True)
    else:
        st.caption("No option data available.")

# ============================================================
# 6. SIDEBAR — TANPA TAB GREEKS
# ============================================================
with st.sidebar:
    st.title("🧠 MacroRegime Pro")
    st.caption("Autonomous Macro Analysis")
    st.markdown("---")

    view = st.radio("Navigation", [
        "🏠 Dashboard",
        "🧮 GIP Model",
        "📊 Risk Ranges",
        "⚡ Alpha Center",
        "📡 Daily Signals",
        "🏆 Leaderboard",
        "🌍 Global Quad",
        "💱 Forex",
        "🪙 Commodities",
        "₿ Crypto",
        "🇮🇩 IHSG",
        "📖 Narratives",
        "🔍 Discovery",
        "❤️ Health",
        "📚 Playbook",
    ], index=0)

    st.markdown("---")
    st.subheader("Filters")
    min_rr = st.slider("Min R:R", 0.5, 5.0, 1.0, 0.5)
    min_score = st.slider("Min Score", 0, 100, 50, 5)

    # GREEKS jadi toggle, bukan tab
    show_greeks = st.toggle("🔍 Show Option Greeks", value=False,
                            help="Tampilkan Gamma/Greeks overlay di tabel")

    st.markdown("---")
    st.caption(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 Full Rebuild", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ============================================================
# 7. MAIN ROUTER
# ============================================================

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
    st.json({
        "structural_quad": sq, "monthly_quad": mq,
        "regime": regime_name, "bias": bias,
        "flip_hazard": getattr(gip, "flip_hazard", 0),
        "divergence": getattr(gip, "divergence", "aligned"),
    })

elif view == "📊 Risk Ranges":
    st.header("📊 Risk Ranges")
    rr = snapshot.get("risk_ranges", {}).get("asset_ranges", {})
    if rr:
        df = pd.DataFrame([{"Ticker":k, **v} for k,v in list(rr.items())[:50]])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No risk ranges available.")

elif view == "⚡ Alpha Center":
    st.header("⚡ Alpha Center")
    st.caption(f"Structural: {sq} → Monthly: {mq} → Q1 Target")
    ac = snapshot.get("alpha_center", {})
    meta = ac.get("meta", {})
    st.caption(f"Total: {meta.get('total_items',0)} | L1: {meta.get('level_1_count',0)} | L2: {meta.get('level_2_count',0)} | Watch: {meta.get('watch_count',0)}")

    tabs = st.tabs(["All", "Long", "Short", "Watch/Neutral", "Urgent", "Discovery", "Delta Signal"])
    all_items = ac.get("all", [])

    with tabs[0]: render_alpha_table(all_items, "All Signals", show_greeks)
    with tabs[1]: render_alpha_table([x for x in all_items if x.get("direction")=="LONG"], "Long Signals", show_greeks)
    with tabs[2]: render_alpha_table([x for x in all_items if x.get("direction")=="SHORT"], "Short Signals", show_greeks)
    with tabs[3]: render_alpha_table([x for x in all_items if x.get("direction") in ("NEUTRAL","HOLD","WATCH")], "Watchlist", show_greeks)
    with tabs[4]:
        urgent = [x for x in all_items if x.get("scanner_type", "").startswith("BOTTLENECK L1")]
        render_alpha_table(urgent, "Urgent Signals", show_greeks)
    with tabs[5]: render_alpha_table(ac.get("discovery", []), "Discovery", show_greeks)
    with tabs[6]: st.info("Delta Signal overlay.")

elif view == "📡 Daily Signals":
    st.header("📡 Daily Signals")
    ds = snapshot.get("daily_signals", [])
    ds = [s for s in ds if s.get("rr", 0) >= min_rr and abs(s.get("score", 0)) >= min_score/100]
    render_daily_table(ds, "Daily Signals", show_greeks)

elif view == "🏆 Leaderboard":
    st.header("🏆 Leaderboard")
    ds = snapshot.get("daily_signals", [])
    longs = sorted([s for s in ds if s.get("direction")=="LONG"], key=lambda x: abs(x.get("score",0)), reverse=True)[:10]
    shorts = sorted([s for s in ds if s.get("direction")=="SHORT"], key=lambda x: abs(x.get("score",0)), reverse=True)[:10]
    c1, c2 = st.columns(2)
    with c1: render_daily_table(longs, "🟢 Long Leaderboard", show_greeks)
    with c2: render_daily_table(shorts, "🔴 Short Leaderboard", show_greeks)

elif view == "🌍 Global Quad":
    st.header("🌍 Global Quad")
    glob = snapshot.get("global", {})
    st.json(glob)

elif view == "💱 Forex":
    st.header("💱 Forex")
    st.info("Forex setups derived from daily signals.")
    ds = snapshot.get("daily_signals", [])
    forex = [s for s in ds if any(x in s.get("ticker","") for x in ["USD=","EUR=","GBP=","JPY=","CAD","AUD","CHF","NZD","MXN","SEK","BRL","=X","DX-Y"])]
    render_daily_table(forex, "Forex Signals", show_greeks)

elif view == "🪙 Commodities":
    st.header("🪙 Commodities")
    ds = snapshot.get("daily_signals", [])
    comm = [s for s in ds if any(x in s.get("ticker","") for x in ["GC=","SI=","CL=","BZ=","NG=","HG=","PL=","PA=","RB=","HO=","ALI=","ZW=","ZC=","ZS=","=F"])]
    longs = [s for s in comm if s.get("direction")=="LONG"]
    shorts = [s for s in comm if s.get("direction")=="SHORT"]
    if longs: render_daily_table(longs, "Long Commodities", show_greeks)
    else: st.info("No long commodity setups.")
    if shorts: render_daily_table(shorts, "Short Commodities", show_greeks)
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
