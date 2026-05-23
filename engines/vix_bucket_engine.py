"""engines/vix_bucket_engine.py — Hedgeye VIX Bucket System v39

Exact Hedgeye Methodology:
  VIX 9-19:  Investable bucket (buy dips, normal risk)
  VIX 20-29: Chop bucket (trade ranges, reduce size, be aggressive on longs)
  VIX 29+:   F*ck bucket (defensive, preserve capital, 10% max equity)

Position Sizing Adjustment:
  VIX < 19:  base_size * 1.0
  VIX 19-29: base_size * 0.5
  VIX > 29:  base_size * 0.1

Gate Logic:
  VIX > 29 + direction=LONG → "AVOID — VIX f*ck bucket"
  VIX 19-29 + direction=LONG → "MARGINAL — Chop bucket, reduce size"
  VIX < 19 + direction=LONG → "PASS — Investable bucket"

Returns:
  {
    "vix": 24.5,
    "bucket": "chop",
    "position_mult": 0.5,
    "gate_status": "MARGINAL",
    "recommendation": "Reduce position sizes 50%, trade ranges",
    "sectors_vulnerable": ["XLK", "XLY", "XLF"]
  }
"""
from __future__ import annotations
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

def classify_vix_bucket(vix: float) -> Dict:
    """Classify VIX into Hedgeye bucket."""
    if vix < 19:
        return {
            "vix": round(vix, 2),
            "bucket": "investable",
            "position_mult": 1.0,
            "gate_status": "PASS",
            "recommendation": "Investable bucket — buy dips, normal risk",
            "sectors_vulnerable": [],
            "max_equity_exposure": 1.0,
            "max_etf_exposure": 1.0,
        }
    elif vix < 29:
        return {
            "vix": round(vix, 2),
            "bucket": "chop",
            "position_mult": 0.5,
            "gate_status": "MARGINAL",
            "recommendation": "Chop bucket — trade ranges, reduce sizes 50%, be aggressive on longs at LRR",
            "sectors_vulnerable": ["XLK", "XLY", "XLF"],
            "max_equity_exposure": 0.5,
            "max_etf_exposure": 0.5,
        }
    else:
        return {
            "vix": round(vix, 2),
            "bucket": "fuck",
            "position_mult": 0.1,
            "gate_status": "FAIL",
            "recommendation": "F*ck bucket — defensive, preserve capital, max 10% equity exposure",
            "sectors_vulnerable": ["XLK", "XLY", "XLF", "XLI", "XLB"],
            "max_equity_exposure": 0.1,
            "max_etf_exposure": 0.1,
        }

def apply_vix_position_sizing(base_size: float, vix: float) -> float:
    """Apply VIX bucket multiplier to position size."""
    bucket = classify_vix_bucket(vix)
    return base_size * bucket["position_mult"]

def vix_gatekeeper(direction: str, vix: float) -> Dict:
    """Gate entry based on VIX bucket and direction."""
    bucket = classify_vix_bucket(vix)
    status = bucket["gate_status"]

    if direction == "LONG":
        if status == "FAIL":
            return {**bucket, "action": "AVOID", "reason": "VIX f*ck bucket — go to cash"}
        elif status == "MARGINAL":
            return {**bucket, "action": "MARGINAL", "reason": "Chop bucket — reduce size, only buy at LRR"}
        else:
            return {**bucket, "action": "PASS", "reason": "Investable bucket — normal entry"}
    else:  # SHORT
        if status == "FAIL":
            return {**bucket, "action": "PASS", "reason": "VIX f*ck bucket — short favorable"}
        elif status == "MARGINAL":
            return {**bucket, "action": "PASS", "reason": "Chop bucket — short at TRR"}
        else:
            return {**bucket, "action": "MARGINAL", "reason": "Investable bucket — short only at extreme TRR"}

def get_sector_vulnerability(vix: float, quad: str = "Q3") -> Dict[str, str]:
    """Get sector vulnerability in current VIX + Quad regime."""
    bucket = classify_vix_bucket(vix)
    vulnerable = bucket["sectors_vulnerable"]

    sector_signals = {}
    for sector in ["XLK", "XLY", "XLF", "XLI", "XLB", "XLE", "XLU", "XLRE"]:
        if sector in vulnerable:
            if quad == "Q3":
                sector_signals[sector] = "AVOID — Chop + Quad 3 double headwind"
            else:
                sector_signals[sector] = "CAUTION — Chop bucket vulnerable"
        elif sector == "XLE":
            sector_signals[sector] = "LONG — Inflation hedge, Quad 3 beneficiary"
        elif sector == "XLU":
            sector_signals[sector] = "HOLD — Defensive, safe in chop"
        else:
            sector_signals[sector] = "NEUTRAL"

    return sector_signals
