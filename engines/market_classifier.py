"""engines/market_classifier.py — Source of Truth for Ticker→Market Tab (Sprint 6)

Prevents ticker leakage between tabs (e.g., GLD showing in both Commodities and US Stocks).
Validates tickers against config buckets, flags ambiguous classification.

Used by app.py to determine which tab a ticker belongs in.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


# Authoritative classification rules — checked in order, first match wins
CLASSIFICATION_RULES = [
    # 1. Format-based (unambiguous)
    {"name": "ihsg", "predicate": lambda t: t.endswith(".JK")},
    {"name": "japan", "predicate": lambda t: t.endswith(".T")},
    {"name": "korea", "predicate": lambda t: t.endswith(".KS")},
    {"name": "china", "predicate": lambda t: t.endswith(".SS") or t.endswith(".SZ")},
    {"name": "hk", "predicate": lambda t: t.endswith(".HK")},
    {"name": "uk", "predicate": lambda t: t.endswith(".L")},
    {"name": "europe", "predicate": lambda t: t.endswith(".AS") or t.endswith(".PA") or t.endswith(".DE")},
    {"name": "crypto", "predicate": lambda t: "-USD" in t or t in ("BTC", "ETH", "SOL")},
    {"name": "forex", "predicate": lambda t: "=X" in t or t in ("DX-Y.NYB", "DXY")},
    {"name": "futures", "predicate": lambda t: t.endswith("=F")},
    {"name": "index", "predicate": lambda t: t.startswith("^")},
]

# Tickers explicitly assigned to a market (overrides above rules)
EXPLICIT_OVERRIDES = {
    # ETFs that proxy commodities — assign to commodities tab
    "GLD": "commodity", "SLV": "commodity", "USO": "commodity", "UNG": "commodity",
    "DBA": "commodity", "DBC": "commodity", "DBP": "commodity", "DBB": "commodity",
    "DBO": "commodity", "BNO": "commodity",
    # ETF FX
    "UUP": "forex", "FXE": "forex", "FXY": "forex", "FXB": "forex", "FXA": "forex",
    "FXC": "forex", "EUO": "forex",
    # Bond ETFs go to US Stocks (rate plays)
    "TLT": "us_equity", "IEF": "us_equity", "SHY": "us_equity", "LQD": "us_equity",
    "HYG": "us_equity", "TIP": "us_equity",
    # Bitcoin/Crypto-linked equity
    "MSTR": "us_equity", "COIN": "us_equity", "MARA": "us_equity", "RIOT": "us_equity",
    "IBIT": "us_equity", "FBTC": "us_equity",
}


def classify_ticker(ticker: str) -> str:
    """Return canonical market category for a ticker."""
    if not ticker:
        return "unknown"
    t = ticker.upper()

    # Check explicit overrides first
    if t in EXPLICIT_OVERRIDES:
        return EXPLICIT_OVERRIDES[t]

    # Apply rules in order
    for rule in CLASSIFICATION_RULES:
        if rule["predicate"](t):
            return rule["name"]

    # Default to US equity
    return "us_equity"


# ────────────────────────────────────────────────────────────────────────
# Validation helpers
# ────────────────────────────────────────────────────────────────────────

def validate_universe_buckets(
    us_buckets: Set[str],
    forex_pairs: Set[str],
    commodities: Set[str],
    crypto: Set[str],
    ihsg: Set[str],
) -> Dict:
    """
    Cross-validate config buckets — find tickers that appear in multiple,
    or are misclassified.
    """
    all_buckets = {
        "us_equity": us_buckets,
        "forex": forex_pairs,
        "commodity": commodities,
        "crypto": crypto,
        "ihsg": ihsg,
    }

    issues = []
    cross_listed = []

    # Find tickers appearing in multiple buckets
    all_tickers = set()
    for b in all_buckets.values():
        all_tickers |= set(b)

    for t in all_tickers:
        in_buckets = [name for name, bucket in all_buckets.items() if t in bucket]
        if len(in_buckets) > 1:
            cross_listed.append({"ticker": t, "buckets": in_buckets})

    # Find tickers in wrong bucket based on canonical classification
    for bucket_name, bucket in all_buckets.items():
        for t in bucket:
            canonical = classify_ticker(t)
            if canonical != bucket_name and canonical not in ("us_equity", "unknown"):
                # Only flag if there's a strong canonical contradiction
                if bucket_name == "us_equity" and canonical in ("crypto", "forex"):
                    issues.append({
                        "ticker": t,
                        "in_bucket": bucket_name,
                        "canonical": canonical,
                        "issue": "should_be_in_canonical_bucket",
                    })

    return {
        "total_tickers": len(all_tickers),
        "cross_listed": cross_listed,
        "issues": issues,
        "n_clean": len(all_tickers) - len(cross_listed) - len(issues),
    }


# ────────────────────────────────────────────────────────────────────────
# Filter tickers for a given tab
# ────────────────────────────────────────────────────────────────────────

def filter_for_tab(tickers: list, tab_name: str) -> list:
    """
    Given list of tickers, return only those that belong to specified tab.
    """
    canonical_tab = {
        "🇺🇸 US Stocks": "us_equity",
        "us_stocks": "us_equity",
        "us_equity": "us_equity",
        "💱 Forex": "forex",
        "forex": "forex",
        "🛢️ Commodities": "commodity",
        "commodities": "commodity",
        "commodity": "commodity",
        "₿ Crypto": "crypto",
        "crypto": "crypto",
        "🌍 IHSG": "ihsg",
        "ihsg": "ihsg",
        "🌏 Global": ["japan", "korea", "china", "hk", "uk", "europe"],
        "global": ["japan", "korea", "china", "hk", "uk", "europe"],
    }.get(tab_name, None)

    if canonical_tab is None:
        return tickers

    if isinstance(canonical_tab, list):
        return [t for t in tickers if classify_ticker(t) in canonical_tab]
    return [t for t in tickers if classify_ticker(t) == canonical_tab]
