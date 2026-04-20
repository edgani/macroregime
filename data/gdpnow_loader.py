"""gdpnow_loader.py

Atlanta Fed GDPNow — Forward-Looking GDP Nowcast.

This is the closest public proxy to Hedgeye's "predictive tracking algorithm."
Atlanta Fed updates daily on business days.

Why this matters:
  - FRED INDPRO lag = 45 days (January data shows in March)
  - GDPNow lag = 0 days (updates same day as data releases)
  - Hedgeye uses proprietary nowcast — GDPNow is best public equivalent
  - When GDPNow drops below prior quarter = structural quad shifts toward Q3/Q4

Source: https://www.atlantafed.org/cqer/research/gdpnow
"""
from __future__ import annotations
import json
import math
import re
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional

_CACHE = Path(".cache/gdpnow_cache.json")
_TTL_HOURS = 4  # Atlanta Fed updates a few times per day
_GDPNOW_URL = "https://www.atlantafed.org/cqer/research/gdpnow"
_GDPNOW_DATA_URL = "https://www.atlantafed.org/-/media/documents/cqer/researchcq/gdpnow/GDPNowCast.xlsx"


def _load_cache() -> Optional[Dict]:
    try:
        if _CACHE.exists():
            data = json.loads(_CACHE.read_text())
            ts = data.get("fetched_at", "")
            if ts:
                age = datetime.now(timezone.utc) - datetime.fromisoformat(ts)
                if age.total_seconds() < _TTL_HOURS * 3600:
                    return data
    except Exception:
        pass
    return None


def _save_cache(data: Dict) -> None:
    try:
        _CACHE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE.write_text(json.dumps(data))
    except Exception:
        pass


def _fetch_gdpnow_html() -> Optional[Dict]:
    """Scrape Atlanta Fed GDPNow page for current estimate."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 MacroRegimePro/9.0",
            "Accept": "text/html,application/xhtml+xml",
        }
        resp = requests.get(_GDPNOW_URL, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        
        html = resp.text
        
        # Try to extract the current estimate
        # Atlanta Fed shows "GDPNow model estimate for real GDP growth: X.X%"
        patterns = [
            r'GDPNow model estimate[^:]*:\s*([+-]?\d+\.?\d*)\s*percent',
            r'latest estimate[^:]*:\s*([+-]?\d+\.?\d*)\s*percent',
            r'nowcast[^:]*:\s*([+-]?\d+\.?\d*)\s*percent',
            r'(\d+\.\d+)\s*percent\s*\(.*?\d{4}\)',
        ]
        
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                val = float(m.group(1))
                # Look for date
                date_pat = r'(\w+ \d+,?\s*\d{4})'
                date_m = re.search(date_pat, html[max(0, m.start()-200):m.start()+200])
                date_str = date_m.group(1) if date_m else ""
                return {"estimate_pct": val, "date": date_str, "source": "html_parse"}
    except Exception:
        pass
    return None


def _fetch_gdpnow_via_proxy() -> Optional[Dict]:
    """
    Use FRED API / St Louis Fed data as backup.
    Atlanta Fed publishes GDPNow forecasts to FRED (series GDPNOW).
    """
    try:
        # Try FRED series GDPNOW
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDPNOW"
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200 and len(resp.text) > 100:
            import io
            import pandas as pd
            df = pd.read_csv(io.StringIO(resp.text), parse_dates=[0])
            df = df.dropna()
            if len(df) > 0:
                latest_val = float(df.iloc[-1, 1])
                latest_date = str(df.iloc[-1, 0].date())
                # Context: last 3 values for trend
                recent = df.iloc[-5:, 1].tolist()
                trend = "rising" if recent[-1] > recent[0] else "falling"
                return {
                    "estimate_pct": latest_val,
                    "date": latest_date,
                    "source": "fred_gdpnow",
                    "recent_trend": trend,
                    "recent_values": [round(v, 1) for v in recent],
                }
    except Exception:
        pass
    return None


def _classify_gdpnow(estimate_pct: float, prior_quarter_pct: float = 2.5) -> Dict:
    """
    Classify GDPNow relative to prior quarter and expectations.
    
    Key thresholds (based on Hedgeye's process):
    - Quad 1: GDP accelerating AND estimate > prior quarter
    - Quad 2: GDP strong but inflation also rising
    - Quad 3: GDP decelerating (estimate < prior quarter)
    - Quad 4: GDP sharply below prior and falling
    """
    delta = estimate_pct - prior_quarter_pct
    
    # Growth acceleration/deceleration
    if delta >= 0.5:
        growth_trend = "accelerating"
        q_bias = "Q1 or Q2"
        color = "#48bb78"
    elif delta >= 0:
        growth_trend = "holding"
        q_bias = "Q2 or Q3 borderline"
        color = "#f6ad55"
    elif delta >= -0.5:
        growth_trend = "decelerating"
        q_bias = "Q3"
        color = "#fc8181"
    else:
        growth_trend = "sharply decelerating"
        q_bias = "Q3 or Q4"
        color = "#e53e3e"
    
    # Absolute level
    if estimate_pct >= 3.0:
        level = "strong"
    elif estimate_pct >= 2.0:
        level = "solid"
    elif estimate_pct >= 1.0:
        level = "soft"
    else:
        level = "weak"
    
    return {
        "growth_trend": growth_trend,
        "q_bias": q_bias,
        "level": level,
        "color": color,
        "delta_vs_prior": round(delta, 2),
        "forward_looking_g_acc": delta >= 0,
    }


def load_gdpnow() -> Dict:
    """
    Main loader. Returns GDPNow estimate with regime implications.
    
    Returns:
        {
            "available": bool,
            "estimate_pct": float,      # GDP growth estimate (annualized %)
            "date": str,                # Last update date
            "source": str,              # How we got the data
            "growth_trend": str,        # accelerating/decelerating/etc
            "q_bias": str,              # Which quad this implies
            "forward_looking_g_acc": bool,  # True = growth accelerating (forward)
            "delta_vs_prior": float,    # vs prior quarter estimate
            "label": str,               # Display label
            "hedgeye_note": str,        # Context in Hedgeye framework
        }
    """
    # Try cache first
    cached = _load_cache()
    if cached:
        return cached
    
    # Try FRED GDPNOW series first (most reliable)
    data = _fetch_gdpnow_via_proxy()
    
    # Fallback to HTML scrape
    if not data:
        data = _fetch_gdpnow_html()
    
    if not data:
        return {
            "available": False,
            "estimate_pct": None,
            "label": "GDPNow N/A",
            "hedgeye_note": "Atlanta Fed GDPNow unavailable. Using FRED lagging data only.",
        }
    
    estimate = float(data.get("estimate_pct", 2.5))
    
    # Classify (assume Q4'25 GDP was 2.23% YoY based on Hedgeye March data)
    prior_q = 2.23
    classification = _classify_gdpnow(estimate, prior_q)
    
    # Hedgeye context
    if estimate < prior_q - 0.3:
        hedgeye_note = f"GDPNow {estimate:.1f}% < prior {prior_q:.1f}% → Structural growth decelerating. Supports Q3 quarterly."
    elif estimate > prior_q + 0.3:
        hedgeye_note = f"GDPNow {estimate:.1f}% > prior {prior_q:.1f}% → Growth accelerating. Consistent with Monthly Q2."
    else:
        hedgeye_note = f"GDPNow {estimate:.1f}% ≈ prior {prior_q:.1f}% → Borderline. Watch ISM and payrolls for confirmation."
    
    result = {
        "available": True,
        "estimate_pct": round(estimate, 2),
        "date": data.get("date", ""),
        "source": data.get("source", "unknown"),
        "recent_trend": data.get("recent_trend", "unknown"),
        "recent_values": data.get("recent_values", []),
        "prior_quarter_pct": prior_q,
        "label": f"GDPNow: {estimate:.1f}%",
        "hedgeye_note": hedgeye_note,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        **classification,
    }
    
    _save_cache(result)
    return result
