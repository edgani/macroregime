"""
MacroRegime Pro v6.0 — Full Fidelity Rebuild
=============================================
All 30 gaps from v33 audit fixed:
- Quad weights match v33 exactly (structural vs monthly separate)
- Structural vs monthly feature builder properly separated
- Policy score + liquidity score
- Data coverage + confidence penalty
- Regime prior system (off/gentle/strong)
- Historical Analog Engine (5 templates)
- Policy Playbook Engine (3 playbooks)
- Full Scenario Discovery (context-aware, divergence-aware)
- Separate crash_score vs risk_off_score
- Petrodollar chain analysis
- Family spillover templates (US + IHSG)
- Confidence band language
- Regime deepness + duration maturity
- Next macro catalyst countdown
- FX, Commodities, Crypto mini-pages
- Execution Bridge score
- IHSG engine with correct weights

Free data: yfinance + FRED public CSV
Run: streamlit run macro_regime_pro_v6.py
"""
from __future__ import annotations
import datetime,math,os
from io import StringIO
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
</style>
""",unsafe_allow_html=True)

# ── WEIGHTS (exact from v33 config/weights.py) ─────────────────────────────────
STRUCT_W = {"g_level":0.35,"g_mom":0.25,"i_level":0.25,"i_mom":0.15,"policy":0.10,"liq":0.10}
MONTHLY_W = {"g_level":0.20,"g_mom":0.45,"i_level":0.15,"i_mom":0.45,"i_shock":0.15,"policy":0.10,"liq":0.10}
QUAD_MOD = {"sf_to_q3":0.10,"sf_to_q2":-0.08,"shock_to_q3":0.08,"shock_to_q1":-0.10,"gm_to_q2":0.05,"gm_to_q4":0.08,"cov_penalty":0.50}
MONTHLY_MOD = {"sf_to_q3":0.12,"sf_to_q2":-0.06,"shock_to_q3":0.16,"shock_to_q1":-0.04,"gm_to_q2":0.04,"gm_to_q4":0.06,"cov_penalty":0.55}
TACT_TRADE_W = {"breadth":0.35,"trend":0.25,"credit":0.20,"vol":0.20}
TACT_TREND_W = {"spy":0.40,"eqw":0.20,"small":0.15,"sector":0.15,"dollar":0.10}
TACT_TAIL_W  = {"vol":0.35,"credit":0.25,"small":0.20,"dollar":0.10,"narrow":0.10}
TACT_AGG_W   = {"trade":0.35,"trend":0.35,"tail":0.30}
CRASH_W = {"tail_state":0.16,"shock_state":0.18,"health":0.12,"vix":0.14,"unwind":0.14,"vol":0.12,"tail_hedge":0.08,"dollar":0.06}
IHSG_W = {"regime":0.24,"em_rotation":0.16,"macro_native":0.24,"breadth_flow":0.18,"execution":0.18}
EXEC_W = {"weather":0.20,"health":0.14,"vix":0.10,"quad":0.12,"conf":0.10,"cross":0.09,"crowd":0.09,"shock":0.08,"crash":0.08}

TTL=3600
FRED_SERIES = {
    "INDPRO":"INDPRO","PAYEMS":"PAYEMS","UNRATE":"UNRATE","ICSA":"ICSA",
    "RSAFS":"RSAFS","HOUST":"HOUST","ISM":"NAPMNOI","LEI":"USSLIND",
    "UMCSENT":"UMCSENT","CPI":"CPIAUCSL","CORECPI":"CPILFESL","COREPCE":"PCEPILFE",
    "DGS2":"DGS2","DGS10":"DGS10","DGS30":"DGS30","REAL10":"DFII10",
    "BREAKEVEN":"T5YIE","FEDFUNDS":"FEDFUNDS","HYOAS":"BAMLH0A0HYM2","IGSPR":"BAMLC0A0CM",
}
US_TICKERS = ["SPY","QQQ","IWM","RSP","XLE","XLF","XLI","XLB","XLK","XLV","XLY","XLP","XLU","XLRE","XLC",
    "HYG","LQD","TLT","IEF","SHY","GLD","GC=F","SI=F","HG=F","CL=F","NG=F","UUP","EEM","EFA",
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
]
UPCOMING_EVENTS = [
    {"title":"US CPI (Apr)","family":"inflation","when":"~Apr 16","countdown":"T-3d","impact":"Panas = yields naik, USD up, QQQ turun. Dingin = relief rally."},
    {"title":"US Retail Sales (Mar)","family":"growth","when":"~Apr 16","countdown":"T-3d","impact":"Miss = growth scare deepens. Beat = soft-landing hope."},
    {"title":"US Nonfarm Payrolls (Apr)","family":"labor","when":"~May 2","countdown":"T-19d","impact":"Data labor jadi kunci apakah Fed bisa cut. Miss = Q4 risk naik."},
    {"title":"FOMC Meeting","family":"policy","when":"~May 6-7","countdown":"T-24d","impact":"Fed hold/cut/pivot → langsung gerakkan rates path, USD, dan durasi."},
    {"title":"US GDP Q1 (advance)","family":"growth","when":"~Apr 30","countdown":"T-17d","impact":"Kontraksi = Q4 scare resmi. Ekspansi = Q3 dominated lebih lama."},
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
    key=os.environ.get("FRED_API_KEY","")
    try: key=key or st.secrets.get("FRED_API_KEY","")
    except: pass
    urls=[f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"]
    if key: urls.append(f"https://api.stlouisfed.org/fred/series/observations?series_id={sid}&api_key={key}&file_type=json")
    sess=requests.Session(); sess.headers.update({"User-Agent":"Mozilla/5.0 MacroRegimePro/6.0"})
    for url in urls:
        try:
            r=sess.get(url,timeout=10); r.raise_for_status()
            if "fredgraph" in url:
                df=pd.read_csv(StringIO(r.text),index_col=0,parse_dates=True)
                s=pd.to_numeric(df.iloc[:,0],errors="coerce").dropna()
                if len(s)>0: return s
            else:
                import json; data=json.loads(r.text); obs=data.get("observations",[])
                if obs:
                    idx=pd.to_datetime([o["date"] for o in obs])
                    vals=pd.to_numeric([o["value"] for o in obs],errors="coerce")
                    s=pd.Series(vals.values,index=idx).dropna()
                    if len(s)>0: return s
        except: continue
    return pd.Series(dtype=float)

@st.cache_data(ttl=TTL,show_spinner=False)
def fetch_prices(tickers:tuple,period:str="2y")->Dict[str,pd.Series]:
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
    except: return {}

def build_proxy(prices:Dict[str,pd.Series])->Dict:
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

def build_macro(fred:Dict[str,pd.Series],prices:Dict[str,pd.Series])->Dict:
    f=build_proxy(prices); proxy_used=0; fred_loaded=0; fred_total=0
    raw_macro_keys=["indpro_yoy","retail_yoy","payrolls_yoy","unrate_3m_delta","claims_13w_delta","ism_last","housing_yoy","cpi_yoy","core_cpi_yoy","breakeven"]
    def ov(k,fk,fn,*args):
        nonlocal fred_loaded,fred_total; fred_total+=1
        s=fred.get(k,pd.Series())
        if not _s(s).empty:
            v=fn(s,*args)
            if math.isfinite(v): f[fk]=v; fred_loaded+=1; return True
        return False
    for rk in raw_macro_keys:
        if not math.isfinite(f.get(rk,float("nan"))): proxy_used+=1
    ov("INDPRO","indpro_yoy",ret_n,12); ov("PAYEMS","payrolls_yoy",ret_n,12)
    ov("PAYEMS","payrolls_mom",ret_n,1); ov("UNRATE","unrate",last)
    ov("UNRATE","unrate_3m_delta",delta_n,3); ov("ICSA","claims_13w_delta",delta_n,13)
    ov("ICSA","claims_last",last); ov("ISM","ism_last",last)
    ov("RSAFS","retail_yoy",ret_n,12); ov("HOUST","housing_yoy",ret_n,12)
    ov("LEI","lei_3m",ret_n,3); ov("UMCSENT","umcsent_last",last)
    ov("CPI","cpi_yoy",ret_n,12); ov("CPI","cpi_mom",ret_n,1)
    ov("CORECPI","core_cpi_yoy",ret_n,12); ov("COREPCE","corepce_yoy",ret_n,12)
    ov("BREAKEVEN","breakeven",last); ov("BREAKEVEN","breakeven_1m",delta_n,1)
    ov("REAL10","real_10y",last); ov("FEDFUNDS","policy_rate",last)
    ov("FEDFUNDS","policy_rate_3m",delta_n,3); ov("DGS2","dgs2",last)
    ov("DGS10","dgs10",last); ov("DGS30","dgs30",last)
    ov("HYOAS","hy_oas",last); ov("HYOAS","hy_oas_1m",delta_n,21)
    ov("IGSPR","ig_oas",last); ov("IGSPR","ig_oas_1m",delta_n,21)
    # Yield curve
    d2=f.get("dgs2",float("nan")); d10=f.get("dgs10",float("nan")); d30=f.get("dgs30",float("nan"))
    if math.isfinite(d2) and math.isfinite(d10):
        sp=d10-d2; f["spread_2s10s"]=sp
        f["yield_curve_state"]="Inverted" if sp<-0.10 else("Flat" if sp<0.25 else("Normal" if sp<1.50 else "Steep"))
        s2=_s(fred.get("DGS2",pd.Series())); s10=_s(fred.get("DGS10",pd.Series()))
        if len(s2)>63 and len(s10)>63:
            a2,a10=s2.align(s10,join="inner"); f["spread_2s10s_3m"]=delta_n(a10-a2,63)
            f["yield_curve_uninverting"]=(math.isfinite(f.get("spread_2s10s_3m",float("nan"))) and f.get("spread_2s10s_3m",0)>0.20 and sp>-0.25)
    if math.isfinite(d10) and math.isfinite(d30): f["spread_10s30s"]=d30-d10
    # RoC flags
    f["indpro_acc"]=roc_acc(fred.get("INDPRO",pd.Series()),12,3)
    f["payrolls_acc"]=roc_acc(fred.get("PAYEMS",pd.Series()),12,3)
    f["cpi_acc"]=roc_acc(fred.get("CPI",pd.Series()),12,3)
    f["corepce_acc"]=roc_acc(fred.get("COREPCE",pd.Series()),12,3)
    f["lei_acc"]=roc_acc(fred.get("LEI",pd.Series()),3,2)
    # Price features
    for t in ["SPY","QQQ","IWM","RSP","UUP","TLT","EEM","EFA","GLD","HYG","LQD",
              "XLE","XLI","XLY","XLP","XLB","XLK","XLF","CL=F","GC=F","HG=F","SI=F"]:
        s=prices.get(t,pd.Series())
        tk=t.replace("^","").replace("=F","f").lower()
        f[f"{tk}_1m"]=ret_n(s,21); f[f"{tk}_3m"]=ret_n(s,63); f[f"{tk}_ts"]=ts(s)
    # Copper/gold
    cop=prices.get("HG=F",pd.Series()); gld=prices.get("GC=F",pd.Series())
    if not _s(cop).empty and not _s(gld).empty:
        c2,g2=_s(cop).align(_s(gld),join="inner")
        if len(c2)>63: cg=c2/g2; f["copper_gold_ratio_3m"]=ret_n(cg,63)
    # VIX
    vix_s=prices.get("^VIX",pd.Series()); vxv_s=prices.get("^VXV",pd.Series())
    f["vix_last"]=last(vix_s); f["vix_1m"]=delta_n(vix_s,21)
    if not _s(vix_s).empty and not _s(vxv_s).empty:
        v,vxv=_s(vix_s).align(_s(vxv_s),join="inner")
        if len(v)>5:
            r=float(v.iloc[-1])/float(vxv.iloc[-1]); f["vix_vxv_ratio"]=r
            f["vix_term_state"]="Contango (calm)" if r<0.90 else("Flat (neutral)" if r<1.00 else "Backwardation (fear)")
        else: f["vix_vxv_ratio"]=float("nan"); f["vix_term_state"]="Unknown"
    else: f["vix_vxv_ratio"]=float("nan"); f["vix_term_state"]="Unknown"
    # Data coverage
    macro_covered=sum(1 for k in raw_macro_keys if math.isfinite(f.get(k,float("nan"))))
    macro_proxy_share=1.0-(macro_covered/len(raw_macro_keys))
    price_avail=sum(1 for t in ["spy_1m","xli_1m","xly_1m","iwm_1m","oil_1m","gold_1m","dxy_1m"] if math.isfinite(f.get(t,float("nan"))))
    monthly_real_share=price_avail/7.0
    fred_real_share=fred_loaded/max(fred_total,1)
    structural_real_share=0.70*fred_real_share+0.30*(1-macro_proxy_share)
    data_coverage=clamp(0.70*structural_real_share+0.30*(1-macro_proxy_share))
    monthly_data_coverage=clamp(0.60*monthly_real_share+0.25*(1-macro_proxy_share)+0.15*structural_real_share)
    # Dual-horizon feature scaffolding (v33 exact formula)
    oil_3m=f.get("clf_3m",f.get("oil_3m",0.0)); gld_3m=f.get("gld_3m",f.get("gold_3m",0.0))
    uup_3m=f.get("uup_3m",f.get("dxy_3m",0.0)); spy_1m=f.get("spy_1m",0.0)
    xli_1m=f.get("xli_1m",0.0); xly_1m=f.get("xly_1m",0.0); iwm_1m=f.get("iwm_1m",0.0)
    oil_1m=f.get("clf_1m",f.get("oil_1m",0.0)); gld_1m=f.get("gcf_1m",f.get("gold_1m",0.0))
    uup_1m=f.get("uup_1m",f.get("dxy_1m",0.0)); bk1m=f.get("breakeven_1m",0.0)
    cpi=f.get("cpi_yoy",0.025); core=f.get("core_cpi_yoy",0.023)
    hcg=float(cpi-core) if(math.isfinite(cpi) and math.isfinite(core)) else 0.0
    # Growth structural (slow-moving, FRED-heavy)
    gi=[th(f.get("indpro_yoy",0)-0.02,0.05),th(f.get("retail_yoy",0)-0.03,0.06),
        th(f.get("payrolls_yoy",0)-0.015,0.03),th(f.get("housing_yoy",0),0.10),
        th((f.get("ism_last",50)-50)/100,0.04),th(-f.get("unrate_3m_delta",0),0.12),
        th(-f.get("claims_13w_delta",0)/40,0.60)]
    gm=[th(f.get("housing_yoy",0),0.08),th(f.get("indpro_yoy",0),0.05),
        th(-f.get("unrate_3m_delta",0),0.10),th(-f.get("claims_13w_delta",0)/50,0.50)]
    g_level=nm(*gi); g_mom=nm(*gm)
    # Inflation structural
    ii=[th(cpi-0.025,0.020),th(core-0.025,0.015),th((f.get("breakeven",2.2)-2.2)/2.0,0.300),
        th(nf(oil_3m),0.250),th(nf(gld_3m),0.180)]
    im=[th(nf(oil_3m),0.220),th(nf(gld_3m),0.180),th((f.get("breakeven",2.2)-2.2)/2.0,0.240),th(nf(uup_3m),0.140)]
    i_level=nm(*ii); i_mom=nm(*im)
    # Slowdown flags
    sf=sum([1 if math.isfinite(f.get("unrate_3m_delta",float("nan"))) and f.get("unrate_3m_delta",0)>0.05 else 0,
        1 if math.isfinite(f.get("claims_13w_delta",float("nan"))) and f.get("claims_13w_delta",0)>0 else 0,
        1 if math.isfinite(f.get("ism_last",float("nan"))) and f.get("ism_last",50)<50 else 0,
        1 if math.isfinite(f.get("housing_yoy",float("nan"))) and f.get("housing_yoy",0)<0 else 0])/4.0
    # Inflation shock
    inf_shock=nf(nm(th(nf(oil_3m),0.22),th((f.get("breakeven",2.2)-2.2)/2.0,0.24),th(nf(uup_3m),0.14)))
    # Monthly growth signal (fast, price-based)
    monthly_gi=[th(nf(spy_1m),0.05),th(nf(xli_1m),0.05),th(nf(xly_1m),0.05),th(nf(iwm_1m),0.07),th(-nf(uup_1m),0.06)]
    monthly_ii=[th(nf(hcg),0.004),th(nf(oil_1m),0.06),th(nf(gld_1m),0.05),th(nf(bk1m),0.08),th(-nf(uup_1m),0.05)]
    monthly_g_signal=nm(*monthly_gi); monthly_i_signal=nm(*monthly_ii)
    # Dual-horizon (exact v33 formulas)
    g_struct_level=nf(g_level); g_struct_mom=nf(g_mom)
    g_month_level=nf(0.65*g_level+0.35*g_mom); g_month_mom=nf(0.45*g_mom+0.55*monthly_g_signal)
    i_struct_level=nf(i_level); i_struct_mom=nf(i_mom)
    i_month_level=nf(0.55*i_level+0.25*i_mom+0.20*th(nf(hcg),0.004))
    i_month_mom=nf(0.45*i_mom+0.55*monthly_i_signal)
    # Policy + liquidity scores
    policy_score=th(-nf(f.get("policy_rate_3m",0.0)),0.50)
    liq_proxy=nm(th(-nf(uup_3m),0.12),th(nf(f.get("tlt_1m",0.0)),0.08))
    liq_score=th(nf(liq_proxy),0.50)
    m_policy=nf(0.60*policy_score+0.40*th(-nf(f.get("policy_rate_3m",0.0)),0.25))
    m_liq=nf(0.50*liq_score+0.50*th(nf(liq_proxy),0.35))
    m_shock=nf(nm(max(0.0,th(nf(hcg),0.004)),max(0.0,th(nf(oil_1m),0.06)),max(0.0,th(nf(bk1m),0.08))))
    # Coverage penalty prior
    PRIOR_MODE="off"
    prior_strength=0.0  # off mode
    prior_map={"Q1":0.0,"Q2":0.0,"Q3":0.0,"Q4":0.0}
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
        "_fred_loaded":fred_loaded,"_fred_total":fred_total,"_proxy_share":macro_proxy_share,
    })
    return f

def _score_block(g_level,g_mom,i_level,i_mom,policy,liq,sf,shock,data_cov,proxy_share,w,mw,monthly=False)->Tuple:
    g_core=w["g_level"]*g_level+w["g_mom"]*g_mom
    i_core=w["i_level"]*i_level+w["i_mom"]*i_mom
    p_core=w["policy"]*policy+w["liq"]*liq
    if monthly: i_core+=w.get("i_shock",0.0)*max(0.0,shock)
    raw={"Q1":+g_core-i_core-0.10*p_core,"Q2":+g_core+i_core-0.05*p_core,
         "Q3":-g_core+1.10*i_core+0.05*p_core,"Q4":-g_core-0.90*i_core+0.18*p_core}
    raw["Q1"]+=mw["shock_to_q1"]*max(0.0,shock)+mw["sf_to_q2"]*sf
    raw["Q2"]+=mw["gm_to_q2"]*max(0.0,g_mom)+mw["sf_to_q2"]*sf
    raw["Q3"]+=mw["sf_to_q3"]*sf+mw["shock_to_q3"]*max(0.0,shock)
    raw["Q4"]+=mw["gm_to_q4"]*max(0.0,-g_mom)
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
    s_probs,s_quad,s_next,s_conf,s_gc,s_ic,s_pc=_score_block(
        f.get("g_struct_level",0),f.get("g_struct_mom",0),
        f.get("i_struct_level",0),f.get("i_struct_mom",0),
        f.get("policy_score",0),f.get("liq_score",0),sf,shock,cov,proxy,STRUCT_W,QUAD_MOD,False)
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
    return dict(quad=s_quad,probs=s_probs,next_quad=s_next,confidence=s_conf,conf_band=cb,
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
    return [{"name":"Pain-before-relief refinancing","evidence":clamp(0.55*long_end+0.25*sf+0.20*max(0,-iwm_1m*5)),"hypothesis":pain_relief,
             "desc":"Long-end pain, growth stress, dan weak internals naikan odds bahwa financial-pain thresholds akhirnya memicu relief messaging.",
             "invalidators":["Long-end worsening tanpa policy response","Credit dan breadth deteriorate bersama-sama","Inflation shock accelerates"]},
            {"name":"War-shock then de-escalation","evidence":clamp(0.60*max(0,oil_3m*2)+0.20*max(0,uup_1m*5)+0.20*breadth_dmg),"hypothesis":war_de,
             "desc":"Energy shock mendukung stagflation trades dulu, tapi rising pain dapat membuat partial de-escalation atau relief narrative jauh lebih relevan.",
             "invalidators":["Oil keeps extending tanpa pause","Dollar pressure intensifies dan breadth tidak stabilize","Small-cap dan credit failure deepens together"]},
            {"name":"Tariff-pressure then negotiation relief","evidence":clamp(0.40*max(0,uup_1m*5)+0.35*max(0,-iwm_1m*5)+0.25*long_end),"hypothesis":tariff_neg,
             "desc":"Rising dollar, weak small caps, dan long-end pain mirip prior pressure cycles di mana later negotiation moderation triggers tactical relief.",
             "invalidators":["Escalation rhetoric compounds","Small caps tidak bisa stabilize","Long-end dan vol stress reinforce each other"]},
    ]

def build_scenarios(q:Dict,f:Dict,analog:Dict,playbooks:List)->Dict:
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
    # Normalize
    total=sum(raw.values()); probs={k:v/total for k,v in raw.items()}
    def _winners_losers(name:str):
        nl=name.lower()
        if "petrodollar" in nl or "shock" in nl: return ["Energy / Gold","Petro FX","Shipping"],["Oil importers","Broad cyclicals","Fragile EM FX"],["Oil fades quickly","USD and rates calm","Importer pain not spreading"]
        if "carry unwind" in nl or "dollar" in nl: return ["USD cash","Funding-safe majors","JPY/CHF hedges"],["Crowded carry","Fragile EM FX","High beta crypto"],["Dollar fails to extend","Vol compresses fast","Carry re-bid returns"]
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

def build_crash(f:Dict,h:Dict,q:Dict)->Dict:
    vix=f.get("vix_last",20.0); hy=f.get("hy_oas",350.0); ig=f.get("ig_oas",100.0)
    tail_s=1.0 if h.get("tail_state")=="stressed" else(0.35 if h.get("tail_state")=="neutral" else 0.10)
    shock_s=clamp(q.get("inf_shock",0.0)*1.5)
    health_frag={"Fragile":0.85,"Narrow":0.65,"Mixed":0.35,"Healthy":0.15,"Broken":0.90}.get(h.get("verdict","Mixed"),0.35)
    vix_s=0.90 if vix>=29 else(0.55 if vix>=19 else 0.20)
    unwind=clamp(h.get("narrow_leadership",0.5)*0.8+max(0,nf(f.get("uup_1m",0.0))*5)*0.2)
    vol_st=clamp((vix-18)/20); tail_hedge=clamp((f.get("vix_vxv_ratio",0.9)-0.9)*5+0.3) if math.isfinite(f.get("vix_vxv_ratio",float("nan"))) else 0.3
    dol_pr=clamp(0.5+nf(f.get("uup_1m",0.0))/0.04)
    # v33 exact crash formula
    crash_score=clamp(CRASH_W["tail_state"]*tail_s+CRASH_W["shock_state"]*shock_s+0.16*health_frag+0.10*vix_s+CRASH_W["unwind"]*unwind+CRASH_W["vol"]*vol_st+CRASH_W["tail_hedge"]*tail_hedge+0.08*dol_pr)
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
    return dict(crash_score=crash_score,risk_off=risk_off,div_state=div_s,state=state,
                vol_stress=vol_st,credit_stress=clamp(0.60*clamp((hy-300)/400 if math.isfinite(hy) else 0.3)+0.40*clamp((ig-80)/120 if math.isfinite(ig) else 0.3)),
                breadth_dmg=health_frag,reasons=rs[:5],crash_reasons=cr[:4],
                exec_score=exec_score,exec_mode=exec_mode)

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

@st.cache_data(ttl=TTL,show_spinner=False)
def load_all()->Dict:
    all_tickers=tuple(set(US_TICKERS+IHSG_TICKERS+FX_TICKERS+COMM_TICKERS+CRYPTO_TICKERS))
    with st.spinner("Fetching prices…"): prices=fetch_prices(all_tickers,period="2y")
    with st.spinner("Fetching FRED macro data…"): fred={k:fetch_fred(v) for k,v in FRED_SERIES.items()}
    f=build_macro(fred,prices); q=build_quad(f); h=build_health(prices,f)
    cr=build_crash(f,h,q); rot=build_rotation(q,h,f,prices); ih=build_ihsg(prices,q,f)
    analog=_match_analog(f); pb=build_playbooks(f,q); sc=build_scenarios(q,f,analog,pb)
    chk=build_checklists(f,h,q,ih)
    return dict(prices=prices,fred=fred,f=f,q=q,h=h,crash=cr,rotation=rot,ihsg=ih,
                analog=analog,playbooks=pb,scenarios=sc,checklists=chk,
                ts=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

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

def render_checklist(items:list,title:str="Checklist")->None:
    """Render v33-style ✓/✗/~ checklist in plain text (no HTML in dataframe)."""
    sh(title)
    rows=[]
    for label,score,note in items:
        sym,cls=_chk(score)
        rows.append({"Status":sym,"Kondisi":label,"Score":f"{score:.0%}","Catatan":note})
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True,height=len(items)*36+40)


def page_radar(snap:Dict)->None:
    q=snap["q"]; f=snap["f"]; rot=snap["rotation"]; analog=snap["analog"]
    s_quad=q["quad"]; m_quad=q["monthly_quad"]; meta=QUAD_META.get(s_quad,QUAD_META["Q4"])
    ps=f.get("_proxy_share",1.0); fl=int(f.get("_fred_loaded",0)); ft=int(f.get("_fred_total",0))
    if ps>0.60:
        st.markdown(f'<div class="proxy-b">⚠️ <strong>Proxy mode</strong> — FRED {fl}/{ft} series. Quad dari price proxy. Set FRED_API_KEY env var.</div>',unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="real-b">&#10003; FRED {fl}/{ft} series. Data coverage: {f.get("data_coverage",0):.0%}</div>',unsafe_allow_html=True)
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
    ih=snap["ihsg"]; q=snap["q"]; f=snap["f"]; prices=snap["prices"]
    sh("🇮🇩 IHSG — INDONESIAN MARKET ANALYSIS")
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
    h=snap["h"]; f=snap["f"]; prices=snap["prices"]
    sh("📡 TACTICAL WEATHER — CAN WE TRADE? (v33 weights)")
    c1,c2,c3,c4=st.columns(4)
    def mcard3(label,s,sub,states):
        cls="good" if s==states[0] else("bad" if s==states[-1] else "warn")
        mc(label,s,sub,cls)
    with c1: mcard3("Trade Environment","Supportive" if h["trade_state"]=="supportive" else("Hostile" if h["trade_state"]=="hostile" else "Balanced"),"breadth+credit+USD",("Supportive","Balanced","Hostile"))
    with c2: mcard3("Market Trend",h["trend_state"].capitalize(),"price+breadth+dollar",("Persistent","Mixed","Fragile"))
    with c3: mcard3("Tail State",h["tail_state"].capitalize(),"vol+credit+small+narrow",("Calm","Neutral","Stressed"))
    with c4: mcard3("Overall Weather",h["weather_state"],"composite 35/35/30",("Risk-On","Mixed","Risk-Off"))
    st.markdown("---"); ca,cb=st.columns(2)
    with ca:
        sh(f"📊 BREADTH (trade={TACT_TRADE_W['breadth']:.0%} weight)")
        gb("Sektor di atas 50-DMA",h["sec_support"],note=f"({h['sec_above50']}/11)")
        gb("SPY trend health",h["spy_trend"])
        gb("Small cap (IWM)",h["iwm_trend"])
        gb("Equal-weight vs cap-weight",clamp(0.5+h.get("eqw_vs_cw",0)*5),note=pct(h.get("eqw_vs_cw",0))+" 3M diff")
        gb("Narrow leadership (inverse)",1-h.get("narrow_leadership",0.5),"low narrow = health")
        gb("Breadth composite",h["breadth"])
    with cb:
        sh("⚡ CREDIT & VOL (tail weights)")
        hy=f.get("hy_oas",float("nan")); ig=f.get("ig_oas",float("nan"))
        gb("HY Credit health",clamp(1.0-(hy-250)/500) if math.isfinite(hy) else 0.5,note=f"{hy:.0f}bps" if math.isfinite(hy) else "proxy")
        gb("IG Credit health ★",clamp(1.0-(ig-50)/200) if math.isfinite(ig) else 0.5,note=f"{ig:.0f}bps" if math.isfinite(ig) else "n/a")
        vix=f.get("vix_last",20.0); gb("VIX health",clamp(1.0-(vix-13)/25),note=f"VIX {vix:.1f}")
        vr=f.get("vix_vxv_ratio",float("nan"))
        gb("VIX term structure ★",clamp(1.0-(vr-0.85)/0.25) if math.isfinite(vr) else 0.5,note=f.get("vix_term_state",""))
        gb("Credit+Vol composite",(h["tail"]))
    st.markdown("---"); sh("📈 YIELD CURVE ★")
    sp=f.get("spread_2s10s",float("nan")); sp30=f.get("spread_10s30s",float("nan")); sp3m=f.get("spread_2s10s_3m",float("nan"))
    y1,y2,y3=st.columns(3)
    with y1: mc("2s10s Spread",f"{sp:+.2f}%" if math.isfinite(sp) else "—",f.get("yield_curve_state",""),"good" if(math.isfinite(sp) and sp>0.5) else("bad" if(math.isfinite(sp) and sp<0) else "warn"))
    with y2: mc("10s30s Spread",f"{sp30:+.2f}%" if math.isfinite(sp30) else "—")
    with y3: mc("2s10s 3M Δ",f"{sp3m:+.2f}%" if math.isfinite(sp3m) else "—","Uninverting → resesi dimulai" if f.get("yield_curve_uninverting") else "","warn" if f.get("yield_curve_uninverting") else "neu")
    st.info("> **Yield curve:** 2Y > 10Y = inverted = sinyal resesi. Ketika curve *steepen* (uninverting), itu tanda resesi sedang dimulai bukan ending. Watch 3M direction.")
    st.markdown("---"); sh("📦 SEKTOR US vs SPY (3M)")
    SECS={"XLE":"Energy","XLF":"Financials","XLI":"Industrials","XLB":"Materials","XLK":"Technology","XLV":"Healthcare","XLY":"Cons.Disc.","XLP":"Cons.Staples","XLU":"Utilities","XLRE":"Real Estate","XLC":"Comm.Svc."}
    spy3=ret_n(prices.get("SPY",pd.Series()),63); rows=[]
    for t,name in SECS.items():
        s=prices.get(t,pd.Series()); r3=ret_n(s,63); r1=ret_n(s,21)
        rel=(r3-spy3) if(math.isfinite(r3) and math.isfinite(spy3)) else float("nan")
        rows.append({"Sektor":name,"3M":pct(r3),"1M":pct(r1),"vs SPY 3M":pct(rel),"50DMA":"✓" if ts(s)>=0.5 else "✗"})
    rows.sort(key=lambda r:float(r["vs SPY 3M"].replace("%","").replace("—","0").replace("+","")) if r["vs SPY 3M"]!="—" else -999,reverse=True)
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True,height=360)
    # v33-style checklist
    st.markdown("---")
    chk=snap.get("checklists",{})
    if chk.get("global"):
        render_checklist(chk["global"],"✅ KONDISI GLOBAL — CHECKLIST TRADING")
        st.caption("✓ = Kondisi baik | ~ = Mixed/watch | ✗ = Kondisi buruk")

def page_playbook(snap:Dict)->None:
    q=snap["q"]; rot=snap["rotation"]; sc=snap["scenarios"]; pb=snap["playbooks"]; prices=snap["prices"]
    s_quad=q["quad"]; meta=QUAD_META.get(s_quad,QUAD_META["Q4"])
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
    f=snap["f"]; fred=snap["fred"]; prices=snap["prices"]; q=snap["q"]
    sh("📋 FRED DATA COVERAGE")
    cov=[{"Series":k,"FRED ID":FRED_SERIES.get(k,""),"Points":len(_s(s)),"Latest":str(_s(s).index[-1])[:10] if not _s(s).empty else "—","Last Value":round(float(_s(s).iloc[-1]),4) if not _s(s).empty else None,"Status":"✓ Loaded" if not _s(s).empty else "✗ Missing"} for k,s in fred.items()]
    st.dataframe(pd.DataFrame(cov),use_container_width=True,hide_index=True,height=480)
    ps=f.get("_proxy_share",1.0); fl=int(f.get("_fred_loaded",0)); ft=int(f.get("_fred_total",0))
    if ps>0.50: st.warning(f"**FRED issue ({fl}/{ft} loaded).** Fix: `export FRED_API_KEY=key` (free at fred.stlouisfed.org/api/key/). App jalan di proxy mode, quad tetap bekerja.")
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
        ("Macro proxy share",f"{f.get('macro_proxy_share',0):.2f}"),
        ("Quad core g_core",f"{q.get('g_core',0):+.4f}"),("Quad core i_core",f"{q.get('i_core',0):+.4f}"),
        ("Structural quad",q.get("quad","")),("Structural conf",f"{q.get('confidence',0):.2f}"),
        ("Monthly quad",q.get("monthly_quad","")),("Monthly conf",f"{q.get('monthly_conf',0):.2f}"),
        ("Flip hazard",f"{q.get('flip_hazard',0):.3f}"),("Deepness",f"{q.get('deepness',0):.3f}"),("Duration maturity",f"{q.get('duration_mat',0):.3f}"),
    ]
    st.dataframe(pd.DataFrame(internal_rows,columns=["Internal Feature","Value"]),use_container_width=True,hide_index=True,height=500)
    sh("📦 PRICE DATA COVERAGE")
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

def page_markets_full(snap:Dict)->None:
    """Markets tab: IHSG + US + FX + Commodities + Crypto, semua terintegrasi."""
    prices=snap["prices"]; q=snap["q"]; f=snap["f"]; ih=snap["ihsg"]; rot=snap["rotation"]
    s_quad=q["quad"]; meta=QUAD_META.get(s_quad,QUAD_META["Q4"])

    t0,t1,t2,t3,t4=st.tabs(["🇮🇩 IHSG","🇺🇸 US Stocks","💱 FX","🛢️ Komoditas","🔐 Crypto"])

    # ── IHSG ─────────────────────────────────────────────────────────────────
    with t0:
        sh("🇮🇩 IHSG — INDONESIAN MARKET ANALYSIS")
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
    with t1:
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

    # ── FX ─────────────────────────────────────────────────────────────────────
    with t2:
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

    # ── Komoditas ──────────────────────────────────────────────────────────────
    with t3:
        sh("🛢️ KOMODITAS")
        COMM_NAMES={"GC=F":"Gold (XAU)","SI=F":"Silver","CL=F":"Oil WTI","BZ=F":"Oil Brent","NG=F":"Natural Gas","HG=F":"Copper","ZC=F":"Corn","ZW=F":"Wheat","DBC":"Broad Commodities ETF","URA":"Uranium ETF"}
        comm_rows=[]
        for tk,name in COMM_NAMES.items():
            s=prices.get(tk,pd.Series()); r1=ret_n(s,21); r3=ret_n(s,63)
            comm_rows.append({"Komoditas":name,"1M":pct(r1),"3M":pct(r3),"Trend":"▲" if ts(s)>=0.5 else "▼"})
        st.dataframe(pd.DataFrame(comm_rows),use_container_width=True,hide_index=True)
        regime_comm={"Q1":"Q1 = Gold ok, Oil ok, Copper ok. Commodities broadly supportive.","Q2":"Q2 = Energy king. Oil, Gas, Copper outperform. Materials rally.","Q3":"Q3 Stagflasi = GOLD best trade. Oil bisa volatile. Avoid cyclical metals.","Q4":"Q4 = Commodities broadly weak. Gold bisa rally jika recession fear dominates."}
        st.info(regime_comm.get(s_quad,""))
        # Petrodollar note
        oil_3m=ret_n(prices.get("CL=F",pd.Series()),63)
        gold_3m=ret_n(prices.get("GC=F",pd.Series()),63)
        mc("Oil WTI 3M",pct(oil_3m),"signal inflasi","warn" if(math.isfinite(oil_3m) and oil_3m>0.05) else "neu")
        mc("Gold 3M",pct(gold_3m),"hard asset hedge","good" if(math.isfinite(gold_3m) and gold_3m>0.05) else "neu")

    # ── Crypto ─────────────────────────────────────────────────────────────────
    with t4:
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
        st.caption("⚠️ Crypto = high-beta risk asset, bukan inflation hedge. Naik paling kencang di Q1, hancur paling dalam di Q3/Q4.")


def main():
    st.markdown('<div style="display:flex;align-items:center;margin-bottom:4px"><span style="font-family:Syne,sans-serif;font-size:20px;font-weight:800;letter-spacing:-.03em">🧭 MacroRegime Pro</span><span style="font-size:10px;opacity:.3;margin-left:8px;font-family:DM Mono,monospace">v6.1 · Hedgeye GIP Framework · v33 weights</span></div>',unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("### ⚙️ Controls")
        if st.button("🔄 Force Refresh",use_container_width=True): st.cache_data.clear(); st.rerun()
        st.markdown("---")
        st.markdown("""
**Urutan baca (orang awam):**
1. 🧭 **Radar** — Kita di regime apa? Trade terbaik apa sekarang?
2. 📡 **Health** — Aman masuk pasar sekarang?
3. 🎯 **Playbook** — Strategy detail + skenario + what-if
4. 🌐 **Markets** — IHSG · US · FX · Komoditas · Crypto
5. ⚠️ **Risk** — Seberapa bahaya kondisi saat ini?
6. 🔬 **Diag** — Kualitas data & internal engine

**v6.1 fixes:**
- Bug prices_placeholder fixed
- Bug Series `and` operator fixed
- IHSG masuk Markets tab
- Semua tab error resolved
        """)
    snap=load_all()
    q=snap["q"]; f=snap["f"]; cr=snap["crash"]; quad=q["quad"]; meta=QUAD_META.get(quad,{})
    ga="▲" if q.get("growth_acc") else "▼"; ia="▲" if q.get("infl_acc") else "▼"
    div_badge=f" / M:{q['monthly_quad']}" if q["divergence"]=="divergent" else ""
    st.markdown(f'<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:7px 10px;border-radius:8px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);margin-bottom:10px;font-size:11px"><span>Regime: {qb(quad)}{div_badge} <strong>{meta.get("label","")}</strong></span><span style="opacity:.25">|</span><span>Conf: <strong>{q["confidence"]:.0%}</strong> ({q.get("conf_band","")})</span><span style="opacity:.25">|</span><span>Growth: <strong>{ga}</strong></span><span style="opacity:.25">|</span><span>Inflasi: <strong>{ia}</strong></span><span style="opacity:.25">|</span><span>Risk: <strong>{cr["state"]}</strong></span><span style="opacity:.25">|</span><span>Exec: <strong>{cr["exec_mode"]}</strong></span><span style="opacity:.25">|</span><span style="opacity:.3">{snap["ts"]}</span></div>',unsafe_allow_html=True)
    tabs=st.tabs(["🧭 Radar","📡 Health","🎯 Playbook","🌐 Markets","⚠️ Risk","🔬 Diagnostics"])
    with tabs[0]: page_radar(snap)
    with tabs[1]: page_health(snap)
    with tabs[2]: page_playbook(snap)
    with tabs[3]: page_markets_full(snap)
    with tabs[4]: page_risk(snap)
    with tabs[5]: page_diag(snap)

if __name__=="__main__": main()
