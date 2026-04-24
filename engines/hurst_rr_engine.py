"""engines/hurst_rr_engine.py — Hedgeye Risk Range™ via Rescaled Range Analysis.

Three-duration framework:
  TRADE  = ≤3 weeks  → entry/exit timing
  TREND  = ≥3 months → intermediate cycle direction
  TAIL   = ≤3 years  → long-term conviction / regime shifts

LRR = Low End Risk Range → buy/add zone
TRR = Top End Risk Range → sell/trim zone

Hurst H > 0.5: trending  → WIDER range (don't fade momentum)
Hurst H < 0.5: mean-rev  → TIGHTER range (fade extremes)

Signal quality:
  A  = Bullish TRADE+TREND, near LRR, volume expanding → cleanest long
  B  = Bullish TREND only, TRADE mixed → add on dips
  C  = Extended (near TRR) → wait for pullback
  S-A = Bearish TRADE+TREND, near TRR → cleanest short
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from config.settings import (
    RR_TRADE_LOOKBACK, RR_TREND_LOOKBACK, RR_TAIL_LOOKBACK,
    RR_TRADE_SIGMA, RR_TREND_SIGMA, RR_TAIL_SIGMA, RR_HURST_SCALE,
)


# ---------------------------------------------------------------------------
# Hurst Exponent via R/S Analysis
# ---------------------------------------------------------------------------

def hurst_rs(close: np.ndarray, min_chunk: int = 8) -> float:
    n = len(close)
    if n < 2 * min_chunk:
        return 0.5
    try:
        log_ret = np.diff(np.log(np.clip(close, 1e-10, None)))
        chunk_sizes = []
        k = min_chunk
        while k <= n // 4:
            chunk_sizes.append(k)
            k = max(k + 1, int(k * 1.6))
        if len(chunk_sizes) < 2:
            return 0.5
        rs_vals, ns_vals = [], []
        for cs in chunk_sizes:
            n_chunks = len(log_ret) // cs
            if n_chunks < 2:
                continue
            rs_c = []
            for i in range(n_chunks):
                seg = log_ret[i*cs:(i+1)*cs]
                mu  = np.mean(seg)
                dev = np.cumsum(seg - mu)
                R   = dev.max() - dev.min()
                S   = np.std(seg, ddof=1)
                if S > 1e-10 and math.isfinite(R/S):
                    rs_c.append(R/S)
            if rs_c:
                rs_vals.append(float(np.mean(rs_c)))
                ns_vals.append(float(cs))
        if len(rs_vals) < 2:
            return 0.5
        slope = float(np.polyfit(np.log(ns_vals), np.log(rs_vals), 1)[0])
        return float(np.clip(slope, 0.05, 0.95))
    except Exception:
        return 0.5


# ---------------------------------------------------------------------------
# Single-duration range
# ---------------------------------------------------------------------------

DURATION_CONFIG = {
    "trade": {"lb": RR_TRADE_LOOKBACK, "vol_w": 10, "hmin": 8,  "sigma": RR_TRADE_SIGMA, "ewm": 10},
    "trend": {"lb": RR_TREND_LOOKBACK, "vol_w": 21, "hmin": 12, "sigma": RR_TREND_SIGMA, "ewm": 21},
    "tail":  {"lb": RR_TAIL_LOOKBACK,  "vol_w": 63, "hmin": 32, "sigma": RR_TAIL_SIGMA,  "ewm": 34},
}


def _duration_range(
    close: np.ndarray, high: np.ndarray, low: np.ndarray, volume: np.ndarray,
    cfg: dict, stress: float = 1.0, down_asym: float = 1.0, up_asym: float = 1.0,
) -> dict:
    n  = len(close)
    lb = min(cfg["lb"], n - 1)
    if lb < 8:
        return _empty_range()

    c = close[-lb:]; h = high[-lb:]; l = low[-lb:]
    v = volume[-lb:] if volume is not None and len(volume) >= lb else None
    px = float(c[-1])
    if not math.isfinite(px) or px <= 0:
        return _empty_range()

    # Fair value midpoint (EMA)
    span = cfg["ewm"]
    wts  = np.exp(-np.arange(lb)[::-1] / span)
    wts /= wts.sum()
    mid  = float(np.dot(wts, c))

    # Realized vol
    vw  = min(cfg["vol_w"], lb - 1)
    lr  = np.diff(np.log(np.clip(c[-vw-1:], 1e-10, None)))
    rv  = float(np.std(lr)) if len(lr) > 1 else 0.01
    rv  = max(rv, 0.003)

    # ATR
    prev = c[:-1]; atr_arr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - prev), np.abs(l[1:] - prev)))
    atr  = float(np.mean(atr_arr[-vw:])) / max(px, 1e-10) if len(atr_arr) >= vw else rv
    atr  = max(atr, 0.003)

    sigma = 0.55 * rv + 0.45 * atr

    # Hurst
    atr_fb = False
    if lb >= 2 * cfg["hmin"]:
        H = hurst_rs(c, cfg["hmin"])
        if not (0.1 <= H <= 0.9): H = 0.5
    else:
        H = 0.5; atr_fb = True

    hurst_adj = 1.0 + RR_HURST_SCALE * (H - 0.5)
    width = cfg["sigma"] * sigma * hurst_adj * stress

    lrr = mid * (1.0 - width * down_asym)
    trr = mid * (1.0 + width * up_asym)

    # Higher highs / lower lows detection
    half = max(lb // 3, 4)
    hh = bool(np.max(h[-half:]) > np.max(h[:half]) * 1.003)
    hl = bool(np.min(l[-half:]) > np.min(l[:half]) * 1.003)
    lh = bool(np.max(h[-half:]) < np.max(h[:half]) * 0.997)
    ll = bool(np.min(l[-half:]) < np.min(l[:half]) * 0.997)

    signal = "bullish" if (hh and hl) else "bearish" if (lh and ll) else "neutral"

    # Stretch
    band = max(trr - lrr, 1e-9)
    pos  = (px - lrr) / band
    stretch = "overbought" if pos >= 0.90 else "oversold" if pos <= 0.10 else \
              "extended"   if pos >= 0.70 else "reset_zone" if pos <= 0.30 else "neutral"

    # Volume confirm
    vc = 0.5
    if v is not None and len(v) >= 10:
        avg_v = float(np.mean(v[-10:]))
        if avg_v > 0:
            vc = float(np.clip(0.25 + 0.75 * min(float(v[-1])/avg_v, 2.0)/2.0, 0.0, 1.0))

    return dict(
        lrr=lrr, trr=trr, mid=mid, px=px,
        hurst=H, sigma=sigma, width_pct=width,
        signal=signal, stretch=stretch,
        hh=hh, hl=hl, lh=lh, ll=ll,
        volume_confirm=vc, atr_fallback=atr_fb,
        bar_count=n,
    )


def _empty_range() -> dict:
    return dict(lrr=float("nan"), trr=float("nan"), mid=float("nan"), px=float("nan"),
                hurst=0.5, sigma=float("nan"), width_pct=float("nan"),
                signal="neutral", stretch="neutral",
                hh=False, hl=False, lh=False, ll=False,
                volume_confirm=0.5, atr_fallback=True, bar_count=0)


# ---------------------------------------------------------------------------
# Alerts (Hedgeye sizing rules)
# ---------------------------------------------------------------------------

def _alerts(trade: dict, trend: dict, tail: dict) -> List[dict]:
    px = trade.get("px", float("nan"))
    if not math.isfinite(px):
        return []
    alerts = []

    # Cleanest long: Bullish TRADE+TREND + near LRR
    if trade["signal"] == "bullish" and trend["signal"] == "bullish":
        if trade["stretch"] in ("oversold","reset_zone"):
            alerts.append(dict(type="BUY_SETUP", duration="TRADE+TREND", action="BUY/ADD",
                               size_bps=75, priority="HIGH",
                               note=f"Bullish T+T, near TRADE LRR {trade['lrr']:.4f}. Add 50-100bps."))

    # Bullish breakout above TRR
    if math.isfinite(trade["trr"]) and px > trade["trr"] and trade["signal"] == "bullish" and trend["signal"] == "bullish":
        alerts.append(dict(type="BULLISH_BREAKOUT", duration="TRADE", action="ADD",
                           size_bps=175, priority="HIGH",
                           note=f"Breakout above TRADE TRR {trade['trr']:.4f}. Add 150-200bps."))

    # Trend breakout above TREND TRR
    if math.isfinite(trend["trr"]) and px > trend["trr"] and trend["signal"] == "bullish":
        alerts.append(dict(type="TREND_BREAKOUT", duration="TREND", action="ADD",
                           size_bps=100, priority="HIGH",
                           note=f"Breakout above TREND TRR {trend['trr']:.4f}."))

    # Near TRR bearish → trim
    if trade["stretch"] in ("overbought","extended") and trend["signal"] == "bearish":
        alerts.append(dict(type="TRIM_SETUP", duration="TRADE", action="TRIM",
                           size_bps=50, priority="MEDIUM",
                           note=f"Overbought near TRR {trade['trr']:.4f} with Bearish TREND."))

    # TREND LRR break = EXIT
    if math.isfinite(trend["lrr"]) and px < trend["lrr"] and trend["signal"] == "bearish":
        alerts.append(dict(type="TREND_BREAKDOWN", duration="TREND", action="EXIT",
                           size_bps=100, priority="CRITICAL",
                           note=f"Price broke TREND LRR {trend['lrr']:.4f}. EXIT — not trim."))

    # TAIL breakdown = structural exit
    if math.isfinite(tail["lrr"]) and px < tail["lrr"]:
        alerts.append(dict(type="TAIL_BREAKDOWN", duration="TAIL", action="EXIT_ALL",
                           size_bps=100, priority="CRITICAL",
                           note=f"Price broke TAIL LRR {tail['lrr']:.4f}. Structural regime shift."))

    return sorted(alerts, key=lambda a: {"CRITICAL":0,"HIGH":1,"MEDIUM":2}.get(a["priority"],3))


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

class HurstRREngine:
    """Hedgeye Risk Range™ via Rescaled Range Analysis. Three durations per asset."""

    def run(
        self,
        price_frames: Dict[str, pd.DataFrame],
        stress: Optional[Dict[str, float]] = None,
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, object]:
        stress = stress or {}
        vs    = float(stress.get("vol_stress",      0.0))
        sh    = float(stress.get("shock_penalty",   0.0))
        cr    = float(stress.get("crowding",        0.0))
        dp    = float(stress.get("dollar_pressure", 0.0))
        th    = float(stress.get("tail_hedge_bid",  0.5))

        scalar   = 1.0 + 0.30*sh + 0.20*vs + 0.10*cr
        d_asym   = 1.0 + 0.20*dp + 0.15*th
        u_asym   = max(0.80, 1.0 - 0.08*min(dp, 0.8))

        keys = symbols or sorted(price_frames.keys())
        asset_ranges: Dict[str, dict] = {}

        for sym in keys:
            df = price_frames.get(sym)
            if df is None or df.empty:
                continue
            df = df.copy()
            df.columns = [str(c[-1] if isinstance(c, tuple) else c) for c in df.columns]
            try:
                cc = "Close" if "Close" in df.columns else df.select_dtypes(include=[np.number]).columns[0]
                close = pd.to_numeric(df[cc], errors="coerce").dropna().values
                high  = pd.to_numeric(df["High"],   errors="coerce").dropna().values if "High"   in df.columns else close
                low   = pd.to_numeric(df["Low"],    errors="coerce").dropna().values if "Low"    in df.columns else close
                vol   = pd.to_numeric(df["Volume"], errors="coerce").dropna().values if "Volume" in df.columns else None
            except Exception:
                continue

            n = len(close)
            if n < 20: continue
            high = high[-n:] if len(high)>=n else np.full(n, close[-1])
            low  = low[-n:]  if len(low) >=n else np.full(n, close[-1])
            if vol is not None: vol = vol[-n:] if len(vol)>=n else None

            px = float(close[-1])
            if not math.isfinite(px) or px <= 0: continue

            trd = _duration_range(close,high,low,vol, DURATION_CONFIG["trade"], scalar,d_asym,u_asym)
            trn = _duration_range(close,high,low,vol, DURATION_CONFIG["trend"], scalar,d_asym,u_asym)
            tal = _duration_range(close,high,low,vol, DURATION_CONFIG["tail"],  scalar,d_asym,u_asym)

            sigs = [trd["signal"], trn["signal"], tal["signal"]]
            bc   = sigs.count("bullish"); be = sigs.count("bearish")
            comp = "bullish" if bc>=2 else "bearish" if be>=2 else "mixed" if bc==1 and be==1 else "neutral"

            # Setup quality (Hedgeye A/B/C system)
            if comp=="bullish" and trd["stretch"] in ("oversold","reset_zone") and trd["volume_confirm"]>0.6:
                quality="A"
            elif comp=="bullish" and trd["stretch"] in ("oversold","reset_zone"):
                quality="B"
            elif comp=="bullish":
                quality="C"
            elif comp=="bearish" and trd["stretch"] in ("overbought","extended") and trd["volume_confirm"]>0.6:
                quality="short_A"
            elif comp=="bearish" and trd["stretch"] in ("overbought","extended"):
                quality="short_B"
            else:
                quality="none"

            alerts = _alerts(trd, trn, tal)

            asset_ranges[sym] = dict(
                trade=trd, trend=trn, tail=tal,
                composite=comp, quality=quality, px=px,
                alerts=alerts,
                # Flat accessors for UI
                trade_lrr=trd["lrr"], trade_trr=trd["trr"], trade_signal=trd["signal"],
                trend_lrr=trn["lrr"], trend_trr=trn["trr"], trend_signal=trn["signal"],
                tail_lrr=tal["lrr"],  tail_trr=tal["trr"],  tail_signal=tal["signal"],
                trade_stretch=trd["stretch"], trend_stretch=trn["stretch"],
                hurst_trade=trd["hurst"], hurst_trend=trn["hurst"],
                volume_confirm=trd["volume_confirm"],
            )

        total = len(asset_ranges)
        return dict(
            asset_ranges=asset_ranges,
            model="hurst_rescaled_range_v2",
            stress=dict(scalar=scalar, d_asym=d_asym, u_asym=u_asym),
            summary=dict(
                total=total,
                bullish=sum(1 for v in asset_ranges.values() if v["composite"]=="bullish"),
                bearish=sum(1 for v in asset_ranges.values() if v["composite"]=="bearish"),
                a_quality=sum(1 for v in asset_ranges.values() if v["quality"] in ("A","short_A")),
                critical=sum(1 for v in asset_ranges.values() for a in v["alerts"] if a.get("priority")=="CRITICAL"),
            ),
        )
