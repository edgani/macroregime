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
    "copper":            {"constraint":0.78,"Q1":0.65,"Q2":0.88,"Q3":0.72,"Q4":0.35},
    "commodity_aluminum":{"constraint":0.65,"Q1":0.55,"Q2":0.82,"Q3":0.65,"Q4":0.30},
    "commodity":         {"constraint":0.60,"Q1":0.55,"Q2":0.80,"Q3":0.65,"Q4":0.30},
    "commodity_copper":  {"constraint":0.78,"Q1":0.65,"Q2":0.88,"Q3":0.72,"Q4":0.35},
    "forex":             {"constraint":0.30,"Q1":0.50,"Q2":0.55,"Q3":0.50,"Q4":0.60},
    "generic":           {"constraint":0.40,"Q1":0.50,"Q2":0.50,"Q3":0.50,"Q4":0.50},
}

# ── Market Classification (ticker → asset class) ──────────────────────────────
MARKET_CLASSIFICATION: dict = {
    # US Equity
    **{t:"us_equity" for t in [
        # AI Optics
        "LITE","COHR","POET","CIEN","VIAV","GLW","MKSI","ACLS",
        "FN","MTSI","IPAR",
        # AI Power
        "ON","WOLF","MPWR","AEHR","FORM",
        # AI Power Infra
        "VST","ETN","GEV","BE","CEG","NRG","EMR","OKLO",
        # Transformer Infra
        "VRT","HUBB","NVT","POWL","AYI","AMETEK","ROP",
        # AI Packaging
        "AJINY","AMKR","COHU","TSEM","KLIC","ONTO",
        # AI Compute
        "NVDA","AMD","AVGO","TSM","QCOM","ARM","INTC","ASML",
        "AMAT","KLAC","LRCX","TXN","ENTG","MCHP","MU","SNDK",
        # AI Networking
        "ALAB","CRDO","ANET","SMCI","CSCO","CLS","APH",
        # Healthcare
        "ISRG","MDT","SYK","ABT","BSX","EW","TMO",
        "DXCM","PODD","RMD",
        "LLY","MRNA","REGN","BMY","PFE","NVO","AZN","VRTX","GILD",
        # Defense
        "LMT","NOC","RTX","GD","KTOS","HII","LDOS","BAH","CACI",
        "SAIC","BWXT","AXON",
        # Precious Metals
        "GLD","SLV","NEM","GOLD","GFI","AEM","WPM","FNV","RGLD",
        # Utilities
        "NEE","DUK","D","SO","AEP","EXC","SRE","PEG","ED",
        # Uranium
        "URA","CCJ","NXE","UUUU","LEU","DNN",
        # Energy
        "KMI","WMB","OKE","XOM","CVX","COP","SLB",
        "HAL","BKR","OXY","DVN","EOG","MPC","VLO","PSX",
        # Copper
        "FCX","SCCO","CPER",
        # Staples
        "WMT","COST","PG","KO","PEP","MCD","PM","MO","HSY","MDLZ",
        # Generic / Mega Cap / Software
        "AAPL","MSFT","GOOGL","META","AMZN","TSLA","NFLX","PLTR",
        "SHOP","CRM","NOW","PANW","SNOW",
        # Legacy / Benchmarks
        "GLD","LMT","KMI","NVD","KTOS",
        "XLK","XLY","XLI","XLF","XLE","XLB","XLV","XLP","XLU","XLRE","XLC",
        "SPY","QQQ","IWM","DIA","VTV","VUG","USMV","HDV","RSP","MTUM","QUAL",
        "TLT","IEF","HYG","LQD","EEM",
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
    # ── AI Compute ────────────────────────────────────────────────────────────
    "NVDA":"ai_compute","AMD":"ai_compute","AVGO":"ai_compute","TSM":"ai_compute",
    "INTC":"ai_compute","QCOM":"ai_compute","ARM":"ai_compute","ASML":"ai_compute",
    "AMAT":"ai_compute","KLAC":"ai_compute","LRCX":"ai_compute","TXN":"ai_compute",
    "ENTG":"ai_compute",   # Entegris — specialty fab materials, semi supply chain
    "MCHP":"ai_compute",   # Microchip — mixed-signal/embedded, AI edge

    # ── AI Networking ─────────────────────────────────────────────────────────
    "ALAB":"ai_networking","CRDO":"ai_networking","ANET":"ai_networking","SMCI":"ai_networking",
    "CSCO":"ai_networking",  # Cisco — 400G/800G AI switching/routing
    "CLS":"ai_networking",   # Celestica — AI rack + CPO integration, contract mfg
    "APH":"ai_networking",   # Amphenol — connectors, data center cable, structural supplier

    # ── AI Optics (CPO Supply Chain) ──────────────────────────────────────────
    "LITE":"ai_optics","COHR":"ai_optics","POET":"ai_optics","CIEN":"ai_optics",
    "VIAV":"ai_optics","GLW":"ai_optics","MKSI":"ai_optics","ACLS":"ai_optics",
    "FN":"ai_optics",    # Fabrinet — contract mfg for LITE/COHR, CPO assembly
    "MTSI":"ai_optics",  # MACOM — InP/GaAs laser drivers upstream of LITE
    "IPAR":"ai_optics",  # IPG Photonics — high-power laser, upstream EML/CW

    # ── AI Memory ─────────────────────────────────────────────────────────────
    "MU":"ai_memory","SNDK":"ai_memory",

    # ── SiC / GaN Power Devices ───────────────────────────────────────────────
    "AEHR":"sic_gan","FORM":"sic_gan",

    # ── AI Power (ICs & Devices) ──────────────────────────────────────────────
    "ON":"ai_power","WOLF":"ai_power","MPWR":"ai_power",   # MPWR = AI server power ICs

    # ── AI Power Infrastructure ───────────────────────────────────────────────
    "VST":"ai_power_infra","ETN":"ai_power_infra","GEV":"ai_power_infra","BE":"ai_power_infra",
    "CEG":"ai_power_infra",   # Constellation Energy — nuclear baseload for AI DCs
    "NRG":"ai_power_infra",   # NRG Energy — generation capacity, AI power purchase
    "EMR":"ai_power_infra",   # Emerson — process automation + AI DC thermal mgmt
    "OKLO":"ai_power_infra",  # Oklo — SMR micro-reactor, Sam Altman backed, AI baseload

    # ── Transformer / Switchgear ──────────────────────────────────────────────
    "VRT":"transformer_infra","HUBB":"transformer_infra","NVT":"transformer_infra",
    "POWL":"transformer_infra",   # Powell Industries — switchgear specialist, AI DC
    "AYI":"transformer_infra",    # Acuity Brands — grid lighting/control
    "AMETEK":"transformer_infra", # Ametek — electronic instruments + power
    "ROP":"transformer_infra",    # Roper Tech — niche industrial tech

    # ── AI Packaging / Advanced Semi Assembly ─────────────────────────────────
    "AJINY":"ai_packaging","AMKR":"ai_packaging","COHU":"ai_packaging",
    "TSEM":"ai_packaging",  # Tower Semi — SiPh foundry for CPO
    "KLIC":"ai_packaging",  # Kulicke & Soffa — wire bonding, advanced packaging
    "ONTO":"ai_packaging",  # Onto Innovation — metrology/inspection for packaging

    # ── Healthcare Equipment ──────────────────────────────────────────────────
    "ISRG":"healthcare_eq","MDT":"healthcare_eq","SYK":"healthcare_eq",
    "ABT":"healthcare_eq","BSX":"healthcare_eq","EW":"healthcare_eq","TMO":"healthcare_eq",
    "DXCM":"healthcare_eq",  # DexCom — CGM, GLP-1 patient monitoring demand
    "PODD":"healthcare_eq",  # Insulet — OmniPod insulin pump, GLP-1 adjacent
    "RMD":"healthcare_eq",   # ResMed — sleep apnea; watch GLP-1 displacement thesis

    # ── Pharma / GLP-1 ───────────────────────────────────────────────────────
    "LLY":"pharma","MRNA":"pharma","REGN":"pharma","BMY":"pharma","PFE":"pharma",
    "NVO":"pharma",   # Novo Nordisk — GLP-1 originator (Ozempic/Wegovy), secular
    "AZN":"pharma",   # AstraZeneca — oncology + GLP-1 pipeline
    "VRTX":"pharma",  # Vertex — CFTR monopoly + non-opioid pain program
    "GILD":"pharma",  # Gilead — HIV/oncology, pipeline optionality

    # ── Defense / Aerospace ───────────────────────────────────────────────────
    "LMT":"defense","NOC":"defense","RTX":"defense","GD":"defense","KTOS":"defense",
    "HII":"defense","LDOS":"defense","BAH":"defense","CACI":"defense",
    "SAIC":"defense",  # SAIC — defense IT/cloud, NATO ramp beneficiary
    "BWXT":"defense",  # BWX Tech — nuclear reactors for subs + defense AI power
    "AXON":"defense",  # Axon Enterprise — AI body cam/Taser, law enforcement tech

    # ── Utilities / Power Grid ────────────────────────────────────────────────
    "NEE":"utilities","DUK":"utilities","D":"utilities","SO":"utilities",
    "AEP":"utilities",  # American Electric Power — AI grid corridor
    "EXC":"utilities",  # Exelon — nuclear utility, AI clean power
    "SRE":"utilities",  # Sempra — LNG + grid, AI-linked power demand
    "PEG":"utilities",  # Public Service Enterprise — nuclear+grid NJ/NE
    "ED":"utilities",   # Consolidated Edison — NY grid, regulated

    # ── Water ─────────────────────────────────────────────────────────────────
    "AWK":"water","WTRG":"water","CWT":"water",

    # ── Uranium / Nuclear ─────────────────────────────────────────────────────
    "URA":"uranium","CCJ":"uranium","NXE":"uranium","UUUU":"uranium",
    "LEU":"uranium",   # Centrus Energy — US uranium enrichment, strategic CHIPS-equivalent
    "DNN":"uranium",   # Denison Mines — explorer/developer, high leverage to uranium price

    # ── Precious Metals (Miners + Streamers + ETFs) ───────────────────────────
    "GLD":"precious_metals","GC=F":"precious_metals","SLV":"precious_metals","SI=F":"precious_metals",
    "NEM":"precious_metals","GOLD":"precious_metals","GFI":"precious_metals",
    "AEM":"precious_metals",   # Agnico Eagle — senior miner, low AISC, Q3/Q4 beast
    "WPM":"precious_metals",   # Wheaton Precious Metals — streamer, max leverage to gold/silver
    "FNV":"precious_metals",   # Franco-Nevada — royalty model, zero capex exposure
    "RGLD":"precious_metals",  # Royal Gold — royalty, defensive in Q4

    # ── Energy Infra / E&P / Oilfield Services ────────────────────────────────
    "KMI":"energy_infra","CL=F":"energy_infra","BZ=F":"energy_infra","USO":"energy_infra",
    "XOM":"energy_infra","CVX":"energy_infra","COP":"energy_infra","SLB":"energy_infra",
    "HAL":"energy_infra","BKR":"energy_infra","OXY":"energy_infra","DVN":"energy_infra",
    "EOG":"energy_infra","WMB":"energy_infra","OKE":"energy_infra",
    "MPC":"energy_infra","VLO":"energy_infra","PSX":"energy_infra",  # refining/downstream

    # ── Copper / Base Metals ──────────────────────────────────────────────────
    "FCX":"copper",   # Freeport-McMoRan — copper king, direct AI transformer chain
    "SCCO":"copper",  # Southern Copper — pure-play copper, LatAm production
    "HG=F":"copper",  # Copper futures
    "CPER":"copper",  # Copper ETF

    # ── Consumer Staples ──────────────────────────────────────────────────────
    "WMT":"staples","COST":"staples","PG":"staples","KO":"staples","PEP":"staples",
    "MCD":"staples","PM":"staples","MO":"staples","HSY":"staples","MDLZ":"staples",

    # ── Commodities (other) ───────────────────────────────────────────────────
    "ALI=F":"commodity_aluminum",
    "ZW=F":"commodity","ZC=F":"commodity","ZS=F":"commodity",

    # ── IHSG ──────────────────────────────────────────────────────────────────
    "^JKSE":"generic","EIDO":"generic",
    "BBCA.JK":"banking_ihsg","BBRI.JK":"banking_ihsg","BMRI.JK":"banking_ihsg",
    "ITMG.JK":"coal","ADRO.JK":"coal","PTBA.JK":"coal",
    "INCO.JK":"nickel","NCKL.JK":"nickel","ANTM.JK":"nickel",
    "SHIP.JK":"osv_hulu","LEAD.JK":"osv_hulu","OBMD.JK":"oil_services",
    "PSSI.JK":"dry_bulk_shipping","TPMA.JK":"dry_bulk_shipping",
    "AKRA.JK":"oil_distribution","MEDC.JK":"energy_infra",

    # ── Crypto ────────────────────────────────────────────────────────────────
    "BTC-USD":"depin_ai","ETH-USD":"depin_ai",
    "TAO22974-USD":"depin_ai","RNDR-USD":"depin_ai","FET-USD":"depin_ai",

    # ── Forex ─────────────────────────────────────────────────────────────────
    "EURUSD=X":"forex","GBPUSD=X":"forex","USDJPY=X":"forex","USDCHF=X":"forex",
    "USDCAD=X":"forex","AUDUSD=X":"forex","NZDUSD=X":"forex",
    "USDMXN=X":"forex","USDBRL=X":"forex","USDIDR=X":"forex","DX-Y.NYB":"forex",

    # ── Generic (Benchmarks + Mega Cap) ──────────────────────────────────────
    "SPY":"generic","QQQ":"generic","IWM":"generic","TLT":"generic",
    "AAPL":"generic","MSFT":"generic","GOOGL":"generic","META":"generic","AMZN":"generic",
    "TSLA":"generic","NFLX":"generic","PLTR":"generic","SHOP":"generic",
    "CRM":"generic","NOW":"generic","PANW":"generic","SNOW":"generic",
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
    "ai_compute": [
        "NVDA","AMD","AVGO","TSM","QCOM","ARM","INTC","ASML",
        "AMAT","KLAC","LRCX","TXN","ENTG","MCHP",
    ],
    "ai_networking": [
        "ALAB","CRDO","ANET","SMCI",
        "CSCO",   # Cisco — 400G/800G AI switching
        "CLS",    # Celestica — AI rack + CPO assembly
        "APH",    # Amphenol — connectors, DC cable
    ],
    "ai_memory": ["MU","SNDK"],
    "ai_optics": [
        "LITE","COHR","POET","MKSI","ACLS","CIEN","VIAV","GLW",
        "FN",     # Fabrinet — CPO contract manufacturing
        "MTSI",   # MACOM — InP/GaAs laser drivers
        "IPAR",   # IPG Photonics — high-power laser upstream
    ],
    "ai_power": ["ON","WOLF","MPWR","AEHR","FORM"],
    "sic_gan":  ["AEHR","FORM"],
    "ai_power_infra": [
        "VST","ETN","GEV","BE",
        "CEG",    # Constellation Energy — nuclear baseload
        "NRG",    # NRG Energy — generation capacity
        "EMR",    # Emerson — process automation/thermal
        "OKLO",   # Oklo — SMR micro-reactor
    ],
    "transformer_infra": [
        "VRT","HUBB","NVT",
        "POWL",   # Powell Industries — switchgear specialist
        "AYI","AMETEK","ROP",
    ],
    "ai_packaging": [
        "AJINY","AMKR","COHU","TSEM",
        "KLIC",   # Kulicke & Soffa — wire bonding
        "ONTO",   # Onto Innovation — metrology/inspection
    ],
    "healthcare_eq": [
        "ISRG","MDT","SYK","ABT","BSX","EW","TMO",
        "DXCM",   # DexCom — CGM, GLP-1 monitoring demand
        "PODD",   # Insulet — OmniPod insulin pump
        "RMD",    # ResMed — sleep apnea (GLP-1 displacement watch)
    ],
    "pharma": [
        "LLY","MRNA","REGN","BMY","PFE",
        "NVO",    # Novo Nordisk — GLP-1 originator (Ozempic/Wegovy)
        "AZN",    # AstraZeneca — oncology + GLP-1 pipeline
        "VRTX",   # Vertex — CFTR monopoly + non-opioid pain
        "GILD",   # Gilead — HIV/oncology
    ],
    "defense": [
        "LMT","NOC","RTX","GD","KTOS","HII","LDOS","BAH","CACI",
        "AXON",   # Axon Enterprise — AI public safety/law enforcement
        "SAIC",   # SAIC — defense IT/cloud
        "BWXT",   # BWX Tech — nuclear reactors for defense + AI power
    ],
    "precious_metals": [
        "GLD","SLV","NEM","GOLD","GFI",
        "AEM",    # Agnico Eagle — senior miner, low AISC
        "WPM",    # Wheaton Precious Metals — streamer, max gold/silver leverage
        "FNV",    # Franco-Nevada — royalty, zero capex model
        "RGLD",   # Royal Gold — royalty, Q4 defensive
    ],
    "utilities": [
        "NEE","DUK","D","SO","XLU",
        "AEP",    # American Electric Power — AI grid corridor
        "EXC",    # Exelon — nuclear utility
        "SRE",    # Sempra — LNG + grid
        "PEG",    # PSEG — nuclear + grid NJ
        "ED",     # Consolidated Edison — regulated NY
    ],
    "uranium": [
        "URA","CCJ","NXE","UUUU",
        "LEU",    # Centrus Energy — US enrichment, strategic
        "DNN",    # Denison Mines — explorer/developer
    ],
    "energy_infra": [
        "KMI","WMB","OKE","XOM","CVX","COP","SLB",
        "HAL","BKR","OXY","DVN","EOG",
        "MPC","VLO","PSX",   # downstream/refining
    ],
    "copper": [
        "FCX",    # Freeport-McMoRan — copper king
        "SCCO",   # Southern Copper — pure-play
        "HG=F","CPER",
    ],
    "staples": [
        "WMT","COST","PG","KO","PEP","MCD","PM","MO","HSY","MDLZ",
    ],
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

# ── Bottleneck Hints ──────────────────────────────────────────────────────────
# Tickers NOT yet in main universe but have confirmed/emerging bottleneck thesis.
# Displayed on Bottleneck page when ticker is absent from loaded prices.
# Format: sector → list of {ticker, name, why, quad_fit, source}
BOTTLENECK_HINTS: dict = {

    # ── AI Compute / Semi Equipment ───────────────────────────────────────────
    "ai_compute": [
        {"ticker":"ONTO","name":"Onto Innovation",
         "why":"Metrology/inspection for advanced packaging — every CoWoS chip needs ONTO's tools. Capacity constrained.",
         "quad_fit":["Q1","Q2"],"source":"Citrini CPO chain"},
        {"ticker":"ICHR","name":"Ichor Holdings",
         "why":"Gas delivery systems for semiconductor fabs. AMAT/LRCX cannot ship tools without ICHR's subsystems.",
         "quad_fit":["Q1","Q2"],"source":"Semi supply chain"},
        {"ticker":"COHU","name":"Cohu",
         "why":"Semiconductor test handlers. AI chip volume ramp = test capacity bottleneck. Underfollowed.",
         "quad_fit":["Q1","Q2"],"source":"AI packaging chain"},
        {"ticker":"ACMR","name":"ACM Research",
         "why":"Wet cleaning equipment for advanced nodes. China + global fab expansion. AMAT competitor in cleaning.",
         "quad_fit":["Q1","Q2"],"source":"Semi equipment"},
    ],

    # ── AI Optics / CPO Extended ──────────────────────────────────────────────
    "ai_optics": [
        {"ticker":"AAOI","name":"Applied Optoelectronics",
         "why":"Transceiver modules for hyperscale DC. Small cap, high leverage to 800G/1.6T data center buildout.",
         "quad_fit":["Q1","Q2"],"source":"CPO chain"},
        {"ticker":"FNSR","name":"Finisar (now COHR)",
         "why":"Fully absorbed into COHR. Track COHR for this exposure.",
         "quad_fit":["Q1","Q2"],"source":"Reference only"},
        {"ticker":"NPKI","name":"NeoPhotonics (acquired)",
         "why":"Absorbed by II-VI → COHR. Track COHR. But signals the CPO M&A wave continues.",
         "quad_fit":["Q1","Q2"],"source":"M&A reference"},
        {"ticker":"SIOL","name":"Sievert Optical / Sivers Semi (OTC)",
         "why":"Swedish InP laser maker — competing with LITE in EML space. Not US-listed, track via LITE.",
         "quad_fit":["Q1","Q2"],"source":"CPO bottleneck research"},
    ],

    # ── AI Networking ─────────────────────────────────────────────────────────
    "ai_networking": [
        {"ticker":"INFN","name":"Infinera",
         "why":"Optical networking for hyperscale backhaul. 800G coherent optics — acquired by Nokia 2024.",
         "quad_fit":["Q1","Q2"],"source":"Networking chain"},
        {"ticker":"VIAV","name":"Viavi Solutions",
         "why":"Network test/measurement for AI data centers. 800G testing bottleneck. Low profile, high leverage.",
         "quad_fit":["Q1","Q2"],"source":"AI networking"},
        {"ticker":"KEYS","name":"Keysight Technologies",
         "why":"T&M for AI chip validation + 800G/1.6T optical testing. Invisible picks-and-shovels.",
         "quad_fit":["Q1","Q2"],"source":"AI infra"},
    ],

    # ── AI Packaging ──────────────────────────────────────────────────────────
    "ai_packaging": [
        {"ticker":"UCTT","name":"Ultra Clean Holdings",
         "why":"Chemical delivery + precision cleaning for advanced fabs. CoWoS expansion = UCTT demand.",
         "quad_fit":["Q1","Q2"],"source":"Packaging chain"},
        {"ticker":"CAMT","name":"Camtek",
         "why":"Israeli inspection/metrology for advanced packaging. TSMC CoWoS = CAMT tools at every step.",
         "quad_fit":["Q1","Q2"],"source":"@dojjunn packaging chain"},
        {"ticker":"KLIC","name":"Kulicke & Soffa",
         "why":"Wire bonding + advanced packaging tools. 2.5D/3D packaging ramp = KLIC unit growth.",
         "quad_fit":["Q1","Q2"],"source":"Packaging bottleneck"},
    ],

    # ── AI Power Infrastructure ───────────────────────────────────────────────
    "ai_power_infra": [
        {"ticker":"CORZ","name":"Core Scientific",
         "why":"Bitcoin miner → AI compute hosting pivot. Already has large-scale power infra (miners need same inputs as AI DC).",
         "quad_fit":["Q1","Q2"],"source":"Aschenbrunner thesis"},
        {"ticker":"IREN","name":"IREN Limited",
         "why":"AI data center on 100% renewable. Owns power + compute = vertically integrated AI physical layer.",
         "quad_fit":["Q1","Q2"],"source":"Aschenbrunner thesis"},
        {"ticker":"APLD","name":"Applied Digital",
         "why":"Purpose-built AI cloud infra. Liquid-cooled high-density DCs designed from scratch for AI workloads.",
         "quad_fit":["Q1","Q2"],"source":"Aschenbrunner thesis"},
        {"ticker":"SMR","name":"NuScale Power",
         "why":"Small Modular Reactor — nuclear for AI DC baseload. Binary risk but structural thesis if SMR gets NRC approval.",
         "quad_fit":["Q1","Q2","Q3"],"source":"Nuclear AI power chain"},
    ],

    # ── Transformer / Switchgear ──────────────────────────────────────────────
    "transformer_infra": [
        {"ticker":"ABB","name":"ABB Ltd (ADR: ABBNY)",
         "why":"Swiss industrial giant — transformers, grid automation, EV charging. US ADR available. ETN's main global competitor.",
         "quad_fit":["Q2","Q3"],"source":"Grid bottleneck"},
        {"ticker":"SIEGY","name":"Siemens Energy (ADR)",
         "why":"Gas turbines + transformers. @dojjunn: gas turbines = next bottleneck after power infra. Siemens has 3-4yr order backlog.",
         "quad_fit":["Q2","Q3"],"source":"@dojjunn bottleneck chain"},
        {"ticker":"WLDN","name":"Willdan Group",
         "why":"Grid engineering services. Every transformer/switchgear install needs engineering firm. Small cap, high leverage.",
         "quad_fit":["Q2","Q3"],"source":"Grid services"},
    ],

    # ── Uranium / Nuclear ─────────────────────────────────────────────────────
    "uranium": [
        {"ticker":"BWXT","name":"BWX Technologies",
         "why":"Nuclear reactors for US Navy submarines + defense. CHIPS Act equivalent for nuclear. Also AI DC SMR candidate.",
         "quad_fit":["Q1","Q2","Q3"],"source":"Nuclear chain"},
        {"ticker":"SMR","name":"NuScale Power (NASDAQ: SMR)",
         "why":"Only NRC-approved SMR design in US. Binary: approved = 10x, delayed = dead. High risk/reward.",
         "quad_fit":["Q1","Q2"],"source":"SMR bottleneck"},
        {"ticker":"PALAF","name":"Paladin Energy (OTC)",
         "why":"Australian uranium miner. Langer Heinrich restart. Physical uranium supply bottleneck play.",
         "quad_fit":["Q2","Q3"],"source":"Uranium supply chain"},
        {"ticker":"UEC","name":"Uranium Energy Corp",
         "why":"US domestic uranium miner. In-situ recovery = fastest to ramp. Strategic US supply.",
         "quad_fit":["Q2","Q3"],"source":"Uranium supply"},
    ],

    # ── Precious Metals ───────────────────────────────────────────────────────
    "precious_metals": [
        {"ticker":"SILV","name":"SilverCrest Metals",
         "why":"High-grade silver-gold developer in Mexico. Acquisition target. Silver supply deficit structural.",
         "quad_fit":["Q3","Q4"],"source":"Silver bottleneck"},
        {"ticker":"MAG","name":"MAG Silver",
         "why":"High-grade silver producer. Juanicipio mine ramping. Pure silver play for Q3 defensive rotation.",
         "quad_fit":["Q3","Q4"],"source":"Silver supply chain"},
        {"ticker":"WPM","name":"Wheaton Precious Metals",
         "why":"Streaming model — zero mining risk, pure metal price leverage. Best vehicle for Q3/Q4 gold thesis.",
         "quad_fit":["Q3","Q4"],"source":"Hedgeye Q3 playbook"},
    ],

    # ── Copper ────────────────────────────────────────────────────────────────
    "copper": [
        {"ticker":"TECK","name":"Teck Resources",
         "why":"Canadian copper + metallurgical coal. QB2 copper mine ramping. M&A target (Glencore bid). Q2 commodity play.",
         "quad_fit":["Q2"],"source":"Copper supply chain"},
        {"ticker":"LUNMF","name":"Lundin Mining (OTC)",
         "why":"Pure-play copper/zinc miner. Cobre Panama restart catalyst. Underfollowed.",
         "quad_fit":["Q2"],"source":"Copper bottleneck"},
        {"ticker":"CMCL","name":"Caledonia Mining (AIM/NYSE)",
         "why":"Zimbabwe gold/copper miner. Small cap, high leverage to metal prices.",
         "quad_fit":["Q2","Q3"],"source":"EM commodity"},
    ],

    # ── Defense ───────────────────────────────────────────────────────────────
    "defense": [
        {"ticker":"RCAT","name":"Red Cat Holdings",
         "why":"Drone defense — Black Widow drones. US Army contract. Sub-$1B market cap with NATO drone demand.",
         "quad_fit":["Q2","Q3"],"source":"Defense drone chain"},
        {"ticker":"JOBY","name":"Joby Aviation",
         "why":"eVTOL air taxi — also US DoD contract for military transport. Dual-use aerospace bottleneck.",
         "quad_fit":["Q1","Q2"],"source":"Defense tech"},
        {"ticker":"PLTR","name":"Palantir Technologies",
         "why":"AI for defense/intelligence. Maven Smart System = US Army AI. Should not be labeled generic.",
         "quad_fit":["Q1","Q2","Q3"],"source":"Defense AI"},
    ],

    # ── Healthcare / GLP-1 Adjacent ───────────────────────────────────────────
    "healthcare_eq": [
        {"ticker":"HIMS","name":"Hims & Hers Health",
         "why":"GLP-1 compounding/telehealth. High risk (FDA compounding policy risk) but massive GLP-1 TAM exposure.",
         "quad_fit":["Q1","Q2"],"source":"GLP-1 chain"},
        {"ticker":"INVA","name":"Innoviva",
         "why":"Royalty on respiratory drugs + GLP-1 adjacent pipeline. Low-profile compounder.",
         "quad_fit":["Q3","Q4"],"source":"Pharma royalty"},
        {"ticker":"NTRA","name":"Natera",
         "why":"Liquid biopsy / cell-free DNA testing. Cancer early detection bottleneck. Pod 1 accelerating.",
         "quad_fit":["Q1","Q2","Q3"],"source":"Genomics bottleneck"},
    ],

    # ── Energy Infra ──────────────────────────────────────────────────────────
    "energy_infra": [
        {"ticker":"DINO","name":"HF Sinclair (née HollyFrontier)",
         "why":"Independent refiner. Crack spread leverage. Q2 stagflation = refining margin expansion.",
         "quad_fit":["Q2","Q3"],"source":"Energy refining"},
        {"ticker":"AM","name":"Antero Midstream",
         "why":"Appalachian natural gas gathering. LNG export demand = nat gas infrastructure bottleneck.",
         "quad_fit":["Q2","Q3"],"source":"Nat gas infrastructure"},
        {"ticker":"TRGP","name":"Targa Resources",
         "why":"Permian NGL gathering/processing. NGL demand from petrochemicals + LNG export. Q2 commodity play.",
         "quad_fit":["Q2"],"source":"NGL bottleneck"},
    ],

    # ── IHSG / Indonesia Specific ─────────────────────────────────────────────
    "banking_ihsg": [
        {"ticker":"BBNI.JK","name":"Bank BNI",
         "why":"State bank, underweight vs BBCA/BBRI. MSCI rebalance + foreign flow recovery = catch-up trade.",
         "quad_fit":["Q1","Q2"],"source":"IHSG banking rotation"},
        {"ticker":"BRIS.JK","name":"Bank BSI (Syariah)",
         "why":"Sharia banking growth. OJK incentives + halal economy narrative. Underfollowed by foreign funds.",
         "quad_fit":["Q1","Q2"],"source":"IHSG narrative"},
    ],
    "osv_hulu": [
        {"ticker":"WINS.JK","name":"Wintermar Offshore",
         "why":"OSV operator. Pertamina hulu spending = WINS revenue. Ricky2212 thesis core name.",
         "quad_fit":["Q2","Q3"],"source":"Ricky2212 hulu thesis"},
        {"ticker":"ELSA.JK","name":"Elnusa",
         "why":"Pertamina subsidiary for seismic/hulu services. Direct beneficiary of oil production target 1M bbl/day by 2030.",
         "quad_fit":["Q2","Q3"],"source":"Ricky2212 hulu thesis"},
    ],
}
