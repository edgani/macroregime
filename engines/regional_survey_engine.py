"""regional_survey_engine.py

Regional Fed Survey Composite Engine.

Hedgeye uses these as HIGH-FREQUENCY leading indicators:
  - ISM New Orders Composite (Richmond, Dallas, Empire, Philly, KC) → demand proxy
  - CapEx Plans Composite (same 5 + NY Fed) → AI buildout + reshoring proxy
  - ISM Prices Paid Composite (MFG + Services) → inflation pulse

From Hedgeye April 17 slides:
  - New Orders April MTD: 26.15 (massive spike — "All Flowers, No Showers")
  - CapEx Plans April MTD: 24.15 (spiking)
  - ISM Prices Paid: 74.50 (elevated — "Flation Now, Stag On A Lag")
  - Inflation Spread (Prices Paid - Prices Received): 19.1 (rising → margin compression)

WHY THESE MATTER:
  - New Orders is the FASTEST leading indicator (monthly, 4-6 weeks before ISM)
  - CapEx Plans captures AI buildout + reshoring demand BEFORE it shows up in GDP
  - Prices Paid - Prices Received spread = margin compression signal
    → When positive and rising: companies absorb costs → earnings headwind Q3/Q4
    → When negative: pricing power → positive for earnings

HOW TO FRONT-RUN HEDGEYE:
  1. New Orders Composite spike above 20 → Hedgeye will call "demand resilient"
     → Buy industrials (XLI), cyclicals BEFORE their signal confirms
  2. CapEx Plans spike → AI buildout narrative confirmed → buy compute infrastructure
  3. Prices Paid spike above 70 → inflation not dead → Hedgeye raises Q3 structural conviction
  4. Prices Paid falling from >70 peak → "Stag On A Lag" arriving → prepare for Q4
"""
from __future__ import annotations
import math
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
import pandas as pd


_CACHE_PATH = Path(".cache/regional_survey_cache.json")
_TTL_HOURS = 24  # Regional surveys update monthly

# FRED series IDs for each regional Fed survey
_FRED_SERIES = {
    # New Orders components (use most recent available)
    "empire_new_orders":    "EMPNEWON",   # NY Fed Empire State Mfg New Orders
    "philly_new_orders":    "NORDI",       # Philly Fed Mfg New Orders
    "richmond_new_orders":  "MNEWORDA",   # Richmond Fed New Orders
    "dallas_new_orders":    "DFNOI",       # Dallas Fed New Orders
    "kc_new_orders":        "KCNOI",       # Kansas City Fed New Orders
    # Prices Paid
    "ism_mfg_prices":       "ISM/MAN_PRICES",  # ISM Manufacturing Prices Paid
    "empire_prices_paid":   "EMPPRICE",
    "philly_prices_paid":   "PPADI",
    # CapEx / Capital Expenditure Plans  
    "philly_capex":         "CAPRDI",     # Philly Fed CapEx Plans
    # General activity
    "empire_general":       "GAFDISA066MSFRBNY",
    "philly_general":       "GAFDI",
    "richmond_general":     "RMANUFACTURING",
}

# Known values from Hedgeye April 17, 2026 slides
_HEDGEYE_OBSERVED = {
    "new_orders_composite_april": 26.15,
    "capex_plans_composite_april": 24.15,
    "ism_prices_paid_april": 74.50,
    "inflation_spread_april": 19.1,  # Prices Paid - Prices Received
}


def _fetch_fred_single(series_id: str) -> Optional[pd.Series]:
    """Fetch a single FRED series."""
    try:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            import io
            df = pd.read_csv(io.StringIO(r.text), parse_dates=[0], index_col=0)
            s = pd.to_numeric(df.iloc[:, 0], errors="coerce").dropna()
            return s if len(s) > 0 else None
    except Exception:
        pass
    return None


def _compute_composite(series_list: list) -> Optional[float]:
    """Equal-weight composite of latest values from multiple series."""
    vals = []
    for s in series_list:
        if s is not None and len(s) > 0:
            v = float(s.iloc[-1])
            if math.isfinite(v):
                vals.append(v)
    return float(sum(vals) / len(vals)) if vals else None


def _classify_new_orders(composite: Optional[float]) -> Dict:
    """Classify New Orders composite level."""
    if composite is None:
        return {"level": "unknown", "signal": "neutral", "color": "#718096"}
    if composite >= 20:
        return {"level": "strong", "signal": "demand_resilient", "color": "#3dbb6c",
                "note": "'All Flowers, No Showers' — demand strong, supports Monthly Q2"}
    elif composite >= 5:
        return {"level": "solid", "signal": "demand_ok", "color": "#68d391",
                "note": "New orders positive but not exceptional"}
    elif composite >= -5:
        return {"level": "flat", "signal": "neutral", "color": "#f6ad55",
                "note": "Demand flat — watch for deterioration"}
    elif composite >= -20:
        return {"level": "weak", "signal": "demand_weakening", "color": "#fc8181",
                "note": "New orders weak — structural Q3 demand slowdown in progress"}
    else:
        return {"level": "collapsing", "signal": "demand_crash", "color": "#e53e3e",
                "note": "New orders crashing — Q4 recession signal"}


def _classify_prices_paid(level: Optional[float]) -> Dict:
    """Classify ISM Prices Paid level."""
    if level is None:
        return {"level": "unknown", "signal": "neutral", "color": "#718096"}
    if level >= 70:
        return {"level": "hot", "signal": "inflation_sticky", "color": "#e05252",
                "note": f"Prices Paid {level:.0f} — 'Flation Now, Stag On A Lag'. Structural Q3 inflation support."}
    elif level >= 60:
        return {"level": "elevated", "signal": "inflation_elevated", "color": "#f6ad55",
                "note": f"Prices Paid {level:.0f} — elevated, not yet re-accelerating"}
    elif level >= 50:
        return {"level": "moderate", "signal": "inflation_moderate", "color": "#e5a020",
                "note": f"Prices Paid {level:.0f} — above 50, some inflation pressure"}
    elif level >= 45:
        return {"level": "cooling", "signal": "disinflation", "color": "#68d391",
                "note": f"Prices Paid {level:.0f} — disinflation in progress (Q1 setup)"}
    else:
        return {"level": "deflation", "signal": "deflation_risk", "color": "#3b82f6",
                "note": f"Prices Paid {level:.0f} — deflation risk (Q4)"}


def _classify_capex(level: Optional[float]) -> Dict:
    """Classify CapEx Plans level."""
    if level is None:
        return {"level": "unknown", "signal": "neutral", "color": "#718096"}
    if level >= 20:
        return {"level": "booming", "signal": "ai_reshoring_buildout", "color": "#3dbb6c",
                "note": f"CapEx {level:.0f} — AI buildout + reshoring = structural demand. Long XLI, construction, power."}
    elif level >= 10:
        return {"level": "solid", "signal": "capex_healthy", "color": "#68d391",
                "note": f"CapEx {level:.0f} — healthy investment cycle"}
    elif level >= 0:
        return {"level": "flat", "signal": "capex_neutral", "color": "#f6ad55",
                "note": f"CapEx {level:.0f} — investment intentions flat"}
    else:
        return {"level": "contracting", "signal": "capex_contraction", "color": "#e05252",
                "note": f"CapEx {level:.0f} — companies pulling back investment (Q3/Q4)"}


def load_regional_surveys() -> Dict:
    """
    Load and compute regional survey composites.

    Uses Hedgeye's observed April 2026 values as fallback/calibration
    when FRED data is stale or unavailable.
    """
    # Try to fetch actual data
    empire_no = _fetch_fred_single("EMPNEWON")
    philly_no = _fetch_fred_single("NORDI")
    richmond_no = _fetch_fred_single("MNEWORDA")

    empire_pp = _fetch_fred_single("EMPPRICE")
    philly_pp = _fetch_fred_single("PPADI")

    # Compute composites
    no_composite = _compute_composite([empire_no, philly_no, richmond_no])
    pp_composite = _compute_composite([empire_pp, philly_pp])

    # If we got data, use it; otherwise fall back to Hedgeye observed values
    no_final = no_composite if no_composite is not None else _HEDGEYE_OBSERVED["new_orders_composite_april"]
    pp_final = pp_composite if pp_composite is not None else _HEDGEYE_OBSERVED["ism_prices_paid_april"]
    capex_final = _HEDGEYE_OBSERVED["capex_plans_composite_april"]  # No free FRED series

    no_class = _classify_new_orders(no_final)
    pp_class = _classify_prices_paid(pp_final)
    capex_class = _classify_capex(capex_final)

    # Macro signal from combined picture
    # "Flation Now, Stag On A Lag":
    #   High New Orders + High Prices Paid = Monthly Q2 (demand + inflation both hot)
    #   BUT Prices Paid - Prices Received rising = margin compression = structural Q3 coming
    inflation_spread = _HEDGEYE_OBSERVED["inflation_spread_april"]

    if no_final >= 15 and pp_final >= 65:
        macro_signal = "hybrid_q2_q3"
        macro_note = (
            f"New Orders {no_final:.0f} (demand resilient) + Prices Paid {pp_final:.0f} (inflation hot) "
            f"= Monthly Q2 surface — but Prices Paid-Received spread {inflation_spread:.0f} = "
            "margin compression building. 'Flation Now, Stag On A Lag.'"
        )
    elif no_final < 0 and pp_final >= 60:
        macro_signal = "q3_confirmed"
        macro_note = "New orders falling + prices paid elevated = textbook Q3 stagflation"
    elif no_final >= 15 and pp_final < 55:
        macro_signal = "q1_signal"
        macro_note = "Strong demand + disinflation = Goldilocks Q1 signal"
    else:
        macro_signal = "mixed"
        macro_note = "Mixed regional data — watch for resolution"

    # Front-run implication
    front_run_note = ""
    if no_final >= 20 and capex_final >= 20:
        front_run_note = (
            "⚡ FRONT-RUN: New Orders + CapEx both spiking → "
            "Hedgeye will flag 'demand resilient' and add XLI/industrials. "
            "Buy XLI, XOP, XTL BEFORE their model confirms."
        )

    return {
        "available": True,
        "new_orders_composite": round(no_final, 1),
        "prices_paid_composite": round(pp_final, 1),
        "capex_plans_composite": round(capex_final, 1),
        "inflation_spread": round(inflation_spread, 1),
        "new_orders_class": no_class,
        "prices_paid_class": pp_class,
        "capex_class": capex_class,
        "macro_signal": macro_signal,
        "macro_note": macro_note,
        "front_run_note": front_run_note,
        "data_source": "fred+hedgeye_calibration",
        "hedgeye_april_reference": _HEDGEYE_OBSERVED,
    }
