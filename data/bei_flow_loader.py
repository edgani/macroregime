"""bei_flow_loader.py

IHSG Foreign Flow Tracker.
Foreign net buy/sell is THE most important leading indicator for IHSG.
When foreign buys → IHSG rallies. When foreign sells → IHSG drops.

Data sources (priority order):
1. IDX API: https://www.idx.co.id/ (official, free, daily)
2. EIDO ETF fund flow proxy (via yfinance — available when IDX unavailable)
3. Cache from last successful fetch

The IDX posts daily summary of net foreign buy/sell in IDR billions.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List
import requests
import pandas as pd

try:
    from utils.streamlit_compat import st
    _HAS_ST = True
except Exception:
    _HAS_ST = False

_CACHE_FILE = Path(".cache/bei_flow_cache.json")
_CACHE_TTL_HOURS = 4


def _load_cache() -> Dict:
    try:
        if _CACHE_FILE.exists():
            data = json.loads(_CACHE_FILE.read_text())
            ts = data.get("fetched_at", "")
            if ts:
                age = datetime.now(timezone.utc) - datetime.fromisoformat(ts)
                if age.total_seconds() < _CACHE_TTL_HOURS * 3600:
                    return data
    except Exception:
        pass
    return {}


def _save_cache(data: Dict) -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(data))
    except Exception:
        pass


def _fetch_idx_foreign_flow() -> Dict:
    """
    Try IDX public API for daily foreign trading summary.
    IDX publishes net foreign buy/sell daily after market close.
    """
    try:
        # IDX API endpoint for stock market summary
        url = "https://www.idx.co.id/primary/TradingData/GetMarketSummary"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.idx.co.id/",
        }
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            # Extract foreign net value (IDX returns in IDR billions)
            foreign_buy = float(data.get("ForeignBuy", 0) or 0)
            foreign_sell = float(data.get("ForeignSell", 0) or 0)
            net = foreign_buy - foreign_sell
            return {
                "source": "idx_api",
                "net_rp_billion": round(net / 1e9, 1),  # convert to billions IDR
                "foreign_buy_rp_billion": round(foreign_buy / 1e9, 1),
                "foreign_sell_rp_billion": round(foreign_sell / 1e9, 1),
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }
    except Exception:
        pass

    # Try alternative IDX endpoint
    try:
        url2 = "https://www.idx.co.id/umbraco/Surface/TradingSummary/GetTradeSummaryByDate"
        today = datetime.now().strftime("%Y-%m-%d")
        params = {"startDate": today, "endDate": today}
        resp2 = requests.get(url2, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        if resp2.status_code == 200:
            data2 = resp2.json()
            items = data2.get("Data", {}).get("TradeListItemModels", [])
            if items:
                item = items[0]
                fb = float(item.get("ForeignBuy", 0) or 0)
                fs = float(item.get("ForeignSell", 0) or 0)
                return {
                    "source": "idx_api_v2",
                    "net_rp_billion": round((fb - fs) / 1e9, 1),
                    "foreign_buy_rp_billion": round(fb / 1e9, 1),
                    "foreign_sell_rp_billion": round(fs / 1e9, 1),
                    "date": today,
                }
    except Exception:
        pass

    return {}


def _eido_proxy_flow() -> Dict:
    """
    EIDO (iShares MSCI Indonesia ETF) as foreign flow proxy.
    When EIDO has net inflow vs benchmark → foreign buying IHSG.
    Uses price + volume momentum as proxy.
    """
    try:
        import yfinance as yf
        eido = yf.download("EIDO", period="30d", progress=False, auto_adjust=True)
        eem = yf.download("EEM", period="30d", progress=False, auto_adjust=True)
        if eido.empty or eem.empty:
            return {}

        close_col = "Close" if "Close" in eido.columns else eido.columns[0]
        eido_ret_5d = float((eido[close_col].iloc[-1] / eido[close_col].iloc[-6]) - 1) if len(eido) >= 6 else 0.0
        eem_ret_5d = float((eem[close_col].iloc[-1] / eem[close_col].iloc[-6]) - 1) if len(eem) >= 6 else 0.0

        # Relative performance: EIDO vs EEM
        relative = eido_ret_5d - eem_ret_5d

        # Volume signal: above-average volume = foreign interest
        vol_col = "Volume" if "Volume" in eido.columns else None
        vol_ratio = 1.0
        if vol_col and len(eido) >= 20:
            avg_vol = eido[vol_col].iloc[-20:-1].mean()
            recent_vol = eido[vol_col].iloc[-5:].mean()
            vol_ratio = float(recent_vol / avg_vol) if avg_vol > 0 else 1.0

        # Estimate net flow direction
        flow_direction = "inflow" if relative > 0.005 else ("outflow" if relative < -0.005 else "neutral")
        # Rough IDR billion estimate (EIDO AUM ~500M USD, 1 move = ~50M USD = ~800B IDR)
        est_net = round(relative * 800, 1)  # very rough

        return {
            "source": "eido_proxy",
            "net_rp_billion": est_net,
            "eido_vs_eem_5d": round(relative * 100, 2),
            "eido_vol_ratio": round(vol_ratio, 2),
            "flow_direction": flow_direction,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "note": "Estimated via EIDO/EEM relative performance",
        }
    except Exception:
        pass

    return {}


def _build_flow_state(net: float, history: List[float]) -> Dict:
    """Classify foreign flow state and generate signals."""
    # 5-day rolling signal
    if len(history) >= 5:
        net_5d = sum(history[-5:])
    else:
        net_5d = net

    if net_5d > 300:
        trend = "strong_inflow"
        label = "🟢 Strong Inflow"
        regime_signal = "confirms_risk_on"
    elif net_5d > 50:
        trend = "inflow"
        label = "🟢 Inflow"
        regime_signal = "confirms_risk_on"
    elif net_5d > -50:
        trend = "neutral"
        label = "⚪ Neutral"
        regime_signal = "neutral"
    elif net_5d > -300:
        trend = "outflow"
        label = "🔴 Outflow"
        regime_signal = "confirms_risk_off"
    else:
        trend = "strong_outflow"
        label = "🔴 Strong Outflow"
        regime_signal = "confirms_risk_off"

    # Today's signal
    day_signal = "buy" if net > 100 else ("sell" if net < -100 else "neutral")

    return {
        "trend": trend,
        "label": label,
        "regime_signal": regime_signal,
        "net_5d_rp_billion": round(net_5d, 1),
        "day_signal": day_signal,
        "ihsg_implication": {
            "strong_inflow": "IHSG likely to rally. Add BBCA, BMRI, broad beta.",
            "inflow": "IHSG supported. Accumulate quality names.",
            "neutral": "Watch for direction. Stay with high-quality names only.",
            "outflow": "IHSG under pressure. Reduce cyclicals, hold defensives.",
            "strong_outflow": "IHSG risk-off. Minimize exposure. Only TLKM/ICBP defensible.",
        }.get(trend, "Monitor closely."),
    }


def load_bei_foreign_flow() -> Dict:
    """
    Main loader. Returns structured foreign flow data for IHSG.
    Cached for 4 hours to avoid hammering IDX API.
    """
    # Try cache first
    cached = _load_cache()
    if cached:
        return cached

    # Try IDX API
    raw = _fetch_idx_foreign_flow()

    # Fallback to EIDO proxy
    if not raw:
        raw = _eido_proxy_flow()

    if not raw:
        # Return minimal dict so system doesn't break
        return {
            "source": "unavailable",
            "net_rp_billion": 0.0,
            "flow_state": {"trend": "neutral", "label": "⚪ Data N/A", "regime_signal": "neutral", "net_5d_rp_billion": 0.0, "day_signal": "neutral", "ihsg_implication": "Foreign flow data unavailable."},
            "history": [],
            "available": False,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    net = raw.get("net_rp_billion", 0.0)

    # Build 5-day history from cache or estimate
    history = cached.get("history", [])
    history.append(net)
    if len(history) > 30:
        history = history[-30:]

    flow_state = _build_flow_state(net, history)

    result = {
        **raw,
        "flow_state": flow_state,
        "history": history,
        "available": True,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_cache(result)
    return result
