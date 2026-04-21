# ═══════════════════════════════════════════════════════════════════════════════
#  MACRO REGIME DASHBOARD — Full Reconstruction v1.0
#  Streamlit app with FRED + yfinance data, Hedgeye-style Quad regime engine
# ═══════════════════════════════════════════════════════════════════════════════

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime, timedelta

# ─── CONFIG ───────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Macro Regime Dashboard", layout="wide", initial_sidebar_state="collapsed")

FRED_API_KEY = "5fbe5dc4c8a5fbb109c4809463a1c27f"
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _h(html: str):
    """Raw HTML renderer."""
    st.markdown(html, unsafe_allow_html=True)

def fred_fetch(series_id: str, limit: int = 500) -> pd.Series:
    """Fetch FRED series via REST. Returns Series indexed by date."""
    try:
        params = {
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        }
        r = requests.get(FRED_BASE, params=params, timeout=30)
        data = r.json()
        obs = data.get("observations", [])
        if not obs:
            return pd.Series(dtype=float)
        df = pd.DataFrame(obs)
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"]).set_index("date").sort_index()
        return df["value"]
    except Exception:
        return pd.Series(dtype=float)

@st.cache_data(ttl=1800)
def load_all_fred() -> dict:
    """Load core FRED series for regime classification."""
    series_map = {
        "GDPC1": "Real GDP",
        "INDPRO": "Industrial Production",
        "CPIAUCSL": "CPI",
        "PCEPI": "PCE",
        "UNRATE": "Unemployment",
        "PAYEMS": "Nonfarm Payrolls",
        "T10Y2Y": "Yield Curve (10Y-2Y)",
        "DFF": "Fed Funds",
        "RSXFS": "Retail Sales",
    }
    out = {}
    loaded = 0
    missing = []
    for sid, name in series_map.items():
        s = fred_fetch(sid)
        if len(s) > 10:
            out[sid] = s
            loaded += 1
        else:
            missing.append(sid)
    return {
        "data": out,
        "meta": {
            "loaded": loaded,
            "missing": len(missing),
            "missing_keys": missing,
            "api_key_present": bool(FRED_API_KEY),
            "real_share": loaded / (loaded + len(missing)) if (loaded + len(missing)) > 0 else 0,
        }
    }

def yf_fetch(tickers_list: list, period="6mo", interval="1d") -> dict:
    """Bulk fetch yfinance prices. Returns dict {ticker: Series}."""
    out = {}
    if not tickers_list:
        return out
    try:
        data = yf.download(tickers_list, period=period, interval=interval, progress=False, auto_adjust=True)
        if len(tickers_list) == 1:
            tk = tickers_list[0]
            s = data["Close"] if isinstance(data, pd.DataFrame) else data
            out[tk] = pd.Series(s.values if hasattr(s, "values") else s, index=s.index if hasattr(s, "index") else pd.DatetimeIndex([])).dropna()
        else:
            for tk in tickers_list:
                try:
                    s = data["Close"][tk].dropna()
                    out[tk] = s
                except Exception:
                    # Fallback single fetch
                    try:
                        t = yf.Ticker(tk)
                        hist = t.history(period=period, interval=interval, auto_adjust=True)
                        out[tk] = hist["Close"].dropna()
                    except Exception:
                        pass
    except Exception:
        # Fallback per-ticker
        for tk in tickers_list:
            try:
                t = yf.Ticker(tk)
                hist = t.history(period=period, interval=interval, auto_adjust=True)
                out[tk] = hist["Close"].dropna()
            except Exception:
                pass
    return out

# ═══════════════════════════════════════════════════════════════════════════════
#  REGIME ENGINE (Hedgeye-style Quad)
# ═══════════════════════════════════════════════════════════════════════════════

def calc_momentum(series: pd.Series, lookback: int = 12) -> float:
    """Normalized momentum score (-1 to 1)."""
    if series is None or len(series) < lookback + 3:
        return 0.0
    recent = series.iloc[-lookback:].mean()
    older = series.iloc[-(lookback * 2):-lookback].mean()
    if older == 0:
        return 0.0
    raw = (recent - older) / abs(older)
    return float(np.tanh(raw * 3))  # squash to [-1, 1]

def calc_roc(series: pd.Series, periods: int = 12) -> float:
    """Rate of change."""
    if series is None or len(series) < periods + 1:
        return 0.0
    return float((series.iloc[-1] / series.iloc[-(periods + 1)] - 1))

def classify_quad(growth_score: float, inflation_score: float) -> str:
    """
    growth_score > 0  → accelerating
    growth_score < 0  → decelerating
    inflation_score > 0 → accelerating
    inflation_score < 0 → decelerating
    
    Q1: G↑ I↓  |  Q2: G↑ I↑  |  Q3: G↓ I↑  |  Q4: G↓ I↓
    """
    if growth_score >= 0 and inflation_score <= 0:
        return "Q1"
    elif growth_score >= 0 and inflation_score > 0:
        return "Q2"
    elif growth_score < 0 and inflation_score > 0:
        return "Q3"
    else:
        return "Q4"

def softmax_probs(g: float, i: float, temp: float = 1.0) -> dict:
    """Convert raw scores to quadrant probabilities."""
    quads = {
        "Q1": np.exp(( g * 1.5 - i * 1.5) / temp),
        "Q2": np.exp(( g * 1.5 + i * 1.5) / temp),
        "Q3": np.exp((-g * 1.5 + i * 1.5) / temp),
        "Q4": np.exp((-g * 1.5 - i * 1.5) / temp),
    }
    total = sum(quads.values())
    return {k: v / total for k, v in quads.items()}

def run_regime(fred: dict) -> dict:
    """Full regime calculation."""
    d = fred.get("data", {})
    
    # ── Growth proxies ──
    g_scores = []
    if "INDPRO" in d:
        g_scores.append(calc_momentum(d["INDPRO"], 6))
    if "PAYEMS" in d:
        g_scores.append(calc_momentum(d["PAYEMS"], 6))
    if "RSXFS" in d:
        g_scores.append(calc_momentum(d["RSXFS"], 3))
    if "GDPC1" in d:
        g_scores.append(calc_roc(d["GDPC1"], 4))
    
    # ── Inflation proxies ──
    i_scores = []
    if "CPIAUCSL" in d:
        # Use 2nd derivative (acceleration) of YoY CPI
        cpi = d["CPIAUCSL"]
        if len(cpi) > 24:
            yoy = cpi.pct_change(periods=12) * 100
            # momentum of YoY = acceleration/deceleration
            i_scores.append(calc_momentum(yoy.dropna(), 6))
    if "PCEPI" in d:
        pce = d["PCEPI"]
        if len(pce) > 24:
            yoy = pce.pct_change(periods=12) * 100
            i_scores.append(calc_momentum(yoy.dropna(), 6))
    
    g = np.mean(g_scores) if g_scores else 0.0
    i = np.mean(i_scores) if i_scores else 0.0
    
    # Structural = longer lookback (already baked in via 12-mo momentum)
    # Monthly = shorter, more responsive
    g_monthly = np.mean([calc_momentum(d.get(k, pd.Series(dtype=float)), 3) for k in ["INDPRO", "PAYEMS"] if k in d]) if any(k in d for k in ["INDPRO", "PAYEMS"]) else g
    i_monthly = i  # inflation doesn't change as fast; keep same or use shorter if data available
    
    s_quad = classify_quad(g, i)
    m_quad = classify_quad(g_monthly, i_monthly)
    
    # Global = simplified; in production this would aggregate EU, CN, EM data
    # For now we mirror structural with slight dampening
    g_global = g * 0.8
    i_global = i * 0.9
    global_quad = classify_quad(g_global, i_global)
    
    s_probs = softmax_probs(g, i, temp=0.8)
    m_probs = softmax_probs(g_monthly, i_monthly, temp=0.6)
    
    return {
        "structural_quad": s_quad,
        "monthly_quad": m_quad,
        "global_quad": global_quad,
        "structural_probs": s_probs,
        "monthly_probs": m_probs,
        "growth_score": round(g, 3),
        "inflation_score": round(i, 3),
        "growth_scores_detail": g_scores,
        "inflation_scores_detail": i_scores,
    }

# ═══════════════════════════════════════════════════════════════════════════════
#  TICKER UNIVERSE
# ═══════════════════════════════════════════════════════════════════════════════

TICKER_UNIVERSE = {
    "us_longs":   ["SPY", "QQQ", "IWM", "XLK", "SMH"],
    "us_shorts":  ["XLU", "XLRE", "TLT"],
    "ihsg_buys":  ["^JKSE", "BBCA.JK", "BBRI.JK", "ASII.JK", "TLKM.JK", "ADRO.JK", "ANTM.JK", "PTBA.JK", "ITMG.JK", "INCO.JK", "KLBF.JK"],
    "fx_longs":   ["UUP", "USDJPY=X"],
    "fx_shorts":  ["EURUSD=X", "AUDUSD=X"],
    "commodity_longs": ["GC=F", "HG=F", "URA"],
    "commodity_shorts": ["NG=F"],
    "crypto_longs": ["BTC-USD", "ETH-USD"],
    "crypto_shorts": [],
}

ALL_TICKERS = list({t for lst in TICKER_UNIVERSE.values() for t in lst})

# ═══════════════════════════════════════════════════════════════════════════════
#  BOTTLENECK & NARRATIVE STUBS (functional placeholders)
# ═══════════════════════════════════════════════════════════════════════════════

def discover_bottlenecks(prices: dict) -> dict:
    """Scan for tickers showing early/building/mature bottleneck patterns."""
    basket = []
    for tk, s in prices.items():
        if s is None or len(s) < 30:
            continue
        ret21 = (s.iloc[-1] / s.iloc[-22] - 1) if len(s) >= 22 else 0
        ret63 = (s.iloc[-1] / s.iloc[-64] - 1) if len(s) >= 64 else 0
        vol = s.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252) if len(s) > 20 else 0
        
        # Simple heuristic: strong momentum + increasing vol = building bottleneck
        score = abs(ret21) * 2 + abs(ret63) - vol
        if abs(ret21) > 0.03 or abs(ret63) > 0.08:
            stage = "early" if abs(ret21) < 0.05 else "building" if abs(ret21) < 0.10 else "mature"
            basket.append({
                "ticker": tk,
                "sector": "",
                "bottleneck_score": round(score, 2),
                "stage": stage,
            })
    basket.sort(key=lambda x: abs(x["bottleneck_score"]), reverse=True)
    return {
        "summary": f"{len(basket)} bottleneck(s) detected",
        "front_run_basket": basket[:15],
    }

def discover_narratives(prices: dict, regime: dict) -> dict:
    """Map current regime to active narratives."""
    # Predefined narrative map based on regime
    quad = regime.get("structural_quad", "Q1")
    narratives = []
    
    if quad in ["Q1", "Q2"]:
        narratives.append({
            "name": "Growth Acceleration",
            "primary_beneficiaries": ["XLK", "SMH", "XLI", "IWM"],
            "primary_stressed": ["XLU", "TLT"],
        })
    if quad in ["Q2", "Q3"]:
        narratives.append({
            "name": "Inflation Persistence",
            "primary_beneficiaries": ["XLE", "GC=F", "HG=F", "URA"],
            "primary_stressed": ["XLY", "XLRE"],
        })
    if quad in ["Q3", "Q4"]:
        narratives.append({
            "name": "Defensive Rotation",
            "primary_beneficiaries": ["XLP", "XLV", "GLD", "TLT"],
            "primary_stressed": ["XLE", "XLK", "IWM"],
        })
    if quad == "Q4":
        narratives.append({
            "name": "Rate Cut Expectations",
            "primary_beneficiaries": ["XLRE", "XLU", "TLT", "QQQ"],
            "primary_stressed": ["UUP", "XLF"],
        })
    
    return {"active_narratives": narratives}

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # ── Load data ──
    fred_bundle = load_all_fred()
    fred_data = fred_bundle["data"]
    fred_meta = fred_bundle["meta"]
    
    with st.spinner("Loading market data…"):
        prices = yf_fetch(ALL_TICKERS, period="6mo", interval="1d")
    
    regime = run_regime(fred_bundle)
    
    # ── Build snap & tickers ──
    snap = {
        "prices": prices,
        "regime_transition": {
            "front_run_window": "21 days",
            "structural_quad": regime["structural_quad"],
            "monthly_quad": regime["monthly_quad"],
            "global_quad": regime["global_quad"],
        },
        "bottleneck_discovery": discover_bottlenecks(prices),
        "narrative_discovery": discover_narratives(prices, regime),
        "fred_meta": fred_meta,
    }
    
    tickers = TICKER_UNIVERSE
    q = regime
    structural_quad = regime["structural_quad"]
    monthly_quad = regime["monthly_quad"]
    
    # ═══════════════════════════════════════════════════════════════════════════
    #  TABS
    # ═══════════════════════════════════════════════════════════════════════════
    tabs = st.tabs([
        "🌍 Regime Overview",
        "📊 Market View", 
        "🔬 Regime State",
        "⚠️ Risk & Diagnostics"
    ])
    
    # ═══════════════════════════════════════════════════════════════════════════
    #  TAB 0 — REGIME OVERVIEW
    # ═══════════════════════════════════════════════════════════════════════════
    with tabs[0]:
        st.markdown("## 🌍 Macro Regime Overview")
        
        # Quad cards
        c1, c2, c3 = st.columns(3)
        quad_colors = {"Q1":"#3fb950", "Q2":"#d29922", "Q3":"#f85149", "Q4":"#58a6ff"}
        qc = quad_colors.get(structural_quad, "#8b949e")
        
        with c1:
            st.markdown(f"""
            <div style="background:#0d1117;border:2px solid {qc};border-radius:12px;padding:16px;text-align:center;">
                <div style="font-size:12px;color:#8b949e;">STRUCTURAL</div>
                <div style="font-size:42px;font-weight:800;color:{qc};">{structural_quad}</div>
                <div style="font-size:11px;color:#c9d1d9;">{'Growth ↑ Infl ↓' if structural_quad=='Q1' else 'Growth ↑ Infl ↑' if structural_quad=='Q2' else 'Growth ↓ Infl ↑' if structural_quad=='Q3' else 'Growth ↓ Infl ↓'}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            mc = quad_colors.get(monthly_quad, "#8b949e")
            st.markdown(f"""
            <div style="background:#0d1117;border:1px solid #30363d;border-radius:12px;padding:16px;text-align:center;">
                <div style="font-size:12px;color:#8b949e;">MONTHLY</div>
                <div style="font-size:32px;font-weight:700;color:{mc};">{monthly_quad}</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            gc = quad_colors.get(regime["global_quad"], "#8b949e")
            st.markdown(f"""
            <div style="background:#0d1117;border:1px solid #30363d;border-radius:12px;padding:16px;text-align:center;">
                <div style="font-size:12px;color:#8b949e;">GLOBAL</div>
                <div style="font-size:32px;font-weight:700;color:{gc};">{regime["global_quad"]}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        # Regime Intel
        st.markdown("### 🧠 Regime Intel")
        g_score = regime["growth_score"]
        i_score = regime["inflation_score"]
        
        checks = []
        checks.append(("Growth Momentum > 0", g_score > 0, f"{g_score:+.3f}"))
        checks.append(("Inflation Momentum > 0", i_score > 0, f"{i_score:+.3f}"))
        checks.append(("Yield Curve > 0", (fred_data.get("T10Y2Y", pd.Series([0])).iloc[-1] > 0 if "T10Y2Y" in fred_data else False), 
                      f"{fred_data.get('T10Y2Y', pd.Series([0])).iloc[-1]:.2f}" if "T10Y2Y" in fred_data else "N/A"))
        checks.append(("Unemployment < 4.5%", (fred_data.get("UNRATE", pd.Series([10])).iloc[-1] < 4.5 if "UNRATE" in fred_data else False),
                      f"{fred_data.get('UNRATE', pd.Series([0])).iloc[-1]:.1f}%" if "UNRATE" in fred_data else "N/A"))
        
        for label, ok, val in checks:
            icon = "✅" if ok else "❌"
            color = "#3fb950" if ok else "#f85149"
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:4px 0;"><span>{icon} {label}</span><span style="color:{color};font-weight:600;">{val}</span></div>', unsafe_allow_html=True)
        
        st.divider()
        
        # Key indicators table
        st.markdown("### 📈 Key Macro Indicators")
        ind_rows = []
        for sid, name in [("INDPRO", "Ind. Production"), ("CPIAUCSL", "CPI Level"), ("UNRATE", "Unemployment"), ("T10Y2Y", "Yield Spread"), ("DFF", "Fed Funds")]:
            if sid in fred_data:
                s = fred_data[sid]
                latest = s.iloc[-1]
                prev = s.iloc[-2] if len(s) > 1 else latest
                chg = latest - prev
                ind_rows.append({"Indicator": name, "Latest": f"{latest:.2f}", "Δ": f"{chg:+.2f}"})
        if ind_rows:
            st.dataframe(pd.DataFrame(ind_rows), use_container_width=True, hide_index=True)
    
    # ═══════════════════════════════════════════════════════════════════════════
    #  TAB 1 — MARKET VIEW (User's fragment, preserved & fixed)
    # ═══════════════════════════════════════════════════════════════════════════
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
            filtered = [item for item in basket if filter_fn(item.get("ticker", ""))]
            if not filtered:
                st.caption(f"No {market_name} bottleneck detected")
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
            st.markdown("**📊 Sector Leadership (Top 5)**")
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
            st.markdown("**🔍 Bottleneck Scan**")
            render_bottleneck_filtered(is_crypto_ticker, "Crypto")
            st.markdown("**📋 Master Board**")
            render_master_filtered("crypto_longs", "crypto_shorts", "#a371f7", "#f85149", is_crypto_ticker, "Crypto")

    # ═══════════════════════════════════════════════════════════════════════════
    #  TAB 2 — REGIME STATE
    # ═══════════════════════════════════════════════════════════════════════════
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

    # ═══════════════════════════════════════════════════════════════════════════
    #  TAB 3 — RISK & DIAGNOSTICS
    # ═══════════════════════════════════════════════════════════════════════════
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

if __name__ == "__main__":
    main()