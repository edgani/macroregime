"""hedgeye_position_sizing.py - Exact Hedgeye Sizing v39
2-6% max per equity, 10-20% max per ETF, 50-100bps adds
"""

def calculate_position_size(ticker, conviction, vix_bucket, quad, portfolio_value, existing_exposure):
    """Calculate position size per Hedgeye methodology."""
    vix_mult = vix_bucket.get("multiplier", 1.0) if vix_bucket else 1.0

    # Base size: 2% min, 6% max per equity
    base_pct = 0.02
    max_pct = 0.06

    # Conviction adjustment
    size_pct = base_pct + (max_pct - base_pct) * conviction
    size_pct *= vix_mult

    # Cap at max
    size_pct = min(size_pct, max_pct)

    # Dollar size
    dollar_size = portfolio_value * size_pct

    # Mode
    mode = "CONVICTION_HIGH" if conviction >= 0.8 else "CONVICTION_MED" if conviction >= 0.5 else "DEFAULT"

    return {
        "size_pct": round(size_pct, 4),
        "dollar_size": round(dollar_size, 2),
        "mode": mode,
        "max_equity_pct": max_pct,
        "vix_multiplier": vix_mult,
        "conviction": conviction,
    }
