"""Row-level market and instrument capability registry.

Product availability is never inherited across markets and never inferred from generic provider
status text.  Options are enabled only from fresh, usable, instrument-specific evidence rows.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

STATIC_CAPABILITIES: dict[str, dict[str, Any]] = {
    "us": {
        "cash": True, "shorting": True,
        "options_product": "LISTED_EQUITY_ETF_INDEX_OPTIONS", "options_scope": "PER_INSTRUMENT",
        "futures_product": "INDEX_FUTURES_OPTIONAL", "order_book_scope": "VENUE_OR_CONSOLIDATED_L2_IF_LICENSED",
    },
    "idx": {
        "cash": True, "shorting": False,
        "options_product": "NONE", "options_scope": "DISABLED",
        "futures_product": "SINGLE_STOCK_FUTURES_IF_ACTIVE_AND_FED", "order_book_scope": "IDX_DEPTH_IF_LICENSED",
    },
    "crypto": {
        "cash": True, "shorting": True,
        "options_product": "VENUE_LISTED_CRYPTO_OPTIONS", "options_scope": "PER_UNDERLYING_PER_VENUE",
        "futures_product": "PERPETUALS_AND_DATED_FUTURES_PER_VENUE", "order_book_scope": "PER_VENUE_ONLY",
    },
    "commodity": {
        "cash": False, "shorting": True,
        "options_product": "OPTIONS_ON_FUTURES", "options_scope": "PER_EXACT_FUTURES_CONTRACT_IF_FED",
        "futures_product": "LISTED_FUTURES", "order_book_scope": "NATIVE_FUTURES_BOOK_IF_LICENSED",
    },
    "fx": {
        "cash": True, "shorting": True,
        "options_product": "LISTED_FX_OPTIONS_OR_OTC_VOL_SURFACE", "options_scope": "PER_PAIR_PRODUCT_VENUE_TENOR",
        "futures_product": "LISTED_FX_FUTURES_OPTIONAL", "order_book_scope": "VENUE_SPECIFIC_NO_GLOBAL_CONSOLIDATED_BOOK",
    },
}

_BAD_STATES = {"", "NO_DATA", "STALE", "ERROR", "OFFLINE", "NOT_CONFIGURED", "NOT_ENTITLED", "ACTION_REQUIRED", "INITIALIZING", "EMPTY"}


def _rows(value: Any) -> list[dict]:
    return [dict(x) for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _num(value: Any) -> float | None:
    try:
        x = float(value)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _fresh(row: dict, max_age_seconds: float = 86400.0) -> bool:
    evidence = row.get("capability_evidence") if isinstance(row.get("capability_evidence"), dict) else {}
    stamp = (evidence.get("observed_at") or row.get("observed_at") or row.get("timestamp") or row.get("generated")
             or row.get("fetched_at") or row.get("as_of") or row.get("updated_at"))
    dt = _parse_time(stamp)
    if dt is None:
        return False
    age = (datetime.now(timezone.utc) - dt).total_seconds()
    return -300 <= age <= max_age_seconds


def _state(rows: list[dict]) -> str:
    if any(str(r.get("state") or "").upper() == "LIVE" for r in rows):
        return "LIVE"
    if any(str(r.get("state") or "").upper() == "STALE" for r in rows):
        return "STALE"
    return "NO_DATA"


def _summary_evidence(row: dict) -> dict:
    ev = row.get("capability_evidence") if isinstance(row.get("capability_evidence"), dict) else {}
    return ev


def _validate_us(row: dict) -> tuple[bool, str, str | None]:
    ticker = str(row.get("ticker") or "").upper().strip()
    ev = _summary_evidence(row)
    if str(row.get("state") or "").upper() in _BAD_STATES:
        return False, "state not usable", None
    if not ticker:
        return False, "underlying missing", None
    if ev.get("row_level_validated") is not True or int(ev.get("exact_contracts") or 0) <= 0:
        return False, "exact contract evidence missing", ticker
    if int(ev.get("quote_rows") or 0) <= 0:
        return False, "usable non-crossed quote evidence missing", ticker
    if not ev.get("providers"):
        return False, "provider evidence missing", ticker
    if not _fresh(row):
        return False, "option evidence stale or untimestamped", ticker
    return True, "", ticker


def _validate_crypto(row: dict) -> tuple[bool, str, str | None]:
    asset = str(row.get("underlying") or row.get("asset") or row.get("currency") or row.get("ticker") or "").upper()
    asset = asset.replace("-USD", "").replace("_USD", "")
    ev = _summary_evidence(row)
    venue = str(row.get("venue") or ev.get("venue") or "").strip()
    if str(row.get("state") or "").upper() in _BAD_STATES:
        return False, "state not usable", None
    if not asset:
        return False, "underlying missing", None
    if not venue:
        return False, "venue missing", asset
    if ev.get("row_level_validated") is not True or int(ev.get("exact_contracts") or 0) <= 0:
        return False, "exact venue contract evidence missing", asset
    if int(ev.get("quote_rows") or 0) <= 0:
        return False, "usable non-crossed quote evidence missing", asset
    if not _fresh(row):
        return False, "option evidence stale or untimestamped", asset
    return True, "", f"{asset}@{venue}"


def _validate_commodity(row: dict) -> tuple[bool, str, str | None]:
    contract = str(row.get("futures_contract") or row.get("underlying_contract") or "").upper().strip()
    if str(row.get("state") or "").upper() in _BAD_STATES:
        return False, "state not usable", None
    if not contract or not any(ch.isdigit() for ch in contract):
        return False, "exact futures contract missing", None
    if not row.get("venue") or not row.get("expiration") or _num(row.get("strike")) is None:
        return False, "venue/expiry/strike missing", contract
    if str(row.get("option_type") or "").lower()[:1] not in {"c", "p"}:
        return False, "option type missing", contract
    bid, ask = _num(row.get("bid")), _num(row.get("ask"))
    if bid is None or ask is None or bid < 0 or ask < bid:
        return False, "usable non-crossed quote missing", contract
    if not _fresh(row):
        return False, "option evidence stale or untimestamped", contract
    return True, "", contract


def _validate_fx(row: dict) -> tuple[bool, str, str | None]:
    pair = str(row.get("pair") or row.get("underlying") or "").upper().replace("/", "").strip()
    product = str(row.get("product_type") or "").upper()
    if str(row.get("state") or "").upper() in _BAD_STATES:
        return False, "state not usable", None
    if len(pair) != 6:
        return False, "FX pair missing", None
    if product not in {"LISTED_OPTION", "VOL_SURFACE"}:
        return False, "spot/futures row cannot enable FX options", pair
    if not row.get("provider") or not row.get("tenor"):
        return False, "provider/tenor missing", pair
    if product == "LISTED_OPTION":
        if not row.get("venue") or not row.get("expiration") or _num(row.get("strike")) is None:
            return False, "listed option contract fields missing", pair
        bid, ask = _num(row.get("bid")), _num(row.get("ask"))
        if bid is None or ask is None or bid < 0 or ask < bid:
            return False, "usable non-crossed quote missing", pair
    else:
        if _num(row.get("implied_volatility")) is None or not (row.get("delta") or row.get("surface_point")):
            return False, "vol-surface point missing", pair
    if not _fresh(row):
        return False, "option evidence stale or untimestamped", pair
    return True, "", f"{pair}:{product}:{row.get('tenor')}"


def _evaluate(rows: list[dict], validator) -> tuple[list[dict], list[dict], list[str]]:
    accepted: list[dict] = []; rejected: list[dict] = []; instruments: list[str] = []
    for row in rows:
        ok, reason, instrument = validator(row)
        if ok:
            accepted.append(row)
            if instrument:
                instruments.append(instrument)
        else:
            rejected.append({"instrument": instrument, "reason": reason})
    return accepted, rejected, sorted(set(instruments))


def derive_market_capabilities(desk: dict) -> dict[str, dict[str, Any]]:
    live = desk.get("live_intelligence") if isinstance(desk.get("live_intelligence"), dict) else {}
    full = desk.get("full_live_data") if isinstance(desk.get("full_live_data"), dict) else {}
    out = deepcopy(STATIC_CAPABILITIES)

    us_ok, us_bad, us_inst = _evaluate(_rows(live.get("us_options")), _validate_us)
    cr_ok, cr_bad, cr_inst = _evaluate(_rows(live.get("crypto_options")), _validate_crypto)
    co_rows = _rows(live.get("commodity_options")) + _rows(full.get("commodity_options"))
    fx_rows = (_rows(live.get("fx_options")) + _rows(full.get("fx_options"))
               + _rows(live.get("fx_vol_surfaces")) + _rows(full.get("fx_vol_surfaces")))
    co_ok, co_bad, co_inst = _evaluate(co_rows, _validate_commodity)
    fx_ok, fx_bad, fx_inst = _evaluate(fx_rows, _validate_fx)

    for market, accepted, rejected, instruments, dealer_state in (
        ("us", us_ok, us_bad, us_inst, "UNKNOWN_UNLESS_EXPLICIT_SIGNED_INVENTORY"),
        ("crypto", cr_ok, cr_bad, cr_inst, "VENUE_POSITIONING_UNKNOWN_UNLESS_EXPLICIT"),
        ("commodity", co_ok, co_bad, co_inst, "UNKNOWN_UNLESS_EXPLICIT_SIGNED_INVENTORY"),
        ("fx", fx_ok, fx_bad, fx_inst, "WITHHELD_WITHOUT_POSITION_OWNERSHIP"),
    ):
        out[market].update({
            "options_data_state": _state(accepted),
            "options_enabled": bool(accepted),
            "option_instruments": instruments,
            "accepted_option_rows": len(accepted),
            "rejected_option_rows": len(rejected),
            "option_rejections": rejected[:50],
            "capability_evidence_level": "ROW_LEVEL_INSTRUMENT_SPECIFIC",
            "dealer_sign_state": dealer_state,
        })

    out["idx"].update({
        "options_data_state": "NOT_APPLICABLE", "options_enabled": False,
        "option_instruments": [], "accepted_option_rows": 0, "rejected_option_rows": 0,
        "capability_evidence_level": "PRODUCT_DISABLED", "dealer_sign_state": "NOT_APPLICABLE",
    })
    return out


def attach_market_capabilities(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    desk["market_capabilities"] = derive_market_capabilities(desk)
    for market_id, market in (desk.get("markets") or {}).items():
        if isinstance(market, dict):
            market["capabilities"] = deepcopy(desk["market_capabilities"].get(market_id, {}))
    return desk
