"""settings.py — All runtime parameters. Zero hardcoded thresholds in engines.

Philosophy: every numeric constant that affects signal output lives here.
Change here → entire system adapts. No hunting through engine files.
"""
from __future__ import annotations
import os

# ---------------------------------------------------------------------------
# API keys (from environment or .streamlit/secrets.toml)
# ---------------------------------------------------------------------------
FRED_API_KEY: str = os.environ.get("FRED_API_KEY", "")

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
PRICE_HISTORY_DAYS: int  = 756   # ~3 years — enough for TAIL Hurst
FRED_HISTORY_MONTHS: int = 36    # 3 years of monthly macro data
CACHE_TTL_SECONDS: int   = 3600  # 1 hour price cache
SNAPSHOT_PATH: str       = ".cache/snapshot.pkl"
HISTORY_PATH: str        = ".cache/history"

# ---------------------------------------------------------------------------
# GIP Model — Growth inputs (monthly, high-frequency)
# These match Hedgeye's ~30 monthly data points
# ---------------------------------------------------------------------------
FRED_GROWTH_SERIES: dict = {
    "INDPRO":  "Industrial Production",
    "RSAFS":   "Retail Sales (Advance)",
    "PAYEMS":  "Total Nonfarm Payrolls",
    "UNRATE":  "Unemployment Rate",
    "ICSA":    "Initial Claims (Weekly)",
    "HOUST":   "Housing Starts",
    "KCFSI":   "KC Fed Financial Stress",   # optional
    "UMCSENT": "U Michigan Sentiment",       # optional
}
FRED_INFLATION_SERIES: dict = {
    "CPIAUCSL": "CPI All Items",
    "CPILFESL": "CPI Core (ex Food+Energy)",
    "PPIACO":   "PPI All Commodities",
    "T5YIE":    "5yr Breakeven Inflation",
    "T10YIE":   "10yr Breakeven Inflation",
    "DFII10":   "10yr TIPS Real Yield",
}
FRED_POLICY_SERIES: dict = {
    "FEDFUNDS": "Federal Funds Rate",
    "DFF":      "Daily Fed Funds",
    "M2SL":     "M2 Money Supply",
}
FRED_LEADING_SERIES: dict = {
    "KCFSI":   "KC Fed Financial Stress",
    "BAMLH0A0HYM2": "HY OAS Spread",      # optional Bloomberg-derived
}

# ISM threshold (neutral = 50)
ISM_NEUTRAL: float = 50.0

# ---------------------------------------------------------------------------
# GIP weights — data-driven calibration
# Hedgeye: RoC (momentum/second derivative) dominates over level
# ---------------------------------------------------------------------------
GROWTH_LEVEL_WEIGHTS: dict = {
    "indpro_yoy":     0.22,
    "retail_yoy":     0.20,
    "payrolls_yoy":   0.18,
    "housing_yoy":    0.12,
    "ism_norm":       0.15,
    "unrate_inv":     0.07,
    "claims_inv":     0.06,
}
GROWTH_MOM_WEIGHTS: dict = {
    "indpro_roc":     0.28,
    "retail_roc":     0.22,
    "payrolls_roc":   0.18,
    "ism_delta":      0.14,
    "unrate_delta":   0.10,
    "claims_delta":   0.08,
}
INFLATION_LEVEL_WEIGHTS: dict = {
    "cpi_yoy":        0.28,
    "core_cpi_yoy":   0.24,
    "breakeven_5y":   0.18,
    "ppi_yoy":        0.14,
    "oil_3m":         0.10,
    "gold_3m":        0.06,
}
INFLATION_MOM_WEIGHTS: dict = {
    "cpi_roc":        0.30,
    "core_cpi_roc":   0.26,
    "breakeven_delta": 0.18,
    "oil_1m":         0.14,
    "dxy_inv_1m":     0.12,
}

# Structural quad weights (quarterly climate)
STRUCTURAL_WEIGHTS: dict = {
    "growth_level":       0.20,
    "growth_momentum":    0.40,   # RoC dominant per Hedgeye
    "inflation_level":    0.10,
    "inflation_momentum": 0.30,
}
# Monthly quad weights (weather overlay)
MONTHLY_WEIGHTS: dict = {
    "growth_level":       0.15,
    "growth_momentum":    0.50,
    "inflation_level":    0.10,
    "inflation_momentum": 0.50,
}
# Policy contribution to quad score (small — Hedgeye says "front-run policy via G+I")
POLICY_WEIGHT_STRUCTURAL: float = 0.12
POLICY_WEIGHT_MONTHLY:    float = 0.10

# ---------------------------------------------------------------------------
# Risk Range — Hurst Rescaled Range
# ---------------------------------------------------------------------------
RR_TRADE_LOOKBACK:  int   = 15    # bars
RR_TREND_LOOKBACK:  int   = 63    # bars (~3 months)
RR_TAIL_LOOKBACK:   int   = 252   # bars (~1 year)
RR_TRADE_SIGMA:     float = 1.5   # base sigma multiplier
RR_TREND_SIGMA:     float = 2.0
RR_TAIL_SIGMA:      float = 2.8
RR_HURST_SCALE:     float = 1.0   # how much H stretches range

# ---------------------------------------------------------------------------
# Global quad
# ---------------------------------------------------------------------------
# Countries: (etf, region, commodity_sensitivity, usd_sensitivity)
COUNTRY_UNIVERSE: dict = {
    "USA":          ("SPY",  "americas", 0.20, 1.00),
    "Mexico":       ("EWW",  "americas", 0.40, 0.85),
    "Canada":       ("EWC",  "americas", 0.55, 0.80),
    "Argentina":    ("ARGT", "americas", 0.35, 0.90),
    "Brazil":       ("EWZ",  "americas", 0.65, 0.75),
    "Chile":        ("ECH",  "americas", 0.60, 0.75),
    "Colombia":     ("GXG",  "americas", 0.65, 0.70),
    "Hong_Kong":    ("EWH",  "asia",     0.15, 0.95),
    "Japan":        ("EWJ",  "asia",     0.20, 0.80),
    "Korea":        ("EWY",  "asia",     0.30, 0.75),
    "Taiwan":       ("EWT",  "asia",     0.15, 0.70),
    "China":        ("MCHI", "asia",     0.30, 0.65),
    "India":        ("INDA", "asia",     0.25, 0.70),
    "Indonesia":    ("EIDO", "asia",     0.70, 0.55),
    "Australia":    ("EWA",  "asia",     0.65, 0.70),
    "Vietnam":      ("VNM",  "asia",     0.40, 0.65),
    "Germany":      ("EWG",  "europe",   0.35, 0.70),
    "UK":           ("EWU",  "europe",   0.30, 0.75),
    "France":       ("EWQ",  "europe",   0.30, 0.70),
    "Switzerland":  ("EWL",  "europe",   0.20, 0.75),
    "Norway":       ("NORW", "europe",   0.75, 0.80),
    "Sweden":       ("EWD",  "europe",   0.35, 0.75),
    "Poland":       ("EPOL", "europe",   0.40, 0.65),
    "Turkey":       ("TUR",  "europe",   0.35, 0.60),
    "Israel":       ("EIS",  "mideast",  0.20, 0.80),
    "UAE":          ("UAE",  "mideast",  0.80, 0.65),
    "Saudi":        ("KSA",  "mideast",  0.85, 0.65),
    "South_Africa": ("EZA",  "em",       0.55, 0.65),
    "Nigeria":      ("NGE",  "em",       0.70, 0.60),
    "Egypt":        ("EGPT", "em",       0.45, 0.60),
    "Peru":         ("EPU",  "americas", 0.60, 0.70),
}

# ---------------------------------------------------------------------------
# Universe — Full but lazy-loaded per asset class
# ---------------------------------------------------------------------------
# US Sectors (for bottleneck scanner + rotation)
US_SECTORS: dict = {
    "XLK": "Technology", "XLY": "Consumer Disc", "XLI": "Industrials",
    "XLF": "Financials", "XLE": "Energy", "XLB": "Materials",
    "XLV": "Healthcare", "XLP": "Consumer Staples", "XLU": "Utilities",
    "XLRE": "Real Estate", "XLC": "Communication",
}
US_FACTORS: dict = {
    "IWM": "Small Cap", "QQQ": "Nasdaq", "SPY": "S&P500", "DIA": "Dow",
    "VTV": "Value", "VUG": "Growth", "USMV": "Min Vol", "HDV": "High Div",
    "VXF": "Extended Mkt",
}
FOREX_PAIRS: list = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCAD=X", "AUDUSD=X",
    "USDCHF=X", "NZDUSD=X", "USDSGD=X", "USDIDR=X",  # IDR for IHSG context
    "DX-Y.NYB",  # DXY index
]
COMMODITIES: dict = {
    "GC=F": "Gold", "SI=F": "Silver", "CL=F": "WTI Oil", "BZ=F": "Brent Oil",
    "NG=F": "Nat Gas", "HG=F": "Copper", "ZW=F": "Wheat", "ZC=F": "Corn",
    "ZS=F": "Soybeans", "GLD": "Gold ETF", "SLV": "Silver ETF",
    "USO": "Oil ETF", "DBA": "Agriculture",
}
CRYPTO: dict = {
    "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum", "SOL-USD": "Solana",
    "BNB-USD": "BNB", "XRP-USD": "Ripple", "DOGE-USD": "Dogecoin",
    "ADA-USD": "Cardano", "AVAX-USD": "Avalanche",
}
IHSG_TICKERS: dict = {
    "^JKSE":  "IHSG Index",
    "EIDO":   "Indonesia ETF (USD)",
    # Note: Individual IDX tickers require Indonesian broker API
    # IHSG regime derived from EIDO + JKSE + macro context
}
BONDS: dict = {
    "TLT": "20yr UST ETF", "IEF": "7-10yr UST ETF", "SHY": "1-3yr UST ETF",
    "LQD": "IG Credit", "HYG": "HY Credit", "EMB": "EM Bonds",
    "TIP": "TIPS ETF",
}
MACRO_PROXIES: dict = {
    "SPY": "S&P500", "IWM": "Russell 2000", "XLI": "Industrials",
    "XLY": "Consumer Disc", "XHB": "Homebuilders", "UUP": "USD ETF",
    "GLD": "Gold", "TLT": "Long Bond",
}

# ---------------------------------------------------------------------------
# Quad playbook — backtested asset class performance by quad
# Source: Hedgeye 27yr backtest documentation
# ---------------------------------------------------------------------------
QUAD_ASSET_PERFORMANCE: dict = {
    "Q1": {  # Goldilocks: Growth ↑, Inflation ↓
        "best":  ["US Equities", "Tech (XLK)", "Consumer Disc (XLY)", "Industrials (XLI)", "Credit"],
        "worst": ["Gold", "Utilities (XLU)", "Consumer Staples (XLP)", "Long Bonds"],
        "style": ["Growth", "Small Cap", "High Beta", "Quality"],
        "fx":    "USD moderate; EM FX with strong GDP benefiting",
        "bonds": "Bearish — yields rising with growth, inflation contained",
        "sectors_overweight":  ["XLK","XLY","XLI","XLF"],
        "sectors_underweight": ["XLU","XLP","XLV"],
    },
    "Q2": {  # Reflation: Growth ↑, Inflation ↑
        "best":  ["Energy (XLE)", "Materials (XLB)", "Commodities", "Industrials", "select Equities"],
        "worst": ["Utilities", "Consumer Staples", "Long Duration Bonds", "High Quality Bonds"],
        "style": ["Value", "High Beta", "Commodity Exposure", "Cyclicals"],
        "fx":    "Commodity FX (AUD, CAD, NOK, MXN, BRL) outperform; USD mixed",
        "bonds": "Very bearish — both growth AND inflation up = steepening curve",
        "sectors_overweight":  ["XLE","XLB","XLI","XLY"],
        "sectors_underweight": ["XLU","XLP","TLT","IEF"],
    },
    "Q3": {  # Stagflation: Growth ↓, Inflation ↑
        "best":  ["Gold", "Commodities (selective)", "Healthcare (XLV)", "Utilities (XLU)", "Consumer Staples (XLP)"],
        "worst": ["Tech (XLK)", "Consumer Disc (XLY)", "Small Caps (IWM)", "Credit", "EM Equities (ex-commodity)"],
        "style": ["Low Beta", "Dividend Yield", "Quality", "Secular Growth (defensive)", "Min Volatility"],
        "fx":    "USD bearish TREND (McCullough Apr 2026); commodity FX mixed; EM commodity exporters OK",
        "bonds": "Long duration USTs bullish (flight to quality) vs nominal bonds",
        "sectors_overweight":  ["XLV","XLP","XLU","GLD"],
        "sectors_underweight": ["XLK","XLY","IWM","XLF"],
        "note":  "Current structural quad. Q2 monthly overlay adds tactical commodity/energy.",
    },
    "Q4": {  # Deflation: Growth ↓, Inflation ↓
        "best":  ["Healthcare (XLV)", "Consumer Staples (XLP)", "Utilities (XLU)", "Long Bonds (TLT)", "USD"],
        "worst": ["Tech (XLK)", "Energy (XLE)", "Credit (HYG)", "Small Caps", "Commodities"],
        "style": ["Min Volatility", "Low Beta", "Dividend", "Quality", "Defensive"],
        "fx":    "USD very bullish (flight to safety); commodity FX crushed; EM brutal",
        "bonds": "Very bullish — deflationary collapse; long TLT",
        "sectors_overweight":  ["XLV","XLP","XLU","TLT"],
        "sectors_underweight": ["XLK","XLE","HYG","IWM"],
    },
}

# ---------------------------------------------------------------------------
# Bottleneck scanner — sector profiles
# ---------------------------------------------------------------------------
BOTTLENECK_PROFILES: dict = {
    "ai_compute":    {"constraint": 0.90, "Q1": 0.85, "Q2": 0.70, "Q3": 0.50, "Q4": 0.30},
    "ai_networking": {"constraint": 0.85, "Q1": 0.80, "Q2": 0.75, "Q3": 0.55, "Q4": 0.35},
    "ai_optics":     {"constraint": 0.80, "Q1": 0.75, "Q2": 0.70, "Q3": 0.60, "Q4": 0.40},
    "ai_power":      {"constraint": 0.85, "Q1": 0.70, "Q2": 0.75, "Q3": 0.65, "Q4": 0.50},
    "healthcare_eq": {"constraint": 0.80, "Q1": 0.65, "Q2": 0.55, "Q3": 0.85, "Q4": 0.80},
    "pharma":        {"constraint": 0.85, "Q1": 0.60, "Q2": 0.50, "Q3": 0.80, "Q4": 0.75},
    "defense":       {"constraint": 0.80, "Q1": 0.55, "Q2": 0.65, "Q3": 0.75, "Q4": 0.60},
    "utilities":     {"constraint": 0.75, "Q1": 0.50, "Q2": 0.45, "Q3": 0.80, "Q4": 0.85},
    "water":         {"constraint": 0.80, "Q1": 0.55, "Q2": 0.50, "Q3": 0.85, "Q4": 0.85},
    "precious_metals": {"constraint": 0.70, "Q1": 0.70, "Q2": 0.65, "Q3": 0.85, "Q4": 0.80},
    "energy_infra":  {"constraint": 0.75, "Q1": 0.55, "Q2": 0.85, "Q3": 0.75, "Q4": 0.30},
    "staples":       {"constraint": 0.55, "Q1": 0.45, "Q2": 0.40, "Q3": 0.75, "Q4": 0.80},
    "generic":       {"constraint": 0.20, "Q1": 0.50, "Q2": 0.50, "Q3": 0.40, "Q4": 0.40},
}

TICKER_SECTOR: dict = {
    "NVDA":"ai_compute","AMD":"ai_compute","AVGO":"ai_compute","TSM":"ai_compute",
    "ALAB":"ai_networking","CRDO":"ai_networking","MRVL":"ai_networking","ANET":"ai_networking",
    "LITE":"ai_optics","CIEN":"ai_optics","COHR":"ai_optics","IIVI":"ai_optics","AAOI":"ai_optics",
    "VST":"ai_power","CEG":"ai_power","ETN":"ai_power","NRG":"ai_power","GEV":"ai_power",
    "ISRG":"healthcare_eq","ABT":"healthcare_eq","BSX":"healthcare_eq","MDT":"healthcare_eq",
    "LLY":"pharma","MRNA":"pharma","REGN":"pharma","BMY":"pharma",
    "LMT":"defense","RTX":"defense","NOC":"defense","GD":"defense","KTOS":"defense","HII":"defense",
    "NEE":"utilities","D":"utilities","DUK":"utilities","SO":"utilities","XLU":"utilities",
    "AWK":"water","WTRG":"water","CWT":"water",
    "GLD":"precious_metals","GC=F":"precious_metals","SLV":"precious_metals","SI=F":"precious_metals",
    "XLE":"energy_infra","CL=F":"energy_infra","BZ=F":"energy_infra","XOM":"energy_infra","CVX":"energy_infra",
    "XLP":"staples","PG":"staples","KO":"staples","PEP":"staples","WMT":"staples",
    "SPY":"generic","QQQ":"generic","IWM":"generic","TLT":"generic","DIA":"generic",
}
