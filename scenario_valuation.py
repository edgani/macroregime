"""Fail-closed scenario valuation helpers.

A scenario range is not produced from price momentum, structural centrality or a narrative.
It requires explicit economic inputs and records every assumption. Probabilities are optional
and expected value remains withheld unless they are externally calibrated and sum to one.
"""
from __future__ import annotations

from typing import Any


EQUITY_REQUIRED = ("demand", "share", "margin", "multiple", "net_debt", "future_diluted_shares")
TOKEN_REQUIRED = ("economic_activity", "capture_rate", "net_costs", "multiple", "future_diluted_supply")


def _num(value: Any) -> float | None:
    try:
        x = float(value)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def _probabilities_valid(scenarios: dict[str, dict]) -> bool:
    probs = [_num((scenarios.get(k) or {}).get("probability")) for k in ("bear", "base", "bull")]
    return all(x is not None and 0 <= x <= 1 for x in probs) and abs(sum(probs) - 1.0) <= 1e-9


def equity_scenarios(current_diluted_equity_value: Any, scenarios: dict[str, dict]) -> dict:
    current = _num(current_diluted_equity_value)
    missing: dict[str, list[str]] = {}
    rows = {}
    if current is None or current <= 0:
        return {"state": "WITHHELD", "reason": "current diluted equity value missing or invalid", "scenarios": {}}
    for name in ("bear", "base", "bull"):
        raw = scenarios.get(name) or {}
        miss = [k for k in EQUITY_REQUIRED if _num(raw.get(k)) is None]
        if miss:
            missing[name] = miss
            continue
        demand, share, margin, multiple, net_debt, shares = (_num(raw[k]) for k in EQUITY_REQUIRED)
        if shares <= 0 or multiple < 0 or not (0 <= share <= 1):
            missing[name] = ["invalid economic assumption"]
            continue
        enterprise = demand * share * margin * multiple
        equity_value = enterprise - net_debt
        per_share = equity_value / shares
        rows[name] = {
            "enterprise_value": enterprise,
            "equity_value": equity_value,
            "per_share": per_share,
            "headroom_pct": (equity_value / current - 1.0) * 100.0,
            "probability": _num(raw.get("probability")),
            "assumptions": {k: raw.get(k) for k in EQUITY_REQUIRED},
        }
    if missing or len(rows) != 3:
        return {"state": "WITHHELD", "reason": "scenario inputs incomplete", "missing": missing, "scenarios": rows}
    out = {"state": "SCENARIO_RANGE", "scenarios": rows, "probability_status": "UNCALIBRATED", "expected_return_pct": None}
    if _probabilities_valid(scenarios) and all(bool((scenarios.get(k) or {}).get("probability_calibrated")) for k in rows):
        out["probability_status"] = "EXTERNALLY_CALIBRATED"
        out["expected_return_pct"] = sum(rows[k]["headroom_pct"] * float(rows[k]["probability"]) for k in rows)
    return out


def token_scenarios(current_diluted_token_value: Any, scenarios: dict[str, dict]) -> dict:
    current = _num(current_diluted_token_value)
    missing: dict[str, list[str]] = {}
    rows = {}
    if current is None or current <= 0:
        return {"state": "WITHHELD", "reason": "current diluted token value missing or invalid", "scenarios": {}}
    for name in ("bear", "base", "bull"):
        raw = scenarios.get(name) or {}
        miss = [k for k in TOKEN_REQUIRED if _num(raw.get(k)) is None]
        if miss:
            missing[name] = miss
            continue
        activity, capture, net_costs, multiple, supply = (_num(raw[k]) for k in TOKEN_REQUIRED)
        if supply <= 0 or multiple < 0 or not (0 <= capture <= 1):
            missing[name] = ["invalid economic assumption"]
            continue
        captured = activity * capture - net_costs
        token_value = max(0.0, captured * multiple)
        per_token = token_value / supply
        rows[name] = {
            "captured_economic_value": captured,
            "token_value": token_value,
            "per_token": per_token,
            "headroom_pct": (token_value / current - 1.0) * 100.0,
            "probability": _num(raw.get("probability")),
            "assumptions": {k: raw.get(k) for k in TOKEN_REQUIRED},
        }
    if missing or len(rows) != 3:
        return {"state": "WITHHELD", "reason": "scenario inputs incomplete", "missing": missing, "scenarios": rows}
    out = {"state": "SCENARIO_RANGE", "scenarios": rows, "probability_status": "UNCALIBRATED", "expected_return_pct": None}
    if _probabilities_valid(scenarios) and all(bool((scenarios.get(k) or {}).get("probability_calibrated")) for k in rows):
        out["probability_status"] = "EXTERNALLY_CALIBRATED"
        out["expected_return_pct"] = sum(rows[k]["headroom_pct"] * float(rows[k]["probability"]) for k in rows)
    return out


def withheld(kind: str, reason: str = "point-in-time economic inputs not loaded") -> dict:
    return {
        "kind": kind,
        "state": "WITHHELD",
        "reason": reason,
        "bear": None,
        "base": None,
        "bull": None,
        "probability_status": "UNCALIBRATED",
        "expected_return_pct": None,
        "capital_permission": "BLOCKED",
    }
