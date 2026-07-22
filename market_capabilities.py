"""Market and instrument capability registry for War Room OS.

Capabilities are product/data facts, not alpha.  A module is visible only where the
instrument actually has the relevant product and the current provider returned usable data.
No market inherits options/Greeks merely because another market has them.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


STATIC_CAPABILITIES: dict[str, dict[str, Any]] = {
    "us": {
        "cash": True,
        "shorting": True,
        "options_product": "LISTED_EQUITY_ETF_INDEX_OPTIONS",
        "options_scope": "PER_INSTRUMENT",
        "futures_product": "INDEX_FUTURES_OPTIONAL",
        "order_book_scope": "VENUE_OR_CONSOLIDATED_L2_IF_LICENSED",
    },
    "idx": {
        "cash": True,
        "shorting": False,
        "options_product": "NONE",
        "options_scope": "DISABLED",
        "futures_product": "SINGLE_STOCK_FUTURES_IF_ACTIVE_AND_FED",
        "order_book_scope": "IDX_DEPTH_IF_LICENSED",
    },
    "crypto": {
        "cash": True,
        "shorting": True,
        "options_product": "VENUE_LISTED_CRYPTO_OPTIONS",
        "options_scope": "PER_UNDERLYING_PER_VENUE",
        "futures_product": "PERPETUALS_AND_DATED_FUTURES_PER_VENUE",
        "order_book_scope": "PER_VENUE_ONLY",
    },
    "commodity": {
        "cash": False,
        "shorting": True,
        "options_product": "OPTIONS_ON_FUTURES",
        "options_scope": "PER_CONTRACT_IF_FED",
        "futures_product": "LISTED_FUTURES",
        "order_book_scope": "NATIVE_FUTURES_BOOK_IF_LICENSED",
    },
    "fx": {
        "cash": True,
        "shorting": True,
        "options_product": "LISTED_FX_OPTIONS_OR_OTC_VOL_SURFACE",
        "options_scope": "OPTIONAL_DATASET_NOT_INFERRED_FROM_SPOT",
        "futures_product": "LISTED_FX_FUTURES_OPTIONAL",
        "order_book_scope": "VENUE_SPECIFIC_NO_GLOBAL_CONSOLIDATED_BOOK",
    },
}

_BAD = {"", "NO_DATA", "ERROR", "OFFLINE", "NOT_CONFIGURED", "NOT_ENTITLED", "ACTION_REQUIRED", "INITIALIZING"}


def _rows(value: Any) -> list[dict]:
    return [x for x in value if isinstance(x, dict)] if isinstance(value, list) else []


def _state_from_rows(rows: list[dict]) -> str:
    states = {str(x.get("state") or "").upper() for x in rows}
    if "LIVE" in states:
        return "LIVE"
    if "STALE" in states:
        return "STALE"
    if rows:
        return "PARTIAL"
    return "NO_DATA"


def _crypto_option_asset(row: dict) -> str | None:
    value = row.get("ticker") or row.get("asset") or row.get("currency") or row.get("underlying")
    if not value:
        return None
    return str(value).upper().replace("-USD", "").replace("_USD", "")


def derive_market_capabilities(desk: dict) -> dict[str, dict[str, Any]]:
    live = desk.get("live_intelligence") if isinstance(desk.get("live_intelligence"), dict) else {}
    full = desk.get("full_live_data") if isinstance(desk.get("full_live_data"), dict) else {}
    statuses = _rows(live.get("statuses")) + _rows(full.get("statuses"))

    out = deepcopy(STATIC_CAPABILITIES)

    us_rows = _rows(live.get("us_options"))
    us_usable = [x for x in us_rows if str(x.get("state") or "").upper() not in _BAD]
    out["us"].update({
        "options_data_state": _state_from_rows(us_usable),
        "options_enabled": bool(us_usable),
        "option_instruments": sorted({str(x.get("ticker") or "").upper() for x in us_usable if x.get("ticker")}),
        "dealer_sign_state": "UNKNOWN_UNLESS_EXPLICIT_SIGNED_INVENTORY",
    })

    crypto_rows = _rows(live.get("crypto_options"))
    crypto_usable = [x for x in crypto_rows if str(x.get("state") or "").upper() not in _BAD]
    out["crypto"].update({
        "options_data_state": _state_from_rows(crypto_usable),
        "options_enabled": bool(crypto_usable),
        "option_instruments": sorted({a for a in (_crypto_option_asset(x) for x in crypto_usable) if a}),
        "dealer_sign_state": "VENUE_POSITIONING_UNKNOWN_UNLESS_EXPLICIT",
    })

    # Futures/COT rows do not prove that an option surface is loaded.  Require an option-specific
    # provider/dataset marker before enabling commodity or FX option analytics.
    commodity_option_status = [x for x in statuses if "OPTION" in f"{x.get('provider','')} {x.get('dataset','')}".upper()
                               and any(k in f"{x.get('dataset','')} {x.get('note','')}".upper()
                                       for k in ("FUTURE", "COMMOD", "CRUDE", "GOLD", "SILVER", "OIL"))]
    commodity_usable = [x for x in commodity_option_status if str(x.get("state") or "").upper() not in _BAD]
    out["commodity"].update({
        "options_data_state": _state_from_rows(commodity_usable),
        "options_enabled": bool(commodity_usable),
        "option_instruments": [],
        "dealer_sign_state": "UNKNOWN_UNLESS_EXPLICIT_SIGNED_INVENTORY",
    })

    fx_option_status = [x for x in statuses if any(k in f"{x.get('provider','')} {x.get('dataset','')} {x.get('note','')}".upper()
                                                     for k in ("FX OPTION", "OPTIONS_VOL", "VOL SURFACE", "RISK REVERSAL"))]
    fx_usable = [x for x in fx_option_status if str(x.get("state") or "").upper() not in _BAD]
    out["fx"].update({
        "options_data_state": _state_from_rows(fx_usable),
        "options_enabled": bool(fx_usable),
        "option_instruments": [],
        "dealer_sign_state": "WITHHELD_WITHOUT_POSITION_OWNERSHIP",
    })

    out["idx"].update({
        "options_data_state": "NOT_APPLICABLE",
        "options_enabled": False,
        "option_instruments": [],
        "dealer_sign_state": "NOT_APPLICABLE",
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
