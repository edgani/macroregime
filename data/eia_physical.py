
from __future__ import annotations
import os
import numpy as np
import pandas as pd

SERIES = [
    ("Crude commercial stocks","DATA_GATED"),
    ("US crude production","DATA_GATED"),
    ("Refinery utilization","DATA_GATED"),
    ("Gasoline stocks","DATA_GATED"),
    ("Distillate stocks","DATA_GATED"),
    ("Natural gas storage","DATA_GATED"),
]

def load_eia_if_configured():
    key=os.getenv("EIA_API_KEY")
    if not key:
        return {"status":"DATA_GATED","reason":"Set EIA_API_KEY in Streamlit Secrets/environment to activate physical-energy feeds.","series":{}}
    # Exact EIA routes are kept fail-closed rather than guessing endpoint semantics.
    return {"status":"CONFIGURED_BUT_ADAPTER_REQUIRES_SERIES_ROUTES",
            "reason":"EIA key detected; map exact EIA v2 routes before treating physical data as live.",
            "series":{}}

def physical_snapshot(bundle):
    rows=[]
    status=(bundle or {}).get("status","DATA_GATED")
    series=(bundle or {}).get("series",{})
    for name,default in SERIES:
        x=series.get(name,{})
        rows.append({
            "metric":name,
            "latest":x.get("latest",np.nan),
            "4w_change":x.get("4w_change",np.nan),
            "13w_change":x.get("13w_change",np.nan),
            "own_history_percentile":x.get("own_history_percentile",np.nan),
            "status":x.get("status",status if status else default),
        })
    return pd.DataFrame(rows)
