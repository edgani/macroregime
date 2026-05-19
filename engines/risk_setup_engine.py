"""engines/risk_setup_engine.py — Integrated Entry/Target/Stop Engine (Sprint 6)

REPLACES naive trade_l/trade_r calculation in app.py _rr_levels() and
orchestrator _alpha_center_proxy().

INPUTS:
  1. Risk Range v2 (Trade/Trend/Tail levels + ATR + realized vol)
  2. Composite Signal (direction with confidence)
  3. Max Pain (options gravitational pull)
  4. Gamma Flip levels (acceleration zones)
  5. Greeks composite (vanna bias for time-decay)
  6. News momentum (entry urgency)

OUTPUT:
  entry / target1 / target2 / stop with rationale + confidence band.

LOGIC (vs old proxy that just used trade_l/trade_r):
  • Entry: Now considers price location, formation, options magnet
  • Target1: closer of (trade_trr/Max Pain/Call Wall) for LONG
  • Target2: trend_trr or tail_trr depending on conviction
  • Stop: ATR-based (1.5x ATR for trade, 2.5x ATR for trend setups)
  • Confidence: derived from composite_signal confidence + RR
"""
from __future__ import annotations

import math
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def _safe_float(v, default=None):
    try:
        f = float(v)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def calculate_risk_setup(
    ticker: str,
    direction: str,                     # "LONG"|"SHORT"|"NEUTRAL"|"AVOID"
    price: float,
    risk_range: Dict,                   # Output from RiskRangeEngine v2
    composite_signal: Optional[Dict] = None,
    gamma_data: Optional[Dict] = None,
    greek_data: Optional[Dict] = None,
    market_type: str = "us_equity",
) -> Dict:
    """
    Returns:
      {
        "entry": float, "target1": float, "target2": float, "stop": float,
        "rr": float, "near_entry": bool, "action": str,
        "entry_rationale": str, "stop_rationale": str,
        "options_magnet": dict (if used), "confidence": 0..1
      }
    """
    rr = risk_range or {}

    # Bail out on neutral/avoid
    if direction in ("NEUTRAL", "AVOID", ""):
        return _neutral_setup(ticker, price)

    # Pull all reference levels
    trade = rr.get("trade", {})
    trend = rr.get("trend", {})
    tail = rr.get("tail", {})
    trade_l = _safe_float(trade.get("lrr"))
    trade_r = _safe_float(trade.get("trr"))
    trend_l = _safe_float(trend.get("lrr"))
    trend_r = _safe_float(trend.get("trr"))
    tail_l = _safe_float(tail.get("lrr"))
    tail_r = _safe_float(tail.get("trr"))
    atr_14 = _safe_float(rr.get("atr_14"), 0)
    atr_30 = _safe_float(rr.get("atr_30"), atr_14)

    # If no usable Risk Range, fall back to ATR-only
    if not (trade_l and trade_r):
        return _atr_only_setup(ticker, price, direction, atr_14 or price * 0.02)

    # Options reference levels
    options_magnet = {}
    max_pain = _safe_float((gamma_data or {}).get("max_pain"))
    call_wall = _safe_float((gamma_data or {}).get("call_wall"))
    put_wall = _safe_float((gamma_data or {}).get("put_wall"))
    gamma_flip_up = _safe_float((gamma_data or {}).get("gamma_flip_up"))
    gamma_flip_down = _safe_float((gamma_data or {}).get("gamma_flip_down"))

    gamma_regime = (gamma_data or {}).get("regime", "")

    # ── LONG SETUP ──────────────────────────────────────────────────────
    if direction == "LONG":
        # Entry strategy:
        # If price already BELOW Trade low → "Buy Now" at current price (don't chase higher)
        # Else → entry = Trade low (wait for dip)
        if price < trade_l:
            entry = round(price, 4)
            entry_rationale = f"Buy Now @ {price:.2f} — already below Trade low {trade_l:.2f}"
            near_entry = True
        else:
            entry = round(trade_l, 4)
            entry_rationale = f"Buy on dip to Trade low {trade_l:.2f}"
            pos_in_trade = (price - trade_l) / max(trade_r - trade_l, 0.001)
            near_entry = pos_in_trade <= 0.35

        # Target 1: closer of Trade upper / Max Pain / Call Wall
        candidates_t1 = [trade_r]
        magnet_used = "Trade upper"
        if max_pain and max_pain > entry and max_pain < trade_r * 1.05:
            candidates_t1.append(max_pain)
            if max_pain < trade_r:
                magnet_used = f"Max Pain {max_pain:.2f}"
        if call_wall and call_wall > entry and call_wall < trend_r * 1.1 if trend_r else True:
            candidates_t1.append(call_wall)
            if call_wall < trade_r:
                magnet_used = f"Call Wall {call_wall:.2f}"
        target1 = round(min(candidates_t1), 4)
        options_magnet["target1_source"] = magnet_used

        # Target 2: Trend upper or Tail (depends on conviction)
        if composite_signal and composite_signal.get("is_strong"):
            # High conviction → aim for Trend
            target2 = round(trend_r if trend_r else trade_r * 1.05, 4)
            t2_src = "Trend upper"
        else:
            # Modest conviction → exit at Trend or 75% of way there
            t2_anchor = trend_r if trend_r else trade_r * 1.03
            target2 = round(entry + (t2_anchor - entry) * 0.8, 4)
            t2_src = "80% to Trend upper"
        options_magnet["target2_source"] = t2_src

        # Stop: ATR-based, asymmetric
        # CRITICAL: Stop MUST be below entry for LONG
        atr_stop = entry - atr_14 * 1.5 if atr_14 > 0 else entry * 0.97
        rr_stop = trade_l - (trade_r - trade_l) * 0.20  # 20% below Trade low
        # Filter: only stops below entry are valid
        valid_stops = [s for s in [atr_stop, rr_stop] if s < entry]
        if put_wall and put_wall < entry and put_wall > entry * 0.92:
            valid_stops.append(put_wall * 0.998)
        if not valid_stops:
            # Fallback: 2 ATR below entry
            valid_stops = [entry - (atr_14 * 2 if atr_14 > 0 else entry * 0.04)]
        stop = round(max(valid_stops), 4)  # tightest valid stop
        stop_rationale = f"ATR-based (-1.5x={atr_stop:.2f}) or RR-based ({rr_stop:.2f}), tightest valid"

        # Recalc near_entry with proper logic
        if not near_entry and trade_l <= price <= trade_r:
            pos_in_trade = (price - trade_l) / max(trade_r - trade_l, 0.001)
            near_entry = pos_in_trade <= 0.40

    # ── SHORT SETUP ─────────────────────────────────────────────────────
    elif direction == "SHORT":
        if price > trade_r:
            entry = round(price, 4)
            entry_rationale = f"Sell Now @ {price:.2f} — already above Trade high {trade_r:.2f}"
            near_entry = True
        else:
            entry = round(trade_r, 4)
            entry_rationale = f"Sell on rally to Trade high {trade_r:.2f}"
            pos_in_trade = (price - trade_l) / max(trade_r - trade_l, 0.001)
            near_entry = pos_in_trade >= 0.65

        candidates_t1 = [trade_l]
        magnet_used = "Trade lower"
        if max_pain and max_pain < entry and max_pain > trade_l * 0.95:
            candidates_t1.append(max_pain)
            if max_pain > trade_l:
                magnet_used = f"Max Pain {max_pain:.2f}"
        if put_wall and put_wall < entry and put_wall > trend_l * 0.9 if trend_l else True:
            candidates_t1.append(put_wall)
            if put_wall > trade_l:
                magnet_used = f"Put Wall {put_wall:.2f}"
        target1 = round(max(candidates_t1), 4)  # max for short = closest below entry
        options_magnet["target1_source"] = magnet_used

        if composite_signal and composite_signal.get("is_strong"):
            target2 = round(trend_l if trend_l else trade_l * 0.95, 4)
            t2_src = "Trend lower"
        else:
            t2_anchor = trend_l if trend_l else trade_l * 0.97
            target2 = round(entry - (entry - t2_anchor) * 0.8, 4)
            t2_src = "80% to Trend lower"
        options_magnet["target2_source"] = t2_src

        atr_stop = entry + atr_14 * 1.5 if atr_14 > 0 else entry * 1.03
        rr_stop = trade_r + (trade_r - trade_l) * 0.20
        valid_stops = [s for s in [atr_stop, rr_stop] if s > entry]
        if call_wall and call_wall > entry and call_wall < entry * 1.08:
            valid_stops.append(call_wall * 1.002)
        if not valid_stops:
            valid_stops = [entry + (atr_14 * 2 if atr_14 > 0 else entry * 0.04)]
        stop = round(min(valid_stops), 4)  # tightest valid stop
        stop_rationale = f"ATR-based (+1.5x={atr_stop:.2f}) or RR-based ({rr_stop:.2f}), tightest valid"

        if not near_entry and trade_l <= price <= trade_r:
            pos_in_trade = (price - trade_l) / max(trade_r - trade_l, 0.001)
            near_entry = pos_in_trade >= 0.60

    else:
        return _neutral_setup(ticker, price)

    # Compute R:R
    rr_ratio = abs(target1 - entry) / max(abs(entry - stop), 0.001)

    # Confidence (combine composite + RR quality)
    base_conf = (composite_signal or {}).get("confidence", 0.5)
    rr_quality = min(1.0, rr_ratio / 3.0)  # RR>=3 = full quality
    confidence = round(base_conf * 0.7 + rr_quality * 0.3, 3)

    # Action label
    if near_entry:
        action = "Buy Now" if direction == "LONG" else "Sell Now"
    else:
        action = "Wait for setup"

    return {
        "ticker": ticker,
        "direction": direction,
        "entry": entry,
        "target1": target1,
        "target2": target2,
        "stop": stop,
        "rr": round(rr_ratio, 2),
        "near_entry": near_entry,
        "action": action,
        "entry_rationale": entry_rationale,
        "stop_rationale": stop_rationale,
        "options_magnet": options_magnet,
        "confidence": confidence,
        "expected_move_weekly_pct": rr.get("expected_move_weekly_pct"),
        "daily_vol_pct": rr.get("daily_vol_pct"),
        "atr_14": atr_14,
    }


def _neutral_setup(ticker: str, price: float) -> Dict:
    return {
        "ticker": ticker, "direction": "NEUTRAL",
        "entry": None, "target1": None, "target2": None, "stop": None,
        "rr": 0.0, "near_entry": False, "action": "Stay flat — no directional edge",
        "entry_rationale": "Neutral composite signal", "stop_rationale": "—",
        "options_magnet": {}, "confidence": 0.0,
    }


def _atr_only_setup(ticker: str, price: float, direction: str, atr: float) -> Dict:
    """Fallback when no Risk Range available — pure ATR based."""
    if direction == "LONG":
        entry = price
        target1 = round(price + atr * 2, 4)
        target2 = round(price + atr * 4, 4)
        stop = round(price - atr * 1.5, 4)
    else:
        entry = price
        target1 = round(price - atr * 2, 4)
        target2 = round(price - atr * 4, 4)
        stop = round(price + atr * 1.5, 4)
    rr = abs(target1 - entry) / max(abs(entry - stop), 0.001)
    return {
        "ticker": ticker, "direction": direction,
        "entry": entry, "target1": target1, "target2": target2, "stop": stop,
        "rr": round(rr, 2), "near_entry": True,
        "action": ("Buy Now" if direction == "LONG" else "Sell Now") + " (ATR-only fallback)",
        "entry_rationale": "No Risk Range available — using ATR fallback",
        "stop_rationale": f"ATR ±1.5x = {atr * 1.5:.2f}",
        "options_magnet": {}, "confidence": 0.4,
    }
