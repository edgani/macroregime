"""settings.py — ALL parameters. Zero hardcoded thresholds in engines.

Hedgeye GIP: 30 monthly data points, 90 quarterly.
Everything flows from this file.

v3.1 Major surgery:
- QUAD_ASSET_PERFORMANCE: complete rewrite aligned with Hedgeye ETF Pro Plus actual tickers
- TICKER_SECTOR + MARKET_CLASSIFICATION: added all missing Hedgeye ETFs
- BOTTLENECK_PROFILES: added housing, oil_services, steel, infra, precious_metals_miners
- COMMODITIES: added SLX, GRID, GDX, GDXJ, SIL, SILJ
- Q2 fix: removed "BTC (reflation)" from best — Hedgeye SHORTS crypto in Q2
- Q2 fix: TLT nuanced — add when 2s/10s/30s all bearish TREND, not default worst
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
    "INDPRO":  "Industrial Production",
    "RSAFS":   "Retail Sales",
    "PAYEMS":  "Nonfarm Payrolls",
    "UNRATE":  "Unemployment",
    "ICSA":    "Initial Claims",
    "HOUST":   "Housing Starts",
    "ISMNO":   "ISM Manufacturing",
}
FRED_INFLATION_SERIES = {
    "CPIAUCSL": "CPI",
    "CPILFESL": "Core CPI",
    "PPIACO":   "PPI",
    "T5YIE":    "5yr Breakeven",
    "T10YIE":   "10yr Breakeven",
    "DFII10":   "10yr TIPS",
}
FRED_POLICY_SERIES = {
    "FEDFUNDS": "Fed Funds",
    "DFF":      "Daily Fed Funds",
    "M2SL":     "M2 Money Supply",
}

# ── GIP Weights ───────────────────────────────────────────────────────────────
GROWTH_LEVEL_WEIGHTS = {
    "indpro_yoy":0.22,"retail_yoy":0.20,"payrolls_yoy":0.18,
    "housing_yoy":0.12,"ism_norm":0.15,"unrate_inv":0.07,"claims_inv":0.06
}
GROWTH_MOM_WEIGHTS = {
    "indpro_roc":0.28,"retail_roc":0.22,"payrolls_roc":0.18,
    "ism_delta":0.14,"unrate_delta":0.10,"claims_delta":0.08
}
INFLATION_LEVEL_WEIGHTS = {
    "cpi_yoy":0.28,"core_cpi_yoy":0.24,"breakeven_5y":0.18,
    "ppi_yoy":0.14,"oil_3m":0.10,"gold_3m":0.06
}
INFLATION_MOM_WEIGHTS = {
    "cpi_roc":0.30,"core_cpi_roc":0.26,"breakeven_delta":0.18,
    "oil_1m":0.14,"dxy_inv_1m":0.12
}
STRUCTURAL_WEIGHTS = {
    "growth_level":0.15, "growth_momentum":0.30,
    "inflation_level":0.20, "inflation_momentum":0.35,
}
MONTHLY_WEIGHTS = {
    "growth_level":0.10, "growth_momentum":0.40,
    "inflation_level":0.15, "inflation_momentum":0.35,
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

# ── Forex ─────────────────────────────────────────────────────────────────────
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

# ── Commodities ───────────────────────────────────────────────────────────────
COMMODITIES: dict = {
    # Precious Metals — Hedgeye core: SLV +143% since May 2025
    "GC=F":"Gold Futures","SI=F":"Silver Futures","PL=F":"Platinum Futures","PA=F":"Palladium Futures",
    "GLD":"Gold ETF","SLV":"Silver ETF","PPLT":"Platinum ETF",
    "GDX":"Gold Miners ETF","GDXJ":"Junior Gold Miners ETF",
    "SIL":"Global Silver Miners ETF","SILJ":"Junior Silver Miners ETF",
    "DUST":"Gold Miners Inverse 2x (hedge)",
    # Energy
    "CL=F":"WTI Crude Oil","BZ=F":"Brent Crude","NG=F":"Natural Gas",
    "RB=F":"RBOB Gasoline","HO=F":"Heating Oil",
    "USO":"Oil ETF","UNG":"Nat Gas ETF","BNO":"Brent Oil ETF",
    "OIH":"Oil Services ETF","XOP":"Oil & Gas E&P ETF",
    # Industrial Metals
    "HG=F":"Copper","ALI=F":"Aluminum","ZNC=F":"Zinc",
    "CPER":"Copper ETF","JJC":"iPath Copper",
    "SLX":"Steel ETF (VanEck)",
    # Infrastructure
    "GRID":"Smart Grid Infrastructure ETF",
    # Agriculture
    "ZW=F":"Wheat","ZC=F":"Corn","ZS=F":"Soybeans","ZO=F":"Oats",
    "KC=F":"Coffee","SB=F":"Sugar","CT=F":"Cotton","CC=F":"Cocoa",
    "DBA":"Agriculture ETF","WEAT":"Wheat ETF","CORN":"Corn ETF","LBS=F":"Lumber",
    # Nuclear
    "URA":"Uranium ETF","CCJ":"Cameco",
}

# ── Crypto ────────────────────────────────────────────────────────────────────
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
    "IBIT":"iShares Bitcoin ETF","FBTC":"Fidelity Bitcoin ETF","ETHA":"iShares Ethereum ETF",
    "MSTR":"MicroStrategy",
    # Hedgeye SHORT ideas (crypto equity)
    "MSTY":"YieldMax MSTR Option Income ETF (SHORT)",
    "BITS":"Global X Blockchain ETF (SHORT)",
    "BLOK":"Amplify Blockchain ETF (SHORT)",
    "WGMI":"Valkyrie Bitcoin Miners ETF (SHORT)",
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
    "TLKM.JK":"Telkom","EXCL.JK":"XL Axiata","ISAT.JK":"Indosat",
    "JSMR.JK":"Jasa Marga","PGAS.JK":"PGN","WIKA.JK":"Wijaya Karya","PTPP.JK":"PP Persero",
    "ICBP.JK":"Indofood CBP","INDF.JK":"Indofood","MYOR.JK":"Mayora",
    "KLBF.JK":"Kalbe","SIDO.JK":"Sido Muncul","ULTJ.JK":"Ultra Jaya","CMRY.JK":"Cisarua",
    "AMRT.JK":"Alfamart","ACES.JK":"Ace Hardware","MAPI.JK":"Mitra Adiperkasa",
    "ERAA.JK":"Erajaya","ASII.JK":"Astra","CPIN.JK":"Charoen Pokphand","JPFA.JK":"Japfa",
    "CTRA.JK":"Ciputra","BSDE.JK":"BSD City","PWON.JK":"Pakuwon","SMRA.JK":"Summarecon",
    "HEAL.JK":"Hermina","MIKA.JK":"Mika","SILO.JK":"Siloam",
    "LSIP.JK":"London Sumatra","AALI.JK":"Astra Agro","SSMS.JK":"Sawit Sumbermas",
    "INKP.JK":"Indah Kiat","TKIM.JK":"Tjiwi Kimia","ESSA.JK":"Surya Esa",
    "WINS.JK":"Wintermar OSV","LEAD.JK":"Logindo OSV","SHIP.JK":"Sillo FPSO","ELSA.JK":"Elnusa hulu",
    "SOCI.JK":"SOCI Mas tanker","BULL.JK":"Bull Armada","TMAS.JK":"Temas container","SMDR.JK":"Samudera Indo",
    "DSNG.JK":"Dharma Satya","TAPG.JK":"Triputra Agro","SGRO.JK":"Sampoerna Agro",
    "BEST.JK":"Bekasi Fajar","KIJA.JK":"Jababeka","DMAS.JK":"Puradelta",
}

# ── Bonds ─────────────────────────────────────────────────────────────────────
BONDS: dict = {
    "TLT":"20yr UST","IEF":"7-10yr UST","SHY":"1-3yr UST","GOVT":"All UST",
    "TIP":"TIPS (inflation-linked)","LTPZ":"Long TIPS",
    "LQD":"IG Corporate","HYG":"HY Corporate","JNK":"HY Bonds",
    "EMB":"EM USD Bonds","PCY":"EM Local Bonds",
    "BND":"Total Bond","AGG":"US Agg Bond",
}

# ── Core macro proxy tickers ──────────────────────────────────────────────────
MACRO_PROXIES: dict = {
    "SPY":"S&P500","QQQ":"Nasdaq","IWM":"Russell 2k","DIA":"Dow",
    "XLI":"Industrials","XLY":"Consumer Disc","XHB":"Homebuilders",
    "UUP":"USD ETF","GLD":"Gold","TLT":"Long Bond","CL=F":"WTI Oil","GC=F":"Gold Futures",
}

# ══════════════════════════════════════════════════════════════════════════════
# QUAD ASSET PERFORMANCE — HEDGEYE ACTUAL (ETF Pro Plus aligned)
# Source: Hedgeye ETF Pro Plus March-May 2026 updates + 27yr backtest
# ══════════════════════════════════════════════════════════════════════════════
QUAD_ASSET_PERFORMANCE: dict = {

    # ── Q1: GOLDILOCKS — Growth↑ Inflation↓ ────────────────────────────────
    # Hedgeye: "Broadest participation. Tech #1. Small caps confirm. Crypto risk-on."
    "Q1": {
        "best": [
            "XLK",   # Tech — #1 in Q1
            "XLY",   # Consumer Disc
            "XLI",   # Industrials
            "IWM",   # Small Caps — must confirm for healthy Q1
            "QQQ",   # Nasdaq
            "RSP",   # Equal Weight — breadth confirmation
            "QUAL",  # Quality
            "SLV",   # Silver — works in early Q1 (precious metals follow growth)
            "GLD",   # Gold — transitions well from Q4→Q1
            "JPXN",  # Japan — Goldilocks + Yen dynamics (ETF Pro Plus confirmed)
            "EIS",   # Israel — geopolitical discount (ETF Pro Plus confirmed)
            "GLIN",  # India — tech + growth EM
            "ITA",   # Defense — secular + geopolitical tailwind
            "IBIT",  # Bitcoin ETF — risk-on Q1
        ],
        "worst": [
            "GLD",   # Gold fades as growth accelerates and safety bid exits
            "XLU",   # Utilities — bond proxy, underperforms in Q1
            "XLP",   # Consumer Staples — defensive, lags
            "TLT",   # Long Bonds — yields rise with growth acceleration
            "XLV",   # Healthcare — defensive, lags cyclicals
            "HYG",   # Credit spreads tighten but HY lags
        ],
        "style": "Growth, Small Cap, High Beta, Quality — broadest participation. Equal-weight RSP must confirm.",
        "fx": "USD moderate weakness; AUD/NZD/CAD supportive; commodity FX benefit; EM FX relief; JPY could strengthen",
        "bonds": "Bearish — yields rise with growth acceleration. Short duration bias.",
        "sectors_overweight": ["XLK","XLY","XLI","XLF","IWM"],
        "sectors_underweight": ["XLU","XLP","XLV","TLT"],
        "monthly_adds": ["JPXN","EIS","ITA","GLIN","RSP"],
        "hedge": "BTAL (anti-beta) as drawdown hedge. DUST if metals overheated.",
        "note": "Q1 = max risk-on. Crypto works. Equal-weight breadth is the confirmation signal.",
    },

    # ── Q2: REFLATION / KNIFE FIGHTS — Growth↑ Inflation↑ ─────────────────
    # Hedgeye ETF Pro Plus March-May 2026: 43 ETFs, energy offense, international long
    # CRITICAL: Hedgeye SHORTS crypto in Q2. BTC NOT a Q2 long.
    # TLT: nuanced — ADD when 2s/10s/30s ALL signal bearish TREND (yields to fall)
    "Q2": {
        "best": [
            # ── Energy Offense (Hedgeye ETF Pro Plus confirmed) ──────────────
            "XLE",   # Energy Sector ETF — core Q2 long
            "OIH",   # Oil Services — operating leverage to commodity prices
            "BNO",   # Brent Oil ETF — direct Brent exposure
            "XOP",   # Oil & Gas E&P — commodity price leverage
            "DAR",   # Darling Ingredients — biofuel, energy adjacency (added April 2026)
            "MTDR",  # Matador Resources — oil E&P (added April 2026)
            # ── Industrials ──────────────────────────────────────────────────
            "XLI",   # Industrials — top US equity long. +11.4% since December add
            "XLB",   # Materials — commodity offense
            "CPER",  # Copper ETF — industrial metals, reflation
            "SLX",   # Steel ETF — infrastructure + industrial demand
            # ── Precious Metals — work in Q2 reflation ────────────────────────
            "SLV",   # Silver — +143% since May 2025. Monster performer. Dual demand (industrial + safe haven)
            "GLD",   # Gold — holds in early Q2 before yields bite
            "PPLT",  # Platinum — industrial precious metal
            "GDX",   # Gold Miners — leverage to gold
            "GDXJ",  # Junior Gold Miners — higher beta
            # ── Housing (Long Duration Equity Proxy) ─────────────────────────
            "ITB",   # iShares Home Construction — rate sensitivity play, long duration equity proxy
            # ── Fixed Income (nuanced) ────────────────────────────────────────
            "TLT",   # ADDED when 2s/10s/30s all bearish TREND — yields to fall thesis
            "LQD",   # IG Corporate — as inflation peaks, credit works
            # ── International (Hedgeye ETF Pro Plus confirmed longs) ──────────
            "JPXN",  # Japan — Goldilocks FX + Nikkei. +10.3% 1M, +37% Q1 2026
            "EIS",   # Israel — geopolitical discount + tech sector resilience. +21.8% since add
            "TUR",   # Turkey — Bullish TREND, improving macro dynamics. +10.3% since add
            "NORW",  # Norway — commodity FX + oil exposure
            "EWZ",   # Brazil — commodity exporter EM, Q2 tailwind
            "EWW",   # Mexico — commodity FX + nearshoring demand
            "EIDO",  # Indonesia — commodity exporter + EM recovery
            "GLIN",  # India — growth EM, tech + domestic demand
        ],
        "worst": [
            # ── Hedgeye SHORT BOOK Q2 (actual ETF Pro Plus) ──────────────────
            "MSTY",  # YieldMax MSTR — SHORT. +55% short-side return since Sep 2025
            "BITS",  # Global X Blockchain — SHORT
            "BLOK",  # Amplify Blockchain — SHORT
            "WGMI",  # Valkyrie Bitcoin Miners — SHORT
            "DESK",  # Remote work proxy — SHORT
            # ── Q2 Underperformers ────────────────────────────────────────────
            "XLU",   # Utilities — bond proxy, growth/inflation headwind
            "XLP",   # Consumer Staples — defensive, lags Q2
            "HYG",   # High Yield — credit spreads widen
            "IWM",   # Small Caps — REDUCED to minimum. TRR signals lower highs at ATH.
        ],
        "style": "Value, Cyclicals, Commodity Exposure, High Beta. International + Energy offense. Go Anywhere.",
        "fx": "Commodity FX outperform: AUD, CAD, NOK, MXN, BRL. USD mixed. Yen bearish (JPXN thesis). IDR under pressure.",
        "bonds": "Nuanced: SHORT duration as default. ADD TLT only when 2s/10s/30s all signal bearish TREND simultaneously.",
        "sectors_overweight": ["XLI","XLE","XLB","ITB","OIH"],
        "sectors_underweight": ["XLU","XLP","HYG","IWM"],
        "monthly_adds": ["OIH","BNO","XOP","ITB","TLT","JPXN","EIS","TUR","DAR","MTDR","SLV"],
        "monthly_removes": ["TXG","MPLX","GEL"],
        "hedge": "BTAL (anti-beta) for drawdowns. DUST if gold miners overextended.",
        "sizing_note": "Start minimum. Scale gradually. Max 3% per name. IWM = minimum allocation only.",
        "note": "Q2 KNIFE FIGHTS. Growth↑ + Infl↑. International longs diversify away from US concentration. Crypto = SHORT BOOK. TLT = add only on rates signal, not default.",
    },

    # ── Q3: STAGFLATION — Growth↓ Inflation↑ ──────────────────────────────
    # Hedgeye: "Most dangerous for longs. Gold #1. SLV monster. Defensive only."
    "Q3": {
        "best": [
            # ── Precious Metals — Q3 #1 asset class ──────────────────────────
            "SLV",   # Silver — +143% since May 2025. Q3/Q4 safe haven + industrial hedge
            "GLD",   # Gold — McCullough: "single best asset allocation in Q3"
            "PPLT",  # Platinum
            "GDX",   # Gold Miners
            "GDXJ",  # Junior Gold Miners
            "SIL",   # Silver Miners
            "SILJ",  # Junior Silver Miners
            # ── Defensives ────────────────────────────────────────────────────
            "XLV",   # Healthcare — Q3 best sector
            "XLP",   # Consumer Staples
            "XLU",   # Utilities
            # ── Fixed Income ─────────────────────────────────────────────────
            "TLT",   # Long Duration UST — flight to quality. Bullish TREND in Q3.
            "IEF",   # 7-10yr UST
            "LQD",   # IG Corporate — quality bid
            # ── Defense ──────────────────────────────────────────────────────
            "ITA",   # Aerospace & Defense — secular + geopolitical + Q3 safe haven
            # ── Infrastructure ────────────────────────────────────────────────
            "GRID",  # Smart Grid — secular, defensive growth
            # ── EM Commodity Exporters (selective) ───────────────────────────
            "EIDO",  # Indonesia — coal/nickel commodity EM
            "NORW",  # Norway — oil EM
            "EWZ",   # Brazil — commodity EM
        ],
        "worst": [
            "XLK",   # Tech — #1 short in Q3. Stagflation destroys multiples.
            "MAGS",  # Magnificent 7 proxy — concentrated short
            "XLY",   # Consumer Discretionary — growth-sensitive
            "IWM",   # Small Caps — high beta, credit sensitive
            "HYG",   # High Yield — credit spreads blow out
            "QQQ",   # Nasdaq — growth premium compresses
            "XLF",   # Financials — net interest margin squeeze + credit risk
            "MSTY",  # SHORT — crypto equity
            "BITS",  # SHORT — crypto equity
            "BLOK",  # SHORT — crypto equity
            "WGMI",  # SHORT — Bitcoin miners
        ],
        "style": "Low Beta, Dividend Yield, Defensive Quality, Min Volatility. Gold first. SLV second.",
        "fx": "USD bearish TREND (McCullough confirmed Apr 2026). Commodity FX mixed. EM: commodity exporters only.",
        "bonds": "Long duration UST bullish (flight to quality). TLT core hold. Watch breakevens for Q4 signal.",
        "sectors_overweight": ["XLV","XLP","XLU","GLD","SLV","ITA"],
        "sectors_underweight": ["XLK","XLY","IWM","XLF","HYG"],
        "monthly_adds": ["SLV","GDX","GDXJ","SIL","ITA","GRID","TLT"],
        "hedge": "BTAL (anti-beta). DUST as metals volatility hedge.",
        "note": "CURRENT STRUCTURAL QUAD (May 2026). Monthly Q2 overlay adds tactical energy/commodity offense. SLV +143% since May 2025 — do not underweight.",
    },

    # ── Q4: DEFLATION — Growth↓ Inflation↓ ────────────────────────────────
    # Hedgeye: "Most dangerous. Capital preservation first. TLT max long."
    "Q4": {
        "best": [
            "TLT",   # Long Duration UST — maximum long
            "IEF",   # 7-10yr UST
            "GLD",   # Gold — deflation flight to quality
            "SLV",   # Silver — precious metal safety
            "XLV",   # Healthcare — defensive
            "XLP",   # Consumer Staples — defensive
            "XLU",   # Utilities — low beta, yield
            "UUP",   # USD — flight to safety
            "BTAL",  # Anti-Beta ETF — maximum hedge vehicle
        ],
        "worst": [
            "XLK",   # Tech — multiple compression in deflation
            "XLE",   # Energy — demand collapse
            "XLY",   # Consumer Disc — discretionary spending crashes
            "HYG",   # HY Credit — credit stress
            "IWM",   # Small Caps — highest credit risk
            "MSTY",  # Crypto equity SHORT
            "BITS",  # Crypto SHORT
            "BTC-USD", # Bitcoin — risk-off, deflation
        ],
        "style": "Min Volatility, Low Beta, Dividend, Quality, Defensive. Capital preservation over return maximization.",
        "fx": "USD very bullish (flight to safety). Commodity FX crushed. EM brutal.",
        "bonds": "Very bullish — deflationary collapse. Maximum long TLT/IEF.",
        "sectors_overweight": ["XLV","XLP","XLU","TLT","GLD"],
        "sectors_underweight": ["XLK","XLE","HYG","IWM","XLF"],
        "monthly_adds": ["TLT","IEF","GLD","BTAL","USMV"],
        "hedge": "BTAL maximum position. DUST.",
        "note": "Q4 = most dangerous. Deflation = cash + bonds + gold + utilities only.",
    },
}

# ── Bottleneck Profiles (constraint × quad regime fitness) ───────────────────
BOTTLENECK_PROFILES: dict = {
    # AI / Tech
    "ai_compute":          {"constraint":0.90,"Q1":0.85,"Q2":0.70,"Q3":0.50,"Q4":0.30},
    "ai_networking":       {"constraint":0.85,"Q1":0.80,"Q2":0.75,"Q3":0.55,"Q4":0.35},
    "ai_optics":           {"constraint":0.92,"Q1":0.78,"Q2":0.72,"Q3":0.62,"Q4":0.40},
    "ai_power":            {"constraint":0.87,"Q1":0.70,"Q2":0.75,"Q3":0.65,"Q4":0.50},
    "ai_power_infra":      {"constraint":0.85,"Q1":0.65,"Q2":0.70,"Q3":0.70,"Q4":0.55},
    "ai_packaging":        {"constraint":0.80,"Q1":0.75,"Q2":0.70,"Q3":0.55,"Q4":0.35},
    # Healthcare / Pharma
    "healthcare_eq":       {"constraint":0.80,"Q1":0.65,"Q2":0.55,"Q3":0.85,"Q4":0.80},
    "pharma":              {"constraint":0.82,"Q1":0.60,"Q2":0.50,"Q3":0.80,"Q4":0.75},
    # Defense
    "defense":             {"constraint":0.82,"Q1":0.55,"Q2":0.65,"Q3":0.78,"Q4":0.62},
    # Utilities / Water
    "utilities":           {"constraint":0.75,"Q1":0.50,"Q2":0.45,"Q3":0.82,"Q4":0.86},
    "water":               {"constraint":0.80,"Q1":0.55,"Q2":0.50,"Q3":0.85,"Q4":0.86},
    # Precious Metals + Miners — KEY for Q3/Q4
    "precious_metals":     {"constraint":0.72,"Q1":0.70,"Q2":0.68,"Q3":0.88,"Q4":0.82},
    "precious_metals_miners": {"constraint":0.80,"Q1":0.65,"Q2":0.70,"Q3":0.85,"Q4":0.78},
    # Energy
    "energy_infra":        {"constraint":0.75,"Q1":0.55,"Q2":0.88,"Q3":0.75,"Q4":0.30},
    "oil_services":        {"constraint":0.78,"Q1":0.60,"Q2":0.90,"Q3":0.65,"Q4":0.25},
    "uranium":             {"constraint":0.85,"Q1":0.70,"Q2":0.80,"Q3":0.65,"Q4":0.50},
    # Industrial Metals
    "steel":               {"constraint":0.70,"Q1":0.65,"Q2":0.82,"Q3":0.55,"Q4":0.25},
    "coal":                {"constraint":0.60,"Q1":0.50,"Q2":0.80,"Q3":0.55,"Q4":0.25},
    "nickel":              {"constraint":0.70,"Q1":0.60,"Q2":0.82,"Q3":0.55,"Q4":0.30},
    "cpo_palm":            {"constraint":0.65,"Q1":0.55,"Q2":0.75,"Q3":0.60,"Q4":0.30},
    # Housing / Homebuilders — Q2 long duration equity proxy (Hedgeye: ITB add)
    "housing":             {"constraint":0.68,"Q1":0.72,"Q2":0.78,"Q3":0.45,"Q4":0.35},
    # Infrastructure / Grid
    "infrastructure":      {"constraint":0.75,"Q1":0.70,"Q2":0.72,"Q3":0.68,"Q4":0.55},
    # Consumer / Staples
    "staples":             {"constraint":0.55,"Q1":0.45,"Q2":0.40,"Q3":0.78,"Q4":0.82},
    # Semis
    "sic_gan":             {"constraint":0.88,"Q1":0.70,"Q2":0.75,"Q3":0.65,"Q4":0.45},
    # Indonesia-specific
    "osv_offshore":        {"constraint":0.82,"Q1":0.55,"Q2":0.80,"Q3":0.72,"Q4":0.30},
    "tanker_shipping":     {"constraint":0.75,"Q1":0.50,"Q2":0.82,"Q3":0.65,"Q4":0.25},
    # Generic fallback
    "generic":             {"constraint":0.50,"Q1":0.50,"Q2":0.50,"Q3":0.50,"Q4":0.50},
}

# ── Ticker → Sector Mapping ───────────────────────────────────────────────────
TICKER_SECTOR: dict = {
    # ── US Sectors / Factors ─────────────────────────────────────────────────
    "SPY":"generic","QQQ":"ai_compute","IWM":"generic","DIA":"generic","RSP":"generic",
    "XLK":"ai_compute","XLY":"generic","XLI":"energy_infra","XLF":"generic",
    "XLE":"energy_infra","XLB":"generic","XLV":"healthcare_eq","XLP":"staples",
    "XLU":"utilities","XLRE":"housing","XLC":"generic","XHB":"housing",
    "VTV":"generic","VUG":"generic","USMV":"generic","HDV":"generic",
    "MTUM":"generic","QUAL":"generic","SIZE":"generic",
    # ── Hedgeye ETF Pro Plus LONG universe ───────────────────────────────────
    "OIH":"oil_services",      # Oil Services — Q2 long
    "BNO":"energy_infra",      # Brent Oil ETF — Q2 long
    "XOP":"energy_infra",      # Oil & Gas E&P — Q2 long
    "ITB":"housing",           # Home Construction — Q2 long duration proxy
    "ITA":"defense",           # Aerospace & Defense — secular long
    "BTAL":"generic",          # Anti-Beta ETF — hedge vehicle
    "DUST":"precious_metals",  # Gold Miners Inverse — hedge
    # ── International ETFs (Hedgeye ETF Pro Plus) ─────────────────────────
    "JPXN":"generic",  # Japan — Goldilocks FX dynamics
    "EIS":"generic",   # Israel — geopolitical discount + tech
    "TUR":"generic",   # Turkey — Bullish TREND
    "NORW":"generic",  # Norway — commodity FX
    "EWZ":"generic",   # Brazil — commodity EM
    "EWW":"generic",   # Mexico — commodity FX + nearshoring
    "EIDO":"generic",  # Indonesia — commodity EM
    "GLIN":"generic",  # India — growth EM
    "UAE":"generic",   # UAE — Gulf Cooperation Council exposure
    "INDA":"generic",  # India large cap
    "EWT":"generic",   # Taiwan — tech EM
    "EWS":"generic",   # Singapore — quality EM
    # ── Precious Metals (KEY — SLV +143% since May 2025) ─────────────────
    "GLD":"precious_metals",
    "SLV":"precious_metals",
    "PPLT":"precious_metals",
    "GDX":"precious_metals_miners",
    "GDXJ":"precious_metals_miners",
    "SIL":"precious_metals_miners",
    "SILJ":"precious_metals_miners",
    "AEM":"precious_metals_miners",
    "WPM":"precious_metals_miners",
    "FNV":"precious_metals_miners",
    "RGLD":"precious_metals_miners",
    # ── Steel / Industrials Metals ────────────────────────────────────────
    "SLX":"steel",     # VanEck Steel ETF — Q2 industrial offense
    "CPER":"generic",  # Copper ETF
    "GRID":"infrastructure",  # Smart Grid — secular
    # ── Energy single stocks ──────────────────────────────────────────────
    "DAR":"energy_infra",   # Darling Ingredients — biofuel
    "MTDR":"energy_infra",  # Matador Resources — oil E&P
    "OXY":"energy_infra","MPC":"energy_infra","VLO":"energy_infra",
    "PSX":"energy_infra","KMI":"energy_infra",
    "XOM":"energy_infra","CVX":"energy_infra","COP":"energy_infra",
    "SLB":"oil_services","HAL":"oil_services","BKR":"oil_services",
    # ── Signal Strength Stocks (confirmed Hedgeye) ────────────────────────
    "ULS":"generic",   # UL Solutions — +46.5% Signal Strength Long
    "BRBR":"staples",  # Bellring Brands — Signal Strength Short (GLP-1 victim)
    # ── Hedgeye SHORT book (crypto equity) ───────────────────────────────
    "MSTY":"generic",  # YieldMax MSTR — short target
    "BITS":"generic",  # Global X Blockchain — short target
    "BLOK":"generic",  # Amplify Blockchain — short target
    "WGMI":"generic",  # Valkyrie Bitcoin Miners — short target
    "MAGS":"ai_compute",  # Magnificent 7 proxy — short in Q3
    # ── AI / Tech ─────────────────────────────────────────────────────────
    "NVDA":"ai_compute","AMD":"ai_compute","AVGO":"ai_compute",
    "TSM":"ai_compute","INTC":"ai_compute","ALAB":"ai_compute",
    "CRDO":"ai_networking","MRVL":"ai_compute","ANET":"ai_networking",
    "SMCI":"ai_compute","LITE":"ai_optics","COHR":"ai_optics",
    "CIEN":"ai_optics","POET":"ai_optics","VIAV":"ai_optics","GLW":"ai_optics",
    "ON":"sic_gan","WOLF":"sic_gan","STM":"sic_gan","MPWR":"ai_power",
    "VST":"ai_power_infra","CEG":"ai_power_infra","ETN":"ai_power_infra",
    "NRG":"ai_power_infra","GEV":"ai_power_infra","EMR":"ai_power_infra","VRT":"ai_power_infra",
    "AMKR":"ai_packaging","ASX":"ai_packaging","TSEM":"ai_packaging",
    "MKSI":"ai_optics","RMBS":"ai_compute","QCOM":"ai_compute","MU":"ai_compute",
    "APH":"ai_networking","MCHP":"ai_compute","ENTG":"ai_compute",
    "KLIC":"ai_packaging","UCTT":"ai_packaging","CAMT":"ai_compute",
    "PLTR":"defense","AXON":"defense","SAIC":"defense","BWXT":"defense",
    "LMT":"defense","RTX":"defense","NOC":"defense","GD":"defense","KTOS":"defense",
    "HII":"defense","LDOS":"defense","BAH":"defense",
    # ── Healthcare ────────────────────────────────────────────────────────
    "LLY":"pharma","MRNA":"pharma","REGN":"pharma","BMY":"pharma","PFE":"pharma",
    "JNJ":"pharma","ABBV":"pharma","MRK":"pharma","AZN":"pharma","NVO":"pharma",
    "ISRG":"healthcare_eq","ABT":"healthcare_eq","BSX":"healthcare_eq",
    "MDT":"healthcare_eq","EW":"healthcare_eq","SYK":"healthcare_eq",
    "ZBH":"healthcare_eq","DXCM":"healthcare_eq","PODD":"healthcare_eq","RMD":"healthcare_eq",
    # ── Utilities ─────────────────────────────────────────────────────────
    "NEE":"utilities","DUK":"utilities","D":"utilities","SO":"utilities",
    "AEP":"utilities","EXC":"utilities","SRE":"utilities","PEG":"utilities","ED":"utilities",
    "AWK":"water","WTRG":"water","CWT":"water",
    # ── Staples ───────────────────────────────────────────────────────────
    "PG":"staples","KO":"staples","PEP":"staples","WMT":"staples","COST":"staples",
    "PM":"staples","MO":"staples","GIS":"staples","K":"staples","HSY":"staples","MDLZ":"staples",
    # ── Industrials single stocks ─────────────────────────────────────────
    "HUBB":"infrastructure","NVT":"ai_power_infra","AYI":"infrastructure",
    "AMETEK":"infrastructure","ROP":"infrastructure",
    # ── Uranium ──────────────────────────────────────────────────────────
    "URA":"uranium","CCJ":"uranium","NXE":"uranium","UUUU":"uranium","LEU":"uranium",
    "DNN":"uranium","URG":"uranium",
    # ── Financials ────────────────────────────────────────────────────────
    "JPM":"generic","BAC":"generic","GS":"generic","MS":"generic",
    "BLK":"generic","V":"generic","MA":"generic","SCHW":"generic",
    # ── Crypto adjacent ──────────────────────────────────────────────────
    "MSTR":"generic","IBIT":"generic","FBTC":"generic","ETHA":"generic",
    "HOOD":"generic","COIN":"generic",
    "TAO22974-USD":"depin_ai","RNDR-USD":"depin_ai",
    "FET-USD":"depin_ai","OCEAN-USD":"depin_ai","GRT6719-USD":"depin_ai","HNT-USD":"depin_ai",
    # ── Forex ─────────────────────────────────────────────────────────────
    "EURUSD=X":"forex","GBPUSD=X":"forex","USDJPY=X":"forex","USDCHF=X":"forex",
    "USDCAD=X":"forex","AUDUSD=X":"forex","NZDUSD=X":"forex","USDSEK=X":"forex","USDNOK=X":"forex",
    "USDMXN=X":"forex","USDBRL=X":"forex","USDTRY=X":"forex","USDZAR=X":"forex",
    "USDIDR=X":"forex","USDSGD=X":"forex","USDINR=X":"forex","USDCNY=X":"forex","USDKRW=X":"forex",
    "USDTHB=X":"forex","USDPHP=X":"forex","USDMYR=X":"forex",
    "EURJPY=X":"forex","GBPJPY=X":"forex","AUDNZD=X":"forex","CADUSD=X":"forex",
    "DX-Y.NYB":"forex",
    # ── Commodities ───────────────────────────────────────────────────────
    "GC=F":"precious_metals","SI=F":"precious_metals","PL=F":"precious_metals","PA=F":"precious_metals",
    "CL=F":"energy_infra","BZ=F":"energy_infra","NG=F":"energy_infra",
    "RB=F":"energy_infra","HO=F":"energy_infra",
    "USO":"energy_infra","UNG":"energy_infra","BNO":"energy_infra",
    "HG=F":"generic","ALI=F":"generic","ZNC=F":"generic","CPER":"generic","JJC":"generic",
    "SLX":"steel",
    "GRID":"infrastructure",
    "ZW=F":"staples","ZC=F":"staples","ZS=F":"staples","ZO=F":"staples",
    "KC=F":"staples","SB=F":"staples","CT=F":"staples","CC=F":"staples",
    "DBA":"staples","WEAT":"staples","CORN":"staples","LBS=F":"generic",
}

# ── Market Classification (for Bottleneck + ETF Pro tab) ─────────────────────
MARKET_CLASSIFICATION: dict = {
    # US Equity
    "SPY":"us_equity","QQQ":"us_equity","IWM":"us_equity","DIA":"us_equity","RSP":"us_equity",
    "XLK":"us_equity","XLY":"us_equity","XLI":"us_equity","XLF":"us_equity",
    "XLE":"us_equity","XLB":"us_equity","XLV":"us_equity","XLP":"us_equity",
    "XLU":"us_equity","XLRE":"us_equity","XLC":"us_equity","XHB":"us_equity",
    "VTV":"us_equity","VUG":"us_equity","USMV":"us_equity","HDV":"us_equity",
    "MTUM":"us_equity","QUAL":"us_equity","SIZE":"us_equity",
    # Hedgeye ETF Pro Plus (US-traded, various exposures)
    "OIH":"us_equity","BNO":"commodity","XOP":"us_equity","ITB":"us_equity",
    "ITA":"us_equity","BTAL":"us_equity","DUST":"us_equity",
    "JPXN":"us_equity","EIS":"us_equity","TUR":"us_equity","NORW":"us_equity",
    "EWZ":"us_equity","EWW":"us_equity","EIDO":"us_equity","GLIN":"us_equity",
    "UAE":"us_equity","INDA":"us_equity","EWT":"us_equity","EWS":"us_equity",
    "GLD":"commodity","SLV":"commodity","PPLT":"commodity",
    "GDX":"us_equity","GDXJ":"us_equity","SIL":"us_equity","SILJ":"us_equity",
    "SLX":"us_equity","CPER":"commodity","GRID":"us_equity",
    "DAR":"us_equity","MTDR":"us_equity",
    "ULS":"us_equity","BRBR":"us_equity",
    "MSTY":"us_equity","BITS":"us_equity","BLOK":"us_equity","WGMI":"us_equity","MAGS":"us_equity",
    # AI / Tech single stocks
    "NVDA":"us_equity","AMD":"us_equity","AVGO":"us_equity","TSM":"us_equity","INTC":"us_equity",
    "ALAB":"us_equity","CRDO":"us_equity","MRVL":"us_equity","ANET":"us_equity","SMCI":"us_equity",
    "LITE":"us_equity","COHR":"us_equity","CIEN":"us_equity","POET":"us_equity","VIAV":"us_equity","GLW":"us_equity",
    "ON":"us_equity","WOLF":"us_equity","STM":"us_equity","MPWR":"us_equity",
    "VST":"us_equity","CEG":"us_equity","ETN":"us_equity","NRG":"us_equity","GEV":"us_equity",
    "EMR":"us_equity","VRT":"us_equity",
    "AMKR":"us_equity","ASX":"us_equity","TSEM":"us_equity",
    # Healthcare
    "LLY":"us_equity","MRNA":"us_equity","REGN":"us_equity","BMY":"us_equity","PFE":"us_equity",
    "JNJ":"us_equity","ABBV":"us_equity","MRK":"us_equity","AZN":"us_equity","NVO":"us_equity",
    "ISRG":"us_equity","ABT":"us_equity","BSX":"us_equity","MDT":"us_equity","EW":"us_equity","SYK":"us_equity",
    "ZBH":"us_equity","DXCM":"us_equity","PODD":"us_equity","RMD":"us_equity",
    # Defense
    "LMT":"us_equity","RTX":"us_equity","NOC":"us_equity","GD":"us_equity","KTOS":"us_equity",
    "HII":"us_equity","LDOS":"us_equity","BAH":"us_equity","PLTR":"us_equity","AXON":"us_equity",
    "SAIC":"us_equity","BWXT":"us_equity",
    # Utilities
    "NEE":"us_equity","DUK":"us_equity","D":"us_equity","SO":"us_equity",
    "AEP":"us_equity","EXC":"us_equity","SRE":"us_equity","PEG":"us_equity","ED":"us_equity",
    "AWK":"us_equity","WTRG":"us_equity","CWT":"us_equity",
    # Staples
    "PG":"us_equity","KO":"us_equity","PEP":"us_equity","WMT":"us_equity","COST":"us_equity",
    "PM":"us_equity","MO":"us_equity","GIS":"us_equity","K":"us_equity","HSY":"us_equity","MDLZ":"us_equity",
    # Precious metals stocks
    "AEM":"us_equity","WPM":"us_equity","FNV":"us_equity","RGLD":"us_equity","NEM":"us_equity","GFI":"us_equity",
    # Uranium
    "URA":"us_equity","CCJ":"us_equity","NXE":"us_equity","UUUU":"us_equity",
    "LEU":"us_equity","DNN":"us_equity","URG":"us_equity",
    # Energy
    "XOM":"us_equity","CVX":"us_equity","COP":"us_equity","SLB":"us_equity",
    "OXY":"us_equity","MPC":"us_equity","VLO":"us_equity","PSX":"us_equity","KMI":"us_equity",
    "DAR":"us_equity","MTDR":"us_equity",
    # Financials
    "JPM":"us_equity","BAC":"us_equity","GS":"us_equity","MS":"us_equity",
    "BLK":"us_equity","V":"us_equity","MA":"us_equity","SCHW":"us_equity",
    # Industrials
    "HUBB":"us_equity","NVT":"us_equity","AYI":"us_equity","AMETEK":"us_equity","ROP":"us_equity",
    "MKSI":"us_equity","APH":"us_equity","MCHP":"us_equity","ENTG":"us_equity",
    "KLIC":"us_equity","UCTT":"us_equity","CAMT":"us_equity","RMBS":"us_equity","QCOM":"us_equity",
    "DXCM":"us_equity","PODD":"us_equity",
    # Crypto (equity proxies + ETFs)
    "MSTR":"us_equity","IBIT":"us_equity","FBTC":"us_equity","ETHA":"us_equity",
    "HOOD":"us_equity","COIN":"us_equity",
    "MSTY":"us_equity","BITS":"us_equity","BLOK":"us_equity","WGMI":"us_equity",
    # Forex
    "EURUSD=X":"forex","GBPUSD=X":"forex","USDJPY=X":"forex","USDCHF=X":"forex",
    "USDCAD=X":"forex","AUDUSD=X":"forex","NZDUSD=X":"forex","USDSEK=X":"forex","USDNOK=X":"forex",
    "USDMXN=X":"forex","USDBRL=X":"forex","USDTRY=X":"forex","USDZAR=X":"forex",
    "USDIDR=X":"forex","USDSGD=X":"forex","USDINR=X":"forex","USDCNY=X":"forex","USDKRW=X":"forex",
    "USDTHB=X":"forex","USDPHP=X":"forex","USDMYR=X":"forex",
    "EURJPY=X":"forex","GBPJPY=X":"forex","AUDNZD=X":"forex","CADUSD=X":"forex","DX-Y.NYB":"forex",
    # Commodities
    "GC=F":"commodity","SI=F":"commodity","PL=F":"commodity","PA=F":"commodity",
    "CL=F":"commodity","BZ=F":"commodity","NG=F":"commodity","RB=F":"commodity","HO=F":"commodity",
    "USO":"commodity","UNG":"commodity","BNO":"commodity",
    "HG=F":"commodity","ALI=F":"commodity","ZNC=F":"commodity","CPER":"commodity","JJC":"commodity",
    "ZW=F":"commodity","ZC=F":"commodity","ZS=F":"commodity","ZO=F":"commodity",
    "KC=F":"commodity","SB=F":"commodity","CT=F":"commodity","CC=F":"commodity",
    "DBA":"commodity","WEAT":"commodity","CORN":"commodity","LBS=F":"commodity",
    "SLX":"commodity",
    # Crypto
    "BTC-USD":"crypto","ETH-USD":"crypto","BNB-USD":"crypto","SOL-USD":"crypto",
    "XRP-USD":"crypto","ADA-USD":"crypto","AVAX-USD":"crypto","DOT-USD":"crypto",
    "MATIC-USD":"crypto","LINK-USD":"crypto","DOGE-USD":"crypto","LTC-USD":"crypto",
    "ATOM-USD":"crypto","NEAR-USD":"crypto","APT-USD":"crypto","ARB-USD":"crypto",
    "OP-USD":"crypto","SUI20947-USD":"crypto","INJ-USD":"crypto","SEI-USD":"crypto",
    "AAVE-USD":"crypto","UNI7083-USD":"crypto","MKR-USD":"crypto","LDO-USD":"crypto",
    "FET-USD":"crypto","TAO22974-USD":"crypto","RNDR-USD":"crypto","GRT6719-USD":"crypto",
    "OCEAN-USD":"crypto","HNT-USD":"crypto","ONDO-USD":"crypto","POLYX-USD":"crypto",
    "TON11419-USD":"crypto","TIA22861-USD":"crypto","PYTH-USD":"crypto",
    "WIF-USD":"crypto","PEPE24478-USD":"crypto","BONK-USD":"crypto","FLOKI-USD":"crypto",
    # IHSG
    "^JKSE":"ihsg","EIDO":"ihsg",
    "BBCA.JK":"ihsg","BBRI.JK":"ihsg","BMRI.JK":"ihsg","BBNI.JK":"ihsg",
    "BRIS.JK":"ihsg","BBTN.JK":"ihsg","BNGA.JK":"ihsg","MEGA.JK":"ihsg","NISP.JK":"ihsg",
    "ADRO.JK":"ihsg","PTBA.JK":"ihsg","ITMG.JK":"ihsg","HRUM.JK":"ihsg",
    "INDY.JK":"ihsg","AADI.JK":"ihsg","BUMI.JK":"ihsg",
    "MEDC.JK":"ihsg","PGEO.JK":"ihsg","AKRA.JK":"ihsg","UNTR.JK":"ihsg",
    "INCO.JK":"ihsg","MDKA.JK":"ihsg","ANTM.JK":"ihsg","TINS.JK":"ihsg",
    "BRMS.JK":"ihsg","NCKL.JK":"ihsg",
    "TLKM.JK":"ihsg","EXCL.JK":"ihsg","ISAT.JK":"ihsg","JSMR.JK":"ihsg",
    "PGAS.JK":"ihsg","WIKA.JK":"ihsg","PTPP.JK":"ihsg",
    "ICBP.JK":"ihsg","INDF.JK":"ihsg","MYOR.JK":"ihsg","KLBF.JK":"ihsg",
    "SIDO.JK":"ihsg","ULTJ.JK":"ihsg","CMRY.JK":"ihsg",
    "AMRT.JK":"ihsg","ACES.JK":"ihsg","MAPI.JK":"ihsg","ERAA.JK":"ihsg",
    "ASII.JK":"ihsg","CPIN.JK":"ihsg","JPFA.JK":"ihsg",
    "CTRA.JK":"ihsg","BSDE.JK":"ihsg","PWON.JK":"ihsg","SMRA.JK":"ihsg",
    "HEAL.JK":"ihsg","MIKA.JK":"ihsg","SILO.JK":"ihsg",
    "LSIP.JK":"ihsg","AALI.JK":"ihsg","SSMS.JK":"ihsg","INKP.JK":"ihsg",
    "TKIM.JK":"ihsg","ESSA.JK":"ihsg",
    "WINS.JK":"ihsg","LEAD.JK":"ihsg","SHIP.JK":"ihsg","ELSA.JK":"ihsg",
    "SOCI.JK":"ihsg","BULL.JK":"ihsg","SMDR.JK":"ihsg","TMAS.JK":"ihsg",
    "DSNG.JK":"ihsg","TAPG.JK":"ihsg","SGRO.JK":"ihsg",
    "BEST.JK":"ihsg","KIJA.JK":"ihsg","DMAS.JK":"ihsg",
}

# ── Quad → Market Direction ───────────────────────────────────────────────────
QUAD_MARKET_DIRECTION: dict = {
    "Q1": {"us_equity":"long","forex":"neutral","commodity":"neutral","crypto":"long","ihsg":"long"},
    "Q2": {"us_equity":"long","forex":"long","commodity":"long","crypto":"short","ihsg":"long"},
    "Q3": {"us_equity":"short","forex":"short","commodity":"long","crypto":"short","ihsg":"short"},
    "Q4": {"us_equity":"short","forex":"short","commodity":"short","crypto":"short","ihsg":"short"},
}

# ── EM Recovery Signals ───────────────────────────────────────────────────────
EM_RECOVERY_SIGNALS: dict = {
    "Q3→Q2": {
        "trigger": "Monthly Q2 inside Structural Q3 = EM commodity exporters early recovery",
        "best": ["EIDO","EWW","EWZ","EWC","NORW","EWA","USDMXN=X","USDBRL=X","AUDUSD=X"],
        "rationale": "Q2 monthly = commodity bid + growth rebound. EM commodity exporters lead. USD bearish TREND = EM FX relief.",
        "confidence": 0.55,
    },
    "Q4→Q1": {
        "trigger": "Deflation → Goldilocks = MAX EM recovery setup",
        "best": ["EIDO","INDA","EWZ","EWW","EEM","VWO","USDMXN=X","USDBRL=X","USDZAR=X"],
        "rationale": "Q4→Q1 = growth re-acceleration + inflation contained + Fed easing. EM equities historically +25-40% in first 6M of Q1.",
        "confidence": 0.85,
    },
    "Q3→Q1": {
        "trigger": "Direct stagflation → goldilocks = EM selective recovery",
        "best": ["INDA","EIDO","EWS","EWT"],
        "rationale": "Rare direct transition. Only high-quality EM recover.",
        "confidence": 0.35,
    },
    "Q3→Q3": {
        "trigger": "Stagflation persistence = EM headwind continues",
        "best": [],
        "rationale": "EM non-commodity exporters under pressure. Defensive EM (India) only.",
        "confidence": 0.70,
    },
}

# ── Country Universe (50 Countries, GDP-weighted for Global Quad) ─────────────
COUNTRY_UNIVERSE: dict = {
    "USA":          ["SPY",     0.280, 0.5, 0.5],
    "China":        ["FXI",     0.120, 0.8, 0.7],
    "Japan":        ["JPXN",    0.060, 0.3, 0.4],   # JPXN = Hedgeye actual ETF
    "Germany":      ["EWG",     0.045, 0.5, 0.6],
    "India":        ["GLIN",    0.040, 0.4, 0.5],   # GLIN = Hedgeye actual (Goldman Sachs India)
    "UK":           ["EWU",     0.035, 0.4, 0.5],
    "France":       ["EWQ",     0.030, 0.5, 0.6],
    "Canada":       ["EWC",     0.025, 0.7, 0.3],
    "Korea":        ["EWT",     0.022, 0.5, 0.5],   # Using EWT (Taiwan) as proxy; EWY = Korea
    "Australia":    ["EWA",     0.020, 0.8, 0.3],
    "Brazil":       ["EWZ",     0.018, 0.8, 0.4],
    "Taiwan":       ["EWT",     0.018, 0.4, 0.5],
    "Mexico":       ["EWW",     0.015, 0.7, 0.4],
    "Indonesia":    ["EIDO",    0.012, 0.7, 0.5],
    "Saudi":        ["KSA",     0.012, 0.5, 0.8],
    "Norway":       ["NORW",    0.008, 0.9, 0.2],
    "Switzerland":  ["EWL",     0.010, 0.2, 0.3],
    "Sweden":       ["EWD",     0.008, 0.4, 0.5],
    "Hong_Kong":    ["EWH",     0.012, 0.6, 0.6],
    "UAE":          ["UAE",     0.008, 0.4, 0.7],   # UAE ETF — added March 2026
    "Israel":       ["EIS",     0.005, 0.3, 0.4],   # EIS — Hedgeye actual long
    "Turkey":       ["TUR",     0.006, 0.6, 0.8],   # TUR — Hedgeye actual long
    "Argentina":    ["ARGT",    0.006, 0.8, 0.9],
    "Chile":        ["ECH",     0.005, 0.7, 0.4],
    "Colombia":     ["GXG",     0.004, 0.7, 0.5],
    "Poland":       ["EPOL",    0.006, 0.5, 0.6],
    "South_Africa": ["EZA",     0.005, 0.8, 0.5],
    "Vietnam":      ["VNM",     0.004, 0.6, 0.5],
    "Egypt":        ["EGPT",    0.003, 0.7, 0.8],
    "Nigeria":      ["NGE",     0.003, 0.8, 0.7],
    "Peru":         ["EPU",     0.004, 0.7, 0.4],
    "Philippines":  ["EPHE",    0.004, 0.6, 0.5],
    "Malaysia":     ["EWM",     0.004, 0.5, 0.4],
    "Thailand":     ["THD",     0.004, 0.5, 0.5],
    "Pakistan":     ["PAK",     0.002, 0.7, 0.8],
    "New_Zealand":  ["ENZL",    0.003, 0.3, 0.3],
    "Singapore":    ["EWS",     0.005, 0.3, 0.4],
    "Denmark":      ["EDEN",    0.004, 0.3, 0.3],
    "Netherlands":  ["EWN",     0.004, 0.4, 0.5],
    "Italy":        ["EWI",     0.005, 0.6, 0.7],
    "Spain":        ["EWP",     0.004, 0.5, 0.6],
    "Russia":       ["ERUS",    0.010, 0.9, 0.7],
    "Hungary":      ["FLHU",    0.002, 0.6, 0.7],
    "Czech":        ["FLCZ",    0.002, 0.5, 0.5],
    "Greece":       ["GREK",    0.002, 0.7, 0.8],
    "Ireland":      ["EIRL",    0.002, 0.3, 0.3],
    "Finland":      ["EFNL",    0.002, 0.3, 0.3],
    "Portugal":     ["PGAL",    0.002, 0.5, 0.5],
    "Romania":      ["FLRO",    0.001, 0.5, 0.6],
}

# ── Sector Buckets ────────────────────────────────────────────────────────────
US_BUCKETS: dict = {
    "Growth":         ["QQQ","VUG","AAPL","MSFT","NVDA","AMZN","META","GOOGL","NFLX","NOW","CRM","SNOW"],
    "Quality":        ["QUAL","LLY","UNH","COST","WMT","PG","KO","PEP","V","MA"],
    "Defensives":     ["XLP","XLU","XLV","WMT","KO","PEP","PG","JNJ","MRK","ABBV"],
    "Semis":          ["NVDA","AMD","AVGO","AMAT","MU","QCOM","TXN","INTC","KLAC","LRCX"],
    "Energy":         ["XLE","OIH","XOP","BNO","XOM","CVX","COP","SLB","HAL","OXY","DAR","MTDR"],
    "Industrials":    ["XLI","CAT","DE","GE","LMT","NOC","RTX","UNP","CSX","NSC","BA"],
    "Financials":     ["XLF","JPM","BAC","GS","MS","BLK","V","MA","SCHW"],
    "AI_Infra":       ["NVDA","ETN","VST","VRT","GEV","LITE","COHR","ON"],
    "PreciousMetals": ["GLD","SLV","PPLT","GDX","GDXJ","SIL","SILJ","AEM","WPM","FNV"],
    "International":  ["JPXN","EIS","TUR","NORW","EWZ","EWW","EIDO","GLIN","UAE"],
    "Housing":        ["ITB","XHB","DHI","LEN","PHM","NVR"],
}
IHSG_BUCKETS: dict = {
    "Banks":          ["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BRIS.JK","BBTN.JK"],
    "Coal_Energy":    ["AADI.JK","ADRO.JK","PTBA.JK","ITMG.JK","HRUM.JK","INDY.JK","BUMI.JK"],
    "Metals":         ["ANTM.JK","INCO.JK","MDKA.JK","TINS.JK","BRMS.JK","NCKL.JK"],
    "Telco_Infra":    ["TLKM.JK","EXCL.JK","ISAT.JK","JSMR.JK","PGAS.JK","UNTR.JK"],
    "Consumer_Def":   ["ICBP.JK","INDF.JK","MYOR.JK","KLBF.JK","SIDO.JK","ULTJ.JK"],
    "Consumer_Cyc":   ["AMRT.JK","ACES.JK","MAPI.JK","ERAA.JK","ASII.JK","CPIN.JK","JPFA.JK"],
    "Property_Health":["CTRA.JK","BSDE.JK","PWON.JK","SMRA.JK","HEAL.JK","MIKA.JK","SILO.JK"],
    "CPO_Agri":       ["AALI.JK","LSIP.JK","SSMS.JK","INKP.JK","TKIM.JK","ESSA.JK","DSNG.JK","TAPG.JK","SGRO.JK"],
    "OSV_Hulu":       ["WINS.JK","LEAD.JK","SHIP.JK","ELSA.JK","MEDC.JK","ESSA.JK"],
    "Tanker_Ship":    ["SOCI.JK","BULL.JK","SMDR.JK","TMAS.JK"],
}
FX_BUCKETS: dict = {
    "Majors":       ["EURUSD=X","GBPUSD=X","AUDUSD=X","NZDUSD=X","USDJPY=X","USDCHF=X","USDCAD=X"],
    "JPY_Cross":    ["EURJPY=X","GBPJPY=X"],
    "EM_FX":        ["USDMXN=X","USDBRL=X","USDTRY=X","USDZAR=X","USDIDR=X","USDINR=X","USDSGD=X"],
    "Commodity_FX": ["AUDUSD=X","USDCAD=X","USDNOK=X"],
}
COMMODITY_BUCKETS: dict = {
    "Precious":    ["GC=F","SI=F","PL=F","PA=F","GLD","SLV"],
    "PreciousMFX": ["GDX","GDXJ","SIL","SILJ"],
    "Energy":      ["CL=F","BZ=F","NG=F","RB=F","HO=F","USO","BNO","OIH","XOP"],
    "Industrial":  ["HG=F","ALI=F","CPER","SLX"],
    "Agri_Softs":  ["ZC=F","ZW=F","ZS=F","KC=F","SB=F","CT=F","CC=F","DBA","WEAT","CORN"],
    "Nuclear":     ["URA","CCJ","NXE"],
}
CRYPTO_BUCKETS: dict = {
    "Majors":    ["BTC-USD","ETH-USD","SOL-USD","BNB-USD","XRP-USD"],
    "L1_L2":     ["ADA-USD","AVAX-USD","ATOM-USD","NEAR-USD","APT-USD","ARB-USD","OP-USD","MATIC-USD"],
    "DeFi":      ["AAVE-USD","UNI7083-USD","MKR-USD","LDO-USD","CRV-USD","COMP5692-USD"],
    "AI_Data":   ["FET-USD","TAO22974-USD","RNDR-USD","GRT6719-USD","OCEAN-USD"],
    "RWA_Infra": ["ONDO-USD","POLYX-USD","LINK-USD","INJ-USD","SEI-USD","TIA22861-USD","PYTH-USD"],
    "High_Beta": ["DOGE-USD","WIF-USD","PEPE24478-USD","BONK-USD","FLOKI-USD"],
    "ETFs":      ["IBIT","FBTC","ETHA"],
    "Shorts":    ["MSTY","BITS","BLOK","WGMI"],  # Hedgeye short targets
}

# ── MAG7 ──────────────────────────────────────────────────────────────────────
MAG7 = ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA"]
