"""Global five-market promotion gate consuming only V9.6 bound proof-run outputs."""
from __future__ import annotations

import hashlib
import json
from typing import Any

MARKETS = ("us", "idx", "commodity", "fx", "crypto")


def evaluate_all(runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    results: dict[str, Any] = {}; reasons: list[str] = []
    for market in MARKETS:
        run = runs.get(market)
        if not isinstance(run, dict):
            results[market] = {"trading_ready": False, "errors": ["V9.6 proof run missing"]}
            reasons.append(f"{market}: proof run missing")
            continue
        results[market] = run
        if run.get("schema") != "warroom.v96.blind_proof_run.v1":
            reasons.append(f"{market}: wrong proof-run schema")
        if str(run.get("market") or "").lower() != market:
            reasons.append(f"{market}: market mismatch")
        if run.get("trading_ready") is not True or run.get("capital_permission") != "LIMITED_PRODUCTION_ELIGIBLE":
            reasons.append(f"{market}: exact-scope proof failed")
        if run.get("errors"):
            reasons.append(f"{market}: proof run contains errors")
    payload = {
        "schema": "warroom.v96.global_market_adjudication.v1",
        "global_trading_ready": not reasons,
        "capital_permission": "ALL_MARKET_LIMITED_PRODUCTION_ELIGIBLE" if not reasons else "BLOCKED",
        "market_results": results,
        "reasons": sorted(set(reasons)),
    }
    payload["adjudication_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    return payload
