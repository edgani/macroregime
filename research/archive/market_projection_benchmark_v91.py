"""Exact-market wrapper for the V8.8 projection metrics.

V8.8 incorrectly required one file to contain and pass all five markets. V9.1 evaluates one frozen
market scope at a time, then the global gate combines five independent receipts.
"""
from __future__ import annotations
from typing import Any
import pandas as pd

from market_projection_benchmark import validate_frame, _market_metrics, MARKETS


def evaluate_exact_market(frame: pd.DataFrame, market: str) -> dict[str, Any]:
    market = str(market).lower().strip()
    if market not in MARKETS:
        return {"schema": "warroom.v91.projection_benchmark.v1", "valid": False, "market": market, "errors": ["unsupported market"], "market_pass": False}
    validation = validate_frame(frame)
    if not validation.get("valid"):
        return {"schema": "warroom.v91.projection_benchmark.v1", "valid": False, "market": market, "errors": validation.get("errors", []), "market_pass": False}
    work = validation.pop("work")
    represented = set(work["market"].astype(str).str.lower().unique())
    if represented != {market}:
        return {"schema": "warroom.v91.projection_benchmark.v1", "valid": False, "market": market, "errors": [f"projection file must contain exact market only; found {sorted(represented)}"], "market_pass": False}
    metrics = _market_metrics(work, market)
    return {
        "schema": "warroom.v91.projection_benchmark.v1",
        "valid": True,
        "market": market,
        "rows": len(work),
        "metrics": metrics,
        "market_pass": bool(metrics.get("all_projection_gates_pass")),
        "errors": [],
        "claim_limit": "Projection proof is exact-market, exact-universe and exact-horizon only.",
    }
