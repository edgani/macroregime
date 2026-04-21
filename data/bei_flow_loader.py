"""bei_flow_loader.py

IHSG Foreign Flow Tracker — Multi-source with real fallbacks.

Sources (priority):
1. IDX API: net foreign buy/sell daily
2. Yahoo Finance: ^JKSE + EIDO relative flow proxy  
3. Estimate from USD/IDR + JKSE correlation
"""
from __future__ import annotations
import json, math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Optional
import requests
import pandas as pd

_CACHE = Path(".cache/bei_flow_cache.json")
_TTL = 4 * 3600  # 4 hours


def _cache_load() -> Optional[Dict]:
    try:
        if _CACHE.exists():
            d = json.loads(_CACHE.read_text())
            if d and datetime.now(timezone.utc).timestamp() - d.get("_ts", 0) < _TTL:
                return d
    except Exception:
        pass
    return None


def _cache_save(d: Dict) -> None:
    try:
        _CACHE.parent.mkdir(parents=True, exist_ok=True)
        d["_ts"] = datetime.now(timezone.utc).timestamp()
        _CACHE.write_text(json.dumps(d))
    except Exception:
        pass


def _fetch_idx_api() -> Optional[Dict]:
    """Try IDX official API endpoints."""
    endpoints = [
        "https://www.idx.co.id/primary/TradingSummary/GetMarketSummary",
        "https://idx.co.id/primary/TradingSummary/GetBursaSummary",
        "https://www.idx.co.id/primary/IndexData/GetIndexSummary",
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh) Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.idx.co.id/",
        "X-Requested-With": "XMLHttpRequest",
    }
    for url in endpoints:
        try:
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200 and r.text.strip().startswith("{"):
                data = r.json()
                # Try to extract foreign flow
                for key in ["foreignBuy", "ForeignBuy", "foreign_buy", "netForeign", "NetForeign"]:
                    if key in data:
                        fb = float(data.get("foreignBuy", data.get("ForeignBuy", 0)) or 0)
                        fs = float(data.get("foreignSell", data.get("ForeignSell", 0)) or 0)
                        net = fb - fs
                        return {
                            "net_foreign_idr_bn": net / 1e9 if abs(net) > 1e6 else net,
                            "foreign_buy_idr_bn": fb / 1e9 if fb > 1e6 else fb,
                            "foreign_sell_idr_bn": fs / 1e9 if fs > 1e6 else fs,
                            "source": "idx_api",
                        }
        except Exception:
            continue
    return None


def _estimate_from_prices(prices: Dict = None) -> Dict:
    """
    Estimate foreign flow from market data correlations.
    
    When IDX API unavailable, use:
    - JKSE 1D return: strong positive = likely foreign buying
    - IDR/USD 1D: IDR strengthening = foreign capital inflow
    - EIDO 1D vs JKSE 1D: EIDO is foreign-held, tracks foreign interest
    
    This is a ROUGH proxy — order of magnitude correct, not exact.
    """
    if not prices:
        return {"net_foreign_idr_bn": None, "source": "unavailable"}
    
    try:
        jkse = prices.get("^JKSE", pd.Series())
        eido = prices.get("EIDO", prices.get("IDR=X", pd.Series()))
        idr = prices.get("IDR=X", pd.Series())  # USD/IDR (higher = weaker IDR)
        
        jkse_1d = float(jkse.pct_change(1).iloc[-1]) if len(jkse) > 1 else 0.0
        idr_1d = float(idr.pct_change(1).iloc[-1]) if len(idr) > 1 else 0.0
        eido_1d = float(eido.pct_change(1).iloc[-1]) if len(eido) > 1 else 0.0
        
        # IDR/USD drops = IDR strengthens = foreign buying
        idr_signal = -idr_1d  # flip: positive = IDR strong = foreign buying
        
        # Combined signal
        flow_signal = 0.50 * jkse_1d + 0.30 * idr_signal + 0.20 * eido_1d
        
        # Convert to rough IDR billions (JKSE 1% move ≈ net flow ~500 IDR bn historically)
        rough_net_bn = flow_signal * 50000  # very rough calibration
        
        # Flow state
        if flow_signal > 0.005:
            state = "inflow"
            state_label = "Foreign Buying (estimated)"
        elif flow_signal < -0.005:
            state = "outflow"
            state_label = "Foreign Selling (estimated)"
        else:
            state = "neutral"
            state_label = "Neutral (estimated)"
        
        return {
            "net_foreign_idr_bn": round(rough_net_bn, 0),
            "flow_state": state,
            "flow_state_label": state_label,
            "jkse_1d_pct": round(jkse_1d * 100, 2),
            "idr_1d_pct": round(idr_1d * 100, 2),
            "flow_signal": round(flow_signal, 4),
            "source": "price_proxy_estimate",
            "note": "Estimated from JKSE/IDR/EIDO correlation — IDX API unavailable",
        }
    except Exception:
        return {"net_foreign_idr_bn": None, "source": "unavailable"}


def load_bei_foreign_flow(prices: Dict = None) -> Dict:
    """
    Main loader for IHSG foreign flow.
    Returns dict with net_foreign_idr_bn and flow state.
    """
    # Try cache
    cached = _cache_load()
    if cached and cached.get("source") != "unavailable":
        return cached
    
    # Try IDX API
    idx_data = _fetch_idx_api()
    if idx_data:
        net = float(idx_data.get("net_foreign_idr_bn", 0) or 0)
        state = "inflow" if net > 100 else ("outflow" if net < -100 else "neutral")
        result = {
            **idx_data,
            "flow_state": state,
            "flow_state_label": "Foreign Buying" if state == "inflow" else ("Foreign Selling" if state == "outflow" else "Neutral"),
            "flow_score": min(1.0, max(0.0, 0.5 + net / 2000)),
        }
        _cache_save(result)
        return result
    
    # Fallback: price proxy
    est = _estimate_from_prices(prices)
    net = est.get("net_foreign_idr_bn")
    if net is not None:
        state = est.get("flow_state", "neutral")
        est["flow_score"] = min(1.0, max(0.0, 0.5 + net / 2000))
        _cache_save(est)
        return est
    
    # Full fallback
    return {
        "net_foreign_idr_bn": None,
        "flow_state": "unknown",
        "flow_state_label": "Data N/A — IDX API or EIDO proxy unavailable",
        "flow_score": 0.5,
        "source": "unavailable",
    }
