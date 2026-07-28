"""warroom/data.py — universe + OHLCV loader.
Complete-but-light: reads a local parquet cache first (built by build_cache.py, bulk/incremental),
then live yfinance, then deterministic synthetic so the app ALWAYS renders.
"""
from __future__ import annotations
from parquet_compat import read_parquet_compat
import os, hashlib, numpy as np, pandas as pd

_CACHE = os.path.join(os.path.dirname(__file__), "..", "cache")

# --- universes (macro proxies first; GIP/regime needs them) ---
MACRO_PROXY = ["SPY", "IWM", "XLI", "XLY", "XHB", "USO", "GLD", "UUP", "TLT", "IEF", "DBC", "HYG", "^VIX",
               "XLK", "XLE", "XLF", "XLV", "XLP", "XLU", "XLB", "XLRE", "XLC", "IWD", "IWF", "MTUM"]
# US: liquid leaders + the AI-buildout supply-chain beneficiaries (from the roadmap/12-layer attachments)
US_NAMES = ["NVDA", "AMD", "AVGO", "MRVL", "SMH", "SOXX", "MU", "TSM", "INTC",
            "ANET", "COHR", "LITE", "FN", "CRDO", "ALAB", "AMKR", "GLW",
            "AMAT", "LRCX", "KLAC", "ENTG", "MKSI",
            "VRT", "ETN", "PWR", "GEV", "CEG", "VST", "NRG", "TLN", "HUBB", "ON",
            "MP", "ATI", "MTRN", "KTOS",
            "MSFT", "GOOGL", "AMZN", "META", "ORCL", "NBIS", "CRM", "NOW",
            "AAPL", "ARKK", "XLE", "XLU", "XLP", "COPX"]
def _dynamic_us():
    import os, json
    try:
        path = os.path.join(os.path.dirname(__file__), "..", "data", "extended_universe.json")
        with open(path, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        ks = list((d.get("tier_2_discovered") or {}).keys()) + list((d.get("tier_3_user_requested") or {}).keys())
        return [k.upper() for k in ks if isinstance(k, str) and k.isalpha() and 1 <= len(k) <= 5 and k.upper() not in US_NAMES and k.upper() != "HYNIX"]
    except Exception:
        return []
US_NAMES = US_NAMES + _dynamic_us()            # adaptive: merge engine-discovered tickers
# cross-asset beta-play candidates (precious/miners, energy, copper, crypto-miners, nuclear) for the beta-play finder
BETA_UNIVERSE = ["ACLS", "GDX", "GDXJ", "SIL", "FNV", "WPM", "NEM", "GOLD", "AEM",
                 "XOP", "OIH", "SLB", "HAL", "AMLP", "FCX", "COPX", "SCCO",
                 "MARA", "RIOT", "CLSK", "DNN", "NXE", "OKLO", "SMR"]
# adjacent-theme names for the theme graph (quantum, robotics/automation, defense-tech)
THEME_EXT = ["IONQ", "RGTI", "QBTS", "ARQQ", "TSLA", "ISRG", "ROK", "SERV", "PATH", "TER", "NNDM", "KTOS"]
# DM<->EM rotation nodes (US-listed country/region ETFs) — the global risk-curve axis
EM_PROXY = ["EEM", "EWZ", "INDA", "FXI", "EWY", "EWT", "EWW", "EFA"]
# country-regime grid proxies (US-listed single-country ETFs) — for the global macro grid
COUNTRY_PROXY = ["EZU", "EWU", "EWJ", "EIDO", "EWA", "EWC", "EWG", "EWL", "EZA"]
# credit / liquidity / rates proxies (price-based meter inputs — no FRED needed for these)
CREDIT_PROXY = ["LQD", "JNK", "AGG", "BIL", "TIP", "EMB", "SHY"]
# secular "wealth" theme proxies (AI/power/nuclear/india/robotics/defense/cyber)
WEALTH_PROXY = ["BOTZ", "NLR", "ITA", "KWEB", "XLK", "IGV"]
# CPO / photonics / HBM / power supply-chain names from user's attachments (consensus_heatmap + bottleneck ref).
# These are the curated thesis tickers — US-listed & ADRs (intl names like Samsung/SK Hynix need yfinance
# on your machine via data_ingest; add "005930.KS","000660.KS","2317.TW" etc. to your cache).
SUPPLY_CHAIN = ["MU", "AVGO", "MRVL", "AAOI", "COHR", "QCOM", "ETN", "CRDO", "AMD", "LNG", "MP", "AXTI",
                "LITE", "SITM", "GLW", "TEL", "APH", "FORM", "NVDA", "ANET", "CIEN", "ALAB", "AEHR",
                "HIMX", "POWL", "VRT", "GEV", "FN", "AMKR", "ARM", "ASML", "LRCX", "AMAT", "KLAC",
                "SMCI", "DELL", "CLS", "FLEX", "TSM", "KEYS", "PLUG", "ASTS", "SMTC"]
US_UNIVERSE = list(dict.fromkeys(MACRO_PROXY + US_NAMES + BETA_UNIVERSE + THEME_EXT + EM_PROXY + COUNTRY_PROXY + CREDIT_PROXY + WEALTH_PROXY + SUPPLY_CHAIN))
IDX_UNIVERSE = ["BBCA.JK", "BMRI.JK", "BBRI.JK", "BBNI.JK", "TLKM.JK", "ASII.JK", "BUMI.JK",
                "ADRO.JK", "ANTM.JK", "MDKA.JK", "GOTO.JK", "AMMN.JK", "BREN.JK", "HUMI.JK", "^JKSE"]
CRYPTO_UNIVERSE = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "COIN", "IBIT", "MSTR"]
FX_UNIVERSE = ["DX-Y.NYB", "EURUSD=X", "USDJPY=X", "GBPUSD=X", "AUDUSD=X", "USDIDR=X"]
COMMO_UNIVERSE = ["GLD", "SLV", "USO", "UNG", "CPER", "DBC", "WEAT", "URA"]

# ---------------------------------------------------------------------------
# Data states (master prompt §9). Production NEVER fabricates prices.
# Synthetic frames exist only behind WARROOM_DATA_TEST_FIXTURE=1 and are tagged
# TEST_FIXTURE so nothing downstream (dashboard, ranking, shadow, live) can
# mistake them for market data.
# ---------------------------------------------------------------------------
CURRENT = "CURRENT"
STALE_LAST_KNOWN = "STALE_LAST_KNOWN"
HISTORICAL_REFERENCE = "HISTORICAL_REFERENCE"
PARTIAL = "PARTIAL"
NO_DATA = "NO_DATA"
ERROR = "ERROR"
TEST_FIXTURE = "TEST_FIXTURE"

STALE_AFTER_DAYS = 7          # daily bars older than this are stale
MIN_BARS = 80

LAST_STATES: dict = {}        # per-ticker state map from the most recent load* call
LAST_ERRORS: list = []        # exact provider errors from the most recent load* call


def _test_fixture_frame(t, n=420):
    """Deterministic synthetic OHLCV. TEST FIXTURE ONLY — gated by env var."""
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=int(n))
    m = len(idx)
    seed = int.from_bytes(hashlib.sha256(str(t).encode("utf-8")).digest()[:4], "big")
    r = np.random.default_rng(seed)
    rets = r.normal(r.uniform(-0.0008, 0.0013), r.uniform(0.011, 0.032), m)
    c = 100 * np.exp(np.cumsum(rets)); intr = np.abs(r.normal(0, 0.018, m)) * c; loc = r.uniform(.2, .8, m)
    h = c + intr * (1 - loc); l = c - intr * loc; o = l + (h - l) * r.uniform(.2, .8, m)
    v = (r.uniform(1e6, 6e7, m) * (1 + np.abs(rets) / 0.02 * 0.5)).round()
    return pd.DataFrame({"Open": o, "High": h, "Low": l, "Close": c, "Volume": v}, index=idx)


def _test_fixtures_enabled() -> bool:
    return os.getenv("WARROOM_DATA_TEST_FIXTURE", "").lower() in {"1", "true", "yes"}


def _offline() -> bool:
    return os.getenv("WARROOM_OFFLINE", "").lower() in {"1", "true", "yes"}


def _frame_state(df) -> str:
    try:
        last = pd.Timestamp(df.index[-1])
        age = (pd.Timestamp.today().normalize() - last.normalize()).days
        return CURRENT if age <= STALE_AFTER_DAYS else STALE_LAST_KNOWN
    except Exception:
        return NO_DATA


def _record(states, ticker, state, source, df=None, error=None):
    states[ticker] = {
        "state": state,
        "source": source,
        "last_bar": str(df.index[-1].date()) if df is not None and len(df) else None,
        "bars": int(len(df)) if df is not None else 0,
        "retrieved_at": pd.Timestamp.utcnow().isoformat(),
        "error": error,
    }


def _from_cache(tickers, states=None):
    out = {}
    path = os.path.join(_CACHE, "prices.parquet")
    if not os.path.exists(path):
        return out
    try:
        df = read_parquet_compat(path)
        for t in tickers:
            if t in df.columns.get_level_values(0):
                d = df[t][["Open", "High", "Low", "Close", "Volume"]].dropna()
                if len(d) > MIN_BARS:
                    out[t] = d
                    if states is not None:
                        _record(states, t, _frame_state(d), "cache/prices.parquet", d)
    except Exception as exc:
        if states is not None:
            LAST_ERRORS.append(f"cache read failed: {type(exc).__name__}: {exc}")
    return out


def load_with_states(tickers, days=420, allow_live=True):
    """Load OHLCV with honest per-ticker data states.

    Order: local parquet cache (last-known-good is never erased) -> live yfinance
    (only when allow_live) -> NO_DATA. No synthetic output in production.
    Returns (frames, source, states).
    """
    global LAST_STATES, LAST_ERRORS
    allow_live = allow_live and not _offline()
    tickers = list(dict.fromkeys(tickers))
    states: dict = {}
    LAST_ERRORS = []
    cached = _from_cache(tickers, states)
    missing = [t for t in tickers if t not in cached]
    frames = dict(cached)

    if missing and allow_live:
        try:
            import yfinance as yf
            raw = yf.download(missing, period=f"{days}d", interval="1d", auto_adjust=False,
                              progress=False, group_by="ticker", threads=True)
            got = set()
            if isinstance(raw.columns, pd.MultiIndex):
                for t in missing:
                    if t in raw.columns.get_level_values(0):
                        d = raw[t][["Open", "High", "Low", "Close", "Volume"]].dropna()
                        if len(d) > MIN_BARS:
                            frames[t] = d; got.add(t)
                            _record(states, t, _frame_state(d), "yfinance live", d)
            elif len(missing) == 1:
                d = raw[["Open", "High", "Low", "Close", "Volume"]].dropna()
                if len(d) > MIN_BARS:
                    frames[missing[0]] = d; got.add(missing[0])
                    _record(states, missing[0], _frame_state(d), "yfinance live", d)
            for t in missing:
                if t not in got:
                    LAST_ERRORS.append(f"yfinance: no usable bars for {t}")
        except Exception as exc:
            LAST_ERRORS.append(f"yfinance download failed: {type(exc).__name__}: {exc}")
    elif missing and not allow_live:
        for t in missing:
            LAST_ERRORS.append(f"live disabled: no cached data for {t}")

    if _test_fixtures_enabled():
        for t in tickers:
            if t not in frames:
                frames[t] = _test_fixture_frame(t, days)
                _record(states, t, TEST_FIXTURE, "synthetic test fixture", frames[t])

    for t in tickers:
        if t not in frames:
            _record(states, t, NO_DATA, None, None)

    n_cur = sum(1 for t in tickers if states.get(t, {}).get("state") == CURRENT)
    n_stale = sum(1 for t in tickers if states.get(t, {}).get("state") == STALE_LAST_KNOWN)
    if not frames:
        source = "NO_DATA (no cache, no live)"
    elif n_cur == len(tickers):
        source = "current (cache/live)"
    else:
        source = f"partial: {n_cur} current, {n_stale} stale, {len(tickers) - n_cur - n_stale} no-data"
    LAST_STATES = states
    return frames, source, states


def load(tickers, days=420, allow_live=True):
    """Backwards-compatible wrapper: returns (frames, source)."""
    frames, source, _ = load_with_states(tickers, days=days, allow_live=allow_live)
    return frames, source
