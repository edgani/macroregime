"""Resilient live derivatives, options and squeeze context for War Room OS.

This module is deliberately conservative:
* no synthetic observations;
* provider failures degrade to STALE last-good cache or explicit ERROR/NOT_CONFIGURED;
* option-chain positioning is not dealer inventory;
* squeeze scores are descriptive pressure indices, never calibrated probabilities;
* reference zones are not guaranteed targets.

Public feeds (no key): Binance Futures, Bybit, OKX, Deribit.
Optional licensed feeds: Massive options, ORTEX short interest, Intrinio official short
interest, CoinGlass liquidation/OI analytics, and an Unusual Whales stream bridge.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import hashlib
import json
import math
import os
import statistics
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / ".cache" / "live_intelligence"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_PATH = CACHE_DIR / "derivatives_history.jsonl"


@dataclass
class FeedStatus:
    provider: str
    dataset: str
    state: str
    observed: bool = True
    fetched_at: Optional[str] = None
    age_seconds: Optional[float] = None
    stale_after_seconds: Optional[int] = None
    records: int = 0
    note: str = ""
    endpoint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _network_enabled() -> bool:
    return os.getenv("WARROOM_NETWORK_MODE", "live").strip().lower() not in {"offline", "disabled", "0", "false"}


def _epoch_seconds(value: Any) -> Optional[float]:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    if x > 1e18:
        x /= 1e9
    elif x > 1e15:
        x /= 1e6
    elif x > 1e12:
        x /= 1e3
    return x


def _iso(value: Any = None) -> str:
    if value in (None, ""):
        return _utc_now()
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return _utc_now()
        try:
            x = _epoch_seconds(s)
        except Exception:
            x = None
        if x is None:
            return s
    else:
        x = _epoch_seconds(value)
    if x is None:
        return _utc_now()
    try:
        return datetime.fromtimestamp(x, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    except (ValueError, OSError, OverflowError):
        return _utc_now()


def _f(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value in (None, "", "null"):
            return default
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def _i(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _median(values: Iterable[Optional[float]]) -> Optional[float]:
    clean = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    return statistics.median(clean) if clean else None


def _mean(values: Iterable[Optional[float]]) -> Optional[float]:
    clean = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    return sum(clean) / len(clean) if clean else None


def _pct_change(new: Optional[float], old: Optional[float]) -> Optional[float]:
    if new is None or old in (None, 0):
        return None
    return (new / old - 1.0) * 100.0


def _clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in value)


def _cache_path(key: str) -> Path:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return CACHE_DIR / f"{_safe_name(key)[:70]}_{digest}.json"


def _read_cache_any(key: str) -> Optional[Dict[str, Any]]:
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["_cache_age_seconds"] = round(max(0.0, time.time() - path.stat().st_mtime), 2)
        return payload
    except Exception:
        return None


def _write_cache(key: str, payload: Dict[str, Any]) -> None:
    path = _cache_path(key)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, default=str, separators=(",", ":")), encoding="utf-8")
    temp.replace(path)


def _session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=1,
        connect=1,
        read=1,
        backoff_factor=0.25,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=30))
    session.headers.update({"User-Agent": "WarRoomOS/2.0 live-intelligence"})
    return session


HTTP = _session()


def _request_json(
    *,
    provider: str,
    dataset: str,
    cache_key: str,
    url: str,
    ttl_seconds: int,
    stale_after_seconds: int,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    method: str = "GET",
    json_body: Optional[Dict[str, Any]] = None,
    timeout: float = 6.0,
) -> Dict[str, Any]:
    """Fetch JSON with fresh-cache and stale last-good failover."""
    cached = _read_cache_any(cache_key)
    if cached is not None and float(cached.get("_cache_age_seconds") or 0) <= ttl_seconds:
        return {
            "ok": True,
            "state": "LIVE",
            "payload": cached.get("payload"),
            "fetched_at": cached.get("fetched_at"),
            "age_seconds": cached.get("_cache_age_seconds", 0),
            "from_cache": True,
            "note": "fresh cache",
        }
    if not _network_enabled():
        if cached is not None:
            return {"ok": True, "state": "STALE", "payload": cached.get("payload"),
                    "fetched_at": cached.get("fetched_at"), "age_seconds": cached.get("_cache_age_seconds"),
                    "from_cache": True, "note": "offline mode: last-good cache"}
        return {"ok": False, "state": "OFFLINE", "payload": None, "fetched_at": None,
                "age_seconds": None, "from_cache": False, "note": "WARROOM_NETWORK_MODE=offline"}
    timeout = min(float(timeout), float(os.getenv("WARROOM_HTTP_TIMEOUT", "6")))
    try:
        if method.upper() == "POST":
            response = HTTP.post(url, params=params, headers=headers, json=json_body, timeout=timeout)
        else:
            response = HTTP.get(url, params=params, headers=headers, timeout=timeout)
        if not (200 <= response.status_code < 300):
            snippet = response.text[:240].replace("\n", " ")
            raise RuntimeError(f"HTTP {response.status_code}: {snippet}")
        payload = response.json()
        wrapped = {"payload": payload, "fetched_at": _utc_now()}
        _write_cache(cache_key, wrapped)
        return {
            "ok": True,
            "state": "LIVE",
            "payload": payload,
            "fetched_at": wrapped["fetched_at"],
            "age_seconds": 0.0,
            "from_cache": False,
            "note": "network",
        }
    except Exception as exc:
        stale = _read_cache_any(cache_key)
        if stale is not None:
            age = float(stale.get("_cache_age_seconds") or 0)
            return {
                "ok": True,
                "state": "STALE",
                "payload": stale.get("payload"),
                "fetched_at": stale.get("fetched_at"),
                "age_seconds": age,
                "from_cache": True,
                "note": f"last-good cache after {type(exc).__name__}: {exc}",
            }
        return {
            "ok": False,
            "state": "ERROR",
            "payload": None,
            "fetched_at": None,
            "age_seconds": None,
            "from_cache": False,
            "note": f"{type(exc).__name__}: {exc}",
        }


def _status_from_result(
    result: Dict[str, Any], provider: str, dataset: str, stale_after: int,
    records: int, note: str, endpoint: str,
) -> Dict[str, Any]:
    state = result.get("state", "ERROR")
    if state == "LIVE" and records == 0:
        state = "EMPTY"
    return FeedStatus(
        provider=provider,
        dataset=dataset,
        state=state,
        fetched_at=result.get("fetched_at"),
        age_seconds=result.get("age_seconds"),
        stale_after_seconds=stale_after,
        records=records,
        note=(note + (f" · {result.get('note')}" if result.get("note") else "")).strip(" ·"),
        endpoint=endpoint,
    ).to_dict()


def _not_configured(provider: str, dataset: str, env_name: str, stale_after: int = 60) -> Dict[str, Any]:
    return {
        "status": FeedStatus(
            provider=provider, dataset=dataset, state="NOT_CONFIGURED", stale_after_seconds=stale_after,
            note=f"Set {env_name}; no placeholder values are emitted."
        ).to_dict(),
        "data": [],
    }


def _extract_rows(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for path in (
        ("results",), ("data",), ("result", "list"), ("result",), ("payload",),
        ("data", "items"), ("data", "data"), ("response",),
    ):
        cur: Any = payload
        for key in path:
            if not isinstance(cur, dict) or key not in cur:
                cur = None
                break
            cur = cur[key]
        if isinstance(cur, list):
            return [x for x in cur if isinstance(x, dict)]
    return []


def _payload_record_count(payload: Any) -> int:
    """Count meaningful vendor records without calling dict payloads empty.

    Several vendor endpoints return a single structured object (for example a
    liquidation heatmap or map) rather than a list of rows. Those objects are
    still live observations and must not be downgraded to EMPTY.
    """
    rows = _extract_rows(payload)
    if rows:
        return len(rows)
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict) and data:
            return 1
        if payload:
            return 1
    if isinstance(payload, list):
        return len(payload)
    return 0


def _parse_csv_env(name: str, default: Sequence[str]) -> List[str]:
    raw = os.getenv(name, "").strip()
    values = [x.strip().upper() for x in raw.split(",") if x.strip()] if raw else list(default)
    out: List[str] = []
    for value in values:
        if value not in out:
            out.append(value)
    return out


def _desk_watchlist(desk: Dict[str, Any], limit: int = 8) -> List[str]:
    configured = _parse_csv_env("WARROOM_OPTIONS_WATCHLIST", [])
    if configured:
        return configured[:limit]
    values: List[str] = []
    # Liquid anchors come first. Previously five obscure setup tickers could consume the entire
    # watchlist and make the aggregate US options panel read NO_DATA even while SPY/QQQ chains existed.
    anchors = _parse_csv_env("WARROOM_OPTIONS_ANCHORS", ["SPY", "QQQ", "IWM", "SMH", "NVDA", "AMD"])
    for ticker in anchors:
        if ticker not in values:
            values.append(ticker)
    for market_id in ("us",):
        market = ((desk.get("markets") or {}).get(market_id) or {})
        for row in market.get("setups") or []:
            ticker = str(row.get("tk") or "").upper().strip()
            if ticker and ticker not in values and ticker.replace(".", "").isalnum():
                values.append(ticker)
    for row in desk.get("alpha") or []:
        ticker = str(row.get("tk") or "").upper().strip()
        if ticker and ticker not in values and ticker.replace(".", "").isalnum():
            values.append(ticker)
    return values[:limit]


def _request_group(specs: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Run independent provider endpoints concurrently so one adapter has a bounded wall clock."""
    if not specs:
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(len(specs), 8)) as pool:
        futures = {pool.submit(_request_json, **kwargs): name for name, kwargs in specs.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                out[name] = future.result()
            except Exception as exc:
                out[name] = {"ok": False, "state": "ERROR", "payload": None, "note": f"{type(exc).__name__}: {exc}"}
    return out


# ---------------------------------------------------------------------------
# Public crypto derivatives feeds
# ---------------------------------------------------------------------------


def fetch_binance_symbol(symbol: str) -> Dict[str, Any]:
    base = os.getenv("BINANCE_FUTURES_BASE_URL", "https://fapi.binance.com").rstrip("/")
    endpoints = {
        "premium": (f"{base}/fapi/v1/premiumIndex", {"symbol": symbol}),
        "oi": (f"{base}/fapi/v1/openInterest", {"symbol": symbol}),
        "ratio": (f"{base}/futures/data/globalLongShortAccountRatio", {"symbol": symbol, "period": "5m", "limit": 2}),
        "taker": (f"{base}/futures/data/takerlongshortRatio", {"symbol": symbol, "period": "5m", "limit": 2}),
    }
    results = _request_group({name: dict(
        provider="Binance", dataset=f"{name}_{symbol}", cache_key=f"binance_{name}_{symbol}",
        url=url, params=params, ttl_seconds=12 if name in {"premium", "oi"} else 45,
        stale_after_seconds=90, timeout=6,
    ) for name, (url, params) in endpoints.items()})
    premium = results["premium"].get("payload") if results["premium"].get("ok") else {}
    oi = results["oi"].get("payload") if results["oi"].get("ok") else {}
    ratio_rows = results["ratio"].get("payload") if results["ratio"].get("ok") else []
    taker_rows = results["taker"].get("payload") if results["taker"].get("ok") else []
    if not isinstance(premium, dict): premium = {}
    if not isinstance(oi, dict): oi = {}
    if not isinstance(ratio_rows, list): ratio_rows = []
    if not isinstance(taker_rows, list): taker_rows = []
    ratio = ratio_rows[-1] if ratio_rows else {}
    taker = taker_rows[-1] if taker_rows else {}
    state = "LIVE" if any(r.get("state") == "LIVE" for r in results.values()) else (
        "STALE" if any(r.get("state") == "STALE" for r in results.values()) else "ERROR"
    )
    row = {
        "provider": "Binance", "symbol": symbol, "asset": symbol.replace("USDT", ""),
        "timestamp": _iso(premium.get("time") or oi.get("time") or ratio.get("timestamp")),
        "mark_price": _f(premium.get("markPrice")), "index_price": _f(premium.get("indexPrice")),
        "funding_rate": _f(premium.get("lastFundingRate")), "next_funding_time": _iso(premium.get("nextFundingTime")) if premium.get("nextFundingTime") else None,
        "open_interest_contracts": _f(oi.get("openInterest")), "open_interest_value": None,
        "global_long_short_ratio": _f(ratio.get("longShortRatio")),
        "long_account_pct": (_f(ratio.get("longAccount")) or 0) * 100 if ratio else None,
        "short_account_pct": (_f(ratio.get("shortAccount")) or 0) * 100 if ratio else None,
        "taker_buy_sell_ratio": _f(taker.get("buySellRatio")),
        "taker_buy_volume": _f(taker.get("buyVol")), "taker_sell_volume": _f(taker.get("sellVol")),
        "state": state, "semantics": "Exchange-specific futures state; not a complete market aggregate.",
    }
    if row["open_interest_contracts"] is not None and row["mark_price"] is not None:
        row["open_interest_value"] = row["open_interest_contracts"] * row["mark_price"]
    statuses = [
        _status_from_result(r, "Binance", f"{k}_{symbol}", 90, 1 if r.get("ok") else 0,
                            "Public USD-M futures state.", endpoints[k][0])
        for k, r in results.items()
    ]
    return {"row": row, "statuses": statuses}


def fetch_bybit_symbol(symbol: str) -> Dict[str, Any]:
    base = os.getenv("BYBIT_BASE_URL", "https://api.bybit.com").rstrip("/")
    calls = {
        "ticker": (f"{base}/v5/market/tickers", {"category": "linear", "symbol": symbol}, 12),
        "oi": (f"{base}/v5/market/open-interest", {"category": "linear", "symbol": symbol, "intervalTime": "5min", "limit": 2}, 30),
        "ratio": (f"{base}/v5/market/account-ratio", {"category": "linear", "symbol": symbol, "period": "5min", "limit": 2}, 45),
    }
    results = _request_group({k: dict(provider="Bybit", dataset=f"{k}_{symbol}", cache_key=f"bybit_{k}_{symbol}",
                                url=u, params=p, ttl_seconds=ttl, stale_after_seconds=90, timeout=6)
               for k, (u, p, ttl) in calls.items()})
    ticker_rows = _extract_rows(results["ticker"].get("payload"))
    oi_rows = _extract_rows(results["oi"].get("payload"))
    ratio_rows = _extract_rows(results["ratio"].get("payload"))
    ticker = ticker_rows[0] if ticker_rows else {}
    oi = oi_rows[0] if oi_rows else {}
    ratio = ratio_rows[0] if ratio_rows else {}
    mark = _f(ticker.get("markPrice"))
    contracts = _f(oi.get("openInterest") or ticker.get("openInterest"))
    state = "LIVE" if any(r.get("state") == "LIVE" for r in results.values()) else (
        "STALE" if any(r.get("state") == "STALE" for r in results.values()) else "ERROR"
    )
    buy_ratio = _f(ratio.get("buyRatio"))
    sell_ratio = _f(ratio.get("sellRatio"))
    row = {
        "provider": "Bybit", "symbol": symbol, "asset": symbol.replace("USDT", ""),
        "timestamp": _iso(ticker.get("timestamp") or oi.get("timestamp") or ratio.get("timestamp")),
        "mark_price": mark, "index_price": _f(ticker.get("indexPrice")),
        "funding_rate": _f(ticker.get("fundingRate")), "next_funding_time": _iso(ticker.get("nextFundingTime")) if ticker.get("nextFundingTime") else None,
        "open_interest_contracts": contracts,
        "open_interest_value": contracts * mark if contracts is not None and mark is not None else None,
        "global_long_short_ratio": buy_ratio / sell_ratio if buy_ratio is not None and sell_ratio not in (None, 0) else None,
        "long_account_pct": buy_ratio * 100 if buy_ratio is not None else None,
        "short_account_pct": sell_ratio * 100 if sell_ratio is not None else None,
        "taker_buy_sell_ratio": None,
        "turnover_24h": _f(ticker.get("turnover24h")), "volume_24h": _f(ticker.get("volume24h")),
        "state": state, "semantics": "Exchange-specific perpetual state; account ratio is not position size.",
    }
    statuses = [_status_from_result(results[k], "Bybit", f"{k}_{symbol}", 90, 1 if results[k].get("ok") else 0,
                                    "Public derivatives state.", calls[k][0]) for k in calls]
    return {"row": row, "statuses": statuses}


def fetch_okx_symbol(asset: str) -> Dict[str, Any]:
    base = os.getenv("OKX_BASE_URL", "https://www.okx.com").rstrip("/")
    inst_id = f"{asset}-USDT-SWAP"
    calls = {
        "ticker": (f"{base}/api/v5/market/ticker", {"instId": inst_id}, 12),
        "oi": (f"{base}/api/v5/public/open-interest", {"instType": "SWAP", "instId": inst_id}, 20),
        "funding": (f"{base}/api/v5/public/funding-rate", {"instId": inst_id}, 20),
    }
    results = _request_group({k: dict(provider="OKX", dataset=f"{k}_{asset}", cache_key=f"okx_{k}_{asset}",
                                url=u, params=p, ttl_seconds=ttl, stale_after_seconds=90, timeout=6)
               for k, (u, p, ttl) in calls.items()})
    ticker_rows = _extract_rows(results["ticker"].get("payload")); ticker = ticker_rows[0] if ticker_rows else {}
    oi_rows = _extract_rows(results["oi"].get("payload")); oi = oi_rows[0] if oi_rows else {}
    fund_rows = _extract_rows(results["funding"].get("payload")); funding = fund_rows[0] if fund_rows else {}
    mark = _f(ticker.get("last") or funding.get("markPx"))
    oi_contracts = _f(oi.get("oi"))
    oi_usd = _f(oi.get("oiUsd"))
    state = "LIVE" if any(r.get("state") == "LIVE" for r in results.values()) else (
        "STALE" if any(r.get("state") == "STALE" for r in results.values()) else "ERROR"
    )
    row = {
        "provider": "OKX", "symbol": inst_id, "asset": asset,
        "timestamp": _iso(ticker.get("ts") or oi.get("ts") or funding.get("fundingTime")),
        "mark_price": mark, "index_price": _f(funding.get("indexPx")),
        "funding_rate": _f(funding.get("fundingRate")), "next_funding_time": _iso(funding.get("nextFundingTime")) if funding.get("nextFundingTime") else None,
        "open_interest_contracts": oi_contracts, "open_interest_value": oi_usd,
        "global_long_short_ratio": None, "long_account_pct": None, "short_account_pct": None,
        "taker_buy_sell_ratio": None, "volume_24h": _f(ticker.get("vol24h")), "turnover_24h": _f(ticker.get("volCcy24h")),
        "state": state, "semantics": "Exchange-specific swap state; contract units vary by instrument.",
    }
    statuses = [_status_from_result(results[k], "OKX", f"{k}_{asset}", 90, 1 if results[k].get("ok") else 0,
                                    "Public swap state.", calls[k][0]) for k in calls]
    return {"row": row, "statuses": statuses}


def fetch_deribit_currency(currency: str) -> Dict[str, Any]:
    base = os.getenv("DERIBIT_BASE_URL", "https://www.deribit.com").rstrip("/")
    url = f"{base}/api/v2/public/get_book_summary_by_currency"
    result = _request_json(provider="Deribit", dataset=f"option_book_{currency}", cache_key=f"deribit_summary_{currency}",
                           url=url, params={"currency": currency, "kind": "option"}, ttl_seconds=20,
                           stale_after_seconds=120, timeout=8)
    rows = _extract_rows(result.get("payload"))
    normalized: List[Dict[str, Any]] = []
    for r in rows:
        instrument = str(r.get("instrument_name") or "")
        parts = instrument.split("-")
        if len(parts) < 4:
            continue
        expiry, strike_raw, cp = parts[-3], parts[-2], parts[-1]
        normalized.append({
            "provider": "Deribit", "underlying": currency, "contract": instrument,
            "expiry_code": expiry, "strike": _f(strike_raw), "option_type": "call" if cp.upper() == "C" else "put",
            "open_interest": _f(r.get("open_interest"), 0.0) or 0.0,
            "volume": _f(r.get("volume"), 0.0) or 0.0, "volume_usd": _f(r.get("volume_usd")),
            "mark_price": _f(r.get("mark_price")), "bid_price": _f(r.get("bid_price")), "ask_price": _f(r.get("ask_price")),
            "bid": _f(r.get("bid_price")), "ask": _f(r.get("ask_price")),
            "mark_iv": _f(r.get("mark_iv")), "underlying_price": _f(r.get("underlying_price")),
            "timestamp": _iso(r.get("creation_timestamp")),
        })
    status = _status_from_result(result, "Deribit", f"option_book_{currency}", 120, len(normalized),
                                 "Public crypto option book summary; OI is venue-specific.", url)
    return {"status": status, "data": normalized}


# ---------------------------------------------------------------------------
# Licensed US options / short interest / liquidation feeds
# ---------------------------------------------------------------------------



def _bs_delta_gamma(spot: float, strike: float, iv: float, days: float, option_type: str,
                    rate: float = 0.04, dividend: float = 0.0) -> Tuple[Optional[float], Optional[float]]:
    if spot <= 0 or strike <= 0 or iv <= 0 or days <= 0:
        return None, None
    t = max(days / 365.0, 1.0 / 365.0)
    root = math.sqrt(t)
    d1 = (math.log(spot / strike) + (rate - dividend + 0.5 * iv * iv) * t) / (iv * root)
    delta_call = math.exp(-dividend * t) * _norm_cdf(d1)
    delta = delta_call if option_type == "call" else delta_call - math.exp(-dividend * t)
    gamma = math.exp(-dividend * t) * _norm_pdf(d1) / (spot * iv * root)
    return delta, gamma


def fetch_yfinance_option_chain(ticker: str, max_expiries: int = 2, limit: int = 300) -> Dict[str, Any]:
    """Free delayed option-chain fallback.

    This is a snapshot of OI/volume/IV/quotes, not live trade flow and not dealer inventory.
    Greeks are Black-Scholes estimates from the reported IV and underlying snapshot.
    """
    key = f"yfinance_options_{ticker}_{max_expiries}_{limit}"
    cached = _read_cache_any(key)
    if cached and float(cached.get("_cache_age_seconds") or 1e9) <= 90:
        rows = cached.get("data") or []
        return {"status": FeedStatus(provider="yfinance", dataset=f"option_chain_{ticker}", state="LIVE",
                                     fetched_at=cached.get("fetched_at"), age_seconds=cached.get("_cache_age_seconds"),
                                     stale_after_seconds=600, records=len(rows),
                                     note="Delayed/free option-chain fallback; not trade-level options flow.").to_dict(),
                "data": rows}
    if not _network_enabled():
        if cached:
            rows = cached.get("data") or []
            return {"status": FeedStatus(provider="yfinance", dataset=f"option_chain_{ticker}", state="STALE",
                                         fetched_at=cached.get("fetched_at"), age_seconds=cached.get("_cache_age_seconds"),
                                         stale_after_seconds=600, records=len(rows),
                                         note="Offline; using last-good delayed option-chain snapshot.").to_dict(),
                    "data": rows}
        return {"status": FeedStatus(provider="yfinance", dataset=f"option_chain_{ticker}", state="OFFLINE",
                                     fetched_at=_utc_now(), stale_after_seconds=600, records=0,
                                     note="Network disabled and no cached chain exists.").to_dict(), "data": []}
    try:
        import yfinance as yf
        tk = yf.Ticker(ticker)
        expiries = list(tk.options or [])[:max_expiries]
        try:
            spot = _f((tk.fast_info or {}).get("last_price"))
        except Exception:
            spot = None
        if spot is None:
            hist = tk.history(period="5d", interval="1d", auto_adjust=True)
            if hist is not None and not hist.empty:
                spot = _f(hist["Close"].dropna().iloc[-1])
        rows: List[Dict[str, Any]] = []
        for expiry in expiries:
            chain = tk.option_chain(expiry)
            for option_type, frame in (("call", chain.calls), ("put", chain.puts)):
                if frame is None or frame.empty:
                    continue
                for record in frame.to_dict("records"):
                    strike = _f(record.get("strike")); iv = _f(record.get("impliedVolatility")); days = _days_to_expiration(expiry)
                    delta = gamma = None
                    if spot and strike and iv and days:
                        delta, gamma = _bs_delta_gamma(spot, strike, iv, days, option_type)
                    rows.append({
                        "provider": "yfinance", "underlying": ticker,
                        "contract": record.get("contractSymbol"), "option_type": option_type,
                        "strike": strike, "expiration": expiry,
                        "open_interest": _f(record.get("openInterest"), 0.0) or 0.0,
                        "implied_volatility": iv, "delta": delta, "gamma": gamma,
                        "theta": None, "vega": None,
                        "bid": _f(record.get("bid")), "ask": _f(record.get("ask")),
                        "last_price": _f(record.get("lastPrice")), "last_size": None,
                        "volume": _f(record.get("volume"), 0.0) or 0.0,
                        "underlying_price": spot, "timestamp": _iso(record.get("lastTradeDate")),
                        "oi_reporting_note": "OI is prior-cleared/delayed; not intraday opening/closing intent.",
                    })
        if spot and len(rows) > limit:
            rows.sort(key=lambda r: (str(r.get("expiration") or ""), abs((_f(r.get("strike")) or spot) - spot), -(_f(r.get("open_interest"), 0.0) or 0.0)))
            rows = rows[:limit]
        payload = {"fetched_at": _utc_now(), "data": rows}
        if rows:
            _write_cache(key, payload)
        state = "LIVE" if rows else "EMPTY"
        return {"status": FeedStatus(provider="yfinance", dataset=f"option_chain_{ticker}", state=state,
                                     fetched_at=payload["fetched_at"], stale_after_seconds=600, records=len(rows),
                                     note="Delayed/free option-chain OI/volume/IV with estimated Greeks; not live flow.").to_dict(),
                "data": rows}
    except Exception as exc:
        if cached:
            rows = cached.get("data") or []
            return {"status": FeedStatus(provider="yfinance", dataset=f"option_chain_{ticker}", state="STALE",
                                         fetched_at=cached.get("fetched_at"), age_seconds=cached.get("_cache_age_seconds"),
                                         stale_after_seconds=600, records=len(rows),
                                         note=f"Fetch failed; using last-good delayed chain: {type(exc).__name__}").to_dict(),
                    "data": rows}
        return {"status": FeedStatus(provider="yfinance", dataset=f"option_chain_{ticker}", state="ERROR",
                                     fetched_at=_utc_now(), stale_after_seconds=600, records=0,
                                     note=f"Option-chain fallback failed: {type(exc).__name__}: {exc}").to_dict(), "data": []}

def fetch_massive_option_chain(ticker: str, limit: int = 250) -> Dict[str, Any]:
    key = os.getenv("MASSIVE_API_KEY", "").strip()
    if not key:
        return _not_configured("Massive", f"option_chain_{ticker}", "MASSIVE_API_KEY", 90)
    base = os.getenv("MASSIVE_BASE_URL", "https://api.massive.com").rstrip("/")
    url = f"{base}/v3/snapshot/options/{ticker}"
    result = _request_json(provider="Massive", dataset=f"option_chain_{ticker}", cache_key=f"massive_options_{ticker}_{limit}",
                           url=url, params={"limit": min(limit, 250), "apiKey": key}, ttl_seconds=20,
                           stale_after_seconds=90, timeout=10)
    rows = _extract_rows(result.get("payload"))
    out: List[Dict[str, Any]] = []
    for r in rows:
        details = r.get("details") or {}
        greeks = r.get("greeks") or {}
        quote = r.get("last_quote") or {}
        trade = r.get("last_trade") or {}
        day = r.get("day") or {}
        underlying = r.get("underlying_asset") or {}
        contract = str(details.get("ticker") or "")
        out.append({
            "provider": "Massive", "underlying": ticker, "contract": contract,
            "option_type": str(details.get("contract_type") or "").lower(),
            "strike": _f(details.get("strike_price")), "expiration": details.get("expiration_date"),
            "open_interest": _f(r.get("open_interest"), 0.0) or 0.0,
            "implied_volatility": _f(r.get("implied_volatility")),
            "delta": _f(greeks.get("delta")), "gamma": _f(greeks.get("gamma")),
            "theta": _f(greeks.get("theta")), "vega": _f(greeks.get("vega")),
            "bid": _f(quote.get("bid")), "ask": _f(quote.get("ask")),
            "last_price": _f(trade.get("price")), "last_size": _f(trade.get("size")),
            "volume": _f(day.get("volume"), 0.0) or 0.0,
            "underlying_price": _f(underlying.get("price") or r.get("underlying_price")),
            "break_even_price": _f(r.get("break_even_price")),
            "timestamp": _iso(max([_epoch_seconds(x) for x in [quote.get("last_updated"), trade.get("sip_timestamp")] if _epoch_seconds(x) is not None], default=None)),
            "oi_reporting_note": "Open interest may reflect the prior trading day's cleared positions.",
        })
    status = _status_from_result(result, "Massive", f"option_chain_{ticker}", 90, len(out),
                                 "Snapshot Greeks/IV/quotes/trades plus OI; OI is not intraday opening/closing intent.", url)
    return {"status": status, "data": out}


def fetch_unusual_whales_state_bridge(tickers: Sequence[str]) -> Dict[str, Any]:
    """Read normalized live-gex/greek-flow/IV state from a user-run UW stream bridge.

    The official real-time service is Kafka/WebSocket based. A persistent worker should write a
    normalized HTTP snapshot; Streamlit then consumes it without owning a fragile socket lifecycle.
    """
    url = os.getenv("UNUSUAL_WHALES_STREAM_BRIDGE_URL", "").strip()
    if not url:
        return _not_configured("Unusual Whales", "greek_flow_live_gex", "UNUSUAL_WHALES_STREAM_BRIDGE_URL", 30)
    token = os.getenv("UNUSUAL_WHALES_STREAM_BRIDGE_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    result = _request_json(provider="Unusual Whales", dataset="greek_flow_live_gex", cache_key="uw_state_bridge",
                           url=url, params={"tickers": ",".join(tickers)}, headers=headers,
                           ttl_seconds=5, stale_after_seconds=30, timeout=6)
    payload = result.get("payload")
    data = payload.get("data") if isinstance(payload, dict) else payload
    rows = data if isinstance(data, list) else []
    status = _status_from_result(result, "Unusual Whales", "greek_flow_live_gex", 30, len(rows),
                                 "Normalized bridge for live-gex, Greek flow, net flow, IV term and option state.", url)
    return {"status": status, "data": rows}


def _ortex_headers() -> Dict[str, str]:
    key = os.getenv("ORTEX_API_KEY", "").strip()
    header_name = os.getenv("ORTEX_API_KEY_HEADER", "Authorization").strip() or "Authorization"
    prefix = os.getenv("ORTEX_API_KEY_PREFIX", "Bearer").strip()
    value = f"{prefix} {key}".strip() if prefix else key
    return {header_name: value, "Accept": "application/json"}


def fetch_ortex_short_interest(ticker: str) -> Dict[str, Any]:
    key = os.getenv("ORTEX_API_KEY", "").strip()
    if not key:
        return _not_configured("ORTEX", f"short_interest_{ticker}", "ORTEX_API_KEY", 300)
    exchange_map_raw = os.getenv("ORTEX_EXCHANGE_MAP", "")
    try:
        exchange_map = json.loads(exchange_map_raw) if exchange_map_raw else {}
    except Exception:
        exchange_map = {}
    exchange = str(exchange_map.get(ticker) or os.getenv("ORTEX_DEFAULT_EXCHANGE", "US")).strip()
    base = os.getenv("ORTEX_BASE_URL", "https://api.ortex.com").rstrip("/")
    endpoints = {
        "live": f"{base}/api/v1/stock/{exchange}/{ticker}/short_interest_live",
        "ctb": f"{base}/api/v1/stock/{exchange}/{ticker}/ctb/all",
        "dtc": f"{base}/api/v1/stock/{exchange}/{ticker}/dtc",
        "float": f"{base}/api/v1/stock/{exchange}/{ticker}/free_float",
    }
    results = _request_group({name: dict(provider="ORTEX", dataset=f"{name}_{ticker}", cache_key=f"ortex_{name}_{exchange}_{ticker}",
                                   url=url, headers=_ortex_headers(), ttl_seconds=60 if name == "live" else 300,
                                   stale_after_seconds=900, timeout=10)
               for name, url in endpoints.items()})
    def first_payload(res: Dict[str, Any]) -> Dict[str, Any]:
        p = res.get("payload")
        rows = _extract_rows(p)
        if rows: return rows[0]
        if isinstance(p, dict): return p.get("data") if isinstance(p.get("data"), dict) else p
        return {}
    live = first_payload(results["live"]); ctb = first_payload(results["ctb"])
    dtc = first_payload(results["dtc"]); flt = first_payload(results["float"])
    row = {
        "provider": "ORTEX", "ticker": ticker, "timestamp": _iso(live.get("date") or live.get("timestamp")),
        "short_interest_shares": _f(live.get("short_interest") or live.get("shortInterest")),
        "short_interest_pct_float": _f(live.get("short_interest_pct_float") or live.get("shortInterestPercentFreeFloat") or live.get("si_percent_ff")),
        "short_interest_change_pct": _f(live.get("short_interest_change") or live.get("shortInterestChange")),
        "cost_to_borrow": _f(ctb.get("ctb") or ctb.get("cost_to_borrow") or ctb.get("ctb_avg")),
        "cost_to_borrow_min": _f(ctb.get("ctb_min")), "cost_to_borrow_max": _f(ctb.get("ctb_max")),
        "days_to_cover": _f(dtc.get("days_to_cover") or dtc.get("dtc")),
        "free_float_shares": _f(flt.get("free_float") or flt.get("freeFloat")),
        "state": "LIVE" if any(r.get("state") == "LIVE" for r in results.values()) else "STALE" if any(r.get("state") == "STALE" for r in results.values()) else "ERROR",
        "semantics": "Estimated/live short-interest fields depend on the licensed ORTEX dataset; verify field mapping against your account schema.",
    }
    statuses = [_status_from_result(results[k], "ORTEX", f"{k}_{ticker}", 900, 1 if results[k].get("ok") else 0,
                                    "Licensed short-interest / borrow context.", endpoints[k]) for k in endpoints]
    return {"row": row, "statuses": statuses}


def fetch_intrinio_short_interest(ticker: str) -> Dict[str, Any]:
    key = os.getenv("INTRINIO_API_KEY", "").strip()
    if not key:
        return _not_configured("Intrinio", f"official_short_interest_{ticker}", "INTRINIO_API_KEY", 86400)
    base = os.getenv("INTRINIO_BASE_URL", "https://api-v2.intrinio.com").rstrip("/")
    url = f"{base}/securities/{ticker}/short_interest"
    result = _request_json(provider="Intrinio", dataset=f"official_short_interest_{ticker}", cache_key=f"intrinio_si_{ticker}",
                           url=url, params={"api_key": key, "page_size": 3}, ttl_seconds=21600,
                           stale_after_seconds=172800, timeout=10)
    rows = _extract_rows(result.get("payload"))
    row0 = rows[0] if rows else {}
    row = {
        "provider": "Intrinio", "ticker": ticker,
        "timestamp": row0.get("settlement_date") or result.get("fetched_at"),
        "short_interest_shares": _f(row0.get("short_interest")),
        "days_to_cover": _f(row0.get("days_to_cover")),
        "average_daily_volume": _f(row0.get("average_daily_volume")),
        "short_interest_pct_float": None, "cost_to_borrow": None, "free_float_shares": None,
        "state": result.get("state"),
        "semantics": "Official reported short interest is periodic and not a real-time squeeze trigger.",
    }
    status = _status_from_result(result, "Intrinio", f"official_short_interest_{ticker}", 172800, len(rows),
                                 "Official settlement-based short-interest history; reporting lag applies.", url)
    return {"row": row if rows else None, "statuses": [status]}


def fetch_coinglass_asset(asset: str) -> Dict[str, Any]:
    key = os.getenv("COINGLASS_API_KEY", "").strip()
    if not key:
        return _not_configured("CoinGlass", f"liquidation_context_{asset}", "COINGLASS_API_KEY", 90)
    base = os.getenv("COINGLASS_BASE_URL", "https://open-api-v4.coinglass.com").rstrip("/")
    headers = {"CG-API-KEY": key, "Accept": "application/json"}
    endpoints = {
        "oi": (f"{base}/api/futures/open-interest/exchange-list", {"symbol": asset}),
        "funding": (f"{base}/api/futures/funding-rate/exchange-list", {"symbol": asset}),
        "liquidation": (f"{base}/api/futures/liquidation/exchange-list", {"symbol": asset, "range": "1h"}),
        "liquidation_heatmap": (f"{base}/api/futures/liquidation/aggregated-heatmap/model1", {"symbol": asset, "range": "3d"}),
        "liquidation_map": (f"{base}/api/futures/liquidation/aggregated-map", {"symbol": asset, "range": "1d"}),
    }
    results = _request_group({k: dict(provider="CoinGlass", dataset=f"{k}_{asset}", cache_key=f"coinglass_{k}_{asset}",
                                url=u, params=p, headers=headers, ttl_seconds=30, stale_after_seconds=180, timeout=10)
               for k, (u, p) in endpoints.items()})
    payloads = {k: results[k].get("payload") for k in results}
    row = {
        "provider": "CoinGlass", "asset": asset, "timestamp": _utc_now(),
        "open_interest": payloads["oi"], "funding": payloads["funding"], "liquidation": payloads["liquidation"],
        "liquidation_heatmap": payloads["liquidation_heatmap"], "liquidation_map": payloads["liquidation_map"],
        "state": "LIVE" if any(r.get("state") == "LIVE" for r in results.values()) else "STALE" if any(r.get("state") == "STALE" for r in results.values()) else "ERROR",
        "semantics": "Vendor-normalized cross-exchange analytics; confirm units and exchange coverage before comparing assets.",
    }
    statuses = [_status_from_result(results[k], "CoinGlass", f"{k}_{asset}", 180,
                                    _payload_record_count(payloads[k]), "Cross-exchange derivatives analytics.", endpoints[k][0]) for k in endpoints]
    return {"row": row, "statuses": statuses}


def _payload_record(row: Dict[str, Any]) -> Dict[str, Any]:
    payload = row.get("payload") if isinstance(row, dict) else None
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload if isinstance(payload, dict) else (row if isinstance(row, dict) else {})


def _first_number(row: Dict[str, Any], aliases: Sequence[str]) -> Optional[float]:
    for alias in aliases:
        cur: Any = row
        for part in alias.split("."):
            if not isinstance(cur, dict) or part not in cur:
                cur = None
                break
            cur = cur[part]
        value = _f(cur)
        if value is not None:
            return value
    return None


def _first_text(row: Dict[str, Any], aliases: Sequence[str]) -> Optional[str]:
    for alias in aliases:
        cur: Any = row
        for part in alias.split('.'):
            if not isinstance(cur, dict) or part not in cur:
                cur = None
                break
            cur = cur[part]
        if cur not in (None, ''):
            return str(cur)
    return None


def _row_epoch(row: Dict[str, Any]) -> float:
    for alias in ('received_at', 'timestamp', 'time', 'created_at', 'event_time', 'payload.timestamp'):
        cur: Any = row
        for part in alias.split('.'):
            if not isinstance(cur, dict) or part not in cur:
                cur = None
                break
            cur = cur[part]
        ts = _epoch_seconds(cur)
        if ts:
            return ts
    return 0.0


def summarize_uw_live_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize official Unusual Whales stream topics conservatively.

    The bridge may expose several protobuf schema revisions. This parser uses aliases,
    preserves topic provenance and refuses to treat option flow as observed dealer
    inventory. Repeated option-state messages are de-duplicated by contract.
    """
    if not rows:
        return {"state": "NO_DATA", "records": 0, "calibrated_probability": None}

    topics: List[str] = []
    topic_counts: Dict[str, int] = {}
    dir_delta_values: List[float] = []
    total_delta_values: List[float] = []
    dir_vega_values: List[float] = []
    total_vega_values: List[float] = []
    gamma_values: List[float] = []
    vanna_values: List[float] = []
    charm_values: List[float] = []
    call_premium_values: List[float] = []
    put_premium_values: List[float] = []
    net_premium_values: List[float] = []
    risk_reversals: List[float] = []
    expected_moves: List[Dict[str, Any]] = []
    strikes: List[Dict[str, Any]] = []
    latest_contract_states: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    sector_flows: Dict[str, Dict[str, Any]] = {}
    directional_buckets: Dict[int, float] = {}
    latest_atm_iv = latest_implied_move = latest_zero_gamma = None

    for wrapper in rows:
        payload = _payload_record(wrapper)
        topic = str(wrapper.get("topic") or payload.get("topic") or payload.get("type") or "unknown")
        topic_l = topic.lower()
        if topic not in topics:
            topics.append(topic)
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        epoch = _row_epoch(wrapper) or _row_epoch(payload)

        # Official GreekFlow separates directional flow from raw total flow.
        dir_delta = _first_number(payload, (
            "dir_delta_flow", "directional_delta_flow", "dirDeltaFlow",
            "net_delta_flow", "delta_flow", "greeks.dir_delta_flow",
        ))
        total_delta = _first_number(payload, (
            "total_delta_flow", "totalDeltaFlow", "raw_delta_flow",
            "call_delta_flow", "greeks.total_delta_flow",
        ))
        dir_vega = _first_number(payload, (
            "dir_vega_flow", "directional_vega_flow", "dirVegaFlow",
            "net_vega_flow", "vega_flow", "greeks.dir_vega_flow",
        ))
        total_vega = _first_number(payload, (
            "total_vega_flow", "totalVegaFlow", "raw_vega_flow",
            "greeks.total_vega_flow",
        ))
        gamma = _first_number(payload, (
            "net_gex", "total_gex", "gamma_exposure", "gex",
            "gamma_flow", "net_gamma_flow", "greeks.gamma_flow",
        ))
        vanna = _first_number(payload, ("vanna", "vanna_oi", "net_vanna", "greeks.vanna"))
        charm = _first_number(payload, ("charm", "charm_oi", "net_charm", "greeks.charm"))

        if dir_delta is not None:
            dir_delta_values.append(dir_delta)
            if epoch:
                directional_buckets[int(epoch // 300)] = directional_buckets.get(int(epoch // 300), 0.0) + dir_delta
        if total_delta is not None: total_delta_values.append(total_delta)
        if dir_vega is not None: dir_vega_values.append(dir_vega)
        if total_vega is not None: total_vega_values.append(total_vega)
        if gamma is not None: gamma_values.append(gamma)
        if vanna is not None: vanna_values.append(vanna)
        if charm is not None: charm_values.append(charm)

        call_premium = _first_number(payload, (
            "net_call_premium", "call_premium", "callPremium", "call_premium_ask_bid",
            "premium.call", "call_premium_net",
        ))
        put_premium = _first_number(payload, (
            "net_put_premium", "put_premium", "putPremium", "put_premium_ask_bid",
            "premium.put", "put_premium_net",
        ))
        net_premium = _first_number(payload, (
            "net_premium", "premium_diff", "call_put_premium_diff", "netPremium",
        ))
        if call_premium is not None: call_premium_values.append(call_premium)
        if put_premium is not None: put_premium_values.append(put_premium)
        if net_premium is not None: net_premium_values.append(net_premium)

        implied_move = _first_number(payload, (
            "implied_move", "expected_move", "atm_implied_move", "expectedMove",
            "move", "implied_move_value",
        ))
        atm_iv = _first_number(payload, ("atm_iv", "iv", "implied_volatility", "atmIv"))
        days = _first_number(payload, ("days", "dte", "days_to_expiry", "daysToExpiration"))
        expiry = _first_text(payload, ("expiry", "expiration", "expiration_date", "expiry_date"))
        if implied_move is not None:
            latest_implied_move = implied_move
            expected_moves.append({"implied_move": implied_move, "days": days, "expiry": expiry, "topic": topic})
        if atm_iv is not None: latest_atm_iv = atm_iv

        rr = _first_number(payload, (
            "risk_reversal", "risk_reversal_skew", "rr_25d", "skew",
            "put_call_skew", "twenty_five_delta_skew",
        ))
        if rr is None:
            call_iv = _first_number(payload, ("call_iv", "callIv", "call_25d_iv"))
            put_iv = _first_number(payload, ("put_iv", "putIv", "put_25d_iv"))
            if call_iv is not None and put_iv is not None:
                rr = call_iv - put_iv
        if rr is not None: risk_reversals.append(rr)

        strike = _first_number(payload, ("strike", "strike_price", "strikePrice"))
        strike_gex = _first_number(payload, ("gamma_exposure", "gex", "net_gamma", "gamma_oi", "net_gex"))
        if strike is not None and strike_gex is not None:
            strikes.append({
                "strike": strike, "gex": strike_gex,
                "expiry": expiry, "topic": topic,
            })
        zg = _first_number(payload, ("zero_gamma", "zero_gamma_level", "gamma_flip", "zeroGamma"))
        if zg is not None: latest_zero_gamma = zg

        # OptionState is a contract snapshot; retain only the newest state per contract.
        if "option-state" in topic_l or "option_state" in topic_l or "optionstate" in topic_l:
            contract = _first_text(payload, (
                "option_symbol", "contract", "option", "symbol", "optionSymbol",
            )) or f"{expiry}:{strike}:{_first_text(payload, ('option_type','type','put_call'))}"
            if contract:
                current = latest_contract_states.get(contract)
                if current is None or epoch >= current[0]:
                    latest_contract_states[contract] = (epoch, payload)

        # Sector/industry net-flow topics are global rotation evidence, not ticker proof.
        if "net-flow" in topic_l or "net_flow" in topic_l or "sector" in topic_l or "industry" in topic_l:
            key = _first_text(payload, ("key", "sector", "industry", "name", "group"))
            if key:
                entry = sector_flows.setdefault(key, {"key": key, "call_premium": 0.0, "put_premium": 0.0, "net": 0.0, "records": 0})
                c = call_premium or 0.0
                p = put_premium or 0.0
                n = net_premium if net_premium is not None else c - p
                entry["call_premium"] += c
                entry["put_premium"] += p
                entry["net"] += n
                entry["records"] += 1

    option_state_oi = option_state_volume = 0.0
    option_state_contracts = 0
    for _, state in latest_contract_states.values():
        option_state_contracts += 1
        option_state_oi += _first_number(state, ("open_interest", "openInterest", "oi")) or 0.0
        option_state_volume += _first_number(state, ("volume", "option_volume", "day_volume")) or 0.0

    def total(values: Sequence[float]) -> Optional[float]:
        return sum(values) if values else None

    def latest(values: Sequence[float]) -> Optional[float]:
        return values[-1] if values else None

    def direction(value: Optional[float]) -> str:
        if value is None: return "NO_DATA"
        if value > 0: return "POSITIVE"
        if value < 0: return "NEGATIVE"
        return "FLAT"

    dir_delta_total = total(dir_delta_values)
    total_delta_total = total(total_delta_values)
    dir_vega_total = total(dir_vega_values)
    total_vega_total = total(total_vega_values)
    gamma_total = total(gamma_values)
    vanna_total = total(vanna_values)
    charm_total = total(charm_values)
    call_premium_total = total(call_premium_values)
    put_premium_total = total(put_premium_values)
    premium_diff = total(net_premium_values)
    if premium_diff is None and (call_premium_total is not None or put_premium_total is not None):
        premium_diff = (call_premium_total or 0.0) - (put_premium_total or 0.0)

    pos = max((x for x in strikes if x["gex"] >= 0), key=lambda x: x["gex"], default=None)
    neg = min((x for x in strikes if x["gex"] < 0), key=lambda x: x["gex"], default=None)
    bucket_values = list(directional_buckets.values())
    if bucket_values:
        dominant_sign = 1 if sum(bucket_values) > 0 else -1 if sum(bucket_values) < 0 else 0
        same = sum(1 for x in bucket_values if (x > 0 and dominant_sign > 0) or (x < 0 and dominant_sign < 0))
        persistence = same / len(bucket_values) if dominant_sign else 0.0
    else:
        persistence = None

    expected_moves = sorted(expected_moves, key=lambda x: (x.get("days") is None, x.get("days") or 1e9))
    sector_rotation = sorted(sector_flows.values(), key=lambda x: abs(x.get("net") or 0.0), reverse=True)

    volatility_context = "NO_DATA"
    if dir_vega_total is not None:
        volatility_context = "VOLATILITY_DEMAND" if dir_vega_total > 0 else "VOLATILITY_SUPPLY" if dir_vega_total < 0 else "FLAT"
    gamma_context = "NO_DATA"
    if gamma_total is not None:
        gamma_context = "POSITIVE_GAMMA_CONTEXT" if gamma_total > 0 else "NEGATIVE_GAMMA_CONTEXT" if gamma_total < 0 else "FLAT_GAMMA"

    return {
        "state": "LIVE", "records": len(rows), "topics": topics, "topic_counts": topic_counts,
        "directional_delta_flow": dir_delta_total,
        "total_delta_flow": total_delta_total,
        "directional_delta_flow_direction": direction(dir_delta_total),
        "directional_delta_persistence_5m": persistence,
        "directional_delta_buckets": len(bucket_values),
        "directional_vega_flow": dir_vega_total,
        "total_vega_flow": total_vega_total,
        "directional_vega_flow_direction": direction(dir_vega_total),
        "volatility_context": volatility_context,
        "gamma_flow": gamma_total, "gamma_flow_direction": direction(gamma_total),
        "gamma_context": gamma_context,
        "vanna": vanna_total, "charm": charm_total,
        "largest_positive_gex": pos, "largest_negative_gex": neg,
        "zero_gamma_level": latest_zero_gamma,
        "net_call_premium": call_premium_total,
        "net_put_premium": put_premium_total,
        "net_option_premium_difference": premium_diff,
        "risk_reversal_skew": latest(risk_reversals),
        "implied_move": latest_implied_move,
        "expected_moves": expected_moves[:20],
        "atm_iv": latest_atm_iv,
        "option_state_contracts": option_state_contracts,
        "option_state_open_interest": option_state_oi if option_state_contracts else None,
        "option_state_volume": option_state_volume if option_state_contracts else None,
        "sector_rotation": sector_rotation[:50],
        "calibrated_probability": None,
        "interpretation": (
            "Directional delta flow describes current option-side directional pressure; directional vega describes volatility demand/supply. "
            "Both can reflect hedges, spreads, rolls or closing trades. GEX is exposure context, not observed dealer inventory."
        ),
    }


def integrate_option_context(chain: Dict[str, Any], live: Dict[str, Any]) -> Dict[str, Any]:
    """Join chain state and streamed Greek flow into an auditable, non-probabilistic path context."""
    if not isinstance(chain, dict):
        chain = {}
    if not isinstance(live, dict):
        live = {"state": "NO_DATA", "records": 0}

    score = _f(chain.get("context_score"), 50.0) or 50.0
    drivers = list(chain.get("drivers") or [])
    evidence: List[str] = []
    if chain.get("state") == "LIVE":
        evidence.append("option_chain")

    ddf = _f(live.get("directional_delta_flow"))
    persistence = _f(live.get("directional_delta_persistence_5m"))
    if ddf is not None:
        score += 8.0 if ddf > 0 else -8.0 if ddf < 0 else 0.0
        drivers.append(f"streamed directional delta {'positive' if ddf > 0 else 'negative' if ddf < 0 else 'flat'}")
        evidence.append("directional_delta_flow")
        if persistence is not None and live.get("directional_delta_buckets", 0) >= 2:
            score += (4.0 if ddf > 0 else -4.0) * _clip(persistence, 0.0, 1.0)
            drivers.append(f"5m delta-flow persistence {persistence:.0%}")

    premium_diff = _f(live.get("net_option_premium_difference"))
    if premium_diff is not None:
        score += 6.0 if premium_diff > 0 else -6.0 if premium_diff < 0 else 0.0
        drivers.append(f"streamed call-minus-put premium {'positive' if premium_diff > 0 else 'negative' if premium_diff < 0 else 'flat'}")
        evidence.append("net_option_premium")

    rr = _f(live.get("risk_reversal_skew"))
    if rr is not None:
        # Most providers encode positive call-over-put RR; keep contribution small because conventions vary.
        score += _clip(rr * 20.0, -3.0, 3.0)
        drivers.append(f"risk-reversal skew {rr:+.4f}; provider convention must be checked")
        evidence.append("risk_reversal")

    if live.get("gamma_flow") is not None or chain.get("gamma_proxy") is not None:
        evidence.append("gamma_context")
    if live.get("directional_vega_flow") is not None:
        evidence.append("vega_context")
    if live.get("option_state_open_interest") is not None or chain.get("call_oi") is not None:
        evidence.append("open_interest")

    score = _clip(score)
    lean = "UPSIDE_PRESSURE_CONTEXT" if score >= 60 else "DOWNSIDE_PRESSURE_CONTEXT" if score <= 40 else "BALANCED_CONTEXT"

    zones = dict(chain.get("zones") or {})
    streamed_moves = live.get("expected_moves") or []
    if streamed_moves:
        zones["streamed_expected_moves"] = streamed_moves
    for key in ("largest_positive_gex", "largest_negative_gex", "zero_gamma_level"):
        value = live.get(key)
        if value is not None:
            zones[f"stream_{key}"] = value

    horizon_parts: List[str] = []
    if chain.get("nearest_expiry"):
        horizon_parts.append(f"nearest chain expiry {chain['nearest_expiry']}")
    for move in streamed_moves[:3]:
        if move.get("days") is not None:
            horizon_parts.append(f"expected-move horizon {move['days']:g}d")
        elif move.get("expiry"):
            horizon_parts.append(f"expected-move expiry {move['expiry']}")
    if live.get("directional_delta_buckets"):
        horizon_parts.append(f"flow persistence across {live['directional_delta_buckets']} five-minute buckets")

    invalidation: List[str] = [
        "Directional delta/premium flow flips sign and persists across at least two observation buckets.",
        "Price rejects or loses the relevant expected-move/gamma reference zone rather than accepting through it.",
        "Next session open-interest reconciliation contradicts the assumption that observed premium opened new risk.",
    ]
    completeness = round(100 * len(set(evidence)) / 7, 1)
    return {
        "state": "LIVE" if evidence else "NO_DATA",
        "context_score": round(score, 1),
        "directional_context": lean,
        "volatility_context": live.get("volatility_context") or "NO_DATA",
        "gamma_context": live.get("gamma_context") or chain.get("gamma_context") or "NO_DATA",
        "reference_zones": zones,
        "horizon_context": "; ".join(dict.fromkeys(horizon_parts)) if horizon_parts else "No defensible horizon loaded.",
        "evidence": sorted(set(evidence)),
        "evidence_completeness_pct": completeness,
        "drivers": drivers,
        "invalidation": invalidation,
        "target_semantics": "Reference zones and expiry-implied ranges only; no guaranteed price target.",
        "duration_semantics": "Expiry/DTE and observed persistence define the context horizon; they do not predict exact move duration.",
        "calibrated_probability": None,
    }


# ---------------------------------------------------------------------------
# Options analytics
# ---------------------------------------------------------------------------


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _days_to_expiration(expiration: Any) -> Optional[float]:
    if not expiration:
        return None
    try:
        dt = datetime.fromisoformat(str(expiration)[:10]).replace(tzinfo=timezone.utc)
        return max(1.0 / 365.0, (dt - datetime.now(timezone.utc)).total_seconds() / 86400.0)
    except Exception:
        return None


def _bs_vanna_charm(spot: float, strike: float, iv: float, days: float, option_type: str,
                    rate: float = 0.04, dividend: float = 0.0) -> Tuple[Optional[float], Optional[float]]:
    if spot <= 0 or strike <= 0 or iv <= 0 or days <= 0:
        return None, None
    t = days / 365.0
    root = math.sqrt(t)
    d1 = (math.log(spot / strike) + (rate - dividend + 0.5 * iv * iv) * t) / (iv * root)
    d2 = d1 - iv * root
    disc_q = math.exp(-dividend * t)
    vanna = -disc_q * _norm_pdf(d1) * d2 / iv
    common = -disc_q * _norm_pdf(d1) * (2 * (rate - dividend) * t - d2 * iv * root) / (2 * t * iv * root)
    if option_type == "call":
        charm = common - dividend * disc_q * _norm_cdf(d1)
    else:
        charm = common + dividend * disc_q * _norm_cdf(-d1)
    return vanna, charm


def _expiry_sort(value: Any) -> str:
    s = str(value or "9999-12-31")
    return s[:10] if len(s) >= 10 else s


def summarize_option_chain(ticker: str, rows: Sequence[Dict[str, Any]], flow_events: Sequence[Dict[str, Any]] = ()) -> Dict[str, Any]:
    valid = [dict(r) for r in rows if _f(r.get("strike")) is not None]
    if not valid:
        return {"ticker": ticker, "state": "NO_DATA", "contracts": 0, "calibrated_probability": None,
                "note": "No option-chain rows available."}
    spot = _median(_f(r.get("underlying_price")) for r in valid)
    expiries = sorted({str(r.get("expiration") or r.get("expiry_code") or "") for r in valid if r.get("expiration") or r.get("expiry_code")}, key=_expiry_sort)
    nearest = expiries[0] if expiries else None
    near_rows = [r for r in valid if str(r.get("expiration") or r.get("expiry_code") or "") == nearest] if nearest else valid
    call_rows = [r for r in valid if str(r.get("option_type") or "").lower().startswith("c")]
    put_rows = [r for r in valid if str(r.get("option_type") or "").lower().startswith("p")]
    call_oi = sum(_f(r.get("open_interest"), 0.0) or 0.0 for r in call_rows)
    put_oi = sum(_f(r.get("open_interest"), 0.0) or 0.0 for r in put_rows)
    call_vol = sum(_f(r.get("volume"), 0.0) or 0.0 for r in call_rows)
    put_vol = sum(_f(r.get("volume"), 0.0) or 0.0 for r in put_rows)

    strike_call_oi: Dict[float, float] = {}
    strike_put_oi: Dict[float, float] = {}
    gamma_by_strike: Dict[float, float] = {}
    vanna_by_strike: Dict[float, float] = {}
    charm_by_strike: Dict[float, float] = {}
    total_gamma = 0.0
    total_vanna = 0.0
    total_charm = 0.0
    call_minus_put_gamma_proxy = 0.0
    dte_buckets = {
        "0DTE": {"gamma": 0.0, "vanna": 0.0, "charm": 0.0, "vega": 0.0, "open_interest": 0.0, "contracts": 0},
        "1_7DTE": {"gamma": 0.0, "vanna": 0.0, "charm": 0.0, "vega": 0.0, "open_interest": 0.0, "contracts": 0},
        "8_30DTE": {"gamma": 0.0, "vanna": 0.0, "charm": 0.0, "vega": 0.0, "open_interest": 0.0, "contracts": 0},
        "31P_DTE": {"gamma": 0.0, "vanna": 0.0, "charm": 0.0, "vega": 0.0, "open_interest": 0.0, "contracts": 0},
    }
    for r in valid:
        strike = float(r["strike"])
        oi = _f(r.get("open_interest"), 0.0) or 0.0
        typ = str(r.get("option_type") or "").lower()
        sign = 1.0 if typ.startswith("c") else -1.0
        if sign > 0: strike_call_oi[strike] = strike_call_oi.get(strike, 0.0) + oi
        else: strike_put_oi[strike] = strike_put_oi.get(strike, 0.0) + oi
        gamma = _f(r.get("gamma"))
        iv = _f(r.get("implied_volatility") or r.get("mark_iv"))
        if iv is not None and iv > 3:
            iv /= 100.0
        days = _days_to_expiration(r.get("expiration"))
        if days is None and r.get("expiry_code"):
            try:
                dt = datetime.strptime(str(r["expiry_code"]), "%d%b%y").replace(tzinfo=timezone.utc)
                days = max(1 / 365, (dt - datetime.now(timezone.utc)).total_seconds() / 86400)
            except Exception:
                days = None
        vanna = charm = None
        if spot and iv and days:
            vanna, charm = _bs_vanna_charm(spot, strike, iv, days, "call" if sign > 0 else "put")
        multiplier = 100.0 if str(r.get("provider")) in {"Massive", "yfinance"} else 1.0
        # Public OI does not identify who is long or short.  Store unsigned Greek magnitude and
        # keep call-minus-put as a separately named chain-composition proxy.
        gamma_notional = abs((gamma or 0.0) * oi * multiplier * ((spot or 1.0) ** 2) * 0.01)
        vanna_notional = abs((vanna or 0.0) * oi * multiplier * (spot or 1.0))
        charm_notional = abs((charm or 0.0) * oi * multiplier * (spot or 1.0))
        vega_raw = abs((_f(r.get("vega"), 0.0) or 0.0) * oi * multiplier)
        total_gamma += gamma_notional; total_vanna += vanna_notional; total_charm += charm_notional
        call_minus_put_gamma_proxy += sign * gamma_notional
        gamma_by_strike[strike] = gamma_by_strike.get(strike, 0.0) + gamma_notional
        vanna_by_strike[strike] = vanna_by_strike.get(strike, 0.0) + vanna_notional
        charm_by_strike[strike] = charm_by_strike.get(strike, 0.0) + charm_notional
        if days is not None:
            bucket = "0DTE" if days < 1.0 else "1_7DTE" if days <= 7 else "8_30DTE" if days <= 30 else "31P_DTE"
            dte_buckets[bucket]["gamma"] += gamma_notional
            dte_buckets[bucket]["vanna"] += vanna_notional
            dte_buckets[bucket]["charm"] += charm_notional
            dte_buckets[bucket]["vega"] += vega_raw
            dte_buckets[bucket]["open_interest"] += oi
            dte_buckets[bucket]["contracts"] += 1

    call_wall = max(strike_call_oi, key=strike_call_oi.get) if strike_call_oi else None
    put_wall = max(strike_put_oi, key=strike_put_oi.get) if strike_put_oi else None
    gamma_wall_pos = max(gamma_by_strike, key=gamma_by_strike.get) if gamma_by_strike else None
    gamma_wall_neg = None  # signed negative wall is unknowable without position-side inventory

    # Max pain: payout at expiry using OI; descriptive and most meaningful near expiry.
    candidates = sorted(set(strike_call_oi) | set(strike_put_oi))
    max_pain = None
    if candidates:
        payouts = {}
        for settlement in candidates:
            call_payout = sum(max(0.0, settlement - k) * oi for k, oi in strike_call_oi.items())
            put_payout = sum(max(0.0, k - settlement) * oi for k, oi in strike_put_oi.items())
            payouts[settlement] = call_payout + put_payout
        max_pain = min(payouts, key=payouts.get)

    # Nearest-expiry ATM straddle midpoint as expected-move reference.
    atm_call = atm_put = None
    if spot and near_rows:
        calls = [r for r in near_rows if str(r.get("option_type") or "").lower().startswith("c")]
        puts = [r for r in near_rows if str(r.get("option_type") or "").lower().startswith("p")]
        if calls: atm_call = min(calls, key=lambda r: abs(float(r["strike"]) - spot))
        if puts: atm_put = min(puts, key=lambda r: abs(float(r["strike"]) - spot))
    def midpoint(r: Optional[Dict[str, Any]]) -> Optional[float]:
        if not r: return None
        bid, ask, last = _f(r.get("bid")), _f(r.get("ask")), _f(r.get("last_price") or r.get("mark_price"))
        if bid is not None and ask is not None and ask >= bid: return (bid + ask) / 2.0
        return last
    call_mid, put_mid = midpoint(atm_call), midpoint(atm_put)
    expected_move = (call_mid + put_mid) if call_mid is not None and put_mid is not None else None

    # 25-delta skew approximation and ATM term slope.
    near_calls = [r for r in near_rows if _f(r.get("delta")) is not None and _f(r.get("implied_volatility") or r.get("mark_iv")) is not None]
    near_puts = [r for r in near_rows if _f(r.get("delta")) is not None and _f(r.get("implied_volatility") or r.get("mark_iv")) is not None]
    c25 = min([r for r in near_calls if str(r.get("option_type") or "").lower().startswith("c")], key=lambda r: abs((_f(r.get("delta")) or 0) - 0.25), default=None)
    p25 = min([r for r in near_puts if str(r.get("option_type") or "").lower().startswith("p")], key=lambda r: abs(abs(_f(r.get("delta")) or 0) - 0.25), default=None)
    c_iv = _f(c25.get("implied_volatility") or c25.get("mark_iv")) if c25 else None
    p_iv = _f(p25.get("implied_volatility") or p25.get("mark_iv")) if p25 else None
    if c_iv is not None and c_iv > 3: c_iv /= 100
    if p_iv is not None and p_iv > 3: p_iv /= 100
    skew_25d = (p_iv - c_iv) if p_iv is not None and c_iv is not None else None

    atm_iv_by_expiry: Dict[str, float] = {}
    if spot:
        for expiry in expiries:
            erows = [r for r in valid if str(r.get("expiration") or r.get("expiry_code") or "") == expiry]
            atm = sorted(erows, key=lambda r: abs(float(r["strike"]) - spot))[:2]
            iv = _mean((_f(r.get("implied_volatility") or r.get("mark_iv")) for r in atm))
            if iv is not None and iv > 3: iv /= 100
            if iv is not None: atm_iv_by_expiry[expiry] = iv
    term_slope = None
    if len(atm_iv_by_expiry) >= 2:
        vals = list(atm_iv_by_expiry.items())
        term_slope = vals[-1][1] - vals[0][1]

    relevant_flow = [e for e in flow_events if str(e.get("ticker") or "").upper() == ticker.upper()]
    call_premium = sum(_f(e.get("premium"), 0.0) or 0.0 for e in relevant_flow if str(e.get("option_type") or "").lower().startswith("c"))
    put_premium = sum(_f(e.get("premium"), 0.0) or 0.0 for e in relevant_flow if str(e.get("option_type") or "").lower().startswith("p"))
    flow_balance = (call_premium - put_premium) / max(1.0, call_premium + put_premium) if relevant_flow else None

    # Context score is a transparent descriptive index, not a forecast probability.
    score = 50.0
    drivers: List[str] = []
    pcr_oi = put_oi / call_oi if call_oi > 0 else None
    pcr_vol = put_vol / call_vol if call_vol > 0 else None
    if flow_balance is not None:
        score += flow_balance * 18
        drivers.append(f"observed flow balance {flow_balance:+.2f}")
    if pcr_vol is not None:
        score += _clip((1.0 - pcr_vol) * 8, -12, 12)
        drivers.append(f"put/call volume {pcr_vol:.2f}")
    if skew_25d is not None:
        score -= _clip(skew_25d * 100 * 1.5, -10, 10)
        drivers.append(f"25Δ put-call skew {skew_25d*100:+.1f} vol pts")
    score = _clip(score)
    lean = "CALL_HEAVY_CHAIN_CONTEXT" if score >= 60 else "PUT_HEAVY_CHAIN_CONTEXT" if score <= 40 else "BALANCED_CHAIN_CONTEXT"
    gamma_context = "MAGNITUDE_ONLY_DEALER_SIGN_UNKNOWN"

    zones = {
        "spot": spot, "nearest_expiry": nearest, "call_wall": call_wall, "put_wall": put_wall,
        "max_pain": max_pain, "positive_gamma_wall": gamma_wall_pos, "negative_gamma_wall": gamma_wall_neg,
        "expected_move": expected_move,
        "expected_move_upper": spot + expected_move if spot is not None and expected_move is not None else None,
        "expected_move_lower": spot - expected_move if spot is not None and expected_move is not None else None,
    }
    return {
        "ticker": ticker, "state": "LIVE", "contracts": len(valid), "spot": spot,
        "nearest_expiry": nearest, "expiries_loaded": len(expiries),
        "call_oi": call_oi, "put_oi": put_oi, "put_call_oi": pcr_oi,
        "call_volume": call_vol, "put_volume": put_vol, "put_call_volume": pcr_vol,
        "gamma_magnitude": total_gamma, "gamma_proxy": total_gamma, "gamma_context": gamma_context,
        "call_minus_put_gamma_proxy": call_minus_put_gamma_proxy,
        "vanna_magnitude": total_vanna, "vanna_proxy": total_vanna,
        "charm_magnitude": total_charm, "charm_proxy": total_charm,
        "dte_buckets": dte_buckets,
        "dealer_sign_state": "UNKNOWN", "ownership_state": "UNVERIFIED",
        "skew_25d": skew_25d, "atm_iv_term": atm_iv_by_expiry, "term_slope": term_slope,
        "flow_balance": flow_balance, "context_score": round(score, 1), "directional_context": lean,
        "drivers": drivers, "zones": zones,
        "horizon_context": f"Nearest loaded expiry {nearest}; expected-move band is expiry-specific." if nearest else "No expiry horizon loaded.",
        "calibrated_probability": None,
        "semantics": {
            "gamma": "Unsigned gamma magnitude from public chain data. Call-minus-put composition is separate and is not dealer inventory.",
            "vanna": "Sensitivity of delta to implied volatility under Black-Scholes assumptions; sign impact depends on spot and IV path.",
            "charm": "Delta decay through time under Black-Scholes assumptions; it is not a guaranteed dealer hedge flow.",
            "zones": "Walls, max pain and expected move are reference zones, not guaranteed targets or support/resistance.",
            "direction": "Chain-balance context describes calls versus puts/observed flow. It is not beneficial-owner intent or calibrated market direction.",
            "dte": "Greeks are bucketed by DTE; no Greek is assumed dominant from DTE alone.",
        },
    }


# ---------------------------------------------------------------------------
# Squeeze analytics and history
# ---------------------------------------------------------------------------


def _load_recent_history(asset: str, max_age_hours: float = 48.0) -> List[Dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []
    cutoff = time.time() - max_age_hours * 3600
    rows: List[Dict[str, Any]] = []
    try:
        with HISTORY_PATH.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                    ts = _epoch_seconds(row.get("epoch")) or 0
                    if row.get("asset") == asset and ts >= cutoff:
                        rows.append(row)
                except Exception:
                    continue
    except Exception:
        return []
    return rows[-500:]


def _append_history(rows: Sequence[Dict[str, Any]]) -> None:
    if not rows:
        return
    now = time.time()
    try:
        with HISTORY_PATH.open("a", encoding="utf-8") as handle:
            for r in rows:
                handle.write(json.dumps({
                    "epoch": now, "asset": r.get("asset"), "provider": r.get("provider"),
                    "price": r.get("mark_price"), "oi_value": r.get("open_interest_value"),
                    "funding_rate": r.get("funding_rate"), "long_short_ratio": r.get("global_long_short_ratio"),
                    "taker_ratio": r.get("taker_buy_sell_ratio"),
                }, separators=(",", ":")) + "\n")
    except Exception:
        pass
    # Compact if history becomes excessive.
    try:
        if HISTORY_PATH.stat().st_size > 8_000_000:
            lines = HISTORY_PATH.read_text(encoding="utf-8").splitlines()[-20_000:]
            HISTORY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass


def aggregate_crypto_asset(asset: str, rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    usable = [r for r in rows if r.get("asset") == asset and r.get("state") in {"LIVE", "STALE"}]
    if not usable:
        return {"asset": asset, "state": "NO_DATA", "calibrated_probability": None}
    prices = [_f(r.get("mark_price")) for r in usable]
    price = _median(prices)
    oi_values = [_f(r.get("open_interest_value")) for r in usable]
    reported_oi = sum(v for v in oi_values if v is not None) if any(v is not None for v in oi_values) else None
    funding = _mean(_f(r.get("funding_rate")) for r in usable)
    long_short = _median(_f(r.get("global_long_short_ratio")) for r in usable)
    taker = _median(_f(r.get("taker_buy_sell_ratio")) for r in usable)
    history = _load_recent_history(asset)
    old_price = old_oi = None
    if history:
        target_cutoff = time.time() - 15 * 60
        prior = [h for h in history if (_epoch_seconds(h.get("epoch")) or 0) <= target_cutoff]
        ref = prior[-1] if prior else history[0]
        old_price = _f(ref.get("price")); old_oi = _f(ref.get("oi_value"))
    price_change = _pct_change(price, old_price)
    oi_change = _pct_change(reported_oi, old_oi)
    quadrant = "INSUFFICIENT_HISTORY"
    if price_change is not None and oi_change is not None:
        if price_change > 0 and oi_change > 0: quadrant = "LONG_BUILD_OR_NEW_RISK"
        elif price_change > 0 and oi_change < 0: quadrant = "SHORT_COVERING_OR_DELEVERAGING"
        elif price_change < 0 and oi_change > 0: quadrant = "SHORT_BUILD_OR_NEW_RISK"
        elif price_change < 0 and oi_change < 0: quadrant = "LONG_LIQUIDATION_OR_DELEVERAGING"

    # Descriptive squeeze pressures. Inputs are intentionally visible.
    short_pressure = 35.0
    long_pressure = 35.0
    drivers_short: List[str] = []
    drivers_long: List[str] = []
    if funding is not None:
        f_bps = funding * 10_000
        if f_bps < 0:
            short_pressure += min(25, abs(f_bps) * 3); drivers_short.append(f"negative funding {f_bps:+.2f} bps")
        elif f_bps > 0:
            long_pressure += min(25, abs(f_bps) * 3); drivers_long.append(f"positive funding {f_bps:+.2f} bps")
    if long_short is not None:
        if long_short < 0.85:
            short_pressure += min(18, (0.85 - long_short) * 30); drivers_short.append(f"accounts short-heavy ratio {long_short:.2f}")
        elif long_short > 1.2:
            long_pressure += min(18, (long_short - 1.2) * 20); drivers_long.append(f"accounts long-heavy ratio {long_short:.2f}")
    if taker is not None:
        if taker > 1.1:
            short_pressure += min(12, (taker - 1.1) * 20); drivers_short.append(f"taker buy/sell {taker:.2f}")
        elif taker < 0.9:
            long_pressure += min(12, (0.9 - taker) * 20); drivers_long.append(f"taker buy/sell {taker:.2f}")
    if oi_change is not None:
        if abs(oi_change) > 1:
            bump = min(12, abs(oi_change) * 1.5)
            short_pressure += bump / 2; long_pressure += bump / 2
    if quadrant == "SHORT_COVERING_OR_DELEVERAGING":
        short_pressure += 12; drivers_short.append("price↑ / OI↓ covering signature")
    elif quadrant == "LONG_LIQUIDATION_OR_DELEVERAGING":
        long_pressure += 12; drivers_long.append("price↓ / OI↓ liquidation signature")
    elif quadrant == "LONG_BUILD_OR_NEW_RISK":
        long_pressure += 7; drivers_long.append("price↑ / OI↑ long-build risk")
    elif quadrant == "SHORT_BUILD_OR_NEW_RISK":
        short_pressure += 7; drivers_short.append("price↓ / OI↑ short-build risk")

    state = "LIVE" if any(r.get("state") == "LIVE" for r in usable) else "STALE"
    return {
        "asset": asset, "state": state, "venues": [r.get("provider") for r in usable],
        "mark_price": price, "reported_oi_value_sum": reported_oi,
        "funding_rate_mean": funding, "long_short_ratio_median": long_short,
        "taker_buy_sell_ratio_median": taker,
        "price_change_since_reference_pct": price_change,
        "oi_change_since_reference_pct": oi_change,
        "positioning_quadrant": quadrant,
        "short_squeeze_pressure": round(_clip(short_pressure), 1),
        "long_squeeze_pressure": round(_clip(long_pressure), 1),
        "short_squeeze_drivers": drivers_short,
        "long_squeeze_drivers": drivers_long,
        "calibrated_probability": None,
        "horizon_context": "Funding updates intraday; OI pressure requires persistence across multiple snapshots. Liquidation zones need a dedicated heatmap feed.",
        "semantics": "Venue OI units/coverage differ. Reported OI values are summed only where a USD value is available and are not a canonical global total.",
        "raw_venues": usable,
    }


def summarize_us_squeeze(ticker: str, short_row: Optional[Dict[str, Any]], option_summary: Optional[Dict[str, Any]],
                         flow_events: Sequence[Dict[str, Any]], setup: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not short_row and not option_summary:
        return {"ticker": ticker, "state": "NO_DATA", "calibrated_probability": None}
    score_short = 25.0
    score_long = 20.0
    short_drivers: List[str] = []
    long_drivers: List[str] = []
    si = _f((short_row or {}).get("short_interest_pct_float"))
    ctb = _f((short_row or {}).get("cost_to_borrow"))
    dtc = _f((short_row or {}).get("days_to_cover"))
    if si is not None:
        score_short += min(30, max(0, si - 5) * 1.2); short_drivers.append(f"SI/float {si:.1f}%")
    if ctb is not None:
        score_short += min(20, max(0, ctb - 2) * 0.6); short_drivers.append(f"borrow {ctb:.1f}%")
    if dtc is not None:
        score_short += min(15, max(0, dtc - 1) * 2); short_drivers.append(f"days-to-cover {dtc:.1f}")
    opt = option_summary or {}
    if opt.get("gamma_context") == "AMPLIFICATION_PROXY":
        score_short += 8; score_long += 8
        short_drivers.append("negative signed-gamma proxy amplifies moves")
        long_drivers.append("negative signed-gamma proxy amplifies moves")
    flow = [e for e in flow_events if str(e.get("ticker") or "").upper() == ticker.upper()]
    call_ask = sum((_f(e.get("premium"), 0.0) or 0.0) for e in flow if str(e.get("option_type") or "").lower().startswith("c") and (_f(e.get("ask_side_pct"), 0.0) or 0) >= 0.6)
    put_ask = sum((_f(e.get("premium"), 0.0) or 0.0) for e in flow if str(e.get("option_type") or "").lower().startswith("p") and (_f(e.get("ask_side_pct"), 0.0) or 0) >= 0.6)
    if call_ask > 0:
        score_short += min(15, math.log10(max(1, call_ask)) * 1.8); short_drivers.append(f"ask-side call premium {call_ask:,.0f}")
    if put_ask > 0:
        score_long += min(15, math.log10(max(1, put_ask)) * 1.8); long_drivers.append(f"ask-side put premium {put_ask:,.0f}")
    setup_state = str((setup or {}).get("act") or "")
    if any(x in setup_state.upper() for x in ("LONG", "BUY", "ACCUM", "BREAK")):
        score_short += 6; short_drivers.append(f"price state {setup_state}")
    if any(x in setup_state.upper() for x in ("SHORT", "SELL", "DISTRIB", "BREAKDOWN")):
        score_long += 6; long_drivers.append(f"price state {setup_state}")
    state = "LIVE" if (short_row or {}).get("state") == "LIVE" or opt.get("state") == "LIVE" else "PARTIAL"
    return {
        "ticker": ticker, "state": state,
        "short_squeeze_pressure": round(_clip(score_short), 1),
        "long_squeeze_pressure": round(_clip(score_long), 1),
        "short_squeeze_drivers": short_drivers, "long_squeeze_drivers": long_drivers,
        "short_interest": short_row, "options": option_summary,
        "reference_zones": opt.get("zones") if opt else None,
        "horizon_context": opt.get("horizon_context") if opt else "Short-interest data has a reporting lag; monitor intraday price/volume and borrow changes.",
        "calibrated_probability": None,
        "semantics": "Pressure index measures ingredients for forced covering/liquidation; it is not the probability or timing of a squeeze.",
    }


def derive_liquidation_zones(coinglass_row: Optional[Dict[str, Any]], spot: Optional[float]) -> Dict[str, Any]:
    if not coinglass_row:
        return {"state": "NO_DATA", "above": [], "below": []}
    levels: Dict[float, float] = {}
    map_payload = coinglass_row.get("liquidation_map")
    if isinstance(map_payload, dict):
        data = map_payload.get("data")
        if isinstance(data, dict) and isinstance(data.get("data"), dict): data = data["data"]
        if isinstance(data, dict):
            for price_key, entries in data.items():
                price = _f(price_key)
                if price is None or not isinstance(entries, list): continue
                total = 0.0
                for entry in entries:
                    if isinstance(entry, list) and len(entry) > 1:
                        total += _f(entry[1], 0.0) or 0.0
                    elif isinstance(entry, dict):
                        total += _f(entry.get("liquidation_level") or entry.get("value"), 0.0) or 0.0
                levels[price] = levels.get(price, 0.0) + total
    heat = coinglass_row.get("liquidation_heatmap")
    if isinstance(heat, dict):
        data = heat.get("data")
        if isinstance(data, dict):
            y_axis = data.get("y_axis") or []
            matrix = data.get("liquidation_leverage_data") or []
            for entry in matrix:
                if not isinstance(entry, list) or len(entry) < 3: continue
                y_idx = _i(entry[1], -1)
                if 0 <= y_idx < len(y_axis):
                    price = _f(y_axis[y_idx]); value = _f(entry[2], 0.0) or 0.0
                    if price is not None: levels[price] = levels.get(price, 0.0) + value
    ranked = sorted(({"price": p, "intensity": v} for p, v in levels.items()), key=lambda x: x["intensity"], reverse=True)
    if spot is None:
        return {"state": "LIVE" if ranked else "EMPTY", "above": ranked[:5], "below": [], "all_top": ranked[:10],
                "semantics": "Calculated liquidation concentrations are model outputs, not resting executable orders."}
    above = sorted([x for x in ranked if x["price"] > spot], key=lambda x: (-x["intensity"], x["price"]))[:5]
    below = sorted([x for x in ranked if x["price"] < spot], key=lambda x: (-x["intensity"], -x["price"]))[:5]
    return {"state": "LIVE" if ranked else "EMPTY", "spot": spot, "above": above, "below": below, "all_top": ranked[:10],
            "nearest_above": min(above, key=lambda x: x["price"]-spot, default=None),
            "nearest_below": min(below, key=lambda x: spot-x["price"], default=None),
            "semantics": "Modeled liquidation concentrations are potential attraction/acceleration zones, not guaranteed targets."}


# ---------------------------------------------------------------------------
# Collection / orchestration
# ---------------------------------------------------------------------------


def _run_parallel(tasks: Dict[str, Tuple[Any, Tuple[Any, ...]]], max_workers: int = 12) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(func, *args): key for key, (func, args) in tasks.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                out[key] = future.result()
            except Exception as exc:
                out[key] = {"error": f"{type(exc).__name__}: {exc}"}
    return out


def collect_live_market_intelligence(desk: Dict[str, Any], institutional: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    institutional = institutional or desk.get("institutional") or {}
    crypto_assets = _parse_csv_env("WARROOM_CRYPTO_DERIVATIVES", ["BTC", "ETH", "SOL"])
    crypto_assets = crypto_assets[:6]
    option_tickers = _desk_watchlist(desk, limit=_i(os.getenv("WARROOM_OPTIONS_MAX_TICKERS", "5"), 5))
    exchange_symbols = [f"{a}USDT" for a in crypto_assets]

    tasks: Dict[str, Tuple[Any, Tuple[Any, ...]]] = {}
    for symbol in exchange_symbols:
        tasks[f"binance:{symbol}"] = (fetch_binance_symbol, (symbol,))
        tasks[f"bybit:{symbol}"] = (fetch_bybit_symbol, (symbol,))
    for asset in crypto_assets:
        tasks[f"okx:{asset}"] = (fetch_okx_symbol, (asset,))
    for currency in [x for x in crypto_assets if x in {"BTC", "ETH"}]:
        tasks[f"deribit:{currency}"] = (fetch_deribit_currency, (currency,))
    for ticker in option_tickers:
        if os.getenv("MASSIVE_API_KEY", "").strip():
            tasks[f"massive:{ticker}"] = (fetch_massive_option_chain, (ticker,))
        else:
            tasks[f"yfopt:{ticker}"] = (fetch_yfinance_option_chain, (ticker,))
        if os.getenv("ORTEX_API_KEY", "").strip():
            tasks[f"ortex:{ticker}"] = (fetch_ortex_short_interest, (ticker,))
        if os.getenv("INTRINIO_API_KEY", "").strip():
            tasks[f"intrinio:{ticker}"] = (fetch_intrinio_short_interest, (ticker,))
    for asset in crypto_assets:
        if os.getenv("COINGLASS_API_KEY", "").strip():
            tasks[f"coinglass:{asset}"] = (fetch_coinglass_asset, (asset,))

    results = _run_parallel(tasks)
    statuses: List[Dict[str, Any]] = []
    crypto_rows: List[Dict[str, Any]] = []
    option_chains: Dict[str, List[Dict[str, Any]]] = {}
    short_rows: Dict[str, Dict[str, Any]] = {}
    deribit_chains: Dict[str, List[Dict[str, Any]]] = {}
    coinglass: Dict[str, Any] = {}

    for key, result in results.items():
        if result.get("error"):
            provider = key.split(":", 1)[0]
            statuses.append(FeedStatus(provider=provider, dataset=key, state="ERROR", note=result["error"]).to_dict())
            continue
        prefix, name = key.split(":", 1)
        if prefix in {"binance", "bybit", "okx"}:
            if result.get("row"): crypto_rows.append(result["row"])
            statuses.extend(result.get("statuses") or [])
        elif prefix == "deribit":
            deribit_chains[name] = result.get("data") or []
            statuses.append(result.get("status") or {})
        elif prefix in {"massive", "yfopt"}:
            option_chains[name] = result.get("data") or []
            statuses.append(result.get("status") or {})
        elif prefix in {"ortex", "intrinio"}:
            candidate = result.get("row")
            existing = short_rows.get(name)
            # Prefer live ORTEX fields; retain Intrinio as settlement-based fallback.
            if candidate and (not existing or prefix == "ortex" or existing.get("state") not in {"LIVE", "STALE"}):
                short_rows[name] = candidate
            statuses.extend(result.get("statuses") or [])
        elif prefix == "coinglass":
            coinglass[name] = result.get("row")
            statuses.extend(result.get("statuses") or [])

    uw_state = fetch_unusual_whales_state_bridge(option_tickers)
    statuses.append(uw_state["status"])
    flow_events = institutional.get("options_flow") or []
    all_uw_rows = uw_state.get("data") or []
    market_options_context = summarize_uw_live_rows(all_uw_rows)

    option_summaries: List[Dict[str, Any]] = []
    for ticker in option_tickers:
        chain = option_chains.get(ticker) or []
        summary = summarize_option_chain(ticker, chain, flow_events)
        # Merge normalized live state from the bridge without converting flow into dealer-position claims.
        bridge_rows: List[Dict[str, Any]] = []
        for r in all_uw_rows:
            payload = _payload_record(r)
            candidates = {
                str(r.get("ticker") or "").upper(),
                str(payload.get("ticker") or "").upper(),
                str(payload.get("underlying_symbol") or payload.get("underlying") or "").upper(),
                str(payload.get("root") or "").upper(),
            }
            if ticker.upper() in candidates:
                bridge_rows.append(r)
        live_context = summarize_uw_live_rows(bridge_rows)
        summary["unusual_whales_live_state"] = bridge_rows
        summary["live_greek_context"] = live_context
        summary["live_greek_flow_available"] = bool(bridge_rows)
        summary["integrated_context"] = integrate_option_context(summary, live_context)
        # Promote the integrated labels for UI compatibility while preserving the original chain-only fields.
        if summary["integrated_context"].get("state") == "LIVE":
            summary["integrated_directional_context"] = summary["integrated_context"].get("directional_context")
            summary["integrated_context_score"] = summary["integrated_context"].get("context_score")
        option_summaries.append(summary)

    # Crypto option summaries from Deribit are separate venue snapshots.
    crypto_option_summaries: List[Dict[str, Any]] = []
    for currency, chain in deribit_chains.items():
        s = summarize_option_chain(currency, chain, ())
        s["venue"] = "Deribit"
        crypto_option_summaries.append(s)

    crypto_aggregates = [aggregate_crypto_asset(asset, crypto_rows) for asset in crypto_assets]
    _append_history(crypto_rows)
    for row in crypto_aggregates:
        if row.get("asset") in coinglass:
            row["coinglass"] = coinglass[row["asset"]]
            row["liquidation_zones"] = derive_liquidation_zones(coinglass[row["asset"]], _f(row.get("mark_price")))
            row["liquidation_heatmap_available"] = bool(coinglass[row["asset"]])
        else:
            row["liquidation_heatmap_available"] = False

    # Build US squeeze summaries using current desk setup when available.
    setup_map: Dict[str, Dict[str, Any]] = {}
    for market in (desk.get("markets") or {}).values():
        for setup in market.get("setups") or []:
            if setup.get("tk"): setup_map[str(setup["tk"]).upper()] = setup
    opt_map = {str(x.get("ticker") or "").upper(): x for x in option_summaries}
    us_squeeze = [summarize_us_squeeze(t, short_rows.get(t), opt_map.get(t), flow_events, setup_map.get(t)) for t in option_tickers]

    events: List[Dict[str, Any]] = []
    for row in crypto_aggregates:
        events.append({
            "event_type": "DERIVATIVES_STATE", "provider": "Multi-exchange", "ticker": row.get("asset"),
            "timestamp": _utc_now(), "state": row.get("state"),
            "description": f"{row.get('positioning_quadrant')} · short squeeze pressure {row.get('short_squeeze_pressure')} · long squeeze pressure {row.get('long_squeeze_pressure')}",
            "observed": True, "position_inference": "CONTEXT_ONLY", "raw": row,
        })
    for row in option_summaries:
        if row.get("state") != "NO_DATA":
            events.append({
                "event_type": "OPTIONS_STATE", "provider": "Option chain + optional UW bridge", "ticker": row.get("ticker"),
                "timestamp": _utc_now(), "state": (row.get("integrated_context") or {}).get("directional_context") or row.get("directional_context"),
                "description": f"{(row.get('integrated_context') or {}).get('directional_context') or row.get('directional_context')} · {(row.get('integrated_context') or {}).get('gamma_context') or row.get('gamma_context')} · context {(row.get('integrated_context') or {}).get('context_score') or row.get('context_score')}",
                "observed": True, "position_inference": "CONTEXT_ONLY", "raw": row,
            })
    events.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)

    active = sum(1 for s in statuses if s.get("state") == "LIVE")
    stale = sum(1 for s in statuses if s.get("state") == "STALE")
    errors = sum(1 for s in statuses if s.get("state") == "ERROR")
    configured_or_public = sum(1 for s in statuses if s.get("state") not in {"NOT_CONFIGURED"})
    domain_records = {
        "crypto_perps": sum(1 for x in crypto_aggregates if x.get("state") not in {"NO_DATA", "ERROR"}),
        "crypto_options": sum(1 for x in crypto_option_summaries if x.get("state") not in {"NO_DATA", "ERROR"}),
        "us_options": sum(1 for x in option_summaries if x.get("state") not in {"NO_DATA", "ERROR"}),
    }
    live_domains = sum(1 for n in domain_records.values() if n > 0)
    if live_domains >= 2:
        overall = "LIVE"
    elif live_domains == 1:
        overall = "PARTIAL"
    elif stale:
        overall = "STALE"
    elif errors:
        overall = "ERROR"
    else:
        overall = "NO_DATA"

    coverage = {
        "public_crypto_derivatives": {"assets": crypto_assets, "venues": ["Binance", "Bybit", "OKX"], "configured": True},
        "crypto_options": {"assets": [x for x in crypto_assets if x in {"BTC", "ETH"}], "venues": ["Deribit"], "configured": True},
        "us_option_chain": {"tickers": option_tickers, "configured": True,
                            "provider": "Massive" if os.getenv("MASSIVE_API_KEY", "").strip() else "yfinance delayed fallback"},
        "live_greek_flow": {"tickers": option_tickers, "configured": bool(os.getenv("UNUSUAL_WHALES_STREAM_BRIDGE_URL", "").strip())},
        "short_interest_borrow": {"tickers": option_tickers, "configured": bool(os.getenv("ORTEX_API_KEY", "").strip() or os.getenv("INTRINIO_API_KEY", "").strip())},
        "liquidation_heatmap": {"assets": crypto_assets, "configured": bool(os.getenv("COINGLASS_API_KEY", "").strip())},
    }
    return {
        "generated": _utc_now(), "overall_state": overall,
        "status_counts": {"live": active, "stale": stale, "error": errors, "live_domains": live_domains, "domain_records": domain_records, "total_non_optional": configured_or_public, "total": len(statuses)},
        "coverage": coverage, "statuses": statuses,
        "crypto_derivatives_raw": crypto_rows, "crypto_derivatives": crypto_aggregates,
        "crypto_options": crypto_option_summaries,
        "us_options": option_summaries, "us_short_interest": list(short_rows.values()),
        "us_squeeze": us_squeeze, "unusual_whales_live_state": all_uw_rows,
        "market_options_context": market_options_context,
        "options_sector_rotation": market_options_context.get("sector_rotation") or [],
        "events": events[:200],
        "rules": {
            "no_synthetic": True, "missing_is_not_neutral": True,
            "squeeze_score_is_probability": False, "targets_are_reference_zones": True,
            "dealer_inventory_is_observed": False,
        },
    }
