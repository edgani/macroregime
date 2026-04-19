"""afl_bridge.py

AFL Bandarmologi Bridge — Complete AFL code + Python interface.

HOW IT WORKS:
1. Your AFL system computes broker flow signals per bar
2. AFL writes results to a JSON file via FileOpen/FileWrite
3. Python reads that JSON and integrates signals into MacroRegime

AFL CODE TO COPY INTO YOUR AFL SYSTEM:
=====================================
Paste this into your AFL as a "MacroRegime Bridge" formula.
Run it on IHSG stocks you want to monitor.

// MacroRegime Bridge — Broker Flow Export
// Paste this into AFL. Run once per day after market.

function ExportBrokerFlow() {
    // ── Broker flow calculation (replace with your existing logic) ──
    // These are PLACEHOLDERS — use your actual broker flow formulas
    
    // Net broker accumulation score (-1 to +1)
    // Positive = big brokers accumulating, Negative = distributing
    broker_buy_vol = Sum(IIf(Foreign(Name(), "C") > Ref(Foreign(Name(),"C"),-1) AND Volume > MA(Volume,20), Volume, 0), 5);
    broker_sell_vol = Sum(IIf(Foreign(Name(), "C") < Ref(Foreign(Name(),"C"),-1) AND Volume > MA(Volume,20), Volume, 0), 5);
    total_vol = broker_buy_vol + broker_sell_vol;
    net_broker_score = IIf(total_vol > 0, (broker_buy_vol - broker_sell_vol) / total_vol, 0);
    
    // Days of consecutive accumulation
    acc_day = IIf(net_broker_score > 0.1, 1, 0);
    days_acc = Sum(acc_day, 10);
    
    // Bid queue depth (0-1, approximated from buy/sell ratio)
    bid_depth = IIf(total_vol > 0, broker_buy_vol / total_vol, 0.5);
    
    // Unusual volume
    unusual = Volume > 2 * MA(Volume, 20);
    
    // Signal quality
    quality_score = 0.3 * ABS(net_broker_score) + 0.3 * bid_depth + 0.2 * (days_acc/10) + 0.2 * IIf(unusual, 1, 0);
    quality_str = IIf(quality_score >= 0.7, "high", IIf(quality_score >= 0.4, "medium", "low"));
    
    return net_broker_score;
}

// Market summary
total_net = 0;
bull_count = 0;
bear_count = 0;

// Write to JSON (adjust path to your macroregime directory)
fh = FileOpen("C:\\path\\to\\macroregime\\.cache\\broker_flow.json", 1+2, 1); 

if (fh != -1) {
    FileWrite(fh, "{");
    FileWrite(fh, "\"timestamp\": \"" + Now(5) + "\",");
    FileWrite(fh, "\"signals\": [");
    
    // Loop through watchlist (simplified — expand for your full universe)
    for (i = 0; i < CategoryGetCount(categoryWatchlist, 1); i++) {
        sym = CategoryGetSymbol(categoryWatchlist, 1, i);
        
        // Basic flow (replace with your broker flow logic)
        net_score = ExportBrokerFlow();
        action = IIf(net_score > 0.3, "accumulate", IIf(net_score < -0.3, "distribute", "neutral"));
        
        if (i > 0) FileWrite(fh, ",");
        FileWrite(fh, "{");
        FileWrite(fh, "\"ticker\": \"" + sym + ".JK\",");
        FileWrite(fh, "\"net_broker_score\": " + NumToStr(net_score, 3) + ",");
        FileWrite(fh, "\"broker_action\": \"" + action + "\",");
        FileWrite(fh, "\"days_accumulating\": " + NumToStr(days_acc, 0) + ",");
        FileWrite(fh, "\"bid_queue_depth\": " + NumToStr(bid_depth, 3) + ",");
        FileWrite(fh, "\"unusual_activity\": " + IIf(unusual, "true", "false") + ",");
        FileWrite(fh, "\"signal_quality\": \"" + quality_str + "\"");
        FileWrite(fh, "}");
        
        total_net = total_net + net_score;
        if (net_score > 0.3) bull_count++;
        if (net_score < -0.3) bear_count++;
    }
    
    FileWrite(fh, "],");
    FileWrite(fh, "\"market_summary\": {");
    FileWrite(fh, "\"total_net_score\": " + NumToStr(total_net, 3) + ",");
    FileWrite(fh, "\"accumulation_count\": " + NumToStr(bull_count, 0) + ",");
    FileWrite(fh, "\"distribution_count\": " + NumToStr(bear_count, 0) + ",");
    FileWrite(fh, "\"market_action\": \"" + IIf(bull_count > bear_count*1.5, "accumulation", IIf(bear_count > bull_count*1.5, "distribution", "mixed")) + "\",");
    FileWrite(fh, "\"foreign_vs_local\": \"unknown\"");
    FileWrite(fh, "}");
    FileWrite(fh, "}");
    FileClose(fh);
}
// END AFL CODE
=====================================

HENGKY ADINATA BANDARMOLOGI METHODOLOGY:
=========================================
The broker flow framework in MacroRegime is inspired by bandarmologi:

1. QUEUE READING (Bid-Offer Analysis):
   - bid_queue_depth > 0.65: Strong demand, offer side thin → price can be marked up
   - offer_thin=True: Easy for big players to accumulate without moving price much
   - Bid depth shrinking while price falling = distribution

2. BROKER PATTERN:
   - Dominant broker consistently buying over 3+ days = accumulation
   - Same broker on offer = distribution
   - Rotation between brokers = institutional handoff

3. SIGNAL QUALITY SCORING:
   - "high" = all signals aligned: net score > 0.5, unusual volume, 3+ days
   - "medium" = 2 of 3 signals
   - "low" = weak or mixed signal

4. CONFLUENCE WITH MACRO:
   - Broker accumulating BBCA when regime = Q1 → DOUBLE CONVICTION
   - Broker distributing ADRO when regime = Q4 → DOUBLE CONVICTION
   - Broker accumulating ADRO when regime = Q1 (coal not in favor) → ignore or wait
"""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

_BROKER_FLOW_FILE = Path(".cache/broker_flow.json")
_MAX_AGE_HOURS = 8


def get_setup_instructions() -> str:
    """Return AFL setup instructions for display in UI."""
    return """
## AFL Bridge Setup

1. **Open your AFL system** (AmiBroker)
2. **Create a new formula** called "MacroRegime_Bridge"  
3. **Paste the AFL code** from `data/afl_bridge.py`
4. **Update the file path** in `FileOpen()` to your MacroRegime directory
5. **Set the watchlist** to your IHSG universe
6. **Run once after market close** (or on a schedule via batch)
7. **Verify**: Check that `.cache/broker_flow.json` is created and updated

The system will automatically read this file every 8 hours.
When connected, you'll see broker flow in the IHSG Markets tab 
and double-conviction alerts when broker flow + macro regime align.
    """.strip()


def get_afl_code_template() -> str:
    """Return the AFL code template as a string for display."""
    return open(__file__).read().split("=====================================")[1].split("=====================================")[0].strip()


def validate_broker_flow_file() -> Dict:
    """Check if the broker flow file exists and is fresh."""
    if not _BROKER_FLOW_FILE.exists():
        return {"valid": False, "reason": "File not found. AFL not connected."}
    try:
        data = json.loads(_BROKER_FLOW_FILE.read_text())
        ts_str = data.get("timestamp", "")
        if not ts_str:
            return {"valid": False, "reason": "No timestamp in file"}
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - ts
            if age.total_seconds() > _MAX_AGE_HOURS * 3600:
                return {"valid": False, "reason": f"File stale ({age.total_seconds()/3600:.1f}h old)"}
        except Exception:
            pass  # if timestamp parse fails, still try to use the data
        n_signals = len(data.get("signals", []))
        return {
            "valid": True,
            "n_signals": n_signals,
            "timestamp": ts_str,
            "market_action": data.get("market_summary", {}).get("market_action", "unknown"),
        }
    except Exception as e:
        return {"valid": False, "reason": f"Parse error: {str(e)[:50]}"}
