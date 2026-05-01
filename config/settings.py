"""config/settings.py — v2 GIP Upgrade
Changes vs previous:
 + PCE & Core PCE added to FRED_INFLATION_SERIES (PCEPI, PCEPILFE)
 + ISM sub-components added to FRED_GROWTH_SERIES (NAPMNO, NAPMII)
 + Real Rates added to FRED_POLICY_SERIES (computed from DFII10 already fetched)
 + INFLATION_LEVEL_WEIGHTS updated: PCE now carries 20% weight (CPI reduced)
 + INFLATION_MOM_WEIGHTS updated: pce_roc + core_pce_roc added
 + GROWTH_LEVEL_WEIGHTS updated: ism_orders_inv_spread added (most leading ISM signal)
 + GROWTH_MOM_WEIGHTS updated: ism_oi_roc added
 + fred_coverage_keys updated to include new series for proxy_share tracking

WHY PCE:
 Fed targets Core PCE, not CPI. CPI runs ~0.2-0.5% ABOVE PCE structurally.
 Hedgeye tracks both. Using only CPI = overestimating inflation signal by ~20-30bps.
 This was causing Q2/Q3 inflation signal to be stickier than Hedgeye's own reading.

WHY ISM New Orders - Inventories:
 Orders-Inventories spread is the MOST LEADING sub-component of ISM (~6wks lead on headline).
 McCullough references "ISM orders" specifically, not just headline ISM.
 Positive spread (orders > inventories) = production acceleration coming = growth bullish.
 Negative spread = destocking coming = growth bearish early warning.

WHY Real Rates (DFII10 level directly):
 DFII10 IS the real rate (TIPS). Already fetched, just not used in policy scoring.
 Rising real rates = tightening financial conditions = policy drag regardless of nominal Fed Funds.
 This makes Q4 detection more accurate (real rates rise while Fed pauses = still tightening).
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
FRED_GROWTH_SERIES = {
    "INDPRO": "Industrial Production",
    "RSAFS": "Retail Sales",
    "PAYEMS": "Nonfarm Payrolls",
    "UNRATE": "Unemployment",
    "ICSA": "Initial Claims",
    "HOUST": "Housing Starts",
    "ISMNO": "ISM Manufacturing",
    # v2: ISM sub-components — Orders-Inventories spread = most leading ISM signal
    "NAPMNO": "ISM New Orders Index",  # soft-fail if unavailable on FRED
    "NAPMII": "ISM Inventories Index",  # soft-fail if unavailable on FRED
}

FRED_INFLATION_SERIES = {
    "CPIAUCSL": "CPI",
    "CPILFESL": "Core CPI",
    "PPIACO": "PPI",
    "T5YIE": "5yr Breakeven",
    "T10YIE": "10yr Breakeven",
    "DFII10": "10yr TIPS (Real Rate)",
    # v2: PCE — Fed's preferred inflation measure. Critical gap was here.
    "PCEPI": "PCE Price Index",  # Fed targets this, not CPI
    "PCEPILFE": "Core PCE (ex Food/Energy)",  # Most important for Fed reaction function
}

FRED_POLICY_SERIES = {
    "FEDFUNDS": "Fed Funds",
    "DFF": "Daily Fed Funds",
    "M2SL": "M2 Money Supply",
    # Note: Real Rates computed from DFII10 (already in inflation series)
    # No new series needed — computed in _extract_fred_features()
}

# ── GIP Weights (updated v2) ─────────────────────────────────────────────────
# Rule: weights must sum to 1.0 per dict. Verified below.

# Growth Level: added ism_orders_inv (ISM New Orders minus Inventories spread)
# Most leading sub-component of ISM. Reduced housing_yoy slightly.
GROWTH_LEVEL_WEIGHTS = {
    "indpro_yoy": 0.22,  # unchanged — best hard data signal
    "retail_yoy": 0.20,  # unchanged — consumption proxy
    "payrolls_yoy": 0.18,  # unchanged — labor market
    "ism_orders_inv": 0.10,  # NEW: orders-inventories spread (leading)
    "ism_norm": 0.10,  # reduced from 0.15 (spread is more leading than headline)
    "housing_yoy": 0.10,  # reduced from 0.12 (lagging indicator)
    "unrate_inv": 0.06,  # reduced from 0.07
    "claims_inv": 0.04,  # reduced from 0.06
}
# Sum check: 0.22+0.20+0.18+0.10+0.10+0.10+0.06+0.04 = 1.00 ✅

# Growth Momentum: added ism_oi_roc (rate of change of orders-inventories)
GROWTH_MOM_WEIGHTS = {
    "indpro_roc": 0.26,  # reduced from 0.28
    "retail_roc": 0.22,  # unchanged
    "payrolls_roc": 0.18,  # unchanged
    "ism_oi_roc": 0.10,  # NEW: ROC of orders-inventories spread
    "ism_delta": 0.10,  # reduced from 0.14
    "unrate_delta": 0.10,  # unchanged
    "claims_delta": 0.04,  # reduced from 0.08
}
# Sum check: 0.26+0.22+0.18+0.10+0.10+0.10+0.04 = 1.00 ✅

# Inflation Level: PCE now primary, CPI secondary
# Rationale: Fed watches PCE. PCE is structurally ~0.2-0.5% below CPI.
# Using only CPI was overestimating inflation persistence → hurting Q3/Q4 accuracy.
INFLATION_LEVEL_WEIGHTS = {
    "pce_yoy": 0.20,  # NEW: PCE YoY — Fed's primary inflation target
    "core_pce_yoy": 0.18,  # NEW: Core PCE — most important for Fed reaction
    "cpi_yoy": 0.16,  # reduced from 0.28 (still relevant as CPI is market-watched)
    "core_cpi_yoy": 0.14,  # reduced from 0.24
    "breakeven_5y": 0.16,  # unchanged — market-implied inflation expectations
    "ppi_yoy": 0.10,  # reduced from 0.14 (pipeline inflation)
    "oil_3m": 0.04,  # reduced from 0.10 (subsumed in PPI/PCE)
    "gold_3m": 0.02,  # reduced from 0.06 (tail hedge, not primary inflation signal)
}
# Sum check: 0.20+0.18+0.16+0.14+0.16+0.10+0.04+0.02 = 1.00 ✅

# Inflation Momentum: PCE ROC is faster and more accurate than CPI ROC
INFLATION_MOM_WEIGHTS = {
    "pce_roc": 0.14,  # NEW: PCE rate of change
    "core_pce_roc": 0.12,  # NEW: Core PCE ROC — fastest Fed reaction signal
    "cpi_roc": 0.20,  # reduced from 0.30
    "core_cpi_roc": 0.18,  # reduced from 0.26
    "breakeven_delta": 0.18,  # unchanged — market inflation expectations momentum
    "oil_1m": 0.10,  # reduced from 0.14
    "dxy_inv_1m": 0.08,  # reduced from 0.12
}
# Sum check: 0.14+0.12+0.20+0.18+0.18+0.10+0.08 = 1.00 ✅

# Structural quad weights: inflation-dominant (Hedgeye Q3 calibration)
STRUCTURAL_WEIGHTS = {
    "growth_level": 0.15,
    "growth_momentum": 0.30,
    "inflation_level": 0.20,
    "inflation_momentum":0.35,
}

MONTHLY_WEIGHTS = {
    "growth_level": 0.15,
    "growth_momentum": 0.50,
    "inflation_level": 0.10,
    "inflation_momentum":0.50,
}

POLICY_WEIGHT_STRUCTURAL: float = 0.12
POLICY_WEIGHT_MONTHLY: float = 0.10
ISM_NEUTRAL: float = 50.0

# ── Keys tracked for proxy_share coverage calculation ────────────────────────
# Extend from 9 to 13 keys (4 new: pce, core_pce, ism_orders_inv, real_rate)
FRED_COVERAGE_KEYS = [
    "indpro_yoy", "retail_yoy", "payrolls_yoy", "cpi_yoy", "core_cpi_yoy",
    "ism_norm", "housing_yoy", "unrate_inv", "claims_inv",
    # v2 additions:
    "pce_yoy", "core_pce_yoy", "ism_orders_inv", "real_rate_norm",
]

# ── Risk Range (Hurst Rescaled Range) ────────────────────────────────────────
RR_TRADE_LOOKBACK = 15; RR_TREND_LOOKBACK = 63; RR_TAIL_LOOKBACK = 252
RR_TRADE_SIGMA = 1.5; RR_TREND_SIGMA = 2.0; RR_TAIL_SIGMA = 2.8
RR_HURST_SCALE = 1.0

# ── Macro proxies (benchmark tickers always loaded) ───────────────────────────
MACRO_PROXIES: dict = {
    "SPY":"S&P500","QQQ":"Nasdaq","IWM":"Russell2000","TLT":"20yr Bond",
    "GLD":"Gold ETF","SLV":"Silver ETF","UUP":"USD ETF","DBA":"Agri ETF",
    "XLI":"Industrials","XLE":"Energy","XLP":"Staples","XLV":"Healthcare",
    "XLY":"Consumer Disc","XLU":"Utilities","XLK":"Technology","XLF":"Financials",
    "XLB":"Materials","XHB":"Homebuilders","HYG":"High Yield","LQD":"IG Credit",
    "EEM":"EM Equities","IEF":"7-10yr Bond","CL=F":"WTI Oil","GC=F":"Gold Futures",
}

# ── US Sectors & Factors ──────────────────────────────────────────────────────
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
    "CADUSD=X":"CAD/USD (Oil proxy)","DX-Y.NYB":"USD Index (DXY)",
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
    "DBA":"Agriculture ETF","WEAT":"Wheat ETF","CORN":"Corn ETF","LBS=F":"Lumber",
    "URA":"Uranium ETF","CCJ":"Cameco",
}

# ── Full Crypto Universe ──────────────────────────────────────────────────────
CRYPTO: dict = {
    "BTC-USD":"Bitcoin","ETH-USD":"Ethereum","BNB-USD":"BNB","SOL-USD":"Solana",
    "XRP-USD":"Ripple","ADA-USD":"Cardano","AVAX-USD":"Avalanche",
    "DOT-USD":"Polkadot","MATIC-USD":"Polygon","LINK-USD":"Chainlink",
    "DOGE-USD":"Dogecoin","LTC-USD":"Litecoin","ATOM-USD":"Cosmos",
    "NEAR-USD":"NEAR","APT-USD":"Aptos","ARB-USD":"Arbitrum",
    "OP-USD":"Optimism","SUI20947-USD":"Sui","INJ-USD":"Injective","SEI-USD":"SEI",
    "AAVE-USD":"Aave","UNI7083-USD":"Uniswap","MKR-USD":"Maker",
    "LDO-USD":"Lido DAO","CRV-USD":"Curve","COMP5692-USD":"Compound",
    "FET-USD":"Fetch.ai","TAO22974-USD":"TAO/Bittensor","RNDR-USD":"Render",
    "GRT6719-USD":"The Graph","OCEAN-USD":"Ocean Protocol","HNT-USD":"Helium",
    "ONDO-USD":"Ondo Finance","POLYX-USD":"Polymesh",
    "TON11419-USD":"Toncoin","TIA22861-USD":"Celestia","PYTH-USD":"Pyth",
    "WIF-USD":"dogwifhat","PEPE24478-USD":"Pepe","BONK-USD":"Bonk","FLOKI-USD":"Floki",
    "IBIT":"iShares Bitcoin ETF","FBTC":"Fidelity Bitcoin ETF",
    "ETHA":"iShares Ethereum ETF","MSTR":"MicroStrategy",
}

# ── IHSG / Indonesia ──────────────────────────────────────────────────────────
IHSG_UNIVERSE: dict = {
    "^JKSE":"IHSG Index","EIDO":"Indonesia ETF (USD)",
    "BBCA.JK":"BCA","BBRI.JK":"BRI","BMRI.JK":"Mandiri","BBNI.JK":"BNI",
    "BRIS.JK":"BSI","BBTN.JK":"BTN","BNGA.JK":"CIMB Niaga","MEGA.JK":"Bank Mega","NISP.JK":"OCBC",
    "ADRO.JK":"Adaro","PTBA.JK":"Bukit Asam","ITMG.JK":"ITMG","HRUM.JK":"Harum",
    "INDY.JK":"Indika","AADI.JK":"Aadi","BUMI.JK":"Bumi Resources",
    "MEDC.JK":"Medco","PGEO.JK":"Pertamina Geothermal","AKRA.JK":"AKR","UNTR.JK":"United Tractors",
    "INCO.JK":"Vale Indonesia","MDKA.JK":"Merdeka","ANTM.JK":"Antam",
    "TINS.JK":"Timah","BRMS.JK":"Bumi Resources Min","NCKL.JK":"Trimegah Bangun",
    "TLKM.JK":"Telkom","ASII.JK":"Astra","UNVR.JK":"Unilever",
    "LSIP.JK":"London Sumatra","AALI.JK":"Astra Agro","SSMS.JK":"Sawit Sumbermas",
    "BSDE.JK":"BSD City","CTRA.JK":"Ciputra","PWON.JK":"Pakuwon",
    "MYOR.JK":"Mayora","HMSP.JK":"HM Sampoerna",
    # OSV / Offshore
    "SHIP.JK":"Sillo Maritime (SHIP)","PSSI.JK":"Pacific Interlink (PSSI)",
    "LEAD.JK":"Logindo (LEAD)","OBMD.JK":"Ocean Bermuda (OBMD)",
    "AKRA.JK":"AKR Corporindo","TPMA.JK":"Trans Power Marine",
}

# ── Bonds / Fixed Income ──────────────────────────────────────────────────────
BONDS: dict = {
    "TLT": "20+ Year Treasury ETF",
    "IEF": "7-10 Year Treasury ETF",
    "SHY": "1-3 Year Treasury ETF",
    "AGG": "US Aggregate Bond ETF",
    "LQD": "Investment Grade Corporate",
    "HYG": "High Yield Corporate",
    "TLTW": "20+ Year Treasury & Write",
    "GOVT": "US Treasury Bond ETF",
    "SPTL": "SPDR Long Term Treasury",
    "VGIT": "Vanguard Int-Term Treasury",
    "VGSH": "Vanguard Short-Term Treasury",
    "VGTL": "Vanguard Long-Term Treasury",
    "BND": "Vanguard Total Bond",
    "SCHZ": "Schwab US Aggregate",
    "TIP": "TIPS Inflation-Protected",
    "STIP": "Short-Term TIPS",
    "VTIP": "Vanguard Short-Term TIPS",
    "SPIP": "SPDR Portfolio TIPS",
    "SPTI": "SPDR Int-Term Treasury",
    "SPTS": "SPDR Short-Term Treasury",
    "SHYG": "0-5 Year High Yield",
    "SJNK": "0-5 Year High Yield",
    "BKLN": "Senior Loan ETF",
    "EMB": "USD Emerging Markets Bond",
    "PCY": "Emerging Markets Sovereign",
    "VWOB": "Vanguard EM Govt Bond",
    "JNK": "Junk Bond ETF",
    "USIG": "Broad USD Investment Grade",
    "IGSB": "Short-Term Investment Grade",
    "IGIB": "Int-Term Investment Grade",
    "IGLB": "Long-Term Investment Grade",
    "SLQD": "0-5 Year Inv Grade Corp",
    "SRLN": "Senior Loan ETF",
    "FALN": "Fallen Angel Bond ETF",
    "ANGL": "VanEck Fallen Angel",
    "PGHY": "Global Short-Term High Yield",
    "USHY": "Broad USD High Yield",
    "SPBO": "SPDR Corp Bond",
    "CORP": "PIMCO Investment Grade Corp",
    "LDUR": "PIMCO Low Duration",
    "MINT": "PIMCO Enhanced Short Maturity",
    "GSY": "Ultra-Short Bond",
    "NEAR": "iShares Short Maturity Bond",
    "ICSH": "Ultra-Short-Term Bond",
    "JPST": "JPMorgan Ultra-Short Income",
}

# ── Quad playbook (backtested 27yr Hedgeye data) ─────────────────────────────
QUAD_ASSET_PERFORMANCE: dict = {
    "Q1":{
        "best":["US Equities","Tech (XLK)","Consumer Disc (XLY)","Industrials (XLI)",
                "Credit","Small Caps (IWM)","Crypto (risk-on)"],
        "worst":["Gold","Utilities (XLU)","Consumer Staples (XLP)","Long Bonds (TLT)","Commodities"],
        "style":"Growth, Small Cap, High Beta, Quality — broadest participation",
        "fx":"USD moderate; EM FX benefit; AUD/NZD/CAD supportive",
        "bonds":"Bearish — yields rising with growth, inflation contained",
        "sectors_overweight":["XLK","XLY","XLI","XLF"],"sectors_underweight":["XLU","XLP","XLV"],
    },
    "Q2":{
        "best":["Energy (XLE)","Materials (XLB)","Industrials (XLI)","Commodities",
                "select Equities","BTC (reflation)"],
        "worst":["Utilities","Consumer Staples","Long Bonds","High Grade Fixed Income"],
        "style":"Value, High Beta, Commodity Exposure, Cyclicals",
        "fx":"Commodity FX outperform: AUD, CAD, NOK, MXN, BRL; USD mixed; IDR under pressure",
        "bonds":"Very bearish — growth AND inflation up = steepening curve, yields surge",
        "sectors_overweight":["XLE","XLB","XLI","XLY"],"sectors_underweight":["XLU","XLP","TLT"],
    },
    "Q3":{
        "best":["Gold","Precious Metals","Healthcare (XLV)","Utilities (XLU)",
                "Consumer Staples (XLP)","Defense","Long USTs (selective)"],
        "worst":["Tech (XLK)","Consumer Disc (XLY)","Small Caps (IWM)",
                "Credit (HYG)","EM Equities (non-commodity)","Crypto"],
        "style":"Low Beta, Dividend Yield, Quality, Secular Growth (defensive), Min Volatility",
        "fx":"USD bearish TREND; commodity FX mixed; EM headwinds except commodity exporters",
        "bonds":"Long duration USTs bullish (flight to quality); watch breakevens",
        "sectors_overweight":["XLV","XLP","XLU","GLD"],"sectors_underweight":["XLK","XLY","IWM","XLF"],
    },
    "Q4":{
        "best":["Healthcare (XLV)","Consumer Staples (XLP)","Utilities (XLU)",
                "Long Bonds (TLT)","USD","Gold"],
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
    "ai_memory": {"constraint":0.83,"Q1":0.80,"Q2":0.72,"Q3":0.55,"Q4":0.35},
    "healthcare_eq": {"constraint":0.80,"Q1":0.65,"Q2":0.55,"Q3":0.85,"Q4":0.80},
    "pharma": {"constraint":0.82,"Q1":0.60,"Q2":0.50,"Q3":0.80,"Q4":0.75},
    "defense": {"constraint":0.82,"Q1":0.55,"Q2":0.65,"Q3":0.78,"Q4":0.62},
    "utilities": {"constraint":0.75,"Q1":0.50,"Q2":0.45,"Q3":0.82,"Q4":0.86},
    "water": {"constraint":0.80,"Q1":0.55,"Q2":0.50,"Q3":0.85,"Q4":0.86},
    "precious_metals": {"constraint":0.72,"Q1":0.70,"Q2":0.68,"Q3":0.88,"Q4":0.82},
    "energy_infra": {"constraint":0.75,"Q1":0.55,"Q2":0.88,"Q3":0.75,"Q4":0.30},
    "uranium": {"constraint":0.85,"Q1":0.70,"Q2":0.80,"Q3":0.65,"Q4":0.50},
    "transformer_infra":{"constraint":0.88,"Q1":0.60,"Q2":0.70,"Q3":0.72,"Q4":0.50},
    "sic_gan": {"constraint":0.88,"Q1":0.70,"Q2":0.75,"Q3":0.65,"Q4":0.45},
    "depin_ai": {"constraint":0.75,"Q1":0.90,"Q2":0.70,"Q3":0.30,"Q4":0.40},
    "staples": {"constraint":0.55,"Q1":0.45,"Q2":0.40,"Q3":0.78,"Q4":0.82},
    "coal": {"constraint":0.60,"Q1":0.50,"Q2":0.80,"Q3":0.55,"Q4":0.25},
    "nickel": {"constraint":0.70,"Q1":0.60,"Q2":0.82,"Q3":0.55,"Q4":0.30},
    "cpo_palm": {"constraint":0.65,"Q1":0.55,"Q2":0.75,"Q3":0.60,"Q4":0.30},
    "oil_services": {"constraint":0.80,"Q1":0.55,"Q2":0.85,"Q3":0.70,"Q4":0.30},
    "osv_hulu": {"constraint":0.82,"Q1":0.50,"Q2":0.82,"Q3":0.68,"Q4":0.25},
    "dry_bulk_shipping":{"constraint":0.78,"Q1":0.55,"Q2":0.80,"Q3":0.60,"Q4":0.25},
    "oil_distribution": {"constraint":0.72,"Q1":0.50,"Q2":0.78,"Q3":0.65,"Q4":0.30},
    "banking_ihsg": {"constraint":0.65,"Q1":0.75,"Q2":0.70,"Q3":0.40,"Q4":0.30},
    "generic": {"constraint":0.40,"Q1":0.50,"Q2":0.50,"Q3":0.50,"Q4":0.50},
}

# ── Market Classification (ticker → asset class) ──────────────────────────────
MARKET_CLASSIFICATION: dict = {
    # US Equity
    **{t:"us_equity" for t in [
        "LITE","COHR","POET","ON","WOLF","VST","ETN","GEV","VRT","HUBB","NVT","BE",
        "AJINY","AMKR","COHU","MU","ARM","SNDK","MPWR","AEHR","ISRG","GLD","LMT",
        "MKSI","ACLS","FORM","KMI","NVD","AMD","AVGO","NVDA","TSLA","AAPL","MSFT",
        "GOOGL","META","AMZN","NFLX","PLTR","AXON","SAIC","KTOS",
        "XLK","XLY","XLI","XLF","XLE","XLB","XLV","XLP","XLU","XLRE","XLC",
        "SPY","QQQ","IWM","DIA","VTV","VUG","USMV","HDV","RSP","MTUM","QUAL",
        "TLT","IEF","HYG","LQD","EEM","GLD","SLV","URA","CCJ",
        "IBIT","FBTC","ETHA","MSTR",
    ]},
    # Forex
    **{t:"forex" for t in [
        "EURUSD=X","GBPUSD=X","USDJPY=X","USDCHF=X","USDCAD=X","AUDUSD=X",
        "NZDUSD=X","USDSEK=X","USDNOK=X","USDMXN=X","USDBRL=X","USDTRY=X",
        "USDZAR=X","USDIDR=X","USDSGD=X","USDINR=X","USDCNY=X","USDKRW=X",
        "USDTHB=X","USDPHP=X","USDMYR=X","EURJPY=X","GBPJPY=X","AUDNZD=X",
        "CADUSD=X","DX-Y.NYB",
    ]},
    # Commodity
    **{t:"commodity" for t in [
        "GC=F","SI=F","PL=F","PA=F","GLD","SLV","PPLT",
        "CL=F","BZ=F","NG=F","RB=F","HO=F","USO","UNG","BNO",
        "HG=F","ALI=F","ZNC=F","CPER","JJC",
        "ZW=F","ZC=F","ZS=F","ZO=F","KC=F","SB=F","CT=F","CC=F",
        "DBA","WEAT","CORN","LBS=F","URA","CCJ",
    ]},
    # Crypto
    **{t:"crypto" for t in [
        "BTC-USD","ETH-USD","BNB-USD","SOL-USD","XRP-USD","ADA-USD","AVAX-USD",
        "DOT-USD","MATIC-USD","LINK-USD","DOGE-USD","LTC-USD","ATOM-USD",
        "NEAR-USD","APT-USD","ARB-USD","OP-USD","SUI20947-USD","INJ-USD","SEI-USD",
        "AAVE-USD","UNI7083-USD","MKR-USD","LDO-USD","CRV-USD","COMP5692-USD",
        "FET-USD","TAO22974-USD","RNDR-USD","GRT6719-USD","OCEAN-USD","HNT-USD",
        "ONDO-USD","POLYX-USD","TON11419-USD","TIA22861-USD","PYTH-USD",
        "WIF-USD","PEPE24478-USD","BONK-USD","FLOKI-USD",
    ]},
    # IHSG
    **{t:"ihsg" for t in [
        "^JKSE","EIDO",
        "BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BRIS.JK","BBTN.JK",
        "BNGA.JK","MEGA.JK","NISP.JK",
        "ADRO.JK","PTBA.JK","ITMG.JK","HRUM.JK","INDY.JK","AADI.JK","BUMI.JK",
        "MEDC.JK","PGEO.JK","AKRA.JK","UNTR.JK",
        "INCO.JK","MDKA.JK","ANTM.JK","TINS.JK","BRMS.JK","NCKL.JK",
        "TLKM.JK","ASII.JK","UNVR.JK","LSIP.JK","AALI.JK","SSMS.JK",
        "BSDE.JK","CTRA.JK","PWON.JK","MYOR.JK","HMSP.JK",
        "SHIP.JK","PSSI.JK","LEAD.JK","OBMD.JK","TPMA.JK",
    ]},
}

# ── Ticker → Sector mapping ───────────────────────────────────────────────────
TICKER_SECTOR: dict = {
    # AI Optics
    "LITE":"ai_optics","COHR":"ai_optics","POET":"ai_optics",
    "MKSI":"ai_optics","ACLS":"ai_optics","FORM":"ai_optics",
    # AI Power
    "ON":"ai_power","WOLF":"ai_power","MPWR":"ai_power","AEHR":"sic_gan",
    # AI Power Infra
    "VST":"ai_power_infra","ETN":"ai_power_infra","GEV":"ai_power_infra","BE":"ai_power_infra",
    # Transformer
    "VRT":"transformer_infra","HUBB":"transformer_infra","NVT":"transformer_infra",
    # AI Packaging
    "AJINY":"ai_packaging","AMKR":"ai_packaging","COHU":"ai_packaging",
    # AI Memory / Compute
    "MU":"ai_memory","SNDK":"ai_memory","ARM":"ai_compute",
    # Healthcare
    "ISRG":"healthcare_eq","MDT":"healthcare_eq","SYK":"healthcare_eq",
    "LLY":"pharma","MRNA":"pharma","REGN":"pharma",
    # Defense
    "LMT":"defense","NOC":"defense","RTX":"defense","GD":"defense","KTOS":"defense",
    # Precious Metals
    "GLD":"precious_metals","GC=F":"precious_metals","SLV":"precious_metals","SI=F":"precious_metals",
    # Energy
    "KMI":"energy_infra","CL=F":"energy_infra","BZ=F":"energy_infra","USO":"energy_infra",
    # Uranium
    "URA":"uranium","CCJ":"uranium",
    # Crypto
    "BTC-USD":"depin_ai","ETH-USD":"depin_ai",
    "TAO22974-USD":"depin_ai","RNDR-USD":"depin_ai","FET-USD":"depin_ai",
    # Forex
    "EURUSD=X":"forex","GBPUSD=X":"forex","USDJPY=X":"forex","USDCHF=X":"forex",
    "USDCAD=X":"forex","AUDUSD=X":"forex","NZDUSD=X":"forex",
    "USDMXN=X":"forex","USDBRL=X":"forex","USDIDR=X":"forex","DX-Y.NYB":"forex",
    # Commodities
    "HG=F":"commodity_copper","ALI=F":"commodity_aluminum",
    "ZW=F":"commodity","ZC=F":"commodity","ZS=F":"commodity",
    # IHSG
    "^JKSE":"generic","EIDO":"generic",
    "BBCA.JK":"banking_ihsg","BBRI.JK":"banking_ihsg","BMRI.JK":"banking_ihsg",
    "ITMG.JK":"coal","ADRO.JK":"coal","PTBA.JK":"coal",
    "INCO.JK":"nickel","NCKL.JK":"nickel","ANTM.JK":"nickel",
    "SHIP.JK":"osv_hulu","LEAD.JK":"osv_hulu","OBMD.JK":"oil_services",
    "PSSI.JK":"dry_bulk_shipping","TPMA.JK":"dry_bulk_shipping",
    "AKRA.JK":"oil_distribution","MEDC.JK":"energy_infra",
    # Benchmarks (generic)
    "SPY":"generic","QQQ":"generic","IWM":"generic","TLT":"generic","GLD":"precious_metals",
}

# ── Quad → Market Direction ───────────────────────────────────────────────────
QUAD_MARKET_DIRECTION: dict = {
    "Q1": {"us_equity":"long","forex":"neutral","commodity":"short","crypto":"long","ihsg":"long","bonds":"short"},
    "Q2": {"us_equity":"long","forex":"long","commodity":"long","crypto":"neutral","ihsg":"long","bonds":"short"},
    "Q3": {"us_equity":"short","forex":"short","commodity":"long","crypto":"short","ihsg":"short","bonds":"long"},
    "Q4": {"us_equity":"short","forex":"short","commodity":"short","crypto":"short","ihsg":"short","bonds":"long"},
}

# ── EM Recovery Signals ───────────────────────────────────────────────────────
EM_RECOVERY_SIGNALS: dict = {
    "Q3→Q2": {
        "trigger": "Monthly Q2 inside Structural Q3 = EM commodity exporters early recovery",
        "best": ["EIDO","EWW","EWZ","EWC","NORW","EWA","USDMXN=X","USDBRL=X","AUDUSD=X"],
        "rationale": "Q2 monthly = commodity bid + growth rebound. EM commodity exporters lead.",
        "confidence": 0.55,
    },
    "Q4→Q1": {
        "trigger": "Deflation → Goldilocks = MAX EM recovery setup",
        "best": ["EIDO","INDA","EWZ","EWW","EEM","VWO","USDMXN=X","USDBRL=X"],
        "rationale": "Q4→Q1 = growth re-acceleration + inflation contained + Fed easing. EM historically +25-40% in first 6M.",
        "confidence": 0.85,
    },
    "Q3→Q1": {
        "trigger": "Direct stagflation → goldilocks = EM selective recovery",
        "best": ["INDA","EIDO","EWS","EWT"],
        "rationale": "Rare direct transition. Only high-quality EM recover.",
        "confidence": 0.60,
    },
    "Q3→Q4": {
        "trigger": "Stagflation → Deflation = EM brutal",
        "best": ["USD","TLT","GLD"],
        "rationale": "EM crushed. Avoid EIDO, EWZ, EWW. Only USD assets.",
        "confidence": 0.70,
    },
}

# ── Country Universe (50+) ────────────────────────────────────────────────────
COUNTRY_UNIVERSE: dict = {
    "USA":("SPY","americas",0.20,1.00),"Mexico":("EWW","americas",0.40,0.85),
    "Canada":("EWC","americas",0.55,0.80),"Argentina":("ARGT","americas",0.35,0.90),
    "Brazil":("EWZ","americas",0.65,0.75),"Chile":("ECH","americas",0.60,0.75),
    "Colombia":("GXG","americas",0.65,0.70),"Peru":("EPU","americas",0.60,0.70),
    "Hong_Kong":("EWH","asia",0.15,0.95),"Japan":("EWJ","asia",0.20,0.80),
    "Korea":("EWY","asia",0.30,0.75),"Taiwan":("EWT","asia",0.15,0.70),
    "China":("MCHI","asia",0.30,0.65),"India":("INDA","asia",0.25,0.70),
    "Indonesia":("EIDO","asia",0.70,0.55),"Australia":("EWA","asia",0.65,0.70),
    "Vietnam":("VNM","asia",0.40,0.65),"Thailand":("THD","asia",0.45,0.65),
    "Malaysia":("EWM","asia",0.50,0.65),"Singapore":("EWS","asia",0.25,0.80),
    "Germany":("EWG","europe",0.35,0.70),"UK":("EWU","europe",0.30,0.75),
    "France":("EWQ","europe",0.30,0.70),"Switzerland":("EWL","europe",0.20,0.75),
    "Norway":("NORW","europe",0.75,0.80),"Sweden":("EWD","europe",0.35,0.75),
    "Poland":("EPOL","europe",0.40,0.65),"Turkey":("TUR","europe",0.35,0.60),
    "Italy":("EWI","europe",0.30,0.70),"Spain":("EWP","europe",0.30,0.70),
    "Israel":("EIS","mideast",0.20,0.80),"UAE":("UAE","mideast",0.80,0.65),
    "Saudi":("KSA","mideast",0.85,0.65),"South_Africa":("EZA","em",0.55,0.65),
    "Nigeria":("NGE","em",0.70,0.60),"Egypt":("EGPT","em",0.45,0.60),
}

# ── MAG7 ─────────────────────────────────────────────────────────────────────
MAG7 = ["AAPL","MSFT","NVDA","GOOGL","META","AMZN","TSLA"]

# ── US Buckets ────────────────────────────────────────────────────────────────
US_BUCKETS: dict = {
    "ai_compute": ["NVDA","AMD","AVGO","TSM","QCOM"],
    "ai_memory": ["MU","SNDK"],
    "ai_optics": ["LITE","COHR","POET","MKSI","ACLS","FORM"],
    "ai_power": ["ON","WOLF","MPWR","AEHR"],
    "ai_power_infra": ["VST","ETN","GEV","BE"],
    "transformer_infra": ["VRT","HUBB","NVT"],
    "ai_packaging": ["AJINY","AMKR","COHU"],
    "healthcare_eq": ["ISRG","MDT","SYK","DXCM","PODD","RMD"],
    "pharma": ["LLY","MRNA","REGN","BMY","PFE","NVO","AZN"],
    "defense": ["LMT","NOC","RTX","GD","KTOS","HII","LDOS","AXON"],
    "precious_metals": ["GLD","SLV","AEM","WPM","FNV","RGLD"],
    "utilities": ["NEE","DUK","D","SO","XLU","AEP","EXC"],
    "uranium": ["URA","CCJ","NXE","UUUU","LEU"],
    "energy_infra": ["KMI","WMB","OKE","XOM","CVX","SLB"],
    "staples": ["WMT","COST","PG","KO","PEP","MCD","PM","MO"],
}

IHSG_BUCKETS: dict = {
    "banking_ihsg": ["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BRIS.JK"],
    "coal": ["ADRO.JK","ITMG.JK","PTBA.JK","HRUM.JK","BUMI.JK"],
    "nickel": ["INCO.JK","MDKA.JK","ANTM.JK","NCKL.JK"],
    "osv_hulu": ["SHIP.JK","LEAD.JK"],
    "oil_services": ["OBMD.JK","MEDC.JK"],
    "dry_bulk_shipping": ["PSSI.JK","TPMA.JK"],
    "oil_distribution": ["AKRA.JK"],
}

FX_BUCKETS: dict = {
    "commodity_fx": ["AUDUSD=X","NZDUSD=X","USDCAD=X","USDNOK=X","USDMXN=X"],
    "em_fx": ["USDIDR=X","USDBRL=X","USDMYR=X","USDPHP=X","USDINR=X"],
    "safe_haven_fx": ["USDJPY=X","USDCHF=X"],
    "dxy": ["DX-Y.NYB"],
}

COMMODITY_BUCKETS: dict = {
    "precious_metals": ["GC=F","SI=F","GLD","SLV"],
    "energy": ["CL=F","BZ=F","NG=F","USO","UNG"],
    "base_metals": ["HG=F","ALI=F","ZNC=F","CPER"],
    "agriculture": ["ZW=F","ZC=F","ZS=F","DBA"],
    "uranium": ["URA","CCJ"],
}

CRYPTO_BUCKETS: dict = {
    "btc_ecosystem": ["BTC-USD","IBIT","FBTC","MSTR"],
    "eth_ecosystem": ["ETH-USD","ETHA","ARB-USD","OP-USD"],
    "layer1": ["SOL-USD","AVAX-USD","ADA-USD","NEAR-USD","APT-USD"],
    "depin_ai": ["TAO22974-USD","RNDR-USD","FET-USD","GRT6719-USD","HNT-USD"],
    "defi": ["AAVE-USD","UNI7083-USD","MKR-USD","CRV-USD"],
}
