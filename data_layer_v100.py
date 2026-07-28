"""Integrated V10.0 data plane: bundled research plus persistent current context."""
from __future__ import annotations

import os
from typing import Any

import data_layer as legacy
import current_context_v100 as current

MARKETS = ("us", "idx", "crypto", "commodity", "fx")
FRED_SERIES = legacy.FRED_SERIES


def load_all(
    markets: list[str] | tuple[str, ...] | None = None,
    start: str | None = None,
    allow_live: bool = True,
    fetch_live_feeds: bool = False,
    allow_synthetic: bool = False,
    fast_core: bool = True,
    skip_slow_context: bool = False,
    bootstrap_core: bool = False,
) -> dict[str, Any]:
    del start, fetch_live_feeds, fast_core, skip_slow_context, bootstrap_core
    if allow_synthetic:
        raise ValueError("Synthetic evidence is forbidden in V10.0")
    selected = [m for m in (markets or MARKETS) if m in MARKETS]
    refresh = allow_live and os.getenv("WARROOM_REFRESH_ON_LOAD", "0").lower() in {"1", "true", "yes"}
    if refresh:
        try:
            current.collect_all(fast=os.getenv("WARROOM_FAST_START", "1").lower() not in {"0", "false", "no"})
        except Exception:
            # Individual collectors retain last-known data; a startup failure must not erase bundled context.
            pass
    base = legacy.load_all(markets=selected, allow_live=False, allow_synthetic=False)
    now_context = current.load_all()
    current_quotes = now_context.get("quotes") or {}
    if int(current_quotes.get("quote_count") or 0) > 0:
        base["quotes"] = current_quotes
    base["current_context"] = now_context
    base["sources"] = dict(base.get("sources") or {})
    base["sources"]["v100_current"] = {
        "quotes": int((now_context.get("quotes") or {}).get("quote_count") or 0),
        "fresh_quotes": int((now_context.get("quotes") or {}).get("fresh_quote_count") or 0),
        "macro": int((now_context.get("macro") or {}).get("series_count") or 0),
        "fundamentals": int((now_context.get("fundamentals") or {}).get("record_count") or 0),
        "crypto_network": int((now_context.get("crypto_network") or {}).get("record_count") or 0),
        "positioning_datasets": len((now_context.get("positioning") or {}).get("datasets") or {}),
    }
    base["overall_source"] = "BUNDLED_RESEARCH_PLUS_PERSISTENT_CURRENT_CONTEXT"
    base["policy"] = {
        **dict(base.get("policy") or {}),
        "research_action": "AVAILABLE_WHEN_MINIMUM_CURRENT_CONTEXT_EXISTS",
        "shadow_permission": "SEPARATE_FROM_SYSTEMATIC_LIVE_PROOF",
        "systematic_live_permission": "EXACT_PROOF_REQUIRED",
    }
    return base
