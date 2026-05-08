"""engines/leveraged_etf_engine.py — Leveraged ETF AUM & Flow Tracker

Fetch real AUM data dari yfinance untuk semua major leveraged ETFs.
Compute long vs short exposure breakdown.
Deteksi ATH, rate of change, dan mechanical rebalancing pressure.

Output masuk ke snap["leveraged_etf"] dan digunakan di Dashboard panel.

ETF Universe (Tier 1 Alpha tracks these):
  LONG (2x/3x bull):  TQQQ, UPRO, SPXL, UDOW, SOXL, TNA, LABU, FNGU, NAIL, DFEN, UTSL, MIDU, URTY
  SHORT (2x/3x bear): SQQQ, SPXU, SDOW, SOXS, TZA, LABD, FNGD, SRTY
  SINGLE STOCK/CRYPTO: NVDL, TSLL, MSTX, BITX, CONL

Note: yfinance "info" field berisi "totalAssets" = AUM dalam USD.
"""
from __future__ import annotations

import math
import time
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── ETF Universe ─────────────────────────────────────────────────────────────
LONG_ETFS: List[str] = [
    "TQQQ",   # 3x QQQ
    "UPRO",   # 3x SPY
    "SPXL",   # 3x S&P 500
    "UDOW",   # 3x Dow
    "SOXL",   # 3x Semiconductors
    "TNA",    # 3x IWM Small Cap
    "LABU",   # 3x Biotech
    "NAIL",   # 3x Homebuilders
    "DFEN",   # 3x Aerospace & Defense
    "UTSL",   # 3x Utilities
    "MIDU",   # 3x Mid Cap
    "URTY",   # 3x Russell 2000
    "SPXS_BULL",  # placeholder, skip
    "ROM",    # 2x Tech
    "SSO",    # 2x S&P 500
    "QLD",    # 2x QQQ
    "UWM",    # 2x IWM
    "SAA",    # 2x Small Cap
    "MVV",    # 2x Mid Cap
    "UXI",    # 2x Industrials
    "RXL",    # 2x Healthcare
    "DIG",    # 2x Energy
    "UYG",    # 2x Financials
    "DDM",    # 2x Dow
]

SHORT_ETFS: List[str] = [
    "SQQQ",   # 3x short QQQ
    "SPXU",   # 3x short SPY
    "SDOW",   # 3x short Dow
    "SOXS",   # 3x short Semiconductors
    "TZA",    # 3x short IWM
    "LABD",   # 3x short Biotech
    "SRTY",   # 3x short Russell 2000
    "FNGD",   # 3x short FANG
    "SDS",    # 2x short S&P
    "QID",    # 2x short QQQ
    "SDD",    # 2x short Small Cap
    "MZZ",    # 2x short Mid Cap
    "REW",    # 2x short Tech
    "SKF",    # 2x short Financials
    "DUG",    # 2x short Energy
    "SMN",    # 2x short Materials
]

SINGLE_CRYPTO_ETFS: List[str] = [
    "NVDL",   # 2x NVDA
    "TSLL",   # 2x TSLA
    "MSTX",   # 2x MicroStrategy
    "BITX",   # 2x Bitcoin
    "CONL",   # 2x Coinbase
    "MSFO",   # 2x Microsoft
    "AAPU",   # 2x Apple
    "AMZU",   # 2x Amazon
    "GOOG",   # skip (not levered), placeholder
    "IBIT",   # Bitcoin ETF (1x)
    "FBTC",   # Bitcoin ETF (1x)
]

# Clean up placeholders
LONG_ETFS = [t for t in LONG_ETFS if "BULL" not in t and "GOOG" not in t]
SINGLE_CRYPTO_ETFS = [t for t in SINGLE_CRYPTO_ETFS if "GOOG" not in t]


def _fetch_aum_yfinance(tickers: List[str]) -> Dict[str, float]:
    """
    Fetch AUM (totalAssets) dari yfinance untuk list tickers.
    Returns dict: {ticker: aum_in_USD}
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance tidak tersedia. pip install yfinance.")
        return {}

    aum_map: Dict[str, float] = {}
    # Batch fetch lebih cepat
    tickers_clean = [t for t in tickers if t]

    for ticker in tickers_clean:
        try:
            info = yf.Ticker(ticker).info
            assets = info.get("totalAssets") or info.get("netAssets") or 0
            if assets and isinstance(assets, (int, float)) and math.isfinite(assets) and assets > 0:
                aum_map[ticker] = float(assets)
        except Exception as e:
            logger.debug(f"AUM fetch failed for {ticker}: {e}")
            continue

    return aum_map


def _to_billions(usd: float) -> float:
    """Convert USD → Billions, rounded 1dp."""
    return round(usd / 1e9, 1)


def _compute_historical_aum(
    prices: Dict[str, pd.Series],
    tickers: List[str],
) -> Optional[float]:
    """
    Fallback: estimate AUM dari price × average shares outstanding proxy.
    Hanya dipakai kalau yfinance gagal total.
    """
    # Tidak bisa compute tanpa shares outstanding data
    return None


class LeveragedETFEngine:
    """
    Fetch dan aggregate leveraged ETF AUM data.
    
    Output snap["leveraged_etf"]:
      total_mcap_b: float          (total AUM semua levered ETFs, dalam $B)
      long_exposure_b: float       ($B long/bull ETFs)
      short_exposure_b: float      ($B short/bear ETFs)
      single_crypto_b: float       ($B single stock + crypto ETFs)
      long_pct: float              (% long dari total)
      short_pct: float             (% short dari total)
      is_ath: bool                 (apakah total AUM di ATH berdasarkan hist)
      top_longs: List[dict]        (top 5 long ETFs by AUM)
      top_shorts: List[dict]       (top 5 short ETFs by AUM)
      yoy_change_b: float | None   (YoY AUM change jika ada history)
      rebalancing_pressure: str    (HIGH / MEDIUM / LOW — dari daily return SPY)
      note: str
    """

    def __init__(self, cache_ttl_hours: float = 6.0):
        self.cache_ttl = cache_ttl_hours * 3600
        self._cache: Optional[Dict] = None
        self._cache_ts: float = 0.0

    def run(
        self,
        prices: Optional[Dict[str, pd.Series]] = None,
        force_refresh: bool = False,
    ) -> Dict:
        """
        Main run. Cache 6 jam karena AUM data tidak berubah cepat.
        """
        # Cache check
        if (
            not force_refresh
            and self._cache is not None
            and (time.time() - self._cache_ts) < self.cache_ttl
        ):
            return self._cache

        # ── Fetch AUM ─────────────────────────────────────────────────────
        logger.info("Fetching leveraged ETF AUM from yfinance...")
        
        long_aum   = _fetch_aum_yfinance(LONG_ETFS)
        short_aum  = _fetch_aum_yfinance(SHORT_ETFS)
        single_aum = _fetch_aum_yfinance(SINGLE_CRYPTO_ETFS)

        # ── Aggregate ─────────────────────────────────────────────────────
        total_long_usd   = sum(long_aum.values())
        total_short_usd  = sum(short_aum.values())
        total_single_usd = sum(single_aum.values())
        total_usd        = total_long_usd + total_short_usd + total_single_usd

        if total_usd == 0:
            # Semua fetch gagal → return fallback dengan flag
            result = self._fallback(reason="yfinance fetch failed — semua ETF return 0 AUM")
            self._cache = result
            self._cache_ts = time.time()
            return result

        # ── Pcts ──────────────────────────────────────────────────────────
        long_pct   = round(total_long_usd   / total_usd * 100, 1)
        short_pct  = round(total_short_usd  / total_usd * 100, 1)
        single_pct = round(total_single_usd / total_usd * 100, 1)

        # ── Top ETFs ──────────────────────────────────────────────────────
        top_longs = sorted(
            [{"ticker": t, "aum_b": _to_billions(v)} for t, v in long_aum.items() if v > 0],
            key=lambda x: x["aum_b"], reverse=True
        )[:5]
        top_shorts = sorted(
            [{"ticker": t, "aum_b": _to_billions(v)} for t, v in short_aum.items() if v > 0],
            key=lambda x: x["aum_b"], reverse=True
        )[:5]

        # ── Rebalancing Pressure ──────────────────────────────────────────
        # Kalau SPY 1-day return besar, 3x ETFs harus rebalance proporsional lebih
        rebal_pressure = "LOW"
        if prices is not None:
            spy = prices.get("SPY") or prices.get("^GSPC")
            if spy is not None and len(spy) >= 2:
                spy_clean = pd.to_numeric(spy, errors="coerce").dropna()
                if len(spy_clean) >= 2:
                    spy_1d = abs(float(spy_clean.iloc[-1] / spy_clean.iloc[-2] - 1))
                    if spy_1d > 0.015:    # >1.5% daily move
                        rebal_pressure = "HIGH"
                    elif spy_1d > 0.007:  # >0.7%
                        rebal_pressure = "MEDIUM"

        # ── ATH Check ────────────────────────────────────────────────────
        # Simple heuristic: total AUM > $120B historically adalah ATH zone
        # (dari chart Tier 1 Alpha yang menunjukkan ATH di ~$150B per Mei 2026)
        # Perlu historical cache untuk true ATH check — untuk sekarang threshold-based
        total_b = _to_billions(total_usd)
        is_ath = total_b > 120.0  # Update threshold ini dari historical data

        result = {
            "ok": True,
            "total_mcap_b": total_b,
            "long_exposure_b": _to_billions(total_long_usd),
            "short_exposure_b": _to_billions(total_short_usd),
            "single_crypto_b": _to_billions(total_single_usd),
            "long_pct": long_pct,
            "short_pct": short_pct,
            "single_pct": single_pct,
            "is_ath": is_ath,
            "top_longs": top_longs,
            "top_shorts": top_shorts,
            "rebalancing_pressure": rebal_pressure,
            "long_etf_count": len([v for v in long_aum.values() if v > 0]),
            "short_etf_count": len([v for v in short_aum.values() if v > 0]),
            "source": "yfinance_totalAssets",
            "note": f"Computed dari {len(long_aum)+len(short_aum)+len(single_aum)} ETFs via yfinance. Cache 6h.",
        }

        self._cache = result
        self._cache_ts = time.time()
        logger.info(f"Leveraged ETF: Total ${total_b}B · Long ${_to_billions(total_long_usd)}B · Short ${_to_billions(total_short_usd)}B")
        return result

    def _fallback(self, reason: str = "") -> Dict:
        """Fallback ketika fetch gagal total."""
        return {
            "ok": False,
            "total_mcap_b": None,
            "long_exposure_b": None,
            "short_exposure_b": None,
            "single_crypto_b": None,
            "long_pct": None,
            "short_pct": None,
            "is_ath": None,
            "top_longs": [],
            "top_shorts": [],
            "rebalancing_pressure": "UNKNOWN",
            "source": "fallback",
            "note": f"Fetch gagal: {reason}",
        }
