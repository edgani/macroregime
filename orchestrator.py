"""orchestrator.py — Snapshot builder. Light & staged loading."""
from __future__ import annotations
import time, logging, math
from typing import Optional, Callable, Dict
import numpy as np
import pandas as pd

from data.loader import load_fred, load_prices, save_snapshot, load_snapshot, snapshot_age_str
from engines.gip_engine import GIPEngine, get_playbook
from engines.global_quad_engine import GlobalQuadEngine
from engines.hurst_rr_engine import HurstRREngine
from engines.scenario_engine import ScenarioEngine
from engines.bottleneck_engine import BottleneckEngine
from config.settings import (
    MACRO_PROXIES, US_SECTORS, US_FACTORS, FOREX_PAIRS,
    COMMODITIES, CRYPTO, BONDS, IHSG_UNIVERSE, COUNTRY_UNIVERSE,
    TICKER_SECTOR,
)

logger = logging.getLogger(__name__)

def _prog(cb, msg, frac):
    logger.info(f"[{frac:.0%}] {msg}")
    if cb: cb(msg, frac)

def build_snapshot(
    progress_cb: Optional[Callable] = None,
    include_crypto: bool = True,
    include_us_stocks: bool = True,
    include_forex: bool = True,
    include_commodities: bool = True,
    include_ihsg: bool = True,
) -> dict:
    t0 = time.time()
    snap: dict = {"ts": t0, "ok": False}

    # 1. FRED
    _prog(progress_cb, "Loading FRED macro data...", 0.04)
    fred = load_fred(months=36)
    snap["fred_coverage"] = len(fred)

    # 2. Core prices (always)
    _prog(progress_cb, "Loading core market prices...", 0.10)
    prices: Dict[str, pd.Series] = {}
    prices.update(load_prices(list(MACRO_PROXIES.keys()) + list(BONDS.keys()) + ["DX-Y.NYB","^VIX"], days=756))

    # 3. US equities
    if include_us_stocks:
        _prog(progress_cb, "Loading US sectors + factors...", 0.16)
        prices.update(load_prices(list(US_SECTORS.keys()) + list(US_FACTORS.keys()), days=756))
        _prog(progress_cb, "Loading notable single stocks...", 0.21)
        notable = [t for t in TICKER_SECTOR if t not in prices and t not in ("generic",)]
        # FIXED: load ALL notable stocks (not just 60) so bottleneck tickers are always available
        prices.update(load_prices(notable, days=365))

    # 4. Forex
    if include_forex:
        _prog(progress_cb, "Loading forex pairs (major + EM)...", 0.26)
        prices.update(load_prices(list(FOREX_PAIRS.keys()), days=756))

    # 5. Commodities
    if include_commodities:
        _prog(progress_cb, "Loading commodities (energy, metals, agri)...", 0.31)
        prices.update(load_prices(list(COMMODITIES.keys()), days=756))

    # 6. Crypto
    if include_crypto:
        _prog(progress_cb, "Loading crypto universe...", 0.36)
        prices.update(load_prices(list(CRYPTO.keys()), days=365))

    # 7. IHSG
    if include_ihsg:
        _prog(progress_cb, "Loading IHSG + Indonesia stocks...", 0.40)
        prices.update(load_prices(list(IHSG_UNIVERSE.keys()), days=756))

    # 8. Country ETFs for global quad
    _prog(progress_cb, "Loading country ETFs (50 countries)...", 0.44)
    country_etfs = list({v[0] for v in COUNTRY_UNIVERSE.values()})
    prices.update(load_prices(country_etfs, days=756))
    snap["prices_loaded"] = len(prices)

    # 9. GIP
    _prog(progress_cb, "Running GIP model (G·I·P second derivative)...", 0.50)
    try:
        gip = GIPEngine().run(fred=fred, prices=prices)
    except Exception as e:
        logger.error(f"GIP error: {e}")
        raise
    snap["gip"] = gip
    snap["playbook"] = get_playbook(gip.structural_quad, gip.monthly_quad)

    # 10. Global Quad
    _prog(progress_cb, "Running Global Quad (50 countries)...", 0.58)
    global_quad = GlobalQuadEngine().run(prices=prices, us_gip_result=gip)
    snap["global"] = global_quad

    # 11. Risk Ranges — build OHLCV frames
    _prog(progress_cb, "Fetching OHLCV for Hurst risk ranges...", 0.64)
    rr_tickers = (
        list(MACRO_PROXIES.keys()) + list(US_SECTORS.keys()) +
        list(BONDS.keys()) + list(COMMODITIES.keys())[:10] +
        (list(CRYPTO.keys())[:6] if include_crypto else []) +
        ["DX-Y.NYB","EIDO","^JKSE"] +
        [t for t in TICKER_SECTOR if TICKER_SECTOR.get(t) in ("ai_optics","ai_power","ai_power_infra","precious_metals","defense")][:20]
    )
    rr_tickers = list(dict.fromkeys(rr_tickers))

    price_frames: Dict[str, pd.DataFrame] = {}
    try:
        import yfinance as yf
        raw = yf.download(rr_tickers, period="2y", progress=False, auto_adjust=True, timeout=30, threads=True)
        if not raw.empty:
            for t in rr_tickers:
                try:
                    if len(rr_tickers) == 1:
                        df = raw
                    else:
                        df = raw.xs(t, level=1, axis=1) if t in raw.columns.get_level_values(1) else pd.DataFrame()
                    if not df.empty and "Close" in df.columns:
                        cols = [c for c in ["Open","High","Low","Close","Volume"] if c in df.columns]
                        df = df[cols].apply(pd.to_numeric, errors="coerce").dropna(subset=["Close"])
                        price_frames[t] = df
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"OHLCV fetch partial: {e}")

    # Fallback: synthetic frames from close
    for t in rr_tickers:
        if t not in price_frames and t in prices:
            c = pd.to_numeric(prices[t], errors="coerce").dropna()
            if len(c) > 20:
                df = pd.DataFrame({"Open":c,"High":c*1.003,"Low":c*0.997,"Close":c,"Volume":np.nan})
                price_frames[t] = df

    snap["price_frames_count"] = len(price_frames)
    stress = _build_stress(prices, gip)
    rr_result = HurstRREngine().run(price_frames=price_frames, stress=stress)
    snap["risk_ranges"] = rr_result
    snap["stress"] = stress

    # 12. Scenarios
    _prog(progress_cb, "Discovering adaptive scenarios...", 0.80)
    scenarios = ScenarioEngine().run(
        structural_quad=gip.structural_quad,
        monthly_quad=gip.monthly_quad,
        features=gip.features,
        flip_hazard=gip.flip_hazard,
        data_coverage=gip.data_coverage,
    )
    snap["scenarios"] = scenarios

    # 13. Bottleneck Scanner
    _prog(progress_cb, "Scanning bottlenecks (all asset classes)...", 0.88)
    asset_ranges = rr_result.get("asset_ranges", {})
    btk = BottleneckEngine().run(
        prices=prices,
        quad_str=gip.structural_quad,
        quad_mon=gip.monthly_quad,
        benchmark="SPY",
        asset_ranges=asset_ranges,
    )
    snap["bottleneck"] = btk

    # Store prices subset for UI charts (close prices only — light)
    snap["prices"] = {k: v for k, v in prices.items() if isinstance(v, pd.Series) and len(v) > 10}
    snap["build_time_s"] = round(time.time() - t0, 1)
    snap["ok"] = True
    _prog(progress_cb, "Saving snapshot...", 0.96)
    save_snapshot(snap)
    _prog(progress_cb, "Done!", 1.0)
    logger.info(f"Built in {snap['build_time_s']}s. Prices: {snap['prices_loaded']}, RR: {snap['price_frames_count']}")
    return snap

def _build_stress(prices, gip) -> dict:
    def last(t):
        s = prices.get(t)
        if s is None: return None
        s = pd.to_numeric(s, errors="coerce").dropna()
        return float(s.iloc[-1]) if not s.empty else None

    def ret1m(t):
        s = prices.get(t)
        if s is None: return 0.0
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 22: return 0.0
        return float(s.iloc[-1]/s.iloc[-22]-1)

    # FIXED: explicit None/finite check instead of `or` on float
    vix_raw = last("^VIX")
    vix = vix_raw if (vix_raw is not None and math.isfinite(vix_raw)) else 18.0

    dxy_1m = ret1m("DX-Y.NYB")
    vol_stress = float(np.clip((vix-15.0)/25.0, 0.0, 1.0))
    shock = 0.5 if gip.structural_quad=="Q3" else 0.8 if gip.structural_quad=="Q4" else 0.2
    crowding = float(gip.features.get("proxy_share", 0.3))
    dollar_pres = float(np.clip(0.5+dxy_1m/0.04, 0.0, 1.0))
    tail_bid = float(np.clip((vix-20.0)/30.0, 0.0, 1.0))
    return dict(vol_stress=vol_stress, shock_penalty=shock*0.5,
                crowding=crowding, dollar_pressure=dollar_pres, tail_hedge_bid=tail_bid, vix=vix)

def get_or_build(force=False, max_age_h=4.0, **kw) -> dict:
    if not force:
        snap = load_snapshot(max_age_hours=max_age_h)
        if snap and snap.get("ok"): return snap
    return build_snapshot(**kw)
