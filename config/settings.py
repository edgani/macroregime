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
    # Majors
    "BTC-USD":"Bitcoin","ETH-USD":"Ethereum","BNB-USD":"BNB","SOL-USD":"Solana",
    "XRP-USD":"Ripple","ADA-USD":"Cardano","AVAX-USD":"Avalanche",
    "DOT-USD":"Polkadot","MATIC-USD":"Polygon","LINK-USD":"Chainlink",
    # L1/L2 Ecosystems
    "DOGE-USD":"Dogecoin","LTC-USD":"Litecoin","ATOM-USD":"Cosmos",
    "NEAR-USD":"NEAR","APT-USD":"Aptos","ARB-USD":"Arbitrum",
    "OP-USD":"Optimism","SUI20947-USD":"Sui","INJ-USD":"Injective","SEI-USD":"SEI",
    # DeFi
    "AAVE-USD":"Aave","UNI7083-USD":"Uniswap","MKR-USD":"Maker",
    "LDO-USD":"Lido DAO","CRV-USD":"Curve","COMP5692-USD":"Compound",
    # AI / Data / DePIN
    "FET-USD":"Fetch.ai","TAO22974-USD":"TAO/Bittensor","RNDR-USD":"Render",
    "GRT6719-USD":"The Graph","OCEAN-USD":"Ocean Protocol","HNT-USD":"Helium",
    # RWA / Infrastructure
    "ONDO-USD":"Ondo Finance","POLYX-USD":"Polymesh",
    "TON11419-USD":"Toncoin","TIA22861-USD":"Celestia","PYTH-USD":"Pyth",
    # High Beta / Meme
    "WIF-USD":"dogwifhat","PEPE24478-USD":"Pepe","BONK-USD":"Bonk",
    "FLOKI-USD":"Floki","BRETT-USD":"Brett",
    # US-listed ETFs & Proxies
    "IBIT":"iShares Bitcoin ETF","FBTC":"Fidelity Bitcoin ETF","ETHA":"iShares Ethereum ETF",
    "MSTR":"MicroStrategy",
}

# ── IHSG / Indonesia ──────────────────────────────────────────────────────────
IHSG_UNIVERSE: dict = {
    "^JKSE":"IHSG Index","EIDO":"Indonesia ETF (USD)",
    # Banks (heavyweights)
    "BBCA.JK":"BCA","BBRI.JK":"BRI","BMRI.JK":"Mandiri","BBNI.JK":"BNI",
    "BRIS.JK":"BSI","BBTN.JK":"BTN","BNGA.JK":"CIMB Niaga","MEGA.JK":"Bank Mega","NISP.JK":"OCBC",
    # Coal / Energy
    "ADRO.JK":"Adaro","PTBA.JK":"Bukit Asam","ITMG.JK":"ITMG","HRUM.JK":"Harum",
    "INDY.JK":"Indika","AADI.JK":"Aadi","BUMI.JK":"Bumi Resources",
    "MEDC.JK":"Medco","PGEO.JK":"Pertamina Geothermal","AKRA.JK":"AKR","UNTR.JK":"United Tractors",
    # Metals / Mining
    "INCO.JK":"Vale Indonesia","MDKA.JK":"Merdeka","ANTM.JK":"Antam",
    "TINS.JK":"Timah","BRMS.JK":"Bumi Resources Min","NCKL.JK":"Trimegah Bangun",
    # Telco / Infrastructure
    "TLKM.JK":"Telkom","EXCL.JK":"XL Axiata","ISAT.JK":"Indosat",
    "JSMR.JK":"Jasa Marga","PGAS.JK":"PGN","WIKA.JK":"Wijaya Karya","PTPP.JK":"PP Persero",
    # Consumer Defensive
    "ICBP.JK":"Indofood CBP","INDF.JK":"Indofood","MYOR.JK":"Mayora",
    "KLBF.JK":"Kalbe","SIDO.JK":"Sido Muncul","ULTJ.JK":"Ultra Jaya","CMRY.JK":"Cisarua",
    # Consumer Cyclical
    "AMRT.JK":"Alfamart","ACES.JK":"Ace Hardware","MAPI.JK":"Mitra Adiperkasa",
    "ERAA.JK":"Erajaya","ASII.JK":"Astra","CPIN.JK":"Charoen Pokphand","JPFA.JK":"Japfa",
    # Property / Healthcare
    "CTRA.JK":"Ciputra","BSDE.JK":"BSD City","PWON.JK":"Pakuwon","SMRA.JK":"Summarecon",
    "HEAL.JK":"Hermina","MIKA.JK":"Mika","SILO.JK":"Siloam",
    # CPO / Agri
    "LSIP.JK":"London Sumatra","AALI.JK":"Astra Agro","SSMS.JK":"Sawit Sumbermas",
    "INKP.JK":"Indah Kiat","TKIM.JK":"Tjiwi Kimia","ESSA.JK":"Surya Esa",
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
    "transformer_infra": {"constraint":0.88,"Q1":0.70,"Q2":0.88,"Q3":0.80,"Q4":0.50},
    "depin_ai":          {"constraint":0.75,"Q1":1.70,"Q2":1.10,"Q3":0.30,"Q4":0.50},
}

TICKER_SECTOR: dict = {
    # AI Compute
    "NVDA":"ai_compute","AMD":"ai_compute","AVGO":"ai_compute","TSM":"ai_compute","INTC":"ai_compute",
    "MRVL":"ai_compute","QCOM":"ai_compute","MU":"ai_compute","ARM":"ai_compute","ASML":"ai_compute",
    "AMAT":"ai_compute","KLAC":"ai_compute","LRCX":"ai_compute","TXN":"ai_compute",
    # AI Networking
    "ALAB":"ai_networking","CRDO":"ai_networking","ANET":"ai_networking","SMCI":"ai_networking",
    # AI Optics
    "LITE":"ai_optics","COHR":"ai_optics","CIEN":"ai_optics","POET":"ai_optics","VIAV":"ai_optics","GLW":"ai_optics",
    # SiC/GaN Power
    "ON":"sic_gan","WOLF":"sic_gan","STM":"sic_gan","AEHR":"sic_gan","FORM":"sic_gan",
    # AI Power Infrastructure
    "VST":"ai_power_infra","CEG":"ai_power_infra","ETN":"ai_power_infra","NRG":"ai_power_infra","GEV":"ai_power_infra","EMR":"ai_power_infra",
    "VRT":"transformer_infra","HUBB":"transformer_infra","NVT":"transformer_infra","AYI":"transformer_infra","AMETEK":"transformer_infra","ROP":"transformer_infra",
    # AI Packaging
    "AMKR":"ai_packaging","TSEM":"ai_packaging",
    # Mega Cap Tech
    "AAPL":"generic","MSFT":"generic","GOOGL":"generic","META":"generic","AMZN":"generic",
    "TSLA":"generic","NFLX":"generic","ORCL":"generic","ADBE":"generic","INTU":"generic",
    # Software / Cloud
    "CRM":"generic","NOW":"generic","PANW":"generic","PLTR":"generic","SNOW":"generic",
    "SHOP":"generic","SQ":"generic","AFRM":"generic","TTD":"generic","RDDT":"generic",
    "CDNS":"generic","SNPS":"generic",
    # Financials
    "JPM":"generic","BAC":"generic","WFC":"generic","GS":"generic","MS":"generic",
    "BLK":"generic","KKR":"generic","BX":"generic","SCHW":"generic","HOOD":"generic",
    "COIN":"generic","V":"generic","MA":"generic","PYPL":"generic",
    # Healthcare
    "ISRG":"healthcare_eq","ABT":"healthcare_eq","BSX":"healthcare_eq","MDT":"healthcare_eq",
    "EW":"healthcare_eq","SYK":"healthcare_eq","TMO":"healthcare_eq",
    "LLY":"pharma","MRNA":"pharma","REGN":"pharma","BMY":"pharma","PFE":"pharma",
    "UNH":"generic","JNJ":"generic","MRK":"generic","ABBV":"generic",
    # Energy
    "XOM":"energy_infra","CVX":"energy_infra","COP":"energy_infra","SLB":"energy_infra",
    "HAL":"energy_infra","BKR":"energy_infra","OXY":"energy_infra","DVN":"energy_infra","EOG":"energy_infra",
    "KMI":"energy_infra","WMB":"energy_infra","OKE":"energy_infra","XLE":"energy_infra",
    # Materials / Mining
    "FCX":"generic","NEM":"precious_metals","GOLD":"precious_metals","CAT":"generic","DE":"generic",
    "GE":"generic","BA":"generic","UNP":"generic","CSX":"generic","NSC":"generic",
    # Defense
    "LMT":"defense","NOC":"defense","RTX":"defense","GD":"defense","KTOS":"defense",
    "HII":"defense","LDOS":"defense","BAH":"defense","CACI":"defense",
    # Utilities & Water
    "NEE":"utilities","DUK":"utilities","D":"utilities","SO":"utilities","XLU":"utilities",
    "AWK":"water","WTRG":"water","CWT":"water",
    # Uranium
    "URA":"uranium","CCJ":"uranium","NXE":"uranium","UUUU":"uranium",
    # Consumer Staples & Discretionary
    "WMT":"staples","COST":"staples","PG":"staples","KO":"staples","PEP":"staples",
    "MCD":"staples","MDLZ":"staples","PM":"staples","MO":"staples","GIS":"staples","K":"staples",
    "UBER":"generic","BKNG":"generic","CMG":"generic","HD":"generic","LOW":"generic",
    "TGT":"generic","NKE":"generic","DIS":"generic","ROST":"generic","TJX":"generic",
    "LEN":"generic","DHI":"generic","PHM":"generic","ETSY":"generic",
    # Precious Metals
    "GLD":"precious_metals","GC=F":"precious_metals","SLV":"precious_metals","SI=F":"precious_metals",
    # Energy Commodities
    "CL=F":"energy_infra","BZ=F":"energy_infra","NG=F":"energy_infra","USO":"energy_infra",
    # Benchmarks
    "SPY":"generic","QQQ":"generic","IWM":"generic","TLT":"generic","DIA":"generic",
    "VTV":"generic","VUG":"generic","RSP":"generic","MTUM":"generic","QUAL":"generic",
    "USMV":"generic","HDV":"generic","EEM":"generic","HYG":"generic","LQD":"generic",
    # Crypto instruments
    "TAO22974-USD":"depin_ai","RNDR-USD":"depin_ai","FET-USD":"depin_ai",
    "OCEAN-USD":"depin_ai","GRT6719-USD":"depin_ai","HNT-USD":"depin_ai",
    "MSTR":"generic","IBIT":"generic","FBTC":"generic","ETHA":"generic",
}

# ── Market Classification for Bottleneck Multi-Asset ─────────────────────────
MARKET_CLASSIFICATION: dict = {
    # US Stocks
    "SPY":"us_equity","QQQ":"us_equity","IWM":"us_equity","DIA":"us_equity",
    "XLK":"us_equity","XLY":"us_equity","XLI":"us_equity","XLF":"us_equity",
    "XLE":"us_equity","XLB":"us_equity","XLV":"us_equity","XLP":"us_equity",
    "XLU":"us_equity","XLRE":"us_equity","XLC":"us_equity",
    "VTV":"us_equity","VUG":"us_equity","USMV":"us_equity","HDV":"us_equity",
    "RSP":"us_equity","MTUM":"us_equity","QUAL":"us_equity","SIZE":"us_equity",
    # AI / Tech single stocks
    "NVDA":"us_equity","AMD":"us_equity","AVGO":"us_equity","TSM":"us_equity","INTC":"us_equity",
    "ALAB":"us_equity","CRDO":"us_equity","MRVL":"us_equity","ANET":"us_equity","SMCI":"us_equity",
    "LITE":"us_equity","COHR":"us_equity","CIEN":"us_equity","POET":"us_equity","VIAV":"us_equity","GLW":"us_equity",
    "ON":"us_equity","WOLF":"us_equity","STM":"us_equity",
    "VST":"us_equity","CEG":"us_equity","ETN":"us_equity","NRG":"us_equity","GEV":"us_equity","EMR":"us_equity",
    "AMKR":"us_equity","ASX":"us_equity","TSEM":"us_equity",
    "ISRG":"us_equity","ABT":"us_equity","BSX":"us_equity","MDT":"us_equity","EW":"us_equity","SYK":"us_equity",
    "LLY":"us_equity","MRNA":"us_equity","REGN":"us_equity","BMY":"us_equity","PFE":"us_equity",
    "LMT":"us_equity","RTX":"us_equity","NOC":"us_equity","GD":"us_equity","KTOS":"us_equity","HII":"us_equity","LDOS":"us_equity","BAH":"us_equity",
    "NEE":"us_equity","DUK":"us_equity","D":"us_equity","SO":"us_equity",
    "AWK":"us_equity","WTRG":"us_equity","CWT":"us_equity",
    "GLD":"us_equity","SLV":"us_equity","PPLT":"us_equity","GFI":"us_equity","NEM":"us_equity",
    "XOM":"us_equity","CVX":"us_equity","COP":"us_equity","SLB":"us_equity",
    "URA":"us_equity","CCJ":"us_equity","NXE":"us_equity","UUUU":"us_equity",
    "PG":"us_equity","KO":"us_equity","PEP":"us_equity","WMT":"us_equity","COST":"us_equity",
    "MKSI":"us_equity","ACLS":"us_equity","AEHR":"us_equity","FORM":"us_equity","COHU":"us_equity",
    "MPWR":"us_equity","RMBS":"us_equity","QCOM":"us_equity","MU":"us_equity",
    "APH":"us_equity","MCHP":"us_equity","ENTG":"us_equity",
    "KLIC":"us_equity","UCTT":"us_equity","CAMT":"us_equity",
    "ZBH":"us_equity","DXCM":"us_equity","PODD":"us_equity","RMD":"us_equity",
    "JNJ":"us_equity","ABBV":"us_equity","MRK":"us_equity","AZN":"us_equity","NVO":"us_equity",
    "AXON":"us_equity","PLTR":"us_equity","SAIC":"us_equity","BWXT":"us_equity",
    "AEP":"us_equity","EXC":"us_equity","SRE":"us_equity","PEG":"us_equity","ED":"us_equity",
    "AEM":"us_equity","WPM":"us_equity","FNV":"us_equity","RGLD":"us_equity",
    "OXY":"us_equity","MPC":"us_equity","VLO":"us_equity","PSX":"us_equity","KMI":"us_equity",
    "LEU":"us_equity","DNN":"us_equity","URG":"us_equity",
    "PM":"us_equity","MO":"us_equity","GIS":"us_equity","K":"us_equity","HSY":"us_equity","MDLZ":"us_equity",
    "HUBB":"us_equity","NVT":"us_equity","AYI":"us_equity","AMETEK":"us_equity","ROP":"us_equity","VRT":"us_equity",
    # Crypto TAO/DePIN
    "TAO22974-USD":"crypto","RNDR-USD":"crypto","FET-USD":"crypto","OCEAN-USD":"crypto","GRT6719-USD":"crypto","HNT-USD":"crypto",
    # Forex
    "EURUSD=X":"forex","GBPUSD=X":"forex","USDJPY=X":"forex","USDCHF=X":"forex",
    "USDCAD=X":"forex","AUDUSD=X":"forex","NZDUSD=X":"forex","USDSEK=X":"forex","USDNOK=X":"forex",
    "USDMXN=X":"forex","USDBRL=X":"forex","USDTRY=X":"forex","USDZAR=X":"forex",
    "USDIDR=X":"forex","USDSGD=X":"forex","USDINR=X":"forex","USDCNY=X":"forex","USDKRW=X":"forex",
    "USDTHB=X":"forex","USDPHP=X":"forex","USDMYR=X":"forex",
    "EURJPY=X":"forex","GBPJPY=X":"forex","AUDNZD=X":"forex","CADUSD=X":"forex",
    "DX-Y.NYB":"forex",
    # Commodities
    "GC=F":"commodity","SI=F":"commodity","PL=F":"commodity","PA=F":"commodity",
    "GLD":"commodity","SLV":"commodity","PPLT":"commodity",
    "CL=F":"commodity","BZ=F":"commodity","NG=F":"commodity","RB=F":"commodity","HO=F":"commodity",
    "USO":"commodity","UNG":"commodity","BNO":"commodity",
    "HG=F":"commodity","ALI=F":"commodity","ZNC=F":"commodity","CPER":"commodity","JJC":"commodity",
    "ZW=F":"commodity","ZC=F":"commodity","ZS=F":"commodity","ZO=F":"commodity",
    "KC=F":"commodity","SB=F":"commodity","CT=F":"commodity","CC=F":"commodity",
    "DBA":"commodity","WEAT":"commodity","CORN":"commodity","LBS=F":"commodity",
    # Crypto
    "BTC-USD":"crypto","ETH-USD":"crypto","BNB-USD":"crypto","SOL-USD":"crypto",
    "XRP-USD":"crypto","ADA-USD":"crypto","AVAX-USD":"crypto","DOT-USD":"crypto",
    "MATIC-USD":"crypto","LINK-USD":"crypto","DOGE-USD":"crypto","LTC-USD":"crypto",
    "ATOM-USD":"crypto","NEAR-USD":"crypto","APT-USD":"crypto","ARB-USD":"crypto",
    "OP-USD":"crypto","SUI-USD":"crypto","INJ-USD":"crypto",
    "IBIT":"crypto","FBTC":"crypto","ETHA":"crypto",
    # IHSG
    "^JKSE":"ihsg","EIDO":"ihsg",
    "BBCA.JK":"ihsg","BBRI.JK":"ihsg","BMRI.JK":"ihsg","TLKM.JK":"ihsg","ASII.JK":"ihsg",
    "UNVR.JK":"ihsg","ICBP.JK":"ihsg","INDF.JK":"ihsg","KLBF.JK":"ihsg",
    "ITMG.JK":"ihsg","ADRO.JK":"ihsg","PTBA.JK":"ihsg","HRUM.JK":"ihsg",
    "INCO.JK":"ihsg","MDKA.JK":"ihsg","ANTM.JK":"ihsg","NCKL.JK":"ihsg",
    "LSIP.JK":"ihsg","AALI.JK":"ihsg","SSMS.JK":"ihsg",
    "BSDE.JK":"ihsg","CTRA.JK":"ihsg","PWON.JK":"ihsg",
    "MYOR.JK":"ihsg","HMSP.JK":"ihsg",
}

# ── Quad → Market Direction (Long/Short bias per asset class) ────────────────
# Format: {quad: {market: "long" / "short" / "neutral"}}
QUAD_MARKET_DIRECTION: dict = {
    "Q1": {"us_equity":"long","forex":"neutral","commodity":"short","crypto":"long","ihsg":"long"},
    "Q2": {"us_equity":"long","forex":"long","commodity":"long","crypto":"neutral","ihsg":"long"},
    "Q3": {"us_equity":"short","forex":"short","commodity":"long","crypto":"short","ihsg":"short"},
    "Q4": {"us_equity":"short","forex":"short","commodity":"short","crypto":"short","ihsg":"short"},
}

# ── EM Recovery Signals (per quad transition) ────────────────────────────────
EM_RECOVERY_SIGNALS: dict = {
    "Q3→Q2": {
        "trigger": "Monthly Q2 inside Structural Q3 = EM commodity exporters early recovery",
        "best": ["EIDO","EWW","EWZ","EWC","NORW","EWA","USDMXN=X","USDBRL=X","AUDUSD=X"],
        "rationale": "Q2 monthly = commodity bid + growth rebound. EM commodity exporters (Brazil, Mexico, Indonesia, Australia) lead. USD bearish TREND = EM FX relief.",
        "confidence": 0.55,
    },
    "Q4→Q1": {
        "trigger": "Deflation → Goldilocks = MAX EM recovery setup",
        "best": ["EIDO","INDA","EWZ","EWW","EEM","VWO","USDMXN=X","USDBRL=X","USDZAR=X"],
        "rationale": "Q4→Q1 = growth re-acceleration + inflation contained + Fed easing. EM equities historically +25-40% in first 6M of Q1. Highest conviction EM long.",
        "confidence": 0.85,
    },
    "Q3→Q1": {
        "trigger": "Direct stagflation → goldilocks = EM selective recovery",
        "best": ["INDA","EIDO","EWS","EWT"],
        "rationale": "Rare direct transition. Requires CPI collapse + ISM rebound. Only high-quality EM (India, Indonesia, Singapore, Taiwan) recover. Commodity EM lags.",
        "confidence": 0.35,
    },
    "Q3→Q3": {
        "trigger": "Stagflation persistence = EM headwind continues",
        "best": [],
        "rationale": "EM non-commodity exporters under pressure. Only gold/precious metals EM (South Africa) and defensive EM (India) viable. Avoid Indonesia, Brazil, Mexico.",
        "confidence": 0.70,
    },
}

# ── Sector Buckets (for breadth scoring) ─────────────────────────────────────
US_BUCKETS: dict = {
    "Growth":        ["QQQ","VUG","AAPL","MSFT","NVDA","AMZN","META","GOOGL","NFLX","NOW","CRM","SNOW"],
    "Quality":       ["QUAL","LLY","UNH","COST","WMT","PG","KO","PEP","V","MA"],
    "Defensives":    ["XLP","XLU","XLV","WMT","KO","PEP","PG","JNJ","MRK","ABBV"],
    "Semis":         ["NVDA","AMD","AVGO","AMAT","MU","QCOM","TXN","INTC","KLAC","LRCX"],
    "Software_Cyber":["MSFT","ORCL","CRM","NOW","ADBE","PANW","SNOW","PLTR"],
    "Energy":        ["XLE","XOM","CVX","COP","SLB","HAL","BKR","OXY","DVN","EOG"],
    "Industrials":   ["XLI","CAT","DE","GE","LMT","NOC","RTX","UNP","CSX","NSC","BA"],
    "Financials":    ["XLF","JPM","BAC","GS","MS","BLK","V","MA","SCHW"],
    "AI_Infra":      ["NVDA","ETN","VST","VRT","GEV","LITE","COHR","ON"],
    "Brokers_Alt":   ["HOOD","COIN","SCHW","MS","GS","BLK","KKR","BX"],
}
IHSG_BUCKETS: dict = {
    "Banks":          ["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BRIS.JK","BBTN.JK"],
    "Coal_Energy":    ["AADI.JK","ADRO.JK","PTBA.JK","ITMG.JK","HRUM.JK","INDY.JK","BUMI.JK","MEDC.JK","PGEO.JK","AKRA.JK"],
    "Metals":         ["ANTM.JK","INCO.JK","MDKA.JK","TINS.JK","BRMS.JK"],
    "Telco_Infra":    ["TLKM.JK","EXCL.JK","ISAT.JK","JSMR.JK","PGAS.JK","UNTR.JK"],
    "Consumer_Def":   ["ICBP.JK","INDF.JK","MYOR.JK","KLBF.JK","SIDO.JK","ULTJ.JK"],
    "Consumer_Cyc":   ["AMRT.JK","ACES.JK","MAPI.JK","ERAA.JK","ASII.JK","CPIN.JK","JPFA.JK"],
    "Property_Health":["CTRA.JK","BSDE.JK","PWON.JK","SMRA.JK","HEAL.JK","MIKA.JK","SILO.JK"],
    "CPO_Agri":       ["AALI.JK","LSIP.JK","SSMS.JK","INKP.JK","TKIM.JK","ESSA.JK"],
}
FX_BUCKETS: dict = {
    "Majors":    ["EURUSD=X","GBPUSD=X","AUDUSD=X","NZDUSD=X","USDJPY=X","USDCHF=X","USDCAD=X"],
    "JPY_Cross": ["EURJPY=X","GBPJPY=X","AUDJPY=X"],
    "EM_FX":     ["USDMXN=X","USDBRL=X","USDTRY=X","USDZAR=X","USDIDR=X","USDINR=X","USDSGD=X"],
    "Commodity_FX": ["AUDUSD=X","USDCAD=X","USDNOK=X"],
}
COMMODITY_BUCKETS: dict = {
    "Precious":    ["GC=F","SI=F","PL=F","PA=F","GLD","SLV"],
    "Energy":      ["CL=F","BZ=F","NG=F","RB=F","HO=F","USO"],
    "Industrial":  ["HG=F","ALI=F","CPER"],
    "Agri_Softs":  ["ZC=F","ZW=F","ZS=F","KC=F","SB=F","CT=F","CC=F","DBA","WEAT","CORN"],
    "Nuclear":     ["URA","CCJ","NXE"],
}
CRYPTO_BUCKETS: dict = {
    "Majors":    ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD"],
    "L1_L2":     ["ADA-USD","AVAX-USD","ATOM-USD","NEAR-USD","APT-USD","ARB-USD","OP-USD","MATIC-USD","SUI20947-USD"],
    "DeFi":      ["AAVE-USD","UNI7083-USD","MKR-USD","LDO-USD","CRV-USD","COMP5692-USD"],
    "AI_Data":   ["FET-USD","TAO22974-USD","RNDR-USD","GRT6719-USD","OCEAN-USD"],
    "RWA_Infra": ["ONDO-USD","POLYX-USD","LINK-USD","TON11419-USD","INJ-USD","SEI-USD","TIA22861-USD","PYTH-USD"],
    "High_Beta": ["DOGE-USD","WIF-USD","PEPE24478-USD","BONK-USD","FLOKI-USD"],
    "ETFs":      ["IBIT","FBTC","ETHA"],
}
# MAG7 for concentration risk
MAG7 = ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA"]
