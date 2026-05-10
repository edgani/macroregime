"""
================================================================================
TIMPA FILE INI KE: orchestrator.py (di root repo macroregime lo)
================================================================================
Cara pakai:
1. Backup dulu:  mv orchestrator.py orchestrator_old.py
2. Timpa:        copy file ini jadi orchestrator.py
3. Push deploy

Yang berubah dari orchestrator.py lama:
- Semua tabel sekarang ada badge Regime / Quad / Bottleneck
- IHSG table beda sendiri (ada Foreign Flow, FX Risk, Policy)
- Crypto table ada on-chain (Funding, OI, Whale Ratio)
- Tab Greeks dihapus, jadi toggle di sidebar (Show Option Greeks)
- Fix spanstyle error (pakai Pandas Styler, bukan HTML string)
- Filter Min R:R & Min Score di sidebar

Engine-engine yang ada di folder engines/ tetap dipakai. Kalau engine lo
export function lain, tinggal ganti nama call-nya di bagian "TODO" di bawah.
================================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# ============================================================
# 0. PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="MacroRegime Pro",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    .stDataFrame { font-size: 13px !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 1. IMPORT ENGINE LO (dari folder engines/)
# ============================================================
# Kalau engine lo export function beda, ganti nama call-nya di fetcher bawah.

try:
    from engines.auto_discovery_engine_v3 import run_discovery
except Exception as e:
    run_discovery = None
    print(f"[WARN] auto_discovery_engine_v3 not loaded: {e}")

try:
    from engines.regime_predictor_engine import predict_regime
except Exception as e:
    predict_regime = None
    print(f"[WARN] regime_predictor_engine not loaded: {e}")

try:
    from engines.leading_indicator_engine import get_leading_signals
except Exception as e:
    get_leading_signals = None
    print(f"[WARN] leading_indicator_engine not loaded: {e}")

try:
    from engines.price_cluster_engine_v3 import get_price_clusters
except Exception as e:
    get_price_clusters = None
    print(f"[WARN] price_cluster_engine_v3 not loaded: {e}")

try:
    from engines.news_nlp_engine_v3 import get_narrative_signals
except Exception as e:
    get_narrative_signals = None
    print(f"[WARN] news_nlp_engine_v3 not loaded: {e}")

try:
    from engines.feedback_loop_engine_v3 import get_feedback_scores
except Exception as e:
    get_feedback_scores = None
    print(f"[WARN] feedback_loop_engine_v3 not loaded: {e}")

try:
    from engines.edgar_scraper_engine import get_sec_signals
except Exception as e:
    get_sec_signals = None
    print(f"[WARN] edgar_scraper_engine not loaded: {e}")

try:
    from engines.supply_chain_graph_engine import get_supply_chain_signals
except Exception as e:
    get_supply_chain_signals = None
    print(f"[WARN] supply_chain_graph_engine not loaded: {e}")

# ============================================================
# 2. BADGE MAPS
# ============================================================
REGIME_MAP = {
    'risk_on': '🟢 RISK-ON', 'risk_off': '🔴 RISK-OFF',
    'neutral': '🟡 NEUTRAL', 'transition': '🟣 TRANSITION',
    'unknown': '⚪ N/A',
}
QUAD_MAP = {
    'Q1': 'Q1📈', 'Q2': 'Q2🔄', 'Q3': 'Q3📉', 'Q4': 'Q4⚠️', 'unknown': '—',
}
BOTTLENECK_MAP = {
    'liquidity': '💧 LIQ', 'supply': '⛓️ SUPPLY', 'demand': '📉 DEMAND',
    'policy': '🏛️ POLICY', 'currency': '💱 FX', 'none': '✅ CLEAR', 'unknown': '—',
}

def get_badges(ticker: str, regime_cache: dict) -> tuple:
    d = regime_cache.get(ticker, {})
    return (
        REGIME_MAP.get(d.get('regime', 'unknown'), '⚪ N/A'),
        QUAD_MAP.get(d.get('quad', 'unknown'), '—'),
        BOTTLENECK_MAP.get(d.get('bottleneck', 'unknown'), '—'),
    )

# ============================================================
# 3. FETCHERS — TODO: SAMBUNGIN ENGINE LO DI SINI
# ============================================================
# Ganti bagian "MOCK" dengan call ke engine lo.

@st.cache_data(ttl=300)
def fetch_alpha_signals() -> pd.DataFrame:
    """
    TODO: GANTI INI dengan call ke engine lo.
    Contoh: return run_discovery()
    """
    if run_discovery is not None:
        try:
            result = run_discovery()
            if isinstance(result, pd.DataFrame):
                return result
            if isinstance(result, list):
                return pd.DataFrame(result)
        except Exception as e:
            st.warning(f"Engine error (auto_discovery): {e}. Fallback ke mock.")

    # MOCK — hapus setelah engine tersambung
    return pd.DataFrame([
        {"ticker":"AAPL","signal":"LONG","direction":"LONG","grade":"A","price":175.0,"entry":172.5,"t1":185.0,"t2":195.0,"stop":168.0,"rr":2.1,"score":78,"advice":"BUY NOW — At buy zone","path":"Normal","time":"1-2 weeks","breakout":"Medium"},
        {"ticker":"TSLA","signal":"SHORT","direction":"SHORT","grade":"B","price":240.0,"entry":245.0,"t1":220.0,"t2":200.0,"stop":255.0,"rr":1.8,"score":62,"advice":"SELL NOW — At sell zone","path":"Normal","time":"2-4 weeks","breakout":"Low"},
        {"ticker":"NVDA","signal":"LONG","direction":"LONG","grade":"S","price":460.0,"entry":455.0,"t1":500.0,"t2":540.0,"stop":440.0,"rr":2.5,"score":92,"advice":"BUY NOW — At buy zone","path":"Normal","time":"1-2 weeks","breakout":"High"},
        {"ticker":"AMD","signal":"LONG","direction":"LONG","grade":"A","price":105.0,"entry":102.0,"t1":115.0,"t2":125.0,"stop":98.0,"rr":2.0,"score":75,"advice":"BUY NOW — At buy zone","path":"Normal","time":"1-2 weeks","breakout":"Medium"},
        {"ticker":"META","signal":"KEEP BULLISH","direction":"LONG","grade":"B","price":300.0,"entry":295.0,"t1":320.0,"t2":340.0,"stop":285.0,"rr":1.5,"score":58,"advice":"HOLD — At buy zone","path":"Normal","time":"2-4 weeks","breakout":"Low"},
    ])


@st.cache_data(ttl=300)
def fetch_regime_cache() -> dict:
    """
    TODO: GANTI INI dengan call ke engine lo.
    Contoh: return predict_regime()
    """
    if predict_regime is not None:
        try:
            return predict_regime()
        except Exception as e:
            st.warning(f"Engine error (regime): {e}. Fallback ke mock.")

    return {
        "AAPL": {"regime": "risk_on", "quad": "Q1", "bottleneck": "none"},
        "TSLA": {"regime": "transition", "quad": "Q3", "bottleneck": "policy"},
        "NVDA": {"regime": "risk_on", "quad": "Q1", "bottleneck": "supply"},
        "AMD":  {"regime": "risk_on", "quad": "Q1", "bottleneck": "none"},
        "META": {"regime": "neutral", "quad": "Q2", "bottleneck": "liquidity"},
    }


@st.cache_data(ttl=300)
def fetch_idx_data() -> pd.DataFrame:
    """
    TODO: GANTI INI dengan data IDX lo (scraper/API).
    """
    return pd.DataFrame([
        {"ticker":"BBCA.JK","sector":"Bank","worth":True,"price":9000,"entry":8900,"t1":9500,"t2":10000,"stop":8600,"rr":2.0,"foreign_flow":"+120B","fx_risk":"LOW","policy":"BI Rate Hold","advice":"BUY NOW — At buy zone","path":"Normal","time":"1-3 mo"},
        {"ticker":"BBRI.JK","sector":"Bank","worth":True,"price":5200,"entry":5100,"t1":5600,"t2":6000,"stop":4900,"rr":1.9,"foreign_flow":"+80B","fx_risk":"LOW","policy":"Dividend Season","advice":"BUY NOW — At buy zone","path":"Normal","time":"1-3 mo"},
        {"ticker":"ITMG.JK","sector":"Coal","worth":True,"price":24000,"entry":23500,"t1":26000,"t2":28000,"stop":22500,"rr":2.2,"foreign_flow":"-45B","fx_risk":"MED","policy":"Export Ban Risk","advice":"BUY NOW — At buy zone","path":"Normal","time":"1-3 mo"},
        {"ticker":"TLKM.JK","sector":"Telco","worth":True,"price":3800,"entry":3750,"t1":4000,"t2":4200,"stop":3600,"rr":1.5,"foreign_flow":"+30B","fx_risk":"LOW","policy":"5G Auction","advice":"BUY NOW — At buy zone","path":"Normal","time":"1-3 mo"},
    ])


@st.cache_data(ttl=300)
def fetch_crypto_data() -> pd.DataFrame:
    """
    TODO: GANTI INI dengan crypto engine + on-chain API lo.
    """
    return pd.DataFrame([
        {"ticker":"BTC-USD","signal":"SHORT","price":64000,"entry":65000,"t1":60000,"t2":55000,"stop":67000,"rr":2.0,"funding":0.012,"oi_change":8.5,"exchange_inflow":450,"whale_ratio":2.3,"advice":"SELL NOW — At sell zone","path":"Normal","time":"1-2 months","breakout":"Medium"},
        {"ticker":"ETH-USD","signal":"SHORT","price":3450,"entry":3500,"t1":3200,"t2":3000,"stop":3600,"rr":1.8,"funding":0.008,"oi_change":5.2,"exchange_inflow":120,"whale_ratio":1.8,"advice":"SELL NOW — At sell zone","path":"Normal","time":"1-2 months","breakout":"Low"},
        {"ticker":"SOL-USD","signal":"SHORT","price":145,"entry":150,"t1":130,"t2":115,"stop":155,"rr":1.6,"funding":0.015,"oi_change":12.0,"exchange_inflow":80,"whale_ratio":2.1,"advice":"SELL NOW — At sell zone","path":"Normal","time":"1-2 months","breakout":"Medium"},
    ])


@st.cache_data(ttl=300)
def fetch_forex_data() -> pd.DataFrame:
    """TODO: GANTI dengan forex engine lo."""
    return pd.DataFrame([
        {"ticker":"EURUSD=X","signal":"LONG","price":1.09,"entry":1.088,"t1":1.10,"t2":1.11,"stop":1.08,"rr":2.0,"advice":"BUY NOW — At buy zone","path":"Normal","time":"1-2 weeks","breakout":"Low"},
        {"ticker":"USDJPY=X","signal":"LONG","price":156.0,"entry":155.5,"t1":158.0,"t2":160.0,"stop":154.0,"rr":1.5,"advice":"BUY NOW — At buy zone","path":"Normal","time":"1-2 months","breakout":"Low"},
    ])


@st.cache_data(ttl=300)
def fetch_commodity_data() -> pd.DataFrame:
    """TODO: GANTI dengan commodity engine lo."""
    return pd.DataFrame([
        {"ticker":"GC=F","signal":"SHORT","price":2300,"entry":2320,"t1":2250,"t2":2200,"stop":2350,"rr":1.8,"advice":"SELL NOW — At sell zone","path":"Normal","time":"1-3 months","breakout":"Low"},
    ])


@st.cache_data(ttl=300)
def fetch_option_chain(ticker: str) -> dict:
    """
    TODO: GANTI dengan option data provider lo (yfinance, CBOE, dll).
    Return dict: {iv_rank, pc_ratio, max_pain, nearest_delta, nearest_gamma, nearest_theta, nearest_vega}
    """
    return {
        "iv_rank": 72, "pc_ratio": 0.85, "max_pain": 175,
        "nearest_delta": 0.55, "nearest_gamma": 0.03,
        "nearest_theta": -0.12, "nearest_vega": 0.25,
    }


# ============================================================
# 4. STYLERS — FIX SPANSTYLE ERROR
# ============================================================
def hl_signal(val):
    v = str(val).upper()
    if v in ('LONG','BUY NOW','KEEP BULLISH','BUY'): return 'color: #00ff88; font-weight: bold'
    if v in ('SHORT','SELL NOW','KEEP BEARISH','SELL'): return 'color: #ff4444; font-weight: bold'
    if v in ('NEUTRAL','HOLD','WATCH'): return 'color: #ffcc00; font-weight: bold'
    return ''

def hl_grade(val):
    if val == 'S': return 'color: #d4af37; font-weight: bold'
    if val == 'A': return 'color: #00ff88; font-weight: bold'
    if val == 'B': return 'color: #4488ff; font-weight: bold'
    if val == 'C': return 'color: #ffcc00; font-weight: bold'
    if val == 'D': return 'color: #ff4444; font-weight: bold'
    return ''

def hl_funding(val):
    if isinstance(val, (int,float)):
        if val > 0.01:  return 'background-color: #ff4444; color: white; font-weight: bold'
        if val < -0.01: return 'background-color: #00ff88; color: black; font-weight: bold'
        if val > 0.005:  return 'color: #ff4444; font-weight: bold'
        if val < -0.005: return 'color: #00ff88; font-weight: bold'
    return ''

def hl_iv(val):
    if isinstance(val, (int,float)):
        if val > 70: return 'color: #ff4444; font-weight: bold'
        if val < 30: return 'color: #00ff88; font-weight: bold'
    return ''

def hl_worth(val):
    if val == True or str(val).upper() == 'YES': return 'color: #00ff88; font-weight: bold'
    return 'color: #ff4444; font-weight: bold'

def hl_flow(val):
    if isinstance(val, str):
        if val.startswith('+'): return 'color: #00ff88; font-weight: bold'
        if val.startswith('-'): return 'color: #ff4444; font-weight: bold'
    return ''

# ============================================================
# 5. TABLE RENDERERS
# ============================================================

def render_global(df: pd.DataFrame, regime_cache: dict, title: str, show_greeks: bool = False):
    if df.empty:
        st.info(f"No {title} signals.")
        return

    # Tambah badge Regime / Quad / Bottleneck
    badges = df['ticker'].apply(lambda t: pd.Series(get_badges(t, regime_cache)))
    badges.columns = ['Regime', 'Quad', 'Bottleneck']
    df = pd.concat([df, badges], axis=1)

    # Urutkan kolom
    core = ['ticker','signal','direction','grade','Regime','Quad','Bottleneck']
    price = ['price','entry','t1','t2','stop','rr']
    meta = ['advice','path','time','breakout']
    ordered = [c for c in core+price+meta if c in df.columns]
    df = df[ordered]

    # Rename
    rename = {
        'ticker':'Ticker','signal':'Signal','direction':'Dir','grade':'Grade',
        'price':'Price','entry':'Entry','t1':'T1','t2':'T2','stop':'Stop','rr':'R:R',
        'advice':'Entry Advice','path':'Path','time':'Time','breakout':'Breakout'
    }
    df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})

    # Styler
    sig_cols = [c for c in ['Signal','Dir','Entry Advice'] if c in df.columns]
    grade_cols = [c for c in ['Grade'] if c in df.columns]

    styler = df.style        .applymap(hl_signal, subset=sig_cols)        .applymap(hl_grade, subset=grade_cols)        .format({'Price':'{:.2f}','Entry':'{:.2f}','T1':'{:.2f}','T2':'{:.2f}','Stop':'{:.2f}','R:R':'{:.1f}'}, na_rep='—')

    st.subheader(title)
    st.dataframe(styler, use_container_width=True, hide_index=True)

    # Option Greeks OVERLAY (bukan tab terpisah)
    if show_greeks and 'Ticker' in df.columns:
        st.markdown("---")
        st.markdown("**🔍 Option Greeks Overlay**")
        rows = []
        for _, row in df.iterrows():
            tkr = row['Ticker']
            try:
                opt = fetch_option_chain(tkr)
                rows.append({
                    'Ticker': tkr, 'IV Rank': opt['iv_rank'], 'P/C Ratio': opt['pc_ratio'],
                    'Max Pain': opt['max_pain'], 'Delta': opt['nearest_delta'],
                    'Gamma': opt['nearest_gamma'], 'Theta': opt['nearest_theta'], 'Vega': opt['nearest_vega'],
                })
            except Exception:
                pass
        if rows:
            gdf = pd.DataFrame(rows)
            gst = gdf.style.applymap(hl_iv, subset=['IV Rank']).format({
                'IV Rank':'{:.0f}%','P/C Ratio':'{:.2f}','Max Pain':'${:.0f}',
                'Delta':'{:.2f}','Gamma':'{:.3f}','Theta':'{:.2f}','Vega':'{:.2f}'
            })
            st.dataframe(gst, use_container_width=True, hide_index=True)
        else:
            st.caption("No option data for displayed tickers.")


def render_idx(df: pd.DataFrame):
    if df.empty:
        st.info("No IDX signals.")
        return

    cols = ['ticker','sector','worth','price','entry','t1','t2','stop','rr',
            'foreign_flow','fx_risk','policy','advice','path','time']
    present = [c for c in cols if c in df.columns]
    df = df[present]
    rename = {
        'ticker':'Ticker','sector':'Sector','worth':'Worth?','price':'Price',
        'entry':'Entry','t1':'T1','t2':'T2','stop':'Stop','rr':'R:R',
        'foreign_flow':'🌊 Foreign Flow','fx_risk':'💱 FX Risk','policy':'🏛️ Policy',
        'advice':'Entry Advice','path':'Path','time':'Time'
    }
    df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})

    styler = df.style        .applymap(hl_worth, subset=['Worth?'])        .applymap(hl_signal, subset=['Entry Advice'])        .applymap(hl_flow, subset=['🌊 Foreign Flow'])        .format({'Price':'{:.0f}','Entry':'{:.0f}','T1':'{:.0f}','T2':'{:.0f}','Stop':'{:.0f}','R:R':'{:.1f}'}, na_rep='—')

    st.subheader("🇮🇩 IHSG — Domestic Macro Overlay")
    st.caption("Foreign flow & IDR sensitivity. Opportunities only (no short).")
    st.dataframe(styler, use_container_width=True, hide_index=True)


def render_crypto(df: pd.DataFrame, regime_cache: dict):
    if df.empty:
        st.info("No crypto signals.")
        return

    badges = df['ticker'].apply(lambda t: pd.Series(get_badges(t, regime_cache)))
    badges.columns = ['Regime','Quad','Bottleneck']
    df = pd.concat([df, badges], axis=1)

    cols = ['ticker','signal','Regime','price','entry','t1','t2','stop','rr',
            'funding','oi_change','exchange_inflow','whale_ratio','advice','path','time','breakout']
    present = [c for c in cols if c in df.columns]
    df = df[present]
    rename = {
        'ticker':'Ticker','signal':'Signal','Regime':'Regime','price':'Price',
        'entry':'Entry','t1':'T1','t2':'T2','stop':'Stop','rr':'R:R',
        'funding':'Funding %','oi_change':'OI Δ %','exchange_inflow':'Inflow',
        'whale_ratio':'Whale Ratio','advice':'Entry Advice','path':'Path',
        'time':'Time','breakout':'Breakout'
    }
    df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})

    styler = df.style        .applymap(hl_signal, subset=['Signal','Entry Advice'])        .applymap(hl_funding, subset=['Funding %'])        .format({
            'Price':'{:.2f}','Entry':'{:.2f}','T1':'{:.2f}','T2':'{:.2f}','Stop':'{:.2f}','R:R':'{:.1f}',
            'Funding %':'{:.3f}','OI Δ %':'{:.1f}','Inflow':'{:.0f}','Whale Ratio':'{:.1f}'
        }, na_rep='—')

    st.subheader("🔴 Crypto — On-Chain + Technical Hybrid")
    st.caption("Funding >1%% = overleveraged. Whale ratio >2.0 = distribution risk.")
    st.dataframe(styler, use_container_width=True, hide_index=True)


# ============================================================
# 6. SIDEBAR
# ============================================================
with st.sidebar:
    st.title("🧠 MacroRegime Pro")
    st.caption("Autonomous Macro Analysis")
    st.markdown("---")

    view = st.radio("Navigation", [
        "🎯 Alpha Center","📡 Daily Signals","🏆 Leaderboard","🌍 Global Quad",
        "💱 Forex","🪙 Commodities","₿ Crypto","🇮🇩 ID Indonesia",
        "📊 Discovery","📈 Narratives","🎓 Playbook",
    ], index=0)

    st.markdown("---")
    st.subheader("Filters")
    min_rr = st.slider("Min R:R", 0.5, 5.0, 1.0, 0.5)
    min_score = st.slider("Min Score", 0, 100, 50, 5)

    # GREECS jadi toggle, bukan tab kosong
    show_greeks = st.toggle("🔍 Show Option Greeks", value=False,
                            help="Tampilkan IV Rank, Delta, Gamma, Theta, Vega")

    st.markdown("---")
    st.caption(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
    st.button("🔄 Full Rebuild", use_container_width=True)


# ============================================================
# 7. MAIN ROUTER
# ============================================================
regime_cache = fetch_regime_cache()

if view == "🎯 Alpha Center":
    st.header("🎯 Alpha Center")
    st.caption("Structural: Q3 → Monthly: Q2 → Q1 Target")
    tabs = st.tabs(["All","Long","Short","Watch/Neutral","Urgent","Discovery","Delta Signal"])
    df = fetch_alpha_signals()
    df = df[(df['rr'] >= min_rr) & (df['score'] >= min_score)]

    with tabs[0]: render_global(df, regime_cache, "All Signals", show_greeks)
    with tabs[1]: render_global(df[df['signal'].str.upper()=='LONG'], regime_cache, "Long Signals", show_greeks)
    with tabs[2]: render_global(df[df['signal'].str.upper()=='SHORT'], regime_cache, "Short Signals", show_greeks)
    with tabs[3]: render_global(df[df['signal'].str.upper().isin(['NEUTRAL','WATCH'])], regime_cache, "Watchlist", show_greeks)
    with tabs[4]:
        urgent = df[df['score'] >= 85]
        render_global(urgent, regime_cache, "Urgent Signals", show_greeks)
    with tabs[5]: st.info("Discovery engine output.")
    with tabs[6]: st.info("Delta Signal overlay.")

elif view == "📡 Daily Signals":
    st.header("📡 Daily Signals")
    df = fetch_alpha_signals()
    df = df[(df['rr'] >= min_rr) & (df['score'] >= min_score)]
    render_global(df, regime_cache, "Daily Signals", show_greeks)

elif view == "🏆 Leaderboard":
    st.header("🏆 Leaderboard")
    st.caption("High-conviction ideas. Macro + Risk Range + Off + On-chain combined.")
    long_df = fetch_alpha_signals()
    long_df = long_df[long_df['signal'].str.upper()=='LONG'].sort_values('score', ascending=False).head(10)
    short_df = fetch_alpha_signals()
    short_df = short_df[short_df['signal'].str.upper()=='SHORT'].sort_values('score', ascending=False).head(10)
    c1, c2 = st.columns(2)
    with c1: render_global(long_df, regime_cache, "🟢 Long Leaderboard", show_greeks)
    with c2: render_global(short_df, regime_cache, "🔴 Short Leaderboard", show_greeks)

elif view == "🌍 Global Quad":
    st.header("🌍 Global Quad")
    st.info("Quad rotation heatmap. (Connect regime_predictor_engine output here)")

elif view == "💱 Forex":
    st.header("💱 Forex Setups")
    st.caption("COT + FX Greeks + Risk Ranges. Sorted by R:R.")
    df = fetch_forex_data()
    df = df[df['rr'] >= min_rr]
    render_global(df, regime_cache, "Long FX", show_greeks)

elif view == "🪙 Commodities":
    st.header("🪙 Commodities")
    long_df = fetch_commodity_data()
    long_df = long_df[long_df['signal'].str.upper()=='LONG']
    short_df = fetch_commodity_data()
    short_df = short_df[short_df['signal'].str.upper()=='SHORT']
    if not long_df.empty: render_global(long_df, regime_cache, "Long Commodities", show_greeks)
    else: st.info("No long commodity setups.")
    if not short_df.empty: render_global(short_df, regime_cache, "Short Commodities", show_greeks)
    else: st.info("No short commodity setups.")

elif view == "₿ Crypto":
    st.header("₿ Crypto")
    df = fetch_crypto_data()
    df = df[df['rr'] >= min_rr]
    render_crypto(df, regime_cache)

elif view == "🇮🇩 ID Indonesia":
    st.header("🇮🇩 ID Indonesia (IHSG)")
    df = fetch_idx_data()
    render_idx(df)

elif view == "📊 Discovery":
    st.header("📊 Discovery")
    st.info("Auto-discovery engine output.")

elif view == "📈 Narratives":
    st.header("📈 Narratives")
    st.info("Macro narrative tracker.")

elif view == "🎓 Playbook":
    st.header("🎓 Playbook")
    st.info("Strategy playbook & backtest rules.")

st.markdown("---")
st.caption("MacroRegime Pro v11 | Lightweight Autonomy Stack")
