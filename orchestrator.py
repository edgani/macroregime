"""orchestrator.py — Builds the full MacroRegime snapshot.

Called by:
  - app.py on startup (loads from cache or snapshot)
  - "Refresh" button (fetches live data, rebuilds)

Architecture:
  1. Load data (FRED + prices)
  2. Run GIP engine → structural + monthly quad
  3. Run global quad engine → 50 countries
  4. Run Hurst Risk Range engine → TRADE/TREND/TAIL per asset
  5. Run scenario engine → adaptive scenario discovery
  6. Run bottleneck scanner → regime-appropriate bottleneck plays
  7. Save snapshot → fast next open
"""
from __future__ import annotations

import time
import logging
from typing import Optional, Dict, Callable
import numpy as np
import pandas as pd

from data.loader import (
    load_fred, load_asset_universe, load_prices,
    save_snapshot, load_snapshot, snapshot_age_str,
)
from engines.gip_engine import GIPEngine, get_playbook
from engines.global_quad_engine import GlobalQuadEngine
from engines.hurst_rr_engine import HurstRREngine
from engines.scenario_engine import ScenarioEngine
from engines.bottleneck_engine import BottleneckEngine
from config.settings import (
    MACRO_PROXIES, US_SECTORS, US_FACTORS, FOREX_PAIRS,
    COMMODITIES, CRYPTO, BONDS, IHSG_TICKERS,
)

logger = logging.getLogger(__name__)


def build_snapshot(
    progress_cb: Optional[Callable[[str, float], None]] = None,
    include_crypto: bool = True,
    include_us_stocks: bool = True,
) -> dict:
    """
    Build full snapshot from live data.
    progress_cb(message, fraction) for Streamlit progress bar.
    """
    def prog(msg, frac):
        if progress_cb:
            progress_cb(msg, frac)
        logger.info(f"[{frac:.0%}] {msg}")

    t0 = time.time()
    snap: dict = {"ts": t0, "ok": False}

    # ----------------------------------------------------------------
    # 1. Load macro data
    # ----------------------------------------------------------------
    prog("Loading FRED macro data...", 0.05)
    fred = load_fred(months=36)
    snap["fred_coverage"] = len(fred)

    # ----------------------------------------------------------------
    # 2. Load prices (staged for light loading)
    # ----------------------------------------------------------------
    prog("Loading core prices (SPY, GLD, TLT, DXY...)...", 0.12)
    core_tickers = list(MACRO_PROXIES.keys()) + list(BONDS.keys()) + ["DX-Y.NYB"]
    prices = load_prices(core_tickers, days=756)

    if include_us_stocks:
        prog("Loading US sectors + factors...", 0.20)
        us_t = list(US_SECTORS.keys()) + list(US_FACTORS.keys())
        prices.update(load_prices(us_t, days=756))

    prog("Loading forex...", 0.28)
    prices.update(load_prices(FOREX_PAIRS, days=756))

    prog("Loading commodities...", 0.35)
    prices.update(load_prices(list(COMMODITIES.keys()), days=756))

    if include_crypto:
        prog("Loading crypto...", 0.40)
        prices.update(load_prices(list(CRYPTO.keys()), days=365))

    prog("Loading IHSG + EM...", 0.44)
    prices.update(load_prices(list(IHSG_TICKERS.keys()), days=756))

    # Load country ETFs for global quad
    from config.settings import COUNTRY_UNIVERSE
    country_etfs = list({v[0] for v in COUNTRY_UNIVERSE.values()})
    prog("Loading country ETFs (50 countries)...", 0.48)
    prices.update(load_prices(country_etfs, days=756))

    snap["prices_loaded"] = len(prices)

    # ----------------------------------------------------------------
    # 3. GIP Engine
    # ----------------------------------------------------------------
    prog("Running GIP model (Growth + Inflation + Policy)...", 0.55)
    gip = GIPEngine().run(fred=fred, prices=prices)
    snap["gip"] = gip
    snap["playbook"] = get_playbook(gip.structural_quad, gip.monthly_quad)

    # ----------------------------------------------------------------
    # 4. Global Quad Engine
    # ----------------------------------------------------------------
    prog("Running Global Quad (50+ countries)...", 0.62)
    global_quad = GlobalQuadEngine().run(prices=prices, us_gip_result=gip)
    snap["global"] = global_quad

    # ----------------------------------------------------------------
    # 5. Hurst Risk Range Engine
    # ----------------------------------------------------------------
    prog("Computing TRADE/TREND/TAIL Risk Ranges (Hurst)...", 0.68)

    # Build OHLCV frames for key assets
    import yfinance as yf
    rr_tickers = (
        list(MACRO_PROXIES.keys()) + list(US_SECTORS.keys()) +
        list(BONDS.keys()) + list(COMMODITIES.keys())[:8] +
        (list(CRYPTO.keys())[:4] if include_crypto else []) +
        ["DX-Y.NYB"]
    )
    try:
        prog("Fetching OHLCV for risk ranges...", 0.70)
        raw_ohlcv = yf.download(rr_tickers, period="2y", progress=False, auto_adjust=True, timeout=30)
        price_frames: Dict[str, pd.DataFrame] = {}
        for t in rr_tickers:
            try:
                if len(rr_tickers) == 1:
                    df = raw_ohlcv
                else:
                    df = raw_ohlcv.xs(t, level=1, axis=1) if t in raw_ohlcv.columns.get_level_values(1) else pd.DataFrame()
                if not df.empty and "Close" in df.columns:
                    df = df[["Open","High","Low","Close","Volume"]].apply(pd.to_numeric, errors="coerce").dropna(subset=["Close"])
                    price_frames[t] = df
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"OHLCV fetch failed: {e}")
        # Fallback: build synthetic frames from close prices
        price_frames = {}
        for t, cls in prices.items():
            if t in rr_tickers:
                df = pd.DataFrame({"Close": cls, "Open": cls, "High": cls, "Low": cls, "Volume": np.nan})
                price_frames[t] = df

    stress = _build_stress(prices, gip)
    rr_result = HurstRREngine().run(price_frames=price_frames, stress=stress)
    snap["risk_ranges"] = rr_result
    snap["price_frames_count"] = len(price_frames)

    # ----------------------------------------------------------------
    # 6. Scenario Engine
    # ----------------------------------------------------------------
    prog("Discovering adaptive scenarios...", 0.82)
    scenarios = ScenarioEngine().run(
        structural_quad=gip.structural_quad,
        monthly_quad=gip.monthly_quad,
        features=gip.features,
        flip_hazard=gip.flip_hazard,
        data_coverage=gip.data_coverage,
    )
    snap["scenarios"] = scenarios

    # ----------------------------------------------------------------
    # 7. Bottleneck Scanner
    # ----------------------------------------------------------------
    prog("Scanning for bottleneck plays...", 0.88)
    # Add notable single-stocks to scan (use close prices)
    from config.settings import TICKER_SECTOR
    notable_tickers = [t for t in TICKER_SECTOR if t not in ("SPY","QQQ","IWM","TLT")]
    prices.update(load_prices(notable_tickers, days=252))

    btk = BottleneckEngine().run(
        prices=prices,
        quad_str=gip.structural_quad,
        quad_mon=gip.monthly_quad,
        benchmark="SPY",
    )
    snap["bottleneck"] = btk

    # ----------------------------------------------------------------
    # 8. Finalise
    # ----------------------------------------------------------------
    snap["build_time_s"] = round(time.time() - t0, 1)
    snap["ok"] = True
    prog("Saving snapshot...", 0.95)
    save_snapshot(snap)
    prog("Done!", 1.0)
    logger.info(f"Snapshot built in {snap['build_time_s']}s")

    return snap


def _build_stress(prices, gip) -> dict:
    """Derive stress scalars from current market data."""
    vix_s = prices.get("^VIX") or prices.get("VIX")
    vix = float(pd.to_numeric(vix_s, errors="coerce").dropna().iloc[-1]) if vix_s is not None and len(pd.to_numeric(vix_s, errors="coerce").dropna()) > 0 else 18.0

    dxy_s = prices.get("DX-Y.NYB") or prices.get("UUP")
    dxy_1m = 0.0
    if dxy_s is not None:
        s = pd.to_numeric(dxy_s, errors="coerce").dropna()
        if len(s) > 22:
            dxy_1m = float(s.iloc[-1]/s.iloc[-22]-1)

    vol_stress = float(np.clip((vix - 15.0) / 25.0, 0.0, 1.0))
    shock = 1.0 if gip.structural_quad == "Q4" else 0.5 if gip.structural_quad == "Q3" else 0.2
    crowding = float(gip.features.get("proxy_share", 0.3))
    dollar_pressure = float(np.clip(0.5 + dxy_1m / 0.04, 0.0, 1.0))
    tail_hedge_bid = float(np.clip((vix - 20.0) / 30.0, 0.0, 1.0))

    return dict(
        vol_stress=vol_stress,
        shock_penalty=shock * 0.5,
        crowding=crowding,
        dollar_pressure=dollar_pressure,
        tail_hedge_bid=tail_hedge_bid,
    )


def get_or_build_snapshot(force_rebuild: bool = False, max_age_hours: float = 4.0, **kwargs) -> dict:
    """Fast path: load snapshot if fresh enough, else rebuild."""
    if not force_rebuild:
        snap = load_snapshot(max_age_hours=max_age_hours)
        if snap and snap.get("ok"):
            return snap
    return build_snapshot(**kwargs)
