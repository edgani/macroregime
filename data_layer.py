"""data_layer.py — the ONE data adapter for War Room OS.

Real data on YOUR machine (yfinance + FRED fredgraph, no API key needed). Production mode
never fabricates a fallback series: missing feeds remain empty and the dashboard renders NO_DATA/STALE.
Synthetic data is available only when explicitly requested for pipeline tests.

Per-market universes are extensible — add tickers here, they flow through the whole pipeline.
On-chain (crypto) + COT (commodity/fx) need their own feeds/keys (onchain_engine, cftc_cot_scraper);
until wired, those markets score on price + the market_drivers matrix only (flagged in the UI).
"""
from __future__ import annotations
import io, sys, time, os
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd

# ─────────────────────────── per-market universes (extend freely) ───────────────────────────
UNIVERSE = {
    "us": ["NVDA","AMD","AVGO","MRVL","MU","AXTI","AAOI","COHR","LITE","CRDO","ALAB","AEHR","FORM",
           "GEV","VRT","ETN","POWL","CEG","VST","CCJ","UEC","SMCI","DELL","ARM","ASML","TSM"],
    "idx": ["BBCA.JK","BREN.JK","BRMS.JK","ADRO.JK","ANTM.JK","MDKA.JK","TLKM.JK","GOTO.JK"],
    "crypto": [  # ~top-100 by mkt cap (stablecoins + pure wrappers excluded). Yahoo skips any that don't resolve.
        "BTC-USD","ETH-USD","XRP-USD","BNB-USD","SOL-USD","DOGE-USD","ADA-USD","TRX-USD","AVAX-USD","LINK-USD",
        "SUI-USD","XLM-USD","HBAR-USD","DOT-USD","BCH-USD","LTC-USD","UNI-USD","NEAR-USD","APT-USD","ICP-USD",
        "ETC-USD","POL-USD","ARB-USD","OP-USD","ATOM-USD","FIL-USD","IMX-USD","INJ-USD","VET-USD","ALGO-USD",
        "GRT-USD","RENDER-USD","TIA-USD","SEI-USD","STX-USD","AAVE-USD","MKR-USD","RUNE-USD","THETA-USD","FTM-USD",
        "FLOW-USD","EGLD-USD","XTZ-USD","SAND-USD","MANA-USD","AXS-USD","CHZ-USD","EOS-USD","QNT-USD","MINA-USD",
        "GALA-USD","CRV-USD","LDO-USD","SNX-USD","ENS-USD","DYDX-USD","JUP-USD","PYTH-USD","JTO-USD","ONDO-USD",
        "WLD-USD","FET-USD","AR-USD","KAS-USD","ZEC-USD","DASH-USD","XMR-USD","COMP-USD","PENDLE-USD","KAVA-USD",
        "ROSE-USD","1INCH-USD","ENJ-USD","ZIL-USD","BAT-USD","CELO-USD","KSM-USD","NEO-USD","IOTA-USD","GMX-USD",
        "WOO-USD","CFX-USD","ASTR-USD","SKL-USD","ANKR-USD","SHIB-USD","PEPE-USD","WIF-USD","BONK-USD","FLOKI-USD",
        "TON-USD","TAO-USD","ENA-USD","STRK-USD","W-USD","JASMY-USD","NOT-USD","ORDI-USD","AKT-USD","BEAM-USD",
    ],
    "commodity": ["CL=F","BZ=F","GC=F","SI=F","HG=F","NG=F"],
    "fx": ["EURUSD=X","JPY=X","GBPUSD=X","AUDUSD=X","IDR=X","DX-Y.NYB"],
}
BENCH = "SPY"

# FRED series that power liquidity / macro (fredgraph CSV, no key)
FRED_SERIES = {
    "WALCL":"Fed balance sheet","RRPONTSYD":"Reverse repo","WTREGEN":"Treasury general acct",
    "DFII10":"Real 10Y (TIPS)","T10YIE":"10Y breakeven","BAMLH0A0HYM2":"HY OAS",
}


def _synth(n=500, drift=0.0004, vol=0.02, start=100.0, seed=None):
    if seed is not None:
        np.random.seed(seed)
    idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=n, freq="B")
    r = np.random.normal(drift, vol, len(idx))
    return pd.Series(start * np.exp(np.cumsum(r)), index=idx)


def load_prices(tickers, start="2022-01-01", allow_live=True, allow_synthetic=False):
    """Return ({ticker: close Series}, source_str).

    Synthetic series are emitted only when ``allow_synthetic=True``. Production callers must
    preserve missingness so NO_DATA cannot silently become a trading signal.
    """
    if allow_live:
        try:
            import yfinance as yf
            data = yf.download(list(tickers), start=start, auto_adjust=True,
                               progress=False, threads=True)
            close = data["Close"] if isinstance(data.columns, pd.MultiIndex) and "Close" in data.columns.get_level_values(0) else data
            out = {}
            if isinstance(close, pd.DataFrame):
                for t in close.columns:
                    s = close[t].dropna()
                    if len(s) > 200:
                        out[t] = s
            else:  # single ticker
                s = close.dropna()
                if len(s) > 200:
                    out[list(tickers)[0]] = s
            if out:
                return out, "LIVE (yfinance)"
        except ImportError:
            pass
        except Exception as e:
            sys.stderr.write(f"[data_layer] yfinance failed ({e}); production keeps NO_DATA\n")
    if allow_synthetic:
        out = {}
        for i, t in enumerate(tickers):
            drift = 0.0003 + (hash(t) % 11) * 0.0001
            out[t] = _synth(drift=drift, seed=(abs(hash(t)) % 9999))
        return out, "SYNTHETIC (explicit test mode)"
    return {}, "NO_DATA (live source unavailable; synthetic disabled)"


def load_fred(allow_live=True):
    """FRED via fredgraph CSV (no API key). Returns {series_id: Series}. Empty if offline."""
    if not allow_live:
        return {}, "OFFLINE"
    out = {}
    try:
        import urllib.request
        for sid in FRED_SERIES:
            try:
                url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
                with urllib.request.urlopen(url, timeout=10) as r:
                    df = pd.read_csv(io.BytesIO(r.read()))
                df.columns = ["date", "value"]
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
                s = df.dropna().set_index(pd.to_datetime(df["date"]))["value"]
                if len(s) > 10:
                    out[sid] = s
            except Exception:
                continue
        if out:
            return out, "LIVE (FRED fredgraph)"
    except Exception:
        pass
    return {}, "OFFLINE (no FRED — liquidity uses price proxy)"


def _load_feeds(allow_live=True, fetch_live=False):
    """Specialized flow feeds (on-chain / COT / GEX / dark-pool) that otherwise leave metrics gated.
    PRIMARY path: read data/feeds_snapshot.pkl — build it once on a networked machine (build_feeds.py),
    commit it; the deploy then reads it, which also sidesteps Yahoo blocking datacenter IPs on Cloud.
    OPT-IN live path (fetch_live=True): best-effort direct fetch; each wrapped so a failure just leaves
    that feed empty — never crashes, never blocks. Returns {feed: value, "_status": {feed: how}}."""
    import os, pickle
    feeds, status = {}, {}
    if not allow_live:
        feeds["_status"] = {"_mode": "offline/test mode; specialized live snapshots disabled"}
        return feeds
    snap = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "feeds_snapshot.pkl")
    try:
        if os.path.exists(snap):
            with open(snap, "rb") as f:
                snapd = pickle.load(f) or {}
            for k in ("onchain", "cot", "gex", "finra", "typef", "fx_carry"):
                if snapd.get(k):
                    feeds[k] = snapd[k]; status[k] = f"snapshot · {snapd.get('_saved_at', '?')}"
        else:
            status["_snapshot"] = "absent (run build_feeds.py on a networked machine, commit the .pkl)"
    except Exception as e:
        status["_snapshot_error"] = f"{type(e).__name__}: {e}"
    if allow_live and fetch_live:
        def _try(k, fn):
            if feeds.get(k):
                return
            try:
                v = fn()
                if v:
                    feeds[k] = v; status[k] = "live"
                else:
                    status[k] = "live · empty"
            except Exception as e:
                status[k] = f"live failed · {type(e).__name__}"
        def _oc():
            from engines.live_data_engine import fetch_onchain_defillama
            return fetch_onchain_defillama({"BTC-USD": "bitcoin", "ETH-USD": "ethereum", "SOL-USD": "solana"})
        def _cot():
            from engines.cftc_cot_scraper import get_all_signals
            return get_all_signals()
        def _finra():
            from engines.live_data_engine import fetch_finra_short_volume
            return fetch_finra_short_volume(["NVDA", "AMD", "AVGO", "MRVL", "MU", "MSFT", "META", "AAPL"], lookback_days=20)
        def _gex():
            from engines.live_data_engine import fetch_options_yf
            return {"source": "yfinance",
                    "data": fetch_options_yf(["NVDA", "AMD", "AVGO", "MRVL", "MU", "SMH", "MSFT", "META", "AAPL", "AMZN"],
                                             max_tickers=10, max_workers=4)}
        _try("onchain", _oc); _try("cot", _cot); _try("finra", _finra); _try("gex", _gex)
    feeds["_status"] = status
    return feeds


def load_all(markets=None, start="2022-01-01", allow_live=True, fetch_live_feeds=False, allow_synthetic=False, fast_core=False, skip_slow_context=False):
    """Use v40's PROVEN live loaders (data.loader.load_prices + data.fred_loader.load_fred_series) —
    the exact path that fetches FRED+Yahoo live for you in v40. It may try alternate real loaders,
    but synthetic series are used only with ``allow_synthetic=True``. Production preserves NO_DATA."""
    markets = markets or list(UNIVERSE.keys())
    if os.getenv("WARROOM_NETWORK_MODE", "live").strip().lower() in {"offline","disabled","0","false"}:
        allow_live = False
    prices, ohlcv, sources = {}, {}, {}
    try:
        from warroom import data as WD
        UNI = {"us": getattr(WD, "US_UNIVERSE", UNIVERSE["us"]),
               "idx": getattr(WD, "IDX_UNIVERSE", UNIVERSE["idx"]),
               "crypto": UNIVERSE["crypto"], "commodity": UNIVERSE["commodity"], "fx": UNIVERSE["fx"]}
    except Exception:
        UNI = dict(UNIVERSE)
    if fast_core:
        fast_limits = {"us": int(os.getenv("WARROOM_FAST_US_NAMES", "18")),
                       "idx": int(os.getenv("WARROOM_FAST_IDX_NAMES", "12")),
                       "crypto": int(os.getenv("WARROOM_FAST_CRYPTO_NAMES", "16")),
                       "commodity": 20, "fx": 20}
        anchors = {"us":["SPY","QQQ","IWM","NVDA","AMD","MSFT","AAPL","AMZN","META","SMH"],
                   "idx":["^JKSE","BBCA.JK","BMRI.JK","BBRI.JK","TLKM.JK","ASII.JK","ANTM.JK","ADRO.JK"],
                   "crypto":["BTC-USD","ETH-USD","SOL-USD","XRP-USD","BNB-USD","DOGE-USD"],
                   "commodity":UNIVERSE["commodity"], "fx":UNIVERSE["fx"]}
        for m in list(UNI):
            values=[]
            for ticker in anchors.get(m,[]) + list(UNI.get(m,[])):
                if ticker not in values: values.append(ticker)
            UNI[m]=values[:fast_limits.get(m,len(values))]
    # ---- prices + OHLCV via v40's data.loader (yfinance per-ticker, the working path) ----
    v40_ok = False
    if allow_live:
        try:
            from data.loader import load_bundle as _bundle

            def _fetch_market(m):
                tk = UNI.get(m, UNIVERSE.get(m, []))
                frames = _bundle(tk, days=756)
                px = {ticker: frame["Close"].dropna() for ticker, frame in frames.items() if "Close" in frame}
                return m, px, frames

            # Markets are independent. Fetch them concurrently so a slow Yahoo batch for one
            # universe cannot block all other markets and create false NO_DATA panels.
            with ThreadPoolExecutor(max_workers=min(5, max(1, len(markets)))) as pool:
                futures = {pool.submit(_fetch_market, m): m for m in markets}
                for fut in as_completed(futures):
                    m = futures[fut]
                    try:
                        _, px, frames = fut.result()
                    except Exception as exc:
                        prices[m], ohlcv[m] = {}, {}
                        sources[m] = f"data.loader error · {type(exc).__name__}: {exc}"
                        continue
                    prices[m], ohlcv[m] = px, frames
                    sources[m] = f"data.loader batch · {len(px)} live" if px else "data.loader batch · 0"
                    if px:
                        v40_ok = True
        except Exception as e:
            sources["_v40loader"] = f"data.loader failed: {e}"
    # ---- macro-proxy ETFs for cross-asset rotation and regime context ----
    # These are core UI inputs, not slow enrichment. The fast profile loads a compact set; the
    # expanded profile adds sectors/EM. Without this wire Flow & Rotation stayed NO_DATA until a
    # much later expanded refresh.
    if allow_live:
        try:
            from data.loader import load_prices as _lp2
            _proxy_fast = ["SPY","QQQ","IWM","SMH","GLD","TLT","UUP","DBC","USO","EEM","EIDO"]
            _proxy_expanded = _proxy_fast + ["XLF","XLE","XLK","XLI","XLY","XLU","XLV","XLP","HYG","LQD","VWO"]
            _prox = _lp2(_proxy_fast if skip_slow_context else _proxy_expanded)
            if _prox:
                prices["_proxy"] = _prox
                sources["_proxy"] = f"macro proxies · {len(_prox)}"
            else:
                sources["_proxy"] = "macro proxies · 0"
        except Exception as exc:
            sources["_proxy"] = f"macro proxies error · {type(exc).__name__}: {exc}"

    # ---- country-index proxies for the REGIONAL REGIME row (real, not hardcoded) ----
    proxies = {}
    if allow_live and not skip_slow_context:
        try:
            from data.loader import load_prices as _lp3
            from regional_regime import EXTRA_PROXY_TICKERS
            proxies = _lp3(EXTRA_PROXY_TICKERS) or {}
        except Exception:
            proxies = {}
    # ---- IHSG/IDX: enrich with idx.co.id (typef_idx) for foreign flow / bandarmologi.
    #      yfinance (BBCA.JK etc.) above is the reliable base; typef_idx OVERWRITES only if it works. ----
    if "idx" in markets and allow_live and not skip_slow_context and os.getenv("WARROOM_ENABLE_IDX_SCRAPER", "0").strip().lower() in {"1","true","yes"}:
        try:
            from gcfis.feeds.typef_idx import build_typef
            from warroom import data as _WD
            idxu = getattr(_WD, "IDX_UNIVERSE", ["BBCA.JK","BMRI.JK","BBRI.JK","BBNI.JK","TLKM.JK","ASII.JK"])
            idx_ohlcv, idx_status = build_typef(idxu, days=120)
            if idx_ohlcv:
                col = lambda df: (df["close"] if "close" in df.columns else df["Close"] if "Close" in df.columns else df.iloc[:, 3])
                prices["idx"] = {tk: col(df) for tk, df in idx_ohlcv.items()}
                ohlcv["idx"] = {tk: df.rename(columns=str.capitalize) for tk, df in idx_ohlcv.items()}
                sources["idx"] = f"typef_idx (idx.co.id) · {len(idx_ohlcv)} names + foreign flow"
                v40_ok = True
            elif prices.get("idx"):
                sources["idx"] = f"yfinance base ({len(prices['idx'])}) · typef_idx enrich failed: {idx_status}"
            else:
                sources["idx"] = f"typef_idx: {idx_status}"
        except Exception as e:
            if not prices.get("idx"):
                sources["idx"] = f"typef_idx failed: {e}"

    # ---- per-market fallback: retry EVERY missing market, even when another market loaded. ----
    # The previous code retried only when *all* v40 markets failed. That meant US could load while
    # FX remained permanently NO_DATA. Missingness is now isolated per market.
    # Explicit synthetic test mode must stay offline. Do not call legacy loaders that may reach
    # Yahoo before the deterministic test fallback below.
    for m in markets:
        if prices.get(m):
            continue
        px, src = load_prices(
            UNI.get(m, UNIVERSE.get(m, [])), start, allow_live,
            allow_synthetic=allow_synthetic,
        )
        prices[m] = px
        sources[m] = f"per-market fallback · {src}"
        if px:
            v40_ok = True
        # Keep the market key present so downstream code can distinguish an empty market from a crash.
        ohlcv.setdefault(m, {})
    # ---- FRED via v40's fred_loader (the working path) ----
    fred, fsrc = {}, "OFFLINE" if not allow_live else "unavailable"
    if allow_live:
        try:
            from data.fred_loader import load_fred_series, load_fred_subset
            _fast_fred = ["INDPRO","RSAFS","PAYEMS","UNRATE","ICSA","CPI","CORECPI","FEDFUNDS",
                          "DGS2","DGS10","DFII10","T10YIE","HYOAS","WALCL","RRPONTSYD","WTREGEN"]
            fred = (load_fred_subset(_fast_fred, force_refresh=False) if fast_core
                    else load_fred_series(force_refresh=False)) or {}
            fred = {k: v for k, v in fred.items() if v is not None and len(v) > 0}
            # Normalise nice-name keys from fred_loader to the semantic IDs consumed by legacy engines.
            _fred_aliases = {
                "HYOAS": "BAMLH0A0HYM2", "CPI": "CPIAUCSL", "CORECPI": "CPILFESL",
                "FEDFUNDS": "FEDFUNDS", "DFF": "DFF", "DGS2": "DGS2", "DGS10": "DGS10",
                "DFII10": "DFII10", "T5YIE": "T5YIE", "T10YIE": "T10YIE",
                "WALCL": "WALCL", "RRPONTSYD": "RRPONTSYD", "WTREGEN": "WTREGEN",
            }
            for _nice, _semantic in _fred_aliases.items():
                if _nice in fred and _semantic not in fred:
                    fred[_semantic] = fred[_nice]
            fsrc = f"data.fred_loader v40 · {len(fred)} series" if fred else "data.fred_loader v40 · 0 (blocked here)"
        except Exception as e:
            try:
                from warroom import fred as WF
                fred = WF.fetch() or {}; fsrc = f"warroom.fred · {len(fred)} series"
            except Exception as e2:
                fred, fsrc = {}, f"fred unavailable ({e2})"
    # ---- VIX (bundled) ----
    vix = None
    try:
        vp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "research", "vix.csv")
        if os.path.exists(vp):
            v = pd.read_csv(vp); v["DATE"] = pd.to_datetime(v["DATE"]); vix = v.set_index("DATE")["CLOSE"]
    except Exception:
        pass
    # ---- liquidity read via US Treasury + NY Fed (TGA/RRP/SOFR, no key) ----
    if allow_live:
        try:
            from engines.treasury_liquidity import analyze_liquidity
            _liq = analyze_liquidity(fred if fred else None)
        except Exception as e:
            _liq = {"ok": False, "error": str(e)}
    else:
        _liq = {"ok": False, "state": "OFFLINE", "error": "offline/test mode"}

    bench = prices.get("us", {}).get(BENCH)
    if bench is None:
        bp, _ = load_prices([BENCH], start, allow_live, allow_synthetic=allow_synthetic); bench = bp.get(BENCH)
    # ---- specialized flow feeds (on-chain / COT / GEX / dark-pool) → un-gate the metrics ----
    feeds = _load_feeds(allow_live=allow_live and not skip_slow_context, fetch_live=fetch_live_feeds)
    live = v40_ok or (len(fred) > 5)
    has_synthetic = any(("synthetic (explicit" in str(v).lower()) or ("test-only" in str(v).lower()) for v in sources.values())
    overall = "SYNTHETIC_TEST" if has_synthetic else ("LIVE" if live else "NO_DATA")
    return {"prices": prices, "ohlcv": ohlcv, "bench": bench, "fred": fred, "vix": vix,
            "sources": sources, "bench_source": "v40" if v40_ok else "unavailable", "fred_source": fsrc,
            "overall_source": overall, "markets": markets,
            "treasury_liquidity": _liq, "proxies": proxies, "feeds": feeds}



if __name__ == "__main__":
    d = load_all(allow_live=True)
    print("overall source:", d["overall_source"])
    for m, src in d["sources"].items():
        print(f"  {m:10} {len(d['prices'][m]):>2} tickers  [{src}]")
    print("  bench:", d["bench_source"], "| fred:", d["fred_source"], f"({len(d['fred'])} series)")
