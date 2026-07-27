"""Attach V8.8 all-market bottleneck-to-price projection status."""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name: str) -> dict:
    try:
        value = json.loads((HERE / name).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def attach_research_evidence_v88(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    audit = _load("V88_CURRENT_ALL_MARKET_AUDIT.json")
    protocol = _load("V88_ALL_MARKET_PROJECTION_PROTOCOL_FROZEN.json")
    desk["v88_all_market_projection"] = {
        "version": "8.8",
        "state": audit.get("state", "BLOCKED_ALL_MARKETS_AWAITING_POINT_IN_TIME_PROJECTION_PROOF"),
        "capital_permission": "BLOCKED",
        "all_market_trading_ready": False,
        "claim": "Every market uses its own bottleneck/value bridge and must independently prove target calibration, realized profit factor and drawdown before capital.",
        "current_result": audit,
        "protocol": protocol,
        "price_projection_engine": "IMPLEMENTED_RESEARCH_ONLY",
        "technical_predictors": 0,
    }
    return desk
