"""engines/keith_signal_sync.py — Keith McCullough Signal Synchronization v39

Current Keith Signals (May 2026) — UPDATED from latest tweets:

COMMODITIES:
  GC=F/GLD: Bearish TRADE (Gold remains Bearish TRADE per Keith)
  SI=F/SLV: Bearish TREND (Silver remains Bearish TRENDS)
  HG=F: Bullish TREND (Dr. Copper Bullish TREND)
  CL=F: Bullish TREND (Energy Bullish TREND, WTI fractal signal $98.52)

FOREX:
  DX-Y.NYB/DXY: Bullish TREND (USD remains Bullish TREND)

ENERGY:
  XLE: Bullish TREND (Energy Bullish TREND)

TECH:
  XLK: Vulnerable (Chop bucket + Quad 3)
  OKLO: AVOID (Fractal Gods kept out, -7%)
  PLTR: SHORT (Just shorted more for The Fam)

SECTORS VULNERABLE:
  XLY, XLF: Vulnerable in Chop + Quad 3

SHORTS (MCM Shorts list):
  DE, ASAN, THC, ACI, WDAY, MNDY, SUJA, ADBE

STRONG HOLDS (never broke trade levels):
  SNDK, STX
"""
from __future__ import annotations
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# UPDATED Keith signals from latest tweets (May 2026)
KEITH_CURRENT_SIGNALS = {
    # Commodities
    "GC=F": {"TRADE": "BEARISH", "TREND": "BULLISH", "TAIL": "BULLISH", "source": "Keith tweet"},
    "GLD": {"TRADE": "BEARISH", "TREND": "BULLISH", "TAIL": "BULLISH", "source": "Keith tweet"},
    "HG=F": {"TRADE": "BULLISH", "TREND": "BULLISH", "TAIL": "NEUTRAL", "source": "Keith tweet"},
    "SI=F": {"TRADE": "BEARISH", "TREND": "BEARISH", "TAIL": "NEUTRAL", "source": "Keith tweet"},
    "SLV": {"TRADE": "BEARISH", "TREND": "BEARISH", "TAIL": "NEUTRAL", "source": "Keith tweet"},
    "CL=F": {"TRADE": "BULLISH", "TREND": "BULLISH", "TAIL": "NEUTRAL", "source": "Keith tweet"},

    # Forex
    "DX-Y.NYB": {"TRADE": "BULLISH", "TREND": "BULLISH", "TAIL": "NEUTRAL", "source": "Keith tweet"},
    "DXY": {"TRADE": "BULLISH", "TREND": "BULLISH", "TAIL": "NEUTRAL", "source": "Keith tweet"},

    # Energy
    "XLE": {"TRADE": "BULLISH", "TREND": "BULLISH", "TAIL": "BULLISH", "source": "Keith tweet"},

    # Tech
    "XLK": {"TRADE": "BEARISH", "TREND": "MARGINAL", "TAIL": "BULLISH", "source": "Keith tweet"},
    "OKLO": {"TRADE": "AVOID", "TREND": "AVOID", "TAIL": "NEUTRAL", "source": "Keith tweet: Fractal Gods kept out -7%"},
    "PLTR": {"TRADE": "SHORT", "TREND": "SHORT", "TAIL": "NEUTRAL", "source": "Keith tweet: Just shorted more"},

    # Strong holds
    "SNDK": {"TRADE": "BULLISH", "TREND": "BULLISH", "TAIL": "BULLISH", "source": "Keith tweet: Never broke trade levels"},
    "STX": {"TRADE": "BULLISH", "TREND": "BULLISH", "TAIL": "BULLISH", "source": "Keith tweet: Never broke trade levels"},

    # MCM Shorts
    "DE": {"TRADE": "SHORT", "TREND": "SHORT", "TAIL": "NEUTRAL", "source": "MCM Shorts list"},
    "ASAN": {"TRADE": "SHORT", "TREND": "SHORT", "TAIL": "NEUTRAL", "source": "MCM Shorts list"},
    "THC": {"TRADE": "SHORT", "TREND": "SHORT", "TAIL": "NEUTRAL", "source": "MCM Shorts list"},
    "ACI": {"TRADE": "SHORT", "TREND": "SHORT", "TAIL": "NEUTRAL", "source": "MCM Shorts list"},
    "WDAY": {"TRADE": "SHORT", "TREND": "SHORT", "TAIL": "NEUTRAL", "source": "MCM Shorts list"},
    "MNDY": {"TRADE": "SHORT", "TREND": "SHORT", "TAIL": "NEUTRAL", "source": "MCM Shorts list"},
    "SUJA": {"TRADE": "SHORT", "TREND": "SHORT", "TAIL": "NEUTRAL", "source": "MCM Shorts list"},
    "ADBE": {"TRADE": "SHORT", "TREND": "SHORT", "TAIL": "NEUTRAL", "source": "MCM Shorts list"},

    # Sectors
    "XLY": {"TRADE": "BEARISH", "TREND": "MARGINAL", "TAIL": "BULLISH", "source": "Keith tweet"},
    "XLF": {"TRADE": "BEARISH", "TREND": "MARGINAL", "TAIL": "BULLISH", "source": "Keith tweet"},
}

DURATION_PRIORITY = ["TRADE", "TREND", "TAIL"]

def get_keith_signal(ticker: str) -> Optional[Dict]:
    return KEITH_CURRENT_SIGNALS.get(ticker.upper())

def resolve_direction(ticker: str, dashboard_direction: str, dashboard_duration: str = "TREND") -> Dict:
    keith = get_keith_signal(ticker)
    if not keith:
        return {
            "ticker": ticker, "direction": dashboard_direction, "duration": dashboard_duration,
            "source": "dashboard", "override": False, "reason": "No Keith signal",
        }

    keith_primary = keith.get(dashboard_duration, "NEUTRAL")

    # Special handling for AVOID
    if keith_primary == "AVOID":
        return {
            "ticker": ticker, "direction": "AVOID", "duration": dashboard_duration,
            "source": "Keith override", "override": True,
            "reason": f"Keith {dashboard_duration}=AVOID — override everything",
            "keith_trade": keith.get("TRADE"), "keith_trend": keith.get("TREND"),
            "keith_tail": keith.get("TAIL"),
        }

    if keith_primary != "NEUTRAL" and keith_primary != dashboard_direction:
        return {
            "ticker": ticker, "direction": keith_primary, "duration": dashboard_duration,
            "source": "Keith override", "override": True,
            "reason": f"Keith {dashboard_duration}={keith_primary} overrides dashboard {dashboard_direction}",
            "keith_trade": keith.get("TRADE"), "keith_trend": keith.get("TREND"),
            "keith_tail": keith.get("TAIL"),
        }

    return {
        "ticker": ticker, "direction": dashboard_direction, "duration": dashboard_duration,
        "source": "dashboard + Keith aligned", "override": False,
        "reason": f"Aligned with Keith {dashboard_duration}={keith_primary}",
        "keith_trade": keith.get("TRADE"), "keith_trend": keith.get("TREND"),
        "keith_tail": keith.get("TAIL"),
    }

def get_duration_display(ticker: str) -> str:
    keith = get_keith_signal(ticker)
    if not keith: return ""
    parts = []
    for dur in DURATION_PRIORITY:
        sig = keith.get(dur, "NEUTRAL")
        if sig != "NEUTRAL":
            emoji = "🟢" if sig == "BULLISH" else "🔴" if sig in ("BEARISH", "SHORT") else "🟡" if sig == "AVOID" else "⚪"
            parts.append(f"{emoji} {sig} {dur}")
    return " | ".join(parts) if parts else ""

def should_avoid(ticker: str, direction: str, duration: str = "TRADE") -> bool:
    keith = get_keith_signal(ticker)
    if not keith: return False
    keith_sig = keith.get(duration, "NEUTRAL")
    if keith_sig == "AVOID": return True
    if keith_sig == "BEARISH" and direction == "LONG": return True
    if keith_sig == "BULLISH" and direction == "SHORT": return True
    if keith_sig == "SHORT" and direction == "LONG": return True
    return False
