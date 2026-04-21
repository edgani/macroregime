"""
MacroRegime Pro v10.0 — Maxed Full-Final Candidate
==========================================
Current build goals:
- Markets-integrated Signal Strength / lifecycle monitor
- Cleaner truth layer: observed macro vs fallback proxy vs market-implied features
- Better data quality accounting: macro source map + price panel diagnostics
- Structural/monthly quad logic preserved
- More honest versioning, source-quality, and prior-mode diagnostics

What this file is:
- Best current integrated app.py candidate based on app(8)
- Syntax-checked single-file Streamlit build

What this file is not:
- Full-universe final scanner
- Fully walk-forward validated research engine
- Guaranteed bug-free production release

Free data: yfinance + FRED public CSV
Run: streamlit run app.py
"""
from __future__ import annotations
import datetime,math,os,html,sqlite3
from io import StringIO
from pathlib import Path
from typing import Dict,List,Optional,Tuple
import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="MacroRegime Pro",page_icon="🧭",layout="wide",initial_sidebar_state="collapsed")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap');
html,[class*="css"]{font-family:'DM Sans',sans-serif}
#MainMenu,footer,header{visibility:hidden}
.block-container{padding-top:.5rem;padding-bottom:2rem}
.qb{display:inline-block;padding:3px 12px;border-radius:20px;font-family:'DM Mono',monospace;font-weight:500;font-size:11px}
.q1{background:#d4edda;color:#155724}.q2{background:#fff3cd;color:#856404}
.q3{background:#ffeeba;color:#7d4e00}.q4{background:#f8d7da;color:#721c24}.qunk{background:#e2e3e5;color:#495057}
.mc{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:12px 14px;margin-bottom:6px}
.mc .lb{font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;opacity:.4;margin-bottom:2px}
.mc .vl{font-family:'Syne',sans-serif;font-size:18px;font-weight:700;line-height:1.2}
.mc .sb{font-size:11px;opacity:.5}
.good{color:#3dbb6c}.warn{color:#e5a020}.bad{color:#e05252}.neu{color:#888}
.sh{font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;opacity:.35;padding:8px 0 4px;border-bottom:1px solid rgba(255,255,255,0.06);margin-bottom:8px}
.proxy-b{padding:8px 14px;border-radius:8px;font-size:12px;margin-bottom:10px;background:rgba(229,160,32,0.12);border:1px solid rgba(229,160,32,0.3);color:#e5a020}
.real-b{padding:8px 14px;border-radius:8px;font-size:12px;margin-bottom:10px;background:rgba(61,187,108,0.08);border:1px solid rgba(61,187,108,0.2);color:#3dbb6c}
.gb{margin-bottom:6px}
.gb .gr{display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px}
.gb .bg{height:5px;border-radius:3px;background:rgba(255,255,255,0.08);overflow:hidden}
.gb .fl{height:100%;border-radius:3px}
.rot-card{padding:10px 12px;border-radius:8px;margin-bottom:6px}
.rot-best{background:rgba(61,187,108,0.08);border-left:3px solid #3dbb6c}
.rot-safe{background:rgba(229,160,32,0.08);border-left:3px solid #e5a020}
.rot-avoid{background:rgba(224,82,82,0.08);border-left:3px solid #e05252}
.chk-ok{color:#3dbb6c}.chk-no{color:#e05252}.chk-w{color:#e5a020}
.tag{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;margin:1px}
.tag-g{background:rgba(61,187,108,0.15);color:#3dbb6c}
.tag-r{background:rgba(224,82,82,0.15);color:#e05252}
.tag-y{background:rgba(229,160,32,0.15);color:#e5a020}
.tag-b{background:rgba(100,150,255,0.15);color:#6496ff}
.rally-shell{background:linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02));border:1px solid rgba(255,255,255,0.08);border-radius:14px;padding:14px 14px 10px;margin:8px 0 12px 0}
.rally-top{display:flex;gap:12px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;margin-bottom:10px}
.rally-kicker{font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;opacity:.45;margin-bottom:3px}
.rally-title{font-family:'Syne',sans-serif;font-size:22px;font-weight:800;line-height:1.05;margin-bottom:4px}
.rally-sub{font-size:12px;opacity:.62;max-width:760px}
.rally-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border-radius:999px;font-size:11px;font-weight:700;border:1px solid rgba(255,255,255,0.08);background:rgba(255,255,255,0.04);margin:2px 6px 2px 0}
.rally-pill.ok{color:#3dbb6c;background:rgba(61,187,108,0.12)}
.rally-pill.warn{color:#e5a020;background:rgba(229,160,32,0.12)}
.rally-pill.bad{color:#e05252;background:rgba(224,82,82,0.12)}
.rally-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:10px}
.rally-item{border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:12px 12px 10px;background:rgba(255,255,255,0.025)}
.rally-item-top{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:8px}
.rally-item-label{font-size:12px;font-weight:700;line-height:1.2}
.rally-item-note{font-size:10px;opacity:.60;line-height:1.35;min-height:28px}
.rally-chip{min-width:24px;height:24px;border-radius:999px;display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:12px;border:1px solid currentColor}
.rally-ok{color:#3dbb6c}
.rally-warn{color:#e5a020}
.rally-bad{color:#e05252}
.rally-meter{height:7px;border-radius:999px;background:rgba(255,255,255,0.08);overflow:hidden;margin:8px 0 4px}
.rally-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#e05252 0%,#e5a020 50%,#3dbb6c 100%)}
.rally-scale{display:flex;justify-content:space-between;font-size:10px;opacity:.42;margin-top:2px}
.rally-legend{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
.rally-mini{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
.rally-mini-card{padding:8px 10px;border-radius:10px;border:1px solid rgba(255,255,255,0.07);background:rgba(255,255,255,0.025);font-size:11px}
@media (max-width:1100px){.rally-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}
@media (max-width:640px){.rally-grid{grid-template-columns:1fr;}.rally-title{font-size:18px}}

.rally-mini-card{min-width:180px;flex:1}
.rally-shell .rally-mini-card{background:rgba(255,255,255,0.03)}


.ck-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:8px}
.ck-card{border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:10px 12px;background:rgba(255,255,255,0.025)}
.ck-top{display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:6px}
.ck-badge{min-width:24px;height:24px;border-radius:999px;display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:12px;border:1px solid currentColor}
.ck-label{font-size:12px;font-weight:700;line-height:1.25}
.ck-note{font-size:10px;opacity:.62;line-height:1.4;margin-top:4px}
.ck-score{font-family:'DM Mono',monospace;font-size:10px;opacity:.5;margin-top:6px}
@media (max-width:1100px){.ck-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}
@media (max-width:640px){.ck-grid{grid-template-columns:1fr;}}

</style>
""",unsafe_allow_html=True)

# ── WEIGHTS (exact from v33 config/weights.py) ─────────────────────────────────
STRUCT_W = {"g_level":0.20,"g_mom":0.40,"i_level":0.10,"i_mom":0.30,"policy":0.10,"liq":0.10}
MONTHLY_W = {"g_level":0.20,"g_mom":0.45,"i_level":0.15,"i_mom":0.45,"i_shock":0.15,"policy":0.10,"liq":0.10}
QUAD_MOD = {"sf_to_q3":0.10,"sf_to_q2":-0.05,"shock_to_q3":0.10,"shock_to_q1":-0.06,"gm_to_q2":0.03,"gm_to_q4":0.03,"cov_penalty":0.62}  # boosted Q3 signal for oil+slowdown confluence
MONTHLY_MOD = {"sf_to_q3":0.12,"sf_to_q2":-0.06,"shock_to_q3":0.16,"shock_to_q1":-0.04,"gm_to_q2":0.04,"gm_to_q4":0.06,"cov_penalty":0.55}
TACT_TRADE_W = {"breadth":0.35,"trend":0.25,"credit":0.20,"vol":0.20}
TACT_TREND_W = {"spy":0.40,"eqw":0.20,"small":0.15,"sector":0.15,"dollar":0.10}
TACT_TAIL_W  = {"vol":0.35,"credit":0.25,"small":0.20,"dollar":0.10,"narrow":0.10}
TACT_AGG_W   = {"trade":0.35,"trend":0.35,"tail":0.30}
CRASH_W = {"tail_state":0.16,"shock_state":0.18,"health":0.12,"vix":0.14,"unwind":0.14,"vol":0.12,"tail_hedge":0.08,"dollar":0.06}
IHSG_W = {"regime":0.24,"em_rotation":0.16,"macro_native":0.24,"breadth_flow":0.18,"execution":0.18}
EXEC_W = {"weather":0.20,"health":0.14,"vix":0.10,"quad":0.12,"conf":0.10,"cross":0.09,"crowd":0.09,"shock":0.08,"crash":0.08}

TTL=3600               # default 1h
TTL_FRED=21600         # FRED: 6h (monthly data doesn't change hourly)
TTL_PRICES=300         # prices: 5min for near-real-time
TTL_NEWS=900           # news: 15min
FRED_DISK_CACHE_DIR=os.path.join(".cache","fred_series")

def _env_float(name:str, default:float) -> float:
    try:
        raw=os.environ.get(name, None)
        return float(raw) if raw not in {None, ""} else float(default)
    except Exception:
        return float(default)

_SIGNAL_STORE_DEFAULT = str(Path(__file__).with_name("macroregime_signal_strength.sqlite3"))
SIGNAL_STORE_PATH = Path(os.environ.get("MRP_SIGNAL_STORE_PATH", _SIGNAL_STORE_DEFAULT))
SIGNAL_ENTER_THRESHOLD = _env_float("MRP_SIGNAL_ENTER_THRESHOLD", 0.035)
SIGNAL_EXIT_THRESHOLD = _env_float("MRP_SIGNAL_EXIT_THRESHOLD", 0.015)


# ── Ticker display name mapping (from v33 data_symbol_map.py) ─────────────────
TICKER_DISPLAY = {
    "GC=F":"XAUUSD (Gold)","GLD":"GLD (Gold ETF)","SI=F":"XAGUSD (Silver)",
    "PL=F":"Platinum","CL=F":"WTI Oil","BZ=F":"Brent Oil","NG=F":"Natural Gas",
    "HG=F":"Copper","ZC=F":"Corn","ZW=F":"Wheat","ZS=F":"Soybeans",
    "DBC":"DBC (Broad Commod)","GSG":"GSG (Commodities)","DBA":"DBA (Agri ETF)",
    "URA":"URA (Uranium)","DJP":"DJP (Commodities)",
    "EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","AUDUSD=X":"AUD/USD",
    "NZDUSD=X":"NZD/USD","JPY=X":"USD/JPY","CHF=X":"USD/CHF","CAD=X":"USD/CAD",
    "IDR=X":"USD/IDR","CNH=X":"USD/CNH","SGD=X":"USD/SGD",
    "EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","AUDJPY=X":"AUD/JPY",
    "BTC-USD":"BTC/USD","ETH-USD":"ETH/USD","SOL-USD":"SOL/USD",
    "DX-Y.NYB":"DXY (Dollar Index)",
    "BNB-USD":"BNB/USD","XRP-USD":"XRP/USD","ADA-USD":"ADA/USD",
    "AVAX-USD":"AVAX/USD","LINK-USD":"LINK/USD","DOGE-USD":"DOGE/USD",
    "^JKSE":"IHSG","^VIX":"VIX","^VXV":"VXV","UUP":"USD Index (UUP)",
    "EEM":"EEM (EM Equity)","EFA":"EFA (Dev Market)",
    "TLT":"TLT (20Y Bond)","IEF":"IEF (7-10Y Bond)","SHY":"SHY (1-3Y Bond)",
    "HYG":"HYG (HY Credit)","LQD":"LQD (IG Credit)",
    "QQQ":"QQQ (Nasdaq/Growth)","IWM":"IWM (Small Cap)","RSP":"RSP (Equal Weight)",
    "SPY":"SPY (S&P 500)","GLD":"GLD (Gold ETF)",
}
def disp(tk:str)->str:
    """Convert ticker to human-readable name."""
    return TICKER_DISPLAY.get(tk, tk.replace("=X","").replace("=F","").replace("-USD","").replace(".JK",""))

FRED_SERIES = {
    "INDPRO":"INDPRO","PAYEMS":"PAYEMS","UNRATE":"UNRATE","ICSA":"ICSA",
    "RSAFS":"RSAFS","HOUST":"HOUST","ISM":"NAPMNOI","LEI":"USSLIND",
    "UMCSENT":"UMCSENT","CPI":"CPIAUCSL","CORECPI":"CPILFESL","COREPCE":"PCEPILFE",
    "DGS2":"DGS2","DGS10":"DGS10","DGS30":"DGS30","REAL10":"DFII10",
    "BREAKEVEN":"T5YIE","FEDFUNDS":"FEDFUNDS","HYOAS":"BAMLH0A0HYM2","IGSPR":"BAMLC0A0CM",
}
US_TICKERS = ["SPY","QQQ","IWM","RSP","XLE","XLF","XLI","XLB","XLK","XLV","XLY","XLP","XLU","XLRE","XLC",
    "HYG","LQD","TLT","IEF","SHY","GLD","GC=F","SI=F","HG=F","CL=F","NG=F","UUP","DX-Y.NYB","EEM","EFA",
    "^VIX","^VXV","^VIX9D","BTC-USD","ETH-USD","SOL-USD","XRP-USD",
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AVGO","AMD","NFLX","JPM","BAC","GS","XOM","CVX"]
IHSG_TICKERS = ["^JKSE","IDR=X","BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BRIS.JK","TLKM.JK","ASII.JK",
    "ADRO.JK","PTBA.JK","ITMG.JK","HRUM.JK","AADI.JK","BUMI.JK","ANTM.JK","INCO.JK","MDKA.JK","TINS.JK",
    "ICBP.JK","INDF.JK","KLBF.JK","AMRT.JK","ACES.JK","CTRA.JK","BSDE.JK","JSMR.JK","PGAS.JK","EXCL.JK","HEAL.JK"]
FX_TICKERS = ["EURUSD=X","GBPUSD=X","AUDUSD=X","NZDUSD=X","JPY=X","CHF=X","IDR=X","CNH=X","SGD=X","CAD=X"]
COMM_TICKERS = ["GC=F","SI=F","PL=F","CL=F","BZ=F","NG=F","HG=F","ZC=F","ZW=F","ZS=F","DBC","GSG","DBA"]
CRYPTO_TICKERS = ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","ADA-USD","AVAX-USD","LINK-USD","DOGE-USD"]

IHSG_BUCKETS = {
    "Bank":["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BRIS.JK"],
    "Batu Bara/Energi":["ADRO.JK","PTBA.JK","ITMG.JK","HRUM.JK","AADI.JK","BUMI.JK"],
    "Logam":["ANTM.JK","INCO.JK","MDKA.JK","TINS.JK"],
    "Telco/Infra":["TLKM.JK","EXCL.JK","JSMR.JK","PGAS.JK"],
    "Consumer":["ICBP.JK","INDF.JK","KLBF.JK","AMRT.JK","ACES.JK","ASII.JK"],
    "Properti/Health":["CTRA.JK","BSDE.JK","HEAL.JK"],
}
US_BUCKETS = {
    "Growth / Tech":["QQQ","AAPL","MSFT","NVDA","AMZN","META","GOOGL","NFLX"],
    "Semis / AI":["AVGO","AMD","TSLA"],
    "Financials":["JPM","BAC","GS","XLF"],
    "Energy / Value":["XOM","CVX","XLE"],
    "Defensives":["XLV","XLP","XLU"],
}

QUAD_META = {
    "Q1":{"label":"Risk-On Goldilocks","desc":"Growth naik, inflasi turun/stabil. Terbaik untuk risk assets. Central banks bisa longgar.","color":"#d4edda","text":"#155724",
          "best":["EEM (EM Equities)","XAUUSD / Gold (GLD)","IHSG (selective)","QQQ / Growth tech"],
          "safe":["Gold (GLD)","Short-duration (SHY)"],"avoid":["Energy commodities","USD longs","Defensives"],
          "confirm":"EEM > SPY 1M, breadth lebar, VIX <18, credit ketat.","invalidate":"VIX spike >25, HY spreads >500bps, USD re-accelerates."},
    "Q2":{"label":"Reflation / Boom","desc":"Growth dan inflasi sama-sama naik. Commodities, cyclicals, real assets menang.","color":"#fff3cd","text":"#856404",
          "best":["WTI / XLE (energi)","HG=F (Copper / Materials)","IHSG coal exporter","Financials (XLF)"],
          "safe":["TIPS / inflation-linked","Commodity FX"],"avoid":["Long bonds (TLT)","High-multiple tech","IG credit"],
          "confirm":"Oil bertahan, commodities lebar, yields naik teratur, ISM >52.","invalidate":"Oil rollback cepat, ISM turun <50, tightening bites."},
    "Q3":{"label":"Stagflation","desc":"Growth melambat, inflasi tinggi. Quad paling sulit. Gold dan USD menang. Equities broadly suffer.","color":"#ffeeba","text":"#7d4e00",
          "best":["XAUUSD / Gold (GLD, GC=F)","USD / Cash (UUP, SHY, BIL)","Energi (XLE) selektif","Short ideas"],
          "safe":["Gold (GLD)","USD (UUP)","T-bills (SHY)"],"avoid":["QQQ / Rate-sensitive tech","XLY (Consumer disc)","EEM / IHSG","TLT","HYG"],
          "confirm":"Gold > SPY 1M, USD kuat, ISM <50, claims naik, YC masih inverted.","invalidate":"Fed pivot kredibel, ISM rebound >52, credit ketat kembali."},
    "Q4":{"label":"Deflasi / Resesi","desc":"Growth dan inflasi turun. Obligasi panjang dan defensif menang. Capital preservation mode.","color":"#f8d7da","text":"#721c24",
          "best":["TLT (Long bonds)","Gold (GLD)","Defensives (XLP, XLU, XLV)","USD (UUP)"],
          "safe":["Treasury bonds (TLT)","Gold (GLD)"],"avoid":["Commodities (XLE, XLB)","Cyclicals (XLI, XLY)","HYG","IWM","EEM"],
          "confirm":"Yields turun, TLT naik, defensives outperform, TLT > SPY.","invalidate":"Fed cut + fiscal stimulus besar, ISM rebound dari <45."},
}
ROUTE_META = {
    "XAUUSD":{"why":"Hard-asset hedge paling bersih saat inflation pulse naik tapi growth rapuh.","confirm":"Real yields tidak meledak dan breadth belum sembuh.","invalidate":"Rates dan dollar sama-sama naik keras."},
    "USD":{"why":"Kas safety paling bersih saat dollar dan funding stress mendominasi.","confirm":"DXY tetap kuat, breadth tetap lemah.","invalidate":"Breadth melebar dan yields lebih tenang."},
    "TLT":{"why":"Duration jadi tempat kabur kalau growth scare menang.","confirm":"Yields mulai adem dan credit tidak memburuk.","invalidate":"Long-end pain lanjut."},
    "Defensives":{"why":"Cash-flow defensives lebih bersih saat broad beta belum sehat.","confirm":"Breadth tetap sempit dan quality outperforms.","invalidate":"Equal-weight dan small caps ikut konfirmasi."},
    "WTI":{"why":"Shock inflasi / supply masih dominan.","confirm":"Oil impulse bertahan dan de-escalation belum kredibel.","invalidate":"Oil rollback cepat."},
    "EEM":{"why":"Broad EM catch-up mulai hidup, bukan cuma selective exporter.","confirm":"EEM > SPY di 1M dan 3M sambil USD adem.","invalidate":"USD re-accelerates."},
    "IHSG":{"why":"Selective exporter + bank quality dalam EM. IDR stable.","confirm":"IHSG > SPY dan commodity chain belum pecah. Asing nett beli.","invalidate":"USD naik lagi dan commodity leadership luntur. Asing jual."},
}
FAMILY_SPILLOVER_US = {
    "long":{
        "default":["Growth / Tech","Semis / AI","Financials","Defensives"],
        "Energy / Value":["Energy / Value","Financials","Semis / AI","Defensives"],
        "Defensives":["Defensives","Financials","Growth / Tech","Defensives"],
    },
    "short":{
        "default":["Growth / Tech","Semis / AI","Financials","Defensives"],
        "Energy / Value":["Energy / Value","Growth / Tech","Semis / AI","Defensives"],
    }
}
FAMILY_SPILLOVER_IHSG = {
    "long":{
        "default":["Bank","Batu Bara/Energi","Consumer","Properti/Health"],
        "Batu Bara/Energi":["Batu Bara/Energi","Bank","Consumer","Telco/Infra"],
        "Bank":["Bank","Consumer","Batu Bara/Energi","Telco/Infra"],
        "Logam":["Logam","Batu Bara/Energi","Bank","Telco/Infra"],
    },
    "short":{
        "default":["Consumer","Properti/Health","Bank","Telco/Infra"],
        "Consumer":["Consumer","Properti/Health","Bank","Telco/Infra"],
    }
}
ANALOG_LIBRARY = [
    {"label":"2018 trade-war pressure","vector":{"growth":-0.20,"inflation":0.15,"dollar":0.40,"oil":0.05,"smallcap":-0.40,"vol":0.25},"path_1m":"policy-sensitive chop","path_3m":"narrow leaders and defensive bid","path_6m":"relief possible after moderation","scenario_family":"policy_pressure","impacts":{"us":"mixed","ihsg":"bearish","fx":"bullish_usd","commodities":"mixed"},"next_bias":"Monthly pressure may fade, structural slowdown stays"},
    {"label":"2022 commodity shock","vector":{"growth":-0.35,"inflation":0.75,"dollar":0.20,"oil":0.90,"smallcap":-0.35,"vol":0.50},"path_1m":"inflation scare and resource lead","path_3m":"dispersion with fragile beta","path_6m":"policy threshold eventually matters","scenario_family":"commodity_shock","impacts":{"us":"energy_up_beta_fragile","ihsg":"exporters_up_importers_down","fx":"commodity_fx_up","commodities":"bullish"},"next_bias":"Monthly Q3 can persist while structural pressure broadens"},
    {"label":"2025 tariff bond rout","vector":{"growth":-0.25,"inflation":0.30,"dollar":0.50,"oil":0.10,"smallcap":-0.55,"vol":0.45},"path_1m":"long-end pain and broad stress","path_3m":"negotiation relief can squeeze laggards","path_6m":"outcome hinges on de-escalation","scenario_family":"rates_shock","impacts":{"us":"defensive","ihsg":"bearish","fx":"usd_up","commodities":"gold_over_cyclicals"},"next_bias":"Structural stress dominates unless policy relief lands"},
    {"label":"2026 war-oil stagflation","vector":{"growth":-0.30,"inflation":0.80,"dollar":0.35,"oil":0.95,"smallcap":-0.45,"vol":0.55},"path_1m":"oil-first stagflation pressure","path_3m":"energy lead with mixed broader tape","path_6m":"de-escalation can abruptly rotate leadership","scenario_family":"petrodollar_tightening","impacts":{"us":"energy_vs_cyclicals","ihsg":"coal_up_rupiah_fragile","fx":"usd_and_petrocurrency_bid","commodities":"energy_gold_up"},"next_bias":"Petrodollar branch can keep monthly Q3 alive inside structural slowdown"},
    {"label":"Mid-cycle mixed slowdown","vector":{"growth":-0.05,"inflation":0.05,"dollar":0.00,"oil":0.00,"smallcap":-0.05,"vol":0.10},"path_1m":"rotation without panic","path_3m":"slowdown signs but no crash","path_6m":"macro path decides winners","scenario_family":"mixed_slowdown","impacts":{"us":"mixed","ihsg":"mixed","fx":"range","commodities":"selective"},"next_bias":"Base case stays mixed until a cleaner impulse emerges"},
    # ── NEW: From Ricky's analysis (April 2026) ─────────────────────────────
    {"label":"2026 TACO de-escalation rally (Ricky pattern)","vector":{"growth":-0.10,"inflation":0.45,"dollar":-0.20,"oil":-0.30,"smallcap":0.40,"vol":-0.35},"path_1m":"de-escalation spike dan relief squeeze laggard","path_3m":"most hated inflated rally — semua aset naik bareng","path_6m":"Warsh cuts + FIFA deadline → rally berlanjut tapi valuasi rapuh","scenario_family":"taco_deescalation","impacts":{"us":"broad risk-on tapi most hated (banyak yang tidak percaya)","ihsg":"asing masuk, MSCI clear catalyze inflow","fx":"DXY turun, IDR menguat, carry works again","commodities":"oil turun tapi gold hold, copper naik"},"next_bias":"Rally ini bukan karena fundamental tapi karena likuiditas. Satu tangan di pintu keluar."},
    {"label":"1999 post-LTCM inflated rally (bubble endgame)","vector":{"growth":0.20,"inflation":0.10,"dollar":-0.10,"oil":0.15,"smallcap":0.60,"vol":-0.50},"path_1m":"everything rally — saham crypto emas semua naik","path_3m":"FOMO masuk puncak, valuasi tertinggi sepanjang sejarah","path_6m":"sistem fragile + likuiditas habis = koreksi brutal","scenario_family":"bubble_endgame","impacts":{"us":"Nasdaq-type blow-off top sebelum crash 78%","ihsg":"asing masuk tapi hati-hati keluar duluan","fx":"DXY weak = EM rally, tapi reversal tajam","commodities":"gold dan komoditas naik awal, lalu selloff saat crash"},"next_bias":"Nikmati tapi satu tangan di pintu keluar. Valuasi AS sudah setara 1929 dan 2000."},
]
UPCOMING_EVENTS = [
    {"title":"US CPI (Apr)","family":"inflation","when":"~Apr 16","countdown":"T-3d","impact":"Panas = yields naik, USD up, QQQ turun. Dingin = buka pintu Warsh cut lebih cepat."},
    {"title":"Kevin Warsh Fed Confirmation Hearing ⭐","family":"policy","when":"Apr 16","countdown":"T-3d","impact":"[CRITICAL] Warsh sudah commit suku bunga harus lebih rendah. Konfirmasi = DXY drop, risk-on, most hated rally dimulai. Warsh menggantikan Powell 15 Mei 2026."},
    {"title":"FOMC Meeting (Powell terakhir)","family":"policy","when":"~May 6-7","countdown":"T-24d","impact":"Pertemuan Powell terakhir sebelum diganti Warsh. Hold expected tapi forward guidance penting."},
    {"title":"Kevin Warsh resmi jadi Fed Chair","family":"policy","when":"May 15","countdown":"T-31d","impact":"[CRITICAL] Warsh masuk = pemotongan suku bunga defensif dimulai. ON RRP tinggal $0.6M dari $2.3T — sistem butuh inject likuiditas baru. Most hated inflated rally bisa mulai."},
    {"title":"OJK-MSCI Meeting (Indonesia) ⭐","family":"growth","when":"~Apr 21-25","countdown":"T-8d","impact":"[IHSG KEY] OJK ketemu MSCI terkait status Indonesia. Worst case = turun ke frontier (kecil). Base case = tetap emerging market, bobot disesuaikan. Saham clear HSC = penerima flow asing."},
    {"title":"US Nonfarm Payrolls (Apr)","family":"labor","when":"~May 2","countdown":"T-19d","impact":"Data labor kunci untuk justifikasi Warsh cut. Miss = Warsh punya argumen lebih kuat untuk cut agresif."},
    {"title":"Iran-AS Perundingan Lanjutan","family":"geopolitics","when":"TBD","countdown":"T-?","impact":"[TACO Chapter 2] Ceasefire 2 minggu berakhir ~Apr 22. Vance tinggalkan 1 proposal final. Kalau Iran terima = de-escalation, oil drop, risk-on. Kalau gagal = re-eskalasi, oil naik ke $100+."},
    {"title":"FIFA World Cup 2026 deadline ⭐","family":"geopolitics","when":"Jun 2026","countdown":"T-~50d","impact":"[POLITICAL DEADLINE] Trump tidak mau panggung terbesar 4 tahun presidennya dirusak perang + harga bensin tinggi. De-eskalasi HARUS terjadi sebelum Juni. Calendar deadline yang tidak bisa ditunda."},
    {"title":"US GDP Q1 (advance)","family":"growth","when":"~Apr 30","countdown":"T-17d","impact":"Kontraksi = growth scare deepens. Ekspansi = soft landing hope, tapi Warsh masih mau cut."},
    {"title":"US Treasury Debt Refinancing Deadline","family":"policy","when":"~Jun 2026","countdown":"T-~50d","impact":"Kebanyakan deadline refinancing utang AS ada di Juni. Treasury butuh yields rendah untuk refinancing. Ini salah satu alasan struktural kenapa Warsh HARUS cut sebelum Juni."},
]

def _s(s)->pd.Series:
    if s is None: return pd.Series(dtype=float)
    return pd.to_numeric(s if isinstance(s,pd.Series) else pd.Series(s),errors="coerce").dropna()
def last(s)->float:
    s=_s(s); return float(s.iloc[-1]) if not s.empty else float("nan")
def ret_n(s,n:int)->float:
    s=_s(s)
    if len(s)<n+1: return float("nan")
    b=float(s.iloc[-(n+1)])
    if not math.isfinite(b) or b==0: return float("nan")
    return float(s.iloc[-1]/b-1.0)
def delta_n(s,n:int)->float:
    s=_s(s)
    if len(s)<n+1: return float("nan")
    return float(s.iloc[-1]-s.iloc[-(n+1)])
def roc_acc(s,n:int,lag:int)->Optional[bool]:
    s=_s(s)
    if len(s)<n+lag+2: return None
    c=ret_n(s,n); p=ret_n(s.iloc[:-lag],n)
    if not(math.isfinite(c) and math.isfinite(p)): return None
    return c>p
def ts(s)->float:
    s=_s(s)
    if len(s)<50: return 0.5
    px=float(s.iloc[-1]); m20=float(s.rolling(20).mean().iloc[-1]); m50=float(s.rolling(50).mean().iloc[-1])
    return 0.5*(1 if px>m20 else 0)+0.5*(1 if px>m50 else 0)
def th(x:float,sc:float)->float:
    if not math.isfinite(x): return 0.0
    return float(math.tanh(x/max(sc,1e-9)))
def clamp(x,lo=0.0,hi=1.0)->float: return max(lo,min(hi,float(x or 0)))
def nm(*v)->float:
    a=[x for x in v if math.isfinite(x)]
    return float(np.mean(a)) if a else 0.0
def pct(v,d=1)->str:
    if not math.isfinite(v): return "—"
    return f"{v*100:+.{d}f}%"
def num(v,d=2)->str:
    if not math.isfinite(v): return "—"
    return f"{v:.{d}f}"
def acc_txt(flag)->str:
    if flag is True: return "▲ Accelerating"
    if flag is False: return "▼ Decelerating"
    return "– Unknown"
def conf_band(conf:float)->str:
    if conf<0.20: return "Low-Conviction"
    if conf<0.40: return "Tentative"
    if conf<0.60: return "Moderate-Conviction"
    return "High-Conviction"
def nf(x,d=0.0): return float(np.nan_to_num(x,nan=d))


@st.cache_data(ttl=TTL,show_spinner=False)
def fetch_fred(sid:str)->pd.Series:
    """Fetch FRED series with multi-layer fallback: live → cache → proxy → empty."""
    os.makedirs(FRED_DISK_CACHE_DIR, exist_ok=True)
    cache_path=os.path.join(FRED_DISK_CACHE_DIR,f"{sid}.csv")
    key=os.environ.get("FRED_API_KEY","")
    try: key=key or st.secrets.get("FRED_API_KEY","")
    except: pass

    def _load_cache()->pd.Series:
        try:
            if os.path.exists(cache_path):
                df=pd.read_csv(cache_path,index_col=0,parse_dates=True)
                if not df.empty:
                    s=pd.to_numeric(df.iloc[:,0],errors="coerce").dropna()
                    if len(s)>0: return s
        except Exception:
            pass
        return pd.Series(dtype=float)

    def _fetch_live()->Optional[pd.Series]:
        urls=[f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"]
        if key: urls.append(f"https://api.stlouisfed.org/fred/series/observations?series_id={sid}&api_key={key}&file_type=json")
        sess=requests.Session()
        sess.headers.update({"User-Agent":"Mozilla/5.0 MacroRegimePro/11.0"})
        for attempt in range(3):
            for url in urls:
                try:
                    r=sess.get(url,timeout=(12+attempt*6))
                    r.raise_for_status()
                    if "fredgraph" in url:
                        df=pd.read_csv(StringIO(r.text),index_col=0,parse_dates=True)
                        s=pd.to_numeric(df.iloc[:,0],errors="coerce").dropna()
                    else:
                        import json
                        data=json.loads(r.text)
                        obs=data.get("observations",[])
                        idx=pd.to_datetime([o["date"] for o in obs])
                        vals=pd.to_numeric([o["value"] for o in obs],errors="coerce")
                        s=pd.Series(vals.values,index=idx).dropna()
                    if len(s)>0:
                        try:
                            s.to_csv(cache_path, header=[sid])
                        except Exception:
                            pass
                        return s
                except Exception:
                    continue
        return None

    # 1. Try live fetch
    live=_fetch_live()
    if live is not None and len(live)>0:
        return live
    # 2. Try disk cache (may be stale but better than empty)
    cached=_load_cache()
    if len(cached)>0:
        return cached
    # 3. Return empty — build_macro will fall back to market proxies
    return pd.Series(dtype=float)

@st.cache_data(ttl=TTL_FRED, show_spinner=False)
def fetch_fred_bundle(series_items: tuple) -> Dict[str, pd.Series]:
    """Parallel FRED fetch — 5-10x faster than sequential."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    result: Dict[str, pd.Series] = {}
    def _fetch_one(item):
        nice, sid = item
        return nice, fetch_fred(sid)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch_one, item): item for item in series_items}
        for future in as_completed(futures):
            try:
                nice, s = future.result(timeout=25)
                result[nice] = s
            except Exception:
                nice, sid = futures[future]
                result[nice] = pd.Series(dtype=float)
    return result

@st.cache_data(ttl=TTL_PRICES, show_spinner=False)
def fetch_prices(tickers: tuple, period: str="2y")->Dict[str,pd.Series]:
    try:
        import yfinance as yf
        raw=yf.download(list(tickers),period=period,auto_adjust=False,progress=False,threads=True,ignore_tz=True)
        out:Dict[str,pd.Series]={}
        if isinstance(raw.columns,pd.MultiIndex):
            close=raw.get("Close",pd.DataFrame())
            if isinstance(close,pd.DataFrame):
                for t in tickers:
                    if t in close.columns:
                        s=close[t].dropna()
                        if len(s)>5: out[t]=s
        return out
    except:
        return {}


def summarize_price_panel(prices:Dict[str,pd.Series], expected_tickers:tuple)->Dict:
    rows=[]; loaded=0; history_years=[]; latest_dates=[]; missing=[]
    for t in expected_tickers:
        s=_s(prices.get(t,pd.Series(dtype=float)))
        pts=len(s)
        if pts>0:
            loaded+=1
            years=pts/252.0
            history_years.append(years)
            latest=str(s.index[-1])[:10]
            latest_dates.append(pd.to_datetime(s.index[-1]))
            rows.append({"Ticker":t,"Points":pts,"Years":years,"Latest":latest,"Missing":False})
        else:
            missing.append(t)
            rows.append({"Ticker":t,"Points":0,"Years":0.0,"Latest":"—","Missing":True})
    expected=len(expected_tickers)
    coverage=loaded/max(expected,1)
    short_hist=sum(1 for y in history_years if y<1.25)
    short_share=short_hist/max(len(history_years),1) if history_years else 1.0
    median_years=float(np.median(history_years)) if history_years else 0.0
    latest_max=max(latest_dates) if latest_dates else None
    stale_share=0.0
    if latest_max is not None and latest_dates:
        stale_share=sum(1 for d in latest_dates if (latest_max-d).days>7)/len(latest_dates)
    return {
        "expected":expected,
        "loaded":loaded,
        "missing_count":expected-loaded,
        "coverage":coverage,
        "short_history_share":short_share,
        "median_years":median_years,
        "stale_share":stale_share,
        "missing_tickers":missing,
        "rows":rows,
    }


def get_regime_prior_mode()->str:
    mode=str(os.environ.get("MRP_REGIME_PRIOR_MODE","off") or "off").strip().lower()
    return mode if mode in {"off","gentle","strong"} else "off"


def build_fallback_macro_proxies(prices:Dict[str,pd.Series])->Dict:
    spy_3m=ret_n(prices.get("SPY",pd.Series()),63); xli_3m=ret_n(prices.get("XLI",pd.Series()),63)
    xly_3m=ret_n(prices.get("XLY",pd.Series()),63); iwm_3m=ret_n(prices.get("IWM",pd.Series()),63)
    uup_3m=ret_n(prices.get("UUP",pd.Series()),63); oil_3m=ret_n(prices.get("CL=F",pd.Series()),63)
    gold_3m=ret_n(prices.get("GC=F",pd.Series()),63); tlt_1m=ret_n(prices.get("TLT",pd.Series()),21)
    hyg_1m=ret_n(prices.get("HYG",pd.Series()),21); cop_3m=ret_n(prices.get("HG=F",pd.Series()),63)
    spy_1m=ret_n(prices.get("SPY",pd.Series()),21); xli_1m=ret_n(prices.get("XLI",pd.Series()),21)
    xly_1m=ret_n(prices.get("XLY",pd.Series()),21); iwm_1m=ret_n(prices.get("IWM",pd.Series()),21)
    oil_1m=ret_n(prices.get("CL=F",pd.Series()),21); gold_1m=ret_n(prices.get("GC=F",pd.Series()),21)
    uup_1m=ret_n(prices.get("UUP",pd.Series()),21)
    bk=2.2+1.2*nf(oil_3m)+0.4*nf(gold_3m)-0.2*nf(uup_3m)
    return dict(
        indpro_yoy=nf(0.55*xli_3m+0.45*spy_3m), retail_yoy=nf(0.60*xly_3m+0.40*spy_3m),
        payrolls_yoy=nf(0.50*iwm_3m+0.50*spy_3m), unrate_3m_delta=nf(-0.10*iwm_3m),
        claims_13w_delta=nf(-10.0*iwm_3m), ism_last=50.0+20.0*nf(xli_3m),
        housing_yoy=nf(iwm_3m*0.6), cpi_yoy=nf(0.025+0.35*oil_3m+0.05*gold_3m),
        core_cpi_yoy=nf(0.023+0.15*oil_3m-0.05*uup_3m),
        corepce_yoy=nf(0.022+0.12*oil_3m-0.04*uup_3m),
        breakeven=bk, breakeven_1m=nf(0.15*oil_3m/3),
        real_10y=1.8-30.0*nf(tlt_1m) if math.isfinite(tlt_1m) else 1.8,
        policy_rate=4.33, policy_rate_3m=0.0,
        dgs2=float("nan"),dgs10=float("nan"),dgs30=float("nan"),
        spread_2s10s=float("nan"),spread_2s10s_3m=float("nan"),
        yield_curve_state="Unknown (proxy)",yield_curve_uninverting=False,
        hy_oas=350.0-1200.0*nf(hyg_1m), hy_oas_1m=-200.0*nf(hyg_1m),
        ig_oas=float("nan"), ig_oas_1m=float("nan"),
        copper_gold_ratio_3m=nf(cop_3m-gold_3m) if(math.isfinite(cop_3m) and math.isfinite(gold_3m)) else 0.0,
        oil_1m=oil_1m, gold_1m=gold_1m, dxy_1m=uup_1m, dxy_3m=uup_3m,
        spy_1m=spy_1m, xli_1m=xli_1m, xly_1m=xly_1m, iwm_1m=iwm_1m,
        oil_3m=oil_3m, gold_3m=gold_3m,
        indpro_acc=None, payrolls_acc=None, cpi_acc=None, corepce_acc=None, lei_acc=None,
    )


def build_macro_observed(fred:Dict[str,pd.Series])->Tuple[Dict,Dict,int,int]:
    obs={}; source_map={}; fred_loaded=0; fred_total=0
    def put(field:str, series_key:str, fn, *args):
        nonlocal fred_loaded, fred_total
        fred_total+=1
        s=fred.get(series_key,pd.Series())
        if not _s(s).empty:
            v=fn(s,*args)
            if math.isfinite(v):
                obs[field]=v
                source_map[field]="observed_fred"
                fred_loaded+=1
                return True
        return False
    put("indpro_yoy","INDPRO",ret_n,12); put("payrolls_yoy","PAYEMS",ret_n,12)
    put("payrolls_mom","PAYEMS",ret_n,1); put("unrate","UNRATE",last)
    put("unrate_3m_delta","UNRATE",delta_n,3); put("claims_13w_delta","ICSA",delta_n,13)
    put("claims_last","ICSA",last); put("ism_last","ISM",last)
    put("retail_yoy","RSAFS",ret_n,12); put("housing_yoy","HOUST",ret_n,12)
    put("lei_3m","LEI",ret_n,3); put("umcsent_last","UMCSENT",last)
    put("cpi_yoy","CPI",ret_n,12); put("cpi_mom","CPI",ret_n,1)
    put("core_cpi_yoy","CORECPI",ret_n,12); put("corepce_yoy","COREPCE",ret_n,12)
    put("breakeven","BREAKEVEN",last); put("breakeven_1m","BREAKEVEN",delta_n,1)
    put("real_10y","REAL10",last); put("policy_rate","FEDFUNDS",last)
    put("policy_rate_3m","FEDFUNDS",delta_n,3); put("dgs2","DGS2",last)
    put("dgs10","DGS10",last); put("dgs30","DGS30",last)
    put("hy_oas","HYOAS",last); put("hy_oas_1m","HYOAS",delta_n,21)
    put("ig_oas","IGSPR",last); put("ig_oas_1m","IGSPR",delta_n,21)
    return obs, source_map, fred_loaded, fred_total


def build_market_implied_features(prices:Dict[str,pd.Series])->Dict:
    f={}
    for t in ["SPY","QQQ","IWM","RSP","UUP","TLT","EEM","EFA","GLD","HYG","LQD",
              "XLE","XLI","XLY","XLP","XLB","XLK","XLF","CL=F","GC=F","HG=F","SI=F"]:
        s=prices.get(t,pd.Series())
        tk=t.replace("^","").replace("=F","f").lower()
        f[f"{tk}_1m"]=ret_n(s,21); f[f"{tk}_3m"]=ret_n(s,63); f[f"{tk}_ts"]=ts(s)
    cop=prices.get("HG=F",pd.Series()); gld=prices.get("GC=F",pd.Series())
    if not _s(cop).empty and not _s(gld).empty:
        c2,g2=_s(cop).align(_s(gld),join="inner")
        if len(c2)>63: f["copper_gold_ratio_3m"]=ret_n(c2/g2,63)
    vix_s=prices.get("^VIX",pd.Series()); vxv_s=prices.get("^VXV",pd.Series())
    f["vix_last"]=last(vix_s); f["vix_1m"]=delta_n(vix_s,21)
    if not _s(vix_s).empty and not _s(vxv_s).empty:
        v,vxv=_s(vix_s).align(_s(vxv_s),join="inner")
        if len(v)>5:
            r=float(v.iloc[-1])/float(vxv.iloc[-1]); f["vix_vxv_ratio"]=r
            f["vix_term_state"]="Contango (calm)" if r<0.90 else("Flat (neutral)" if r<1.00 else "Backwardation (fear)")
        else:
            f["vix_vxv_ratio"]=float("nan"); f["vix_term_state"]="Unknown"
    else:
        f["vix_vxv_ratio"]=float("nan"); f["vix_term_state"]="Unknown"
    return f


def _delta_roc(s: pd.Series, window: int = 12, offset: int = 3) -> float:
    """Second derivative: change in YoY rate — Hedgeye's core signal."""
    try:
        if s is None or len(s) < window + offset + 2:
            return float("nan")
        roc = s.pct_change(window).dropna()
        if len(roc) < offset + 1:
            return float("nan")
        delta = float(roc.iloc[-1]) - float(roc.iloc[-(offset+1)])
        return delta if math.isfinite(delta) else float("nan")
    except Exception:
        return float("nan")


def build_macro(fred:Dict[str,pd.Series],prices:Dict[str,pd.Series],price_meta:Optional[Dict]=None)->Dict:
    raw_macro_keys=["indpro_yoy","retail_yoy","payrolls_yoy","unrate_3m_delta","claims_13w_delta","ism_last","housing_yoy","cpi_yoy","core_cpi_yoy","breakeven"]
    f=build_fallback_macro_proxies(prices)
    source_map={k:"fallback_proxy" for k in raw_macro_keys if k in f}
    source_detail={
        "indpro_yoy":"XLI/SPY return proxy",
        "retail_yoy":"XLY/SPY return proxy",
        "payrolls_yoy":"IWM/SPY return proxy",
        "unrate_3m_delta":"IWM inverse proxy",
        "claims_13w_delta":"IWM inverse proxy",
        "ism_last":"XLI return proxy",
        "housing_yoy":"IWM proxy",
        "cpi_yoy":"Oil/Gold/UUP proxy",
        "core_cpi_yoy":"Oil/UUP proxy",
        "breakeven":"Oil/Gold/UUP blend proxy",
    }
    observed, observed_sources, fred_loaded, fred_total = build_macro_observed(fred)
    f.update(observed)
    source_map.update(observed_sources)
    market_features=build_market_implied_features(prices)
    f.update(market_features)
    # Yield curve observed path
    d2=f.get("dgs2",float("nan")); d10=f.get("dgs10",float("nan")); d30=f.get("dgs30",float("nan"))
    if math.isfinite(d2) and math.isfinite(d10):
        sp=d10-d2; f["spread_2s10s"]=sp
        f["yield_curve_state"]="Inverted" if sp<-0.10 else("Flat" if sp<0.25 else("Normal" if sp<1.50 else "Steep"))
        s2=_s(fred.get("DGS2",pd.Series())); s10=_s(fred.get("DGS10",pd.Series()))
        if len(s2)>63 and len(s10)>63:
            a2,a10=s2.align(s10,join="inner"); f["spread_2s10s_3m"]=delta_n(a10-a2,63)
            f["yield_curve_uninverting"]=(math.isfinite(f.get("spread_2s10s_3m",float("nan"))) and f.get("spread_2s10s_3m",0)>0.20 and sp>-0.25)
    if math.isfinite(d10) and math.isfinite(d30):
        f["spread_10s30s"]=d30-d10
    # RoC flags
    f["indpro_acc"]=roc_acc(fred.get("INDPRO",pd.Series()),12,3)
    f["payrolls_acc"]=roc_acc(fred.get("PAYEMS",pd.Series()),12,3)
    f["cpi_acc"]=roc_acc(fred.get("CPI",pd.Series()),12,3)
    f["corepce_acc"]=roc_acc(fred.get("COREPCE",pd.Series()),12,3)
    f["lei_acc"]=roc_acc(fred.get("LEI",pd.Series()),3,2)

    macro_observed_count=sum(1 for k in raw_macro_keys if source_map.get(k)=="observed_fred")
    macro_proxy_count=len(raw_macro_keys)-macro_observed_count
    observed_macro_share=macro_observed_count/max(len(raw_macro_keys),1)
    macro_proxy_share=macro_proxy_count/max(len(raw_macro_keys),1)
    price_panel_coverage=float((price_meta or {}).get("coverage",0.0)) if price_meta else 0.0
    price_short_history_share=float((price_meta or {}).get("short_history_share",1.0)) if price_meta else 1.0
    price_median_years=float((price_meta or {}).get("median_years",0.0)) if price_meta else 0.0
    price_stale_share=float((price_meta or {}).get("stale_share",0.0)) if price_meta else 0.0

    price_avail=sum(1 for t in ["spy_1m","xli_1m","xly_1m","iwm_1m","oil_1m","gold_1m","dxy_1m"] if math.isfinite(f.get(t,float("nan"))))
    monthly_real_share=price_avail/7.0
    fred_real_share=fred_loaded/max(fred_total,1)
    structural_real_share=0.55*observed_macro_share+0.25*fred_real_share+0.20*price_panel_coverage
    data_coverage=clamp(0.50*structural_real_share+0.20*(1-macro_proxy_share)+0.20*(1-price_short_history_share)+0.10*(1-price_stale_share))
    monthly_data_coverage=clamp(0.45*monthly_real_share+0.20*observed_macro_share+0.20*price_panel_coverage+0.15*(1-price_stale_share))
    macro_source_quality=clamp(0.45*observed_macro_share+0.20*fred_real_share+0.20*price_panel_coverage+0.10*(1-price_short_history_share)+0.05*(1-price_stale_share))
    data_source_mode=(
        "Observed-Heavy" if observed_macro_share>=0.70 and price_panel_coverage>=0.85 else
        "Hybrid" if observed_macro_share>=0.35 else
        "Proxy-Heavy"
    )

    # Dual-horizon feature scaffolding (v33 exact formula preserved)
    oil_3m=f.get("clf_3m",f.get("oil_3m",0.0)); gld_3m=f.get("gld_3m",f.get("gold_3m",0.0))
    uup_3m=f.get("uup_3m",f.get("dxy_3m",0.0)); spy_1m=f.get("spy_1m",0.0)
    xli_1m=f.get("xli_1m",0.0); xly_1m=f.get("xly_1m",0.0); iwm_1m=f.get("iwm_1m",0.0)
    oil_1m=f.get("clf_1m",f.get("oil_1m",0.0)); gld_1m=f.get("gcf_1m",f.get("gold_1m",0.0))
    uup_1m=f.get("uup_1m",f.get("dxy_1m",0.0)); bk1m=f.get("breakeven_1m",0.0)
    cpi=f.get("cpi_yoy",0.025); core=f.get("core_cpi_yoy",0.023)
    hcg=float(cpi-core) if(math.isfinite(cpi) and math.isfinite(core)) else 0.0
    gi=[th(f.get("indpro_yoy",0)-0.02,0.05),th(f.get("retail_yoy",0)-0.03,0.06),
        th(f.get("payrolls_yoy",0)-0.015,0.03),th(f.get("housing_yoy",0),0.10),
        th((f.get("ism_last",50)-50)/100,0.04),th(-f.get("unrate_3m_delta",0),0.12),
        th(-f.get("claims_13w_delta",0)/40,0.60)]
    gm=[th(f.get("housing_yoy",0),0.08),th(f.get("indpro_yoy",0),0.05),
        th(-f.get("unrate_3m_delta",0),0.10),th(-f.get("claims_13w_delta",0)/50,0.50)]
    g_level=nm(*gi); g_mom=nm(*gm)
    ii=[th(cpi-0.025,0.020),th(core-0.025,0.015),th((f.get("breakeven",2.2)-2.2)/2.0,0.300),
        th(nf(oil_3m),0.250),th(nf(gld_3m),0.180)]
    im=[th(nf(oil_3m),0.220),th(nf(gld_3m),0.180),th((f.get("breakeven",2.2)-2.2)/2.0,0.240),th(nf(uup_3m),0.140)]
    i_level=nm(*ii); i_mom=nm(*im)
    sf=sum([1 if math.isfinite(f.get("unrate_3m_delta",float("nan"))) and f.get("unrate_3m_delta",0)>0.05 else 0,
        1 if math.isfinite(f.get("claims_13w_delta",float("nan"))) and f.get("claims_13w_delta",0)>0 else 0,
        1 if math.isfinite(f.get("ism_last",float("nan"))) and f.get("ism_last",50)<50 else 0,
        1 if math.isfinite(f.get("housing_yoy",float("nan"))) and f.get("housing_yoy",0)<0 else 0])/4.0
    inf_shock=nf(nm(th(nf(oil_3m),0.22),th((f.get("breakeven",2.2)-2.2)/2.0,0.24),th(nf(uup_3m),0.14)))
    monthly_gi=[th(nf(spy_1m),0.05),th(nf(xli_1m),0.05),th(nf(xly_1m),0.05),th(nf(iwm_1m),0.07),th(-nf(uup_1m),0.06)]
    monthly_ii=[th(nf(hcg),0.004),th(nf(oil_1m),0.06),th(nf(gld_1m),0.05),th(nf(bk1m),0.08),th(-nf(uup_1m),0.05)]
    monthly_g_signal=nm(*monthly_gi); monthly_i_signal=nm(*monthly_ii)

# Structural truth should be slower and less tape-driven than monthly weather.
# The old block was too willing to call quarterly Q2/Q4 from proxy-only tape.
# New rule: use proxy mostly for growth climate and inflation momentum, not inflation level.
    structural_obs_reliability=clamp(0.65*observed_macro_share+0.35*fred_real_share)
    structural_proxy_damp=clamp(1.0-0.55*macro_proxy_share,0.35,1.0)
    structural_speed_damp=clamp(0.20+0.80*structural_obs_reliability,0.20,1.0)
    structural_proxy_scale=clamp(1.0-structural_obs_reliability)

    def acc_num(v):
        if v is True: return 1.0
        if v is False: return -1.0
        return float("nan")

    # True-root fix: structural quad must be driven by rate-of-change, not absolute level.
    # Otherwise any positive growth + mildly positive inflation proxy mechanically biases toward Q2.
    g_struct_roc_obs=nm(
        acc_num(f.get("indpro_acc")),
        acc_num(f.get("payrolls_acc")),
        acc_num(f.get("lei_acc")),
        th(-f.get("unrate_3m_delta",0.0),0.08),
        th(-f.get("claims_13w_delta",0.0)/45.0,0.60),
    )
    i_struct_roc_obs=nm(
        acc_num(f.get("cpi_acc")),
        acc_num(f.get("corepce_acc")),
        th(f.get("breakeven_1m",0.0),0.08),
        th(-nf(uup_1m),0.05),
    )

    g_struct_proxy_roc=nm(
        th(nf(f.get("spy_1m",0.0))-nf(f.get("spy_3m",0.0))/3.0,0.03),
        th(nf(f.get("xli_1m",0.0))-nf(f.get("xli_3m",0.0))/3.0,0.03),
        th(nf(f.get("xly_1m",0.0))-nf(f.get("xly_3m",0.0))/3.0,0.03),
        th(nf(f.get("iwm_1m",0.0))-nf(f.get("iwm_3m",0.0))/3.0,0.04),
        th(nf(f.get("eem_1m",0.0))-nf(f.get("eem_3m",0.0))/3.0,0.04),
        th(nf(f.get("rsp_1m",f.get("spy_1m",0.0)))-nf(f.get("rsp_3m",f.get("spy_3m",0.0)))/3.0,0.03),
    )
    # Structural inflation proxy: use 3m-based signals, not 1m
    # 1M oil/gold moves are WEATHER (monthly), not CLIMATE (structural)
    # Breakeven inflation is the purest structural inflation signal
    i_struct_proxy_roc=nm(
        th(nf(oil_3m)/3.0, 0.04),              # oil TREND (3m), dampened
        th(nf(bk1m),0.08),                     # breakeven = forward-looking inflation
        th(nf(gld_3m)/3.0, 0.03),              # gold TREND (3m)
        th(nf(f.get("tlt_1m",0.0))*-1, 0.04), # TLT inverse = bond inflation signal
    )

    g_struct_climate=nf(structural_obs_reliability*g_struct_roc_obs + 0.70*structural_proxy_scale*g_struct_proxy_roc)
    i_struct_climate=nf(structural_obs_reliability*i_struct_roc_obs + 0.70*structural_proxy_scale*i_struct_proxy_roc)
    # ── Sticky-inflation floor: oil alone should not drag structural inflation negative
    # when other signals (core gap, breakeven, monthly shock) are still elevated. ──
    _sticky_inf_signals=[
        th(nf(f.get("headline_core_gap",0.0)),0.005),
        th(nf(f.get("m_shock",0.0)),0.10),
        th((f.get("breakeven",2.2)-2.2)/2.0,0.30),
        th(-nf(f.get("uup_1m",0.0)),0.05),
    ]
    _sticky_inflation=float(nm(*_sticky_inf_signals))
    if _sticky_inflation>0.15 and i_struct_climate<0.08:
        i_struct_climate=0.08  # floor: inflation is not fully dead

    g_struct_proxy_mom=nm(
        th(nf(f.get("xli_1m",0.0)),0.04),
        th(nf(f.get("xly_1m",0.0)),0.04),
        th(nf(f.get("iwm_1m",0.0)),0.05),
        th(nf(f.get("eem_1m",0.0)),0.05),
        th(nf(f.get("rsp_1m",f.get("spy_1m",0.0))),0.04),
    )
    i_struct_proxy_mom=nm(
        th(nf(oil_1m),0.06),
        th(nf(bk1m),0.08),
        th(-nf(uup_1m),0.05),
        th(-nf(f.get("tlt_1m",0.0)),0.06),
    )

    g_struct_level=clamp(g_struct_climate)
    i_struct_level=clamp(i_struct_climate)
    g_struct_mom=nf(0.70*g_struct_climate + 0.20*structural_proxy_scale*g_struct_proxy_mom)
    i_struct_mom=nf(0.70*i_struct_climate + 0.20*structural_proxy_scale*i_struct_proxy_mom)

    g_month_level=nf(0.65*g_level+0.35*g_mom)
    g_month_mom=nf(0.45*g_mom+0.55*monthly_g_signal)
    i_month_level=nf(0.55*i_level+0.25*i_mom+0.20*th(nf(hcg),0.004))
    i_month_mom=nf(0.45*i_mom+0.55*monthly_i_signal)

    # Tariff/trade headwind: ISM below 50 + oil shock + USD strength = stagflation structural
    # This is what Hedgeye's forward-looking model captures that lagging FRED misses
    ism_last = f.get("ism_last", 51.0)
    ism_sub50 = max(0.0, (50.0 - ism_last) / 5.0) if math.isfinite(ism_last) else 0.0
    oil_3m_shock = clamp(nf(f.get("clf_3m", f.get("oil_3m", 0.0))) / 0.10)  # normalize: 10% = full signal
    usd_stress = clamp(nf(f.get("uup_1m", 0.0)) / 0.03)
    # Tariff headwind: use 3M oil trend (not 1M) to avoid noise from weekly swings
    # Oil -13% in 1 week ≠ structural inflation trend change
    # Use ISM services + manufacturing composite for Q3 sticky inflation signal
    oil_3m_val = nf(f.get("clf_3m", f.get("oil_3m", 0.0)))
    oil_headwind = clamp(oil_3m_val / 0.10) if oil_3m_val > 0 else 0.0  # only when oil UP on 3m basis
    tariff_growth_headwind = clamp(
        0.35 * ism_sub50
        + 0.30 * oil_headwind
        + 0.20 * usd_stress
        + 0.15 * max(0.0, f.get("claims_13w_delta", 0.0) / 20.0)
    )
    structural_slowdown_flags = clamp(
        0.45 * sf
        + 0.30 * max(0.0, -g_struct_climate)
        + 0.25 * tariff_growth_headwind  # NEW: forward-looking headwind
    )
    structural_inf_shock=clamp(0.60*max(0.0,i_struct_climate)+0.40*max(0.0,i_struct_proxy_mom))
    policy_score=th(-nf(f.get("policy_rate_3m",0.0)),0.50)
    liq_proxy=nm(th(-nf(uup_3m),0.12),th(nf(f.get("tlt_1m",0.0)),0.08))
    liq_score=th(nf(liq_proxy),0.50)
    m_policy=nf(0.60*policy_score+0.40*th(-nf(f.get("policy_rate_3m",0.0)),0.25))
    m_liq=nf(0.50*liq_score+0.50*th(nf(liq_proxy),0.35))
    m_shock=nf(nm(max(0.0,th(nf(hcg),0.004)),max(0.0,th(nf(oil_1m),0.06)),max(0.0,th(nf(bk1m),0.08))))

    prior_mode=get_regime_prior_mode()
    f.update({
        "g_struct_level":g_struct_level,"g_struct_mom":g_struct_mom,
        "i_struct_level":i_struct_level,"i_struct_mom":i_struct_mom,
        "g_month_level":g_month_level,"g_month_mom":g_month_mom,
        "i_month_level":i_month_level,"i_month_mom":i_month_mom,
        "m_policy":m_policy,"m_liq":m_liq,"m_shock":m_shock,
        "policy_score":policy_score,"liq_score":liq_score,
        "g_level":g_level,"g_mom":g_mom,"i_level":i_level,"i_mom":i_mom,
        "slowdown_flags":sf,"inf_shock":inf_shock,"headline_core_gap":hcg,
        "data_coverage":data_coverage,"monthly_data_coverage":monthly_data_coverage,
        "macro_proxy_share":macro_proxy_share,"fred_real_share":fred_real_share,
        "macro_observed_share":observed_macro_share,"macro_source_quality":macro_source_quality,
        "data_source_mode":data_source_mode,
        "price_panel_coverage":price_panel_coverage,
        "price_short_history_share":price_short_history_share,
        "price_median_years":price_median_years,
        "price_stale_share":price_stale_share,
        "macro_source_map":source_map,
        "macro_source_detail":source_detail,
        "macro_observed_fields":[k for k in raw_macro_keys if source_map.get(k)=="observed_fred"],
        "macro_proxy_fields":[k for k in raw_macro_keys if source_map.get(k)!="observed_fred"],
        "structural_obs_reliability":structural_obs_reliability,
        "structural_proxy_damp":structural_proxy_damp,
        "structural_speed_damp":structural_speed_damp,
        "structural_proxy_scale":structural_proxy_scale,
        "g_struct_climate":g_struct_climate,
        "tariff_growth_headwind":tariff_growth_headwind,
        # --- 2nd-derivative (Hedgeye-style) signals injected from features layer ---
        "indpro_roc_3m":   _delta_roc(fred.get("INDPRO",  pd.Series()), window=12, offset=3),
        "cpi_roc_3m":      _delta_roc(fred.get("CPI",     pd.Series()), window=12, offset=3),
        "payrolls_roc_3m": _delta_roc(fred.get("PAYEMS",  pd.Series()), window=12, offset=3),
        "ism_3m_delta":    _delta_roc(fred.get("ISM",     pd.Series()), window=3,  offset=1),
        "lei_3m_delta":    _delta_roc(fred.get("LEI",     pd.Series()), window=3,  offset=1),
        "core_cpi_roc_3m": _delta_roc(fred.get("CORECPI", pd.Series()), window=12, offset=3),
        "leading_indicator_composite": float(nm(
            th(_delta_roc(fred.get("LEI",    pd.Series()), 3, 1),  0.30),
            th(_delta_roc(fred.get("INDPRO", pd.Series()), 12, 3), 0.25),
            th(_delta_roc(fred.get("PAYEMS", pd.Series()), 12, 3), 0.25),
            th(-_delta_roc(fred.get("ISM",   pd.Series()), 3, 1),  0.20) * -1,
        ) if True else 0.0),
        "i_struct_climate":i_struct_climate,
        "g_struct_roc_obs":g_struct_roc_obs,
        "i_struct_roc_obs":i_struct_roc_obs,
        "g_struct_proxy_roc":g_struct_proxy_roc,
        "i_struct_proxy_roc":i_struct_proxy_roc,
        "structural_slowdown_flags":structural_slowdown_flags,
        "structural_inf_shock":structural_inf_shock,
        "prior_mode":prior_mode,
        "prior_mode_active":prior_mode!="off",
        "_fred_loaded":fred_loaded,"_fred_total":fred_total,"_proxy_share":macro_proxy_share,
    })
    return f


def _score_block(g_level,g_mom,i_level,i_mom,policy,liq,sf,shock,data_cov,proxy_share,w,mw,monthly=False)->Tuple:
    g_core=w["g_level"]*g_level+w["g_mom"]*g_mom
    i_core=w["i_level"]*i_level+w["i_mom"]*i_mom
    p_core=w["policy"]*policy+w["liq"]*liq
    if monthly: i_core+=w.get("i_shock",0.0)*max(0.0,shock)
    raw={"Q1":+g_core-i_core+0.15*p_core,"Q2":+g_core+i_core-0.08*p_core,
         "Q3":-g_core+1.10*i_core-0.12*p_core,"Q4":-g_core-0.90*i_core+0.25*p_core}
    raw["Q1"]+=mw["shock_to_q1"]*max(0.0,shock)+mw["sf_to_q2"]*sf
    raw["Q2"]+=mw["gm_to_q2"]*max(0.0,g_mom)+mw["sf_to_q2"]*sf
    raw["Q3"]+=mw["sf_to_q3"]*sf+mw["shock_to_q3"]*max(0.0,shock)
    raw["Q4"]+=mw["gm_to_q4"]*max(0.0,-g_mom)
    # Penalty: high inflation shock makes pure-deflationary Q4 less likely
    raw["Q4"]-=0.12*max(0.0,shock)
    # Penalty: high inflation shock makes pure-deflationary Q4 less likely
    raw["Q4"]-=0.12*max(0.0,shock)
    prior_adj={k:raw[k] for k in raw}  # prior=off, no adjustment
    arr=np.array([prior_adj[q] for q in ["Q1","Q2","Q3","Q4"]],dtype=float)
    exp=np.exp(arr-arr.max()); prbs=exp/exp.sum()
    probs=dict(zip(["Q1","Q2","Q3","Q4"],prbs.tolist()))
    ordered=sorted(probs.items(),key=lambda kv:kv[1],reverse=True)
    quad=ordered[0][0]; top=ordered[0][1]; next_q=ordered[1][0]; margin=top-ordered[1][1]
    cov_pen=mw["cov_penalty"]*proxy_share
    conf=clamp(top*(0.70+0.30*data_cov)*(1.0-cov_pen))
    return probs,quad,next_q,conf,g_core,i_core,p_core

def build_quad(f:Dict)->Dict:
    sf=f.get("slowdown_flags",0.0); shock=f.get("inf_shock",0.0)
    cov=f.get("data_coverage",0.5); proxy=f.get("macro_proxy_share",1.0)
    mcov=f.get("monthly_data_coverage",0.5)
    struct_sf=nf(f.get("structural_slowdown_flags",sf))*clamp(f.get("structural_speed_damp",0.5))
    struct_shock=nf(f.get("structural_inf_shock",shock))*clamp(0.25+0.75*f.get("structural_obs_reliability",0.5))
    structural_proxy=clamp(1.0-f.get("structural_obs_reliability",0.0))
    s_probs,s_quad,s_next,s_conf,s_gc,s_ic,s_pc=_score_block(
        f.get("g_struct_level",0),f.get("g_struct_mom",0),
        f.get("i_struct_level",0),f.get("i_struct_mom",0),
        f.get("policy_score",0),f.get("liq_score",0),struct_sf,struct_shock,cov,structural_proxy,STRUCT_W,QUAD_MOD,False)
    m_probs,m_quad,m_next,m_conf,m_gc,m_ic,m_pc=_score_block(
        f.get("g_month_level",0),f.get("g_month_mom",0),
        f.get("i_month_level",0),f.get("i_month_mom",0),
        f.get("m_policy",0),f.get("m_liq",0),sf,f.get("m_shock",shock),mcov,proxy,MONTHLY_W,MONTHLY_MOD,True)
    div="aligned" if s_quad==m_quad else "divergent"
    operating=f"Aligned {s_quad}" if div=="aligned" else f"Monthly {m_quad} inside Structural {s_quad}"
    s_ordered=sorted(s_probs.items(),key=lambda kv:kv[1],reverse=True)
    margin=s_ordered[0][1]-s_ordered[1][1]
    deepness=clamp((abs(s_gc)+abs(s_ic)+0.35*abs(s_pc)+0.25*sf+0.20*max(0.0,shock))/1.8)
    duration_mat=clamp(0.30+0.35*deepness+0.20*abs(f.get("i_struct_mom",0))+0.15*abs(f.get("g_struct_mom",0)))
    disagreement=clamp(0.5+0.5*abs(s_gc-s_ic)-0.5*margin)
    flip_h=clamp(0.30*(1-margin)+0.20*duration_mat+0.15*disagreement+0.15*abs(s_probs.get("Q3",0)-m_probs.get("Q3",0))+0.10*sf+0.10*max(0.0,shock))
    yc=f.get("yield_curve_state",""); hy=f.get("hy_oas",350.0)
    yc_adj=-0.12 if"Inverted"in yc else(-0.05 if f.get("yield_curve_uninverting") else 0.06 if"Normal"in yc or"Steep"in yc else 0.0)
    cred_adj=(clamp((hy-300)/600)*-0.15 if math.isfinite(hy) else 0.0)
    adj_gc=s_gc+yc_adj+cred_adj
    g_acc=f.get("indpro_acc") or f.get("payrolls_acc")
    if g_acc is None: g_acc=(s_gc>0)
    i_acc=f.get("cpi_acc") or f.get("corepce_acc")
    if i_acc is None: i_acc=(s_ic>0)
    cb=conf_band(s_conf)
    
    # STRUCTURAL STICKINESS: Hedgeye anchors quarterly quad for ~3 months
    # A single week of data (oil -13%) should NOT flip structural Q3 → Q4
    # Implementation: when confidence < 25% and top quad is Q4,
    # apply a Q3 prior bias if ISM Prices Paid remains elevated (>65)
    # This mimics Hedgeye's "sticky quarterly" behavior
    _prices_paid_proxy = f.get("prices_paid_composite", f.get("ism_mfg_prices", 65.0) or 65.0)
    _oil_3m_trend = nf(f.get("clf_3m", f.get("oil_3m", 0.0)))
    _sticky_q3 = (
        float(_prices_paid_proxy or 65.0) >= 65.0  # inflation still elevated
        and _oil_3m_trend > -0.05  # oil not in full collapse (>-5% on 3m)
        and s_conf < 0.25           # low confidence = borderline
        and s_quad == "Q4"          # currently showing Q4
    )
    if _sticky_q3:
        # Hedgeye's quarterly anchor: bias back toward Q3 when sticky inflation
        s_quad = "Q3"
        s_probs = {**s_probs, "Q3": s_probs.get("Q3", 0.20) + 0.08, "Q4": max(0, s_probs.get("Q4", 0.26) - 0.08)}
    
    # Transitional state: when confidence < 20% AND spread between top 2 quads is < 5%, label it
    q_ordered = sorted(s_probs.items(), key=lambda x: -x[1])
    top_spread = q_ordered[0][1] - q_ordered[1][1]
    is_transitional = s_conf < 0.20 and top_spread < 0.08
    transitional_label = f"Transitional ({q_ordered[0][0]}/{q_ordered[1][0]})" if is_transitional else s_quad
    return dict(quad=s_quad,probs=s_probs,next_quad=s_next,confidence=s_conf,conf_band=cb,
                transitional=is_transitional,transitional_label=transitional_label,
                monthly_quad=m_quad,monthly_probs=m_probs,monthly_next=m_next,monthly_conf=m_conf,
                divergence=div,operating=operating,flip_hazard=flip_h,deepness=deepness,duration_mat=duration_mat,
                g_core=adj_gc,i_core=s_ic,p_core=s_pc,g_level=s_gc,i_level=s_ic,
                growth_acc=g_acc,infl_acc=i_acc,slowdown_flags=sf,inf_shock=shock)

def _match_analog(f:Dict)->Dict:
    oil_3m=nf(f.get("clf_3m",f.get("oil_3m",0.0)))
    gold_3m=nf(f.get("gld_3m",f.get("gold_3m",0.0)))
    uup_1m=nf(f.get("uup_1m",f.get("dxy_1m",0.0)))
    smallcap=nf(f.get("iwm_1m",0.0))
    vix=f.get("vix_last",20.0); vix_s=(vix-18)/20.0
    current={"growth":nf(f.get("g_level",0)),"inflation":nf(f.get("i_level",0)),
              "dollar":clamp(uup_1m*10+0.0),"oil":clamp(oil_3m*2+0.5),"smallcap":clamp(smallcap*5-0.5),"vol":clamp(vix_s)}
    best=None; best_sim=0.0
    for a in ANALOG_LIBRARY:
        v=a["vector"]
        dots=sum(current.get(k,0)*v.get(k,0) for k in v)
        mag_c=math.sqrt(sum(current.get(k,0)**2 for k in v))+1e-9
        mag_a=math.sqrt(sum(v[k]**2 for k in v))+1e-9
        sim=clamp(dots/(mag_c*mag_a)*0.5+0.5)
        if sim>best_sim: best_sim=sim; best=dict(a,similarity=sim)
    return best or dict(ANALOG_LIBRARY[-1],similarity=0.5)

def build_playbooks(f:Dict,q:Dict)->List[Dict]:
    oil_3m=nf(f.get("clf_3m",f.get("oil_3m",0.0)))
    uup_1m=nf(f.get("uup_1m",0.0)); tlt_1m=nf(f.get("tlt_1m",0.0))
    iwm_1m=nf(f.get("iwm_1m",0.0)); long_end=clamp(0.5-tlt_1m*5)
    breadth_dmg=clamp(0.5-iwm_1m*5); sf=q.get("slowdown_flags",0)
    pain_relief=clamp(0.35*long_end+0.20*breadth_dmg+0.20*sf+0.15*max(0,uup_1m*5)+0.10*max(0,oil_3m))
    war_de=clamp(0.45*max(0,oil_3m*2)+0.20*max(0,uup_1m*5)+0.20*breadth_dmg+0.15*(1.0 if q.get("inf_shock",0)>0.3 else 0.0))
    tariff_neg=clamp(0.35*max(0,uup_1m*5)+0.25*long_end+0.20*max(0,iwm_1m*-5)+0.20*breadth_dmg)
    # New playbooks (Ricky / April 2026)
    taco_ch2=clamp(0.35*(1-max(0,oil_3m))+0.20*(1-sf)+0.25*(1-long_end)+0.20*(1-breadth_dmg))
    warsh_cut=clamp(0.20*(1-sf)+0.25*(1-long_end)+0.25*(1-breadth_dmg)+0.30*(1-sf))
    shock_pen_p=clamp(q.get("inf_shock",0)*1.5)
    bubble_end=clamp(0.12+0.15*(1 if q.get("quad","Q3") in("Q1","Q2") else 0)+0.15*q.get("confidence",0.3)+0.15*(1-shock_pen_p))
    return [{"name":"Pain-before-relief refinancing","evidence":clamp(0.55*long_end+0.25*sf+0.20*max(0,-iwm_1m*5)),"hypothesis":pain_relief,
             "desc":"Long-end pain, growth stress, dan weak internals naikan odds bahwa financial-pain thresholds akhirnya memicu relief messaging.",
             "invalidators":["Long-end worsening tanpa policy response","Credit dan breadth deteriorate bersama-sama","Inflation shock accelerates"]},
            {"name":"War-shock then de-escalation","evidence":clamp(0.60*max(0,oil_3m*2)+0.20*max(0,uup_1m*5)+0.20*breadth_dmg),"hypothesis":war_de,
             "desc":"Energy shock mendukung stagflation trades dulu, tapi rising pain dapat membuat partial de-escalation atau relief narrative jauh lebih relevan.",
             "invalidators":["Oil keeps extending tanpa pause","Dollar pressure intensifies dan breadth tidak stabilize","Small-cap dan credit failure deepens together"]},
            {"name":"Tariff-pressure then negotiation relief","evidence":clamp(0.40*max(0,uup_1m*5)+0.35*max(0,-iwm_1m*5)+0.25*long_end),"hypothesis":tariff_neg,
             "desc":"Rising dollar, weak small caps, dan long-end pain mirip prior pressure cycles di mana later negotiation moderation triggers tactical relief.",
             "invalidators":["Escalation rhetoric compounds","Small caps tidak bisa stabilize","Long-end dan vol stress reinforce each other"]},
            {"name":"TACO Ch.2: Iran de-escalation inevitable before June 2026 ⭐","evidence":clamp(0.50*(1-max(0,oil_3m))+0.30*(1-sf)+0.20*(1-long_end)),"hypothesis":taco_ch2,
             "desc":"Setiap perundingan gagal, efeknya ke pasar makin kecil (less effect). De-eskalasi HARUS terjadi sebelum Juni: FIFA World Cup 2026 (Trump butuh panggung), Treasury debt refinancing June deadline, Warsh confirmation butuh market stabil. Pattern Liberation Day 2025 terulang sempurna.",
             "invalidators":["Iran massive retaliation ke pangkalan AS/Israel","Warsh gagal dikonfirmasi Senat","Serangan militer skala baru sebelum FIFA deadline","Ceasefire collapses completely tanpa negosiasi lanjutan"]},
            {"name":"Warsh Fed cut + ON RRP habis → Most Hated Inflated Rally ⭐","evidence":clamp(0.40*(1-long_end)+0.35*(1-sf)+0.25*(1-shock_pen_p)),"hypothesis":warsh_cut,
             "desc":"Warsh masuk 15 Mei menggantikan Powell. Komit suku bunga harus turun. ON RRP tinggal $0.6M dari $2.3T — sistem butuh likuiditas baru. Pemotongan defensif (bukan ekspansif) → semua aset naik bukan karena fundamental tapi karena uang tidak tahu harus ke mana. Most hated karena banyak yang skeptis dan tidak ikut, justru itu yang bikin rally lama.",
             "invalidators":["Inflasi re-accelerate lebih cepat dari cut","Warsh gagal dikonfirmasi","Shock eksternal baru","Likuiditas habis lebih cepat dari yang diperkirakan"]},
            {"name":"Bubble Endgame / Ujung Siklus → koreksi brutal setelah most hated rally ⚠️","evidence":clamp(0.30*(1-shock_pen_p)+0.40*(1-sf)+0.30*(1-long_end)),"hypothesis":bubble_end,
             "desc":"Valuasi AS setara 1929 dan 2000. Utang global tertinggi masa damai. Warsh cut defensif = rally suntikan. Ricky anatomy bubble: inovasi/ekspansi → harga naik → FOMO → everything rally → ujung siklus. 1999: Nasdaq -78%. 2007: S&P -57%. 2021: growth stocks -60-80%. Nikmati pestanya, tapi satu tangan di pintu keluar.",
             "invalidators":["AI genuinely changes productivity (super cycle valid)","QE infinity dari Fed","Resolusi geopolitik global simultaneous (peace dividend besar)"]},
    ]

def build_scenarios(q:Dict,f:Dict,h:Dict,analog:Dict,playbooks:List)->Dict:
    s_quad=q["quad"]; m_quad=q["monthly_quad"]; s_next=q.get("next_quad",s_quad)
    m_next=q.get("monthly_next",m_quad); div=q["divergence"]; hazard=q.get("flip_hazard",0.5)
    shock_str=clamp(q.get("inf_shock",0.0)*2); conf=q.get("confidence",0.5)
    oil_3m=nf(f.get("clf_3m",f.get("oil_3m",0.0))); uup_1m=nf(f.get("uup_1m",0.0))
    raw={}
    if div=="aligned":
        raw[f"Base: Aligned {s_quad} continuation"]=0.34+0.18*conf
        raw[f"Alt: tactical move toward {s_next}"]=0.18+0.18*hazard
        raw["Family: shock branch"]=0.12+0.22*shock_str
        raw["Family: broadening leadership"]=0.12
        raw["Family: false relief"]=0.10+0.12*max(0.0,hazard-conf)
    else:
        raw[f"Base: Monthly {m_quad} inside Structural {s_quad}"]=0.28+0.16*conf
        raw[f"Alt: Monthly {m_quad} fades to Structural {s_quad}"]=0.18+0.16*max(0.0,0.55-conf)+0.10*hazard
        raw[f"Transition: Monthly {m_quad} broadens into Structural {m_next}"]=0.12+0.14*conf
        raw["Family: divergence resolves via confirmation"]=0.10
        raw["Family: policy / rates override"]=0.08
        raw["Family: shock branch"]=0.10+0.20*shock_str
    # Out-of-box scenarios
    petro=clamp(max(0,oil_3m*2)*0.5+shock_str*0.5)
    if petro>=0.40: raw["Out-of-box: Petrodollar tightening shock"]=0.12+0.20*petro
    usd_sq=clamp(max(0,uup_1m*8))
    if usd_sq>=0.35: raw["Out-of-box: Carry unwind / dollar squeeze"]=0.10+0.16*usd_sq
    raw[f"Analog: {analog.get('label','Historical echo')}"]=0.08+0.18*float(analog.get("similarity",0.5))
    pb=max(playbooks,key=lambda x:x["hypothesis"])
    raw[f"Playbook: {pb['name']}"]=0.08+0.25*float(pb["hypothesis"])
    # ── NEW SCENARIOS (April 2026 — Ricky/real-world framework) ───────────────
    # 1. TACO de-escalation: scales with weather and low flip hazard
    _taco=clamp(0.30+0.25*(1-q.get("flip_hazard",0.5))+0.25*h.get("weather",0.5)+0.20*(1-max(0,shock_str)))
    raw["TACO Ch.2: Iran de-escalation → risk-on rally"]=_taco
    # 2. Warsh Fed cut → most hated inflated rally
    _warsh=clamp(0.20+0.30*(1-shock_str)+0.25*(1-q.get("slowdown_flags",0))+0.25*h.get("weather",0.5))
    raw["Most Hated Inflated Rally (Warsh cut + TACO final)"]=_warsh
    # 3. Bubble endgame / ujung siklus
    _vix_low=f.get("vix_last",20); _bubble=clamp(0.08+0.15*(1 if s_quad in("Q1","Q2") else 0)+0.10*q.get("confidence",0.3)+0.10*clamp(1-(_vix_low-13)/15))
    raw["Bubble Endgame / Ujung Siklus (Ricky bubble anatomy)"]=_bubble
    # 4. MSCI Indonesia clear → asing masuk IHSG
    raw["MSCI Indonesia clear → asing masuk IHSG"]=clamp(0.08 if s_quad in("Q1","Q2") else 0.04+0.10*(1-max(0,nf(uup_1m)*5)))
    # 5. Hormuz blockade re-eskalasi → WTI $110+
    if max(0,oil_3m)>0.10 or shock_str>0.20:
        raw["Hormuz Blockade / re-eskalasi → WTI $110+"]=clamp(0.12+0.20*shock_str+0.15*max(0,oil_3m))
    # Normalize
    total=sum(raw.values()); probs={k:v/total for k,v in raw.items()}
    def _winners_losers(name:str):
        nl=name.lower()
        if "petrodollar" in nl or "shock" in nl: return ["Energy / Gold","Petro FX","Shipping"],["Oil importers","Broad cyclicals","Fragile EM FX"],["Oil fades quickly","USD and rates calm","Importer pain not spreading"]
        if "carry unwind" in nl or "dollar" in nl: return ["USD cash","Funding-safe majors","JPY/CHF hedges"],["Crowded carry","Fragile EM FX","High beta crypto"],["Dollar fails to extend","Vol compresses fast","Carry re-bid returns"]
        if "taco" in nl or "de-escalation" in nl: return ["Risk assets broad (most hated)","IWM small caps","EEM/IHSG eksportir","BTC/ETH","Oil DOWN"],["USD longs","TLT","Defensives"],["Iran massive retaliation","Warsh not confirmed","Ceasefire collapses again"]
        if "most hated inflated" in nl or "warsh" in nl: return ["Everything: saham+emas+crypto+komoditas","EM/IHSG inflow","High beta alts"],["Cash holders terlambat","TLT longs"],["Inflasi re-accelerate","Warsh gagal","External shock baru"]
        if "bubble" in nl or "ujung siklus" in nl: return ["Yang masuk duluan + keluar sebelum crash","Gold hedge","Short beta setelah puncak"],["Retail FOMO di puncak","High-multiple growth","Leverage positions"],["Valuasi sustained (super cycle)","Fed terus inject infinity"]
        if "msci" in nl: return ["IHSG quality (BBCA,BMRI,TLKM)","Saham clear HSC","Coal exporters (ADRO,PTBA)","IDR"],["Saham HSC tinggi (BREN type)","Free float rendah"],["Indonesia turun ke frontier","Asing tidak masuk meski clear"]
        if "hormuz" in nl or "blockade" in nl: return ["WTI/Brent oil","XLE energy","ADRO/PTBA coal","Gold","Shipping tankers"],["Oil importers","Consumer (biaya naik)","EM importers","Airlines"],["Hormuz reopens quickly","Iran capitulates","Diplomatic resolution sudden"]
        if "broadening" in nl: return ["Equal-weight / selective beta","EM catch-up","Quality laggards"],["Consensus hedges","Ultra-defensive late trades"],["Small caps fail to confirm","USD re-accelerates","Credit fails to improve"]
        if "analog" in nl: return ["Names aligned with analog path","Selective hard assets"],["Crowded late-cycle beta","Consensus laggards"],["Cross-asset path diverges from analog","Breadth expands against analog"]
        if "playbook" in nl: return ["Second-order beneficiaries","Relief duration beneficiaries"],["Consensus late trades","Overcrowded trend-chasing"],["Long-end pain does not trigger relief","Breadth stays narrow"]
        return ["Selective winners with scenario fit"],["Crowded mismatched expressions"],["Cross-asset confirmation flips","Shock state changes materially"]
    cases={}
    for name,p in sorted(probs.items(),key=lambda kv:kv[1],reverse=True):
        w,l,inv=_winners_losers(name)
        cases[name]={"probability":p,"winners":w,"losers":l,"invalidators":inv,
                     "description":f"{name} under {q['operating']}, {s_quad}/{m_quad}, shock={shock_str:.2f}."}
    return cases

def build_health(prices:Dict[str,pd.Series],f:Dict)->Dict:
    SECS=["XLE","XLF","XLI","XLB","XLK","XLV","XLY","XLP","XLU","XLRE","XLC"]
    spy_t=ts(prices.get("SPY",pd.Series())); qqq_t=ts(prices.get("QQQ",pd.Series())); iwm_t=ts(prices.get("IWM",pd.Series()))
    spy_3m=f.get("spy_3m",0.0); rsp_3m=ret_n(prices.get("RSP",pd.Series()),63)
    eqw=clamp(0.5+(rsp_3m-spy_3m)*5) if(math.isfinite(rsp_3m) and math.isfinite(spy_3m)) else 0.5
    narrow=clamp(0.5+(spy_3m-rsp_3m)*5) if(math.isfinite(rsp_3m) and math.isfinite(spy_3m)) else 0.5
    ab50=sum(1 for t in SECS if len(_s(prices.get(t,pd.Series())))>=50 and float(_s(prices.get(t,pd.Series())).iloc[-1])>float(_s(prices.get(t,pd.Series())).rolling(50).mean().iloc[-1]))
    sec_s=ab50/len(SECS); small_conf=clamp(0.5+f.get("iwm_1m",0.0)*5)
    # Exact v33 tactical weather formula
    breadth_s=clamp(nm(sec_s,spy_t,small_conf))
    trade=clamp(TACT_TRADE_W["breadth"]*breadth_s+TACT_TRADE_W["trend"]*spy_t+TACT_TRADE_W["credit"]*(1-clamp((f.get("hy_oas",350)-250)/400))+TACT_TRADE_W["vol"]*(1-clamp((f.get("vix_last",20)-13)/25)))
    trend_=clamp(TACT_TREND_W["spy"]*spy_t+TACT_TREND_W["eqw"]*eqw+TACT_TREND_W["small"]*small_conf+TACT_TREND_W["sector"]*sec_s+TACT_TREND_W["dollar"]*(0.5-nf(f.get("uup_1m",0.0))))
    tail=clamp(TACT_TAIL_W["vol"]*(1-clamp((f.get("vix_last",20)-13)/25))+TACT_TAIL_W["credit"]*(1-clamp((f.get("hy_oas",350)-250)/400))+TACT_TAIL_W["small"]*small_conf+TACT_TAIL_W["dollar"]*(0.5-nf(f.get("uup_1m",0.0)))+TACT_TAIL_W["narrow"]*(1-narrow))
    weather=clamp(TACT_AGG_W["trade"]*trade+TACT_AGG_W["trend"]*trend_+TACT_AGG_W["tail"]*tail)
    def s3(v,hi=0.62,lo=0.42,lb=("Healthy","Mixed","Fragile")): return lb[0] if v>=hi else(lb[2] if v<=lo else lb[1])
    return dict(breadth=breadth_s,trade=trade,trend=trend_,tail=tail,weather=weather,
                sec_above50=ab50,sec_support=sec_s,eqw_vs_cw=rsp_3m-spy_3m if(math.isfinite(rsp_3m) and math.isfinite(spy_3m)) else 0.0,
                narrow_leadership=narrow,small_conf=small_conf,spy_trend=spy_t,iwm_trend=iwm_t,
                trade_state="supportive" if trade>=0.60 else("hostile" if trade<=0.40 else "balanced"),
                trend_state="persistent" if trend_>=0.60 else("fragile" if trend_<=0.40 else "mixed"),
                tail_state="calm" if tail>=0.58 else("stressed" if tail<=0.42 else "neutral"),
                weather_state="Risk-On" if weather>=0.58 else("Risk-Off" if weather<=0.42 else "Mixed"),
                verdict="Healthy" if weather>=0.62 else("Narrow" if weather>=0.50 else("Fragile" if weather>=0.38 else "Broken")))

def _fetch_cnn_fear_greed() -> float:
    """Fetch CNN Fear & Greed index (0=extreme fear, 100=extreme greed). Returns 0.5 on error."""
    try:
        import requests
        resp = requests.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            headers={"User-Agent":"Mozilla/5.0 MacroRegimePro"},
            timeout=6
        )
        if resp.status_code == 200:
            data = resp.json()
            score = float(data.get("fear_and_greed",{}).get("score",50))
            return clamp(score / 100.0)
    except Exception:
        pass
    # Fallback: approximate from VIX position (inverse relationship)
    return None  # Signal that fetch failed

def _iwm_ath_distance(prices:Dict[str,pd.Series]) -> float:
    """IWM distance from ATH — proxy for small cap health / breadth peak.
    High ATH-distance = crowded longs far from peak = cascade risk elevated."""
    try:
        s = prices.get("IWM", pd.Series())
        if s is None or len(s) < 20: return 0.5
        peak = float(s.rolling(252, min_periods=60).max().iloc[-1])
        current = float(s.iloc[-1])
        if peak > 0 and math.isfinite(peak) and math.isfinite(current):
            drawdown_from_ath = (current - peak) / peak  # negative = below ATH
            # Convert to risk score: 0% = 0.0, -15% = 0.5, -30% = 1.0
            return clamp(-drawdown_from_ath / 0.30)
    except Exception:
        pass
    return 0.5

@st.cache_data(ttl=900, show_spinner=False)
def _fetch_cnn_fg_cached() -> Optional[float]:
    return _fetch_cnn_fear_greed()

def build_crash(f:Dict,h:Dict,q:Dict,prices:Optional[Dict]=None)->Dict:
    vix=f.get("vix_last",20.0); hy=f.get("hy_oas",350.0); ig=f.get("ig_oas",100.0)
    tail_s=1.0 if h.get("tail_state")=="stressed" else(0.35 if h.get("tail_state")=="neutral" else 0.10)
    shock_s=clamp(q.get("inf_shock",0.0)*1.5)
    health_frag={"Fragile":0.85,"Narrow":0.65,"Mixed":0.35,"Healthy":0.15,"Broken":0.90}.get(h.get("verdict","Mixed"),0.35)
    vix_s=0.90 if vix>=29 else(0.55 if vix>=19 else 0.20)
    unwind=clamp(h.get("narrow_leadership",0.5)*0.8+max(0,nf(f.get("uup_1m",0.0))*5)*0.2)
    vol_st=clamp((vix-18)/20); tail_hedge=clamp((f.get("vix_vxv_ratio",0.9)-0.9)*5+0.3) if math.isfinite(f.get("vix_vxv_ratio",float("nan"))) else 0.3
    dol_pr=clamp(0.5+nf(f.get("uup_1m",0.0))/0.04)

    # NEW: CNN Fear & Greed (extreme greed = crowding risk, extreme fear = tail risk)
    cnn_fg_raw = _fetch_cnn_fg_cached() if st is not None else None
    if cnn_fg_raw is not None:
        cnn_fg = float(cnn_fg_raw)
        # Extreme greed (>0.75) = crowding/complacency risk
        # Extreme fear (<0.25) = panic / potential crash underway
        cnn_greed_risk = clamp((cnn_fg - 0.65) / 0.35) if cnn_fg > 0.65 else 0.0  # greedy = crowding
        cnn_fear_risk  = clamp((0.25 - cnn_fg) / 0.25) if cnn_fg < 0.25 else 0.0  # fearful = cascade
        cnn_crash_signal = max(cnn_greed_risk * 0.6, cnn_fear_risk * 1.0)  # fear weighs more for crash
    else:
        cnn_fg = 0.5; cnn_crash_signal = 0.0
        # VIX-based approximation when CNN unavailable
        cnn_fg = clamp(1.0 - (vix - 10) / 30)

    # NEW: IWM ATH-to-ATH distance (small cap health / breadth cascade risk)
    iwm_ath = _iwm_ath_distance(prices) if prices else 0.5

    # v33 exact crash formula (now with CNN F&G + IWM ATH)
    crash_score=clamp(CRASH_W["tail_state"]*tail_s+CRASH_W["shock_state"]*shock_s+0.12*health_frag+0.10*vix_s+CRASH_W["unwind"]*unwind+CRASH_W["vol"]*vol_st+CRASH_W["tail_hedge"]*tail_hedge+0.06*dol_pr+0.08*cnn_crash_signal+0.06*iwm_ath)
    risk_off=clamp(0.30*(1.0-h.get("weather",0.5))+0.20*health_frag+0.15*dol_pr+0.15*vol_st+0.10*unwind+0.10*vix_s)
    div_s="aligned" if abs(crash_score-risk_off)<0.08 else("tail_heavier" if crash_score>risk_off else "broad_defensive")
    rs=[]; cr=[]
    if 1-h.get("weather",0.5)>=0.58: rs.append("Tactical weather melemah")
    if health_frag>=0.65: rs.append("Market internals rapuh"); cr.append("Breadth rapuh → cascade lebih mudah")
    if dol_pr>=0.62: rs.append("USD pressure mengencang"); cr.append("USD squeeze memperbesar lintas-aset stress")
    if vol_st>=0.62: rs.append("Vol stress naik"); cr.append("Vol stress elevated")
    if unwind>=0.65: rs.append("Crowding unwind risk tinggi"); cr.append("Crowding unwind → deleveraging risk")
    if vix_s>=0.55: rs.append("VIX tidak lagi investable")
    if tail_hedge>=0.65: cr.append("Tail-hedge bid naik — market pricing left-tail risk")
    state="🔴 ELEVATED" if crash_score>=0.65 else("🟡 WATCH" if crash_score>=0.42 else "🟢 CALM")
    # Execution bridge (exact v33 weights)
    quad_sc={"Q1":0.68,"Q2":0.78,"Q3":0.48,"Q4":0.25}.get(q["quad"],0.50)
    health_sc={"Healthy":0.80,"Narrow":0.48,"Fragile":0.34,"Mixed":0.35,"Broken":0.18}.get(h.get("verdict","Mixed"),0.50)
    vix_buck_sc={"Investable":0.78,"Chop":0.42,"Defensive":0.22}.get("Investable" if vix<19 else("Chop" if vix<29 else "Defensive"),0.42)
    exec_score=clamp(EXEC_W["weather"]*h.get("weather",0.5)+EXEC_W["health"]*health_sc+EXEC_W["vix"]*vix_buck_sc+EXEC_W["quad"]*quad_sc+EXEC_W["conf"]*q.get("confidence",0.5)+EXEC_W["cross"]*h.get("trade",0.5)+EXEC_W["crowd"]*(1-unwind)+EXEC_W["shock"]*(1-shock_s)+EXEC_W["crash"]*(1-crash_score))
    exec_mode="🟢 Add on Reset" if exec_score>=0.60 else("🟡 Wait Reclaim" if exec_score>=0.45 else "🔴 Defensive Only")
    if cnn_fg < 0.25:
        cr.append(f"CNN Fear & Greed: {cnn_fg:.0%} — Extreme fear (panic selling risk)")
    elif cnn_fg > 0.75:
        rs.append(f"CNN Fear & Greed: {cnn_fg:.0%} — Extreme greed (crowding risk)")
    if iwm_ath > 0.40:
        cr.append(f"IWM {iwm_ath:.0%} below ATH — breadth deterioration, small cap cascade risk")

    return dict(crash_score=crash_score,risk_off=risk_off,div_state=div_s,state=state,
                vol_stress=vol_st,credit_stress=clamp(0.60*clamp((hy-300)/400 if math.isfinite(hy) else 0.3)+0.40*clamp((ig-80)/120 if math.isfinite(ig) else 0.3)),
                breadth_dmg=health_frag,reasons=rs[:5],crash_reasons=cr[:4],
                exec_score=exec_score,exec_mode=exec_mode,
                cnn_fear_greed=round(cnn_fg,3),
                cnn_crash_signal=round(cnn_crash_signal,3),
                iwm_ath_distance=round(iwm_ath,3),
                cnn_available=cnn_fg_raw is not None)

def build_rotation(q:Dict,h:Dict,f:Dict,prices:Dict[str,pd.Series]={})->Dict:
    s_quad=q["quad"]; m_quad=q["monthly_quad"]
    uup_3m=nf(f.get("uup_3m",f.get("dxy_3m",0.0))); oil_3m=nf(f.get("clf_3m",f.get("oil_3m",0.0)))
    hy=f.get("hy_oas",350.0)
    safe_scores={"XAUUSD":{"Q1":0.30,"Q2":0.35,"Q3":0.72,"Q4":0.60}.get(s_quad,0.5),
                 "USD":{"Q1":0.35,"Q2":0.30,"Q3":0.50,"Q4":0.78}.get(s_quad,0.5),
                 "TLT":{"Q1":0.30,"Q2":0.28,"Q3":0.46,"Q4":0.74}.get(s_quad,0.5),
                 "Defensives":{"Q1":0.35,"Q2":0.30,"Q3":0.52,"Q4":0.64}.get(s_quad,0.5)}
    ben_scores={"WTI":{"Q1":0.40,"Q2":0.60,"Q3":0.70,"Q4":0.28}.get(s_quad,0.5),
                "EEM":{"Q1":0.62,"Q2":0.68,"Q3":0.42,"Q4":0.30}.get(s_quad,0.5),
                "IHSG":{"Q1":0.58,"Q2":0.64,"Q3":0.56,"Q4":0.32}.get(s_quad,0.5),
                "XAUUSD":{"Q1":0.42,"Q2":0.46,"Q3":0.74,"Q4":0.62}.get(s_quad,0.5)}
    safe_scores["XAUUSD"]+=0.10*q.get("inf_shock",0.0)
    if "Inverted" in f.get("yield_curve_state",""): safe_scores["TLT"]*=0.85
    if m_quad!=s_quad:
        ben_scores["IHSG"]*=(1.10 if m_quad in("Q1","Q2") else 0.90)
        ben_scores["EEM"]*=(1.08 if m_quad in("Q1","Q2") else 0.92)
    usd_pen=clamp(uup_3m*5); ben_scores["IHSG"]*=(1.0-0.25*usd_pen); ben_scores["EEM"]*=(1.0-0.20*usd_pen)
    if oil_3m>0.05: ben_scores["WTI"]*=1.10; ben_scores["IHSG"]*=1.05
    if math.isfinite(hy) and hy>400:
        for k in ben_scores: ben_scores[k]*=0.90
    safe_sorted=sorted(safe_scores.items(),key=lambda x:x[1],reverse=True)
    ben_sorted=sorted(ben_scores.items(),key=lambda x:x[1],reverse=True)
    top_safe=safe_sorted[0][0]; top_ben=ben_sorted[0][0]
    em_score=clamp(0.35*ben_scores["EEM"]+0.35*ben_scores["IHSG"]+0.30*(1-usd_pen))
    em_state="Accumulate" if em_score>0.60 else("Wait" if em_score>0.45 else "Avoid")
    # Family spillover
    top_us_bucket=next(iter(US_BUCKETS))
    best_us_scores={}
    for bname,syms in US_BUCKETS.items():
        rs=[ret_n(prices.get(t,pd.Series()),21) for t in syms if t in prices and math.isfinite(ret_n(prices.get(t,pd.Series()),21))]
        if rs: best_us_scores[bname]=np.mean(rs)
    top_us_bucket=max(best_us_scores,key=best_us_scores.get) if best_us_scores else "Growth / Tech"
    spill_us=FAMILY_SPILLOVER_US["long"].get(top_us_bucket,FAMILY_SPILLOVER_US["long"]["default"])
    petro_score=clamp(oil_3m*2+0.5*q.get("inf_shock",0.0)) if oil_3m>0 else 0.0
    return dict(top_safe=top_safe,top_ben=top_ben,safe_rows=[{"route":k,"score":v} for k,v in safe_sorted[:3]],
                ben_rows=[{"route":k,"score":v} for k,v in ben_sorted[:3]],
                safe_meta=ROUTE_META.get(top_safe,ROUTE_META["USD"]),best_meta=ROUTE_META.get(top_ben,ROUTE_META["XAUUSD"]),
                em_score=em_score,em_state=em_state,petro_score=petro_score,
                spill_us=spill_us,top_us_bucket=top_us_bucket)

prices_placeholder:Dict[str,pd.Series]={}

def build_ihsg(prices:Dict[str,pd.Series],q:Dict,f:Dict)->Dict:
    jkse=prices.get("^JKSE",pd.Series()); idr=prices.get("IDR=X",pd.Series()); spy=prices.get("SPY",pd.Series())
    jkse_1m=ret_n(jkse,21); jkse_3m=ret_n(jkse,63); spy_1m=ret_n(spy,21)
    usd_idr_1m=ret_n(idr,21); usd_idr_3m=ret_n(idr,63)
    usd_idr_pressure=clamp(0.5+(nf(usd_idr_1m)/0.08))
    bank_scores=[ret_n(prices.get(t,pd.Series()),21) for t in ["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BRIS.JK"] if math.isfinite(ret_n(prices.get(t,pd.Series()),21))]
    bank_health=clamp(0.5+np.mean(bank_scores)/0.06) if bank_scores else 0.5
    coal_s=[ret_n(prices.get(t,pd.Series()),21) for t in ["ADRO.JK","PTBA.JK","ITMG.JK","HRUM.JK","AADI.JK"] if math.isfinite(ret_n(prices.get(t,pd.Series()),21))]
    met_s=[ret_n(prices.get(t,pd.Series()),21) for t in ["ANTM.JK","INCO.JK","MDKA.JK","TINS.JK"] if math.isfinite(ret_n(prices.get(t,pd.Series()),21))]
    all_comm=coal_s+met_s; comm_spill=clamp(0.5+np.mean(all_comm)/0.07) if all_comm else 0.5
    rel_1m=(jkse_1m-spy_1m) if(math.isfinite(jkse_1m) and math.isfinite(spy_1m)) else 0.0
    foreign_flow=clamp(0.5+rel_1m/0.06)
    flow_state="Nett Beli" if foreign_flow>0.60 else("Nett Jual" if foreign_flow<0.40 else "Netral")
    bi_path=clamp(0.60-0.35*usd_idr_pressure-0.20*(1.0-bank_health))
    bi_state="Potensi cut" if bi_path>0.60 else("Hold" if bi_path>0.42 else "Hawkish / hati-hati")
    sp=0; st=0
    for bname,syms in IHSG_BUCKETS.items():
        rs=[ret_n(prices.get(t,pd.Series()),21) for t in syms if math.isfinite(ret_n(prices.get(t,pd.Series()),21))]
        if rs: st+=1; sp+=(1 if np.mean(rs)>0 else 0)
    breadth_ihsg=sp/max(st,1)
    em_regime_score={"Q1":0.65,"Q2":0.70,"Q3":0.52,"Q4":0.28}.get(q["quad"],0.5)
    # IHSG exact v33 formula
    ihsg_score=clamp(IHSG_W["regime"]*em_regime_score+IHSG_W["em_rotation"]*foreign_flow+IHSG_W["macro_native"]*(1.0-usd_idr_pressure)+IHSG_W["breadth_flow"]*clamp(0.55*breadth_ihsg+0.45*bank_health)+IHSG_W["execution"]*comm_spill)
    exec_mode="🟢 Add on Reset" if ihsg_score>=0.60 else("🟡 Wait Reclaim" if ihsg_score>=0.47 else "🔴 Defensive / Selective Only")
    rel_state="IHSG > SPY (outperform)" if rel_1m>0.01 else("IHSG < SPY (underperform)" if rel_1m<-0.01 else "IHSG ≈ SPY")
    # Petrodollar impact
    oil_3m=nf(f.get("clf_3m",f.get("oil_3m",0.0)))
    petro_impact="Coal exporter benefit" if oil_3m>0.05 else("Mixed" if oil_3m>-0.05 else "Commodity headwind")
    # Leading family for IHSG
    top_sector="Bank"
    best_sec_score={}
    for bname,syms in IHSG_BUCKETS.items():
        rs=[ret_n(prices.get(t,pd.Series()),21) for t in syms if math.isfinite(ret_n(prices.get(t,pd.Series()),21))]
        if rs: best_sec_score[bname]=np.mean(rs)
    if best_sec_score: top_sector=max(best_sec_score,key=best_sec_score.get)
    spill_ihsg=FAMILY_SPILLOVER_IHSG["long"].get(top_sector,FAMILY_SPILLOVER_IHSG["long"]["default"])
    # Stock rows
    stock_rows=[]
    for bname,syms in IHSG_BUCKETS.items():
        for t in syms:
            s=prices.get(t,pd.Series()); r1=ret_n(s,21); r3=ret_n(s,63); tr=ts(s)
            if math.isfinite(r1):
                stock_rows.append({"Ticker":t.replace(".JK",""),"Sektor":bname,"1M":pct(r1),"3M":pct(r3),"Trend":"▲" if tr>=0.5 else "▼","_r1":r1})
    stock_rows.sort(key=lambda x:x["_r1"],reverse=True)
    return dict(jkse_1m=jkse_1m,jkse_3m=jkse_3m,usd_idr_1m=usd_idr_1m,usd_idr_3m=usd_idr_3m,
                usd_idr_pressure=usd_idr_pressure,bank_health=bank_health,comm_spill=comm_spill,
                foreign_flow=foreign_flow,flow_state=flow_state,bi_path=bi_path,bi_state=bi_state,
                breadth_ihsg=breadth_ihsg,ihsg_score=ihsg_score,exec_mode=exec_mode,
                rel_state=rel_state,petro_impact=petro_impact,em_regime=em_regime_score,
                top_sector=top_sector,spill_ihsg=spill_ihsg,stock_rows=stock_rows[:30])

# ── Modular compute adapters ─────────────────────────────────────────────────

def _compat_aliases(f: dict) -> None:
    """Map macro_features key names to monolith aliases so downstream
    functions (build_health, build_crash, build_ihsg, etc.) keep working."""
    # CL=F price aliases
    f.setdefault("clf_1m",   f.get("oil_1m",   float("nan")))
    f.setdefault("clf_3m",   f.get("oil_3m",   float("nan")))
    f.setdefault("gcf_1m",   f.get("gold_1m",  float("nan")))
    f.setdefault("gld_3m",   f.get("gold_3m",  float("nan")))
    f.setdefault("gld_1m",   f.get("gold_1m",  float("nan")))
    f.setdefault("dxy_1m",   f.get("uup_1m",   float("nan")))
    f.setdefault("dxy_3m",   f.get("uup_3m",   float("nan")))
    # Spread aliases from build_market_implied_features (HYG/LQD)
    hyg_1m = f.get("hyg_1m", float("nan")); lqd_1m = f.get("lqd_1m", float("nan"))
    if math.isfinite(hyg_1m) and math.isfinite(lqd_1m):
        f.setdefault("hyg_lqd_spread", float((hyg_1m - lqd_1m) * 100))
    # YoY aliases: macro_features uses "cpi_yoy", monolith also uses "cpi_yoy" — already same
    # Policy aliases
    f.setdefault("policy_rate",     f.get("policy_rate_level",  float("nan")))
    f.setdefault("policy_rate_3m",  f.get("policy_rate_3m_delta", float("nan")))
    f.setdefault("breakeven",       f.get("breakeven_last",     2.2))
    f.setdefault("breakeven_1m",    f.get("breakeven_1m_delta", float("nan")))
    f.setdefault("liq_score",       f.get("liquidity_score",    0.0))
    f.setdefault("m_policy",        f.get("monthly_policy_score",  f.get("policy_score", 0.0)))
    f.setdefault("m_liq",           f.get("monthly_liquidity_score", f.get("liquidity_score", 0.0)))
    f.setdefault("m_shock",         f.get("monthly_inflation_shock", f.get("inflation_shock", 0.0)))
    # Structural/monthly scaffolding keys (monolith uses g_struct_level etc.)
    f.setdefault("g_struct_level",  f.get("growth_structural_level",   f.get("growth_level",   0.0)))
    f.setdefault("g_struct_mom",    f.get("growth_structural_momentum", f.get("growth_momentum", 0.0)))
    f.setdefault("i_struct_level",  f.get("inflation_structural_level",  f.get("inflation_level",  0.0)))
    f.setdefault("i_struct_mom",    f.get("inflation_structural_momentum", f.get("inflation_momentum", 0.0)))
    f.setdefault("g_month_level",   f.get("growth_monthly_level",   f.get("growth_level",   0.0)))
    f.setdefault("g_month_mom",     f.get("growth_monthly_momentum", f.get("growth_momentum", 0.0)))
    f.setdefault("i_month_level",   f.get("inflation_monthly_level",  f.get("inflation_level",  0.0)))
    f.setdefault("i_month_mom",     f.get("inflation_monthly_momentum", f.get("inflation_momentum", 0.0)))
    # data quality keys
    f.setdefault("macro_proxy_share",  f.get("macro_proxy_share", 1.0))
    f.setdefault("fred_real_share",    f.get("fred_real_share", 0.5))
    f.setdefault("data_coverage",      f.get("data_coverage", 0.5))
    f.setdefault("monthly_data_coverage", f.get("monthly_data_coverage", 0.5))
    f.setdefault("structural_obs_reliability",
                 clamp(0.65 * f.get("macro_real_share", 0.5) + 0.35 * f.get("fred_real_share", 0.5)))
    f.setdefault("structural_proxy_scale", clamp(1.0 - f.get("structural_obs_reliability", 0.5)))
    f.setdefault("_proxy_share",    f.get("macro_proxy_share", 1.0))
    f.setdefault("macro_source_quality", f.get("macro_real_share", 0.5))


def _q_posterior_to_dict(p, f: dict) -> dict:
    """Convert RegimePosterior → monolith q dict format (UI unchanged)."""
    import math as _math
    s_quad = p.structural_quad; m_quad = p.monthly_quad
    g_acc = f.get("growth_structural_momentum", f.get("growth_momentum", 0.0)) > 0
    i_acc = f.get("inflation_structural_momentum", f.get("inflation_momentum", 0.0)) > 0
    q_ordered = sorted(p.structural_probs.items(), key=lambda x: -x[1])
    top_spread = q_ordered[0][1] - q_ordered[1][1]
    is_transitional = p.structural_confidence < 0.20 and top_spread < 0.08
    transitional_label = f"{q_ordered[0][0]}/{q_ordered[1][0]}" if is_transitional else s_quad
    cb_map = {
        (0.0, 0.25): "Low-Conviction",
        (0.25, 0.45): "Moderate-Conviction",
        (0.45, 0.65): "Conviction",
        (0.65, 1.01): "High-Conviction",
    }
    cb = next((v for (lo, hi), v in cb_map.items() if lo <= p.structural_confidence < hi), "Low-Conviction")
    return dict(
        quad=s_quad,
        probs=p.structural_probs,
        next_quad=p.structural_next_quad,
        confidence=p.structural_confidence,
        conf_band=cb,
        monthly_quad=m_quad,
        monthly_probs=p.monthly_probs,
        monthly_next=p.monthly_next_quad,
        monthly_conf=p.monthly_confidence,
        divergence=p.divergence_state,
        operating=p.operating_regime,
        flip_hazard=p.flip_hazard,
        deepness=p.deepness,
        duration_mat=p.duration_maturity,
        g_core=p.g_core,
        i_core=p.i_core,
        p_core=p.p_core,
        g_level=p.g_core,
        i_level=p.i_core,
        growth_acc=g_acc,
        infl_acc=i_acc,
        slowdown_flags=f.get("slowdown_flags", 0.0),
        inf_shock=f.get("inflation_shock", 0.0),
        transitional=is_transitional,
        transitional_label=transitional_label,
    )


def _add_tariff_headwind(f: dict) -> None:
    """Inject tariff/oil headwind into structural_slowdown_flags."""
    ism = f.get("ism_last", 51.0)
    ism_sub50 = max(0.0, (50.0 - ism) / 5.0) if math.isfinite(ism) else 0.0
    oil_3m_s = clamp(nf(f.get("clf_3m", f.get("oil_3m", 0.0))) / 0.10)
    usd_s = clamp(nf(f.get("uup_1m", 0.0)) / 0.03)
    tariff_hw = clamp(0.35*ism_sub50 + 0.30*oil_3m_s + 0.20*usd_s + 0.15*max(0.0, f.get("claims_13w_delta", 0.0)/20.0))
    f["tariff_growth_headwind"] = tariff_hw
    # Augment slowdown_flags with tariff headwind
    sf = f.get("slowdown_flags", 0.0)
    f["slowdown_flags"] = clamp(0.55*sf + 0.20*max(0.0, -f.get("growth_structural_momentum", 0.0)) + 0.25*tariff_hw)


# Core tickers needed for regime computation (fast subset)
_CORE_TICKERS = (
    "SPY","QQQ","IWM","RSP","TLT","HYG","LQD","UUP","EEM","^VIX","^VXV",
    "GLD","GC=F","SI=F","CL=F","BZ=F","HG=F","NG=F",
    "XLE","XLF","XLI","XLB","XLK","XLV","XLY","XLP","XLU","XLRE","XLC",
    "^JKSE","IDR=X","BBCA.JK","BBRI.JK","BMRI.JK","ADRO.JK","PTBA.JK",
    "EURUSD=X","AUDUSD=X","JPY=X","BTC-USD","ETH-USD","SOL-USD",
)

@st.cache_data(ttl=TTL_PRICES, show_spinner=False)
def fetch_prices_core(period: str = "2y") -> Dict[str, pd.Series]:
    return fetch_prices(_CORE_TICKERS, period=period)


# ═══════════════════════════════════════════════════════════════════════════════
# NARRATIVE BOTTLENECK ENGINE v11 — Front-run macro narrative detection
# Inspired by Citrini Research, Jukan, Zephyr, Serenity methodology.
# Detects supply-chain, policy, and positioning bottlenecks BEFORE price fully
# reflects them, then maps affected tickers across all markets.
# ═══════════════════════════════════════════════════════════════════════════════

NARRATIVE_REGISTRY = [
    {
        "id": "warsh_liquidity_injection",
        "name": "Warsh Liquidity Injection / Most Hated Rally",
        "category": "policy",
        "desc": "Fed Chair Warsh commits to lower rates. ON RRP drained. Liquidity hunt begins.",
        "triggers": {
            "policy_score": (-1.0, -0.15),      # dovish
            "tlt_1m": (0.015, 1.0),             # bonds rally = cuts priced
            "vix_last": (0.0, 22.0),            # calm
        },
        "confirmers": {
            "uup_1m": (-0.05, 0.0),             # DXY softening
            "m_shock": (0.0, 0.30),             # inflation not exploding
        },
        "tickers": {
            "US": ["QQQ","IWM","XLF","EEM","RSP"],
            "IHSG": ["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK"],
            "FX": ["EURUSD=X","AUDUSD=X","IDR=X"],
            "Commodities": ["GC=F","HG=F"],
            "Crypto": ["BTC-USD","ETH-USD","SOL-USD"],
        },
        "front_run": True,
        "conviction_boost": 0.18,
    },
    {
        "id": "taco_ch2_relief",
        "name": "TACO Ch.2 De-escalation Relief",
        "category": "geopolitics",
        "desc": "Iran de-escalation before FIFA 2026 deadline. Oil rolls off. Risk-on broadens.",
        "triggers": {
            "clf_1m": (-0.15, -0.02),           # oil rolling off 1M
            "vix_last": (0.0, 20.0),            # fear subsiding
            "uup_1m": (-0.05, 0.0),             # DXY soft
        },
        "confirmers": {
            "clf_3m": (-0.20, 0.0),             # oil trend not spiking
        },
        "tickers": {
            "US": ["QQQ","IWM","XLY","XLK","XLI"],
            "IHSG": ["BBCA.JK","BBRI.JK","BMRI.JK","ADRO.JK"],
            "FX": ["EURUSD=X","IDR=X"],
            "Commodities": ["GC=F"],            # gold holds
            "Crypto": ["BTC-USD","ETH-USD","SOL-USD"],
        },
        "front_run": True,
        "conviction_boost": 0.16,
    },
    {
        "id": "stagflation_sticky",
        "name": "Sticky Stagflation / Supply Bottleneck",
        "category": "inflation",
        "desc": "Growth slowing but inflation sticky from supply constraints. Hard assets win.",
        "triggers": {
            "g_struct_level": (-1.0, -0.05),      # growth down
            "headline_core_gap": (0.003, 1.0),   # supply-driven inflation
            "m_shock": (0.10, 1.0),              # monthly shock elevated
        },
        "confirmers": {
            "gld_1m": (0.0, 1.0),                # gold bid
            "uup_1m": (0.0, 0.05),               # USD firm
        },
        "tickers": {
            "US": ["GLD","GC=F","XLE","XLP","XLU"],
            "IHSG": ["ADRO.JK","PTBA.JK","ANTM.JK","TLKM.JK"],
            "FX": ["USD","JPY=X","CHF=X"],
            "Commodities": ["GC=F","CL=F","SI=F"],
            "Crypto": ["BTC-USD"],
        },
        "front_run": False,  # already visible
        "conviction_boost": 0.14,
    },
    {
        "id": "ai_compute_bottleneck",
        "name": "AI Compute / Semiconductor Bottleneck",
        "category": "technology",
        "desc": "AI demand outstrips supply. NVDA/AVGO/AMD lead. Front-run: equipment & power.",
        "triggers": {
            "nvda_1m": (0.05, 1.0),              # NVDA leading
            "qqq_1m": (0.02, 1.0),              # growth tape strong
        },
        "confirmers": {
            "xlk_1m": (0.02, 1.0),             # tech sector broad
        },
        "tickers": {
            "US": ["NVDA","AVGO","AMD","AAPL","MSFT","META"],
            "IHSG": [],  # no direct AI compute yet
            "FX": [],
            "Commodities": ["HG=F","GC=F"],     # copper for data centers
            "Crypto": ["SOL-USD","LINK-USD"],   # AI-crypto proxies
        },
        "front_run": True,
        "conviction_boost": 0.12,
    },
    {
        "id": "indonesia_msci_flow",
        "name": "Indonesia MSCI / EM Rebalancing Bottleneck",
        "category": "em",
        "desc": "OJK-MSCI meeting catalyst. Foreign flow turn = front-run IHSG quality.",
        "triggers": {
            "foreign_flow": (0.55, 1.0),         # IHSG foreign flow turning positive
            "usd_idr_1m": (-0.03, 0.0),        # IDR stabilizing
        },
        "confirmers": {
            "jkse_1m": (0.0, 1.0),             # IHSG momentum
        },
        "tickers": {
            "US": ["EEM"],
            "IHSG": ["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","ADRO.JK"],
            "FX": ["IDR=X"],
            "Commodities": [],
            "Crypto": [],
        },
        "front_run": True,
        "conviction_boost": 0.15,
    },
    {
        "id": "credit_duration_stress",
        "name": "Credit / Duration Bottleneck",
        "category": "credit",
        "desc": "Long-end pain + HY widening. Defensive rotation into TLT & quality.",
        "triggers": {
            "tlt_1m": (-0.05, -0.01),           # bonds selling off
            "hy_oas": (350.0, 9999.0),          # HY spreads elevated
        },
        "confirmers": {
            "vix_last": (18.0, 9999.0),         # vol elevated
        },
        "tickers": {
            "US": ["TLT","SHY","XLP","XLU","XLV"],
            "IHSG": ["TLKM.JK","ICBP.JK","KLBF.JK"],
            "FX": ["JPY=X","CHF=X"],
            "Commodities": ["GC=F"],
            "Crypto": [],
        },
        "front_run": False,
        "conviction_boost": 0.10,
    },
    {
        "id": "smallcap_crowded_unwind",
        "name": "Small Cap Crowded Trade Unwind",
        "category": "positioning",
        "desc": "IWM underperform + narrow breadth = crowded long unwind risk. Fade beta.",
        "triggers": {
            "iwm_1m": (-0.10, -0.02),           # small cap lagging
            "breadth": (0.0, 0.45),             # breadth fragile
        },
        "confirmers": {
            "vix_last": (20.0, 9999.0),         # vol rising
        },
        "tickers": {
            "US": ["IWM","HYG"],                # short or avoid
            "IHSG": ["BSDE.JK","CTRA.JK"],      # property risk
            "FX": [],
            "Commodities": [],
            "Crypto": ["DOGE-USD","ADA-USD"],   # high-beta alts
        },
        "front_run": False,
        "conviction_boost": 0.10,
    },
]


def _check_trigger(feat:Dict, key:str, bounds:Tuple[float,float])->float:
    """Return 1.0 if inside bounds, 0.0 if outside, linear fade at edges."""
    v=feat.get(key)
    if v is None:
        return 0.0
    try:
        v=float(v)
    except Exception:
        return 0.0
    lo,hi=bounds
    if lo<=v<=hi:
        return 1.0
    fade=0.10*max(abs(lo),abs(hi),0.01)
    if v<lo:
        return max(0.0,1.0-(lo-v)/fade)
    return max(0.0,1.0-(v-hi)/fade)


def build_narrative_bottlenecks(f:Dict, q:Dict, h:Dict, prices:Dict[str,pd.Series], rot:Dict)->Dict:
    """
    Detect active narrative bottlenecks and map to tickers per market.
    Returns: {"active": [...], "front_run_picks": [...], "summary": str}
    """
    feat=dict(f)
    feat.update({
        "nvda_1m":ret_n(prices.get("NVDA",pd.Series()),21),
        "qqq_1m":ret_n(prices.get("QQQ",pd.Series()),21),
        "xlk_1m":ret_n(prices.get("XLK",pd.Series()),21),
        "foreign_flow":rot.get("ihsg",{}).get("foreign_flow",0.5) if isinstance(rot.get("ihsg"),dict) else 0.5,
        "usd_idr_1m":rot.get("ihsg",{}).get("usd_idr_1m",0.0) if isinstance(rot.get("ihsg"),dict) else 0.0,
        "jkse_1m":rot.get("ihsg",{}).get("jkse_1m",0.0) if isinstance(rot.get("ihsg"),dict) else 0.0,
        "breadth":h.get("breadth",0.5),
    })

    active=[]
    front_run_picks=[]
    for narr in NARRATIVE_REGISTRY:
        trig_scores=[_check_trigger(feat,k,b) for k,b in narr["triggers"].items()]
        trig_score=float(np.mean(trig_scores)) if trig_scores else 0.0
        conf_scores=[_check_trigger(feat,k,b) for k,b in narr["confirmers"].items()]
        conf_score=float(np.mean(conf_scores)) if conf_scores else 0.0
        composite=0.55*trig_score+0.35*conf_score+0.10*(1.0 if narr["front_run"] else 0.0)
        if composite<0.35:
            continue
        affected={mkt:tks for mkt,tks in narr["tickers"].items() if tks}
        active.append({
            "id":narr["id"],
            "name":narr["name"],
            "category":narr["category"],
            "stage":"front-run" if (narr["front_run"] and composite<0.65) else "active",
            "conviction":round(composite,3),
            "trig_score":round(trig_score,3),
            "conf_score":round(conf_score,3),
            "description":narr["desc"],
            "affected":affected,
            "boost":narr["conviction_boost"],
        })
        if narr["front_run"] and composite>=0.45:
            for mkt,tks in affected.items():
                for tk in tks[:3]:
                    front_run_picks.append({
                        "ticker":tk,
                        "market":mkt,
                        "narrative":narr["name"],
                        "conviction":round(composite,3),
                        "front_run":True,
                        "rationale":narr["desc"][:90],
                    })
    active.sort(key=lambda x:x["conviction"],reverse=True)
    seen=set()
    deduped=[]
    for p in sorted(front_run_picks,key=lambda x:x["conviction"],reverse=True):
        if p["ticker"] not in seen:
            seen.add(p["ticker"])
            deduped.append(p)
    summary="No dominant narrative." if not active else f"Top: {active[0]['name']} ({active[0]['conviction']:.0%})"
    return {"active":active,"front_run_picks":deduped[:15],"summary":summary}


# ═══════════════════════════════════════════════════════════════════════════════
# End Narrative Bottleneck Engine
# ═══════════════════════════════════════════════════════════════════════════════

def load_all()->Dict:
    # ── v11 engine fallback init (prevents UnboundLocalError) ───────────────────
    options_regime:Dict={}; regime_transition:Dict={}; regime_tickers:Dict={}
    narrative_discovery:Dict={}; bei_flow:Dict={}; broker_flow:Dict={}
    broker_confirm:Dict={}; usd_corr:Dict={}; global_quad_data:Dict={}
    regional_surveys:Dict={}; frontrun_data:Dict={}; gdpnow:Dict={}
    data_freshness:Dict={}; backtest_data:Dict={}; intraday_dict:Dict={}
    position_data:Dict={}
    # ────────────────────────────────────────────────────────────────────────────
    price_period=str(os.environ.get("MRP_PRICE_PERIOD","2y") or "2y").strip() or "2y"

    # Phase 1: Core tickers (fast — only what regime engine needs)
    progress_bar = st.progress(0, text="Loading core market data…")
    with st.spinner("Loading core market data (Phase 1/3)…"):
        prices = fetch_prices_core(period=price_period)

    progress_bar.progress(25, text="Phase 2/3: Extended universe…")
    # Phase 2: Extended universe (deferred — for stock tables)
    extended_tickers = tuple(t for t in set(US_TICKERS+IHSG_TICKERS+FX_TICKERS+COMM_TICKERS+CRYPTO_TICKERS) if t not in _CORE_TICKERS)
    try:
        prices_ext = fetch_prices(extended_tickers, period=price_period)
        prices = {**prices, **prices_ext}
    except Exception:
        pass  # Extended load failure doesn't block regime computation

    all_tickers = tuple(prices.keys())
    price_meta=summarize_price_panel(prices,all_tickers)
    progress_bar.progress(45, text="Phase 3/3: FRED macro data (parallel fetch)…")
    with st.spinner("Fetching FRED macro data (parallel)…"): fred=fetch_fred_bundle(tuple(FRED_SERIES.items()))
    progress_bar.progress(70, text="Computing regime signals (modular engine)…")

    # ── REBUILT compute layer: modular engines replace monolith build_macro/build_quad ──
    try:
        from features.macro_features import build_macro_features as _bmf
        from engines.quad_state_engine import QuadStateEngine as _QSE
        # 1. Build f dict from modular features (true Hedgeye RoC, delta_ret_n, etc.)
        f = _bmf(fred, prices)
        # 2. Augment with market-implied micro features (VIX, spreads, yield curve)
        f.update(build_market_implied_features(prices))
        # 3. Build FRED meta (loaded count etc.) for data quality display
        fred_obs, fred_obs_meta, fred_loaded, fred_total = build_macro_observed(fred)
        f.update(fred_obs)
        f["_fred_loaded"] = fred_loaded; f["_fred_total"] = fred_total
        f["data_source_mode"] = (
            "Observed-Heavy" if f.get("macro_real_share",0)>=0.70 else
            "Hybrid" if f.get("macro_real_share",0)>=0.35 else "Proxy-Heavy"
        )
        f["prior_mode"] = "off"
        # 4. Add compat aliases for downstream functions
        _compat_aliases(f)
        # 5. Tariff/oil headwind
        _add_tariff_headwind(f)
        # 6. Compute quad via modular engine (correct policy signs, config/weights.py)
        q_posterior = _QSE().run(f)
        q = _q_posterior_to_dict(q_posterior, f)
    except Exception as _compute_err:
        # Fallback to monolith if modular fails (safety net)
        import traceback; traceback.print_exc()
        f = build_macro(fred, prices, price_meta=price_meta)
        q = build_quad(f)
    # ─────────────────────────────────────────────────────────────────────────────
    h=build_health(prices,f)
    cr=build_crash(f,h,q,prices=prices); rot=build_rotation(q,h,f,prices); ih=build_ihsg(prices,q,f)
    analog=_match_analog(f); pb=build_playbooks(f,q); sc=build_scenarios(q,f,h,analog,pb)
    chk=build_checklists(f,h,q,ih)
    most_hated=build_most_hated_rally_monitor(f,prices)
    family=get_dominant_family(q,f,rot)
    risk_ranges=build_risk_range(prices,f,cr)
    sizing=build_position_sizing(q,h,cr,f,risk_ranges,price_meta)
    asset_chk=build_asset_checklists_full(f,h,q,ih,prices)
    macro_impact=build_macro_impact_all(q,f,rot)
    sw_all=build_strong_weak_all(prices,q)
    route=derive_route_state(q,h,cr)
    news_overlay=build_news_catalyst_overlay(q,f,h,route=route,most_hated=most_hated)
    asset_trans=build_asset_translation(route["primary"],q,h,f,route)
    opps=build_opportunities(prices,q,f,h,rot,ih,most_hated,risk_ranges=risk_ranges,sizing=sizing,price_meta=price_meta,route=route)
    fwd_radar=build_forward_radar(prices,q,f,route=route,opps=opps,risk_ranges=risk_ranges,most_hated=most_hated,news_overlay=news_overlay)
    signal_strength=build_signal_strength(opps,prices,q,f,h,risk_ranges=risk_ranges,route=route,crash=cr,sizing=sizing)
    top_drivers=build_top_drivers_now(q,f,h,cr,route,most_hated,news_overlay)
    # ── New intelligence engines (v11) ──────────────────────────────────────────
    try:
        from engines.regime_transition_engine import RegimeTransitionEngine
        from engines.regime_ticker_engine import RegimeTickerEngine
        from engines.narrative_discovery_engine import NarrativeDiscoveryEngine
        from engines.options_regime_engine import OptionsRegimeEngine
        from data.narrative_news_loader import load_narrative_signals
        from data.bei_flow_loader import load_bei_foreign_flow
        from data.broker_flow_loader import load_broker_flow, get_broker_regime_confirmation
        from dataclasses import asdict as _asdict

        # Build compat regime_posterior from monolith q dict
        class _RegimePosteriorCompat:
            def __init__(self, q):
                self.structural_quad = q.get("quad", "Q?")
                self.monthly_quad = q.get("monthly_quad", q.get("quad", "Q?"))
                self.structural_confidence = q.get("confidence", 0.5)
                self.monthly_confidence = q.get("monthly_conf", 0.5)
                self.flip_hazard = q.get("flip_hazard", 0.3)
                self.divergence_state = q.get("divergence", "aligned")
                self.g_core = q.get("g_core", 0.0)
                self.i_core = q.get("i_core", 0.0)
                self.p_core = q.get("p_core", 0.0)
                self.structural_probs = q.get("probs", {})
                self.monthly_probs = q.get("monthly_probs", {})
                self.structural_next_quad = q.get("next_quad", "Q?")
                self.monthly_next_quad = q.get("monthly_next", "Q?")

        rpc = _RegimePosteriorCompat(q)

        # Build minimal scenario_features from f dict
        scen_feats = {
            "oil_shock": 1.0 if nf(f.get("clf_3m", 0)) > 0.10 else 0.0,
            "petrodollar_shock": clamp(0.4*max(0, nf(f.get("clf_3m",0))/0.12) + 0.3*max(0, nf(f.get("uup_1m",0))/0.04)),
            "em_importer_pain": clamp(0.4*max(0, nf(f.get("clf_3m",0))/0.12) + 0.3*max(0, nf(f.get("uup_1m",0))/0.04)),
            "carry_unwind": clamp(0.4*max(0,nf(f.get("uup_1m",0))/0.04) + 0.3*max(0,-nf(f.get("tlt_1m",0))/0.05)),
            "war_oil_hazard": news_overlay.get("war_oil", 0.0),
            "policy_pressure_hazard": news_overlay.get("policy_pressure", 0.0),
            "credit_stress_hazard": 0.0,
            "relief_hazard": news_overlay.get("relief", 0.0),
        }

        # Options regime
        opt_engine = OptionsRegimeEngine()
        opt_sig = opt_engine.run(prices, macro_quad=q.get("quad","Q?"), vix_last=f.get("vix_last",20.0), market_features=f)
        options_regime = {
            "vix_spot": opt_sig.vix_spot, "vix_3m": opt_sig.vix_3m,
            "term_structure_slope": opt_sig.term_structure_slope,
            "term_structure_state": opt_sig.term_structure_state,
            "vix_bucket": opt_sig.vix_bucket, "vix_regime_signal": opt_sig.vix_regime_signal,
            "vix_sizing_cap": opt_sig.vix_sizing_cap,
            "iv_rv_spread": opt_sig.iv_rv_spread, "vol_premium_state": opt_sig.vol_premium_state,
            "hyg_lqd_spread": opt_sig.hyg_lqd_spread, "credit_regime": opt_sig.credit_regime,
            "options_regime_confirm": opt_sig.options_regime_confirm,
            "regime_alignment_score": opt_sig.regime_alignment_score,
        }

        # Regime transition
        transition_obj = RegimeTransitionEngine().run(f, f, rpc, scen_feats, float(scen_feats.get("oil_shock",0)))
        regime_transition = {
            "current_quad": transition_obj.current_quad,
            "current_monthly_quad": transition_obj.current_monthly_quad,
            "most_likely_next": transition_obj.most_likely_next,
            "front_run_window": transition_obj.front_run_window,
            "front_run_rationale": transition_obj.front_run_rationale,
            "leading_composite": transition_obj.leading_composite,
            "early_warning_signals": transition_obj.early_warning_signals,
            "transition_paths": [
                {"from_quad": p.from_quad, "to_quad": p.to_quad, "probability": p.probability,
                 "timeframe_weeks": p.timeframe_weeks, "early_warning_score": p.early_warning_score,
                 "confirmation_needed": p.confirmation_needed, "invalidators": p.invalidators,
                 "asset_implications": p.asset_implications, "confidence": p.confidence}
                for p in transition_obj.transition_paths
            ],
        }

        # Regime tickers
        ticker_obj = RegimeTickerEngine().run(rpc, transition_output=transition_obj, news_state=scen_feats, scenario_features=scen_feats)
        regime_tickers = {
            "structural_quad": ticker_obj.structural_quad, "monthly_quad": ticker_obj.monthly_quad,
            "front_run_window": ticker_obj.front_run_window,
            "transition_alert": ticker_obj.transition_alert,
            "most_important_signal": ticker_obj.most_important_signal,
            "us_longs": ticker_obj.us_longs, "us_shorts": ticker_obj.us_shorts,
            "ihsg_buys": ticker_obj.ihsg_buys,
            "fx_longs": ticker_obj.fx_longs, "fx_shorts": ticker_obj.fx_shorts,
            "commodity_longs": ticker_obj.commodity_longs, "commodity_shorts": ticker_obj.commodity_shorts,
            "crypto_longs": ticker_obj.crypto_longs, "crypto_shorts": ticker_obj.crypto_shorts,
            "front_run_picks": [
                {"ticker": p.ticker, "market": p.market, "side": p.side,
                 "conviction": p.conviction, "rationale": p.rationale, "front_run": p.front_run}
                for p in ticker_obj.front_run_picks
            ],
        }

        # Narrative discovery
        # Narrative signals: parallel RSS fetch, timeout-protected
        try:
            narr_signals = load_narrative_signals()
        except Exception:
            narr_signals = {"narratives": {}, "top_narratives": [], "generated_at": ""}
        narr_obj = NarrativeDiscoveryEngine().run(
            narrative_signals=narr_signals,
            current_quad=q.get("quad","Q?"), monthly_quad=q.get("monthly_quad","Q?"),
            scenario_features=scen_feats,
        )
        narrative_discovery = {
            "active_narratives": [
                {"name": c.name, "category": c.category, "stage": c.stage,
                 "conviction": c.conviction, "regime_multiplier": c.regime_multiplier,
                 "regime_adjusted_conviction": c.regime_adjusted_conviction,
                 "pump_risk": c.pump_risk, "net_news_score": c.net_news_score,
                 "primary_beneficiaries": c.primary_beneficiaries,
                 "secondary_beneficiaries": c.secondary_beneficiaries,
                 "what_fades": c.what_fades, "claude_insight": c.claude_insight,
                 "confirmation_signals": c.confirmation_signals,
                 "catalyst_type": c.catalyst_type, "action_summary": c.action_summary,
                 "invalidators": c.invalidators, "headlines": c.headlines}
                for c in narr_obj.active_narratives
            ],
            "top_conviction": narr_obj.top_conviction.name if narr_obj.top_conviction else None,
            "early_stage_alerts": [
                {"name": c.name, "stage": c.stage, "conviction": c.conviction,
                 "regime_adjusted_conviction": c.regime_adjusted_conviction,
                 "pump_risk": c.pump_risk, "action_summary": c.action_summary,
                 "claude_insight": c.claude_insight, "catalyst_type": c.catalyst_type,
                 "primary_beneficiaries": c.primary_beneficiaries,
                 "what_fades": c.what_fades, "confirmation_signals": c.confirmation_signals,
                 "invalidators": c.invalidators}
                for c in narr_obj.early_stage_alerts
            ],
            "summary": narr_obj.summary,
        }

        # BEI foreign flow + broker flow
        bei_flow = load_bei_foreign_flow(prices=prices)
        broker_flow = load_broker_flow()
        broker_confirm = get_broker_regime_confirmation(broker_flow, ticker_obj.ihsg_buys)

        # --- USD Correlation (THE mythic variable) ---
        from engines.usd_correlation_engine import build_usd_correlation_matrix
        usd_corr = build_usd_correlation_matrix(prices)

        # --- Global Quad (50 countries) ---
        from engines.global_quad_engine import run_global_quad_engine
        global_quad_data = run_global_quad_engine(
            prices,
            us_structural_quad=q.get("quad","Q3"),
            us_monthly_quad=q.get("monthly_quad","Q2"),
            usd_trend=usd_corr.get("usd_trend","neutral"),
        )

        # --- Regional Survey (ISM New Orders, CapEx, Prices Paid) ---
        from engines.regional_survey_engine import load_regional_surveys
        regional_surveys = load_regional_surveys()

        # --- Front-Run Engine (Signal + Quad ticker selection) ---
        from engines.frontrun_engine import run_frontrun_engine
        frontrun_data = run_frontrun_engine(
            prices,
            s_quad=q.get("quad","Q3"),
            m_quad=q.get("monthly_quad","Q2"),
            usd_trend=usd_corr.get("usd_trend","neutral"),
            usd_correlations=usd_corr.get("correlations",{}),
        )

        # --- GDPNow (forward-looking GDP) ---
        from data.gdpnow_loader import load_gdpnow
        gdpnow = load_gdpnow()

        # --- Data freshness ---
        from engines.data_freshness_engine import build_data_freshness_report
        data_freshness = build_data_freshness_report(fred, prices)

        # --- Backtest (cached per session, expensive) ---
        from engines.backtest_quad_engine import run_backtest, format_backtest_summary
        @st.cache_data(ttl=3600*6, show_spinner=False)
        def _run_backtest_cached(price_keys):
            return run_backtest(prices)
        try:
            # Backtest is expensive on first run — use session state to defer
            if "backtest_done" not in st.session_state:
                bt_results = _run_backtest_cached(tuple(sorted(prices.keys()))[:30])  # limit tickers for speed
                backtest_data = format_backtest_summary(bt_results)
                st.session_state["backtest_done"] = True
                st.session_state["backtest_data"] = backtest_data
            else:
                backtest_data = st.session_state.get("backtest_data", {})
        except Exception:
            backtest_data = {}

        # --- Intraday regime update ---
        from engines.intraday_regime_engine import run_intraday_update
        intraday_update = run_intraday_update(prices, q.get("quad","Q?"))
        intraday_dict = {
            "spy_1d": intraday_update.spy_1d,
            "vix_1d": intraday_update.vix_1d,
            "oil_1d": intraday_update.oil_1d,
            "tlt_1d": intraday_update.tlt_1d,
            "risk_on": intraday_update.risk_on_signal,
            "inflation_pressure": intraday_update.inflation_pressure,
            "flight_to_safety": intraday_update.flight_to_safety,
            "credit_stress": intraday_update.credit_stress,
            "q1_shift": intraday_update.q1_shift,
            "q2_shift": intraday_update.q2_shift,
            "q3_shift": intraday_update.q3_shift,
            "q4_shift": intraday_update.q4_shift,
            "intraday_regime": intraday_update.intraday_regime,
            "signal_strength": intraday_update.signal_strength,
            "summary": intraday_update.summary,
            "action_note": intraday_update.action_note,
        }

        # --- Position tracker ---
        from engines.position_tracker_engine import (
            get_active_positions, enrich_positions_with_prices,
            generate_exit_signals, get_position_history
        )
        raw_positions = get_active_positions()
        active_positions = enrich_positions_with_prices(raw_positions, prices)
        exit_signals = generate_exit_signals(active_positions, q.get("quad","Q?"), q.get("flip_hazard",0.3))
        position_data = {
            "active": [
                {"id":p.id,"ticker":p.ticker,"market":p.market,"side":p.side,
                 "entry_price":p.entry_price,"entry_date":p.entry_date,"entry_quad":p.entry_quad,
                 "size_pct":p.size_pct,"current_price":p.current_price,"pnl_pct":p.pnl_pct,
                 "days_held":p.days_held,"stop_price":p.stop_price,"target_price":p.target_price,
                 "stop_hit":p.stop_hit,"target_hit":p.target_hit,
                 "exit_signal_score":p.exit_signal_score,"notes":p.notes}
                for p in active_positions
            ],
            "exit_signals": [
                {"id":s.position_id,"ticker":s.ticker,"urgency":s.urgency,
                 "reason":s.reason,"action":s.action}
                for s in exit_signals
            ],
            "history": get_position_history(10),
        }

    except Exception as _e_v11:
        import traceback as _tb_v11
        _tb_v11.print_exc()
        # Fallbacks already initialized at top of load_all


    try: progress_bar.empty()
    except Exception: pass
    # ── Narrative Bottleneck Engine call (v11) ────────────────────────────────
    narrative_output=build_narrative_bottlenecks(f,q,h,prices,{"ihsg":ih})
    narrative_front_run=narrative_output.get("front_run_picks",[])
    # ────────────────────────────────────────────────────────────────────────────
    return dict(prices=prices,price_meta=price_meta,fred=fred,f=f,q=q,h=h,crash=cr,rotation=rot,ihsg=ih,
                analog=analog,playbooks=pb,scenarios=sc,checklists=chk,
                most_hated_rally=most_hated,opportunities=opps,signal_strength=signal_strength,family=family,risk_ranges=risk_ranges,
                position_sizing=sizing,asset_checklists=asset_chk,macro_impact=macro_impact,
                forward_radar=fwd_radar,strong_weak_all=sw_all,
                route=route,asset_translation=asset_trans,news_overlay=news_overlay,top_drivers=top_drivers,
                options_regime=options_regime,
                regime_transition=regime_transition,
                regime_tickers=regime_tickers,
                narrative_discovery=narrative_discovery,
                narrative_bottlenecks=narrative_output,
                bei_flow=bei_flow,
                broker_flow=broker_flow,
                broker_confirm=broker_confirm,
                usd_corr=usd_corr,
                global_quad=global_quad_data,
                regional_surveys=regional_surveys,
                frontrun=frontrun_data,
                gdpnow=gdpnow,
                data_freshness=data_freshness,
                backtest_data=backtest_data,
                intraday=intraday_dict,
                positions=position_data,
                decision_context={
                    "route_primary":route.get("primary"),
                    "route_bias":route.get("route_bias"),
                    "long_allowed":route.get("long_allowed"),
                    "short_allowed":route.get("short_allowed"),
                    "position_cap":route.get("position_cap"),
                    "crash_score":cr.get("crash_score"),
                },
                ts=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                build_meta={
                    "app_version":"v10.0-final-macro-brain",
                    "price_period":price_period,
                    "regime_prior_mode":f.get("prior_mode","off"),
                    "signal_enter_threshold":SIGNAL_ENTER_THRESHOLD,
                    "signal_exit_threshold":SIGNAL_EXIT_THRESHOLD,
                    "signal_store_path":str(SIGNAL_STORE_PATH),
                    "markets_integrated_signals":True,
                    "top_drivers_enabled":True,
                    "setup_quality_enabled":True,
                    "risk_range_ttt_enabled":True,
                    "position_sizing_enabled":True,
                })


# ── UI helpers ────────────────────────────────────────────────────────────────
def qb(q:str)->str:
    cls=q.lower() if q in("Q1","Q2","Q3","Q4") else "qunk"
    return f'<span class="qb {cls}">{q}</span>'
def mc(label,value,sub="",cls=""): st.markdown(f'<div class="mc"><div class="lb">{label}</div><div class="vl {cls}">{value}</div>{"<div class=sb>"+sub+"</div>" if sub else""}</div>',unsafe_allow_html=True)
def sh(t): st.markdown(f'<div class="sh">{t}</div>',unsafe_allow_html=True)
def gb(label,v,note="",gd="high"):
    v=clamp(v); fill=v if gd=="high" else 1.0-v
    col="#3dbb6c" if fill>=0.62 else("#e5a020" if fill>=0.38 else "#e05252")
    st.markdown(f'<div class="gb"><div class="gr"><span>{label}</span><span style="color:{col};font-size:11px;font-family:DM Mono,monospace">{v:.0%} {note}</span></div><div class="bg"><div class="fl" style="width:{v*100:.0f}%;background:{col}"></div></div></div>',unsafe_allow_html=True)
def tag(text,kind="b"): return f'<span class="tag tag-{kind}">{text}</span>'
def chk(flag,good_txt="Yes",bad_txt="No"):
    if flag is True: return f'<span class="chk-ok">✓ {good_txt}</span>'
    if flag is False: return f'<span class="chk-no">✗ {bad_txt}</span>'
    return '<span style="opacity:.4">? Unknown</span>'


import math
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

# ── Regime policy (exact from v33 config/regime_policy.py) ────────────────────
QUAD_POLICY = {
    "Q1": {
        "us":          {"long":["Growth/Tech","Quality","Semis/AI"],       "short":["Energy/Value"],         "avoid":["Energy","Small beta"]},
        "ihsg":        {"long":["Bank","Consumer","Telco/Infra"],           "short":["Batu Bara/Energi"],     "avoid":["Logam","Special board"]},
        "fx":          {"long":["Majors","Defensive USD"],                  "short":["Carry beta"],           "avoid":["Commodity FX"]},
        "commodities": {"long":["Gold","Silver","Broad proxy"],             "short":["Industrial metals"],    "avoid":["Energy","Agri"]},
        "crypto":      {"long":["BTC","ETH","SOL","Infra"],                 "short":["High beta alts"],      "avoid":["Meme coins"]},
    },
    "Q2": {
        "us":          {"long":["Growth/Tech","Semis","Energy/Value","Industrials"], "short":["Defensives"],  "avoid":["Bonds"]},
        "ihsg":        {"long":["Bank","Batu Bara/Energi","Logam","Consumer"], "short":["Consumer Def"],     "avoid":["Special board"]},
        "fx":          {"long":["Commodity FX","AUD","CAD"],                "short":["Defensive USD"],       "avoid":["JPY/CHF hedges"]},
        "commodities": {"long":["Oil","Copper","Agri"],                     "short":["Gold"],                "avoid":["Precious"]},
        "crypto":      {"long":["BTC","ETH","L1/L2","DeFi","AI crypto"],   "short":["Micro alts"],          "avoid":["Stables only"]},
    },
    "Q3": {
        "us":          {"long":["Defensives","Energy/Value","Gold via GLD"], "short":["Consumer disc","Small caps","Cyclicals"], "avoid":["QQQ","IWM","HYG"]},
        "ihsg":        {"long":["Batu Bara/Energi","Logam","Consumer Def","Telco/Infra"], "short":["Consumer","Properti"], "avoid":["IDR-sensitive stocks"]},
        "fx":          {"long":["USD","Defensive FX"],                      "short":["Carry","Asia EM FX"],  "avoid":["IDR","TRY","BRL"]},
        "commodities": {"long":["Gold","Silver","Oil (selective)"],         "short":["Copper","Base metals"],"avoid":["Industrial metals"]},
        "crypto":      {"long":["BTC only"],                                "short":["Alts","High beta"],   "avoid":["DeFi","Meme"]},
    },
    "Q4": {
        "us":          {"long":["Defensives","TLT","Gold","Quality"],       "short":["Consumer disc","Small caps","Cyclicals"], "avoid":["Commodities","Junk credit"]},
        "ihsg":        {"long":["Consumer Def","Telco/Infra (TLKM)"],      "short":["Consumer cyc","Logam"], "avoid":["Coal (demand collapse)"]},
        "fx":          {"long":["USD","JPY","CHF"],                         "short":["Carry","Commodity FX"],"avoid":["EM FX"]},
        "commodities": {"long":["Gold"],                                    "short":["Oil","Industrial"],     "avoid":["Agri","Energy"]},
        "crypto":      {"long":["BTC (only)"],                              "short":["All alts"],            "avoid":["High beta entirely"]},
    },
}

# ── Rotation Family definitions (from v33 orchestration/route_layers.py) ──────
ROTATION_FAMILIES = {
    "petrodollar": {
        "name": "Petrodollar Route",
        "desc": "Oil/war shock → freight → importer pain → exporter benefit. USD dan energy dominan.",
        "trigger": "Oil shock / geopolitical event → freight stress → USD tightening",
        "nodes": [
            {"label":"Oil/War Shock",        "role":"Trigger",         "bias":"up",  "why":"Supply risk premium → oil dan freight naik."},
            {"label":"Freight/Energy Stress","role":"First Order",     "bias":"up",  "why":"Higher oil hurts importers, lifts producers."},
            {"label":"Importer Pain/USD↑",   "role":"Second Order",   "bias":"mixed","why":"EM FX tertekan, IDR dan Asia FX rapuh."},
            {"label":"Exporter Winners",     "role":"Expression",     "bias":"up",  "why":"Coal/energy exporter menang. ADRO, PTBA, XLE."},
            {"label":"Breaks If Oil Fades",  "role":"Invalidator",    "bias":"down","why":"Route pecah jika oil dan USD keduanya turun."},
        ],
        "best_expressions": {
            "US":["XLE","XOM","CVX"],   "IHSG":["ADRO.JK","PTBA.JK","AADI.JK"],
            "FX":["USD/IDR short IDR"], "Commodities":["CL=F","BZ=F","GC=F"],
            "Crypto":["BTC (defensive)"],
        },
        "confirms":["Oil > $85 bertahan","ADRO/PTBA outperform","USD/IDR stays elevated"],
        "invalidators":["Oil drops >10% in week","Fed signals cuts urgently","De-escalation confirmed"],
    },
    "em_rotation": {
        "name": "EM Rotation Route",
        "desc": "USD relief → selective EM flows → IHSG/EEM catch-up. Exporters lead dulu.",
        "trigger": "USD softening → EEM breadth improves → IHSG foreign flow turns positive",
        "nodes": [
            {"label":"USD Relief",           "role":"Trigger",         "bias":"down","why":"DXY softens → EM funding condition improves."},
            {"label":"Selective EM Flows",   "role":"First Order",     "bias":"up",  "why":"Exporters dan quality EM first to catch bids."},
            {"label":"Broader Participation","role":"Second Order",    "bias":"up",  "why":"Breadth must broaden beyond just exporters."},
            {"label":"IHSG/EEM Catch-Up",    "role":"Expression",     "bias":"up",  "why":"Banks dan domestic consumer join the rally."},
            {"label":"Breaks If USD Re-Accel","role":"Invalidator",   "bias":"down","why":"Route gagal jika USD kuat kembali."},
        ],
        "best_expressions": {
            "US":["EEM","selective EM-linked"], "IHSG":["BBCA.JK","BBRI.JK","coal exporters"],
            "FX":["Selective EM FX longs"],    "Commodities":["Less defensive skew"],
            "Crypto":["Higher beta watch if liquidity confirms"],
        },
        "confirms":["EEM > SPY 1M dan 3M","USD/IDR stabilizes","IHSG asing nett beli"],
        "invalidators":["USD re-accelerates","Only exporters work","EEM breadth rolls over"],
    },
    "reflation": {
        "name": "Reflation Route",
        "desc": "Growth + inflation keduanya naik. Cyclicals, real assets, dan EM lebar semua menang.",
        "trigger": "ISM >52 + commodity pulse up → earnings revision up → broad risk-on",
        "nodes": [
            {"label":"Growth Reaccel",       "role":"Trigger",         "bias":"up",  "why":"ISM/PMI naik, earnings revision positif."},
            {"label":"Commodity/Cyclical Up","role":"First Order",     "bias":"up",  "why":"Energy, materials, industrials lead."},
            {"label":"Broad Beta Up",        "role":"Second Order",    "bias":"up",  "why":"Small caps, EM, dan quality growth ikut."},
            {"label":"Risk-On Expression",   "role":"Expression",     "bias":"up",  "why":"Seluruh risk asset naik, defensives lag."},
            {"label":"Breaks If Fed Bites",  "role":"Invalidator",    "bias":"down","why":"Tightening terlalu agresif → Q3 pivot."},
        ],
        "best_expressions": {
            "US":["QQQ","IWM","XLE","XLI"],    "IHSG":["BBCA.JK","ADRO.JK","ANTM.JK"],
            "FX":["AUD","CAD","commodity FX"], "Commodities":["Oil","Copper","Agri"],
            "Crypto":["BTC","ETH","L1/L2 alts"],
        },
        "confirms":["ISM >52 dua bulan","IWM outperforms SPY","Commodities breadth positive"],
        "invalidators":["ISM fails to hold >50","Fed overtightens","Credit spreads widen"],
    },
    "growth_scare": {
        "name": "Growth Scare / Defensive Route",
        "desc": "Growth scare dominan. Defensives, TLT, gold, cash menang. Capital preservation mode.",
        "trigger": "ISM <48 + payrolls miss → earnings cuts → broad de-risking",
        "nodes": [
            {"label":"Growth Miss",          "role":"Trigger",         "bias":"down","why":"Data miss → recession fear pricing in."},
            {"label":"Credit/Breadth Break", "role":"First Order",     "bias":"down","why":"HY spreads widen, breadth collapses."},
            {"label":"Risk-Off Cascade",     "role":"Second Order",    "bias":"down","why":"Forced selling: ETFs, momentum, leveraged."},
            {"label":"Defensive Winners",    "role":"Expression",     "bias":"up",  "why":"TLT, gold, defensives, cash all rally."},
            {"label":"Breaks If Fed Pivots", "role":"Invalidator",    "bias":"up",  "why":"Credible Fed cut → risk-on relief squeeze."},
        ],
        "best_expressions": {
            "US":["TLT","XLP","XLU","XLV","GLD"],  "IHSG":["TLKM.JK","ICBP.JK","KLBF.JK"],
            "FX":["USD","JPY","CHF"],               "Commodities":["Gold"],
            "Crypto":["BTC (hold only)","avoid alts"],
        },
        "confirms":["TLT > SPY 1M","Credit spreads keep widening","ISM stays <49"],
        "invalidators":["Fed credible pivot","ISM rebounds from <45","Fiscal stimulus announced"],
    },
}

# ── Determine active rotation family (from v33 route_layers._dominant_family) ─
def get_dominant_family(q:Dict, f:Dict, rot:Dict) -> str:
    petro=rot.get("petro_score",0.0)
    em=rot.get("em_score",0.0)
    oil_3m=f.get("clf_3m",f.get("oil_3m",0.0))
    if not (oil_3m is not None and hasattr(oil_3m,"__float__")): oil_3m=0.0
    try: oil_3m=float(oil_3m)
    except: oil_3m=0.0
    sf=q.get("slowdown_flags",0.0); shock=q.get("inf_shock",0.0)
    flip=q.get("flip_hazard",0.5); quad=q.get("quad","Q3")
    if oil_3m>0.08 or shock>0.30 or petro>0.45: return "petrodollar"
    if em>0.60 and quad in("Q1","Q2"): return "em_rotation"
    if quad in("Q3","Q4") and sf>=0.50: return "growth_scare"
    return "reflation"

# ── Build opportunity rows (Long/Short ranked with entry/target/invalidation) ─
def build_opportunities(prices:Dict[str,pd.Series], q:Dict, f:Dict, h:Dict, rot:Dict, ih:Dict, most_hated:Dict,
                        risk_ranges:Optional[Dict]=None, sizing:Optional[Dict]=None,
                        price_meta:Optional[Dict]=None, route:Optional[Dict]=None) -> List[Dict]:
    """Final opportunity engine: macro + route + Trade/Trend/Tail + sizing aware."""
    risk_ranges = risk_ranges or {}
    sizing = sizing or {}
    price_meta = price_meta or {}
    route = route or {}

    quad=str(q.get("quad","Q3"))
    conf=float(q.get("confidence",0.5) or 0.5)
    monthly_quad=str(q.get("monthly_quad",quad))
    weather=float(h.get("weather",0.5) or 0.5)
    regime_ev=0.60*conf+0.40*weather
    branch_state=str(most_hated.get("branch_state","dormant"))
    posture=str(most_hated.get("posture","Defense / selective only"))
    long_boost=float(most_hated.get("scanner_long_boost",0.0) or 0.0)
    short_penalty=float(most_hated.get("scanner_short_penalty",0.0) or 0.0)
    active_branch=branch_state in {"arming","pre_confirmed","active"}
    hot_branch=branch_state in {"pre_confirmed","active"}
    route_primary=str(route.get("primary","growth_scare"))
    route_conf=float(route.get("confidence",0.5) or 0.5)
    long_allowed=bool(route.get("long_allowed",True))
    short_allowed=bool(route.get("short_allowed",True))
    crash_score=clamp((route.get("crash_score", q.get("crash_score", 0.0)) or 0.0))
    coverage=float(price_meta.get("coverage",1.0) or 1.0)
    short_hist=float(price_meta.get("short_history_share",0.0) or 0.0)
    stale_share=float(price_meta.get("stale_share",0.0) or 0.0)
    data_penalty=float(np.clip(0.45*max(0.0,0.90-coverage)/0.90+0.30*short_hist+0.25*stale_share,0.0,1.0))

    def _market_of(tk:str)->str:
        if tk in IHSG_TICKERS or tk.endswith('.JK'):
            return 'IHSG'
        if tk in FX_TICKERS:
            return 'FX'
        if tk in COMM_TICKERS:
            return 'Commodities'
        if tk in CRYPTO_TICKERS:
            return 'Crypto'
        return 'US'

    def _display(tk:str, market:str)->str:
        if market == 'IHSG':
            return tk.replace('.JK','') + ' (JK)'
        if market in {'Crypto','Commodities','FX'}:
            return disp(tk)
        return tk

    def _ret_score(s:pd.Series,bias:str)->float:
        s=_s(s)
        r1=ret_n(s,21); r3=ret_n(s,63); tr=ts(s)
        if not (math.isfinite(r1) and math.isfinite(r3)):
            return 0.0
        base=0.55*r1+0.45*r3+0.03*(tr-0.5)
        return float(np.nan_to_num(base if bias=='LONG' else -base, nan=0.0))

    def _macro_align(tk:str,bias:str,market:str)->Tuple[float,str]:
        rr=risk_ranges.get(tk,{})
        bullish=rr.get('trade_state')=='bullish' and rr.get('trend_state')=='bullish'
        bearish=rr.get('trade_state')=='bearish' and rr.get('trend_state')=='bearish'
        risk_on={'QQQ','IWM','RSP','XLF','XLI','XLE','EEM','BTC-USD','ETH-USD','SOL-USD','BBCA.JK','BBRI.JK','BMRI.JK','ADRO.JK','PTBA.JK','ANTM.JK'}
        defensives={'TLT','GLD','GC=F','UUP','XLP','XLV','XLU','TLKM.JK'}
        if bias=='LONG':
            if quad in {'Q1','Q2'} and tk in risk_on:
                return (1.0 if bullish or rr.get('buy_dip_ok') else 0.80), '✓'
            if quad=='Q3' and tk in {'GLD','GC=F','UUP','XLE','TLKM.JK','ADRO.JK','PTBA.JK','ANTM.JK'}:
                return (1.0 if bullish or rr.get('buy_dip_ok') else 0.78), '✓'
            if quad=='Q4' and tk in defensives:
                return (1.0 if bullish or rr.get('buy_dip_ok') else 0.78), '✓'
            if rr.get('triple_aligned') and bullish:
                return 0.75, '~'
            return 0.42, '✗'
        else:
            if quad in {'Q3','Q4'} and tk in {'QQQ','IWM','HYG','EEM','BTC-USD','ETH-USD','SOL-USD','^JKSE'}:
                return (1.0 if bearish or rr.get('sell_rip_ok') else 0.78), '✓'
            if quad in {'Q1','Q2'} and tk in {'UUP','TLT'}:
                return (0.72 if bearish or rr.get('sell_rip_ok') else 0.60), '~ Tactical'
            if rr.get('triple_aligned') and bearish:
                return 0.74, '~'
            return 0.40, '✗'

    def _route_align(tk:str,bias:str)->Tuple[float,str]:
        bull_routes={'quality_disinflation','reflation_reaccel','vshape_rebound'}
        bear_routes={'growth_scare','deflationary_riskoff','panic_crash'}
        if bias=='LONG':
            if not long_allowed:
                return 0.20, '✗'
            if route_primary in bull_routes:
                return 1.0 if hot_branch or route_conf>=0.55 else 0.84, '✓'
            if route_primary=='stagflation_persist' and tk in {'GLD','GC=F','UUP','XLE','ADRO.JK','PTBA.JK','ANTM.JK','TLKM.JK'}:
                return 0.90, '✓'
            return 0.55, '~ Tactical'
        else:
            if not short_allowed:
                return 0.20, '✗'
            if route_primary in bear_routes:
                return 1.0 if route_conf>=0.55 else 0.84, '✓'
            if hot_branch and tk in {'UUP','CL=F'}:
                return 0.82, '~ Tactical'
            return 0.52, '~ Tactical'

    def _entry_zone(px:float, rr:Dict, bias:str)->str:
        if not math.isfinite(px) or px<=0:
            return '—'
        if rr:
            if bias=='LONG':
                lo=rr.get('trade_low', px*0.97)
                hi=min(rr.get('trade_basis', px), rr.get('trade_high', px*1.02))
            else:
                lo=max(rr.get('trade_basis', px), rr.get('trade_low', px*0.98))
                hi=rr.get('trade_high', px*1.03)
            return f"{lo:.2f} – {hi:.2f}"
        atr=max(0.02,abs(px)*0.03)
        return f"{px-atr:.2f} – {px-atr*0.3:.2f}" if bias=='LONG' else f"{px+atr*0.3:.2f} – {px+atr:.2f}"

    def _target(px:float, rr:Dict, bias:str)->str:
        if not math.isfinite(px) or px<=0:
            return '—'
        if rr:
            if bias=='LONG':
                t1=rr.get('trend_high', px*1.05); t2=rr.get('tail_high', t1)
                return f"{t1:.2f} / {t2:.2f}"
            t1=rr.get('trend_low', px*0.95); t2=rr.get('tail_low', t1)
            return f"{t1:.2f} / {t2:.2f}"
        return f"{px*1.06:.2f}" if bias=='LONG' else f"{px*0.94:.2f}"

    def _invalidation(px:float, rr:Dict, bias:str)->str:
        if rr:
            if bias=='LONG':
                return f"<{rr.get('trade_low',px*0.97):.2f} then <{rr.get('trend_low',px*0.94):.2f}"
            return f">{rr.get('trade_high',px*1.03):.2f} then >{rr.get('trend_high',px*1.06):.2f}"
        return f"<{px*0.95:.2f}" if bias=='LONG' else f">{px*1.05:.2f}"

    def _holding_window(rr:Dict)->str:
        if rr.get('triple_aligned'):
            return 'Trend / Tail'
        if rr.get('trade_state') == rr.get('trend_state') and rr.get('trade_state') in {'bullish','bearish'}:
            return 'Trade / Trend'
        return 'Trade'

    def _setup_quality(score:float)->str:
        return 'A' if score>=0.72 else ('B' if score>=0.58 else ('C' if score>=0.44 else 'D'))

    def _path_state(macro_txt:str, route_txt:str)->str:
        if macro_txt=='✓' and route_txt=='✓': return 'Primary'
        if 'Tactical' in macro_txt or 'Tactical' in route_txt or '~' in macro_txt or '~' in route_txt: return 'Tactical'
        return 'Watch'

    def _risk_bucket(rr:Dict)->str:
        rq=float(rr.get('range_quality',0.5) or 0.5)
        return 'Tight' if rq>=0.72 else ('Medium' if rq>=0.48 else 'Wide')

    def _rally_overlay(tk:str, market:str, bias:str)->Tuple[float,str,str]:
        if branch_state in {'dormant','watching'}:
            return 0.0,'Neutral',''
        stage_mult={'arming':0.65,'pre_confirmed':0.90,'active':1.00}.get(branch_state,0.0)
        base=long_boost*stage_mult
        if bias=='LONG':
            if market in {'US','Crypto'} and tk in {'QQQ','IWM','RSP','XLF','XLI','EEM','BTC-USD','ETH-USD','SOL-USD'}:
                return base+0.03,'Boosted','Checklist hidup → beta dan catch-up longs dinaikkan'
            if market=='IHSG' and tk in {'BBCA.JK','BBRI.JK','BMRI.JK','TLKM.JK','ADRO.JK','PTBA.JK','ANTM.JK'}:
                return base+0.02,'Boosted','Likuiditas global + potensi flow asing mendukung beneficiaries'
            if market=='Commodities' and tk in {'HG=F','GC=F'}:
                return (0.05 if tk=='HG=F' else 0.02)+(0.01 if hot_branch else 0.0),'Boosted','Copper ikut bantu risk-on; gold tetap boleh jadi hedge'
            if market=='Commodities' and tk=='CL=F':
                return (-0.05 if hot_branch else -0.025),'Fade','De-escalation branch biasanya jadi headwind buat oil'
            if market=='US' and tk in {'UUP','XLP','XLU','XLV','TLT'} and hot_branch:
                return -0.05,'Fade','Saat branch hidup, leadership cenderung pindah dari safe harbor ke beta'
        else:
            if tk in {'QQQ','IWM','EEM','RSP','BTC-USD','ETH-USD','SOL-USD','BNB-USD','XLF','XLI'}:
                return short_penalty-(0.02 if hot_branch else 0.0),'Squeezed','Short ini rawan disqueeze kalau branch hidup'
            if tk=='UUP' and active_branch:
                return max(0.03,base*0.7),'Boosted','Short USD = expression direct dari DXY softening branch'
            if tk=='CL=F' and hot_branch:
                return max(0.03,base*0.6),'Boosted','De-escalation final + oil mean reversion'
        return 0.0,'Neutral',''

    rows=[]
    all_candidates=sorted(set(US_TICKERS+IHSG_TICKERS+FX_TICKERS+COMM_TICKERS+CRYPTO_TICKERS))
    for tk in all_candidates:
        market=_market_of(tk)
        if market=='FX':
            continue  # keep board focused like current scanner
        s=_s(prices.get(tk,pd.Series(dtype=float)))
        rr=risk_ranges.get(tk,{})
        sz=sizing.get(tk,{})
        if len(s)<80:
            continue
        px=last(s)
        if not math.isfinite(px):
            continue

        for bias in ['LONG','SHORT']:
            if bias=='LONG' and not long_allowed and market not in {'Commodities'}:
                continue
            if bias=='SHORT' and not short_allowed and not (hot_branch and tk in {'UUP','CL=F'}):
                continue

            score_ret=_ret_score(s,bias)
            macro_score, macro_txt=_macro_align(tk,bias,market)
            route_score, route_txt=_route_align(tk,bias)
            range_score=(1.0 if rr.get('buy_dip_ok') else 0.72 if rr.get('trade_state')=='bullish' and rr.get('trend_state')=='bullish' else 0.38) if bias=='LONG' else (1.0 if rr.get('sell_rip_ok') else 0.72 if rr.get('trade_state')=='bearish' and rr.get('trend_state')=='bearish' else 0.38)
            size_scalar=float(sz.get('size_scalar_long' if bias=='LONG' else 'size_scalar_short',0.25) or 0.25)
            size_label=str(sz.get('size_current_long' if bias=='LONG' else 'size_current_short','0.25x'))
            rally_adj, rally_fit, rally_note = _rally_overlay(tk, market, bias)
            rr_quality=float(rr.get('range_quality',0.50) or 0.50)

            ev_base=float(np.clip(
                0.24*(0.50+score_ret)+
                0.22*macro_score+
                0.18*route_score+
                0.18*range_score+
                0.18*rr_quality,
                0.0,1.0
            ))
            # ── Narrative Bottleneck boost (v11) ──────────────────────────────────
            narr_boost=0.0
            if 'narrative_front_run' in globals():
                for npick in narrative_front_run:
                    if npick.get("ticker")==tk and npick.get("market")==market:
                        narr_boost=npick.get("conviction",0.0)*0.15  # up to +15% EV
                        break
            # ──────────────────────────────────────────────────────────────────────
            final_ev=float(np.clip(
                (ev_base + rally_adj + narr_boost)
                * (0.72 + 0.28*conf)
                * (0.72 + 0.28*weather)
                * (0.70 + 0.30*route_conf)
                * size_scalar
                * (1.0 - 0.35*data_penalty)
                * (1.0 - 0.35*crash_score if bias=='LONG' else 1.0),
                0.0,1.0
            ))

            if final_ev < 0.12:
                continue
            if bias=='SHORT' and tk not in {'UUP','CL=F','QQQ','IWM','EEM','BTC-USD','ETH-USD','SOL-USD','^JKSE','HYG'} and final_ev < 0.28:
                continue
            if bias=='LONG' and market=='Crypto' and final_ev < 0.24:
                continue

            why_now=[]; why_not=[]
            if macro_txt=='✓': why_now.append('macro aligned')
            else: why_not.append('macro alignment incomplete')
            if route_txt=='✓': why_now.append('route aligned')
            else: why_not.append('route branch not clean')
            if range_score>=0.90: why_now.append('range setup clean')
            elif range_score>=0.60: why_not.append('range not at ideal edge yet')
            else: why_not.append('durations not aligned')
            if data_penalty>=0.35: why_not.append('data confidence reduced')
            if rally_note: why_now.append(rally_note)

            setup=_setup_quality(final_ev)
            path=_path_state(macro_txt, route_txt)
            risk_bucket=_risk_bucket(rr)
            bias_label='▲ LONG' if bias=='LONG' else '▼ SHORT'
            if final_ev<0.36:
                bias_label='WATCH-LONG' if bias=='LONG' else 'WATCH-SHORT'
            rows.append({
                'Ticker': _display(tk, market),
                'Market': market,
                'Bias': bias_label,
                'Horizon': _holding_window(rr),
                'Entry Zone': _entry_zone(px, rr, bias),
                'Target': _target(px, rr, bias),
                'Invalidation': _invalidation(px, rr, bias),
                'Why Now': '; '.join(why_now) if why_now else 'none',
                'Why Not Yet': '; '.join(why_not) if why_not else 'none',
                'Setup': setup,
                'Path': path,
                'Risk Bucket': risk_bucket,
                'EV': f"{final_ev:.0%}",
                'Conf': f"{conf:.0%}",
                'Macro Aligned': macro_txt,
                'Route Aligned': route_txt,
                'Range Aligned': '✓' if range_score>=0.90 else ('~' if range_score>=0.60 else '✗'),
                'Rally Fit': rally_fit,
                'Sizing': size_label,
                'Rally State': posture,
                'Trade State': rr.get('trade_state','neutral'),
                'Trend State': rr.get('trend_state','neutral'),
                'Tail State': rr.get('tail_state','neutral'),
                '_score': score_ret,
                '_ev': final_ev,
                '_raw_ticker': tk,
            })

    longs=[r for r in rows if 'LONG' in r['Bias']]
    shorts=[r for r in rows if 'SHORT' in r['Bias']]

    # fallback: never leave Markets board completely empty on selective / low-conviction days
    if not longs and not shorts:
        if quad in {'Q1','Q2'}:
            fallback_longs=['QQQ','XLE','BBCA.JK','ADRO.JK','GC=F']
            fallback_shorts=['TLT','UUP']
        elif quad=='Q3':
            fallback_longs=['GLD','GC=F','XLE','TLKM.JK','ADRO.JK']
            fallback_shorts=['QQQ','IWM','EEM','BTC-USD']
        else:
            fallback_longs=['TLT','GLD','TLKM.JK','BBCA.JK']
            fallback_shorts=['QQQ','IWM','HYG','BTC-USD']

        def _mk_fallback(tk:str,bias:str):
            s=_s(prices.get(tk,pd.Series(dtype=float)))
            if len(s)<40:
                return None
            px=last(s)
            if not math.isfinite(px):
                return None
            market=_market_of(tk)
            rr=risk_ranges.get(tk,{})
            sz=sizing.get(tk,{})
            size_label=str(sz.get('size_current_long' if bias=='LONG' else 'size_current_short','0.25x'))
            return {
                'Ticker': _display(tk, market),
                'Market': market,
                'Bias': 'WATCH-LONG' if bias=='LONG' else 'WATCH-SHORT',
                'Horizon': _holding_window(rr) if rr else 'Trade',
                'Entry Zone': _entry_zone(px, rr, bias),
                'Target': _target(px, rr, bias),
                'Invalidation': _invalidation(px, rr, bias),
                'Why Now': 'fallback watchlist to avoid empty board on selective day',
                'Why Not Yet': 'conviction below launch threshold',
                'Setup': 'C',
                'Path': 'Watch',
                'Risk Bucket': _risk_bucket(rr) if rr else 'Medium',
                'EV': '18%',
                'Conf': f"{conf:.0%}",
                'Macro Aligned': '~',
                'Route Aligned': '~',
                'Range Aligned': '~' if rr else '✗',
                'Rally Fit': 'Neutral',
                'Sizing': size_label,
                'Rally State': posture,
                'Trade State': rr.get('trade_state','neutral') if rr else 'neutral',
                'Trend State': rr.get('trend_state','neutral') if rr else 'neutral',
                'Tail State': rr.get('tail_state','neutral') if rr else 'neutral',
                '_score': 0.0,
                '_ev': 0.18,
                '_raw_ticker': tk,
            }

        for tk in fallback_longs:
            row=_mk_fallback(tk,'LONG')
            if row is not None:
                longs.append(row)
        for tk in fallback_shorts:
            row=_mk_fallback(tk,'SHORT')
            if row is not None:
                shorts.append(row)

    longs.sort(key=lambda x:(x['_ev'], x.get('Rally Fit')=='Boosted', x.get('Macro Aligned') in {'✓','~ Tactical'}), reverse=True)
    shorts.sort(key=lambda x:(x['_ev'], x.get('Rally Fit')=='Boosted'), reverse=True)
    return longs + shorts


def build_top_drivers_now(q:Dict, f:Dict, h:Dict, cr:Dict, route:Dict, most_hated:Dict, news_overlay:Dict)->List[Dict]:
    drivers=[]
    def add(label:str, score:float, tone:str, why:str, tag:str=""):
        sc=clamp(score)
        if sc<=0.05:
            return
        drivers.append({"label":label,"score":sc,"tone":tone,"why":why,"tag":tag})

    slowdown=float(q.get("slowdown_flags",0.0) or 0.0)
    add("Growth slowdown", slowdown, "bad" if slowdown>=0.50 else "warn", "Claims / ISM / housing memberi sinyal perlambatan growth.", "macro")

    inf=float(q.get("inf_shock",0.0) or 0.0)
    add("Inflation shock", inf, "bad" if inf>=0.45 else "warn", "Oil / breakeven / USD mendorong tekanan inflasi jangka pendek.", "macro")

    usd_1m=float(nf(f.get("uup_1m", f.get("dxy_1m", 0.0)), 0.0))
    if abs(usd_1m) >= 0.012:
        add("USD pressure" if usd_1m>0 else "USD easing", abs(usd_1m)/0.04, "bad" if usd_1m>0 else "good", "Dollar mengubah risk appetite lintas aset dan EM sensitivity.", "cross-asset")

    oil_1m=float(nf(f.get("clf_1m", f.get("oil_1m", 0.0)), 0.0))
    if abs(oil_1m) >= 0.02:
        add("Oil impulse" if oil_1m>0 else "Oil rollback", abs(oil_1m)/0.08, "warn" if oil_1m>0 else "good", "Gerak oil mempengaruhi inflation branch, exporters, dan margin pressure.", "commodities")

    breadth=float(h.get("breadth", 0.5) or 0.5)
    if breadth <= 0.45:
        add("Breadth fragility", (0.50-breadth)/0.20, "bad", "Partisipasi sempit; rally lebih rawan unwind jika leaders gagal.", "internals")
    elif breadth >= 0.60:
        add("Breadth healing", (breadth-0.50)/0.20, "good", "Partisipasi melebar; tape lebih sehat untuk beta dan follow-through.", "internals")

    crash_score=float(cr.get("crash_score",0.0) or 0.0)
    if crash_score >= 0.42:
        add("Tail-risk pressure", crash_score, "bad" if crash_score>=0.60 else "warn", "Crash meter belum jinak; sizing dan invalidation harus lebih disiplin.", "risk")

    clear_count=int(most_hated.get("hard_clear_count", most_hated.get("clear_count", 0)) or 0)
    if clear_count >= 2:
        add("Liquidity / relief branch", clear_count/4.0, "good" if clear_count>=3 else "warn", "Checklist rally makin hidup; catch-up beta dan squeeze risk ikut naik.", "branch")

    route_meta=(route or {}).get("primary_meta", {}) or {}
    if route_meta:
        add(route_meta.get("label","Primary route"), 0.45 + 0.35*float(q.get("confidence",0.0) or 0.0), "good", route_meta.get("desc",""), "route")

    if news_overlay:
        nl=str(news_overlay.get("label",""))
        if nl:
            tone_map={"good":"good","warn":"warn","bad":"bad","neu":"warn"}
            add(nl, max(float(news_overlay.get("war_oil",0.0) or 0.0), float(news_overlay.get("policy_pressure",0.0) or 0.0), float(news_overlay.get("relief",0.0) or 0.0), 0.30), tone_map.get(str(news_overlay.get("cls","neu")),"warn"), str(news_overlay.get("desc",""))[:110], "catalyst")

    drivers.sort(key=lambda x:(x["score"], x["tone"]=="bad", x["tone"]=="good"), reverse=True)
    return drivers[:6]


def render_top_drivers_now(drivers:List[Dict], title:str="🧠 TOP DRIVERS NOW") -> None:
    if not drivers:
        return
    sh(title)
    cols=st.columns(min(3, len(drivers)))
    for idx,drv in enumerate(drivers[:min(6,len(drivers))]):
        col=cols[idx % len(cols)]
        tone=str(drv.get("tone","warn"))
        css=tone if tone in {"good","warn","bad"} else "neu"
        with col:
            st.markdown(
                '<div class="mc" style="border-left:3px solid currentColor">'+
                '<div class="lb">'+html.escape(str(drv.get("tag","driver")).upper())+'</div>'+
                '<div class="vl '+css+'" style="font-size:16px">'+html.escape(str(drv.get("label","—")))+'</div>'+
                '<div style="font-size:11px;opacity:.76;line-height:1.45;margin-top:4px">'+html.escape(str(drv.get("why","")))+'</div>'+
                '<div style="font-family:DM Mono,monospace;font-size:10px;opacity:.45;margin-top:5px">Intensity '+f'{float(drv.get("score",0.0)):.0%}'+'</div>'+
                '</div>',
                unsafe_allow_html=True,
            )


def _signal_snapshot_date()->str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")


def _safe_float(v, default:float=float("nan")) -> float:
    try:
        if v is None or (isinstance(v, str) and not v.strip()):
            return default
        return float(v)
    except Exception:
        return default


def _coerce_pctish(v, default:float=0.0) -> float:
    if isinstance(v, str):
        s=v.strip().replace(",","")
        if s.endswith("%"):
            try:
                return float(s[:-1])/100.0
            except Exception:
                return default
    return _safe_float(v, default)


def compute_trade_state(s:pd.Series) -> str:
    s2=_s(s)
    if len(s2)<25:
        return "neutral"
    px=float(s2.iloc[-1])
    ma20=float(s2.rolling(20).mean().iloc[-1])
    ma50=float(s2.rolling(50).mean().iloc[-1]) if len(s2)>=50 else ma20
    if px>ma20 and ma20>=ma50:
        return "bullish"
    if px<ma20 and ma20<=ma50:
        return "bearish"
    return "neutral"


def compute_trend_state(s:pd.Series) -> str:
    s2=_s(s)
    if len(s2)<100:
        return "neutral"
    px=float(s2.iloc[-1])
    ma50=float(s2.rolling(50).mean().iloc[-1])
    ma100=float(s2.rolling(100).mean().iloc[-1])
    if px>ma50 and ma50>=ma100:
        return "bullish"
    if px<ma50 and ma50<=ma100:
        return "bearish"
    return "neutral"


def compute_signal_score(s:pd.Series, bias:str, ev_hint:float=0.5) -> float:
    r1=nf(ret_n(s,21),0.0)
    r3=nf(ret_n(s,63),0.0)
    tr=nf(ts(s)-0.5,0.0)
    direction=1.0 if "LONG" in str(bias) else -1.0
    raw=direction*(0.55*r1+0.35*r3+0.10*tr)+0.25*(ev_hint-0.5)
    return float(np.nan_to_num(raw, nan=0.0))


def init_signal_store() -> None:
    SIGNAL_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(SIGNAL_STORE_PATH)) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS signal_snapshots (
            asof_date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            ticker_display TEXT,
            market TEXT,
            bias TEXT,
            signal_active INTEGER,
            status_today TEXT,
            signal_score REAL,
            trade_state TEXT,
            trend_state TEXT,
            entry_close REAL,
            last_close REAL,
            pct_since_signal REAL,
            signal_start_date TEXT,
            days_on INTEGER,
            opportunity_ev REAL,
            macro_aligned TEXT,
            horizon TEXT,
            why_now TEXT,
            quad TEXT,
            monthly_quad TEXT,
            PRIMARY KEY (asof_date, ticker, market, bias)
        )
        """)
        conn.commit()


def read_prev_signal_state(asof_date:str) -> pd.DataFrame:
    init_signal_store()
    with sqlite3.connect(str(SIGNAL_STORE_PATH)) as conn:
        cur=conn.execute(
            "SELECT MAX(asof_date) FROM signal_snapshots WHERE asof_date < ? AND signal_active = 1",
            (asof_date,)
        )
        row=cur.fetchone()
        prev_date=row[0] if row else None
        if not prev_date:
            return pd.DataFrame()
        return pd.read_sql_query(
            "SELECT * FROM signal_snapshots WHERE asof_date = ? AND signal_active = 1",
            conn, params=(prev_date,)
        )


def write_signal_snapshot(active_df:pd.DataFrame, removed_df:pd.DataFrame, asof_date:str) -> None:
    init_signal_store()
    cols=[
        "asof_date","ticker","ticker_display","market","bias","signal_active","status_today",
        "signal_score","trade_state","trend_state","entry_close","last_close","pct_since_signal",
        "signal_start_date","days_on","opportunity_ev","macro_aligned","horizon","why_now",
        "quad","monthly_quad"
    ]
    frames=[]
    for df in (active_df, removed_df):
        if isinstance(df,pd.DataFrame) and not df.empty:
            frames.append(df[cols].copy())
    with sqlite3.connect(str(SIGNAL_STORE_PATH)) as conn:
        conn.execute("DELETE FROM signal_snapshots WHERE asof_date = ?", (asof_date,))
        for frame in frames:
            frame.to_sql("signal_snapshots", conn, if_exists="append", index=False)
        conn.commit()


def build_signal_strength(opps:List[Dict], prices:Dict[str,pd.Series], q:Dict, f:Dict, h:Dict,
                          risk_ranges:Optional[Dict]=None, route:Optional[Dict]=None,
                          crash:Optional[Dict]=None, sizing:Optional[Dict]=None) -> Dict:
    """Lifecycle engine: Added / Active / Weakening / Removed / Invalidated."""
    risk_ranges = risk_ranges or {}
    route = route or {}
    crash = crash or {}
    sizing = sizing or {}

    asof_date=_signal_snapshot_date()
    prev_df=read_prev_signal_state(asof_date)
    prev_map={}
    if isinstance(prev_df,pd.DataFrame) and not prev_df.empty:
        for _,row in prev_df.iterrows():
            prev_map[(str(row.get('ticker','')), str(row.get('market','')), str(row.get('bias','')))] = row.to_dict()

    route_conf=float(route.get('confidence',0.5) or 0.5)
    crash_score=clamp(crash.get('crash_score',0.0))
    long_allowed=bool(route.get('long_allowed',True))
    short_allowed=bool(route.get('short_allowed',True))

    def _status(score_now:float, score_prev:float, invalidated:bool)->str:
        if invalidated:
            return 'Invalidated'
        if score_now >= SIGNAL_ENTER_THRESHOLD and score_prev < SIGNAL_ENTER_THRESHOLD:
            return 'added'
        if score_now >= SIGNAL_ENTER_THRESHOLD and score_prev >= SIGNAL_ENTER_THRESHOLD:
            return 'remaining'
        if SIGNAL_EXIT_THRESHOLD <= score_now < SIGNAL_ENTER_THRESHOLD and score_prev >= SIGNAL_ENTER_THRESHOLD:
            return 'weakening'
        return 'removed'

    active_rows=[]
    current_keys=set()
    for r in opps:
        raw_ticker=str(r.get('_raw_ticker') or r.get('Ticker') or '')
        market=str(r.get('Market',''))
        bias=str(r.get('Bias',''))
        if not raw_ticker or not market or not bias or bias=='WATCH':
            continue
        s=prices.get(raw_ticker,pd.Series())
        if _s(s).empty:
            continue
        current_close=last(s)
        if not math.isfinite(current_close):
            continue
        key=(raw_ticker,market,bias)
        current_keys.add(key)
        prev=prev_map.get(key,{})
        prev_score=_safe_float(prev.get('signal_score'),0.0)
        rr=risk_ranges.get(raw_ticker,{})
        sz=sizing.get(raw_ticker,{})

        trade_state=str(rr.get('trade_state','neutral'))
        trend_state=str(rr.get('trend_state','neutral'))
        tail_state=str(rr.get('tail_state','neutral'))
        triple_aligned=bool(rr.get('triple_aligned',False))
        opp_score=_safe_float(r.get('_ev',0.0),0.0)
        size_scalar=_safe_float(sz.get('size_scalar_long' if 'LONG' in bias else 'size_scalar_short'),0.25)
        macro_fit=1.0 if str(r.get('Macro Aligned','')).startswith('✓') else 0.70
        route_fit=1.0 if str(r.get('Route Aligned','')).startswith('✓') else 0.65
        range_fit=1.0 if str(r.get('Range Aligned','')).startswith('✓') else 0.60
        invalidated=False
        if 'LONG' in bias and not long_allowed:
            invalidated=True
        if 'SHORT' in bias and not short_allowed:
            invalidated=True
        if 'LONG' in bias and crash_score>=0.75:
            invalidated=True
        if 'LONG' in bias and trade_state=='bearish' and trend_state=='bearish':
            invalidated=True
        if 'SHORT' in bias and trade_state=='bullish' and trend_state=='bullish':
            invalidated=True

        signal_score=float(np.clip(
            opp_score*(0.55+0.20*macro_fit+0.15*route_fit+0.10*range_fit)*(0.70+0.30*size_scalar)*(0.85+0.15*route_conf)*(1.0-0.30*crash_score if 'LONG' in bias else 1.0),
            -1.0,1.0
        ))
        status_today=_status(signal_score, prev_score, invalidated)
        if status_today in {'removed','Invalidated'}:
            continue
        signal_start_date=str(prev.get('signal_start_date') or asof_date)
        entry_close=_safe_float(prev.get('entry_close'), current_close)
        if not prev or status_today=='added':
            signal_start_date=asof_date
            entry_close=current_close
        try:
            days_on=max((datetime.date.fromisoformat(asof_date)-datetime.date.fromisoformat(signal_start_date)).days+1,1)
        except Exception:
            days_on=int(_safe_float(prev.get('days_on'),1))
        pct_since=(current_close/entry_close-1.0) if (math.isfinite(current_close) and math.isfinite(entry_close) and entry_close) else float('nan')
        if 'SHORT' in bias:
            pct_since *= -1.0
        active_rows.append({
            'asof_date':asof_date,
            'ticker':raw_ticker,
            'ticker_display':str(r.get('Ticker', raw_ticker)),
            'market':market,
            'bias':bias,
            'signal_active':1,
            'status_today':status_today,
            'signal_score':signal_score,
            'trade_state':trade_state,
            'trend_state':trend_state,
            'tail_state':tail_state,
            'entry_close':entry_close,
            'last_close':current_close,
            'pct_since_signal':pct_since,
            'signal_start_date':signal_start_date,
            'days_on':int(days_on),
            'opportunity_ev':opp_score,
            'macro_aligned':str(r.get('Macro Aligned','')),
            'horizon':str(r.get('Horizon','')),
            'why_now':str(r.get('Why Now','')),
            'quad':str(q.get('quad','')),
            'monthly_quad':str(q.get('monthly_quad','')),
        })

    removed_rows=[]
    for key,prev in prev_map.items():
        if key in current_keys:
            continue
        ticker,market,bias=key
        s=prices.get(ticker,pd.Series())
        current_close=last(s) if not _s(s).empty else _safe_float(prev.get('last_close'))
        entry_close=_safe_float(prev.get('entry_close'), current_close)
        pct_since=(current_close/entry_close-1.0) if (math.isfinite(current_close) and math.isfinite(entry_close) and entry_close) else float('nan')
        if 'SHORT' in bias:
            pct_since *= -1.0
        signal_start_date=str(prev.get('signal_start_date', asof_date))
        try:
            days_on=max((datetime.date.fromisoformat(asof_date)-datetime.date.fromisoformat(signal_start_date)).days+1,1)
        except Exception:
            days_on=int(_safe_float(prev.get('days_on'),1))
        removed_rows.append({
            'asof_date':asof_date,
            'ticker':ticker,
            'ticker_display':str(prev.get('ticker_display', ticker)),
            'market':market,
            'bias':bias,
            'signal_active':0,
            'status_today':'removed',
            'signal_score':_safe_float(prev.get('signal_score'), float('nan')),
            'trade_state':str(prev.get('trade_state','neutral')),
            'trend_state':str(prev.get('trend_state','neutral')),
            'tail_state':str(prev.get('tail_state','neutral')),
            'entry_close':entry_close,
            'last_close':current_close,
            'pct_since_signal':pct_since,
            'signal_start_date':signal_start_date,
            'days_on':int(days_on),
            'opportunity_ev':_safe_float(prev.get('opportunity_ev'), float('nan')),
            'macro_aligned':str(prev.get('macro_aligned','')),
            'horizon':str(prev.get('horizon','')),
            'why_now':str(prev.get('why_now','Signal no longer qualifies under current state')),
            'quad':str(q.get('quad','')),
            'monthly_quad':str(q.get('monthly_quad','')),
        })

    active_df=pd.DataFrame(active_rows)
    removed_df=pd.DataFrame(removed_rows)
    write_signal_snapshot(active_df, removed_df, asof_date)

    long_active=active_df[active_df['bias'].str.contains('LONG', na=False)] if not active_df.empty else pd.DataFrame()
    short_active=active_df[active_df['bias'].str.contains('SHORT', na=False)] if not active_df.empty else pd.DataFrame()
    added_df=active_df[active_df['status_today']=='added'].copy() if not active_df.empty else pd.DataFrame()
    remaining_df=active_df[active_df['status_today']=='remaining'].copy() if not active_df.empty else pd.DataFrame()
    weakening_df=active_df[active_df['status_today']=='weakening'].copy() if not active_df.empty else pd.DataFrame()

    if not active_df.empty:
        active_df=active_df.sort_values(['days_on','pct_since_signal'], ascending=[False,False], na_position='last')
    if not removed_df.empty:
        removed_df=removed_df.sort_values(['days_on','pct_since_signal'], ascending=[False,False], na_position='last')
    if not added_df.empty:
        added_df=added_df.sort_values(['signal_score','pct_since_signal'], ascending=[False,False], na_position='last')
    if not remaining_df.empty:
        remaining_df=remaining_df.sort_values(['days_on','pct_since_signal'], ascending=[False,False], na_position='last')
    if not weakening_df.empty:
        weakening_df=weakening_df.sort_values(['signal_score','pct_since_signal'], ascending=[False,False], na_position='last')

    market_summary={}
    market_order=['US','IHSG','FX','Commodities','Crypto']
    for market in market_order:
        adf=active_df[active_df['market']==market].copy() if not active_df.empty else pd.DataFrame()
        rdf=removed_df[removed_df['market']==market].copy() if not removed_df.empty else pd.DataFrame()
        m_added=added_df[added_df['market']==market].copy() if not added_df.empty else pd.DataFrame()
        m_remaining=remaining_df[remaining_df['market']==market].copy() if not remaining_df.empty else pd.DataFrame()
        market_summary[market]={
            'active_total':int(len(adf)),
            'active_longs':int(len(adf[adf['bias'].str.contains('LONG', na=False)])) if not adf.empty else 0,
            'active_shorts':int(len(adf[adf['bias'].str.contains('SHORT', na=False)])) if not adf.empty else 0,
            'added_today':int(len(m_added)),
            'remaining_total':int(len(m_remaining)),
            'removed_today':int(len(rdf)),
            'best_active':str(adf.iloc[0]['ticker_display']) if not adf.empty else '—',
            'best_added':str(m_added.iloc[0]['ticker_display']) if not m_added.empty else '—',
            'best_removed':str(rdf.iloc[0]['ticker_display']) if not rdf.empty else '—',
        }

    return {
        'asof_date':asof_date,
        'active':active_df,
        'added':added_df,
        'remaining':remaining_df,
        'weakening':weakening_df,
        'removed':removed_df,
        'invalidated':pd.DataFrame(),
        'market_summary':market_summary,
        'summary':{
            'active_longs':int(len(long_active)),
            'active_shorts':int(len(short_active)),
            'added_today':int(len(added_df)),
            'removed_today':int(len(removed_df)),
            'active_total':int(len(active_df)),
        },
    }


# ── Checklist engine (v33 inspired) ───────────────────────────────────────────
def _chk(score:float)->(str,str):
    """Returns (symbol, color_class) for a checklist item."""
    if score>=0.62: return "✓","good"
    if score>=0.42: return "~","warn"
    return "✗","bad"

def build_checklists(f:Dict,h:Dict,q:Dict,ih:Dict)->Dict:
    """v33-style checklist: ✓/✗/? per condition per market."""
    sf=q.get("slowdown_flags",0); shock=q.get("inf_shock",0)
    g_acc=q.get("growth_acc",False); i_acc=q.get("infl_acc",False)
    vix=f.get("vix_last",20.0); hy=f.get("hy_oas",350.0)
    uup_1m=nf(f.get("uup_1m",0.0)); yc=f.get("yield_curve_state","")

    # Global checklist (Health tab)
    global_items=[
        ("Growth accelerating",clamp(0.5+0.5*float(g_acc)),
         "INDPRO/payrolls trending up" if g_acc else "Growth momentum slowing"),
        ("Inflasi terkendali",clamp(1.0-i_acc*0.6-shock*0.4),
         "Core inflation falling/stable" if not i_acc else "Inflation re-accelerating"),
        ("USD/DXY tidak tekanan",clamp(0.5-uup_1m*8),
         "Dollar stable or weakening" if uup_1m<0.01 else "USD strengthening = EM headwind"),
        ("Yield curve normal",clamp(0.70 if "Normal" in yc or "Steep" in yc else (0.35 if "Flat" in yc else 0.15)),
         yc),
        ("Breadth sehat",h.get("breadth",0.5),
         f"Sektor di atas 50-DMA: {h.get('sec_above50',0)}/11"),
        ("Credit aman (HY spreads)",clamp(1.0-(hy-250)/450) if math.isfinite(hy) else 0.5,
         f"HY OAS: {hy:.0f}bps" if math.isfinite(hy) else "Proxy mode"),
        ("VIX investable",clamp(1.0-(vix-13)/20),
         "Investable" if vix<19 else ("Chop" if vix<29 else "Defensive")),
        ("Tidak ada shock aktif",clamp(1.0-shock*2),
         "No major inflation/oil shock" if shock<0.2 else f"Shock level: {shock:.2f}"),
    ]

    # IHSG checklist
    ihsg_items=[
        ("USD/IDR aman",1-ih.get("usd_idr_pressure",0.5),
         f"IDR 1M: {pct(ih.get('usd_idr_1m',float('nan')))} (naik=buruk)"),
        ("Asing nett beli",ih.get("foreign_flow",0.5),
         f"Flow state: {ih.get('flow_state','?')}"),
        ("Bank health (BBCA/BBRI/BMRI)",ih.get("bank_health",0.5),
         "Big banks holding up" if ih.get("bank_health",0.5)>0.55 else "Banks under pressure"),
        ("Commodity spillover positif",ih.get("comm_spill",0.5),
         "Coal/metals supporting" if ih.get("comm_spill",0.5)>0.55 else "Commodity chain weak"),
        ("Breadth sektoral",ih.get("breadth_ihsg",0.5),
         f"{sum(1 for v in [ih.get('breadth_ihsg',0)] if v>0.5)}/6 sectors positive"),
        ("EM regime supportif",ih.get("em_regime",0.5),
         f"EM score: {ih.get('em_regime',0):.0%}"),
        ("BI policy supportif",ih.get("bi_path",0.5),
         ih.get("bi_state","?")),
    ]

    return {"global":global_items,"ihsg":ihsg_items}

def build_most_hated_rally_monitor(f:Dict, prices:Dict[str,pd.Series])->Dict:
    """Advanced four-point trigger engine for Ricky's Most Hated Inflated Rally thesis."""
    def _fmt_num(v:float, digits:int=2, prefix:str="", suffix:str="") -> str:
        if not math.isfinite(v):
            return "—"
        return f"{prefix}{v:,.{digits}f}{suffix}"

    def _score_below(v:float, clear_thr:float, near_thr:float, conf:float=1.0) -> Tuple[float,bool,bool]:
        if not math.isfinite(v):
            return 0.42*conf, False, False
        if v < clear_thr:
            return 1.00*conf, True, True
        if v < near_thr:
            return 0.72*conf, False, True
        return 0.24*conf, False, False

    def _score_above(v:float, clear_thr:float, near_thr:float, conf:float=1.0, strong_thr:Optional[float]=None) -> Tuple[float,bool,bool]:
        if not math.isfinite(v):
            return 0.42*conf, False, False
        if strong_thr is not None and v >= strong_thr:
            return 1.00*conf, True, True
        if v >= clear_thr:
            return 0.90*conf, True, True
        if v >= near_thr:
            return 0.68*conf, False, True
        return 0.24*conf, False, False

    cards=[]
    tuple_items=[]

    vix=last(prices.get("^VIX",pd.Series()))
    vix_score,vix_hard,vix_soft=_score_below(vix,20.0,22.0,1.0)
    vix_note="Volatility fear mereda" if vix_hard else ("Sudah mendekat, tapi fear belum bersih" if vix_soft else "Masih terlalu tinggi untuk bilang fear sudah lewat")
    cards.append({"label":"VIX < 20","value":f"VIX {_fmt_num(vix,2)}","threshold":"Clear <20 · near <22","score":vix_score,"hard_clear":vix_hard,"soft_clear":vix_soft,"source":"Exact","confidence":1.0,"note":vix_note})
    tuple_items.append(("VIX < 20",vix_score,vix_note if math.isfinite(vix) else "Data VIX belum tersedia"))

    dxy=last(prices.get("DX-Y.NYB",pd.Series()))
    dxy_exact=math.isfinite(dxy)
    if dxy_exact:
        dxy_score,dxy_hard,dxy_soft=_score_below(dxy,98.0,98.5,1.0)
        dxy_note="Modal global mulai keluar dari USD" if dxy_hard else ("Sudah dekat area break, butuh sedikit lagi" if dxy_soft else "Dollar masih terlalu kuat untuk rally broad risk-on")
        dxy_value=f"DXY {_fmt_num(dxy,3)}"
        dxy_source="Exact"
        dxy_conf=1.0
    else:
        uup_s=prices.get("UUP",pd.Series())
        uup=last(uup_s); uup_1m=ret_n(uup_s,21)
        dxy_hard=False
        dxy_soft=math.isfinite(uup_1m) and uup_1m<0
        dxy_conf=0.55
        if math.isfinite(uup_1m) and uup_1m<0:
            dxy_score=0.62*dxy_conf + 0.10
            dxy_note="DXY exact belum ada, tapi proxy UUP sudah melemah 1M"
        elif math.isfinite(uup_1m):
            dxy_score=0.24*dxy_conf
            dxy_note="Proxy UUP belum mendukung soft dollar"
        else:
            dxy_score=0.38*dxy_conf
            dxy_note="DXY exact belum ada dan proxy juga terbatas"
        dxy_value=f"UUP {_fmt_num(uup,2)} · 1M {pct(uup_1m)}"
        dxy_source="Proxy"
    cards.append({"label":"DXY < 98","value":dxy_value,"threshold":"Clear <98 · near <98.5","score":dxy_score,"hard_clear":dxy_hard,"soft_clear":dxy_soft,"source":dxy_source,"confidence":dxy_conf,"note":dxy_note})
    tuple_items.append(("DXY < 98",dxy_score,dxy_note))

    ust2y=f.get("dgs2",float("nan"))
    ust_score,ust_hard,ust_soft=_score_below(ust2y,3.5,3.7,1.0)
    ust_note="Market sudah pricing deeper cuts" if ust_hard else ("Hampir sampai threshold cut-friendly" if ust_soft else "Rate expectations masih terlalu ketat")
    cards.append({"label":"UST 2Y < 3.5%","value":f"UST 2Y {_fmt_num(ust2y,2,suffix='%')}","threshold":"Clear <3.5% · near <3.7%","score":ust_score,"hard_clear":ust_hard,"soft_clear":ust_soft,"source":"Exact","confidence":1.0,"note":ust_note})
    tuple_items.append(("UST 2Y < 3.5%",ust_score,ust_note if math.isfinite(ust2y) else "FRED DGS2 belum tersedia"))

    btc=last(prices.get("BTC-USD",pd.Series()))
    btc_score,btc_hard,btc_soft=_score_above(btc,72000,70000,1.0,strong_thr=74000)
    btc_note="Liquidity proxy sudah hidup; >74k = stronger confirm" if btc_hard else ("Sudah dekat tapi belum betul-betul clear" if btc_soft else "Liquidity proxy belum confirm")
    cards.append({"label":"BTC > 72k–73k","value":f"BTC {_fmt_num(btc,0,prefix='$')}","threshold":"Clear >72k · strong >74k","score":btc_score,"hard_clear":btc_hard,"soft_clear":btc_soft,"source":"Exact","confidence":1.0,"note":btc_note})
    tuple_items.append(("BTC > 72k–73k",btc_score,btc_note if math.isfinite(btc) else "BTC data belum tersedia"))

    hard_clear_count=sum(1 for c in cards if c["hard_clear"])
    soft_clear_count=sum(1 for c in cards if c["soft_clear"])
    data_quality=float(np.mean([c["confidence"] for c in cards])) if cards else 0.0
    exact_count=sum(1 for c in cards if c["source"]=="Exact")
    score=float(np.mean([c["score"] for c in cards])) if cards else 0.0

    branch_score=clamp(0.55*(hard_clear_count/4.0)+0.25*(soft_clear_count/4.0)+0.20*data_quality)
    if hard_clear_count<=1 and branch_score<0.48:
        branch_state="dormant"; stage="Belum hidup"; posture="Defense / selective only"; action="Belum ada alasan buat agresif. Fokus defense, quality, dan jangan kejar beta."; size_mult=0.35; cls="bad"
    elif hard_clear_count<=1:
        branch_state="watching"; stage="Watching / early"; posture="Probe only"; action="Ada tanda awal, tapi belum cukup. Naikkan watchlist, jangan naikkan size terlalu cepat."; size_mult=0.45; cls="warn"
    elif hard_clear_count==2:
        branch_state="arming"; stage="Transisi 2/4"; posture="Scale in pelan"; action="Branch sedang dibangun. Boleh mulai scale-in bertahap ke beta/EM/crypto-quality, tapi tetap disiplin."; size_mult=0.60; cls="warn"
    elif hard_clear_count==3:
        branch_state="pre_confirmed"; stage="Nyaris aktif 3/4"; posture="Tactical risk-on bertahap"; action="Pre-confirmation. Scanner boleh upgrade risk-on longs dan kurangi conviction short yang rawan kesqueeze."; size_mult=0.82; cls="good"
    else:
        branch_state="active"; stage="Rally live 4/4"; posture="Tactical risk-on aktif"; action="Likuiditas-led branch aktif. Risk-on tactical boleh lebih agresif, tapi tetap satu tangan di pintu keluar."; size_mult=1.00; cls="good"

    oil_1m=nf(f.get("clf_1m", f.get("oil_1m", 0.0)))
    hy=f.get("hy_oas",float("nan"))
    fragility=clamp(0.55*clamp(max(0.0,oil_1m)/0.10)+0.45*(clamp((hy-350)/180) if math.isfinite(hy) else 0.35))
    fragility_note="Fondasi rally tetap rapuh: ini liquidity rally, bukan fundamental repair." if branch_state in {"pre_confirmed","active"} else "Belum ada risk-on branch yang cukup kuat; jangan over-interpret satu-dua sinyal."
    if branch_state=="active" and fragility>=0.55:
        stage += " · fragile"
        action += " Credit/oil belum sepenuhnya bersih, jadi treat ini sebagai tactical move, bukan izin euforia."

    scanner_long_boost={"dormant":0.00,"watching":0.02,"arming":0.05,"pre_confirmed":0.10,"active":0.14}.get(branch_state,0.0)
    scanner_short_penalty={"dormant":0.00,"watching":-0.02,"arming":-0.05,"pre_confirmed":-0.10,"active":-0.14}.get(branch_state,0.0)

    cross_asset=[
        ("US", "Beta & breadth catch-up belum prioritas" if branch_state in {"dormant","watching"} else "QQQ / IWM / XLF / XLI / EEM mulai lebih layak diprioritaskan", "g" if branch_state in {"pre_confirmed","active"} else "y"),
        ("IHSG", "Masih selective; fokus quality / defensif" if branch_state in {"dormant","watching"} else "Bank besar, telco, exporter, metal names lebih diuntungkan oleh flow asing", "g" if branch_state in {"arming","pre_confirmed","active"} else "y"),
        ("Crypto", "Tunggu BTC confirm dulu" if branch_state in {"dormant","watching"} else "BTC/ETH/SOL jadi expression paling sensitif ke liquidity branch", "g" if branch_state in {"pre_confirmed","active"} else "y"),
        ("Commodities", "Gold masih hedge; oil belum tentu turun" if branch_state in {"dormant","watching"} else "Copper positif, gold tetap oke, oil cenderung jadi headwind saat de-escalation", "b"),
    ]

    invalidators=[]
    if not vix_hard: invalidators.append("VIX gagal turun <20")
    if not dxy_hard: invalidators.append("DXY belum pecah <98")
    if not ust_hard: invalidators.append("UST 2Y belum turun <3.5%")
    if not btc_hard: invalidators.append("BTC belum tahan di atas 72k–73k")
    if branch_state in {"pre_confirmed","active"}:
        invalidators.extend(["Oil spike baru / geopolitik re-escalate", "Credit spreads widen lagi"])
    invalidators=invalidators[:4]

    ihsg_title=("Belum ada dukungan likuiditas global untuk IHSG beta" if branch_state in {"dormant","watching"} else
                "Likuiditas global mulai buka pintu untuk IHSG" if branch_state=="arming" else
                "Trigger global sudah mendukung inflow IHSG")
    ihsg_msg=("Fokus quality dan jangan maksa ke saham yang butuh risk appetite besar." if branch_state in {"dormant","watching"} else
              "Mulai prioritaskan bank besar, telco, dan exporter yang paling siap menerima flow." if branch_state=="arming" else
              "Bank besar, telco, exporter, dan metal names lebih pantas dinaikkan ranking-nya, tapi tetap hati-hati euforia.")

    return {
        "items":tuple_items,
        "cards":cards,
        "clear_count":hard_clear_count,
        "hard_clear_count":hard_clear_count,
        "soft_clear_count":soft_clear_count,
        "total":4,
        "stage":stage,
        "action":action,
        "cls":cls,
        "score":score,
        "branch_score":branch_score,
        "dxy_exact":dxy_exact,
        "data_quality":data_quality,
        "exact_count":exact_count,
        "branch_state":branch_state,
        "posture":posture,
        "size_mult":size_mult,
        "scanner_long_boost":scanner_long_boost,
        "scanner_short_penalty":scanner_short_penalty,
        "cross_asset":cross_asset,
        "invalidators":invalidators,
        "fragility":fragility,
        "fragility_note":fragility_note,
        "ihsg_title":ihsg_title,
        "ihsg_msg":ihsg_msg,
    }


def _rally_bucket(score:float)->Tuple[str,str]:
    if score>=0.90: return "✓","rally-ok"
    if score>=0.60: return "~","rally-warn"
    return "✗","rally-bad"


def _rally_tone(state:str)->str:
    if state in {"pre_confirmed","active"}: return "ok"
    if state in {"watching","arming"}: return "warn"
    return "bad"


def render_most_hated_rally_monitor(mon:Dict, compact:bool=False)->None:
    state=str(mon.get("branch_state","dormant"))
    tone=_rally_tone(state)
    fill=max(0.0,min(100.0,float(mon.get("branch_score",mon.get("score",0)))*100.0))
    stage=html.escape(mon.get("stage",""))
    action=html.escape(mon.get("action",""))
    posture=html.escape(mon.get("posture",""))
    size_txt=f"{float(mon.get('size_mult',0.35)):.2f}x"
    if compact:
        pills=[]
        for card in mon.get("cards",[]):
            sym,_cls=_rally_bucket(float(card.get("score",0.0)))
            pills.append(f'<span class="rally-pill {_rally_tone("active" if card.get("hard_clear") else "arming" if card.get("soft_clear") else "dormant")}">{sym} {html.escape(card.get("label",""))}</span>')
        st.markdown(
            f'<div class="rally-shell">'
            f'<div class="rally-top">'
            f'<div><div class="rally-kicker">Most Hated Inflated Rally</div><div class="rally-title">{mon.get("clear_count",0)}/{mon.get("total",4)} · {stage}</div><div class="rally-sub">{posture} · size {size_txt} · data {float(mon.get("data_quality",0.0)):.0%}</div></div>'
            f'<div class="rally-pill {tone}">Composite {fill:.0f}%</div>'
            f'</div>'
            f'<div class="rally-mini">{"".join(pills)}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        return

    sh(f"🔥 MOST HATED INFLATED RALLY MONITOR — {mon.get('clear_count',0)}/{mon.get('total',4)}")
    legend=''.join([
        '<span class="rally-pill bad">0–1/4 · belum hidup</span>',
        '<span class="rally-pill warn">2/4 · transisi</span>',
        '<span class="rally-pill ok">3/4 · nyaris aktif</span>',
        '<span class="rally-pill ok">4/4 · rally live</span>'
    ])
    items_html=[]
    for card in mon.get("cards",[]):
        sym,cls=_rally_bucket(float(card.get("score",0.0)))
        width=max(8.0,min(100.0,float(card.get("score",0.0))*100.0))
        items_html.append(
            f'<div class="rally-item">'
            f'<div class="rally-item-top"><div><div class="rally-item-label">{html.escape(card.get("label",""))}</div><div style="font-size:11px;opacity:.72;margin-top:2px">{html.escape(card.get("value","—"))}</div></div><span class="rally-chip {cls}">{sym}</span></div>'
            f'<div class="rally-item-note"><b>{html.escape(card.get("threshold",""))}</b><br>{html.escape(card.get("note",""))}</div>'
            f'<div class="rally-meter"><div class="rally-fill" style="width:{width:.0f}%"></div></div>'
            f'<div class="rally-scale"><span>{html.escape(card.get("source",""))}</span><span>conf {float(card.get("confidence",0.0)):.0%}</span><span>{"hard" if card.get("hard_clear") else "near" if card.get("soft_clear") else "fail"}</span></div>'
            f'</div>'
        )

    side_cards=''.join(
        f'<div class="rally-mini-card"><div style="font-size:10px;opacity:.5;letter-spacing:.08em;text-transform:uppercase;margin-bottom:4px">{html.escape(title)}</div><div style="font-size:12px;font-weight:700;margin-bottom:3px">{html.escape(desc)}</div></div>'
        for title,desc,_kind in mon.get("cross_asset",[])
    )
    invalidators=''.join(
        f'<div class="rally-mini-card"><div style="font-size:10px;opacity:.5;letter-spacing:.08em;text-transform:uppercase;margin-bottom:4px">Fail-fast</div><div style="font-size:12px">{html.escape(x)}</div></div>'
        for x in mon.get("invalidators",[])
    )

    st.markdown(
        f'<div class="rally-shell">'
        f'<div class="rally-top">'
        f'<div><div class="rally-kicker">Narrative → Execution Bridge</div><div class="rally-title">{stage}</div><div class="rally-sub">{action}</div></div>'
        f'<div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end">'
        f'<span class="rally-pill {tone}">Posture · {posture}</span>'
        f'<span class="rally-pill {tone}">Sizing · {size_txt}</span>'
        f'<span class="rally-pill {tone}">Composite · {fill:.0f}%</span>'
        f'<span class="rally-pill {tone}">Data · {float(mon.get("data_quality",0.0)):.0%}</span>'
        f'</div></div>'
        f'<div class="rally-meter"><div class="rally-fill" style="width:{fill:.0f}%"></div></div>'
        f'<div class="rally-legend">{legend}</div>'
        f'<div class="rally-grid">{"".join(items_html)}</div>'
        f'<div class="rally-mini" style="margin-top:10px">{side_cards}</div>'
        f'<div style="font-size:11px;opacity:.62;margin-top:8px">{html.escape(mon.get("fragility_note",""))}</div>'
        f'<div class="rally-mini" style="margin-top:10px">{invalidators}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

def render_ihsg_rally_note(mon:Dict, ih:Dict)->None:
    clear_count=int(mon.get("hard_clear_count", mon.get("clear_count",0)) or 0)
    title=mon.get("ihsg_title","Global liquidity → IHSG")
    msg=mon.get("ihsg_msg","")
    flow=ih.get("foreign_flow",0.5)
    idr=nf(ih.get("usd_idr_1m",0.0))
    flow_txt=f"Asing {ih.get('flow_state','mixed')}"
    idr_txt=("IDR supportif" if idr<-0.01 else ("IDR netral" if idr<0.01 else "IDR tertekan"))
    if clear_count>=4: bc="#3dbb6c"; bg="rgba(61,187,108,0.10)"
    elif clear_count>=2: bc="#e5a020"; bg="rgba(229,160,32,0.10)"
    else: bc="#e05252"; bg="rgba(224,82,82,0.10)"
    st.markdown(
        f'<div style="border:1px solid {bc}55;background:{bg};border-radius:12px;padding:12px 14px;margin-bottom:12px">'
        f'<div style="font-size:10px;letter-spacing:.10em;text-transform:uppercase;opacity:.52;margin-bottom:3px">Global Liquidity → IHSG</div>'
        f'<div style="font-weight:800;font-size:16px;margin-bottom:3px;color:{bc}">{html.escape(str(title))}</div>'
        f'<div style="font-size:12px;opacity:.88">{html.escape(str(msg))}</div>'
        f'<div style="font-size:11px;opacity:.65;margin-top:6px">Checklist {clear_count}/4 · {flow_txt} · {idr_txt} · posture {html.escape(str(mon.get("posture","")))}</div>'
        f'</div>',
        unsafe_allow_html=True
    )


def render_checklist(items:list,title:str="Checklist")->None:
    """Render checklist as compact cards for better readability."""
    sh(title)
    cards=[]
    for label,score,note in items:
        sym,cls=_chk(score)
        score_txt=f"{float(score):.0%}"
        cards.append(
            f'<div class="ck-card">'
            f'<div class="ck-top"><div><div class="ck-label">{html.escape(str(label))}</div></div><span class="ck-badge {cls}">{sym}</span></div>'
            f'<div class="ck-note">{html.escape(str(note))}</div>'
            f'<div class="ck-score">score {score_txt}</div>'
            f'</div>'
        )
    st.markdown(f'<div class="ck-grid">{"".join(cards)}</div>',unsafe_allow_html=True)


def build_risk_range(prices:Dict[str,pd.Series], f:Dict, crash:Dict) -> Dict:
    """Final Trade/Trend/Tail risk range engine with state + buy-dip / sell-rip context."""
    vix=float(f.get("vix_last",20.0) or 20.0)
    uup_1m=nf(f.get("uup_1m", f.get("dxy_1m", 0.0)))
    inf_shock=clamp(f.get("inf_shock",0.0))
    crash_score=clamp(crash.get("crash_score",0.0))
    breadth_dmg=clamp(crash.get("breadth_dmg",0.0))

    stress_scalar=1.0+0.30*inf_shock+0.22*clamp((vix-13.0)/20.0)+0.18*crash_score+0.10*breadth_dmg
    down_asym=1.0+0.18*clamp(0.5+uup_1m/0.04)+0.18*crash_score
    up_asym=max(0.78,1.0-0.10*clamp(uup_1m/0.04))

    WATCH_TICKERS=sorted(set([
        "SPY","QQQ","IWM","RSP","XLE","XLF","XLI","XLP","XLU","XLV","GLD","GC=F","CL=F","TLT","UUP","EEM",
        "BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","ADA-USD","AVAX-USD","LINK-USD","DOGE-USD",
        "^JKSE","BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","TLKM.JK","ADRO.JK","PTBA.JK","ANTM.JK","INCO.JK","MDKA.JK"
    ]))

    def _rv_annual(s:pd.Series,n:int)->float:
        s=_s(s)
        if len(s)<n+2:
            return 0.20
        rets=s.pct_change().dropna()
        if len(rets)<n:
            return 0.20
        return float(rets.tail(n).std()*np.sqrt(252))

    def _slope_norm(series:pd.Series,lookback:int=10)->float:
        s=_s(series)
        if len(s)<lookback+2:
            return 0.0
        a=float(s.iloc[-1]); b=float(s.iloc[-(lookback+1)])
        if not math.isfinite(a) or not math.isfinite(b) or b==0:
            return 0.0
        return float(a/b-1.0)

    def _state(px:float,basis:float,slope:float,tol:float=0.003)->str:
        if not math.isfinite(px) or not math.isfinite(basis):
            return "neutral"
        rel=(px/basis)-1.0
        if rel>tol and slope>0:
            return "bullish"
        if rel<-tol and slope<0:
            return "bearish"
        return "neutral"

    def _stretch(px:float,lo:float,hi:float)->str:
        band=max(hi-lo, abs(px)*0.001)
        pos=(px-lo)/band if band>0 else 0.5
        if pos>=0.90: return "overbought"
        if pos<=0.10: return "oversold"
        if pos>=0.72: return "extended_up"
        if pos<=0.28: return "reset_zone"
        return "neutral"

    out={}
    for tk in WATCH_TICKERS:
        s=_s(prices.get(tk,pd.Series(dtype=float)))
        if len(s)<260:
            continue
        px=float(s.iloc[-1])
        if px<=0 or not math.isfinite(px):
            continue

        ema20=float(s.ewm(span=20,adjust=False).mean().iloc[-1])
        ema63=float(s.ewm(span=63,adjust=False).mean().iloc[-1])
        ema252=float(s.ewm(span=252,adjust=False).mean().iloc[-1])

        rv21=_rv_annual(s,21); rv63=_rv_annual(s,63); rv126=_rv_annual(s,126)
        base_trade=max(0.006,(rv21/np.sqrt(252))*np.sqrt(5))
        base_trend=max(0.010,(rv63/np.sqrt(252))*np.sqrt(21))
        base_tail=max(0.018,(rv126/np.sqrt(252))*np.sqrt(63))

        tw=base_trade*1.10*stress_scalar
        rw=base_trend*1.35*stress_scalar
        lw=base_tail*1.60*stress_scalar

        trade_low=ema20*(1.0-tw*down_asym); trade_high=ema20*(1.0+tw*up_asym)
        trend_low=ema63*(1.0-rw*down_asym); trend_high=ema63*(1.0+rw*up_asym)
        tail_low=ema252*(1.0-lw*down_asym); tail_high=ema252*(1.0+lw*up_asym)

        trade_slope=_slope_norm(s.ewm(span=20,adjust=False).mean(),8)
        trend_slope=_slope_norm(s.ewm(span=63,adjust=False).mean(),12)
        tail_slope=_slope_norm(s.ewm(span=252,adjust=False).mean(),21)

        trade_state=_state(px,ema20,trade_slope)
        trend_state=_state(px,ema63,trend_slope)
        tail_state=_state(px,ema252,tail_slope)
        triple_aligned=trade_state==trend_state==tail_state and trade_state in {"bullish","bearish"}

        if not triple_aligned:
            phase_transition="mixed"
        elif trade_state=="bullish":
            phase_transition="bull_trend_persistent"
        else:
            phase_transition="bear_trend_persistent"

        range_quality=float(np.clip(
            0.34*(1.0 if trade_state==trend_state else 0.0)+
            0.34*(1.0 if trend_state==tail_state else 0.0)+
            0.32*(1.0-crash_score),
            0.0,1.0
        ))

        buy_dip_ok=triple_aligned and trade_state=="bullish" and px>=trade_low and px<=trade_high
        sell_rip_ok=triple_aligned and trade_state=="bearish" and px>=trade_low and px<=trade_high

        out[tk]={
            "px":round(px,4),
            "trade_basis":round(ema20,4),"trade_low":round(trade_low,4),"trade_high":round(trade_high,4),"trade_state":trade_state,
            "trend_basis":round(ema63,4),"trend_low":round(trend_low,4),"trend_high":round(trend_high,4),"trend_state":trend_state,
            "tail_basis":round(ema252,4),"tail_low":round(tail_low,4),"tail_high":round(tail_high,4),"tail_state":tail_state,
            "triple_aligned":bool(triple_aligned),
            "phase_transition":phase_transition,
            "stretch":_stretch(px,trade_low,trade_high),
            "range_quality":round(range_quality,3),
            "buy_dip_ok":bool(buy_dip_ok),
            "sell_rip_ok":bool(sell_rip_ok),
            "trend":trend_state,
        }
    return out




def build_position_sizing(q:Dict, h:Dict, crash:Dict, f:Dict, risk_ranges:Dict, price_meta:Dict)->Dict:
    """Position sizing ladder from regime + crash + range alignment + data quality."""
    quad=str(q.get("quad","Q3"))
    quad_conf=float(q.get("confidence",0.5) or 0.5)
    weather=float(h.get("weather",0.5) or 0.5)
    crash_score=clamp(crash.get("crash_score",0.0))
    breadth_dmg=clamp(crash.get("breadth_dmg",0.0))

    coverage=float(price_meta.get("coverage",1.0) or 1.0)
    short_hist=float(price_meta.get("short_history_share",0.0) or 0.0)
    stale_share=float(price_meta.get("stale_share",0.0) or 0.0)

    data_penalty=np.clip(
        0.45*max(0.0,0.90-coverage)/0.90+
        0.30*short_hist+
        0.25*stale_share,
        0.0,1.0
    )

    if quad in {"Q1","Q2"}:
        long_base, short_base = 1.00, 0.60
    elif quad=="Q3":
        long_base, short_base = 0.55, 0.90
    else:
        long_base, short_base = 0.40, 1.00

    regime_scalar=np.clip(0.55*quad_conf+0.45*weather,0.25,1.00)
    defensive_scalar=np.clip(1.0-0.50*crash_score-0.20*breadth_dmg-0.35*data_penalty,0.20,1.00)

    def _bucket(x:float)->str:
        if x>=0.90: return "1.00x"
        if x>=0.70: return "0.75x"
        if x>=0.45: return "0.50x"
        return "0.25x"

    out={}
    for tk, rr in risk_ranges.items():
        triple=bool(rr.get("triple_aligned",False))
        t_state=str(rr.get("trade_state","neutral"))
        tr_state=str(rr.get("trend_state","neutral"))
        tl_state=str(rr.get("tail_state","neutral"))

        align_scalar=1.0 if triple else 0.65
        if t_state==tr_state==tl_state=="bullish":
            long_state_scalar, short_state_scalar = 1.00, 0.45
        elif t_state==tr_state==tl_state=="bearish":
            long_state_scalar, short_state_scalar = 0.40, 1.00
        else:
            long_state_scalar = short_state_scalar = 0.65

        long_current=float(np.clip(long_base*regime_scalar*defensive_scalar*align_scalar*long_state_scalar,0.10,1.00))
        short_current=float(np.clip(short_base*regime_scalar*defensive_scalar*align_scalar*short_state_scalar,0.10,1.00))
        reasons=[]
        if crash_score>=0.60: reasons.append("crash override")
        if not triple: reasons.append("durations not fully aligned")
        if data_penalty>=0.35: reasons.append("data confidence reduced")
        if quad in {"Q3","Q4"}: reasons.append("defensive macro backdrop")
        out[tk]={
            "size_floor":"0.25x",
            "size_base_long":_bucket(long_base),
            "size_base_short":_bucket(short_base),
            "size_current_long":_bucket(long_current),
            "size_current_short":_bucket(short_current),
            "size_scalar_long":round(long_current,3),
            "size_scalar_short":round(short_current,3),
            "size_reason":", ".join(reasons) if reasons else "full conditions acceptable",
        }
    return out

def build_asset_checklists_full(f:Dict, h:Dict, q:Dict, ih:Dict, prices:Dict) -> Dict:
    """v33-style asset checklists per market (US, FX, Commodities, Crypto)."""
    vix=f.get("vix_last",20.0); hy=f.get("hy_oas",350.0)
    uup_1m=nf(f.get("uup_1m",0.0)); uup_3m=nf(f.get("uup_3m",f.get("dxy_3m",0.0)))
    oil_3m=nf(f.get("clf_3m",f.get("oil_3m",0.0))); gold_3m=nf(f.get("gld_3m",f.get("gold_3m",0.0)))
    spy_1m=nf(f.get("spy_1m",0.0)); iwm_1m=nf(f.get("iwm_1m",0.0))
    tlt_1m=nf(f.get("tlt_1m",0.0))
    btc_1m=ret_n(prices.get("BTC-USD",pd.Series()),21)
    eth_1m=ret_n(prices.get("ETH-USD",pd.Series()),21)
    hg_1m=ret_n(prices.get("HG=F",pd.Series()),21)
    sf=q.get("slowdown_flags",0.0); shock=q.get("inf_shock",0.0)

    us=[
        ("Breadth melebar (equal-weight confirm)",clamp(0.5+nf(ret_n(prices.get("RSP",pd.Series()),21))*5),"RSP vs SPY 1M"),
        ("Small caps ikut (IWM confirm)",clamp(0.5+iwm_1m*5),"IWM 1M: "+pct(iwm_1m)),
        ("Credit aman (HY spreads)",clamp(1-(hy-250)/450) if math.isfinite(hy) else 0.5,f"HY OAS: {hy:.0f}bps" if math.isfinite(hy) else "proxy"),
        ("VIX investable (<19)",clamp(1-(vix-13)/20),f"VIX: {vix:.1f}"),
        ("Sector breadth sehat",h.get("sec_support",0.5),f"{h.get('sec_above50',0)}/11 di atas 50-DMA"),
        ("SPY trend positif",h.get("spy_trend",0.5),"Price above 20+50 DMA"),
    ]

    fx=[
        ("USD tidak terlalu kuat",clamp(0.5-uup_1m*8),"UUP 1M: "+pct(uup_1m)),
        ("USD trend tidak melonjak",clamp(0.5-uup_3m*4),"UUP 3M: "+pct(uup_3m)),
        ("Inflasi tidak re-accelerate",clamp(1-shock*2),"Shock: "+f"{shock:.2f}"),
        ("Carry tidak terlalu panas",clamp(0.65-shock*0.5),"Proxy dari VIX dan inflasi"),
        ("EM FX tidak stress",1-ih.get("usd_idr_pressure",0.5),"USD/IDR: "+pct(ih.get("usd_idr_1m",float("nan")))),
    ]

    commodities=[
        ("Gold trend positif",clamp(0.5+gold_3m*3),"GLD 3M: "+pct(gold_3m)),
        ("Oil tidak collapse",clamp(0.5+oil_3m*2),"Oil 3M: "+pct(oil_3m)),
        ("Copper (growth proxy)",clamp(0.5+nf(hg_1m)*5),"HG 1M: "+pct(nf(hg_1m))),
        ("USD tidak tekanan commodity",clamp(0.5-uup_3m*3),"DXY headwind: "+pct(-uup_3m)),
        ("Inflasi pulse mendukung",clamp(0.5+shock*2),"Shock: "+f"{shock:.2f}" if shock>0 else "No shock"),
    ]

    crypto=[
        ("BTC trend positif",clamp(0.5+nf(btc_1m)*2),"BTC 1M: "+pct(nf(btc_1m))),
        ("ETH confirm",clamp(0.5+nf(eth_1m)*2),"ETH 1M: "+pct(nf(eth_1m))),
        ("VIX rendah (risk-on)",clamp(1-(vix-13)/20),f"VIX: {vix:.1f}"),
        ("Credit aman",clamp(1-(hy-250)/450) if math.isfinite(hy) else 0.5,"HY spreads"),
        ("Regime supportif (Q1/Q2)",clamp({"Q1":0.80,"Q2":0.65,"Q3":0.25,"Q4":0.15}.get(q.get("quad","Q3"),0.5)),f"Regime {q.get('quad','?')}"),
        ("Breadth lebar (tidak cuma BTC)",clamp(0.5+nf(btc_1m)-abs(nf(btc_1m)-nf(eth_1m))*0.5),"BTC-ETH divergence"),
    ]

    return {"us":us,"fx":fx,"commodities":commodities,"crypto":crypto}


def build_macro_impact_all(q:Dict, f:Dict, rot:Dict) -> Dict:
    """v33 Macro Impact Board per market: now/best_expression/invalidator/branch."""
    quad=q["quad"]; conf=q["confidence"]; cb=q["conf_band"]
    oil_3m=nf(f.get("clf_3m",f.get("oil_3m",0.0))); uup_1m=nf(f.get("uup_1m",0.0))
    sf=q.get("slowdown_flags",0.0); shock=q.get("inf_shock",0.0)

    boards={
        "us":{
            "Q1":("Growth + inflasi turun = risk-on lebar.","QQQ + quality growth + EM beta.","Kalau breadth lebar dan credit ketat, second-line leaders bisa nyusul.","Yield spike + breadth makin sempit + credit stress.",["real yields","breadth","credit","sector"]),
            "Q2":("Growth + inflasi sama2 naik = reflation.","XLE + XLI + XLF + commodities-linked.","Kalau ISM bertahan >52, cyclical rotation bisa makin lebar.","ISM rollover + Fed overtighten.",["ISM","yields","commodities","earnings"]),
            "Q3":("Stagflasi = risk broadly bearish.","GLD + XLE selektif + XLP/XLU + cash.","Kalau Fed pivot kredibel, duration dapat relief squeeze.","VIX spike + credit + breadth collapse.",["gold","USD","defensives","short beta"]),
            "Q4":("Deflasi/resesi = capital preservation.","TLT + GLD + XLP/XLU/XLV.","Kalau fiscal/Fed stimulus besar, V-shape recovery trade.","Stimulus besar + ISM rebound dari <45.",["TLT","gold","defensives","quality"]),
        },
        "ihsg":{
            "Q1":("Goldilocks = asing masuk, IHSG kondusif.","Bank besar + consumer cyclical + domestic beta.","Kalau rupiah stabil dan asing beli, breadth bisa melebar.","USD/IDR naik lagi + asing sell.",["rupiah","asing","bank","broad breadth"]),
            "Q2":("Reflation = commodity exporter + bank lead.","ADRO + PTBA + ANTM + BBCA.","Kalau coal/mineral bertahan, exporter dan bank bisa naik bareng.","Commodity rollback + USD kuat.",["batubara","logam","rupiah","asing"]),
            "Q3":("Stagflasi = IHSG mixed-bearish, defensif.","ADRO/PTBA (coal) + TLKM + ICBP. Kurangi consumer cyclical.","Coal exporter bisa survive stagflasi. Rest butuh USD/IDR stabil.","Oil drop + USD/IDR naik + asing keluar.",["coal","USD/IDR","defensif","asing"]),
            "Q4":("Resesi = IHSG broadly bearish.","TLKM + ICBP + KLBF (consumer staples).","Kalau Fed cut agresif + IDR stabil, quality IHSG bisa outperform.","USD/IDR terus naik + asing outflow masif.",["defensif","dividend quality","rupiah"]),
        },
        "fx":{
            "Q1":("Goldilocks = USD mild, carry works.","AUD/USD long, EUR/USD long, IDR selective.","Kalau inflasi melandai dan data kuat, EM FX bisa lebar.","USD re-accelerates, carry unwinds.",["USD","carry","EM FX","inflasi"]),
            "Q2":("Reflation = commodity FX naik.","AUD, CAD, NOK (commodity FX). Short JPY/CHF.","Commodity FX bisa lanjut kalau ISM dan oil bertahan.","Demand scare + oil rollback.",["commodity FX","carry","EM FX"]),
            "Q3":("Stagflasi = USD dan funding king.","Long USD (UUP), short carry (IDR, TRY). JPY counter-trend.","USD bisa lanjut dominan sampai Fed pivot kredibel.","De-escalation + Fed pivot + oil drop.",["USD dominan","carry pain","EM fragile"]),
            "Q4":("Deflasi = JPY, CHF, USD defensive.","USD/JPY short (yen menguat), EUR/USD mixed.","Kalau risk-off melebar, JPY dan CHF outperform.","Risk-on squeeze + Fed cut surprise.",["JPY","CHF","USD defensive"]),
        },
        "commodities":{
            "Q1":("Goldilocks = gold ok, oil ok.","GLD + selective oil. Copper ok.","Kalau pertumbuhan bertahan, broad commodity bisa positif.","Yield spike + USD naik.",["gold","copper","broad commodity"]),
            "Q2":("Reflation = energy + metals king.","WTI/Brent + XLE + Copper + Agri.","Commodity super-cycle bisa lanjut kalau ISM bertahan.","Demand scare + dollar squeeze.",["energy","metals","agri"]),
            "Q3":("Stagflasi = gold best trade.","XAUUSD + GLD. Oil volatile (bisa naik dulu).","Gold bisa lanjut selama real yields tidak meledak.","Real yields spike + USD super-strong.",["gold","oil volatile","industrial metals avoid"]),
            "Q4":("Deflasi = gold only.","GLD saja. Semua lain broadly bearish.","Gold bisa menguat kalau Fed cut agresif + safe-haven demand.","Commodity demand collapse breadth.",["gold","oil bearish","metals bearish"]),
        },
        "crypto":{
            "Q1":("Goldilocks = crypto bull market.","BTC + ETH + SOL + L1/L2 alts.","Kalau breadth lebar dan BTC rally, alts bisa outperform.","VIX spike + credit stress + breadth collapse.",["BTC lead","ETH catch-up","alts beta"]),
            "Q2":("Reflation = crypto ok tapi commodities lead.","BTC + ETH. Alts selective.","Jaga sizing karena reflation bisa cepat berubah ke stagflasi.","Inflation panic + rate spike tiba-tiba.",["BTC/ETH ok","alts secondary"]),
            "Q3":("Stagflasi = crypto very bearish.","BTC only (sebagai digital gold proxy). Jangan alts.","Bahkan BTC bisa tekanan kalau USD sangat kuat.","Yield spike + dollar dominance masif.",["BTC saja","alts hindari","preserve capital"]),
            "Q4":("Deflasi = crypto worst environment.","Cash > semua crypto. BTC hold only.","Hanya jika Fed pivot agresif → BTC bisa relief bounce.","Resesi deep + credit collapse.",["cash king","avoid all crypto"])}
    }

    result={}
    for mkt,quad_boards in boards.items():
        bd=quad_boards.get(quad, quad_boards.get("Q3",("—","—","—","—",[])))
        result[mkt]={"now":bd[0],"best_expression":bd[1],"forward_branch":bd[2],
                     "invalidator":bd[3],"drivers":bd[4],"quad":quad,"confidence":conf}
    return result


def render_flow_state_strip(q:Dict)->None:
    """v33 Flow State Strip: Structural→Monthly→Resolved→Next as horizontal pills."""
    s_quad=q["quad"]; m_quad=q["monthly_quad"]; div=q["divergence"]
    next_q=q.get("next_quad",s_quad); flip=q.get("flip_hazard",0.5)
    operating=q.get("operating","?"); cb=q.get("conf_band","?")
    items=[
        {"label":"Structural","value":s_quad,"note":cb,"tone":"structural"},
        {"label":"Monthly","value":m_quad,"note":"aligned" if div=="aligned" else "divergent","tone":"monthly"},
        {"label":"Operating","value":operating[:22],"note":f"Conf {q.get('confidence',0):.0%}","tone":"resolved"},
        {"label":"Next","value":next_q,"note":f"Flip {flip:.0%}","tone":"next"},
    ]
    tone_colors={"structural":"#378ADD","monthly":"#e5a020" if div=="divergent" else "#3dbb6c",
                 "resolved":"#9b6aff","next":"#e05252" if flip>0.55 else "#aaa"}
    parts=[]
    for i,item in enumerate(items):
        tc=tone_colors.get(item["tone"],"#888")
        parts.append(
            '<div style="flex:1;min-width:0;border:1px solid '+tc+'44;border-radius:8px;padding:6px 10px;'+
            ('background:'+tc+'18;' if i<3 else "")+'">'+
            '<div style="font-size:9px;font-weight:700;letter-spacing:.08em;color:'+tc+';">'+item["label"].upper()+'</div>'+
            '<div style="font-size:14px;font-weight:700;margin:2px 0;color:var(--color-text-primary)">'+item["value"]+'</div>'+
            '<div style="font-size:10px;color:var(--color-text-secondary)">'+item["note"]+'</div>'+
            '</div>'
        )
        if i<len(items)-1:
            parts.append('<div style="font-size:18px;color:#aaa;padding:0 2px;display:flex;align-items:center">&rarr;</div>')
    html_strip='<div style="display:flex;align-items:stretch;gap:4px;margin-bottom:10px">'+'\n'.join(parts)+'</div>'
    st.markdown(html_strip, unsafe_allow_html=True)


def render_master_rotation_graph(q:Dict, f:Dict, rot:Dict, family:str)->None:
    """v33 Master Rotation Graph: YOU ARE HERE mind-map with stage nodes."""
    s_quad=q["quad"]; m_quad=q["monthly_quad"]; div=q["divergence"]
    next_q=q.get("next_quad",s_quad); flip=q.get("flip_hazard",0.5)
    top_ben=rot.get("top_ben","XAUUSD"); top_safe=rot.get("top_safe","Gold")
    em_state=rot.get("em_state","Wait"); petro=rot.get("petro_score",0.0)
    oil_3m=nf(f.get("clf_3m",f.get("oil_3m",0.0))); shock=q.get("inf_shock",0.0)

    # Determine current stage
    if div=="aligned" and flip<0.35: stage="structural"
    elif div=="divergent": stage="monthly"
    else: stage="resolved"

    family_meta=ROTATION_FAMILIES.get(family,{})
    family_label=family_meta.get("name","?")

    def _node(title, label, note, tickers, *, active=False, next_path=False, danger=False)->str:
        if danger: bc,bg="#e05252","rgba(224,82,82,0.10)"
        elif next_path: bc,bg="#e5a020","rgba(229,160,32,0.10)"
        elif active: bc,bg="#378ADD","rgba(55,138,221,0.12)"
        else: bc,bg="rgba(255,255,255,0.15)","rgba(255,255,255,0.03)"
        badge=""
        if active: badge='<span style="font-size:9px;font-weight:800;color:'+bc+'">● YOU ARE HERE</span><br>'
        elif next_path: badge='<span style="font-size:9px;font-weight:800;color:'+bc+'">→ NEXT</span><br>'
        elif danger: badge='<span style="font-size:9px;font-weight:800;color:'+bc+'">⚠ RISK</span><br>'
        tks=", ".join(tickers[:3]) if tickers else "—"
        return (
            '<div style="border:1.5px solid '+bc+';background:'+bg+';border-radius:10px;padding:10px 8px;text-align:center;min-height:120px;display:flex;flex-direction:column;justify-content:center;flex:1">'+
            badge+
            '<div style="font-size:9px;color:rgba(255,255,255,0.4);letter-spacing:.08em;text-transform:uppercase;margin-bottom:3px">'+title+'</div>'+
            '<div style="font-size:14px;font-weight:700;color:var(--color-text-primary);margin-bottom:2px">'+label+'</div>'+
            '<div style="font-size:10px;color:var(--color-text-secondary);margin-bottom:4px">'+note+'</div>'+
            '<div style="font-size:9px;color:'+bc+';font-family:monospace">'+tks+'</div>'+
            '</div>'
        )

    nodes_html=[
        _node("Structural Regime", s_quad, QUAD_META.get(s_quad,{}).get("label","?")[:20],
              QUAD_META.get(s_quad,{}).get("best",[])[:2], active=(stage=="structural")),
        _node("Monthly Overlay", m_quad, "divergent" if div=="divergent" else "aligned",
              [], active=(stage=="monthly"), next_path=(stage=="structural" and div=="divergent")),
        _node("Operating / Resolved", q.get("operating","?")[:22], q.get("conf_band","?"),
              [top_ben, top_safe], active=(stage=="resolved")),
        _node("Best Long / Safe Harbor", top_ben, "beneficiary", [top_ben],
              next_path=True),
        _node("Next / Invalidation", next_q, f"flip {flip:.0%}",
              ["confirm: breadth+credit"], danger=(flip>0.55)),
    ]
    sep='<div style="font-size:20px;color:rgba(255,255,255,0.3);display:flex;align-items:center;padding:0 2px">&rarr;</div>'
    graph_html=(
        '<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:12px 10px;margin-bottom:10px">'+
        '<div style="font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,255,255,0.35);margin-bottom:8px">MASTER ROTATION GRAPH — '+family_label.upper()+'</div>'+
        '<div style="display:flex;align-items:center;gap:4px;flex-wrap:nowrap">'+
        sep.join(nodes_html)+
        '</div></div>'
    )
    st.markdown(graph_html, unsafe_allow_html=True)




# ── Route State System (v33 regime_router.py exact logic) ─────────────────────
ROUTE_STATE_META = {
    "quality_disinflation": {
        "label": "Quality Disinflation",
        "emoji": "✨",
        "desc": "Growth cukup bagus, inflasi melandai. Quality names dan selected growth menang. Defensives ok tapi bukan pemenang.",
        "color": "#3dbb6c",
        "long": ["Quality growth (MSFT, AAPL, GOOGL)", "Selected tech", "IHSG bank quality"],
        "avoid": ["Deep cyclicals", "High-beta", "Commodities"],
    },
    "reflation_reaccel": {
        "label": "Reflation Re-Acceleration",
        "emoji": "⚡",
        "desc": "Growth dan inflasi sama-sama naik. Commodity, cyclical, dan EM dalam satu trade. Jangan defensif.",
        "color": "#e5a020",
        "long": ["XLE, XLI, XLF", "ADRO, PTBA, ANTM", "AUD, CAD, commodity FX"],
        "avoid": ["TLT", "Defensives", "USD longs"],
    },
    "stagflation_persist": {
        "label": "Stagflation Persists",
        "emoji": "🔥",
        "desc": "Growth melambat tapi inflasi keras. Quad paling sulit. Hard assets dan cash menang. Equities broadly suffer.",
        "color": "#e5a020",
        "long": ["Gold (XAUUSD)", "Energy selective (XLE)", "USD (UUP)", "Defensives (XLP, XLU)"],
        "avoid": ["QQQ", "IWM", "EEM", "IHSG domestic beta"],
    },
    "growth_scare": {
        "label": "Growth Scare / De-Risk",
        "emoji": "📉",
        "desc": "Growth data memburuk cepat, inflasi belum benar-benar turun. Risk-off tapi belum full crash. Quality dan cash.",
        "color": "#e05252",
        "long": ["TLT", "Gold (GLD)", "XLP, XLV", "USD"],
        "avoid": ["Cyclicals", "EM", "Crypto", "Small caps"],
    },
    "deflationary_riskoff": {
        "label": "Deflationary Risk-Off",
        "emoji": "❄️",
        "desc": "Growth dan inflasi turun. Resesi pricing. Long bonds, gold, dan defensives. Capital preservation mode.",
        "color": "#e05252",
        "long": ["TLT (20Y bonds)", "Gold (GLD)", "XLP, XLU, XLV", "USD, JPY, CHF"],
        "avoid": ["Semua commodity", "Cyclicals", "EM", "Crypto"],
    },
    "vshape_rebound": {
        "label": "V-Shape Rebound Watch",
        "emoji": "🚀",
        "desc": "Setelah downturn, tanda awal recovery muncul. Equal-weight, IWM, EM bisa rebound keras. High risk/reward.",
        "color": "#59a8e5",
        "long": ["IWM (small caps)", "EEM", "XLI, XLF", "IHSG broad"],
        "avoid": ["Ultra-defensives", "Long bonds", "Cash heavy"],
    },
    "panic_crash": {
        "label": "Panic / Crash Mode",
        "emoji": "🚨",
        "desc": "Tail event. Forced selling, liquidity stress. Cash adalah king. Aktif hedge. Jangan beli the dip dulu.",
        "color": "#e05252",
        "long": ["Cash (BIL, SHY)", "Gold (GLD)", "JPY, CHF", "VIX hedges"],
        "avoid": ["SEMUA equities", "SEMUA credit", "Crypto", "EM"],
    },
}

def derive_route_state(q:Dict, h:Dict, crash:Dict) -> Dict:
    """Route engine with permissions, confidence, alt, and invalidator route."""
    structural=str(q.get('quad','Q3'))
    monthly=str(q.get('monthly_quad',structural))
    div=str(q.get('divergence','aligned'))
    risk_off=clamp(crash.get('risk_off',0.0))
    crash_score=clamp(crash.get('crash_score',0.0))
    exec_score=clamp(crash.get('exec_score',0.0))
    weather=clamp(h.get('weather',0.5))
    tail_state=str(h.get('tail_state','neutral'))
    slowdown_flags=float(q.get('slowdown_flags',0.0) or 0.0)
    inf_shock=float(q.get('inf_shock',0.0) or 0.0)

    if crash_score>=0.78:
        primary='panic_crash'; alt='vshape_rebound'; invalidator='deflationary_riskoff'
    elif structural=='Q4' or risk_off>=0.68:
        primary='deflationary_riskoff'; alt='vshape_rebound' if exec_score>=0.55 else 'reflation_reaccel'; invalidator='quality_disinflation'
    elif structural=='Q3' and (monthly in {'Q3','Q4'} or tail_state=='stressed' or inf_shock>0.30):
        primary='stagflation_persist'; alt='growth_scare' if risk_off>=0.58 else 'reflation_reaccel'; invalidator='quality_disinflation'
    elif monthly=='Q2' and exec_score>=0.56 and weather>=0.56:
        primary='reflation_reaccel'; alt='growth_scare'; invalidator='deflationary_riskoff'
    elif structural=='Q1' and weather>=0.52:
        primary='quality_disinflation'; alt='reflation_reaccel'; invalidator='growth_scare'
    else:
        primary='growth_scare' if risk_off>=0.55 else 'quality_disinflation'
        alt='reflation_reaccel' if primary!='reflation_reaccel' else 'growth_scare'
        invalidator='deflationary_riskoff' if primary!='deflationary_riskoff' else 'vshape_rebound'

    if div=='divergent' and monthly=='Q2' and exec_score>=0.56 and weather>=0.56:
        alt='reflation_reaccel'
    if div=='divergent' and monthly=='Q4' and risk_off>=0.58:
        alt='vshape_rebound' if primary=='deflationary_riskoff' else 'deflationary_riskoff'
    if alt==primary:
        alt='vshape_rebound' if primary!='vshape_rebound' else 'reflation_reaccel'

    confidence=float(np.clip(
        0.28*(1.0-abs(risk_off-0.5))+
        0.24*weather+
        0.20*exec_score+
        0.16*(1.0 if div=='aligned' else 0.55)+
        0.12*(1.0-min(crash_score,0.75)),
        0.0,1.0
    ))

    if primary in {'panic_crash','deflationary_riskoff'}:
        long_allowed=False; short_allowed=True; route_bias='defensive'; position_cap=0.25 if primary=='panic_crash' else 0.50
    elif primary=='stagflation_persist':
        long_allowed=True; short_allowed=True; route_bias='barbell'; position_cap=0.60
    elif primary in {'reflation_reaccel','quality_disinflation','vshape_rebound'}:
        long_allowed=True; short_allowed=False if primary!='vshape_rebound' else True; route_bias='pro-risk'; position_cap=1.00 if confidence>=0.60 else 0.75
    else:
        long_allowed=True; short_allowed=True; route_bias='mixed'; position_cap=0.60

    primary_meta=ROUTE_STATE_META.get(primary,ROUTE_STATE_META['growth_scare'])
    alt_meta=ROUTE_STATE_META.get(alt,ROUTE_STATE_META['growth_scare'])
    invalidator_meta=ROUTE_STATE_META.get(invalidator,ROUTE_STATE_META['growth_scare'])
    return {
        'primary':primary,'alt':alt,'invalidator_route':invalidator,
        'primary_meta':primary_meta,'alt_meta':alt_meta,'invalidator_meta':invalidator_meta,
        'confidence':round(confidence,3),'route_bias':route_bias,'position_cap':position_cap,
        'long_allowed':long_allowed,'short_allowed':short_allowed,
        'risk_off':risk_off,'crash_score':crash_score,'exec_score':exec_score,
        'structural_quad':structural,'monthly_quad':monthly,'divergence':div,
        'slowdown_flags':slowdown_flags,'tail_state':tail_state,
    }


def build_asset_translation(route_state:str, q:Dict, h:Dict, f:Dict, route:Optional[Dict]=None) -> Dict:
    """Structured asset translation with bias, trigger, invalidator, size cap, and execution note."""
    route = route or {}
    shock=float(q.get('inf_shock',0.0) or 0.0)
    stress=(shock>0.30 or h.get('tail_state')=='stressed')
    mixed=(h.get('weather',0.5)<0.58)
    position_cap=float(route.get('position_cap',0.60) or 0.60)

    def _cap(x:float)->str:
        if x>=0.95: return '1.00x'
        if x>=0.70: return '0.75x'
        if x>=0.45: return '0.50x'
        return '0.25x'

    route_caps={'panic_crash':0.25,'deflationary_riskoff':0.50,'stagflation_persist':0.60,'growth_scare':0.50,'quality_disinflation':0.75,'reflation_reaccel':1.00,'vshape_rebound':0.60}
    local_cap=_cap(min(position_cap, route_caps.get(route_state,0.60)))

    translations={
        'panic_crash': {
            'US':[
                {'bias':'AVOID','setup':'Broad beta longs','tickers':['SPY','QQQ','IWM'],'why':'Crash branch aktif, broad beta jadi alat jual paksa.','trigger':'Crash meter turun jelas + breadth stabil.','invalidator':'Cascade selling berlanjut.','size_cap':'0.25x','timeframe':'Trade only','execution_note':'No aggressive longs.'},
                {'bias':'LONG','setup':'Safe havens','tickers':['TLT','GLD','UUP'],'why':'Survival dulu, offense belakangan.','trigger':'Yields turun / fear lanjut.','invalidator':'V-shape relief kuat.','size_cap':'0.50x','timeframe':'Trade / Trend','execution_note':'Prioritize capital preservation.'},
                {'bias':'SHORT','setup':'Broken high beta','tickers':['QQQ','IWM','HYG'],'why':'Forced deleveraging masih dominan.','trigger':'Breakdown persists.','invalidator':'Breadth + credit repair.','size_cap':'0.50x','timeframe':'Trade','execution_note':'Only if liquid and clean.'},
            ],
            'IHSG':[{'bias':'AVOID','setup':'Broad domestic beta','tickers':['^JKSE','BBRI.JK','BSDE.JK'],'why':'EM beta rentan saat crash branch global.','trigger':'Need USD calm + foreign flow stabilize.','invalidator':'USD pressure persists.','size_cap':'0.25x','timeframe':'Trade','execution_note':'Stay selective only.'}],
            'FX':[{'bias':'LONG','setup':'USD safety','tickers':['UUP','IDR=X','CNH=X'],'why':'Funding stress favors dollar.','trigger':'Vol high + breadth weak.','invalidator':'DXY breaks down.','size_cap':'0.50x','timeframe':'Trade / Trend','execution_note':'Prefer USD over carry.'}],
            'Commodities':[{'bias':'WATCH','setup':'Gold only, not broad commodities','tickers':['GC=F','GLD'],'why':'Gold can hedge, cyclicals still fragile.','trigger':'Real yields stop rising.','invalidator':'USD + real yields rip higher.','size_cap':'0.50x','timeframe':'Trade / Trend','execution_note':'Avoid oil/copper beta.'}],
            'Crypto':[{'bias':'AVOID','setup':'High beta crypto','tickers':['BTC-USD','ETH-USD','SOL-USD'],'why':'Liquidity stress hits crypto fast.','trigger':'Need relief branch active.','invalidator':'Another volatility shock.','size_cap':'0.25x','timeframe':'Trade only','execution_note':'No hero catching.'}],
        },
        'deflationary_riskoff': {
            'US':[
                {'bias':'LONG','setup':'Long bonds + defensives','tickers':['TLT','XLP','XLU','XLV'],'why':'Q4/risk-off favors duration and defensives.','trigger':'Yields down, defensives outperform.','invalidator':'Reflation surprise.','size_cap':local_cap,'timeframe':'Trend / Tail','execution_note':'Prefer quality cash-flow.'},
                {'bias':'WATCH','setup':'Gold','tickers':['GLD','GC=F'],'why':'Can still work, but bonds are cleaner in pure deflationary scare.','trigger':'Dollar stops overpowering.','invalidator':'Real yields jump.','size_cap':'0.50x','timeframe':'Trade / Trend','execution_note':'Secondary safe harbor.'},
                {'bias':'SHORT','setup':'Cyclicals / junk beta','tickers':['IWM','HYG','XLY'],'why':'Growth scare hurts balance-sheet-light risk.','trigger':'Breadth remains weak.','invalidator':'Credit repair.','size_cap':'0.50x','timeframe':'Trade','execution_note':'Short only on weakness, not late chase.'},
            ],
            'IHSG':[{'bias':'WATCH','setup':'Top-quality banks only','tickers':['BBCA.JK'],'why':'If must own IHSG, own quality.','trigger':'USD pressure eases.','invalidator':'Foreign flow deteriorates again.','size_cap':'0.25x','timeframe':'Trade','execution_note':'No broad IHSG beta.'}],
            'FX':[{'bias':'LONG','setup':'USD vs fragile beta','tickers':['IDR=X','CNH=X','SGD=X'],'why':'Dollar stays cleaner than EM beta.','trigger':'Risk-off persists.','invalidator':'Broad reflation branch.','size_cap':'0.50x','timeframe':'Trade / Trend','execution_note':'Avoid carry-heavy longs.'}],
            'Commodities':[{'bias':'AVOID','setup':'Oil / copper cyclicals','tickers':['CL=F','HG=F'],'why':'Pure growth scare hurts cyclicals.','trigger':'Need reflation reaccel first.','invalidator':'Demand impulse returns.','size_cap':'0.25x','timeframe':'Trade','execution_note':'Stay defensive.'}],
            'Crypto':[{'bias':'AVOID','setup':'Broad crypto beta','tickers':['BTC-USD','ETH-USD'],'why':'Deflationary risk-off rarely rewards aggressive crypto longs.','trigger':'Need route flip.','invalidator':'Liquidity impulse returns.','size_cap':'0.25x','timeframe':'Trade only','execution_note':'Preserve cash.'}],
        },
        'stagflation_persist': {
            'US':[
                {'bias':'LONG','setup':'Energy & cash-flow leaders','tickers':['XLE','XOM','CVX'],'why':'Hard-asset/cash-flow producers tahan paling baik.','trigger':'Oil/gold leadership persists.','invalidator':'Breadth widens and hard-asset lead fades.','size_cap':local_cap,'timeframe':'Trade / Trend','execution_note':'Best longs are selective, not broad.'},
                {'bias':'LONG' if not mixed else 'WATCH','setup':'Selective defensives / quality','tickers':['XLP','XLV','TLT'],'why':'Dipakai saat growth melemah tapi broad relief belum confirm.','trigger':'Beta remains fragile.','invalidator':'Equal-weight + small caps confirm upside.','size_cap':'0.50x','timeframe':'Trade / Trend','execution_note':'Barbell posture.'},
                {'bias':'SHORT' if stress else 'AVOID','setup':'Weak small-cap & long-duration laggards','tickers':['QQQ','IWM','HYG'],'why':'Stagflation punishes duration-sensitive beta.','trigger':'USD firm + breadth weak.','invalidator':'Yields + USD cool together.','size_cap':'0.50x','timeframe':'Trade','execution_note':'Short laggards, not leaders.'},
            ],
            'IHSG':[
                {'bias':'LONG','setup':'Exporters / resource-linked','tickers':['ADRO.JK','PTBA.JK','ANTM.JK'],'why':'Exporter/resource branch helps IHSG in Q3.','trigger':'Commodity chain still alive.','invalidator':'USD pressure and commodity lead both fade.','size_cap':local_cap,'timeframe':'Trade / Trend','execution_note':'Prefer resource over domestic demand beta.'},
                {'bias':'WATCH','setup':'Quality banks','tickers':['BBCA.JK'],'why':'Quality financials can survive but not broad domestic beta.','trigger':'Funding stress stays contained.','invalidator':'FX pressure worsens.','size_cap':'0.25x','timeframe':'Trade','execution_note':'Selective only.'},
                {'bias':'AVOID','setup':'Import-sensitive domestic names','tickers':['ICBP.JK','BSDE.JK'],'why':'FX + input-cost squeeze.','trigger':'Need USD down + energy pressure cool.','invalidator':'Domestic relief confirmed.','size_cap':'0.25x','timeframe':'Trade','execution_note':'Avoid broad consumer/property chase.'},
            ],
            'FX':[{'bias':'LONG','setup':'USD vs fragile importers','tickers':['IDR=X','CNH=X'],'why':'Dollar usually cleaner in stagflation stress.','trigger':'Vol and breadth remain fragile.','invalidator':'Broad risk-on confirmation.','size_cap':'0.50x','timeframe':'Trade / Trend','execution_note':'Avoid funding-sensitive carry.'}],
            'Commodities':[{'bias':'LONG','setup':'Gold first, oil selective','tickers':['GC=F','GLD','CL=F'],'why':'Gold is cleanest; oil only if shock branch still live.','trigger':'Real yields stable, supply shock not resolved.','invalidator':'USD + real yields both surge.','size_cap':local_cap,'timeframe':'Trade / Trend','execution_note':'Gold cleaner than copper.'}],
            'Crypto':[{'bias':'WATCH','setup':'Only high-quality liquid crypto','tickers':['BTC-USD','ETH-USD'],'why':'Can trade, but macro backdrop still hostile.','trigger':'Liquidity relief improves.','invalidator':'Dollar re-accelerates + vol spikes.','size_cap':'0.25x','timeframe':'Trade only','execution_note':'Do not size like Q1/Q2.'}],
        },
        'growth_scare': {
            'US':[
                {'bias':'LONG','setup':'Defensives / duration','tickers':['TLT','XLV','XLP'],'why':'Growth scare favors safety before clean reflation.','trigger':'Yields falling + cyclicals lag.','invalidator':'Reflation branch confirmed.','size_cap':'0.50x','timeframe':'Trade / Trend','execution_note':'Stay patient.'},
                {'bias':'WATCH','setup':'Gold','tickers':['GLD'],'why':'Useful hedge, but not always first best expression.','trigger':'Dollar not too dominant.','invalidator':'Real yields rise.','size_cap':'0.50x','timeframe':'Trade','execution_note':'Secondary offense.'},
                {'bias':'AVOID','setup':'Broad cyclicals','tickers':['IWM','XLY','HYG'],'why':'Growth scare punishes weak balance sheets.','trigger':'Need route flip.','invalidator':'Breadth/cyclicals repair.','size_cap':'0.25x','timeframe':'Trade','execution_note':'No broad chase.'},
            ],
            'IHSG':[{'bias':'WATCH','setup':'Quality + defensive exposure','tickers':['BBCA.JK','TLKM.JK'],'why':'If touching IHSG, keep it high quality.','trigger':'USD and foreign flow stabilize.','invalidator':'Commodity/em pressure worsens.','size_cap':'0.25x','timeframe':'Trade','execution_note':'No broad domestic beta.'}],
            'FX':[{'bias':'LONG','setup':'USD defensive tilt','tickers':['IDR=X','CNH=X'],'why':'Growth scare keeps safety demand alive.','trigger':'Risk appetite weak.','invalidator':'Global breadth repair.','size_cap':'0.50x','timeframe':'Trade / Trend','execution_note':'Avoid carry stretch.'}],
            'Commodities':[{'bias':'WATCH','setup':'Gold over cyclicals','tickers':['GC=F','GLD'],'why':'Gold cleaner than oil/copper in scare.','trigger':'Rates soften.','invalidator':'Real yields surge.','size_cap':'0.50x','timeframe':'Trade','execution_note':'Skip demand-sensitive cyclicals.'}],
            'Crypto':[{'bias':'AVOID','setup':'Broad crypto risk','tickers':['BTC-USD','ETH-USD'],'why':'Still too correlated to liquidity appetite.','trigger':'Need better route.','invalidator':'Another risk-off wave.','size_cap':'0.25x','timeframe':'Trade only','execution_note':'Cash is a position.'}],
        },
        'quality_disinflation': {
            'US':[
                {'bias':'LONG','setup':'Quality growth + disinflation winners','tickers':['QQQ','MSFT','AAPL'],'why':'Growth improving while inflation eases.','trigger':'Breadth expands, yields orderly.','invalidator':'Inflation shock returns.','size_cap':local_cap,'timeframe':'Trend / Tail','execution_note':'Higher quality first.'},
                {'bias':'WATCH','setup':'EM / selective cyclicals','tickers':['EEM','XLF'],'why':'Second-wave beneficiaries after quality confirms.','trigger':'USD softer + breadth wider.','invalidator':'Dollar re-accelerates.','size_cap':'0.50x','timeframe':'Trade / Trend','execution_note':'Scale after confirmation.'},
            ],
            'IHSG':[{'bias':'LONG','setup':'Quality banks + selective growth','tickers':['BBCA.JK','BMRI.JK','TLKM.JK'],'why':'Better backdrop for domestic quality.','trigger':'IDR stable + foreign flow improves.','invalidator':'USD pressure returns.','size_cap':local_cap,'timeframe':'Trend','execution_note':'Prefer quality compounders.'}],
            'FX':[{'bias':'WATCH','setup':'EM catch-up','tickers':['IDR=X'],'why':'Works only if USD properly softens.','trigger':'DXY downtrend confirmed.','invalidator':'Dollar squeeze.','size_cap':'0.50x','timeframe':'Trade / Trend','execution_note':'Selective carry only.'}],
            'Commodities':[{'bias':'WATCH','setup':'Gold / selective copper','tickers':['GLD','HG=F'],'why':'Mixed, depends on inflation and growth quality.','trigger':'Growth and breadth both improve.','invalidator':'Shock branch returns.','size_cap':'0.50x','timeframe':'Trade','execution_note':'Not first-best expression.'}],
            'Crypto':[{'bias':'WATCH','setup':'Majors only','tickers':['BTC-USD','ETH-USD'],'why':'Can improve in better liquidity backdrop, but still need confirmation.','trigger':'Breadth + liquidity improve together.','invalidator':'Dollar/real yields reverse.','size_cap':'0.50x','timeframe':'Trade','execution_note':'No low-quality alt chase.'}],
        },
        'reflation_reaccel': {
            'US':[
                {'bias':'LONG','setup':'Cyclicals / reflation winners','tickers':['XLE','XLF','IWM'],'why':'Growth and inflation re-accelerating reopens broad beta.','trigger':'Breadth widens, yields rise orderly.','invalidator':'Growth scare or oil rollback collapse.','size_cap':local_cap,'timeframe':'Trade / Trend','execution_note':'Broader offense allowed.'},
                {'bias':'WATCH','setup':'Quality growth','tickers':['QQQ','NVDA'],'why':'Still works, but cyclicals may catch up harder.','trigger':'Leadership broadens.','invalidator':'Rates spike disorderly.','size_cap':'0.75x','timeframe':'Trade / Trend','execution_note':"Don't be one-factor only."},
            ],
            'IHSG':[{'bias':'LONG','setup':'Banks + resource + selective domestic','tickers':['BBCA.JK','ADRO.JK','PTBA.JK'],'why':'IHSG likes both bank quality and commodity spillover in reflation.','trigger':'Foreign flow improves.','invalidator':'USD up / commodity rollover.','size_cap':local_cap,'timeframe':'Trade / Trend','execution_note':'Best broad IHSG branch.'}],
            'FX':[{'bias':'WATCH','setup':'Carry / EM FX selectively','tickers':['IDR=X'],'why':'Only works if vol behaves.','trigger':'DXY softer, vol lower.','invalidator':'Dollar squeezes.','size_cap':'0.50x','timeframe':'Trade','execution_note':'Selective, not blind carry.'}],
            'Commodities':[{'bias':'LONG','setup':'Oil / copper / reflation basket','tickers':['CL=F','HG=F','DBC'],'why':'Best cyclical commodity branch.','trigger':'Demand impulse alive.','invalidator':'Growth slowdown returns.','size_cap':local_cap,'timeframe':'Trade / Trend','execution_note':'More offense okay here.'}],
            'Crypto':[{'bias':'WATCH','setup':'Majors on liquidity expansion','tickers':['BTC-USD','ETH-USD'],'why':'Can participate if risk appetite broadens.','trigger':'Dollar down + liquidity up.','invalidator':'Policy shock or yields spike.','size_cap':'0.50x','timeframe':'Trade','execution_note':'Still use disciplined sizing.'}],
        },
        'vshape_rebound': {
            'US':[
                {'bias':'WATCH','setup':'Fast beta rebound','tickers':['QQQ','IWM','SPY'],'why':'Powerful but fragile reflex rally.','trigger':'Breadth thrust and short-covering persist.','invalidator':'Fails within 1–2 weeks.','size_cap':'0.50x','timeframe':'Trade only','execution_note':'Do not confuse with durable trend yet.'},
                {'bias':'WATCH','setup':'Most hated squeeze names','tickers':['IWM','HYG'],'why':'Can rip hardest but break hardest too.','trigger':'Confirmation via breadth + credit.','invalidator':'Breadth fades quickly.','size_cap':'0.25x','timeframe':'Trade only','execution_note':'Hit-and-run, not investment.'},
            ],
            'IHSG':[{'bias':'WATCH','setup':'Tactical beta bounce','tickers':['^JKSE','BBRI.JK'],'why':'Can squeeze if foreign relief comes fast.','trigger':'USD cools and flows stabilize.','invalidator':'Relief dies fast.','size_cap':'0.25x','timeframe':'Trade only','execution_note':"Don't overstay."}],
            'FX':[{'bias':'WATCH','setup':'USD fade tactical','tickers':['IDR=X'],'why':'Only if relief is real.','trigger':'Dollar loses momentum.','invalidator':'DXY reclaims trend.','size_cap':'0.25x','timeframe':'Trade only','execution_note':'Tactical only.'}],
            'Commodities':[{'bias':'WATCH','setup':'Cyclical rebound basket','tickers':['CL=F','HG=F'],'why':'Good for squeeze, not durable by default.','trigger':'Demand expectations rebound.','invalidator':'Relief fails.','size_cap':'0.25x','timeframe':'Trade only','execution_note':'No oversized conviction.'}],
            'Crypto':[{'bias':'WATCH','setup':'High beta bounce','tickers':['BTC-USD','ETH-USD'],'why':'Can bounce violently, but still fragile.','trigger':'Liquidity improves quickly.','invalidator':'Vol returns.','size_cap':'0.25x','timeframe':'Trade only','execution_note':'Tactical, not core.'}],
        },
    }

    out=translations.get(route_state, translations['growth_scare'])
    for market, rows in out.items():
        for row in rows:
            row['route']=route_state
            row['route_bias']=route.get('route_bias','mixed')
            row['weather']='mixed' if mixed else 'supportive'
            row['stress']='stressed' if stress else 'contained'
            if stress and row['bias']=='LONG' and row['size_cap']=='1.00x':
                row['size_cap']='0.75x'
    return out


def _countdown_to_proximity(countdown:str)->float:
    s=str(countdown or '').strip().lower()
    if not s or '?' in s:
        return 0.45
    try:
        if 't-' in s and 'd' in s:
            days=float(s.replace('t-','').replace('d','').replace('~','').strip())
            return clamp(np.exp(-days/30.0))
    except Exception:
        pass
    return 0.40


def build_news_catalyst_overlay(q:Dict, f:Dict, h:Dict, route:Optional[Dict]=None, most_hated:Optional[Dict]=None) -> Dict:
    """Event-lite catalyst filter: combine current market-implied pressure with scheduled catalyst families.
    This is intentionally not a literal news reader; it is a front-run catalyst mapper.
    """
    route=route or {}
    most_hated=most_hated or {}
    oil_3m=nf(f.get("clf_3m",f.get("oil_3m",0.0)))
    uup_1m=nf(f.get("uup_1m",0.0)); tlt_1m=nf(f.get("tlt_1m",0.0))
    vix=f.get("vix_last",20.0); vix_1m=nf(f.get("vix_1m",0.0))
    spy_1m=nf(f.get("spy_1m",0.0)); iwm_1m=nf(f.get("iwm_1m",0.0))
    sf=q.get("slowdown_flags",0.0); shock=q.get("inf_shock",0.0)
    branch_state=str(most_hated.get("branch_state","dormant"))

    oil_up=max(0.0,oil_3m); oil_down=max(0.0,-oil_3m)
    usd_up=max(0.0,uup_1m); usd_down=max(0.0,-uup_1m)
    long_end=max(0.0,-tlt_1m); vol_stress=max(0.0,vix_1m/20)
    breadth_stress=max(0.0,-iwm_1m+spy_1m) if spy_1m>0 else 0.0
    breadth_relief=max(0.0,iwm_1m-spy_1m) if iwm_1m>spy_1m else 0.0

    war_oil=clamp(0.28*clamp(0.5+oil_up/0.12)+0.20*clamp(0.5+usd_up/0.04)+0.18*shock+0.16*clamp(0.5+vol_stress)+0.18*clamp(0.5+breadth_stress/0.03))
    policy_pressure=clamp(0.28*clamp(0.5+long_end/0.05)+0.22*sf+0.18*clamp(0.5+usd_up/0.04)+0.14*clamp(0.5+vol_stress)+0.18*shock)
    relief=clamp(0.26*clamp(0.5+oil_down/0.10)+0.18*clamp(0.5+usd_down/0.04)+0.22*clamp(0.5+breadth_relief/0.03)+0.16*(1-shock)+0.18*(1.0 if branch_state in {"arming","pre_confirmed","active"} else 0.0))

    family_scores={
        "inflation": max(war_oil, shock),
        "policy": max(policy_pressure, relief*0.8),
        "growth": max(sf, relief*0.6),
        "labor": max(sf, policy_pressure*0.7),
        "geopolitics": max(war_oil, relief),
    }
    event_rows=[]
    for ev in UPCOMING_EVENTS:
        fam=str(ev.get("family",""))
        proximity=_countdown_to_proximity(ev.get("countdown",""))
        fam_score=clamp(family_scores.get(fam,0.35))
        score=clamp(0.58*fam_score+0.42*proximity)
        event_rows.append({
            "type":fam.upper() if fam else "EVENT",
            "label":ev.get("title","Event"),
            "impact":"high" if score>=0.68 else ("medium" if score>=0.52 else "watch"),
            "score":score,
            "countdown":ev.get("countdown",""),
        })
    event_rows.sort(key=lambda x:x["score"], reverse=True)
    top_events=event_rows[:5]

    dominant=max({"war_oil":war_oil,"policy_pressure":policy_pressure,"relief":relief}.items(), key=lambda kv: kv[1])
    s=dominant[0]
    if s=="war_oil" and war_oil>=0.58:
        label="⚔️ Event-Lite: War/Oil Shock"
        desc="Energy shock / USD pressure masih dominan. Front-run via exporters, avoid importers / broad beta."
        cls="bad"
    elif s=="policy_pressure" and policy_pressure>=0.56:
        label="📋 Event-Lite: Policy / Duration Pressure"
        desc="Long-end pain, slowdown flags, dan funding pressure masih dominan. Focus pada quality, selective shorts, dan confirmation breadth."
        cls="warn"
    elif relief>=0.50:
        label="🕊️ Event-Lite: Relief / De-escalation"
        desc="Pressure mulai mereda. Front-run breadth broadening, EM rotation, dan laggard catch-up; fade overcrowded safe havens."
        cls="good"
    else:
        label="😶 Event-Lite: No Dominant Catalyst"
        desc="Tidak ada catalyst dominan. Ikuti regime + route; hindari maksa front-run."
        cls="neu"

    return {
        "state":s,
        "label":label,
        "desc":desc,
        "cls":cls,
        "war_oil":war_oil,
        "policy_pressure":policy_pressure,
        "relief":relief,
        "events":top_events,
        "dominant_family":top_events[0]["type"] if top_events else "EVENT",
    }


def build_forward_radar(prices:Dict[str,pd.Series], q:Dict, f:Dict, route:Optional[Dict]=None,
                        opps:Optional[List[Dict]]=None, risk_ranges:Optional[Dict]=None,
                        most_hated:Optional[Dict]=None, news_overlay:Optional[Dict]=None) -> List[Dict]:
    """Forward radar built from near-ready opportunities plus route/catalyst state.
    Goal: show what can be front-run next without pretending it is already actionable.
    """
    route=route or {}
    opps=opps or []
    risk_ranges=risk_ranges or {}
    most_hated=most_hated or {}
    news_overlay=news_overlay or {}
    quad=str(q.get("quad","Q3"))
    hot_branch=str(most_hated.get("branch_state","dormant")) in {"arming","pre_confirmed","active"}
    catalyst_state=str(news_overlay.get("state","quiet"))

    rows=[]
    seen=set()
    for r in opps:
        bias=str(r.get("Bias",""))
        setup=str(r.get("Setup","C"))
        path=str(r.get("Path","Watch"))
        why_not=str(r.get("Why Not Yet","none"))
        raw=str(r.get("_raw_ticker","") or r.get("Ticker",""))
        if not raw or raw in seen:
            continue
        if path not in {"Watch","Tactical"}:
            continue
        if setup not in {"A","B","C"}:
            continue
        if "WATCH" not in bias and path=="Primary":
            continue
        rr=risk_ranges.get(raw,{})
        side="LONG" if "LONG" in bias else "SHORT"
        next_trigger=[]
        if side=="LONG":
            if str(r.get("Macro Aligned",""))!="✓":
                next_trigger.append("macro alignment clean up")
            if str(r.get("Route Aligned","")) not in {"✓","~ Tactical"}:
                next_trigger.append("route branch confirm")
            if str(r.get("Range Aligned",""))!="✓":
                next_trigger.append("better edge / buy-dip zone")
            if catalyst_state=="relief" and raw in {"EEM","IWM","RSP","QQQ","XLF","XLI","BTC-USD","ETH-USD","SOL-USD","BBCA.JK","BBRI.JK","BMRI.JK"}:
                next_trigger.append("breadth broadening follow-through")
            if hot_branch and raw in {"EEM","IWM","BTC-USD","ETH-USD","SOL-USD","BBCA.JK","BBRI.JK","BMRI.JK"}:
                next_trigger.append("rally checklist stays alive")
        else:
            if str(r.get("Macro Aligned",""))!="✓":
                next_trigger.append("risk-off macro confirm")
            if str(r.get("Route Aligned","")) not in {"✓","~ Tactical"}:
                next_trigger.append("bear route confirm")
            if str(r.get("Range Aligned",""))!="✓":
                next_trigger.append("better rip / breakdown zone")
            if catalyst_state=="war_oil" and raw in {"QQQ","IWM","EEM","BTC-USD","ETH-USD","SOL-USD","^JKSE","HYG"}:
                next_trigger.append("breadth failure persist")
        s=_s(prices.get(raw,pd.Series()))
        r1=ret_n(s,21)
        status="Starting to confirm" if (side=="LONG" and math.isfinite(r1) and r1>0) or (side=="SHORT" and math.isfinite(r1) and r1<0) else "On radar"
        rows.append({
            "ticker": raw,
            "ticker_display": disp(raw),
            "side": side,
            "why_not_yet": why_not,
            "trigger": "; ".join(next_trigger[:3]) if next_trigger else "watch for cleaner confirmation",
            "signal_quality": setup,
            "momentum_1m": pct(r1) if math.isfinite(r1) else "—",
            "status": status,
        })
        seen.add(raw)
        if len(rows)>=12:
            break

    if not rows:
        fallback={
            "Q1":[("EEM","LONG","USD calm + EM breadth"),("IWM","LONG","small-cap breadth follow-through"),("XLF","LONG","credit tighten")],
            "Q2":[("XLI","LONG","growth + reflation confirm"),("HG=F","LONG","copper follows through"),("ADRO.JK","LONG","commodity leadership persists")],
            "Q3":[("GLD","LONG","real yields peak / slowdown deepens"),("QQQ","SHORT","breadth failure confirm"),("CTRA.JK","SHORT","USD/IDR pressure persists")],
            "Q4":[("TLT","LONG","credit widens / yields roll over"),("XLP","LONG","defensive breadth improves"),("XLE","SHORT","oil breakdown confirms")],
        }
        for tk,side,trg in fallback.get(quad,[]):
            rows.append({"ticker":tk,"ticker_display":disp(tk),"side":side,"why_not_yet":"fallback watchlist on selective day","trigger":trg,"signal_quality":"C","momentum_1m":pct(ret_n(prices.get(tk,pd.Series()),21)) if math.isfinite(ret_n(prices.get(tk,pd.Series()),21)) else "—","status":"On radar"})
    return rows


def build_strong_weak_all(prices:Dict[str,pd.Series], q:Dict) -> Dict:
    """v33 Strong/Weak per market for FX, Commodities, Crypto."""
    quad=q["quad"]
    def sw_market(tickers, names_map, n=5):
        rows=[]
        for tk in tickers:
            s=prices.get(tk,pd.Series()); r1=ret_n(s,21); r3=ret_n(s,63)
            if not math.isfinite(r1): continue
            rows.append({"tk":tk,"name":names_map.get(tk,disp(tk)),"r1":r1,"r3":r3,"trend":ts(s)})
        rows.sort(key=lambda x:x["r1"],reverse=True)
        return {"strong":rows[:n],"weak":rows[-n:][::-1]}

    fx_tickers=["EURUSD=X","GBPUSD=X","AUDUSD=X","JPY=X","CHF=X","IDR=X","CAD=X","SGD=X"]
    fx_names={"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","AUDUSD=X":"AUD/USD","JPY=X":"USD/JPY","CHF=X":"USD/CHF","IDR=X":"USD/IDR","CAD=X":"USD/CAD","SGD=X":"USD/SGD"}
    comm_tickers=["GC=F","SI=F","CL=F","BZ=F","NG=F","HG=F","ZC=F","ZW=F"]
    comm_names={"GC=F":"XAUUSD","SI=F":"XAGUSD","CL=F":"WTI Oil","BZ=F":"Brent","NG=F":"Nat Gas","HG=F":"Copper","ZC=F":"Corn","ZW=F":"Wheat"}
    crypto_tickers=["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD","ADA-USD","AVAX-USD","LINK-USD"]
    crypto_names={t:disp(t) for t in crypto_tickers}

    return {"fx":sw_market(fx_tickers,fx_names),"commodities":sw_market(comm_tickers,comm_names),"crypto":sw_market(crypto_tickers,crypto_names)}


def render_rotational_flow_map(q:Dict, rot:Dict, f:Dict, family:str)->None:
    """
    v33 Rotational Flow Map — visual mind map for orang awam.
    Shows causal chain: macro trigger → market family → spillover → expression → shelter.
    This is the KEY visual the user asked for: easy to read, shows "mana yang jalan duluan".
    """
    quad=q["quad"]; m_quad=q["monthly_quad"]; div=q["divergence"]
    top_ben=rot.get("top_ben","XAUUSD"); top_safe=rot.get("top_safe","Gold")
    spill_us=rot.get("spill_us",[]); top_us=rot.get("top_us_bucket","Growth / Tech")
    em_score=rot.get("em_score",0.5); em_state=rot.get("em_state","Wait")
    petro=rot.get("petro_score",0.0)
    uup_1m=nf(f.get("uup_1m",0.0)); oil_3m=nf(f.get("clf_3m",f.get("oil_3m",0.0)))

    # Colors per role
    C={"trigger":"#378ADD","first":"#3dbb6c","second":"#e5a020","expression":"#9b6aff",
       "shelter":"#e05252","active":"#59a8e5","dim":"rgba(255,255,255,0.15)"}

    # Determine active stage
    if div=="aligned" and q.get("flip_hazard",0.5)<0.40: active_stage=0  # structural holds
    elif div=="divergent": active_stage=1   # monthly overlay in play
    elif petro>0.45: active_stage=2         # expression: energy
    else: active_stage=2                    # expression: default

    # Build 5-node flow based on active family
    family_meta=ROTATION_FAMILIES.get(family,ROTATION_FAMILIES["reflation"])
    nodes_data=family_meta.get("nodes",[])

    def _pill(t,bc)->str:
        return ('<span style="display:inline-block;padding:1px 7px;border-radius:99px;'+
                'border:1px solid '+bc+'44;background:'+bc+'15;color:'+bc+';'+
                'font-size:9px;font-weight:700;margin:1px 2px">'+ t+'</span>')

    def _node(title, label, note, tickers, role_color, *, is_active=False)->str:
        bc=role_color if not is_active else "#fff"
        bg=role_color+"20" if is_active else "rgba(255,255,255,0.02)"
        border="2px solid "+role_color if is_active else "1px solid "+role_color+"33"
        you_badge=('<div style="font-size:8px;font-weight:800;color:'+role_color+';margin-bottom:2px">◉ KITA DI SINI</div>') if is_active else ""
        pills="".join(_pill(t,role_color) for t in tickers[:3])
        return (
            '<div style="'+border+';background:'+bg+';border-radius:10px;padding:9px 8px;'+
            'text-align:center;flex:1;min-width:0;display:flex;flex-direction:column;justify-content:center">'+
            you_badge+
            '<div style="font-size:8px;color:'+role_color+';font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-bottom:2px">'+title+'</div>'+
            '<div style="font-size:13px;font-weight:700;color:var(--color-text-primary);line-height:1.2;margin-bottom:3px">'+label+'</div>'+
            '<div style="font-size:9px;color:var(--color-text-secondary);line-height:1.3;margin-bottom:4px">'+note[:42]+'</div>'+
            '<div>'+pills+'</div>'
            '</div>'
        )

    def _arrow()->str:
        return '<div style="font-size:16px;color:rgba(255,255,255,0.3);display:flex;align-items:center;padding:0 3px">&rarr;</div>'

    role_cols=[C["trigger"],C["first"],C["second"],C["expression"],C["shelter"]]
    nodes_html=[]
    for i,node in enumerate(nodes_data[:5]):
        rc=role_cols[i] if i<len(role_cols) else C["dim"]
        is_active=(i==active_stage)
        tickers=ROTATION_FAMILIES.get(family,{}).get("best_expressions",{})
        # get relevant tickers for this node stage
        expr_tickers=[]
        if i==3:  # expression node
            for mkt_tickers in list(tickers.values())[:2]:
                expr_tickers.extend([t for t in mkt_tickers[:2] if not t.startswith("select")])
        nodes_html.append(_node(node["role"],node["label"],node["why"],expr_tickers[:3],rc,is_active=is_active))

    sep=_arrow()
    container=(
        '<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);'+
        'border-radius:12px;padding:12px 10px;margin:6px 0">'+
        '<div style="font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;'+
        'color:rgba(255,255,255,0.3);margin-bottom:8px">ROTATIONAL FLOW MAP — '+
        family_meta.get("name","").upper()+' &mdash; CARA BACA: dari kiri ke kanan</div>'+
        '<div style="display:flex;align-items:stretch;gap:3px;flex-wrap:nowrap">'+
        sep.join(nodes_html)+
        '</div>'+
        '<div style="margin-top:8px;font-size:10px;color:rgba(255,255,255,0.4);">'+
        '&bull; Panah = urutan transmisi. &#9679; = saat ini. Warna: Trigger &rarr; First order &rarr; Second order &rarr; Expression &rarr; Invalidation</div>'+
        '</div>'
    )
    st.markdown(container, unsafe_allow_html=True)

    # Best expressions table below the map (compact)
    be=family_meta.get("best_expressions",{})
    if be:
        be_cols=st.columns(len(be))
        for col,(mkt,tickers) in zip(be_cols,be.items()):
            with col:
                st.markdown(f"**{mkt}**")
                for t in tickers[:3]:
                    s=prices_placeholder.get(t,pd.Series()) if t in prices_placeholder else pd.Series()
                    r1=ret_n(s,21); perf=pct(r1) if math.isfinite(r1) else ""
                    cls="good" if(math.isfinite(r1) and r1>0) else("bad" if(math.isfinite(r1) and r1<-0.01) else "")
                    st.markdown('<span class="'+cls+'" style="font-size:11px">'+disp(t)+' '+perf+'</span>  \n',unsafe_allow_html=True)



def _opp_view_df(rows:List[Dict], detail:bool=False)->pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df=pd.DataFrame([{k:v for k,v in r.items()} for r in rows])
    if detail:
        detail_cols=["Ticker","Market","Bias","Setup","Path","Risk Bucket","Horizon","Entry Zone","Invalidation","Target","EV","Conf","Macro Aligned","Rally Fit","Sizing","Rally State","Why Now","Why Not Yet"]
        cols=[c for c in detail_cols if c in df.columns]
        return df[cols]
    compact_cols=["Ticker","Market","Setup","Entry Zone","Invalidation","Target","EV","Rally Fit","Sizing"]
    cols=[c for c in compact_cols if c in df.columns]
    out=df[cols].copy()
    rename_map={"Entry Zone":"Entry","Invalidation":"Stop","Target":"TP","EV":"EV+","Rally Fit":"Fit","Sizing":"Size"}
    return out.rename(columns={k:v for k,v in rename_map.items() if k in out.columns})


def _opp_card_html(rows:List[Dict], empty_text:str, accent:str, icon:str)->str:
    if not rows:
        return f'<div class="mc" style="border-left:3px solid {accent}55"><div style="font-size:12px;opacity:.65">{html.escape(empty_text)}</div></div>'
    cards=[]
    for r in rows[:5]:
        ticker=html.escape(str(r.get("Ticker","—")))
        market=html.escape(str(r.get("Market","—")))
        ev=html.escape(str(r.get("EV","—")))
        fit=html.escape(str(r.get("Rally Fit","Neutral")))
        setup=html.escape(str(r.get("Setup","—")))
        path=html.escape(str(r.get("Path","—")))
        note=html.escape(str(r.get("Why Now","")))[:120]
        cards.append(
            f'<div class="mc" style="border-left:3px solid {accent}55;padding:8px 10px">'
            f'<div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start">'
            f'<div><div style="font-size:13px;font-weight:700">{icon} {ticker}</div><div style="font-size:10px;opacity:.5;margin-top:1px">{market} · {fit} · setup {setup} · {path}</div></div>'
            f'<div style="font-family:DM Mono,monospace;font-size:12px;font-weight:700;color:{accent}">{ev}</div></div>'
            f'<div style="font-size:11px;opacity:.72;margin-top:4px;line-height:1.45">{note}</div>'
            f'</div>'
        )
    return ''.join(cards)




def render_narrative_bottlenecks(snap:Dict)->None:
    """Render active narrative bottlenecks with affected tickers per market."""
    narr=snap.get("narrative_bottlenecks",{})
    active=narr.get("active",[])
    picks=narr.get("front_run_picks",[])
    if not active and not picks:
        return
    sh("🧠 NARRATIVE BOTTLENECKS — front-run engine (v11)")
    st.caption("Inspired by Citrini / Jukan / Zephyr / Serenity methodology. Detects bottlenecks BEFORE price fully reflects them.")
    # Active narratives
    for n in active[:4]:
        stage_col="#e5a020" if n["stage"]=="front-run" else "#3dbb6c"
        st.markdown(
            f'<div class="mc" style="border-left:3px solid {stage_col}44">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:3px">'
            f'<b style="font-size:13px">{html.escape(n["name"])}</b>'
            f'<span style="font-family:DM Mono,monospace;font-size:11px;color:{stage_col}">'
            f'{n["stage"].upper()} · {n["conviction"]:.0%}</span></div>'
            f'<div style="font-size:11px;opacity:.75;margin-bottom:4px">{html.escape(n["description"])}</div>'
            f'<div style="font-size:10px;opacity:.55">'
            f'Trig: {n["trig_score"]:.0%} · Conf: {n["conf_score"]:.0%} · Boost: +{n["boost"]:.0%} EV</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        # Affected tickers per market
        if n.get("affected"):
            pills=[]
            for mkt,tks in n["affected"].items():
                for tk in tks[:4]:
                    pills.append(f'<span class="tag tag-b">{html.escape(disp(tk))}</span>')
            if pills:
                st.markdown(f'<div style="margin:2px 0 8px 12px">{" ".join(pills)}</div>',unsafe_allow_html=True)
    # Front-run picks table
    if picks:
        st.markdown("---")
        st.markdown("**🚀 FRONT-RUN PICKS — narrative conviction > 45%**")
        pick_rows=[]
        for p in picks[:10]:
            pick_rows.append({
                "Ticker":disp(p["ticker"]),
                "Market":p["market"],
                "Narrative":p["narrative"][:28],
                "Conv":f"{p['conviction']:.0%}",
                "Rationale":p["rationale"],
            })
        st.dataframe(pd.DataFrame(pick_rows),use_container_width=True,hide_index=True,height=min(len(pick_rows)*36+46,320))
    st.markdown("---")



# ═══════════════════════════════════════════════════════════════════════════════
# NARRATIVE PAGE — Front-run bottleneck visualization
# ═══════════════════════════════════════════════════════════════════════════════

def page_narrative(snap:Dict)->None:
    """Narrative Bottleneck page: front-run macro stories before price catches up."""
    narr=snap.get("narrative_bottlenecks",{})
    active=narr.get("active",[])
    picks=narr.get("front_run_picks",[])
    q=snap.get("q",{}); quad=q.get("quad","Q?")

    sh("🧠 NARRATIVE BOTTLENECK ENGINE v11")
    st.caption("Front-run methodology: detect supply-chain, policy, and positioning bottlenecks BEFORE price fully reflects them. Inspired by Citrini Research / Jukan / Zephyr / Serenity.")

    # Top narrative card
    if active:
        top=active[0]
        stage_color="#e5a020" if top["stage"]=="front-run" else "#3dbb6c"
        st.markdown(
            f'<div style="text-align:center;padding:16px;border-radius:12px;border:1.5px solid {stage_color}33;margin-bottom:12px">'
            f'<div style="font-size:10px;letter-spacing:.1em;text-transform:uppercase;opacity:.4;margin-bottom:3px">DOMINANT NARRATIVE</div>'
            f'<div style="font-family:Syne,sans-serif;font-size:26px;font-weight:800;color:{stage_color};line-height:1.1">{html.escape(top["name"])}</div>'
            f'<div style="font-size:12px;opacity:.75;margin-top:6px">{html.escape(top["description"])}</div>'
            f'<div style="font-size:11px;opacity:.5;margin-top:4px">Conviction {top["conviction"]:.0%} · Stage: {top["stage"].upper()} · Trig {top["trig_score"]:.0%} / Conf {top["conf_score"]:.0%}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    else:
        st.info("No dominant narrative detected. Market in mixed/transition state. Follow regime + route.")

    # Active narratives grid
    if len(active)>1:
        sh("📡 ACTIVE NARRATIVES")
        cols=st.columns(min(3, len(active)))
        for idx, n in enumerate(active[:6]):
            col=cols[idx % len(cols)]
            stage_col="#e5a020" if n["stage"]=="front-run" else "#3dbb6c"
            with col:
                st.markdown(
                    f'<div class="mc" style="border-left:3px solid {stage_col}44">'
                    f'<div style="font-size:10px;letter-spacing:.08em;text-transform:uppercase;opacity:.4;margin-bottom:2px">{html.escape(n["category"].upper())}</div>'
                    f'<div style="font-size:14px;font-weight:700;margin-bottom:3px">{html.escape(n["name"])}</div>'
                    f'<div style="font-size:11px;opacity:.72;margin-bottom:4px">{html.escape(n["description"][:80])}</div>'
                    f'<div style="font-size:10px;opacity:.5">Conv: {n["conviction"]:.0%} · Boost: +{n["boost"]:.0%} EV</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if n.get("affected"):
                    pills=[]
                    for mkt, tks in n["affected"].items():
                        for tk in tks[:3]:
                            pills.append(f'<span class="tag tag-b">{html.escape(disp(tk))}</span>')
                    st.markdown(f'<div style="margin-top:4px">{" ".join(pills)}</div>', unsafe_allow_html=True)

    # Front-run picks table
    if picks:
        sh("🚀 FRONT-RUN PICKS — narrative conviction > 45%")
        pick_rows=[]
        for p in picks[:12]:
            s=snap.get("prices",{}).get(p["ticker"],pd.Series())
            r1=ret_n(s,21) if not s.empty else float("nan")
            pick_rows.append({
                "Ticker":disp(p["ticker"]),
                "Market":p["market"],
                "Narrative":p["narrative"][:30],
                "Conv":f"{p['conviction']:.0%}",
                "1M":pct(r1) if math.isfinite(r1) else "—",
                "Rationale":p["rationale"],
            })
        st.dataframe(pd.DataFrame(pick_rows), use_container_width=True, hide_index=True, height=min(len(pick_rows)*36+46, 420))
        st.caption("These picks get +15% EV boost in the Opportunity Engine when narrative conviction > 45%.")

    # Narrative-to-Regime bridge
    st.markdown("---")
    sh("🔗 NARRATIVE → REGIME BRIDGE")
    bridge_rows=[]
    for n in active[:4]:
        regime_fit="HIGH" if n["category"] in ["policy","inflation"] and quad in ["Q3","Q2"] else                    ("MED" if n["category"] in ["em","technology"] else "LOW")
        bridge_rows.append({
            "Narrative":n["name"][:35],
            "Category":n["category"],
            "Stage":n["stage"],
            "Regime Fit":regime_fit,
            "Action":"Scale in" if n["stage"]=="front-run" and regime_fit=="HIGH" else ("Watch" if regime_fit!="LOW" else "Ignore"),
        })
    if bridge_rows:
        st.dataframe(pd.DataFrame(bridge_rows), use_container_width=True, hide_index=True)

    # How it works
    with st.expander("How Narrative Bottleneck Engine works", expanded=False):
        st.markdown("""
**Methodology (Citrini / Jukan / Zephyr / Serenity inspired):**

1. **Trigger Detection** — Scan macro features (policy score, oil, VIX, breadth, etc.) against predefined trigger ranges.
2. **Confirmation** — Check secondary signals to reduce false positives.
3. **Ticker Mapping** — Each narrative maps to affected tickers across ALL markets (US, IHSG, FX, Commodities, Crypto).
4. **Front-run Scoring** — Narratives marked `front_run=True` get higher priority when conviction > 45%.
5. **EV Boost** — Front-run picks receive +15% EV boost in the Opportunity Engine, making them appear higher in the execution board.
6. **Regime Bridge** — Narratives are cross-checked against current Hedgeye quad for regime-fit validation.

**Current narratives monitored:**
- Warsh Liquidity Injection / Most Hated Rally
- TACO Ch.2 De-escalation Relief
- Sticky Stagflation / Supply Bottleneck
- AI Compute / Semiconductor Bottleneck
- Indonesia MSCI / EM Rebalancing
- Credit / Duration Bottleneck
- Small Cap Crowded Trade Unwind
        """)


def page_opportunities(snap:Dict)->None:
    """Refactored one-fold decision board: action first, detail second."""
    # ── Narrative bottleneck overlay (v11) ────────────────────────────────────
    render_narrative_bottlenecks(snap)
    # ────────────────────────────────────────────────────────────────────────────
    opps=snap.get("opportunities",[])
    q=snap["q"]; quad=q["quad"]; conf=q["confidence"]
    family=snap.get("family","reflation"); f=snap["f"]; rot=snap["rotation"]
    rot_meta=ROTATION_FAMILIES.get(family,ROTATION_FAMILIES["reflation"])
    prices=snap["prices"]
    most_hated=snap.get("most_hated_rally",{})

    longs=[r for r in opps if "LONG" in r.get("Bias","")]
    shorts=[r for r in opps if "SHORT" in r.get("Bias","")]
    watchs=[r for r in opps if str(r.get("Bias","")).startswith("WATCH")]
    clear_count=int(most_hated.get("clear_count",0) or 0)
    boosted_longs=[r for r in longs if r.get("Rally Fit")=="Boosted"]
    squeezed_shorts=[r for r in shorts if r.get("Rally Fit")=="Squeezed"]

    c1,c2,c3,c4=st.columns(4)
    with c1: mc("Rally State",most_hated.get("stage","monitor"),f"{clear_count}/4 checklist","good" if clear_count>=3 else ("warn" if clear_count>=2 else "bad"))
    with c2: mc("Action",most_hated.get("action","Selective")[:24],most_hated.get("posture",""),"good" if clear_count>=3 else ("warn" if clear_count>=2 else "bad"))
    with c3: mc("Exec Mode",snap["crash"]["exec_mode"],f"score {snap['crash']['exec_score']:.0%}","good" if snap["crash"]["exec_score"]>=0.60 else "warn")
    with c4: mc("Board",f"{len(longs)}L / {len(shorts)}S / {len(watchs)}W",f"{quad} · {conf:.0%} conf","good" if len(longs)>=len(shorts) else "warn")

    if most_hated:
        render_most_hated_rally_monitor(most_hated,compact=True)
        if clear_count>=4:
            st.success("Rally branch live. Fokus: long leaders + boosted risk-on. Short hanya yang benar-benar bersih dan tidak rawan squeeze.")
        elif clear_count>=3:
            st.warning("Pre-confirmed. Scale in bertahap ke risk-on names, tapi jangan over-size sebelum 4/4 clear.")
        elif clear_count>=2:
            st.info("Transisi. Watchlist risk-on naik, tapi board utama tetap selective.")
        else:
            st.error("Belum aktif. Default mode: selective / defensive.")

    drivers=snap.get("top_drivers",[])
    render_top_drivers_now(drivers, title="🧠 TOP DRIVERS NOW — peluang ini bergerak karena apa")

    depth=st.radio("Board depth",["Top 5","Top 8","Top 12","All"],horizontal=True,key="opp_depth_onefold")
    top_n=len(opps) if depth=="All" else int(depth.split()[1])
    long_view=longs[:top_n]
    short_view=shorts[:top_n]

    sh("🎯 EXECUTION BOARD — lihat ini dulu")
    a,b=st.columns(2)
    with a:
        st.markdown(f"**▲ Top longs ({len(long_view)})**")
        if long_view:
            st.dataframe(_opp_view_df(long_view,detail=False),use_container_width=True,hide_index=True,height=min(max(220,len(long_view)*35+46),420))
        else:
            st.info("Belum ada long yang qualified.")
    with b:
        st.markdown(f"**▼ Top shorts ({len(short_view)})**")
        if short_view:
            st.dataframe(_opp_view_df(short_view,detail=False),use_container_width=True,hide_index=True,height=min(max(220,len(short_view)*35+46),420))
        else:
            st.info("Belum ada short yang qualified.")

    if watchs:
        sh("👀 WATCHLIST — selective / belum launch")
        st.dataframe(_opp_view_df(watchs[:top_n],detail=False),use_container_width=True,hide_index=True,height=min(max(180,len(watchs[:top_n])*35+46),360))

    f1,f2=st.columns(2)
    with f1:
        sh("⚡ BOOSTED / PRIORITY LONGS")
        st.markdown(_opp_card_html(boosted_longs[:5] or longs[:5],"Belum ada boosted long yang bersih.","#3dbb6c","⚡"),unsafe_allow_html=True)
    with f2:
        sh("⚠ SHORTS AT RISK OF SQUEEZE")
        st.markdown(_opp_card_html(squeezed_shorts[:5] or shorts[:5],"Belum ada short yang rawan squeeze.","#e5a020","⚠"),unsafe_allow_html=True)

    with st.expander("Secondary context — forward radar, causal map, translation, full detail", expanded=False):
        tab_a,tab_b,tab_c=st.tabs(["🔭 Radar","🔄 Route / Translation","🧾 Full Detail"])
        with tab_a:
            fwd=snap.get("forward_radar",[])
            if fwd:
                st.caption("Setup yang sudah dipantau tapi belum trigger.")
                fwd_rows=[{"Ticker":r.get("ticker_display",r.get("ticker","")),"Side":r.get("side",""),"Status":r.get("status",""),"Trigger":r.get("trigger",""),"Why Not Yet":r.get("why_not_yet",""),"1M":r.get("momentum_1m","—"),"Signal":r.get("signal_quality","")} for r in fwd]
                st.dataframe(pd.DataFrame(fwd_rows),use_container_width=True,hide_index=True,height=min(len(fwd_rows)*36+46,360))
            else:
                st.info("Belum ada forward radar yang menonjol.")

        with tab_b:
            sh(f"ROTATIONAL FLOW MAP — {rot_meta['name'].upper()}")
            st.markdown('<div style="font-size:12px;opacity:.75;margin-bottom:8px">'+rot_meta["desc"]+'</div>',unsafe_allow_html=True)
            render_rotational_flow_map(q,rot,f,family)
            be=rot_meta.get("best_expressions",{})
            if be:
                st.markdown("---")
                be_cols=st.columns(len(be))
                for col,(market,tickers) in zip(be_cols,be.items()):
                    with col:
                        st.markdown(f"**{market}**")
                        for t in tickers[:4]:
                            s=prices.get(t,pd.Series()); r1=ret_n(s,21)
                            perf=pct(r1) if math.isfinite(r1) else ""
                            cls="good" if(math.isfinite(r1) and r1>0) else("bad" if(math.isfinite(r1) and r1<-0.01) else "")
                            st.markdown('<span class="'+cls+'" style="font-size:12px">'+disp(t)+' '+perf+'</span><br>',unsafe_allow_html=True)
            at=snap.get("asset_translation",{})
            if at:
                st.markdown("---")
                sh("ASSET TRANSLATION")
                at_cols=st.columns(len(at))
                for col,(mkt,setups) in zip(at_cols,at.items()):
                    with col:
                        st.markdown(f"**{mkt}**")
                        for setup in setups[:3]:
                            bias=setup.get("bias","")
                            bc="good" if "LONG" in bias else ("bad" if "AVOID" in bias or "SHORT" in bias else "warn")
                            st.markdown('<div style="border-left:2px solid currentColor;padding:3px 6px;margin:3px 0;font-size:11px" class="'+bc+'"><b>'+bias+'</b><br>'+setup.get("setup","")[:40]+'<br><span style="opacity:.55;font-size:9px">✗ '+setup.get("invalidator","")[:35]+'</span></div>',unsafe_allow_html=True)

        with tab_c:
            ld, sd = st.columns(2)
            with ld:
                st.markdown(f"**▲ Long full detail ({len(long_view)})**")
                if long_view:
                    st.dataframe(_opp_view_df(long_view,detail=True),use_container_width=True,hide_index=True,height=min(max(260,len(long_view)*36+46),520))
                else:
                    st.info("Tidak ada long opportunity yang qualified untuk regime ini.")
            with sd:
                st.markdown(f"**▼ Short full detail ({len(short_view)})**")
                if short_view:
                    st.dataframe(_opp_view_df(short_view,detail=True),use_container_width=True,hide_index=True,height=min(max(260,len(short_view)*36+46),520))
                else:
                    st.info("Tidak ada short opportunity yang qualified untuk regime ini.")

            st.markdown("---")
            sh(f"REGIME POLICY MATRIX — {quad}")
            policy=QUAD_POLICY.get(quad,{})
            pol_cols=st.columns(5)
            for col,(market,pol) in zip(pol_cols,policy.items()):
                with col:
                    st.markdown(f"**{market.upper()}**")
                    st.markdown("🟢 **LONG:**")
                    for x in pol.get("long",[])[:3]:
                        st.markdown(f'<span style="font-size:11px;color:#3dbb6c">• {x}</span>',unsafe_allow_html=True)
                    st.markdown("🔴 **SHORT:**")
                    for x in pol.get("short",[])[:3]:
                        st.markdown(f'<span style="font-size:11px;color:#e05252">• {x}</span>',unsafe_allow_html=True)
                    st.markdown("⚫ **AVOID:**")
                    for x in pol.get("avoid",[])[:2]:
                        st.markdown(f'<span style="font-size:11px;opacity:.5">• {x}</span>',unsafe_allow_html=True)


def page_radar(snap:Dict)->None:
    q=snap["q"]; f=snap["f"]; rot=snap["rotation"]; analog=snap["analog"]
    s_quad=q["quad"]; m_quad=q["monthly_quad"]; meta=QUAD_META.get(s_quad,QUAD_META["Q4"])
    ps=f.get("_proxy_share",1.0); fl=int(f.get("_fred_loaded",0)); ft=int(f.get("_fred_total",0))
    mode=f.get("data_source_mode","Hybrid")
    src_q=f.get("macro_source_quality",0.0)
    if ps>0.60:
        st.markdown(f'<div class="proxy-b">⚠️ <strong>{mode}</strong> — FRED {fl}/{ft} series. Macro source quality {src_q:.0%}. Quad masih jalan, tapi lebih banyak ditopang fallback proxy/market-implied data.</div>',unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="real-b">&#10003; <strong>{mode}</strong> — FRED {fl}/{ft} series. Data coverage: {f.get("data_coverage",0):.0%} · Macro source quality {src_q:.0%}</div>',unsafe_allow_html=True)
    div=q["divergence"]; cb=q["conf_band"]; meta_col=meta["text"]
    # Build regime hero as string concat (avoids f-string HTML rendering bug with nested quotes)
    div_badge = ""
    if div == "divergent":
        div_badge = " &nbsp;&#8596;&nbsp; " + qb(m_quad) + ' <span style="opacity:.4;font-size:12px">Monthly</span>'
    hero = (
        '<div style="text-align:center;padding:18px 16px">' +
        '<div style="margin-bottom:6px">' + qb(s_quad) + ' <span style="opacity:.4;font-size:12px">Structural</span>' + div_badge + '</div>' +
        '<div style="font-family:Syne,sans-serif;font-size:28px;font-weight:800;letter-spacing:-.03em;color:' + meta_col + ';margin-bottom:2px">' + meta["label"] + '</div>' +
        '<div style="font-size:12px;opacity:.5;margin-bottom:4px">' + cb + " " + q["operating"] + " &middot; Conf " + f'{q["confidence"]:.0%}' + " &middot; Deepness " + f'{q["deepness"]:.0%}' + '</div>' +
        '<div style="font-size:13px;opacity:.75;max-width:480px;margin:0 auto;line-height:1.7">' + meta["desc"] + '</div></div>'
    )
    st.markdown(hero, unsafe_allow_html=True)
    if div == "divergent":
        st.info(f"🔄 **Divergensi aktif:** Structural {s_quad} vs Monthly {m_quad}. Tren besar masih {s_quad}, bulan ini bergerak seperti {m_quad}. Monthly = trigger, Structural = arah besar.")
    # Regime maturity badges
    dm=q.get("duration_mat",0)
    maturity = "Early" if dm<0.35 else ("Mid-Cycle" if dm<0.60 else "Late / Mature")
    mat_html = ('<div style="display:flex;gap:8px;justify-content:center;margin:6px 0;flex-wrap:wrap;font-size:11px">' +
        '<span style="background:rgba(255,255,255,0.06);padding:2px 10px;border-radius:10px">Maturity: <b>' + maturity + '</b></span>' +
        '<span style="background:rgba(255,255,255,0.06);padding:2px 10px;border-radius:10px">Deepness: <b>' + f'{q.get("deepness",0):.0%}' + '</b></span>' +
        '<span style="background:rgba(255,255,255,0.06);padding:2px 10px;border-radius:10px">Flip hazard: <b>' + f'{q.get("flip_hazard",0):.0%}' + '</b></span></div>'
    )
    st.markdown(mat_html, unsafe_allow_html=True)
    # Route State Banner (v33 named route state - more actionable than Q1-Q4)
    route_snap=snap.get("route",{}); rm=route_snap.get("primary_meta",{}); alt_m=route_snap.get("alt_meta",{})
    rc=rm.get("color","#888")
    route_html=(
        '<div style="display:flex;gap:8px;margin-bottom:10px;align-items:stretch">'+
        '<div style="flex:2;border:1.5px solid '+rc+';border-radius:10px;padding:10px 14px;background:'+rc+'12">'+
        '<div style="font-size:9px;font-weight:700;letter-spacing:.1em;color:'+rc+';text-transform:uppercase;margin-bottom:3px">ROUTE STATE AKTIF</div>'+
        '<div style="font-size:18px;font-weight:700;color:var(--color-text-primary)">'+rm.get("emoji","")+" "+rm.get("label","?")+'</div>'+
        '<div style="font-size:11px;color:var(--color-text-secondary);margin-top:3px">'+rm.get("desc","")[:90]+'</div>'+
        '<div style="margin-top:5px;font-size:10px"><b style="color:'+rc+'">Best:</b> '+", ".join(rm.get("long",[])[:2])+' &nbsp;|&nbsp; <b style="color:#e05252">Avoid:</b> '+", ".join(rm.get("avoid",[])[:2])+'</div>'+
        '</div>'+
        '<div style="flex:1;border:1px solid rgba(255,255,255,0.12);border-radius:10px;padding:10px 12px">'+
        '<div style="font-size:9px;font-weight:700;letter-spacing:.08em;opacity:.4;text-transform:uppercase;margin-bottom:3px">ALT ROUTE (jika primary fails)</div>'+
        '<div style="font-size:14px;font-weight:600">'+alt_m.get("emoji","")+" "+alt_m.get("label","?")+'</div>'+
        '<div style="font-size:10px;opacity:.55;margin-top:3px">'+alt_m.get("desc","")[:50]+'</div></div>'+
        '</div>'
    )
    st.markdown(route_html, unsafe_allow_html=True)
    # News Catalyst Overlay
    news_snap=snap.get("news_overlay",{})
    if news_snap:
        nc={"bad":"#e05252","warn":"#e5a020","good":"#3dbb6c","neu":"rgba(255,255,255,0.3)"}.get(news_snap.get("cls","neu"),"#888")
        st.markdown(
            '<div style="padding:6px 12px;border-radius:8px;border:1px solid '+nc+'44;background:'+nc+'10;font-size:11px;margin-bottom:8px">'+
            '<b style="color:'+nc+'">'+news_snap.get("label","")+'</b> &nbsp;—&nbsp; '+news_snap.get("desc","")[:70]+
            ' &nbsp;|&nbsp; war/oil: '+f'{news_snap.get("war_oil",0):.0%}'+
            ' | policy: '+f'{news_snap.get("policy_pressure",0):.0%}'+
            ' | relief: '+f'{news_snap.get("relief",0):.0%}'+"</div>",
            unsafe_allow_html=True
        )
    # Master Rotation Graph (v33 YOU ARE HERE mind-map)
    render_master_rotation_graph(q,f,snap["rotation"],snap["family"])
    # Flow State Strip (horizontal pill chain)
    render_flow_state_strip(q)
    render_top_drivers_now(snap.get("top_drivers",[]))
    st.markdown("---")
    c1,c2,c3,c4=st.columns(4)
    with c1:
        g_acc=q.get("growth_acc"); mc("Growth Rate-of-Change",acc_txt(g_acc),"vs 3 bulan lalu","good" if g_acc else "bad")
    with c2:
        i_acc=q.get("infl_acc"); mc("Inflasi Rate-of-Change",acc_txt(i_acc),"vs 3 bulan lalu","bad" if i_acc else "good")
    with c3:
        vix=f.get("vix_last",0); vb="Investable (<19)" if vix<19 else("Chop (19-29)" if vix<29 else "Defensive (>29)")
        mc("VIX",f"{vix:.1f}" if math.isfinite(vix) else "—",vb,"good" if vix<19 else("bad" if vix>28 else "warn"))
    with c4:
        sp=f.get("spread_2s10s",float("nan")); yc=f.get("yield_curve_state","Unknown")
        mc("Yield Curve 2s10s",f"{sp:+.2f}%" if math.isfinite(sp) else "—",yc,"good" if("Normal" in yc or"Steep" in yc) else("bad" if"Inverted" in yc else "warn"))
    st.markdown("---")
    ca,cb2=st.columns([1,1])
    with ca:
        sh("📊 REGIME PROBABILITY")
        probs=q.get("probs",{}); m_probs=q.get("monthly_probs",{})
        for qk in ["Q1","Q2","Q3","Q4"]:
            p=probs.get(qk,0.0); pm=m_probs.get(qk,0.0); act="●" if qk==s_quad else("◉" if qk==m_quad else "○")
            fc="#3dbb6c" if qk==s_quad else("#e5a020" if qk==m_quad else "rgba(255,255,255,0.15)")
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px"><span style="font-family:DM Mono,monospace;font-size:11px;width:34px;color:{fc}">{act} {qk}</span><div style="flex:1;background:rgba(255,255,255,0.07);border-radius:3px;height:6px;overflow:hidden"><div style="width:{p*100:.0f}%;background:{fc};height:100%"></div></div><span style="font-family:DM Mono,monospace;font-size:11px;width:34px;text-align:right">{p:.0%}</span><span style="font-family:DM Mono,monospace;font-size:10px;opacity:.35;width:28px;text-align:right">{pm:.0%}M</span></div>',unsafe_allow_html=True)
        flag="⚠️ Transisi tinggi" if q.get("flip_hazard",0)>0.50 else "Stabil"
        st.caption(f"Flip hazard: **{q.get('flip_hazard',0):.0%}** — {flag} · Duration maturity: {q.get('duration_mat',0):.0%} · Next: **{q.get('next_quad','?')}**")
    with cb2:
        sh(f"🎯 TRADE TERBAIK SEKARANG ({s_quad})")
        top_ben=rot["top_ben"]; top_safe=rot["top_safe"]
        best_m=rot["best_meta"]; safe_m=rot["safe_meta"]
        st.markdown(f"""<div class="rot-card rot-best">
        <div style="font-size:10px;opacity:.5;font-weight:700;letter-spacing:.08em">BEST LONG / BENEFICIARY</div>
        <div style="font-size:17px;font-weight:700;font-family:Syne,sans-serif;margin:2px 0">{top_ben}</div>
        <div style="font-size:11px;opacity:.75">{best_m['why']}</div>
        <div style="font-size:10px;opacity:.45;margin-top:3px">✓ {best_m['confirm']}</div>
        <div style="font-size:10px;opacity:.45">✗ {best_m['invalidate']}</div></div>""",unsafe_allow_html=True)
        st.markdown(f"""<div class="rot-card rot-safe">
        <div style="font-size:10px;opacity:.5;font-weight:700;letter-spacing:.08em">SAFE HARBOR / HEDGE</div>
        <div style="font-size:17px;font-weight:700;font-family:Syne,sans-serif;margin:2px 0">{top_safe}</div>
        <div style="font-size:11px;opacity:.75">{safe_m['why']}</div>
        <div style="font-size:10px;opacity:.45;margin-top:3px">✓ {safe_m['confirm']}</div></div>""",unsafe_allow_html=True)
        st.markdown("**Hindari:** "+"&nbsp;".join(tag(a,"r") for a in meta["avoid"]),unsafe_allow_html=True)
    # Historical Analog
    st.markdown("---")
    sh(f"🕰️ ANALOG HISTORIS — {analog.get('label','Unknown')}")
    a=analog
    ac,ab,ac2=st.columns(3)
    with ac: mc("1 Bulan ke Depan",a.get("path_1m","—"))
    with ab: mc("3 Bulan ke Depan",a.get("path_3m","—"))
    with ac2: mc("6 Bulan ke Depan",a.get("path_6m","—"))
    st.info(f"**Next bias:** {a.get('next_bias','')} | Similarity: {a.get('similarity',0):.0%}")
    impacts=a.get("impacts",{}); st.markdown("&nbsp;&nbsp;".join(f"<b>{k.upper()}:</b> {v}" for k,v in impacts.items()),unsafe_allow_html=True)
    # Next macro events
    st.markdown("---")
    sh("📅 NEXT MACRO CATALYSTS")
    for ev in UPCOMING_EVENTS[:4]:
        fam_col={"inflation":"bad","labor":"warn","growth":"warn","policy":"bad"}.get(ev["family"],"neu")
        st.markdown(f"""<div class="mc" style="border-left:3px solid rgba(255,255,255,0.15)">
        <div style="display:flex;justify-content:space-between"><b style="font-size:13px">{ev['title']}</b>
        <span style="font-family:DM Mono,monospace;font-size:11px;opacity:.5">{ev['countdown']} ({ev['when']})</span></div>
        <div style="font-size:12px;opacity:.75;margin-top:3px">{ev['impact']}</div></div>""",unsafe_allow_html=True)
    # Key indicators
    st.markdown("---"); sh("🔑 INDIKATOR KUNCI (plain text — no HTML)")
    rows=[("── GROWTH ──","",""),("Industrial Production YoY",pct(f.get("indpro_yoy",float("nan"))),acc_txt(f.get("indpro_acc"))),
        ("Nonfarm Payrolls YoY",pct(f.get("payrolls_yoy",float("nan"))),acc_txt(f.get("payrolls_acc"))),
        ("Retail Sales YoY",pct(f.get("retail_yoy",float("nan"))),acc_txt(f.get("retail_acc") if "retail_acc" in f else None)),
        ("ISM Manufacturing",num(f.get("ism_last",float("nan")),1),""),
        ("LEI 3M",pct(f.get("lei_3m",float("nan"))),acc_txt(f.get("lei_acc"))),
        ("Copper/Gold 3M ★",pct(f.get("copper_gold_ratio_3m",float("nan"))),""),
        ("Unemployment Rate",f"{f.get('unrate',float('nan')):.1f}%" if math.isfinite(f.get("unrate",float("nan"))) else "—",f"3M Δ: {f.get('unrate_3m_delta',0):+.2f}" if math.isfinite(f.get("unrate_3m_delta",float("nan"))) else ""),
        ("── INFLASI ──","",""),("CPI YoY",pct(f.get("cpi_yoy",float("nan"))),acc_txt(f.get("cpi_acc"))),
        ("Core PCE YoY ★",pct(f.get("corepce_yoy",float("nan"))),acc_txt(f.get("corepce_acc"))),
        ("5Y Breakeven",num(f.get("breakeven",float("nan")),2),""),
        ("Headline-Core Gap ★",pct(f.get("headline_core_gap",float("nan"))),"+ve = supply-driven inflation"),
        ("Monthly Inflation Shock ★",f"{f.get('m_shock',0):.3f}","Bulan ini: seberapa cepat inflasi naik"),
        ("── RATES / POLICY ──","",""),
        ("Fed Funds Rate",num(f.get("policy_rate",float("nan")),2),f"3M Δ: {f.get('policy_rate_3m',0):+.2f}" if math.isfinite(f.get("policy_rate_3m",float("nan"))) else ""),
        ("Policy Score ★",f"{f.get('policy_score',0):+.3f}","+ = dovish/cutting, - = hawkish/hiking"),
        ("Liquidity Score ★",f"{f.get('liq_score',0):+.3f}","DXY + TLT derived"),
        ("2s10s Yield Curve ★",f"{f.get('spread_2s10s',float('nan')):+.2f}%" if math.isfinite(f.get("spread_2s10s",float("nan"))) else "—",f.get("yield_curve_state","")),
        ("── CREDIT & VOL ──","",""),
        ("HY OAS",f"{f.get('hy_oas',float('nan')):.0f}bps" if math.isfinite(f.get("hy_oas",float("nan"))) else "—",f"1M Δ: {f.get('hy_oas_1m',0):+.0f}bps" if math.isfinite(f.get("hy_oas_1m",float("nan"))) else ""),
        ("IG OAS ★",f"{f.get('ig_oas',float('nan')):.0f}bps" if math.isfinite(f.get("ig_oas",float("nan"))) else "—",f"1M Δ: {f.get('ig_oas_1m',0):+.0f}bps" if math.isfinite(f.get("ig_oas_1m",float("nan"))) else ""),
        ("VIX / Term Structure ★",num(f.get("vix_last",float("nan")),1),f.get("vix_term_state","")),
        ("── QUAD INTERNALS ★ ──","",""),
        ("Growth Core (Structural)",f"{q.get('g_level',0):+.3f}","+ = tumbuh, - = melambat"),
        ("Inflation Core (Structural)",f"{q.get('i_level',0):+.3f}","+ = naik, - = turun"),
        ("Slowdown Flags",f"{q.get('slowdown_flags',0):.0%}","% dari 4 indikator slowdown aktif"),
        ("Data Coverage",f"{f.get('data_coverage',0):.0%}","Kualitas data input quad")]
    st.dataframe(pd.DataFrame(rows,columns=["Indikator","Nilai","Catatan"]),use_container_width=True,hide_index=True,height=540)

def page_ihsg(snap:Dict)->None:
    ih=snap["ihsg"]; q=snap["q"]; f=snap["f"]; prices=snap["prices"]; most_hated=snap.get("most_hated_rally",{})
    sh("🇮🇩 IHSG — INDONESIAN MARKET ANALYSIS")
    if most_hated:
        render_ihsg_rally_note(most_hated,ih)
    score=ih["ihsg_score"]; sc="#3dbb6c" if score>=0.60 else("#e5a020" if score>=0.47 else "#e05252")
    st.markdown(f'<div style="text-align:center;padding:16px;border-radius:12px;border:1.5px solid {sc}33;margin-bottom:12px"><div style="font-size:10px;letter-spacing:.1em;text-transform:uppercase;opacity:.4;margin-bottom:3px">IHSG COMPOSITE SCORE (v33 formula)</div><div style="font-family:Syne,sans-serif;font-size:40px;font-weight:800;color:{sc};line-height:1">{score:.0%}</div><div style="font-size:15px;font-weight:700;color:{sc};margin-top:3px">{ih["exec_mode"]}</div></div>',unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    with c1:
        jk=ih["jkse_1m"]; cls="good" if(math.isfinite(jk) and jk>0) else("bad" if(math.isfinite(jk) and jk<-0.02) else "warn")
        mc("^JKSE 1M",pct(jk),f"3M: {pct(ih['jkse_3m'])}",cls)
    with c2:
        idr=ih["usd_idr_1m"]; cls="bad" if(math.isfinite(idr) and idr>0.02) else("good" if(math.isfinite(idr) and idr<-0.01) else "warn")
        mc("USD/IDR 1M",pct(idr),"Naik = IDR lemah = buruk",cls)
    with c3: mc("Asing Flow",ih["flow_state"],f"Score: {ih['foreign_flow']:.0%}","good" if ih["foreign_flow"]>0.60 else("bad" if ih["foreign_flow"]<0.40 else "warn"))
    with c4: mc("BI Policy Proxy",ih["bi_state"],f"Score: {ih['bi_path']:.0%}","good" if ih["bi_path"]>0.60 else("warn" if ih["bi_path"]>0.42 else "bad"))
    st.markdown("---"); ca,cb=st.columns(2)
    with ca:
        sh("📊 FAKTOR UTAMA (bobot v33)")
        gb(f"Regime score ({IHSG_W['regime']:.0%} weight)",ih["em_regime"],"EM macro support")
        gb(f"Asing flow ({IHSG_W['em_rotation']:.0%} weight)",ih["foreign_flow"],"Dana masuk/keluar")
        gb(f"USD/IDR pressure ({IHSG_W['macro_native']:.0%} weight)",1-ih["usd_idr_pressure"],"Lebih tinggi = IDR lebih kuat")
        gb(f"Breadth + bank ({IHSG_W['breadth_flow']:.0%} weight)",clamp(0.55*ih["breadth_ihsg"]+0.45*ih["bank_health"]),"Sektoral health")
        gb(f"Commodity spill ({IHSG_W['execution']:.0%} weight)",ih["comm_spill"],"Batubara + logam")
    with cb:
        sh("🏗️ SPILLOVER CHAIN IHSG")
        top_s=ih["top_sector"]; spill=ih["spill_ihsg"]
        st.markdown(f"**Leader saat ini:** {top_s}")
        for i,fam in enumerate(spill):
            roles=["Leader awal","Beneficiary kedua","Breadth follower","Defensif / shelter"]
            role=roles[i] if i<len(roles) else ""
            col_cls="good" if i==0 else("warn" if i==1 else("neu" if i==2 else "bad"))
            syms_in_fam=IHSG_BUCKETS.get(fam,[])[:3]
            syms_str=" / ".join(t.replace(".JK","") for t in syms_in_fam)
            st.markdown(f'<div style="display:flex;gap:8px;margin-bottom:4px"><span style="font-size:11px;opacity:.4;width:24px">{i+1}.</span><div><span class="{col_cls}" style="font-weight:600;font-size:12px">{fam}</span><br><span style="font-size:10px;opacity:.5">{role} · {syms_str}</span></div></div>',unsafe_allow_html=True)
        mc("Petrodollar Impact",ih["petro_impact"],f"Oil 3M: {pct(nf(f.get('clf_3m',f.get('oil_3m',0.0))))}","warn" if "benefit" in ih["petro_impact"].lower() else "neu")
        mc("IHSG vs SPY",ih["rel_state"])
    st.markdown("---"); sh("📈 IHSG STOCK RANKINGS (1M momentum)")
    if ih["stock_rows"]:
        df=pd.DataFrame([{k:v for k,v in r.items() if not k.startswith("_")} for r in ih["stock_rows"]])
        st.dataframe(df,use_container_width=True,hide_index=True,height=400)
    else: st.info("Saham IHSG belum tersedia. Cek koneksi internet.")

def page_health(snap:Dict)->None:
    h=snap["h"]; f=snap["f"]; prices=snap["prices"]; most_hated=snap.get("most_hated_rally",{})
    sh("📡 HEALTH — ONE-SCREEN DECISION BOARD")

    c1,c2,c3,c4=st.columns(4)
    def mcard3(label,s,sub,states):
        cls="good" if s==states[0] else("bad" if s==states[-1] else "warn")
        mc(label,s,sub,cls)
    with c1: mcard3("Trade Environment","Supportive" if h["trade_state"]=="supportive" else("Hostile" if h["trade_state"]=="hostile" else "Balanced"),"breadth+credit+USD",("Supportive","Balanced","Hostile"))
    with c2: mcard3("Overall Weather",h["weather_state"],"composite 35/35/30",("Risk-On","Mixed","Risk-Off"))
    with c3:
        stage=most_hated.get("stage","monitor") if most_hated else "Monitor"
        cls="good" if most_hated.get("clear_count",0)>=3 else ("warn" if most_hated.get("clear_count",0)>=2 else "bad")
        mc("Rally State",stage,f"{most_hated.get('clear_count',0)}/4 checklist",cls)
    with c4:
        action=most_hated.get("action","Tetap selective") if most_hated else "Tetap selective"
        posture=most_hated.get("posture","") if most_hated else ""
        cls="good" if most_hated.get("clear_count",0)>=3 else ("warn" if most_hated.get("clear_count",0)>=2 else "bad")
        mc("Action Now",action[:24],posture,cls)

    if most_hated:
        render_most_hated_rally_monitor(most_hated,compact=False)
        cc=int(most_hated.get("clear_count",0) or 0)
        if cc>=4:
            st.success("4/4 clear — rally branch aktif. Mode: tactical risk-on. Long beta/EM/crypto boleh dinaikkan, tapi tetap ingat ini liquidity rally yang rapuh.")
        elif cc>=3:
            st.warning("3/4 clear — nyaris aktif. Risk-on boleh dinaikkan bertahap, tapi masih perlu disiplin invalidator dan sizing.")
        elif cc>=2:
            st.info("2/4 clear — transisi. Watchlist risk-on naik, tapi belum full confirm.")
        else:
            st.error("0–1/4 clear — branch most hated rally belum hidup. Fokus defense / selective execution.")

    tape_tab, sector_tab, extra_tab = st.tabs(["⚡ Core Tape","📦 Sector Leadership","🧾 Extra Checklists"])

    with tape_tab:
        ca,cb=st.columns(2)
        with ca:
            sh(f"📊 BREADTH (trade={TACT_TRADE_W['breadth']:.0%} weight)")
            gb("Sektor di atas 50-DMA",h["sec_support"],note=f"({h['sec_above50']}/11)")
            gb("SPY trend health",h["spy_trend"])
            gb("Small cap (IWM)",h["iwm_trend"])
            gb("Equal-weight vs cap-weight",clamp(0.5+h.get("eqw_vs_cw",0)*5),note=pct(h.get("eqw_vs_cw",0))+" 3M diff")
            gb("Narrow leadership (inverse)",1-h.get("narrow_leadership",0.5),"low narrow = sehat")
            gb("Breadth composite",h["breadth"])
        with cb:
            sh("⚡ CREDIT & VOL")
            hy=f.get("hy_oas",float("nan")); ig=f.get("ig_oas",float("nan")); vix=f.get("vix_last",20.0)
            gb("HY Credit health",clamp(1.0-(hy-250)/500) if math.isfinite(hy) else 0.5,note=f"{hy:.0f}bps" if math.isfinite(hy) else "proxy")
            gb("IG Credit health",clamp(1.0-(ig-50)/200) if math.isfinite(ig) else 0.5,note=f"{ig:.0f}bps" if math.isfinite(ig) else "n/a")
            gb("VIX health",clamp(1.0-(vix-13)/25),note=f"VIX {vix:.1f}")
            vr=f.get("vix_vxv_ratio",float("nan"))
            gb("VIX term structure",clamp(1.0-(vr-0.85)/0.25) if math.isfinite(vr) else 0.5,note=f.get("vix_term_state",""))
            gb("Credit+Vol composite",h["tail"])

        sh("📈 YIELD CURVE")
        sp=f.get("spread_2s10s",float("nan")); sp30=f.get("spread_10s30s",float("nan")); sp3m=f.get("spread_2s10s_3m",float("nan"))
        y1,y2,y3=st.columns(3)
        with y1: mc("2s10s Spread",f"{sp:+.2f}%" if math.isfinite(sp) else "—",f.get("yield_curve_state",""),"good" if(math.isfinite(sp) and sp>0.5) else("bad" if(math.isfinite(sp) and sp<0) else "warn"))
        with y2: mc("10s30s Spread",f"{sp30:+.2f}%" if math.isfinite(sp30) else "—")
        with y3: mc("2s10s 3M Δ",f"{sp3m:+.2f}%" if math.isfinite(sp3m) else "—","Uninverting = risiko resesi berjalan" if f.get("yield_curve_uninverting") else "", "warn" if f.get("yield_curve_uninverting") else "neu")

    with sector_tab:
        sh("📦 SECTOR LEADERSHIP — lihat ini setelah trigger")
        SECS={"XLE":"Energy","XLF":"Financials","XLI":"Industrials","XLB":"Materials","XLK":"Technology","XLV":"Healthcare","XLY":"Cons.Disc.","XLP":"Cons.Staples","XLU":"Utilities","XLRE":"Real Estate","XLC":"Comm.Svc."}
        spy3=ret_n(prices.get("SPY",pd.Series()),63); rows=[]
        for t,name in SECS.items():
            s=prices.get(t,pd.Series()); r3=ret_n(s,63); r1=ret_n(s,21)
            rel=(r3-spy3) if(math.isfinite(r3) and math.isfinite(spy3)) else float("nan")
            rows.append({"Sektor":name,"3M":pct(r3),"1M":pct(r1),"vs SPY 3M":pct(rel),"50DMA":"✓" if ts(s)>=0.5 else "✗","_rel":rel if math.isfinite(rel) else -999})
        top=sorted(rows,key=lambda r:r["_rel"],reverse=True)[:5]
        bot=sorted(rows,key=lambda r:r["_rel"])[:4]
        sa,sb=st.columns(2)
        with sa:
            st.markdown("**Leaders sekarang**")
            st.dataframe(pd.DataFrame([{k:v for k,v in r.items() if not k.startswith("_")} for r in top]),use_container_width=True,hide_index=True,height=250)
        with sb:
            st.markdown("**Laggards / perlu hati-hati**")
            st.dataframe(pd.DataFrame([{k:v for k,v in r.items() if not k.startswith("_")} for r in bot]),use_container_width=True,hide_index=True,height=250)
        with st.expander("Lihat full sector table", expanded=False):
            full=sorted(rows,key=lambda r:r["_rel"],reverse=True)
            st.dataframe(pd.DataFrame([{k:v for k,v in r.items() if not k.startswith("_")} for r in full]),use_container_width=True,hide_index=True,height=380)

    with extra_tab:
        chk=snap.get("checklists",{})
        asset_chk=snap.get("asset_checklists",{})
        if chk.get("global"):
            render_checklist(chk["global"],"✅ KONDISI GLOBAL — CHECKLIST TRADING")
            st.caption("Checklist ini sekunder. Hero trigger utama tetap 4 Ricky signals di atas.")
        if asset_chk.get("us"):
            st.markdown("---")
            render_checklist(asset_chk["us"],"🇺🇸 US EQUITY CHECKLIST")
        if asset_chk.get("fx"):
            st.markdown("---")
            render_checklist(asset_chk["fx"],"💱 FX CHECKLIST")


def page_playbook(snap:Dict)->None:
    q=snap["q"]; rot=snap["rotation"]; sc=snap["scenarios"]; pb=snap["playbooks"]; prices=snap["prices"]; most_hated=snap.get("most_hated_rally",{})
    s_quad=q["quad"]; meta=QUAD_META.get(s_quad,QUAD_META["Q4"])
    # Asset Translation Engine (v33 — per market LONG/WATCH/AVOID in plain language)
    at=snap.get("asset_translation",{}); route=snap.get("route",{})
    route_label=route.get("primary_meta",{}).get("label","?")
    route_primary=route.get("primary","growth_scare")
    sh(f"🎯 ASSET TRANSLATION — {route_label.upper()} ({s_quad})")
    st.caption("Tabel ini menjawab: per market, mana yang LONG, mana WATCH, mana AVOID. Dari v33 Asset Translation Engine.")
    if at:
        at_cols=st.columns(len(at))
        for col,(mkt,setups) in zip(at_cols,at.items()):
            with col:
                st.markdown(f"**{mkt}**")
                for setup in setups[:3]:
                    bias=setup.get("bias","")
                    bc="good" if "LONG" in bias else("bad" if "AVOID" in bias or "SHORT" in bias else "warn")
                    st.markdown('<div style="border-left:2px solid currentColor;padding:3px 6px;margin:3px 0;font-size:11px" class="'+bc+'">'+
                        '<b>'+bias+'</b><br>'+setup.get("setup","")[:40]+'<br>'+
                        '<span style="opacity:.55;font-size:9px">✗ '+setup.get("invalidator","")[:35]+"</span></div>",
                        unsafe_allow_html=True)
    st.markdown("---")
    if most_hated:
        render_most_hated_rally_monitor(most_hated,compact=True)
        st.caption("Mini-trigger ini ngikat narrative Warsh/TACO ke playbook risk-on vs wait mode.")
        st.markdown("---")
    sh(f"🎯 FULL PLAYBOOK — {q['operating'].upper()}")
    st.markdown("**BENEFICIARY (long / beli):**")
    for row in rot["ben_rows"]:
        rm=ROUTE_META.get(row["route"],{})
        st.markdown(f"""<div class="rot-card rot-best"><b>{row['route']}</b> <span style="font-size:11px;opacity:.4">score {row['score']:.0%}</span><br>
        <span style="font-size:12px">{rm.get('why','')}</span><br>
        <span style="font-size:10px;opacity:.45">✓ {rm.get('confirm','')} &nbsp; ✗ {rm.get('invalidate','')}</span></div>""",unsafe_allow_html=True)
    st.markdown("**SAFE HARBOR (hedge):**")
    for row in rot["safe_rows"]:
        rm=ROUTE_META.get(row["route"],{})
        st.markdown(f"""<div class="rot-card rot-safe"><b>{row['route']}</b> <span style="font-size:11px;opacity:.4">score {row['score']:.0%}</span><br>
        <span style="font-size:12px">{rm.get('why','')}</span></div>""",unsafe_allow_html=True)
    st.markdown("**Hindari:** "+"&nbsp;".join(tag(a,"r") for a in meta["avoid"]),unsafe_allow_html=True)
    # US Family spillover
    st.markdown("---"); sh("🏗️ US FAMILY SPILLOVER CHAIN")
    spill=rot["spill_us"]; top_us=rot["top_us_bucket"]
    st.markdown(f"**Leader saat ini:** {top_us}")
    for i,fam in enumerate(spill):
        roles=["Leader awal","Spillover kedua","Breadth follower","Hedge / shelter"]
        role=roles[i] if i<len(roles) else ""
        syms=list(US_BUCKETS.get(fam,[]))[:3]; syms_str=" / ".join(syms)
        col_cls="good" if i==0 else("warn" if i==1 else("neu" if i==2 else "bad"))
        st.markdown(f'<div style="display:flex;gap:8px;margin-bottom:4px"><span style="font-size:11px;opacity:.4;width:20px">{i+1}.</span><div><span class="{col_cls}" style="font-weight:600;font-size:13px">{fam}</span><br><span style="font-size:10px;opacity:.5">{role} · {syms_str}</span></div></div>',unsafe_allow_html=True)
    # EM rotation
    st.markdown("---"); sh("🌏 EM ROTATION SIGNAL")
    em_col="good" if rot["em_score"]>0.60 else("bad" if rot["em_score"]<0.45 else "warn")
    mc("EM / IHSG Rotation","Accumulate" if rot["em_score"]>0.60 else("Wait" if rot["em_score"]>0.45 else "Avoid"),f"Score: {rot['em_score']:.0%}",em_col)
    petro=rot.get("petro_score",0.0)
    if petro>0.45: st.warning(f"⚡ **Petrodollar branch active** ({petro:.0%}). Oil shock sedang mendistorsi EM rotation. Coal exporters (ADRO, PTBA) bisa outperform bahkan dalam Q3.")
    # Policy playbooks
    st.markdown("---"); sh("📋 POLICY PLAYBOOKS (v33 engine)")
    pb_sorted=sorted(pb,key=lambda x:x["hypothesis"],reverse=True)
    for p in pb_sorted:
        c=p["hypothesis"]
        pc="#3dbb6c" if c<0.35 else("#e5a020" if c<0.55 else "#e05252")
        st.markdown(f"""<div class="mc" style="border-left:3px solid {pc}55">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <b style="font-size:13px">{p['name']}</b>
        <span style="font-family:DM Mono,monospace;font-size:12px;color:{pc}">Hypo: {p['hypothesis']:.0%} · Evid: {p['evidence']:.0%}</span></div>
        <div style="font-size:12px;opacity:.8;margin-bottom:6px">{p['desc']}</div>
        <div style="font-size:10px;opacity:.5">✗ Invalidasi: {" · ".join(p['invalidators'][:2])}</div></div>""",unsafe_allow_html=True)
    # Scenario Lab
    st.markdown("---"); sh("🔬 SCENARIO LAB — FULL CONTEXT-AWARE (v33 engine)")
    st.markdown(f"*Operating regime: {q['operating']} · Divergence: {q['divergence']} · Shock: {q.get('inf_shock',0):.2f}*")
    for name,case in list(sc.items())[:8]:
        p=case["probability"]; col="#3dbb6c" if p<0.15 else("#e5a020" if p<0.30 else "#e05252")
        st.markdown(f"""<div class="mc" style="border-left:3px solid {col}44">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <b style="font-size:12px">{name}</b><span style="font-family:DM Mono,monospace;color:{col};font-size:12px">{p:.0%}</span></div>
        <div style="display:flex;gap:16px;flex-wrap:wrap;font-size:11px;margin-top:3px">
        <div><b>✓ Winners:</b> {", ".join(case['winners'][:2])}</div>
        <div><b>✗ Losers:</b> {", ".join(case['losers'][:2])}</div></div>
        <div style="font-size:10px;opacity:.45;margin-top:3px">Invalidasi: {" · ".join(case['invalidators'][:2])}</div></div>""",unsafe_allow_html=True)
    # Cross-asset heatmap
    st.markdown("---"); sh("🌐 CROSS-ASSET RETURNS HEATMAP")
    ASSETS={"US Equity (SPY)":"SPY","Growth (QQQ)":"QQQ","Small Cap (IWM)":"IWM","Long Bond (TLT)":"TLT","Credit (HYG)":"HYG","Gold (GLD)":"GLD","Oil (CL=F)":"CL=F","Copper (HG=F)":"HG=F","USD (UUP)":"UUP","EM (EEM)":"EEM","IHSG (^JKSE)":"^JKSE","BTC":"BTC-USD","ETH":"ETH-USD"}
    heat=[]
    for name,t in ASSETS.items():
        s=prices.get(t,pd.Series())
        heat.append({"Asset":name,"1W":pct(ret_n(s,5)),"1M":pct(ret_n(s,21)),"3M":pct(ret_n(s,63)),"6M":pct(ret_n(s,126)),"1Y":pct(ret_n(s,252))})
    st.dataframe(pd.DataFrame(heat),use_container_width=True,hide_index=True,height=460)

def page_risk(snap:Dict)->None:
    cr=snap["crash"]; f=snap["f"]; q=snap["q"]
    sc=cr["crash_score"]; ro=cr["risk_off"]; col="#e05252" if sc>=0.65 else("#e5a020" if sc>=0.42 else "#3dbb6c")
    ro_col="#e05252" if ro>=0.65 else("#e5a020" if ro>=0.42 else "#3dbb6c")
    crash_html = (
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px">' +
        '<div style="text-align:center;padding:18px;border-radius:12px;border:1.5px solid ' + col + '33">' +
        '<div style="font-size:10px;letter-spacing:.1em;text-transform:uppercase;opacity:.4;margin-bottom:4px">CRASH METER (tail/cascade)</div>' +
        '<div style="font-family:Syne,sans-serif;font-size:44px;font-weight:800;color:' + col + ';line-height:1">' + f'{sc:.0%}' + '</div>' +
        '<div style="font-size:14px;font-weight:600;color:' + col + ';margin-top:3px">' + cr["state"] + '</div></div>' +
        '<div style="text-align:center;padding:18px;border-radius:12px;border:1.5px solid ' + ro_col + '33">' +
        '<div style="font-size:10px;letter-spacing:.1em;text-transform:uppercase;opacity:.4;margin-bottom:4px">RISK-OFF METER (broad defensive)</div>' +
        '<div style="font-family:Syne,sans-serif;font-size:44px;font-weight:800;color:' + ro_col + ';line-height:1">' + f'{ro:.0%}' + '</div>' +
        '<div style="font-size:14px;font-weight:600;color:' + ro_col + ';margin-top:3px">Div: ' + cr["div_state"] + '</div></div></div>'
    )
    st.markdown(crash_html, unsafe_allow_html=True)
    st.info("> **Crash vs Risk-Off:** Crash meter = tail/cascade risk (sudden unwind). Risk-Off meter = broad defensive deterioration. 'tail_heavier' = sudden crash risk lebih besar dari broad tape. 'broad_defensive' = tape luas defensive tapi belum ada panic.")
    r1,r2,r3=st.columns(3)
    def rm(label,v,sub):
        cls="bad" if v>=0.60 else("warn" if v>=0.35 else "good")
        mc(label,f"{v:.0%}",sub,cls)
    with r1: rm("Vol Stress",cr["vol_stress"],"VIX-based")
    with r2: rm("Credit Stress",cr["credit_stress"],"HY + IG OAS")
    with r3: rm("Breadth Damage",cr["breadth_dmg"],"market internals")
    mc("Execution Bridge Score ★",cr["exec_mode"],f"Score: {cr['exec_score']:.0%} (v33 exact weights)")
    if cr["reasons"]:
        st.markdown("---"); sh("⚠️ RISK-OFF FLAGS")
        for r in cr["reasons"]: st.markdown(f"- {r}")
    if cr["crash_reasons"]:
        sh("💥 CRASH-SPECIFIC FLAGS")
        for r in cr["crash_reasons"]: st.markdown(f"- {r}")
    st.markdown("---"); sh("📉 VIX REGIME ★")
    vix=f.get("vix_last",20.0); vr=f.get("vix_vxv_ratio",float("nan"))
    v1,v2,v3=st.columns(3)
    with v1: mc("VIX Bucket","Investable (<19)" if vix<19 else("Chop (19-29)" if vix<29 else "Defensive (>29)"),f"VIX = {vix:.1f}","good" if vix<19 else("warn" if vix<29 else "bad"))
    with v2: mc("VIX/VXV Ratio ★",f"{vr:.3f}" if math.isfinite(vr) else "—",f.get("vix_term_state",""),"good" if(math.isfinite(vr) and vr<0.90) else("bad" if(math.isfinite(vr) and vr>=1.0) else "warn"))
    with v3:
        rm_mode="Normal" if vix<19 else("Reduced" if vix<29 else "Defensive")
        mc("Risk Mode",rm_mode,"sizing guide","good" if rm_mode=="Normal" else("warn" if rm_mode=="Reduced" else "bad"))
    st.markdown("---"); sh("💳 CREDIT SPREAD ★")
    hy=f.get("hy_oas",float("nan")); ig=f.get("ig_oas",float("nan"))
    c1,c2=st.columns(2)
    with c1: mc("HY OAS",f"{hy:.0f}bps" if math.isfinite(hy) else "—",f"1M Δ: {f.get('hy_oas_1m',0):+.0f}bps" if math.isfinite(f.get('hy_oas_1m',float('nan'))) else "","good" if(math.isfinite(hy) and hy<350) else("bad" if(math.isfinite(hy) and hy>500) else "warn")); st.caption("Normal<350 | Watch 350-500 | Stress>500")
    with c2: mc("IG OAS ★",f"{ig:.0f}bps" if math.isfinite(ig) else "—",f"1M Δ: {f.get('ig_oas_1m',0):+.0f}bps" if math.isfinite(f.get('ig_oas_1m',float('nan'))) else "","good" if(math.isfinite(ig) and ig<100) else("bad" if(math.isfinite(ig) and ig>150) else "warn")); st.caption("Normal<100 | Watch 100-150 | Stress>150")
    # Position sizing guide (v33 VIX bucket based)
    st.markdown("---"); sh("📐 POSITION SIZING GUIDE (VIX-based)")
    vix2=f.get("vix_last",20.0)
    if vix2<19:
        sizing="**Full size (100%)** — VIX Investable. Pasar tenang, bisa masuk penuh sesuai conviction."
        sizing_cls="good"
    elif vix2<29:
        sizing="**Reduced size (50-75%)** — VIX Chop. Volatility elevated, kurangi size, prioritas high-conviction setup saja."
        sizing_cls="warn"
    else:
        sizing="**Defensive size (25% max)** — VIX Defensive. Capital preservation mode. Hanya hedge dan cash."
        sizing_cls="bad"
    mc("Rekomendasi Sizing",f"VIX {vix2:.1f}",sizing,sizing_cls)
    exec_score2=cr.get("exec_score",0.5)
    mc("Execution Bridge Score",cr.get("exec_mode","?"),f"Score: {exec_score2:.0%} — {'Masuk dengan sizing normal' if exec_score2>=0.60 else ('Wait reclaim key levels' if exec_score2>=0.45 else 'Defensive only — jangan force entry')}",
       "good" if exec_score2>=0.60 else("warn" if exec_score2>=0.45 else "bad"))
    st.markdown("---"); sh("🔭 FORWARD RISK")
    lei=f.get("lei_3m",float("nan")); cg=f.get("copper_gold_ratio_3m",float("nan")); umi=f.get("umcsent_last",float("nan"))
    st.markdown(f"""
- **Flip hazard:** {q.get('flip_hazard',0):.0%} · Deepness: {q.get('deepness',0):.0%} · Duration maturity: {q.get('duration_mat',0):.0%}
- **Operating:** {q.get('operating','')} · Confidence band: **{q.get('conf_band','')}**
- **Yield curve:** {f.get('yield_curve_state','')} | 3M Δ: {pct(f.get('spread_2s10s_3m',float('nan')))}
- **LEI 3M:** {pct(lei)} {"⚠️ Leading indicator turun" if(math.isfinite(lei) and lei<-0.01) else "✓ LEI holding" if math.isfinite(lei) else "(proxy)"}
- **Copper/Gold 3M:** {pct(cg)} {"→ growth expectations turun" if(math.isfinite(cg) and cg<-0.05) else "→ holding"}
- **Monthly inflation shock:** {f.get('m_shock',0):.3f} {"⚠️ Elevated" if f.get('m_shock',0)>0.15 else "Normal"}
- **Slowdown flags:** {q.get('slowdown_flags',0):.0%} dari 4 aktif
    """)

def page_markets(snap:Dict)->None:
    prices=snap["prices"]; q=snap["q"]
    sh("🌐 MULTI-MARKET OVERVIEW")
    s_quad=q["quad"]; meta=QUAD_META.get(s_quad,QUAD_META["Q4"])
    t1,t2,t3=st.tabs(["💱 FX","🛢️ Commodities","🔐 Crypto"])
    with t1:
        sh("💱 FX RATES")
        FX_NAMES={"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","AUDUSD=X":"AUD/USD","JPY=X":"USD/JPY","CHF=X":"USD/CHF","IDR=X":"USD/IDR","CNH=X":"USD/CNH","SGD=X":"USD/SGD","CAD=X":"USD/CAD"}
        fx_rows=[]
        for t,name in FX_NAMES.items():
            s=prices.get(t,pd.Series()); r1=ret_n(s,21); r3=ret_n(s,63)
            note="IDR: naik = lemah (buruk IHSG)" if t=="IDR=X" else ("JPY: naik = yen lemah = risk-on" if t=="JPY=X" else "")
            fx_rows.append({"Pair":name,"1M":pct(r1),"3M":pct(r3),"Trend":"▲" if ts(s)>=0.5 else "▼","Catatan":note})
        st.dataframe(pd.DataFrame(fx_rows),use_container_width=True,hide_index=True)
        uup_1m=ret_n(prices.get("UUP",pd.Series()),21)
        st.info(f"**Regime {s_quad} dan DXY:** {'USD kuat dalam stagflation — tekanan EM dan IHSG.' if s_quad=='Q3' else ('USD biasanya lemah di Goldilocks — EM dan commodity FX benefit.' if s_quad=='Q1' else 'Monitor USD direction untuk konfirmasi regime.')}")
    with t2:
        sh("🛢️ COMMODITIES")
        COMM_NAMES={"GC=F":"Gold","SI=F":"Silver","PL=F":"Platinum","CL=F":"Oil (WTI)","BZ=F":"Oil (Brent)","NG=F":"Natural Gas","HG=F":"Copper","ZC=F":"Corn","ZW=F":"Wheat","DBC":"Broad Commodities","URA":"Uranium ETF"}
        comm_rows=[]
        for t,name in COMM_NAMES.items():
            s=prices.get(t,pd.Series()); r1=ret_n(s,21); r3=ret_n(s,63)
            comm_rows.append({"Commodity":name,"1M":pct(r1),"3M":pct(r3),"Trend":"▲" if ts(s)>=0.5 else "▼"})
        st.dataframe(pd.DataFrame(comm_rows),use_container_width=True,hide_index=True)
        st.info(f"**Regime {s_quad} dan commodities:** {meta.get('desc','')}")
    with t3:
        sh("🔐 CRYPTO")
        CRYPTO_NAMES={"BTC-USD":"Bitcoin","ETH-USD":"Ethereum","SOL-USD":"Solana","BNB-USD":"BNB","XRP-USD":"XRP","ADA-USD":"Cardano","AVAX-USD":"Avalanche","LINK-USD":"Chainlink","DOGE-USD":"Dogecoin"}
        cr_rows=[]
        for t,name in CRYPTO_NAMES.items():
            s=prices.get(t,pd.Series()); r1=ret_n(s,21); r3=ret_n(s,63); r1w=ret_n(s,5)
            cr_rows.append({"Asset":name,"1W":pct(r1w),"1M":pct(r1),"3M":pct(r3),"BTC Corr":"High"})
        st.dataframe(pd.DataFrame(cr_rows),use_container_width=True,hide_index=True)
        btc_1m=ret_n(prices.get("BTC-USD",pd.Series()),21)
        st.info(f"**Crypto dan regime:** Crypto = high-beta risk asset. Q1 = most bullish. Q3/Q4 = sangat bearish. BTC 1M: {pct(btc_1m)}. Dalam Q3, crypto biasanya underperform bahkan Gold.")

def page_diag(snap:Dict)->None:
    f=snap["f"]; fred=snap["fred"]; prices=snap["prices"]; q=snap["q"]; price_meta=snap.get("price_meta",{})
    # Risk Range table (v33 ATR-based)
    rr=snap.get("risk_ranges",{})
    if rr:
        sh("📐 RISK RANGE ENGINE (ATR-based per aset)")
        rr_rows=[]
        for tk,v in rr.items():
            px=v.get("px",0); tlo=v.get("trade_low",0); thi=v.get("trade_high",0)
            stretch=v.get("stretch","neutral"); trend=v.get("trend","neutral")
            stretch_sym="🔴" if "overbought" in stretch else("🟢" if "oversold" in stretch else("🟡" if "reset" in stretch else "⚪"))
            rr_rows.append({"Ticker":disp(tk),"Price":f"{px:.2f}","Trade Low":f"{tlo:.2f}","Trade High":f"{thi:.2f}","Stretch":stretch_sym+" "+stretch,"Trend":"▲" if trend=="bullish" else("▼" if trend=="bearish" else "—"),"ATR%":f"{v.get('atr_pct',0)*100:.1f}%"})
        st.dataframe(pd.DataFrame(rr_rows),use_container_width=True,hide_index=True,height=360)
        st.caption("🟢 oversold/reset = possible entry | 🔴 overbought = consider trimming | Trade range = ATR-based 1-2 week range")
        st.markdown("---")
    sh("📋 FRED DATA COVERAGE")
    cov=[{"Series":k,"FRED ID":FRED_SERIES.get(k,""),"Points":len(_s(s)),"Latest":str(_s(s).index[-1])[:10] if not _s(s).empty else "—","Last Value":round(float(_s(s).iloc[-1]),4) if not _s(s).empty else None,"Status":"✓ Loaded" if not _s(s).empty else "✗ Missing"} for k,s in fred.items()]
    st.dataframe(pd.DataFrame(cov),use_container_width=True,hide_index=True,height=480)
    ps=f.get("_proxy_share",1.0); fl=int(f.get("_fred_loaded",0)); ft=int(f.get("_fred_total",0))
    if ps>0.50: st.warning(f"**FRED issue ({fl}/{ft} loaded).** Fix: `export FRED_API_KEY=key` (free at fred.stlouisfed.org/api/key/). App jalan di {f.get('data_source_mode','Proxy-Heavy').lower()} mode; gunakan output dengan disiplin ekstra.")
    sh("🧪 SOURCE QUALITY")
    src_rows=[
        ("Data source mode",f.get("data_source_mode","")),
        ("Macro source quality",f"{f.get('macro_source_quality',0):.2f}"),
        ("Observed macro share",f"{f.get('macro_observed_share',0):.2f}"),
        ("Macro proxy share",f"{f.get('macro_proxy_share',0):.2f}"),
        ("Price panel coverage",f"{f.get('price_panel_coverage',0):.2f}"),
        ("Price short-history share",f"{f.get('price_short_history_share',0):.2f}"),
        ("Price stale share",f"{f.get('price_stale_share',0):.2f}"),
        ("Median price history (yrs)",f"{f.get('price_median_years',0):.2f}"),
        ("Regime prior mode",f.get("prior_mode","off")),
    ]
    st.dataframe(pd.DataFrame(src_rows,columns=["Quality Lens","Value"]),use_container_width=True,hide_index=True,height=260)
    core_source_rows=[{"Field":k,"Source":f.get("macro_source_map",{}).get(k,"unknown"),"Detail":f.get("macro_source_detail",{}).get(k,"") or ("FRED observed" if f.get("macro_source_map",{}).get(k)=="observed_fred" else "") ,"Value":f.get(k)} for k in ["indpro_yoy","retail_yoy","payrolls_yoy","unrate_3m_delta","claims_13w_delta","ism_last","housing_yoy","cpi_yoy","core_cpi_yoy","breakeven"]]
    st.dataframe(pd.DataFrame(core_source_rows),use_container_width=True,hide_index=True,height=320)
    sh("🔬 QUAD INTERNALS (v33 weights verifikasi)")
    internal_rows=[
        ("Structural g_level",f"{f.get('g_struct_level',0):+.4f}"),("Structural g_mom",f"{f.get('g_struct_mom',0):+.4f}"),
        ("Structural i_level",f"{f.get('i_struct_level',0):+.4f}"),("Structural i_mom",f"{f.get('i_struct_mom',0):+.4f}"),
        ("Monthly g_level",f"{f.get('g_month_level',0):+.4f}"),("Monthly g_mom",f"{f.get('g_month_mom',0):+.4f}"),
        ("Monthly i_level",f"{f.get('i_month_level',0):+.4f}"),("Monthly i_mom",f"{f.get('i_month_mom',0):+.4f}"),
        ("Policy score",f"{f.get('policy_score',0):+.4f}"),("Liquidity score",f"{f.get('liq_score',0):+.4f}"),
        ("Monthly policy",f"{f.get('m_policy',0):+.4f}"),("Monthly liq",f"{f.get('m_liq',0):+.4f}"),
        ("Monthly shock",f"{f.get('m_shock',0):+.4f}"),("Slowdown flags",f"{f.get('slowdown_flags',0):.2f}"),
        ("Inflation shock",f"{f.get('inf_shock',0):.4f}"),("Data coverage",f"{f.get('data_coverage',0):.2f}"),
        ("Monthly coverage",f"{f.get('monthly_data_coverage',0):.2f}"),("FRED real share",f"{f.get('fred_real_share',0):.2f}"),
        ("Observed macro share",f"{f.get('macro_observed_share',0):.2f}"),("Macro proxy share",f"{f.get('macro_proxy_share',0):.2f}"),
        ("Macro source quality",f"{f.get('macro_source_quality',0):.2f}"),("Prior mode",f.get("prior_mode","off")),
        ("Quad core g_core",f"{q.get('g_core',0):+.4f}"),("Quad core i_core",f"{q.get('i_core',0):+.4f}"),
        ("Structural quad",q.get("quad","")),("Structural conf",f"{q.get('confidence',0):.2f}"),
        ("Monthly quad",q.get("monthly_quad","")),("Monthly conf",f"{q.get('monthly_conf',0):.2f}"),
        ("Flip hazard",f"{q.get('flip_hazard',0):.3f}"),("Deepness",f"{q.get('deepness',0):.3f}"),("Duration maturity",f"{q.get('duration_mat',0):.3f}"),
    ]
    st.dataframe(pd.DataFrame(internal_rows,columns=["Internal Feature","Value"]),use_container_width=True,hide_index=True,height=500)
    build_meta=snap.get("build_meta",{}) or {}
    sh("🛠️ BUILD / FEATURE FLAGS")
    build_rows=[
        ("App version", build_meta.get("app_version","v10.0")),
        ("Price period", build_meta.get("price_period","")),
        ("Regime prior mode", build_meta.get("regime_prior_mode","off")),
        ("Signal enter threshold", f"{float(build_meta.get('signal_enter_threshold',0.0)):.3f}"),
        ("Signal exit threshold", f"{float(build_meta.get('signal_exit_threshold',0.0)):.3f}"),
        ("Signal store", str(build_meta.get("signal_store_path",""))[-60:]),
        ("Markets-integrated signals", "on" if build_meta.get("markets_integrated_signals") else "off"),
        ("Top drivers", "on" if build_meta.get("top_drivers_enabled") else "off"),
        ("Setup quality", "on" if build_meta.get("setup_quality_enabled") else "off"),
    ]
    st.dataframe(pd.DataFrame(build_rows,columns=["Build Lens","Value"]),use_container_width=True,hide_index=True,height=300)
    sh("📦 PRICE DATA COVERAGE")
    pm_summary=[
        ("Expected tickers",price_meta.get("expected",0)),
        ("Loaded tickers",price_meta.get("loaded",0)),
        ("Missing tickers",price_meta.get("missing_count",0)),
        ("Coverage",f"{price_meta.get('coverage',0):.2f}"),
        ("Short-history share",f"{price_meta.get('short_history_share',0):.2f}"),
        ("Median history (yrs)",f"{price_meta.get('median_years',0):.2f}"),
        ("Stale share",f"{price_meta.get('stale_share',0):.2f}"),
    ]
    st.dataframe(pd.DataFrame(pm_summary,columns=["Price Panel Metric","Value"]),use_container_width=True,hide_index=True,height=240)
    prows=[{"Ticker":t,"Points":len(s),"Latest":str(s.index[-1])[:10] if not s.empty else "—","Last Close":round(float(s.iloc[-1]),4) if not s.empty else None} for t,s in sorted(prices.items())]
    st.dataframe(pd.DataFrame(prows),use_container_width=True,hide_index=True,height=400)


def build_strong_weak(prices:Dict[str,pd.Series],quad:str,limit:int=6)->Dict:
    """Rank stocks by 1M momentum, regime-adjusted. Returns strong/weak lists."""
    # Regime multipliers: Q1=growth, Q2=commodity/cyclical, Q3=gold/energy, Q4=defensive
    regime_boost = {
        "Q3": {"ANTM.JK":1.3,"ADRO.JK":1.2,"PTBA.JK":1.2,"GC=F":1.4,"XLE":1.3,"UUP":1.2,"XLP":1.2,"XLU":1.1},
        "Q2": {"XLE":1.3,"HG=F":1.3,"XLB":1.2,"XLF":1.2,"ADRO.JK":1.3,"PTBA.JK":1.3},
        "Q1": {"QQQ":1.2,"NVDA":1.3,"META":1.2,"AAPL":1.1,"BBCA.JK":1.2,"BBRI.JK":1.1},
        "Q4": {"TLT":1.4,"GLD":1.2,"XLP":1.3,"XLU":1.3,"XLV":1.2,"TLKM.JK":1.2,"ICBP.JK":1.2},
    }
    boosts = regime_boost.get(quad,{})
    rows = []
    for tk,s in prices.items():
        r1 = ret_n(s,21)
        if not math.isfinite(r1): continue
        adj = r1 * boosts.get(tk,1.0)
        rows.append({"Ticker":tk,"1M":pct(r1),"Adjusted Score":round(adj,4),"Trend":"▲" if ts(s)>=0.5 else "▼"})
    rows.sort(key=lambda x:x["Adjusted Score"],reverse=True)
    return {"strong":rows[:limit],"weak":rows[-limit:]}

def _signal_view_df(df:pd.DataFrame)->pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out=df.copy()
    out["Days On"]=out["days_on"].astype(int)
    out["Ticker"]=out["ticker_display"]
    out["Signal Date"]=out["signal_start_date"]
    out["Entry Close"]=out["entry_close"].map(lambda x: num(x,2))
    out["Last Close"]=out["last_close"].map(lambda x: num(x,2))
    out["% Since Signal"]=out["pct_since_signal"].map(lambda x: pct(x,1))
    out["Trade"]=out["trade_state"].str.title()
    out["Trend"]=out["trend_state"].str.title()
    out["Score"]=out["signal_score"].map(lambda x: f"{x:+.3f}")
    out["EV+"]=out["opportunity_ev"].map(lambda x: pct(x,0) if math.isfinite(_safe_float(x)) else "—")
    out["Macro"]=out["macro_aligned"].fillna("")
    out["Why Now"]=out["why_now"].fillna("")
    cols=["Days On","Ticker","market","bias","Signal Date","Entry Close","Last Close","% Since Signal","Trade","Trend","Score","EV+","Macro","Why Now"]
    out=out[cols].rename(columns={"market":"Market","bias":"Bias"})
    return out


def _signal_market_summary_cards(sig:Dict, show_header:bool=True)->None:
    market_summary=sig.get("market_summary",{}) or {}
    markets=[("US","🇺🇸"),("IHSG","🇮🇩"),("FX","💱"),("Commodities","🛢️"),("Crypto","🔐")]
    if show_header:
        sh("📈 SIGNAL SNAPSHOT BY MARKET")
    cols=st.columns(len(markets))
    for col,(market,emoji) in zip(cols,markets):
        m=market_summary.get(market,{}) or {}
        active_total=int(m.get("active_total",0))
        added=int(m.get("added_today",0))
        removed=int(m.get("removed_today",0))
        best=str(m.get("best_active","—"))
        tone="good" if active_total>0 and added>=removed else ("warn" if active_total>0 else "neu")
        with col:
            mc(f"{emoji} {market}", str(active_total), f"+{added} / -{removed} · lead: {best}", tone)


def _signal_market_detail(sig:Dict, market:str, key_suffix:str="", compact:bool=False)->None:
    active_df=sig.get("active",pd.DataFrame())
    added_df=sig.get("added",pd.DataFrame())
    removed_df=sig.get("removed",pd.DataFrame())
    remaining_df=sig.get("remaining",pd.DataFrame())
    market_summary=(sig.get("market_summary",{}) or {}).get(market,{}) or {}

    def _flt(df:pd.DataFrame)->pd.DataFrame:
        if isinstance(df,pd.DataFrame) and not df.empty:
            return df[df["market"]==market].copy()
        return pd.DataFrame()

    adf=_flt(active_df)
    addf=_flt(added_df)
    remf=_flt(removed_df)
    keepf=_flt(remaining_df)

    c1,c2,c3,c4=st.columns(4)
    with c1: mc("Active", str(int(market_summary.get("active_total", len(adf)))), f"lead: {market_summary.get('best_active','—')}", "good" if len(adf) else "neu")
    with c2: mc("Added", str(int(market_summary.get("added_today", len(addf)))), f"new: {market_summary.get('best_added','—')}", "good" if len(addf) else "neu")
    with c3: mc("Remaining", str(int(market_summary.get("remaining_total", len(keepf)))), "persisting lifecycle", "warn" if len(keepf) else "neu")
    with c4: mc("Removed", str(int(market_summary.get("removed_today", len(remf)))), f"last out: {market_summary.get('best_removed','—')}", "bad" if len(remf) else "neu")

    view_choice=st.radio(
        f"{market} signal view",
        ["Active","Added","Remaining","Removed"],
        horizontal=True,
        key=f"signal_market_view_{market}_{key_suffix}",
    )
    source_map={"Active":adf,"Added":addf,"Remaining":keepf,"Removed":remf}
    view_df=source_map.get(view_choice,pd.DataFrame())
    if isinstance(view_df,pd.DataFrame) and not view_df.empty:
        height=340 if compact else min(max(260, len(view_df)*35+46), 560)
        st.dataframe(_signal_view_df(view_df), use_container_width=True, hide_index=True, height=height)
    else:
        st.info(f"Belum ada {view_choice.lower()} signals untuk {market}.")


def page_signal_strength(snap:Dict, forced_market:Optional[str]=None, key_suffix:str="global", compact:bool=False, show_header:bool=True)->None:
    sig=snap.get("signal_strength",{}) or {}
    summary=sig.get("summary",{}) or {}
    active_df=sig.get("active",pd.DataFrame())
    added_df=sig.get("added",pd.DataFrame())
    remaining_df=sig.get("remaining",pd.DataFrame())
    removed_df=sig.get("removed",pd.DataFrame())

    if show_header:
        sh("📈 SIGNAL STRENGTH — lifecycle monitor")
        st.caption("Layer ini stateful: Added / Remaining / Removed, Days On, Signal Date, dan return sejak signal aktif. Verified mulai sejak persistence layer ini hidup.")

    c1,c2,c3,c4=st.columns(4)
    with c1: mc("Active Longs",str(summary.get("active_longs",0)),f"as of {sig.get('asof_date','—')}","good")
    with c2: mc("Active Shorts",str(summary.get("active_shorts",0)),"directional downside","warn")
    with c3: mc("Added Today",str(summary.get("added_today",0)),"newly activated","good")
    with c4: mc("Removed Today",str(summary.get("removed_today",0)),"fell out of active set","bad" if summary.get("removed_today",0) else "neu")

    _signal_market_summary_cards(sig, show_header=show_header)

    market_order=["US","IHSG","FX","Commodities","Crypto"]
    available_markets=[]
    for df in (active_df,removed_df):
        if isinstance(df,pd.DataFrame) and not df.empty:
            available_markets.extend(df["market"].dropna().astype(str).tolist())
    available_markets=[m for m in market_order if m in set(available_markets)]

    if forced_market:
        st.caption(f"Filtered untuk market: {forced_market}")
        _signal_market_detail(sig, forced_market, key_suffix=key_suffix, compact=compact)
    else:
        market_choice=st.radio("Market", ["All"]+available_markets, horizontal=True, key=f"signal_market_filter_{key_suffix}")
        if market_choice=="All":
            view_choice=st.radio("View", ["Added","Remaining","Removed","Active All"], horizontal=True, key=f"signal_status_filter_{key_suffix}")
            source_map={"Added":added_df, "Remaining":remaining_df, "Removed":removed_df, "Active All":active_df}
            view_df=source_map.get(view_choice,pd.DataFrame())
            if isinstance(view_df,pd.DataFrame) and not view_df.empty:
                st.dataframe(_signal_view_df(view_df), use_container_width=True, hide_index=True, height=min(max(280, len(view_df)*35+46), 760))
            else:
                st.info("Belum ada signal untuk filter ini. Pada first live day, seluruh signal aktif biasanya masuk Added karena belum ada history hari sebelumnya.")
        else:
            _signal_market_detail(sig, market_choice, key_suffix=key_suffix, compact=compact)

    with st.expander("Signal detail dan caveat", expanded=False):
        st.markdown("""
- **Added** = hari ini aktif, sebelumnya tidak aktif.
- **Remaining** = aktif berlanjut dari snapshot sebelumnya.
- **Removed** = sebelumnya aktif, sekarang gagal memenuhi rule.
- **Days On** dan **% Since Signal** verified sejak engine ini mulai live.
- Ini **bukan** copy exact formula Hedgeye; ini lifecycle layer kausal di atas board opportunity yang sudah ada.
        """)

def page_markets_full(snap:Dict)->None:
    """Markets tab: execution board + signal lifecycle + market-specific views."""
    prices=snap["prices"]; q=snap["q"]; f=snap["f"]; ih=snap["ihsg"]; rot=snap["rotation"]
    s_quad=q["quad"]; meta=QUAD_META.get(s_quad,QUAD_META["Q4"])

    sig=snap.get("signal_strength",{}) or {}
    _signal_market_summary_cards(sig, show_header=True)
    st.caption("Markets sekarang fokus ke action per market. Opportunities dan signal overview dipadatkan di atas, supaya tidak dobel dengan tab market.")
    with st.expander("📊 Execution overview", expanded=False):
        page_opportunities(snap)
    with st.expander("📈 Signal lifecycle overview", expanded=False):
        page_signal_strength(snap, key_suffix="markets", show_header=False)

    t2,t3,t4,t5,t6=st.tabs(["🇮🇩 IHSG","🇺🇸 US Stocks","💱 FX","🛢️ Komoditas","🔐 Crypto"])

    # ── IHSG ─────────────────────────────────────────────────────────────────
    with t2:
        sh("🇮🇩 IHSG — INDONESIAN MARKET ANALYSIS")
        if snap.get("most_hated_rally"):
            render_ihsg_rally_note(snap.get("most_hated_rally",{}),ih)
        score=ih["ihsg_score"]; sc="#3dbb6c" if score>=0.60 else("#e5a020" if score>=0.47 else "#e05252")
        st.markdown(f'<div style="text-align:center;padding:14px;border-radius:12px;border:1.5px solid {sc}33;margin-bottom:12px"><div style="font-size:10px;letter-spacing:.1em;text-transform:uppercase;opacity:.4;margin-bottom:2px">IHSG COMPOSITE SCORE</div><div style="font-family:Syne,sans-serif;font-size:38px;font-weight:800;color:{sc};line-height:1">{score:.0%}</div><div style="font-size:14px;font-weight:700;color:{sc};margin-top:2px">{ih["exec_mode"]}</div></div>',unsafe_allow_html=True)
        c1,c2,c3,c4=st.columns(4)
        with c1:
            jk=ih["jkse_1m"]; cls="good" if(math.isfinite(jk) and jk>0) else("bad" if(math.isfinite(jk) and jk<-0.02) else "warn")
            mc("^JKSE 1M",pct(jk),f"3M: {pct(ih['jkse_3m'])}",cls)
        with c2:
            idr=ih["usd_idr_1m"]; cls="bad" if(math.isfinite(idr) and idr>0.02) else("good" if(math.isfinite(idr) and idr<-0.01) else "warn")
            mc("USD/IDR 1M",pct(idr),"Naik = IDR lemah = buruk",cls)
        with c3: mc("Asing Flow",ih["flow_state"],f"Score: {ih['foreign_flow']:.0%}","good" if ih["foreign_flow"]>0.60 else("bad" if ih["foreign_flow"]<0.40 else "warn"))
        with c4: mc("BI Policy Proxy",ih["bi_state"],f"Score: {ih['bi_path']:.0%}","good" if ih["bi_path"]>0.60 else("warn" if ih["bi_path"]>0.42 else "bad"))
        st.markdown("---")
        ca,cb=st.columns(2)
        with ca:
            sh("📊 FAKTOR UTAMA (bobot v33)")
            gb(f"Regime score ({IHSG_W['regime']:.0%})",ih["em_regime"],"EM macro support")
            gb(f"Asing flow ({IHSG_W['em_rotation']:.0%})",ih["foreign_flow"],"Dana masuk/keluar")
            gb(f"USD/IDR pressure ({IHSG_W['macro_native']:.0%})",1-ih["usd_idr_pressure"],"Lebih tinggi = IDR kuat")
            gb(f"Breadth+bank ({IHSG_W['breadth_flow']:.0%})",clamp(0.55*ih["breadth_ihsg"]+0.45*ih["bank_health"]),"Sektoral health")
            gb(f"Commodity spill ({IHSG_W['execution']:.0%})",ih["comm_spill"],"Batubara+logam")
        with cb:
            sh("🏗️ SPILLOVER CHAIN IHSG")
            top_s=ih["top_sector"]; spill=ih["spill_ihsg"]
            st.markdown(f"**Leader saat ini:** {top_s}")
            for i,fam in enumerate(spill):
                roles=["Leader awal","Beneficiary ke-2","Breadth follower","Defensif / shelter"]
                role=roles[i] if i<len(roles) else ""
                col_cls="good" if i==0 else("warn" if i==1 else("neu" if i==2 else "bad"))
                syms_str=" / ".join(t.replace(".JK","") for t in IHSG_BUCKETS.get(fam,[])[:3])
                st.markdown(f'<div style="display:flex;gap:8px;margin-bottom:4px"><span style="font-size:11px;opacity:.4;width:20px">{i+1}.</span><div><span class="{col_cls}" style="font-weight:600;font-size:12px">{fam}</span><br><span style="font-size:10px;opacity:.5">{role} · {syms_str}</span></div></div>',unsafe_allow_html=True)
            quad_impact={"Q1":"✅ Goldilocks = IHSG kondusif. Asing beli, bank outperform.","Q2":"⚡ Reflation = coal/logam/CPO outperform. Watch tail jika Fed overtighten.","Q3":"⚠️ Stagflasi = IHSG tertekan. USD kuat, asing keluar. Hanya coal exporter bisa bertahan.","Q4":"🔴 Resesi = IHSG defensif. Hold cash, ICBP/KLBF/TLKM."}
            st.info(quad_impact.get(s_quad,""))
        st.markdown("---"); sh("📈 IHSG STOCK RANKINGS (1M momentum)")
        if ih["stock_rows"]:
            df=pd.DataFrame([{k:v for k,v in r.items() if not k.startswith("_")} for r in ih["stock_rows"]])
            st.dataframe(df,use_container_width=True,hide_index=True,height=380)
        # Key pairs
        st.markdown("---"); sh("📚 KEY IHSG PAIRS TO WATCH")
        for t,desc,regime in [("BBCA.JK","Bank terbesar, kualitas premium. Leading IHSG di Q1/Q2.","Q1,Q2"),("ADRO.JK","Coal king. Rally di Q2/Q3 (commodity shock).","Q2,Q3"),("ANTM.JK","Gold/nickel proxy. Cocok di Q3 stagflasi.","Q3"),("TLKM.JK","Defensif. Dividend play, cocok Q4.","Q4"),("IDR=X","USD/IDR: naik = buruk (asing kabur dari IHSG).","All"),]:
            s=prices.get(t,pd.Series()); r1=ret_n(s,21); perf=pct(r1) if math.isfinite(r1) else "—"
            cls="good" if(math.isfinite(r1) and r1>0) else("bad" if(math.isfinite(r1) and r1<-0.01) else "warn")
            st.markdown('<div class="mc" style="display:flex;justify-content:space-between;align-items:center"><div><div class="lb">'+t+' — '+' '.join(tag(r,"b") for r in regime.split(","))+'</div><div style="font-size:12px;opacity:.8">'+desc+'</div></div><div class="vl '+cls+'" style="font-size:16px">'+perf+'</div></div>',unsafe_allow_html=True)
        st.markdown("---")
        sh("📈 SIGNAL LIFECYCLE — IHSG")
        page_signal_strength(snap, forced_market="IHSG", key_suffix="ihsg", compact=True, show_header=False)

        # IHSG Checklist (v33 style)
        st.markdown("---")
        chk=snap.get("checklists",{})
        if chk.get("ihsg"):
            render_checklist(chk["ihsg"],"🇮🇩 IHSG CHECKLIST — KONDISI MASUK")
            st.caption("v33 checklist: ✓ = kondisi oke | ~ = mixed/watch | ✗ = kondisi buruk")
        # Macro impact board for IHSG
        st.markdown("---")
        sh("📊 MACRO IMPACT PADA IHSG — SEKARANG vs NEXT")
        q2=snap["q"]; s_quad2=q2["quad"]
        macro_impact_ihsg={
            "Q1":{"sekarang":"Growth global naik + inflasi turun = kondisi ideal. Asing masuk EM. IHSG bisa ikut naik terutama bank dan consumer.","best_path":"BBCA/BBRI lead, consumer cyclical ikut, foreign flow positif.","invalidator":"USD strengthens kembali atau yields spike.","next":"Jika Q1 bertahan: IHSG rally lebar. Jika Q2: rotate ke coal/commodity."},
            "Q2":{"sekarang":"Commodity rally = IHSG coal exporters kuat. Tapi USD bisa menguat, menekan IDR dan asing.","best_path":"ADRO/PTBA/ITMG lead, ANTM ikut. Banks mixed.","invalidator":"Oil reversal cepat atau Fed tighten lebih agresif dari ekspektasi.","next":"Jika Q2 → Q3: coal still ok tapi bank dan consumer mulai rapuh."},
            "Q3":{"sekarang":"Stagflasi = IHSG mixed-bearish. USD kuat menekan IDR dan asing keluar. Hanya coal exporter bisa bertahan.","best_path":"Defensive pada TLKM/ICBP. Coal exporter: ADRO, PTBA. Kurangi posisi bank dan consumer cyclical.","invalidator":"Fed pivot atau oil breakdown + IDR stabilize.","next":"Jika Q3 berlanjut: cash dan coal. Jika Q4: switch ke defensives penuh."},
            "Q4":{"sekarang":"Resesi / deflasi = IHSG broadly bearish. Asing keluar EM. Hanya defensive quality yang bisa tahan.","best_path":"TLKM (dividend), ICBP, KLBF. Kurangi semua beta tinggi.","invalidator":"Fed cut agresif + fiscal stimulus besar = V-shape recovery di EM.","next":"Early signs of Q1 recovery: bank lead kembali."},
        }
        impact=macro_impact_ihsg.get(s_quad2,{})
        if impact:
            a2,b2=st.columns(2)
            with a2:
                mc("Kondisi Sekarang",s_quad2,impact.get("sekarang",""))
                mc("Best Path Sekarang","→ "+impact.get("best_path",""))
            with b2:
                mc("Invalidator","⚠️ "+impact.get("invalidator",""))
                mc("Next Branch","→ "+impact.get("next",""))

    # ── US Stocks ──────────────────────────────────────────────────────────────
    with t3:
        sh("🇺🇸 US STOCKS")
        # Sector performance
        SECS={"XLE":"Energy","XLF":"Financials","XLI":"Industrials","XLB":"Materials","XLK":"Technology","XLV":"Healthcare","XLY":"Cons.Disc.","XLP":"Cons.Staples","XLU":"Utilities","XLRE":"Real Estate","XLC":"Comm.Svc."}
        spy3=ret_n(prices.get("SPY",pd.Series()),63); sec_rows=[]
        for tk,name in SECS.items():
            s=prices.get(tk,pd.Series()); r3=ret_n(s,63); r1=ret_n(s,21)
            rel=(r3-spy3) if(math.isfinite(r3) and math.isfinite(spy3)) else float("nan")
            sec_rows.append({"Sektor":name,"3M":pct(r3),"1M":pct(r1),"vs SPY 3M":pct(rel),"50DMA":"✓" if ts(s)>=0.5 else "✗"})
        sec_rows.sort(key=lambda r:float(r["vs SPY 3M"].replace("%","").replace("—","0").replace("+","")) if r["vs SPY 3M"]!="—" else -999,reverse=True)
        st.dataframe(pd.DataFrame(sec_rows),use_container_width=True,hide_index=True,height=360)
        # US Family spillover
        st.markdown("---"); sh("🏗️ US FAMILY SPILLOVER CHAIN")
        spill=rot["spill_us"]; top_us=rot["top_us_bucket"]
        st.markdown(f"**Leader saat ini:** {top_us}")
        for i,fam in enumerate(spill):
            roles=["Leader awal","Spillover ke-2","Breadth follower","Hedge / shelter"]
            role=roles[i] if i<len(roles) else ""
            syms_str=" / ".join(list(US_BUCKETS.get(fam,[]))[:3])
            col_cls="good" if i==0 else("warn" if i==1 else("neu" if i==2 else "bad"))
            st.markdown(f'<div style="display:flex;gap:8px;margin-bottom:4px"><span style="font-size:11px;opacity:.4;width:20px">{i+1}.</span><div><span class="{col_cls}" style="font-weight:600;font-size:13px">{fam}</span><br><span style="font-size:10px;opacity:.5">{role} · {syms_str}</span></div></div>',unsafe_allow_html=True)
        # Individual US stocks
        st.markdown("---"); sh("📊 KEY US STOCKS (1M momentum)")
        us_stocks={"AAPL":"Apple","MSFT":"Microsoft","NVDA":"Nvidia","AMZN":"Amazon","META":"Meta","GOOGL":"Alphabet","TSLA":"Tesla","AVGO":"Broadcom","AMD":"AMD","NFLX":"Netflix","JPM":"JPMorgan","BAC":"BofA","GS":"Goldman","XOM":"ExxonMobil","CVX":"Chevron"}
        stock_rows=[]
        for tk,name in us_stocks.items():
            s=prices.get(tk,pd.Series()); r1=ret_n(s,21); r3=ret_n(s,63)
            sp1=ret_n(prices.get("SPY",pd.Series()),21); rel=(r1-sp1) if(math.isfinite(r1) and math.isfinite(sp1)) else float("nan")
            stock_rows.append({"Stock":name,"Ticker":tk,"1M":pct(r1),"3M":pct(r3),"vs SPY 1M":pct(rel),"Trend":"▲" if ts(s)>=0.5 else "▼"})
        stock_rows.sort(key=lambda r:float(r["1M"].replace("%","").replace("—","0").replace("+","")) if r["1M"]!="—" else -999,reverse=True)
        st.dataframe(pd.DataFrame(stock_rows),use_container_width=True,hide_index=True,height=460)
        # Strong / Weak Map (v33 style)
        st.markdown("---"); sh(f"💪 STRONG vs WEAK — US STOCKS (regime-adjusted {s_quad})")
        sw=build_strong_weak(prices,s_quad,limit=5)
        col_s,col_w=st.columns(2)
        with col_s:
            st.markdown("**🟢 STRONG (buy/hold):**")
            for r in sw["strong"]:
                tk=r["Ticker"]
                if any(tk.endswith(x) for x in [".JK","=F","=X","-USD"]): continue  # US stocks only
                st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:12px;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.05)"><span><b>{tk}</b></span><span class="good">{r["1M"]} {r["Trend"]}</span></div>',unsafe_allow_html=True)
        with col_w:
            st.markdown("**🔴 WEAK (avoid/reduce):**")
            for r in sw["weak"]:
                tk=r["Ticker"]
                if any(tk.endswith(x) for x in [".JK","=F","=X","-USD"]): continue
                st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:12px;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.05)"><span><b>{tk}</b></span><span class="bad">{r["1M"]} {r["Trend"]}</span></div>',unsafe_allow_html=True)
        st.caption(f"Regime-adjusted: {s_quad} boosts certain sectors. Data from yfinance 1M returns.")

        st.markdown("---")
        sh("📈 SIGNAL LIFECYCLE — US")
        page_signal_strength(snap, forced_market="US", key_suffix="us", compact=True, show_header=False)

        # Macro Impact Board for US (v33)
        macro_impact=snap.get("macro_impact",{})
        if macro_impact.get("us"):
            st.markdown("---"); sh("📊 MACRO IMPACT BOARD — US")
            bd=macro_impact["us"]
            a3,b3=st.columns(2)
            with a3:
                mc("Sekarang",bd["quad"]+" Regime",bd["now"])
                mc("Best Expression","→",bd["best_expression"])
            with b3:
                mc("Forward Branch","→",bd["forward_branch"])
                mc("Invalidator","⚠️",bd["invalidator"])
            st.markdown("**Drivers:** "+" · ".join(bd.get("drivers",[])),unsafe_allow_html=True)
        # US Asset Checklist
        asset_chk2=snap.get("asset_checklists",{})
        if asset_chk2.get("us"):
            st.markdown("---")
            render_checklist(asset_chk2["us"],"🇺🇸 US EQUITY CHECKLIST")

    # ── FX ─────────────────────────────────────────────────────────────────────
    with t4:
        sh("💱 FX RATES")
        FX_NAMES={"EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","AUDUSD=X":"AUD/USD","JPY=X":"USD/JPY (naik=yen lemah)","CHF=X":"USD/CHF","IDR=X":"USD/IDR (naik=IDR lemah)","CNH=X":"USD/CNH","SGD=X":"USD/SGD","CAD=X":"USD/CAD"}
        fx_rows=[]
        for tk,name in FX_NAMES.items():
            s=prices.get(tk,pd.Series()); r1=ret_n(s,21); r3=ret_n(s,63)
            fx_rows.append({"Pair":name,"1M":pct(r1),"3M":pct(r3),"Trend":"▲" if ts(s)>=0.5 else "▼"})
        st.dataframe(pd.DataFrame(fx_rows),use_container_width=True,hide_index=True)
        uup_1m=ret_n(prices.get("UUP",pd.Series()),21)
        uup_txt=f"UUP (USD proxy): {pct(uup_1m)} 1M. "
        regime_fx={"Q1":"Q1 Goldilocks = USD biasanya lemah. EM dan commodity FX benefit.","Q2":"Q2 Reflation = commodity FX (AUD, CAD) outperform. USD mixed.","Q3":"Q3 Stagflasi = USD kuat. IDR/EM FX tertekan. Dollar king.","Q4":"Q4 Deflasi = USD kuat awalnya, tapi Fed cut → Dollar bisa lemah."}
        st.info(uup_txt + regime_fx.get(s_quad,""))
        st.markdown("---")
        sh("📈 SIGNAL LIFECYCLE — FX")
        page_signal_strength(snap, forced_market="FX", key_suffix="fx", compact=True, show_header=False)

        # FX Strong/Weak + Macro Impact + Checklist
        sw3=snap.get("strong_weak_all",{})
        if sw3.get("fx"):
            sh("💪 FX STRONG vs WEAK (1M momentum)")
            fx_sw=sw3["fx"]; fc1,fc2=st.columns(2)
            with fc1:
                st.markdown("**Strong (▲):**")
                for r in fx_sw["strong"][:4]:
                    cls="good" if r["r1"]>0 else "bad"
                    st.markdown(f'<span class="{cls}" style="font-size:12px">▲ {r["name"]}: {pct(r["r1"])}</span>',unsafe_allow_html=True)
            with fc2:
                st.markdown("**Weak (▼):**")
                for r in fx_sw["weak"][:4]:
                    cls="bad" if r["r1"]<0 else "good"
                    st.markdown(f'<span class="{cls}" style="font-size:12px">▼ {r["name"]}: {pct(r["r1"])}</span>',unsafe_allow_html=True)
        mi3=snap.get("macro_impact",{})
        if mi3.get("fx"):
            bd=mi3["fx"]; sh("📊 MACRO IMPACT — FX")
            mc("Sekarang",bd["quad"],bd["now"]); mc("Best",bd["best_expression"][:40])
        ac3=snap.get("asset_checklists",{})
        if ac3.get("fx"): render_checklist(ac3["fx"],"💱 FX CHECKLIST")

    # ── Komoditas ──────────────────────────────────────────────────────────────
    with t5:
        sh("🛢️ KOMODITAS")
        COMM_NAMES={"GC=F":"Gold (XAU)","SI=F":"Silver","CL=F":"Oil WTI","BZ=F":"Oil Brent","NG=F":"Natural Gas","HG=F":"Copper","ZC=F":"Corn","ZW=F":"Wheat","DBC":"Broad Commodities ETF","URA":"Uranium ETF"}
        comm_rows=[]
        for tk,name in COMM_NAMES.items():
            s=prices.get(tk,pd.Series()); r1=ret_n(s,21); r3=ret_n(s,63)
            comm_rows.append({"Komoditas":name,"1M":pct(r1),"3M":pct(r3),"Trend":"▲" if ts(s)>=0.5 else "▼"})
        st.dataframe(pd.DataFrame(comm_rows),use_container_width=True,hide_index=True)
        regime_comm={"Q1":"Q1 = Gold ok, Oil ok, Copper ok. Commodities broadly supportive.","Q2":"Q2 = Energy king. Oil, Gas, Copper outperform. Materials rally.","Q3":"Q3 Stagflasi = GOLD best trade. Oil bisa volatile. Avoid cyclical metals.","Q4":"Q4 = Commodities broadly weak. Gold bisa rally jika recession fear dominates."}
        st.info(regime_comm.get(s_quad,""))
        oil_3m=ret_n(prices.get("CL=F",pd.Series()),63); gold_3m=ret_n(prices.get("GC=F",pd.Series()),63)
        mc("Oil WTI 3M",pct(oil_3m),"signal inflasi","warn" if(math.isfinite(oil_3m) and oil_3m>0.05) else "neu")
        mc("Gold 3M",pct(gold_3m),"hard asset hedge","good" if(math.isfinite(gold_3m) and gold_3m>0.05) else "neu")
        st.markdown("---")
        sh("📈 SIGNAL LIFECYCLE — KOMODITAS")
        page_signal_strength(snap, forced_market="Commodities", key_suffix="commodities", compact=True, show_header=False)

        # Commodities Strong/Weak + Impact + Checklist
        sw4=snap.get("strong_weak_all",{})
        if sw4.get("commodities"):
            sh("💪 COMMODITIES STRONG vs WEAK")
            cs=sw4["commodities"]; cc1,cc2=st.columns(2)
            with cc1:
                for r in cs["strong"][:4]:
                    st.markdown(f'<span class="good" style="font-size:12px">▲ {r["name"]}: {pct(r["r1"])}</span>',unsafe_allow_html=True)
            with cc2:
                for r in cs["weak"][:4]:
                    st.markdown(f'<span class="bad" style="font-size:12px">▼ {r["name"]}: {pct(r["r1"])}</span>',unsafe_allow_html=True)
        mi4=snap.get("macro_impact",{})
        if mi4.get("commodities"):
            bd=mi4["commodities"]; sh("📊 MACRO IMPACT — COMMODITIES")
            mc("Sekarang",bd["quad"],bd["now"]); mc("Best",bd["best_expression"][:40])
        ac4=snap.get("asset_checklists",{})
        if ac4.get("commodities"): render_checklist(ac4["commodities"],"🛢️ COMMODITIES CHECKLIST")

    # ── Crypto ─────────────────────────────────────────────────────────────────
    with t6:
        sh("🔐 CRYPTO")
        CRYPTO_NAMES={"BTC-USD":"Bitcoin (BTC)","ETH-USD":"Ethereum (ETH)","SOL-USD":"Solana (SOL)","BNB-USD":"BNB","XRP-USD":"XRP","ADA-USD":"Cardano","AVAX-USD":"Avalanche","LINK-USD":"Chainlink","DOGE-USD":"Dogecoin"}
        cr_rows=[]
        for tk,name in CRYPTO_NAMES.items():
            s=prices.get(tk,pd.Series()); r1=ret_n(s,21); r3=ret_n(s,63); r1w=ret_n(s,5)
            cr_rows.append({"Asset":name,"1W":pct(r1w),"1M":pct(r1),"3M":pct(r3),"Trend":"▲" if ts(s)>=0.5 else "▼"})
        st.dataframe(pd.DataFrame(cr_rows),use_container_width=True,hide_index=True)
        btc_1m=ret_n(prices.get("BTC-USD",pd.Series()),21)
        regime_crypto={"Q1":"Q1 = Crypto bullish. High-beta risk asset. BTC biasanya outperform.","Q2":"Q2 = Crypto ok tapi attention ke commodities. BTC masih bisa naik.","Q3":"Q3 Stagflasi = Crypto BEARISH. Bukan hedge inflation. Gold > Crypto.","Q4":"Q4 = Crypto sangat bearish. Capital preservation mode. Cash > Crypto."}
        st.info(f"BTC 1M: {pct(btc_1m)}. {regime_crypto.get(s_quad,'')}")
        st.markdown("---")
        sh("📈 SIGNAL LIFECYCLE — CRYPTO")
        page_signal_strength(snap, forced_market="Crypto", key_suffix="crypto", compact=True, show_header=False)

        sw5=snap.get("strong_weak_all",{})
        if sw5.get("crypto"):
            sh("💪 CRYPTO STRONG vs WEAK")
            crs=sw5["crypto"]; cr1,cr2=st.columns(2)
            with cr1:
                for r in crs["strong"][:4]:
                    st.markdown(f'<span class="good" style="font-size:12px">▲ {r["name"]}: {pct(r["r1"])}</span>',unsafe_allow_html=True)
            with cr2:
                for r in crs["weak"][:4]:
                    st.markdown(f'<span class="bad" style="font-size:12px">▼ {r["name"]}: {pct(r["r1"])}</span>',unsafe_allow_html=True)
        mi5=snap.get("macro_impact",{})
        if mi5.get("crypto"):
            bd=mi5["crypto"]; sh("📊 MACRO IMPACT — CRYPTO")
            mc("Sekarang",bd["quad"],bd["now"]); mc("Best",bd["best_expression"][:40])
        ac5=snap.get("asset_checklists",{})
        if ac5.get("crypto"): render_checklist(ac5["crypto"],"🔐 CRYPTO CHECKLIST")
        st.caption("⚠️ Crypto = high-beta risk asset, bukan inflation hedge.")


def main():
    st.markdown('<div style="display:flex;align-items:center;margin-bottom:4px"><span style="font-family:Syne,sans-serif;font-size:20px;font-weight:800;letter-spacing:-.03em">🧭 MacroRegime Pro</span><span style="font-size:10px;opacity:.3;margin-left:8px;font-family:DM Mono,monospace">v10.0 · Maxed Candidate · Markets-Integrated Signals + Top Drivers + Setup Quality</span></div>',unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("### ⚙️ Controls")
        if st.button("🔄 Force Refresh",use_container_width=True): st.cache_data.clear(); st.rerun()
        st.markdown("---")
        st.markdown("""
**Urutan baca (orang awam):**
1. 🧭 **Radar** — Regime apa? Trade terbaik? Analog historis?
2. 📡 **Health** — Aman masuk? Breadth + credit + checklist
3. 🎯 **Playbook** — Full strategy + scenarios + what-if
4. 🌐 **Markets** → 📊 Opportunities + 📈 Signal Strength + IHSG + US + FX + Komoditas + Crypto
5. ⚠️ **Risk** — Crash meter + sizing guide
6. 🔬 **Diag** — Data quality + quad internals

**v10 feature additions:**
- Signal Strength tetap di Markets
- Top Drivers Now untuk jelasin kenapa tape bergerak sekarang
- Setup Quality + Path + Why Not Yet di opportunity board
- Truth-layer diagnostics: observed vs proxy vs market-implied
- Price panel coverage / short-history / stale-share diagnostics
- Prior mode ditampilkan eksplisit (default off)
- Header/versioning dirapikan agar lebih jujur ke kondisi build
        """)
    snap=load_all()
    most_hated=snap.get("most_hated_rally",{})
    q=snap["q"]; f=snap["f"]; cr=snap["crash"]; quad=q["quad"]; meta=QUAD_META.get(quad,{})
    ga="▲" if q.get("growth_acc") else "▼"; ia="▲" if q.get("infl_acc") else "▼"
    div_badge=f" / M:{q['monthly_quad']}" if q["divergence"]=="divergent" else ""
    route=snap.get("route",{}); news=snap.get("news_overlay",{})
    route_meta=route.get("primary_meta",{}); route_label=route_meta.get("label","?"); route_emoji=route_meta.get("emoji","")
    route_color=route_meta.get("color","#888")
    # Best long/short from opportunities for quick summary
    opps_all=snap.get("opportunities",[])
    best_long=next((o for o in opps_all if "LONG" in o.get("Bias","")),None)
    best_short=next((o for o in opps_all if "SHORT" in o.get("Bias","")),None)
    best_long_tk=best_long["Ticker"] if best_long else "—"
    best_short_tk=best_short["Ticker"] if best_short else "—"
    # Enhanced status bar with route state
    news_label=news.get("label","") if news else ""
    st.markdown(
        '<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:8px 12px;'+
        'border-radius:8px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);'+
        'margin-bottom:10px;font-size:11px">'+
        '<span>'+qb(quad)+div_badge+' <strong>'+meta.get("label","")+"</strong></span>"+
        '<span style="opacity:.2">|</span>'+
        '<span style="color:'+route_color+';font-weight:700">'+route_emoji+' '+route_label+'</span>'+
        '<span style="opacity:.2">|</span>'+
        '<span>Conf: <strong>'+f'{q["confidence"]:.0%}'+' ('+q.get("conf_band","")+")</strong></span>"+
        '<span style="opacity:.2">|</span>'+
        '<span>Growth: <strong>'+ga+'</strong> | Inflasi: <strong>'+ia+'</strong></span>'+
        '<span style="opacity:.2">|</span>'+
        '<span>▲ Best Long: <strong>'+best_long_tk+'</strong></span>'+
        '<span style="opacity:.2">|</span>'+
        '<span>▼ Best Short: <strong>'+best_short_tk+'</strong></span>'+
        '<span style="opacity:.2">|</span>'+
        '<span>Risk: <strong>'+cr["state"]+'</strong> | Exec: <strong>'+cr["exec_mode"]+'</strong></span>'+
        ('<span style="opacity:.2">|</span><span>Rally Trigger: <strong>'+str(most_hated.get("clear_count","—"))+'/4</strong></span>' if most_hated else '')+
        ('<span style="opacity:.2">|</span><span style="opacity:.6">'+news_label+'</span>' if news_label else "")+
        '<span style="opacity:.25;margin-left:auto">'+snap["ts"]+'</span></div>',
        unsafe_allow_html=True
    )
    top_drivers=snap.get("top_drivers",[]) or []
    if top_drivers:
        driver_line=" · ".join([f"{d.get('label','')}: {float(d.get('score',0)):.0%}" for d in top_drivers[:3]])
        st.caption("Top drivers now → "+driver_line)

    # ---- New engines (v11) ----
    try:
        from ui.command_center_page import render_command_center
        _has_cc = True
    except Exception:
        _has_cc = False
    try:
        from ui.components.narrative_discovery_panel import render_narrative_discovery_panel
        _has_narr = True
    except Exception:
        _has_narr = False
    try:
        from ui.components.regime_transition_panel import render_regime_transition_panel
        _has_rt = True
    except Exception:
        _has_rt = False

    # ── v11: 5-tab consolidated architecture ──────────────────────────────────
    try:
        from ui.pages_redesigned import page_regime_intel, page_strategy, page_markets_v2, page_risk_diag
        _has_new_pages = True
    except Exception as _pe:
        _has_new_pages = False

    _tab_labels = ["⚡ Command Center", "📊 Regime Intel", "🧠 Narrative", "🎯 Strategy", "🌐 Markets", "⚠️ Risk & Diag"]
    tabs = st.tabs(_tab_labels)

    with tabs[0]:
        if _has_cc:
            render_command_center(snap)
        else:
            st.warning("Command Center not available.")

    with tabs[1]:
        if _has_new_pages:
            page_regime_intel(snap)
        else:
            page_radar(snap)
            st.markdown("---")
            page_health(snap)

    with tabs[2]:
        page_narrative(snap)

    with tabs[3]:
        if _has_new_pages:
            page_strategy(snap)
        else:
            page_playbook(snap)

    with tabs[4]:
        if _has_new_pages:
            page_markets_v2(snap)
        else:
            page_markets_full(snap)

    with tabs[5]:
        if _has_new_pages:
            page_risk_diag(snap)
        else:
            page_risk(snap)
            st.markdown("---")
            page_diag(snap)

if __name__=="__main__": main()
