"""engines/leveraged_etf_engine.py — Leveraged ETF Flow Engine v2

Robust yfinance fetch with fallback AUM estimation.
Fixes v1: yfinance .info() often returns empty in cloud/headless env.
"""
import logging, math
from typing import Dict
import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Major leveraged ETFs — long & short
LEV_ETF_UNIVERSE = {
    # 3x Equity
    "TQQQ": {"direction": "long",  "leverage": 3, "asset": "nasdaq100"},
    "UPRO": {"direction": "long",  "leverage": 3, "asset": "sp500"},
    "SPXL": {"direction": "long",  "leverage": 3, "asset": "sp500"},
    "UDOW": {"direction": "long",  "leverage": 3, "asset": "dow30"},
    "UMDD": {"direction": "long",  "leverage": 3, "asset": "midcap"},
    "URTY": {"direction": "long",  "leverage": 3, "asset": "russell2k"},
    # 2x Equity
    "QLD":  {"direction": "long",  "leverage": 2, "asset": "nasdaq100"},
    "SSO":  {"direction": "long",  "leverage": 2, "asset": "sp500"},
    "DDM":  {"direction": "long",  "leverage": 2, "asset": "dow30"},
    "MVV":  {"direction": "long",  "leverage": 2, "asset": "midcap"},
    "UWM":  {"direction": "long",  "leverage": 2, "asset": "russell2k"},
    # 3x Inverse Equity
    "SQQQ": {"direction": "short", "leverage": 3, "asset": "nasdaq100"},
    "SPXS": {"direction": "short", "leverage": 3, "asset": "sp500"},
    "SPXU": {"direction": "short", "leverage": 3, "asset": "sp500"},
    "SDOW": {"direction": "short", "leverage": 3, "asset": "dow30"},
    "SMDD": {"direction": "short", "leverage": 3, "asset": "midcap"},
    "SRTY": {"direction": "short", "leverage": 3, "asset": "russell2k"},
    # 2x Inverse Equity
    "QID":  {"direction": "short", "leverage": 2, "asset": "nasdaq100"},
    "SDS":  {"direction": "short", "leverage": 2, "asset": "sp500"},
    "DXD":  {"direction": "short", "leverage": 2, "asset": "dow30"},
    "MZZ":  {"direction": "short", "leverage": 2, "asset": "midcap"},
    "TWM":  {"direction": "short", "leverage": 2, "asset": "russell2k"},
    # Crypto
    "BITU": {"direction": "long",  "leverage": 2, "asset": "bitcoin"},
    "BITO": {"direction": "long",  "leverage": 1, "asset": "bitcoin"},
}

def _safe_float(v):
    if v is None: return None
    try:
        if isinstance(v, pd.Series): v = v.iloc[0]
        f = float(v)
        return f if math.isfinite(f) else None
    except: return None

def _estimate_aum(ticker: str, hist: pd.DataFrame) -> float:
    """Estimate AUM in $B when yfinance info fails.
    Proxy: avg daily dollar volume * 20 (assumes 20-day avg holding).
    """
    if hist is None or hist.empty: return 0.0
    h = hist.copy()
    if "Close" not in h.columns or "Volume" not in h.columns:
        return 0.0
    h["Close"] = pd.to_numeric(h["Close"], errors="coerce")
    h["Volume"] = pd.to_numeric(h["Volume"], errors="coerce")
    h = h.dropna(subset=["Close", "Volume"])
    if len(h) < 5: return 0.0
    adv = (h["Close"] * h["Volume"]).mean()
    if not math.isfinite(adv): return 0.0
    aum_b = (adv * 20) / 1e9
    return float(aum_b) if math.isfinite(aum_b) else 0.0

def _fetch_ticker_info(ticker: str) -> Dict:
    """Fetch yfinance info with timeout. Returns dict with aum_b or None."""
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        aum = info.get("totalAssets")
        if aum is None:
            aum = info.get("assetsUnderManagement")
        if aum is not None:
            aum_b = float(aum) / 1e9
            if math.isfinite(aum_b) and aum_b > 0:
                return {"aum_b": round(aum_b, 2), "source": "info"}
    except Exception as e:
        logger.debug(f"yfinance info failed for {ticker}: {e}")
    return {"aum_b": None, "source": "info_failed"}

class LeveragedETFEngine:
    def run(self, prices: Dict[str, pd.Series] = None) -> Dict:
        tickers = list(LEV_ETF_UNIVERSE.keys())
        results = []
        total_long_b = 0.0
        total_short_b = 0.0
        total_single_crypto_b = 0.0
        top_longs = []
        top_shorts = []

        # Batch download history for all tickers (6mo for ADV calc)
        try:
            hist_all = yf.download(tickers, period="6mo", progress=False, auto_adjust=True, timeout=25, threads=True)
        except Exception as e:
            logger.warning(f"yfinance batch download failed: {e}")
            hist_all = pd.DataFrame()

        for ticker in tickers:
            meta = LEV_ETF_UNIVERSE[ticker]
            # Layer 1: Try info AUM
            info_res = _fetch_ticker_info(ticker)
            aum_b = info_res["aum_b"]
            source = info_res["source"]

            # Layer 2: Fallback estimate from history ADV
            if (aum_b is None or aum_b <= 0) and not hist_all.empty:
                try:
                    if len(tickers) == 1:
                        df = hist_all
                    else:
                        df = hist_all.xs(ticker, level=1, axis=1) if ticker in hist_all.columns.get_level_values(1) else pd.DataFrame()
                    est = _estimate_aum(ticker, df)
                    if est > 0:
                        aum_b = est
                        source = "estimate"
                except Exception as e:
                    logger.debug(f"Estimate AUM failed for {ticker}: {e}")

            # Layer 3: Last resort heuristic from price magnitude
            if (aum_b is None or aum_b <= 0) and prices and ticker in prices:
                try:
                    px = _safe_float(prices[ticker].iloc[-1])
                    if px and px > 0:
                        aum_b = 0.5 if px < 20 else 1.5 if px < 60 else 3.0
                        source = "heuristic"
                except Exception:
                    pass

            if aum_b is None or aum_b <= 0:
                continue

            direction = meta["direction"]
            lev = meta["leverage"]
            notional = aum_b * lev

            entry = {
                "ticker": ticker,
                "aum_b": round(aum_b, 2),
                "notional_b": round(notional, 2),
                "direction": direction,
                "leverage": lev,
                "asset": meta["asset"],
                "source": source,
            }
            results.append(entry)

            if direction == "long":
                total_long_b += notional
                top_longs.append(entry)
            else:
                total_short_b += notional
                top_shorts.append(entry)

            if meta["asset"] == "bitcoin" and lev == 1:
                total_single_crypto_b += aum_b

        if not results:
            return {
                "ok": False,
                "total_mcap_b": None,
                "note": "Fetch gagal: yfinance fetch failed — semua ETF return 0 AUM",
            }

        total = total_long_b + total_short_b + total_single_crypto_b
        long_pct = (total_long_b / total * 100) if total > 0 else 0
        short_pct = (total_short_b / total * 100) if total > 0 else 0

        rebal = "LOW"
        if total > 10:
            ratio = max(long_pct, short_pct) / 100.0
            if ratio > 0.75: rebal = "HIGH"
            elif ratio > 0.65: rebal = "MEDIUM"

        top_longs.sort(key=lambda x: x["notional_b"], reverse=True)
        top_shorts.sort(key=lambda x: x["notional_b"], reverse=True)

        return {
            "ok": True,
            "total_mcap_b": round(total, 2),
            "long_exposure_b": round(total_long_b, 2),
            "short_exposure_b": round(total_short_b, 2),
            "single_crypto_b": round(total_single_crypto_b, 2),
            "long_pct": round(long_pct, 1),
            "short_pct": round(short_pct, 1),
            "rebalancing_pressure": rebal,
            "is_ath": False,
            "top_longs": top_longs[:5],
            "top_shorts": top_shorts[:5],
            "all": results,
            "note": f"{len(results)} ETFs loaded · mix of info/estimate/heuristic",
        }