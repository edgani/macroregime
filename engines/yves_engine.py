"""engines/yves_engine.py — Yves Lamoureux Behavioral Alerts v2 (Sprint 2)

Upgrades vs aaii_scraper._yves_alert (v1):
  • Specific numbers (not generic strings)
  • Concrete action items with tickers + price levels
  • Invalidation conditions
  • Historical analogs
  • Time horizons
  • Multi-alert (can fire multiple simultaneously)

Yves Lamoureux core philosophy:
  - Behavior > fundamentals at extremes
  - "Casino mode" = retail euphoria peak (CASH RAISE signal)
  - "Capitulation" = panic selling (DEPLOY CASH signal)
  - "Bonds asleep" = inflation mispricing (DEFENSIVE)
  - Bull-Bear spread is leading indicator
"""
from __future__ import annotations

import math
import logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def _safe_pct(s, n: int) -> Optional[float]:
    if s is None:
        return None
    try:
        ser = pd.to_numeric(s, errors="coerce").dropna()
        if len(ser) < n + 1:
            return None
        return float(ser.iloc[-1] / ser.iloc[-n - 1] - 1)
    except Exception:
        return None


def _safe_last(s) -> Optional[float]:
    if s is None:
        return None
    try:
        ser = pd.to_numeric(s, errors="coerce").dropna()
        return float(ser.iloc[-1]) if len(ser) > 0 else None
    except Exception:
        return None


def _safe_yoy(s) -> Optional[float]:
    if s is None:
        return None
    try:
        ser = pd.to_numeric(s, errors="coerce").dropna()
        if len(ser) < 13:
            return None
        return float(ser.iloc[-1] / ser.iloc[-13] - 1)
    except Exception:
        return None


def build_yves_alerts(aaii: Dict, vix: float, real_yield: float,
                      put_call: float, prices: Dict, fred: Dict) -> List[Dict]:
    """
    Build list of structured, actionable Yves alerts.

    Returns:
        [
          {
            "level": "CRITICAL" | "WARNING" | "CAUTION" | "OPPORTUNITY" | "NEUTRAL",
            "category": str,
            "title": str (with emoji),
            "specifics": str (numbers, percentages),
            "action": list[str] (concrete steps with tickers/levels),
            "invalidation": str (what kills this thesis),
            "historical_analogs": list[str],
            "time_horizon": str,
            "confidence": float,
          }
        ]
    """
    alerts: List[Dict] = []

    bull = float(aaii.get("bullish", 30) or 30)
    bear = float(aaii.get("bearish", 30) or 30)
    spread = bull - bear

    # Price levels for action items
    spy_last = _safe_last(prices.get("SPY")) or 580
    qqq_last = _safe_last(prices.get("QQQ")) or 500
    vix_last = float(vix) if vix else 20

    # Macro context
    cpi_yoy = _safe_yoy(fred.get("CPIAUCSL") if "CPIAUCSL" in fred else fred.get("CPI"))
    cpi_yoy_pct = (cpi_yoy * 100) if cpi_yoy is not None else None

    # Momentum context
    spy_3m = _safe_pct(prices.get("SPY"), 63) or 0.0
    spy_1m = _safe_pct(prices.get("SPY"), 21) or 0.0
    qqq_3m = _safe_pct(prices.get("QQQ"), 63) or 0.0

    # ═══════════════════════════════════════════════════════════════
    # ALERT 1: CASINO MODE (Retail Euphoria)
    # ═══════════════════════════════════════════════════════════════
    if bull > 50 and vix_last < 18 and put_call < 0.85:
        spy_put_strike = round(spy_last * 0.92, 0)
        spy_put_inner = round(spy_last * 0.88, 0)
        alerts.append({
            "level": "CRITICAL",
            "category": "casino_behavior",
            "title": "🎰 CASINO MODE — Retail Euphoria Peak",
            "specifics": (
                f"AAII Bull {bull:.0f}% (top decile), VIX {vix_last:.1f} (<18 = complacency), "
                f"P/C {put_call:.2f} (calls > puts). Spread {spread:+.0f}pp."
            ),
            "action": [
                f"Trim winners with >+25% YTD — raise cash to 15-20%",
                f"Buy SPY put spread 60-90 DTE: long {spy_put_strike:.0f}P / short {spy_put_inner:.0f}P",
                f"Fade 0DTE call buyers on NVDA/SMCI/TSLA at any breakout",
                f"Reduce single-name beta exposure, rotate to XLU/XLP/GLD",
            ],
            "invalidation": f"VIX > 22 OR AAII Bull drops below 40% within 30 days",
            "historical_analogs": ["Feb 2018", "Jan 2022", "Jul 2024"],
            "time_horizon": "3-6 weeks resolution",
            "confidence": 0.75,
        })

    # ═══════════════════════════════════════════════════════════════
    # ALERT 2: CAPITULATION ZONE (Panic Buy)
    # ═══════════════════════════════════════════════════════════════
    if bear > 45 and vix_last > 28:
        deploy_pct = 30 if bear > 50 else 25
        alerts.append({
            "level": "OPPORTUNITY",
            "category": "panic_capitulation",
            "title": "💎 CAPITULATION ZONE — Contrarian Buy",
            "specifics": (
                f"AAII Bear {bear:.0f}% (sub-5%-tile), VIX {vix_last:.1f} (>28 = fear), "
                f"Spread {spread:+.0f}pp."
            ),
            "action": [
                f"Deploy {deploy_pct}% of cash reserves over 2-4 weeks",
                f"Buy SPY at Trade-range low (~{spy_last * 0.97:.0f})",
                f"Long high-quality semis (NVDA/AMD/AVGO) if oversold below 50d MA",
                f"Sell SPY puts 30 DTE at -8% strike to collect premium",
            ],
            "invalidation": "AAII Bear stays >45% for 3+ weeks = structural bear market",
            "historical_analogs": ["Oct 2022", "Mar 2020", "Dec 2018", "Mar 2009"],
            "time_horizon": "2-8 weeks bounce",
            "confidence": 0.78,
        })

    # ═══════════════════════════════════════════════════════════════
    # ALERT 3: BONDS ASLEEP (Inflation Mispricing)
    # ═══════════════════════════════════════════════════════════════
    real_yield_inverted = real_yield is not None and real_yield < 0
    if real_yield is not None and real_yield < 1.0 and not real_yield_inverted:
        cpi_str = f"{cpi_yoy_pct:.1f}%" if cpi_yoy_pct else "elevated"
        mispricing = (cpi_yoy_pct - real_yield * 100) if cpi_yoy_pct else 0
        alerts.append({
            "level": "WARNING",
            "category": "bond_asleep",
            "title": "💤 BOND TRADERS ASLEEP — Inflation Mispriced",
            "specifics": (
                f"10Y Real Yield {real_yield:.2f}% (sub-1%), CPI YoY {cpi_str}. "
                f"Breakeven gap {mispricing:.1f}pp."
            ),
            "action": [
                "Long TIP vs short IEF (curve trade: inflation re-acceleration)",
                "Long GLD (real yield compression beneficiary)",
                "Long SLV (industrial + monetary dual demand)",
                "Fade long-duration tech (XLK) if VIX < 17",
                "Watch TLT for break of $90 = bond pivot signal",
            ],
            "invalidation": "Real yield > 2% within 30 days OR CPI YoY < 2.5%",
            "historical_analogs": ["Q1 2021", "Late 2010"],
            "time_horizon": "1-3 months",
            "confidence": 0.65,
        })

    # ═══════════════════════════════════════════════════════════════
    # ALERT 4: MOMENTUM EXTREME (Overstretched Rally)
    # ═══════════════════════════════════════════════════════════════
    if spy_3m > 0.12 and bull > 42 and vix_last < 16:
        alerts.append({
            "level": "CAUTION",
            "category": "momentum_extreme",
            "title": "🚀 OVERSTRETCHED RALLY — Take Some Off",
            "specifics": (
                f"SPY +{spy_3m * 100:.1f}% in 3M, QQQ +{qqq_3m * 100:.1f}% in 3M, "
                f"AAII Bull {bull:.0f}%, VIX {vix_last:.1f}."
            ),
            "action": [
                "Lock in 20-30% of trade-level gains in winners with >+20% YTD",
                "Roll SPY puts higher: from -10% strike to -7% strike",
                "Increase portfolio cash to 12-15%",
                "Watch for first VIX close > 18 = momentum break signal",
            ],
            "invalidation": "VIX > 18 OR SPY closes below 21-EMA",
            "historical_analogs": ["Jun 2024", "Jan 2024", "Jul 2023"],
            "time_horizon": "2-4 weeks reversion",
            "confidence": 0.60,
        })

    # ═══════════════════════════════════════════════════════════════
    # ALERT 5: BULL-BEAR SPREAD EXTREME
    # ═══════════════════════════════════════════════════════════════
    if spread > 28 and bull > 45:
        alerts.append({
            "level": "CAUTION",
            "category": "spread_extreme_bullish",
            "title": "⚠️ AAII SPREAD EXTREME (Bullish) — Trim Winners",
            "specifics": (
                f"Bull-Bear spread {spread:+.0f}pp (>28 historical reversion zone). "
                f"Bull {bull:.0f}%, Bear {bear:.0f}%."
            ),
            "action": [
                "Trim 25% of top-3 portfolio winners",
                "Add to XLU / XLP / TLT (defensive rotation)",
                "Buy VIX call spread 30-DTE 20/25 strikes",
            ],
            "invalidation": "Spread drops below 15 within 4 weeks (orderly cooldown)",
            "historical_analogs": ["Dec 2021", "Aug 2018"],
            "time_horizon": "3-6 weeks",
            "confidence": 0.55,
        })

    if spread < -25 and bear > 45:
        alerts.append({
            "level": "OPPORTUNITY",
            "category": "spread_extreme_bearish",
            "title": "💰 AAII SPREAD EXTREME (Bearish) — Contrarian Long",
            "specifics": (
                f"Bull-Bear spread {spread:+.0f}pp (sub-25 = panic). "
                f"Bull {bull:.0f}%, Bear {bear:.0f}%."
            ),
            "action": [
                "Buy SPY at next test of 50d MA",
                "Sell put credit spreads at -8% strikes (collect premium)",
                "Add to oversold high-quality names",
            ],
            "invalidation": "Spread stays sub-25 for 4+ weeks = real bear",
            "historical_analogs": ["Oct 2022", "Mar 2020", "Dec 2018"],
            "time_horizon": "2-6 weeks",
            "confidence": 0.62,
        })

    # ═══════════════════════════════════════════════════════════════
    # ALERT 6: VOLATILITY COMPLACENCY (VIX Term)
    # ═══════════════════════════════════════════════════════════════
    if vix_last < 13 and spy_1m > 0.04:
        alerts.append({
            "level": "CAUTION",
            "category": "vol_complacency",
            "title": "😴 VOLATILITY COMPLACENCY — Cheap Hedge",
            "specifics": f"VIX {vix_last:.1f} (sub-13 historical low), SPY +{spy_1m * 100:.1f}% in 1M.",
            "action": [
                "Buy cheap protection: SPY 60-DTE puts -7% strike",
                "Add VIX call spread 30-DTE 17/22",
                "Hedge ~25% of long book at minimal cost",
            ],
            "invalidation": "VIX > 16 within 2 weeks = vol expansion confirmed",
            "historical_analogs": ["Jan 2018", "Sep 2014"],
            "time_horizon": "1-3 weeks",
            "confidence": 0.55,
        })

    # ═══════════════════════════════════════════════════════════════
    # DEFAULT: Neutral state
    # ═══════════════════════════════════════════════════════════════
    if not alerts:
        alerts.append({
            "level": "NEUTRAL",
            "category": "balanced",
            "title": "⚖️ Balanced Behavioral Regime",
            "specifics": (
                f"AAII Bull {bull:.0f}%, Bear {bear:.0f}%, Spread {spread:+.0f}pp. "
                f"VIX {vix_last:.1f}. No behavioral extremes."
            ),
            "action": [
                "Maintain current allocation",
                "Follow GIP regime playbook",
                "Watch for VIX < 14 or > 22 as next behavioral signal",
            ],
            "invalidation": "Bull > 50% or Bear > 45% triggers alert reassessment",
            "historical_analogs": [],
            "time_horizon": "Monitor weekly",
            "confidence": 0.50,
        })

    return alerts


def build_yves_summary(alerts: List[Dict]) -> Dict:
    """One-line summary suitable for dashboard top-bar."""
    if not alerts:
        return {"level": "NONE", "title": "—", "n_alerts": 0}

    # Priority order
    level_rank = {"CRITICAL": 5, "OPPORTUNITY": 4, "WARNING": 3, "CAUTION": 2, "NEUTRAL": 1, "NONE": 0}
    top = max(alerts, key=lambda a: level_rank.get(a.get("level", "NONE"), 0))

    return {
        "level": top["level"],
        "title": top["title"],
        "category": top["category"],
        "n_alerts": len(alerts),
        "alert_categories": [a["category"] for a in alerts],
        "confidence": top.get("confidence", 0.5),
    }


def run_yves_v2(aaii: Dict, vix: float, real_yield: float,
                put_call: float, prices: Dict, fred: Dict) -> Dict:
    """Main entry. Returns full Yves analysis."""
    alerts = build_yves_alerts(aaii, vix, real_yield, put_call, prices, fred)
    summary = build_yves_summary(alerts)
    return {
        "alerts": alerts,
        "summary": summary,
        "n_alerts": len(alerts),
        "vix": vix,
        "real_yield": real_yield,
        "put_call": put_call,
        "bull": aaii.get("bullish", 30),
        "bear": aaii.get("bearish", 30),
        "spread": (aaii.get("bullish", 30) or 30) - (aaii.get("bearish", 30) or 30),
    }
