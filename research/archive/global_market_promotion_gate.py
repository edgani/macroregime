"""V8.8 all-market completion gate.

The War Room may be called globally trading-ready only when all five independently proven market
receipts pass.  One market's proof cannot authorize another market.
"""
from __future__ import annotations
from typing import Any
import hashlib
import json

from promotion_gate_v88 import evaluate

MARKETS = ("us", "idx", "commodity", "fx", "crypto")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def evaluate_all(receipts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    reasons: list[str] = []
    for market in MARKETS:
        receipt = receipts.get(market)
        if not isinstance(receipt, dict):
            results[market] = {"eligible": False, "permission": "BLOCKED", "reasons": ["receipt missing"]}
            reasons.append(f"{market}: receipt missing")
            continue
        result = evaluate(receipt)
        results[market] = result
        if str((receipt.get("scope") or {}).get("market") or "").lower() != market:
            reasons.append(f"{market}: scope market mismatch")
        if not result.get("eligible"):
            reasons.append(f"{market}: exact-scope proof failed")
    payload = {
        "schema": "warroom.v88.global_market_adjudication.v1",
        "global_trading_ready": not reasons,
        "capital_permission": "ALL_MARKET_LIMITED_PRODUCTION_ELIGIBLE" if not reasons else "BLOCKED",
        "market_results": results,
        "reasons": reasons,
    }
    payload["adjudication_hash"] = hashlib.sha256(_canonical(payload)).hexdigest()
    return payload
