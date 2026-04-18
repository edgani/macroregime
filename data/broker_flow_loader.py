"""broker_flow_loader.py

Bandarmologi / Broker Flow Bridge.

Reads broker flow signals from a shared JSON file that your AFL system writes.
This is the critical bridge between bandarmologi analysis and MacroRegime.

AFL Integration:
  In your AFL code, after computing broker flow signals, write to:
    .cache/broker_flow.json
  
  Using AFL's writeFile() or external DDE/COM:
    file = FileOpen("C:\\path\\to\\macroregime\\.cache\\broker_flow.json", 1+2);
    FileWrite(file, CreateJSON(signals));
    FileClose(file);

JSON Schema (AFL writes this):
{
  "timestamp": "2026-04-18T10:30:00",
  "signals": [
    {
      "ticker": "BBCA.JK",
      "net_broker_score": 0.75,     // -1 to +1: positive = broker accumulating
      "dominant_broker": "DB",      // broker with biggest net buy
      "broker_action": "accumulate", // accumulate | distribute | neutral | churn
      "net_lot": 125000,            // net lot bought (positive) or sold (negative)
      "unusual_activity": true,     // volume >> avg
      "days_accumulating": 3,       // consecutive days of accumulation
      "price_vs_broker_avg": 0.02,  // price vs broker avg buy price (+2% = buying above avg)
      "bid_queue_depth": 0.68,      // bid queue fill ratio 0-1 (>0.6 = strong demand)
      "offer_thin": true,           // offer side is thin = easy markup
      "signal_quality": "high"      // high | medium | low
    }
  ],
  "market_summary": {
    "total_net_broker": 1250000,
    "dominant_market_maker": "DB",
    "market_action": "distribution",
    "foreign_vs_local": "foreign_buying"
  }
}

When AFL is not connected, the system runs in simulation mode
using price-based broker flow proxies.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List

_BROKER_FLOW_FILE = Path(".cache/broker_flow.json")
_MAX_AGE_HOURS = 8   # signals older than 8h are treated as stale


def _is_market_hours() -> bool:
    """Jakarta market hours: 9:00-15:45 WIB = 02:00-08:45 UTC."""
    now = datetime.now(timezone.utc)
    h = now.hour + now.minute / 60
    return 2.0 <= h <= 8.75


def _read_afl_file() -> Dict:
    """Read AFL-generated broker flow JSON."""
    try:
        if not _BROKER_FLOW_FILE.exists():
            return {}
        data = json.loads(_BROKER_FLOW_FILE.read_text())
        # Check freshness
        ts_str = data.get("timestamp", "")
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
                age = datetime.now(timezone.utc) - ts
                if age.total_seconds() > _MAX_AGE_HOURS * 3600:
                    return {"stale": True, "age_hours": round(age.total_seconds() / 3600, 1)}
            except Exception:
                pass
        return data
    except Exception:
        return {}


def _parse_signal(raw: Dict) -> Dict:
    """Normalize a raw AFL signal dict into a clean broker flow record."""
    ticker = str(raw.get("ticker", "")).strip()
    score = float(raw.get("net_broker_score", 0.0))
    action = str(raw.get("broker_action", "neutral"))
    dominant = str(raw.get("dominant_broker", "—"))
    net_lot = int(raw.get("net_lot", 0))
    unusual = bool(raw.get("unusual_activity", False))
    days_acc = int(raw.get("days_accumulating", 0))
    bid_depth = float(raw.get("bid_queue_depth", 0.5))
    offer_thin = bool(raw.get("offer_thin", False))
    quality = str(raw.get("signal_quality", "low"))

    # Composite conviction score
    conviction = min(1.0, (
        0.30 * abs(score)
        + 0.20 * (1.0 if unusual else 0.0)
        + 0.15 * min(1.0, days_acc / 5)
        + 0.20 * bid_depth
        + 0.15 * (1.0 if offer_thin else 0.0)
    ))

    signal_type = "buy" if score > 0.3 else ("sell" if score < -0.3 else "neutral")

    return {
        "ticker": ticker,
        "signal_type": signal_type,
        "score": round(score, 3),
        "conviction": round(conviction, 3),
        "action": action,
        "dominant_broker": dominant,
        "net_lot": net_lot,
        "unusual_activity": unusual,
        "days_accumulating": days_acc,
        "bid_queue_depth": round(bid_depth, 2),
        "offer_thin": offer_thin,
        "quality": quality,
        "label": {
            "accumulate": "🟢 Akumulasi",
            "distribute": "🔴 Distribusi",
            "neutral": "⚪ Neutral",
            "churn": "🟡 Churn",
        }.get(action, action),
    }


def load_broker_flow() -> Dict:
    """
    Main loader. Returns structured broker flow data.
    
    Returns:
        {
            "connected": bool,        # True = AFL is writing data
            "stale": bool,
            "signals": List[Dict],    # sorted by conviction desc
            "buys": List[str],        # top buy tickers
            "sells": List[str],       # top sell tickers
            "market_action": str,     # accumulation | distribution | neutral | mixed
            "market_summary": Dict,
            "timestamp": str,
        }
    """
    afl_data = _read_afl_file()
    stale = bool(afl_data.get("stale", False))
    connected = bool(afl_data) and not stale and "signals" in afl_data

    if connected:
        raw_signals = afl_data.get("signals", [])
        signals = [_parse_signal(s) for s in raw_signals if isinstance(s, dict)]
        signals.sort(key=lambda s: (-s["conviction"], -s["score"]))

        buys = [s["ticker"] for s in signals if s["signal_type"] == "buy"][:6]
        sells = [s["ticker"] for s in signals if s["signal_type"] == "sell"][:6]

        market_summary = afl_data.get("market_summary", {})
        market_action = str(market_summary.get("market_action", "neutral"))

        # High-conviction signals (conviction >= 0.60)
        high_conv = [s for s in signals if s["conviction"] >= 0.60]

        return {
            "connected": True,
            "stale": False,
            "signals": signals[:12],
            "high_conviction": high_conv[:4],
            "buys": buys,
            "sells": sells,
            "market_action": market_action,
            "market_summary": market_summary,
            "timestamp": afl_data.get("timestamp", ""),
            "signal_count": len(signals),
        }

    # Not connected — return empty but structured response
    stale_note = f"Stale ({afl_data.get('age_hours', '?')}h old)" if stale else "AFL not connected"
    return {
        "connected": False,
        "stale": stale,
        "signals": [],
        "high_conviction": [],
        "buys": [],
        "sells": [],
        "market_action": "unknown",
        "market_summary": {},
        "timestamp": "",
        "signal_count": 0,
        "note": stale_note,
        "setup_instructions": (
            "To connect AFL:\n"
            "1. In your AFL system, after computing broker flow signals:\n"
            "2. Write to: .cache/broker_flow.json\n"
            "3. Use the schema defined in data/broker_flow_loader.py\n"
            "4. AFL writes every bar/trigger; Python reads every 8h"
        ),
    }


def get_broker_regime_confirmation(broker_data: Dict, macro_tickers: List[str]) -> Dict:
    """
    Check if broker flow CONFIRMS or CONTRADICTS the macro regime.
    
    This is the bandarmologi × macro intersection:
    - If macro says Q1 (risk-on) AND broker accumulating banks/cyclicals → DOUBLE CONVICTION
    - If macro says Q3 AND broker distributing everything → CONFIRMED bearish
    - If macro says Q1 BUT broker distributing → WARNING, don't trust the regime
    """
    if not broker_data.get("connected"):
        return {"status": "unavailable", "confirmation": "unknown", "detail": "AFL not connected"}

    buys = set(broker_data.get("buys", []))
    sells = set(broker_data.get("sells", []))
    macro_set = set(macro_tickers)

    # Check overlap
    confirmed_buys = list(buys & macro_set)
    contradicted = list(sells & macro_set)

    if len(confirmed_buys) >= 2 and len(contradicted) == 0:
        status = "double_conviction"
        detail = f"Broker CONFIRMS macro: {', '.join(confirmed_buys[:3])} akumulasi"
    elif len(contradicted) >= 2:
        status = "contradiction"
        detail = f"PERINGATAN: Broker distributes {', '.join(contradicted[:3])} yang harusnya long di regime ini"
    elif confirmed_buys:
        status = "partial_confirm"
        detail = f"Partial confirmation: {', '.join(confirmed_buys[:2])}"
    else:
        status = "no_overlap"
        detail = "Broker flow tidak overlap dengan macro picks"

    return {
        "status": status,
        "confirmation": status,
        "confirmed_buys": confirmed_buys,
        "contradicted": contradicted,
        "detail": detail,
    }
