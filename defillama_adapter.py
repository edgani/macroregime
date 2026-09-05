from __future__ import annotations

import math
import urllib.parse
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd
import requests

FREE_BASE = "https://api.llama.fi"
HEADERS = {"User-Agent": "OpportunityIntelligence/3.0 research-dashboard", "Accept": "application/json"}


def _f(x: Any) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else math.nan
    except Exception:
        return math.nan


def _get(path: str, *, params: Optional[Mapping[str, Any]] = None, timeout: float = 5.0, session: Any = requests) -> Tuple[Any, str]:
    try:
        r = session.get(FREE_BASE + path, params=dict(params or {}), headers=HEADERS, timeout=timeout)
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}"
        return r.json(), ""
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _series_from_pairs(raw: Any) -> pd.Series:
    rows = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                ts = item.get("date") or item.get("timestamp")
                val = item.get("tvl") if "tvl" in item else item.get("totalCirculatingUSD")
                if isinstance(val, dict):
                    val = val.get("peggedUSD") or val.get("usd")
                v = _f(val)
                if ts is not None and math.isfinite(v):
                    rows.append((pd.to_datetime(ts, unit="s", errors="coerce", utc=True), v))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                v = _f(item[1])
                if math.isfinite(v):
                    rows.append((pd.to_datetime(item[0], unit="s", errors="coerce", utc=True), v))
    if not rows:
        return pd.Series(dtype=float)
    return pd.Series({t: v for t, v in rows if not pd.isna(t)}).sort_index()


def pct_change_days(s: pd.Series, days: int) -> float:
    s = pd.to_numeric(s, errors="coerce").dropna().sort_index()
    if len(s) < 2:
        return math.nan
    end = s.index[-1]
    target = end - pd.Timedelta(days=int(days))
    before = s[s.index <= target]
    if before.empty:
        return math.nan
    base = _f(before.iloc[-1]); cur = _f(s.iloc[-1])
    return cur / base - 1.0 if math.isfinite(cur) and math.isfinite(base) and base > 0 else math.nan


def protocol_tvl(slug: str, *, session: Any = requests) -> Tuple[pd.Series, str]:
    j, err = _get(f"/protocol/{urllib.parse.quote(str(slug))}", session=session)
    if err or not isinstance(j, dict):
        return pd.Series(dtype=float), err or "invalid payload"
    return _series_from_pairs(j.get("tvl") or []), ""


def chain_tvl(chain: str, *, session: Any = requests) -> Tuple[pd.Series, str]:
    j, err = _get(f"/v2/historicalChainTvl/{urllib.parse.quote(str(chain))}", session=session)
    return (_series_from_pairs(j), err) if not err else (pd.Series(dtype=float), err)


def chain_stablecoins(chain: str, *, session: Any = requests) -> Tuple[pd.Series, str]:
    j, err = _get(f"/stablecoincharts/{urllib.parse.quote(str(chain))}", session=session)
    return (_series_from_pairs(j), err) if not err else (pd.Series(dtype=float), err)


def _overview_metric(path: str, data_type: Optional[str] = None, *, session: Any = requests) -> Tuple[Dict[str, Any], str]:
    params = {"excludeTotalDataChart": "false", "excludeTotalDataChartBreakdown": "true"}
    if data_type:
        params["dataType"] = data_type
    j, err = _get(path, params=params, session=session)
    if err or not isinstance(j, dict):
        return {}, err or "invalid payload"
    chart = j.get("totalDataChart") or []
    s = _series_from_pairs(chart)
    return {
        "current": _f(s.iloc[-1]) if len(s) else _f(j.get("total24h")),
        "change_1d": pct_change_days(s, 1),
        "change_7d": pct_change_days(s, 7),
        "history": s,
        "total24h": _f(j.get("total24h")),
        "total7d": _f(j.get("total7d")),
        "change_1d_api": _f(j.get("change_1d")),
        "change_7d_api": _f(j.get("change_7d")),
    }, ""


def chain_dex(chain: str, *, session: Any = requests) -> Tuple[Dict[str, Any], str]:
    return _overview_metric(f"/overview/dexs/{urllib.parse.quote(str(chain))}", session=session)


def chain_fees(chain: str, data_type: str = "dailyFees", *, session: Any = requests) -> Tuple[Dict[str, Any], str]:
    return _overview_metric(f"/overview/fees/{urllib.parse.quote(str(chain))}", data_type=data_type, session=session)


def protocol_fees(slug: str, data_type: str = "dailyRevenue", *, session: Any = requests) -> Tuple[Dict[str, Any], str]:
    return _overview_metric(f"/summary/fees/{urllib.parse.quote(str(slug))}", data_type=data_type, session=session)


def chain_snapshot(chain: str, *, session: Any = requests) -> Dict[str, Any]:
    tvl, e1 = chain_tvl(chain, session=session)
    stable, e2 = chain_stablecoins(chain, session=session)
    dex, e3 = chain_dex(chain, session=session)
    fees, e4 = chain_fees(chain, "dailyFees", session=session)
    rev, e5 = chain_fees(chain, "dailyRevenue", session=session)
    errors = [x for x in [e1, e2, e3, e4, e5] if x]
    fields = {
        "tvl": _f(tvl.iloc[-1]) if len(tvl) else math.nan,
        "tvl_7d": pct_change_days(tvl, 7),
        "tvl_30d": pct_change_days(tvl, 30),
        "stablecoins": _f(stable.iloc[-1]) if len(stable) else math.nan,
        "stablecoins_7d": pct_change_days(stable, 7),
        "stablecoins_30d": pct_change_days(stable, 30),
        "dex_volume_24h": _f(dex.get("total24h")),
        "dex_volume_7d_change": _f(dex.get("change_7d_api")) / 100.0 if math.isfinite(_f(dex.get("change_7d_api"))) else _f(dex.get("change_7d")),
        "fees_24h": _f(fees.get("total24h")),
        "fees_7d_change": _f(fees.get("change_7d_api")) / 100.0 if math.isfinite(_f(fees.get("change_7d_api"))) else _f(fees.get("change_7d")),
        "revenue_24h": _f(rev.get("total24h")),
        "revenue_7d_change": _f(rev.get("change_7d_api")) / 100.0 if math.isfinite(_f(rev.get("change_7d_api"))) else _f(rev.get("change_7d")),
        "defillama_errors": errors,
        "source_quality": "HIGH" if not errors else ("MEDIUM" if len(errors) <= 2 else "LOW"),
    }
    # TVL can rise from asset repricing; stablecoin + activity confirmation is intentionally separate.
    confirms = [fields["stablecoins_7d"], fields["dex_volume_7d_change"], fields["fees_7d_change"]]
    fields["ecosystem_confirmation_count"] = int(sum(math.isfinite(x) and x > 0 for x in confirms))
    return fields
