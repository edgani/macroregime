"""Authoritative US liquidity context with bounded latency and last-good cache.

The engine never converts a failed request into NEUTRAL. It exposes LIVE/PARTIAL/STALE/NO_DATA,
uses independent official endpoints concurrently, and can fall back to already-loaded FRED series.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
import json
import logging
import os
import time
import urllib.request

logger = logging.getLogger(__name__)
HERE = Path(__file__).resolve().parents[1]
CACHE = HERE / ".cache" / "treasury_liquidity.json"
CACHE.parent.mkdir(parents=True, exist_ok=True)
_UA = {"User-Agent": os.getenv("WARROOM_PUBLIC_USER_AGENT", "WarRoomOS/2.4 research contact-required")}
_TIMEOUT = max(2, min(8, int(os.getenv("WARROOM_LIQUIDITY_TIMEOUT", "5"))))
_CACHE_TTL = max(60, int(os.getenv("WARROOM_LIQUIDITY_CACHE_TTL", "900")))
_STALE_AFTER = max(_CACHE_TTL, int(os.getenv("WARROOM_LIQUIDITY_STALE_AFTER", "86400")))

_TGA_URL = ("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/"
            "accounting/dts/operating_cash_balance"
            "?fields=record_date,open_today_bal,account_type"
            "&filter=account_type:eq:Treasury%20General%20Account%20(TGA)%20Opening%20Balance"
            "&sort=-record_date&page[size]=10")
_RRP_LATEST = "https://markets.newyorkfed.org/api/rp/reverserepo/all/latest.json"
_SOFR_URL = "https://markets.newyorkfed.org/api/rates/secured/sofr/last/2.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_cache() -> Optional[dict]:
    if not CACHE.exists():
        return None
    try:
        obj = json.loads(CACHE.read_text(encoding="utf-8"))
        obj["_age_seconds"] = max(0.0, time.time() - CACHE.stat().st_mtime)
        return obj
    except Exception:
        return None


def _write_cache(obj: dict) -> None:
    try:
        tmp = CACHE.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, default=str, separators=(",", ":")), encoding="utf-8")
        tmp.replace(CACHE)
    except Exception:
        pass


def _get_json(url: str) -> Optional[dict]:
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        logger.debug("liquidity fetch failed %s: %s", url[:70], exc)
        return None


def fetch_tga() -> Dict:
    payload = _get_json(_TGA_URL)
    try:
        rows = (payload or {}).get("data", [])
        if not rows:
            return {"ok": False, "source": "US Treasury Fiscal Data"}
        latest = float(rows[0]["open_today_bal"])
        prev = float(rows[1]["open_today_bal"]) if len(rows) > 1 else None
        return {"ok": True, "latest": latest, "prev": prev,
                "change": latest - prev if prev is not None else None,
                "date": rows[0].get("record_date"), "source": "US Treasury Fiscal Data"}
    except Exception:
        return {"ok": False, "source": "US Treasury Fiscal Data"}


def fetch_rrp() -> Dict:
    payload = _get_json(_RRP_LATEST)
    try:
        ops = (payload or {}).get("repo", {}).get("operations", []) or (payload or {}).get("operations", [])
        if not ops:
            return {"ok": False, "source": "New York Fed"}
        op = ops[0]
        amount = op.get("totalAmtAccepted") or op.get("totalAmtSubmitted")
        return {"ok": True, "amount": float(amount), "date": op.get("operationDate"), "source": "New York Fed"}
    except Exception:
        return {"ok": False, "source": "New York Fed"}


def fetch_sofr() -> Dict:
    payload = _get_json(_SOFR_URL)
    try:
        refs = (payload or {}).get("refRates", [])
        if not refs:
            return {"ok": False, "source": "New York Fed"}
        return {"ok": True, "sofr": float(refs[0]["percentRate"]),
                "date": refs[0].get("effectiveDate"), "source": "New York Fed"}
    except Exception:
        return {"ok": False, "source": "New York Fed"}


def _last(fred: Optional[Dict], key: str):
    if not fred or key not in fred:
        return None
    try:
        import pandas as pd
        series = pd.Series(fred[key]).dropna()
        return float(series.iloc[-1]) if len(series) else None
    except Exception:
        return None


def _previous(fred: Optional[Dict], key: str):
    if not fred or key not in fred:
        return None
    try:
        import pandas as pd
        series = pd.Series(fred[key]).dropna()
        return float(series.iloc[-2]) if len(series) > 1 else None
    except Exception:
        return None


def analyze_liquidity(fred: Optional[Dict] = None) -> Dict:
    cached = _read_cache()
    if cached and cached.get("_age_seconds", 1e9) <= _CACHE_TTL:
        cached["state"] = "LIVE"
        cached["cache"] = "fresh"
        return cached

    with ThreadPoolExecutor(max_workers=3) as pool:
        ftga, frrp, fsofr = pool.submit(fetch_tga), pool.submit(fetch_rrp), pool.submit(fetch_sofr)
        tga, rrp, sofr = ftga.result(), frrp.result(), fsofr.result()

    # Official FRED observations already loaded by the macro plane are valid fallbacks.
    if not tga.get("ok"):
        latest, prev = _last(fred, "WTREGEN"), _previous(fred, "WTREGEN")
        if latest is not None:
            tga = {"ok": True, "latest": latest, "prev": prev,
                   "change": latest - prev if prev is not None else None,
                   "date": None, "source": "FRED WTREGEN fallback"}
    if not rrp.get("ok"):
        amount = _last(fred, "RRPONTSYD")
        if amount is not None:
            rrp = {"ok": True, "amount": amount, "date": None, "source": "FRED RRPONTSYD fallback"}
    walcl = _last(fred, "WALCL")

    signals, score = [], 0
    if rrp.get("ok") and rrp.get("amount") is not None:
        signals.append(f"RRP ${rrp['amount']:.0f}B")
    if tga.get("ok") and tga.get("change") is not None:
        change_bn = float(tga["change"]) / 1000.0
        if change_bn > 30:
            score -= 1
            signals.append(f"TGA building +${change_bn:.0f}B (drain)")
        elif change_bn < -30:
            score += 1
            signals.append(f"TGA drawdown ${abs(change_bn):.0f}B (add)")
        else:
            signals.append(f"TGA change ${change_bn:+.0f}B")

    net_liq_bn = None
    if walcl is not None and tga.get("ok") and rrp.get("ok"):
        net_liq_bn = walcl / 1000.0 - float(tga["latest"]) / 1000.0 - float(rrp["amount"])
        signals.append(f"Net liquidity ≈ ${net_liq_bn:,.0f}B")

    count = sum(bool(x.get("ok")) for x in (tga, rrp, sofr)) + int(walcl is not None)
    if count == 0:
        if cached:
            cached["state"] = "STALE"
            cached["cache"] = "last-good"
            return cached
        return {"ok": False, "state": "NO_DATA", "coverage": 0, "tga": tga, "rrp": rrp,
                "sofr": sofr, "net_liquidity_bn": None, "signals": [], "bias": "NO_DATA",
                "note": "All official liquidity sources unavailable; no neutral value substituted.",
                "generated": _now()}

    bias = "RISK_ON" if score > 0 else "RISK_OFF" if score < 0 else "BALANCED"
    state = "LIVE" if count >= 3 else "PARTIAL"
    note = ("Liquidity expanding/supportive" if bias == "RISK_ON" else
            "Liquidity draining/headwind" if bias == "RISK_OFF" else
            "Liquidity balance not decisively directional")
    result = {"ok": True, "state": state, "coverage": count, "tga": tga, "rrp": rrp,
              "sofr": sofr, "walcl": walcl, "net_liquidity_bn": net_liq_bn,
              "signals": signals, "bias": bias, "note": note + ". " + "; ".join(signals),
              "generated": _now(), "stale_after_seconds": _STALE_AFTER}
    _write_cache(result)
    return result
