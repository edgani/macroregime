"""data_layer.py — the ONE data adapter for War Room OS.

Real data on the user machine through a provider cascade plus persistent last-known-good cache.
Decision-bearing UI paths never synthesize prices. Provider failures are isolated per ticker/market
and clearly stamped as live refresh, fresh cache, stale cache, partial, or unavailable.

Per-market universes are extensible — add tickers here, they flow through the whole pipeline.
On-chain (crypto) + COT (commodity/fx) need their own feeds/keys (onchain_engine, cftc_cot_scraper);
until wired, those markets score on price + the market_drivers matrix only (flagged in the UI).
"""
from __future__ import annotations
import io, sys, time
import numpy as np
import pandas as pd

# ─────────────────────────── per-market universes (extend freely) ───────────────────────────
UNIVERSE = {
    "us": ["NVDA","AMD","AVGO","MRVL","MU","AXTI","AAOI","COHR","LITE","CRDO","ALAB","AEHR","FORM",
           "GEV","VRT","ETN","POWL","CEG","VST","CCJ","UEC","SMCI","DELL","ARM","ASML","TSM"],
    "idx": ["BBCA.JK","BREN.JK","BRMS.JK","ADRO.JK","ANTM.JK","MDKA.JK","TLKM.JK","GOTO.JK"],
    "crypto": [  # ~top-100 by mkt cap (stablecoins + pure wrappers excluded). Yahoo skips any that don't resolve.
        "BTC-USD","ETH-USD","XRP-USD","BNB-USD","SOL-USD","DOGE-USD","ADA-USD","TRX-USD","AVAX-USD","LINK-USD",
        "SUI-USD","XLM-USD","HBAR-USD","DOT-USD","BCH-USD","LTC-USD","UNI7083-USD","NEAR-USD","APT-USD","ICP-USD",
        "ETC-USD","POL-USD","ARB-USD","OP-USD","ATOM-USD","FIL-USD","IMX-USD","INJ-USD","VET-USD","ALGO-USD",
        "GRT-USD","RENDER-USD","TIA-USD","SEI-USD","STX-USD","AAVE-USD","MKR-USD","RUNE-USD","THETA-USD","FTM-USD",
        "FLOW-USD","EGLD-USD","XTZ-USD","SAND-USD","MANA-USD","AXS-USD","CHZ-USD","EOS-USD","QNT-USD","MINA-USD",
        "GALA-USD","CRV-USD","LDO-USD","SNX-USD","ENS-USD","DYDX-USD","JUP-USD","PYTH-USD","JTO-USD","ONDO-USD",
        "WLD-USD","FET-USD","AR-USD","KAS-USD","ZEC-USD","DASH-USD","XMR-USD","COMP5692-USD","PENDLE-USD","KAVA-USD",
        "ROSE-USD","1INCH-USD","ENJ-USD","ZIL-USD","BAT-USD","CELO-USD","KSM-USD","NEO-USD","IOTA-USD","GMX-USD",
        "WOO-USD","CFX-USD","ASTR-USD","SKL-USD","ANKR-USD","SHIB-USD","PEPE-USD","WIF-USD","BONK-USD","FLOKI-USD",
        "TON11419-USD","TAO22974-USD","ENA-USD","STRK-USD","W-USD","JASMY-USD","NOT-USD","ORDI-USD","AKT-USD","BEAM-USD",
    ],
    "commodity": ["CL=F","BZ=F","GC=F","SI=F","HG=F","NG=F"],
    "fx": ["EURUSD=X","USDJPY=X","GBPUSD=X","AUDUSD=X","USDIDR=X","DX-Y.NYB"],
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


def load_prices(tickers, start="2022-01-01", allow_live=True):
    """Return ({ticker: close Series}, source_str). Tries yfinance; falls back to synthetic."""
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
            sys.stderr.write(f"[data_layer] yfinance failed ({e}) → synthetic fallback\n")
    # synthetic fallback — deterministic per ticker so the dashboard is stable
    out = {}
    for i, t in enumerate(tickers):
        drift = 0.0003 + (hash(t) % 11) * 0.0001
        out[t] = _synth(drift=drift, seed=(abs(hash(t)) % 9999))
    return out, "SYNTHETIC (offline fallback)"


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


def load_all(markets=None, start="2022-01-01", allow_live=True, fetch_live_feeds=False, force_refresh=False):
    """Load all requested markets through the resilient v5 provider/cache cascade.

    Live path never fabricates prices. Each ticker independently resolves through providers and then
    last-known-good cache. One failed ticker or market cannot blank the rest of the desk.
    """
    import os
    markets = markets or list(UNIVERSE.keys())
    prices, ohlcv, sources, bundles = {}, {}, {}, {}
    try:
        from warroom import data as WD
        UNI = {
            "us": getattr(WD, "US_UNIVERSE", UNIVERSE["us"]),
            "idx": getattr(WD, "IDX_UNIVERSE", UNIVERSE["idx"]),
            "crypto": UNIVERSE["crypto"],
            "commodity": UNIVERSE["commodity"],
            "fx": UNIVERSE["fx"],
        }
    except Exception:
        UNI = dict(UNIVERSE)

    if allow_live:
        from data.loader import load_market, clear_memory_cache
        if force_refresh:
            clear_memory_cache()
        for market in markets:
            tickers = UNI.get(market, UNIVERSE.get(market, []))
            try:
                bundle = load_market(tickers, market=market, days=756, force_refresh=force_refresh)
                bundles[market] = bundle
                ohlcv[market] = dict(bundle.frames)
                prices[market] = {t: frame["Close"].dropna() for t, frame in bundle.frames.items() if "Close" in frame}
                sources[market] = bundle.source_summary
            except Exception as exc:
                prices[market], ohlcv[market] = {}, {}
                sources[market] = f"resilient_v6 failed · {type(exc).__name__}: {exc}"
    else:
        # Explicit test-only path. The Streamlit app never calls this mode.
        for market in markets:
            px, src = load_prices(UNI.get(market, UNIVERSE.get(market, [])), start, allow_live=False)
            prices[market] = px
            ohlcv[market] = {t: pd.DataFrame({"Open": s, "High": s, "Low": s, "Close": s, "Volume": 0.0}) for t, s in px.items()}
            sources[market] = "SYNTHETIC_TEST_ONLY"

    # Macro proxies and regional proxies use the same persistent provider/cache layer.
    proxies = {}
    if allow_live:
        try:
            from data.loader import load_market
            proxy_tickers = ["SPY", "^GSPC", "GLD", "USO", "UUP", "XLI", "XLY", "TLT", "DBC", "IWM", "SMH"]
            proxy_bundle = load_market(proxy_tickers, market="us", days=756, force_refresh=force_refresh)
            bundles["_proxy"] = proxy_bundle
            prices["_proxy"] = {t: f["Close"].dropna() for t, f in proxy_bundle.frames.items()}
            sources["_proxy"] = proxy_bundle.source_summary
        except Exception as exc:
            prices["_proxy"] = {}
            sources["_proxy"] = f"proxy unavailable · {type(exc).__name__}"
        try:
            from data.loader import load_market
            from regional_regime import EXTRA_PROXY_TICKERS
            region_bundle = load_market(EXTRA_PROXY_TICKERS, market="us", days=756, force_refresh=force_refresh)
            bundles["_regional"] = region_bundle
            proxies = {t: f["Close"].dropna() for t, f in region_bundle.frames.items()}
        except Exception:
            proxies = {}

    # Optional IDX official enrichment. It can improve IDX rows but never erases the LKG base.
    if allow_live and "idx" in markets:
        try:
            from gcfis.feeds.typef_idx import build_typef
            from warroom import data as _WD
            idxu = getattr(_WD, "IDX_UNIVERSE", ["BBCA.JK", "BMRI.JK", "BBRI.JK", "BBNI.JK", "TLKM.JK", "ASII.JK"])
            idx_frames, idx_status = build_typef(idxu, days=120)
            if idx_frames:
                normalized = {}
                for ticker, frame in idx_frames.items():
                    f = frame.rename(columns={str(c): str(c).capitalize() for c in frame.columns})
                    if "Close" in f.columns:
                        normalized[ticker] = f
                if normalized:
                    ohlcv.setdefault("idx", {}).update(normalized)
                    prices.setdefault("idx", {}).update({t: f["Close"].dropna() for t, f in normalized.items()})
                    sources["idx"] = sources.get("idx", "") + f" · idx.co.id enrich:{len(normalized)}"
            else:
                sources["idx"] = sources.get("idx", "") + f" · idx enrich unavailable:{idx_status}"
        except Exception as exc:
            sources["idx"] = sources.get("idx", "") + f" · idx enrich error:{type(exc).__name__}"

    # FRED already has API -> CSV -> DBnomics -> persistent-cache cascade.
    fred, fsrc = {}, "unavailable"
    try:
        from data.fred_loader import load_fred_series
        fred = load_fred_series(force_refresh=bool(force_refresh)) or {}
        fsrc = f"fred_resilient · {len(fred)} series" if fred else "fred unavailable/cache empty"
    except Exception as exc:
        try:
            from warroom import fred as WF
            fred = WF.fetch() or {}
            fsrc = f"warroom.fred · {len(fred)} series"
        except Exception:
            fred, fsrc = {}, f"fred unavailable · {type(exc).__name__}"

    vix = None
    try:
        vp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "research", "vix.csv")
        if os.path.exists(vp):
            v = pd.read_csv(vp)
            v["DATE"] = pd.to_datetime(v["DATE"])
            vix = v.set_index("DATE")["CLOSE"]
    except Exception:
        pass

    try:
        from engines.treasury_liquidity import analyze_liquidity
        liquidity = analyze_liquidity(fred if fred else None)
    except Exception as exc:
        liquidity = {"ok": False, "error": str(exc)}

    bench = prices.get("us", {}).get(BENCH)
    if bench is None:
        bench = prices.get("_proxy", {}).get(BENCH)
    if bench is None:
        bench = prices.get("_proxy", {}).get("^GSPC")
    if bench is None and allow_live:
        try:
            from data.loader import load_market
            bb = load_market([BENCH], market="us", days=756, force_refresh=force_refresh)
            bundles["_bench"] = bb
            if BENCH in bb.frames:
                bench = bb.frames[BENCH]["Close"].dropna()
        except Exception:
            bench = None

    feeds = _load_feeds(allow_live=allow_live, fetch_live=fetch_live_feeds)

    market_meta = {}
    approved_count = 0
    stale_market_count = 0
    for market in markets:
        pm = prices.get(market) or {}
        bundle = bundles.get(market)
        latest = []
        for series in pm.values():
            try:
                if len(series.index):
                    latest.append(pd.Timestamp(series.index.max()))
            except Exception:
                pass
        as_of = max(latest).isoformat() if latest else None
        if bundle is not None:
            status = bundle.status
            live_count = bundle.live_count
            cache_fresh = bundle.cache_fresh_count
            cache_stale = bundle.cache_stale_count
            missing = bundle.missing_count
            requested = bundle.requested_count
            provider_counts = bundle.provider_counts
        else:
            status = "READY" if pm else "MISSING"
            live_count, cache_fresh, cache_stale = (len(pm), 0, 0) if pm else (0, 0, 0)
            missing, requested, provider_counts = (0, len(pm), {}) if pm else (0, 0, {})
        approved = bool(pm) and status != "MISSING"
        if approved:
            approved_count += 1
        if cache_stale and not (live_count or cache_fresh):
            stale_market_count += 1
        market_meta[market] = {
            "status": status,
            "source": sources.get(market, "MISSING"),
            "loaded": len(pm),
            "requested": requested,
            "live_refreshed": live_count,
            "cache_fresh": cache_fresh,
            "cache_stale": cache_stale,
            "missing": missing,
            "provider_counts": provider_counts,
            "ohlcv_loaded": len(ohlcv.get(market) or {}),
            "as_of": as_of,
            "frequency": "DAILY_MODEL",
            "realtime": False,
            "last_known_good_enabled": True,
        }

    if approved_count == len(markets) and approved_count:
        overall_source = "RESILIENT_DAILY_LKG" if stale_market_count else "RESILIENT_DAILY"
    elif approved_count:
        overall_source = "RESILIENT_DAILY_PARTIAL"
    else:
        overall_source = "DATA_UNAVAILABLE"

    try:
        from data.resilient_market_data import write_health
        write_health(bundles, {"overall_source": overall_source, "fred_source": fsrc})
    except Exception:
        pass

    return {
        "prices": prices,
        "ohlcv": ohlcv,
        "bench": bench,
        "fred": fred,
        "vix": vix,
        "sources": sources,
        "bench_source": "resilient_v6",
        "fred_source": fsrc,
        "overall_source": overall_source,
        "market_meta": market_meta,
        "markets": markets,
        "treasury_liquidity": liquidity,
        "proxies": proxies,
        "feeds": feeds,
    }



if __name__ == "__main__":
    d = load_all(allow_live=True)
    print("overall source:", d["overall_source"])
    for m, src in d["sources"].items():
        print(f"  {m:10} {len(d['prices'][m]):>2} tickers  [{src}]")
    print("  bench:", d["bench_source"], "| fred:", d["fred_source"], f"({len(d['fred'])} series)")
