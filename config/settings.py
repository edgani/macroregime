"""settings.py — ALL parameters. Zero hardcoded thresholds in engines.

Hedgeye GIP: 30 monthly data points, 90 quarterly.
Everything flows from this file.
"""
from __future__ import annotations
import os

# ── API ───────────────────────────────────────────────────────────────────────
FRED_API_KEY: str = os.environ.get("FRED_API_KEY", "")

# ── Cache / storage ───────────────────────────────────────────────────────────
PRICE_HISTORY_DAYS: int = 756
FRED_HISTORY_MONTHS: int = 36
CACHE_TTL_SECONDS: int = 3600
SNAPSHOT_PATH: str = ".cache/snapshot.pkl"

# ── FRED series ───────────────────────────────────────────────────────────────
# FIXED: added ISMNO (ISM Manufacturing) — critical for Hedgeye GIP
FRED_GROWTH_SERIES = {
    "INDPRO":"Industrial Production",
    "RSAFS":"Retail Sales",
    "PAYEMS":"Nonfarm Payrolls",
    "UNRATE":"Unemployment",
    "ICSA":"Initial Claims",
    "HOUST":"Housing Starts",
    "ISMNO":"ISM Manufacturing",  # ← ADDED
}
FRED_INFLATION_SERIES = {
    "CPIAUCSL":"CPI",
    "CPILFESL":"Core CPI",
    "PPIACO":"PPI",
    "T5YIE":"5yr Breakeven",
    "T10YIE":"10yr Breakeven",
    "DFII10":"10yr TIPS",
}
FRED_POLICY_SERIES = {
    "FEDFUNDS":"Fed Funds",
    "DFF":"Daily Fed Funds",
    "M2SL":"M2 Money Supply",
}

# ── GIP Weights (Hedgeye: RoC/momentum dominant) ─────────────────────────────
GROWTH_LEVEL_WEIGHTS = {
    "indpro_yoy":0.22,"retail_yoy":0.20,"payrolls_yoy":0.18,
    "housing_yoy":0.12,"ism_norm":0.15,"unrate_inv":0.07,"claims_inv":0.06
}
GROWTH_MOM_WEIGHTS = {
    "indpro_roc":0.28,"retail_roc":0.22,"payrolls_roc":0.18,
    "ism_delta":0.14,"unrate_delta":0.10,"claims_delta":0.08
}
INFLATION_LEVEL_WEIGHTS= {
    "cpi_yoy":0.28,"core_cpi_yoy":0.24,"breakeven_5y":0.18,
    "ppi_yoy":0.14,"oil_3m":0.10,"gold_3m":0.06
}
INFLATION_MOM_WEIGHTS = {
    "cpi_roc":0.30,"core_cpi_roc":0.26,"breakeven_delta":0.18,
    "oil_1m":0.14,"dxy_inv_1m":0.12
}

# FIXED: Structural = inflation-dominant for Q3 accuracy (was growth 60%/inf 40%)
# Hedgeye structural Q3 = growth decelerating + inflation accelerating
STRUCTURAL_WEIGHTS = {
    "growth_level":0.15,
    "growth_momentum":0.30,
    "inflation_level":0.20,
    "inflation_momentum":0.35,
}
MONTHLY_WEIGHTS = {
    "growth_level":0.15,
    "growth_momentum":0.50,
    "inflation_level":0.10,
    "inflation_momentum":0.50,
}
POLICY_WEIGHT_STRUCTURAL: float = 0.12
POLICY_WEIGHT_MONTHLY: float = 0.10
ISM_NEUTRAL: float = 50.0

# ── Risk Range (Hurst Rescaled Range) ────────────────────────────────────────
RR_TRADE_LOOKBACK = 15; RR_TREND_LOOKBACK = 63; RR_TAIL_LOOKBACK = 252
RR_TRADE_SIGMA = 1.5; RR_TREND_SIGMA = 2.0; RR_TAIL_SIGMA = 2.8
RR_HURST_SCALE = 1.0

# ── Country universe (50+) ────────────────────────────────────────────────────
COUNTRY_UNIVERSE: dict = {
    "USA":("SPY","americas",0.20,1.00), "Mexico":("EWW","americas",0.40,0.85),
    "Canada":("EWC","americas",0.55,0.80), "Argentina":("ARGT","americas",0.35,0.90),
    "Brazil":("EWZ","americas",0.65,0.75), "Chile":("ECH","americas",0.60,0.75),
    "Colombia":("GXG","americas",0.65,0.70),"Peru":("EPU","americas",0.60,0.70),
    "Hong_Kong":("EWH","asia",0.15,0.95), "Japan":("EWJ","asia",0.20,0.80),
    "Korea":("EWY","asia",0.30,0.75), "Taiwan":("EWT","asia",0.15,0.70),
    "China":("MCHI","asia",0.30,0.65), "India":("INDA","asia",0.25,0.70),
    "Indonesia":("EIDO","asia",0.70,0.55), "Australia":("EWA","asia",0.65,0.70),
    "Vietnam":("VNM","asia",0.40,0.65), "Thailand":("THD","asia",0.45,0.65),
    "Malaysia":("EWM","asia",0.50,0.65), "Singapore":("EWS","asia",0.25,0.80),
    "Germany":("EWG","europe",0.35,0.70), "UK":("EWU","europe",0.30,0.75),
    "France":("EWQ","europe",0.30,0.70), "Switzerland":("EWL","europe",0.20,0.75),
    "Norway":("NORW","europe",0.75,0.80), "Sweden":("EWD","europe",0.35,0.75),
    "Poland":("EPOL","europe",0.40,0.65), "Turkey":("TUR","europe",0.35,0.60),
    "Italy":("EWI","europe",0.30,0.70), "Spain":("EWP","europe",0.30,0.70),
    "Israel":("EIS","mideast",0.20,0.80), "UAE":("UAE","mideast",0.80,0.65),
    "Saudi":("KSA","mideast",0.85,0.65), "Qatar":("QAT","mideast",0.80,0.65),
    "South_Africa":("EZA","em",0.55,0.65),"Nigeria":("NGE","em",0.70,0.60),
    "Egypt":("EGPT","em",0.45,0.60), "Kenya":("EAF","em",0.40,0.60),
}

# ── US Sectors ────────────────────────────────────────────────────────────────
US_SECTORS: dict = {
    "XLK":"Technology","XLY":"Consumer Disc","XLI":"Industrials","XLF":"Financials",
    "XLE":"Energy","XLB":"Materials","XLV":"Healthcare","XLP":"Consumer Staples",
    "XLU":"Utilities","XLRE":"Real Estate","XLC":"Communication",
}
US_FACTORS: dict = {
    "SPY":"S&P500","QQQ":"Nasdaq","IWM":"Russell 2000","DIA":"Dow Jones",
    "VTV":"Value","VUG":"Growth","USMV":"Min Vol","HDV":"High Div",
    "RSP":"Equal Weight","MTUM":"Momentum","QUAL":"Quality","SIZE":"Small-Mid",
}

# ── Full Forex Universe ───────────────────────────────────────────────────────
FOREX_PAIRS: dict = {
    "EURUSD=X":"EUR/USD","GBPUSD=X":"GBP/USD","USDJPY=X":"USD/JPY",
    "USDCHF=X":"USD/CHF","USDCAD=X":"USD/CAD","AUDUSD=X":"AUD/USD",
    "NZDUSD=X":"NZD/USD","USDSEK=X":"USD/SEK","USDNOK=X":"USD/NOK",
    "USDMXN=X":"USD/MXN","USDBRL=X":"USD/BRL","USDTRY=X":"USD/TRY",
    "USDZAR=X":"USD/ZAR","USDIDR=X":"USD/IDR","USDSGD=X":"USD/SGD",
    "USDINR=X":"USD/INR","USDCNY=X":"USD/CNY","USDKRW=X":"USD/KRW",
    "USDTHB=X":"USD/THB","USDPHP=X":"USD/PHP","USDMYR=X":"USD/MYR",
    "EURJPY=X":"EUR/JPY","GBPJPY=X":"GBP/JPY","AUDNZD=X":"AUD/NZD",
    "CADUSD=X":"CAD/USD (Oil proxy)",
    "DX-Y.NYB":"USD Index (DXY)",
}

# ── Full Commodities Universe ─────────────────────────────────────────────────
COMMODITIES: dict = {
    "GC=F":"Gold","SI=F":"Silver","PL=F":"Platinum","PA=F":"Palladium",
    "GLD":"Gold ETF","SLV":"Silver ETF","PPLT":"Platinum ETF",
    "CL=F":"WTI Crude Oil","BZ=F":"Brent Crude","NG=F":"Natural Gas",
    "RB=F":"RBOB Gasoline","HO=F":"Heating Oil",
    "USO":"Oil ETF","UNG":"Nat Gas ETF","BNO":"Brent Oil ETF",
    "HG=F":"Copper","ALI=F":"Aluminum","ZNC=F":"Zinc",
    "CPER":"Copper ETF","JJC":"iPath Copper",
    "ZW=F":"Wheat","ZC=F":"Corn","ZS=F":"Soybeans",
    "ZO=F":"Oats","KC=F":"Coffee","SB=F":"Sugar","CT=F":"Cotton","CC=F":"Cocoa",
    "DBA":"Agriculture ETF","WEAT":"Wheat ETF","CORN":"Corn ETF",
    "LBS=F":"Lumber",
    "URA":"Uranium ETF","CCJ":"Cameco",
}

# ── Full Crypto Universe ──────────────────────────────────────────────────────
CRYPTO: dict = {
    "BTC-USD":"Bitcoin","ETH-USD":"Ethereum","BNB-USD":"BNB","SOL-USD":"Solana",
    "XRP-USD":"Ripple","ADA-USD":"Cardano","AVAX-USD":"Avalanche",
    "DOT-USD":"Polkadot","MATIC-USD":"Polygon","LINK-USD":"Chainlink",
    "DOGE-USD":"Dogecoin","LTC-USD":"Litecoin","ATOM-USD":"Cosmos",
    "NEAR-USD":"NEAR Protocol","APT-USD":"Aptos","ARB-USD":"Arbitrum",
    "OP-USD":"Optimism","SUI-USD":"Sui","INJ-USD":"Injective",
    "IBIT":"iShares Bitcoin ETF","FBTC":"Fidelity Bitcoin ETF",
    "ETHA":"iShares Ethereum ETF",
}

# ── IHSG / Indonesia ──────────────────────────────────────────────────────────
IHSG_UNIVERSE: dict = {
    "^JKSE":"IHSG Index","EIDO":"Indonesia ETF (USD listed)",
    "BBCA.JK":"BCA Bank","BBRI.JK":"BRI Bank","BMRI.JK":"Mandiri Bank",
    "TLKM.JK":"Telkom","ASII.JK":"Astra International",
    "UNVR.JK":"Unilever Indonesia","ICBP.JK":"Indofood CBP",
    "INDF.JK":"Indofood","KLBF.JK":"Kalbe Farma",
    "ITMG.JK":"Indo Tambangraya Megah","ADRO.JK":"Adaro Energy",
    "PTBA.JK":"Bukit Asam","HRUM.JK":"Harum Energy",
    "INCO.JK":"Vale Indonesia","MDKA.JK":"Merdeka Copper Gold",
    "ANTM.JK":"Aneka Tambang","NCKL.JK":"Trimegah Bangun Persada",
    "LSIP.JK":"PP London Sumatra","AALI.JK":"Astra Agro","SSMS.JK":"Sawit Sumbermas",
    "BSDE.JK":"BSD City","CTRA.JK":"Ciputra","PWON.JK":"Pakuwon Jati",
    "MYOR.JK":"Mayora Indah","HMSP.JK":"HM Sampoerna",
}

# ── Bonds ─────────────────────────────────────────────────────────────────────
BONDS: dict = {
    "TLT":"20yr UST","IEF":"7-10yr UST","SHY":"1-3yr UST","GOVT":"All UST",
    "TIP":"TIPS (inflation-linked)","LTPZ":"Long TIPS",
    "LQD":"IG Corporate","HYG":"HY Corporate","JNK":"HY Bonds",
    "EMB":"EM USD Bonds","PCY":"EM Local Bonds",
    "BND":"Total Bond","AGG":"US Agg Bond",
}

# ── Core macro proxy tickers (always loaded) ──────────────────────────────────
MACRO_PROXIES: dict = {
    "SPY":"S&P500","QQQ":"Nasdaq","IWM":"Russell 2k","DIA":"Dow",
    "XLI":"Industrials","XLY":"Consumer Disc","XHB":"Homebuilders",
    "UUP":"USD ETF","GLD":"Gold","TLT":"Long Bond",
    "CL=F":"WTI Oil","GC=F":"Gold Futures",
}

# ── Quad playbook (backtested 27yr Hedgeye data) ─────────────────────────────
QUAD_ASSET_PERFORMANCE: dict = {
    "Q1":{
        "best":["US Equities","Tech (XLK)","Consumer Disc (XLY)","Industrials (XLI)","Credit","Small Caps (IWM)","Crypto (risk-on)"],
        "worst":["Gold","Utilities (XLU)","Consumer Staples (XLP)","Long Bonds (TLT)","Commodities"],
        "style":"Growth, Small Cap, High Beta, Quality — broadest participation",
        "fx":"USD moderate; EM FX with strong GDP benefit; AUD/NZD/CAD supportive",
        "bonds":"Bearish — yields rising with growth, inflation contained",
        "sectors_overweight":["XLK","XLY","XLI","XLF"],"sectors_underweight":["XLU","XLP","XLV"],
    },
    "Q2":{
        "best":["Energy (XLE)","Materials (XLB)","Industrials (XLI)","Commodities","select Equities","BTC (reflation)"],
        "worst":["Utilities","Consumer Staples","Long Bonds","High Grade Fixed Income"],
        "style":"Value, High Beta, Commodity Exposure, Cyclicals",
        "fx":"Commodity FX outperform: AUD, CAD, NOK, MXN, BRL; USD mixed; IDR under pressure",
        "bonds":"Very bearish — growth AND inflation up = steepening curve, yields surge",
        "sectors_overweight":["XLE","XLB","XLI","XLY"],"sectors_underweight":["XLU","XLP","TLT"],
    },
    "Q3":{
        "best":["Gold","Precious Metals","Healthcare (XLV)","Utilities (XLU)","Consumer Staples (XLP)","Defense","Long USTs (selective)"],
        "worst":["Tech (XLK)","Consumer Disc (XLY)","Small Caps (IWM)","Credit (HYG)","EM Equities (non-commodity)","Crypto"],
        "style":"Low Beta, Dividend Yield, Quality, Secular Growth (defensive), Min Volatility",
        "fx":"USD bearish TREND (McCullough Apr 2026 confirmed); commodity FX mixed; EM headwinds except commodity exporters",
        "bonds":"Long duration USTs bullish (flight to quality); watch breakevens",
        "sectors_overweight":["XLV","XLP","XLU","GLD"],"sectors_underweight":["XLK","XLY","IWM","XLF"],
        "note":"CURRENT STRUCTURAL QUAD (Apr 2026). Monthly Q2 overlay adds tactical commodity/energy.",
    },
    "Q4":{
        "best":["Healthcare (XLV)","Consumer Staples (XLP)","Utilities (XLU)","Long Bonds (TLT)","USD","Gold"],
        "worst":["Tech (XLK)","Energy (XLE)","Credit (HYG)","Small Caps","Commodities","Crypto"],
        "style":"Min Volatility, Low Beta, Dividend, Quality, Defensive",
        "fx":"USD very bullish (flight to safety); commodity FX crushed; EM brutal",
        "bonds":"Very bullish — deflationary collapse; max long TLT",
        "sectors_overweight":["XLV","XLP","XLU","TLT"],"sectors_underweight":["XLK","XLE","HYG","IWM"],
    },
}

# ── Bottleneck profiles ───────────────────────────────────────────────────────
BOTTLENECK_PROFILES: dict = {
    "ai_compute": {"constraint":0.90,"Q1":0.85,"Q2":0.70,"Q3":0.50,"Q4":0.30},
    "ai_networking": {"constraint":0.85,"Q1":0.80,"Q2":0.75,"Q3":0.55,"Q4":0.35},
    "ai_optics": {"constraint":0.92,"Q1":0.78,"Q2":0.72,"Q3":0.62,"Q4":0.40},
    "ai_power": {"constraint":0.87,"Q1":0.70,"Q2":0.75,"Q3":0.65,"Q4":0.50},
    "ai_power_infra": {"constraint":0.85,"Q1":0.65,"Q2":0.70,"Q3":0.70,"Q4":0.55},
    "ai_packaging": {"constraint":0.80,"Q1":0.75,"Q2":0.70,"Q3":0.55,"Q4":0.35},
    "healthcare_eq": {"constraint":0.80,"Q1":0.65,"Q2":0.55,"Q3":0.85,"Q4":0.80},
    "pharma": {"constraint":0.82,"Q1":0.60,"Q2":0.50,"Q3":0.80,"Q4":0.75},
    "defense": {"constraint":0.82,"Q1":0.55,"Q2":0.65,"Q3":0.78,"Q4":0.62},
    "utilities": {"constraint":0.75,"Q1":0.50,"Q2":0.45,"Q3":0.82,"Q4":0.86},
    "water": {"constraint":0.80,"Q1":0.55,"Q2":0.50,"Q3":0.85,"Q4":0.86},
    "precious_metals": {"constraint":0.72,"Q1":0.70,"Q2":0.68,"Q3":0.88,"Q4":0.82},
    "energy_infra": {"constraint":0.75,"Q1":0.55,"Q2":0.88,"Q3":0.75,"Q4":0.30},
    "uranium": {"constraint":0.85,"Q1":0.70,"Q2":0.80,"Q3":0.65,"Q4":0.50},
    "staples": {"constraint":0.55,"Q1":0.45,"Q2":0.40,"Q3":0.78,"Q4":0.82},
    "sic_gan": {"constraint":0.88,"Q1":0.70,"Q2":0.75,"Q3":0.65,"Q4":0.45},
    "coal": {"constraint":0.60,"Q1":0.50,"Q2":0.80,"Q3":0.55,"Q4":0.25},
    "nickel": {"constraint":0.70,"Q1":0.60,"Q2":0.82,"Q3":0.55,"Q4":0.30},
    "cpo_palm": {"constraint":0.65,"Q1":0.55,"Q2":0.75,"Q3":0.60,"Q4":0.30},
    "generic": {"constraint":0.20,"Q1":0.50,"Q2":0.50,"Q3":0.40,"Q4":0.40},
}

TICKER_SECTOR: dict = {
    "NVDA":"ai_compute","AMD":"ai_compute","AVGO":"ai_compute","TSM":"ai_compute","INTC":"ai_compute",
    "ALAB":"ai_networking","CRDO":"ai_networking","MRVL":"ai_networking","ANET":"ai_networking","SMCI":"ai_networking",
    "LITE":"ai_optics","COHR":"ai_optics","CIEN":"ai_optics","POET":"ai_optics","VIAV":"ai_optics","GLW":"ai_optics",
    "ON":"sic_gan","WOLF":"sic_gan","STM":"sic_gan","IFNNY":"sic_gan",
    "VST":"ai_power_infra","CEG":"ai_power_infra","ETN":"ai_power_infra","NRG":"ai_power_infra","GEV":"ai_power_infra","EMR":"ai_power_infra",
    "AMKR":"ai_packaging","ASX":"ai_packaging","TSEM":"ai_packaging",
    "ISRG":"healthcare_eq","ABT":"healthcare_eq","BSX":"healthcare_eq","MDT":"healthcare_eq","EW":"healthcare_eq","SYK":"healthcare_eq",
    "LLY":"pharma","MRNA":"pharma","REGN":"pharma","BMY":"pharma","PFE":"pharma",
    "LMT":"defense","RTX":"defense","NOC":"defense","GD":"defense","KTOS":"defense","HII":"defense","LDOS":"defense","BAH":"defense",
    "NEE":"utilities","DUK":"utilities","D":"utilities","SO":"utilities","XLU":"utilities",
    "AWK":"water","WTRG":"water","CWT":"water",
    "GLD":"precious_metals","GC=F":"precious_metals","SLV":"precious_metals","SI=F":"precious_metals","PPLT":"precious_metals","GFI":"precious_metals","NEM":"precious_metals",
    "XLE":"energy_infra","CL=F":"energy_infra","BZ=F":"energy_infra","XOM":"energy_infra","CVX":"energy_infra","COP":"energy_infra","SLB":"energy_infra",
    "URA":"uranium","CCJ":"uranium","NXE":"uranium","UUUU":"uranium",
    "XLP":"staples","PG":"staples","KO":"staples","PEP":"staples","WMT":"staples","COST":"staples",
    "SPY":"generic","QQQ":"generic","IWM":"generic","TLT":"generic","DIA":"generic","VTV":"generic","VUG":"generic",
}
