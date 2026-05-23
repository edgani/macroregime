"""engines/hedgeye_position_sizing.py — Exact Hedgeye Position Sizing v39

Exact Hedgeye Framework:
  - Adds: 50-100bps increments, scaled to conviction and volatility
  - Min equity position: 2%
  - Max equity position: 6%
  - Max ETF position: 10-20%
  - Max currency position: 12%
  - Real-Time Alerts win rate: 74-87% since 2008

Formula:
  base_size = max(2%, min(6%, kelly_fraction * portfolio_value))

  If VIX < 19:  final_size = base_size * 1.0
  If VIX 19-29: final_size = base_size * 0.5
  If VIX > 29:  final_size = base_size * 0.1

  If conviction >= 80: add 100bps
  If conviction 60-79:  add 50bps
  If conviction < 60:    no add, reduce to min

  Max position check:
    If equity:  final_size = min(final_size, 6% of portfolio)
    If ETF:     final_size = min(final_size, 20% of portfolio)
    If currency: final_size = min(final_size, 12% of portfolio)
    If sector exposure > 40%: final_size = min(final_size, 40% - current_sector)
"""
from __future__ import annotations
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Hedgeye exact parameters
MIN_EQUITY_PCT = 0.02      # 2%
MAX_EQUITY_PCT = 0.06      # 6%
MAX_ETF_PCT = 0.20         # 20%
MAX_CURRENCY_PCT = 0.12    # 12%
MAX_SECTOR_PCT = 0.40      # 40%
ADD_INCREMENT_HIGH = 0.01  # 100bps
ADD_INCREMENT_LOW = 0.005  # 50bps

def calculate_position_size(
    portfolio_value: float,
    kelly_fraction: float,
    vix: float,
    conviction: float,
    ticker_type: str = "equity",  # equity, etf, currency
    current_sector_exposure: float = 0.0,
    sector: str = "",
) -> Dict:
    """Calculate exact Hedgeye position size."""

    # Step 1: Base size from Kelly
    base_size = portfolio_value * kelly_fraction

    # Step 2: Apply min/max by asset type
    if ticker_type == "equity":
        base_size = max(MIN_EQUITY_PCT * portfolio_value, 
                        min(MAX_EQUITY_PCT * portfolio_value, base_size))
    elif ticker_type == "etf":
        base_size = max(MIN_EQUITY_PCT * portfolio_value,
                        min(MAX_ETF_PCT * portfolio_value, base_size))
    elif ticker_type == "currency":
        base_size = max(MIN_EQUITY_PCT * portfolio_value,
                        min(MAX_CURRENCY_PCT * portfolio_value, base_size))

    # Step 3: Apply VIX bucket multiplier
    vix_mult = 1.0
    vix_bucket = "investable"
    if vix >= 29:
        vix_mult = 0.1
        vix_bucket = "fuck"
    elif vix >= 19:
        vix_mult = 0.5
        vix_bucket = "chop"

    sized = base_size * vix_mult

    # Step 4: Apply conviction adds
    if conviction >= 80:
        sized += ADD_INCREMENT_HIGH * portfolio_value
    elif conviction >= 60:
        sized += ADD_INCREMENT_LOW * portfolio_value
    else:
        # Low conviction — reduce to minimum
        sized = MIN_EQUITY_PCT * portfolio_value

    # Step 5: Sector cap check
    max_for_sector = MAX_SECTOR_PCT * portfolio_value - current_sector_exposure
    if max_for_sector < sized:
        sized = max(0, max_for_sector)

    # Step 6: Final cap check
    if ticker_type == "equity":
        sized = min(sized, MAX_EQUITY_PCT * portfolio_value)
    elif ticker_type == "etf":
        sized = min(sized, MAX_ETF_PCT * portfolio_value)
    elif ticker_type == "currency":
        sized = min(sized, MAX_CURRENCY_PCT * portfolio_value)

    return {
        "position_size_dollars": round(sized, 2),
        "position_pct": round(sized / portfolio_value * 100, 2),
        "base_size_pct": round(base_size / portfolio_value * 100, 2),
        "vix_bucket": vix_bucket,
        "vix_mult": vix_mult,
        "conviction_add": ADD_INCREMENT_HIGH * portfolio_value if conviction >= 80 else (
            ADD_INCREMENT_LOW * portfolio_value if conviction >= 60 else 0),
        "ticker_type": ticker_type,
        "max_allowed_pct": MAX_EQUITY_PCT * 100 if ticker_type == "equity" else (
            MAX_ETF_PCT * 100 if ticker_type == "etf" else MAX_CURRENCY_PCT * 100),
    }

def get_add_increment(conviction: float, vix: float) -> float:
    """Get add increment based on conviction and VIX."""
    if vix >= 29:
        return 0.0  # No adds in f*ck bucket
    if conviction >= 80:
        return ADD_INCREMENT_HIGH
    elif conviction >= 60:
        return ADD_INCREMENT_LOW
    return 0.0
