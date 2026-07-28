"""Regime-model tournament contract.

The adaptive Wasserstein HMM is a challenger, never the default merely because a paper reports
a high Sharpe.  Every challenger must face identical data, costs, lag, constraints, repeated WFA
and a one-time untouched lockbox before it can influence capital.
"""
from __future__ import annotations

from typing import Any


MODELS = [
    {"id": "equal_weight", "role": "BASELINE", "complexity": "MINIMAL"},
    {"id": "static_risk_balanced", "role": "BASELINE", "complexity": "LOW"},
    {"id": "simple_trend_defensive", "role": "BASELINE", "complexity": "LOW"},
    {"id": "simple_hmm_2_state", "role": "CHALLENGER", "complexity": "MEDIUM"},
    {"id": "simple_hmm_3_state", "role": "CHALLENGER", "complexity": "MEDIUM"},
    {"id": "wasserstein_adaptive_hmm", "role": "CHALLENGER", "complexity": "HIGH"},
]


def build_regime_tournament(_: dict | None = None) -> dict[str, Any]:
    rows = []
    for model in MODELS:
        rows.append({
            **model,
            "state": "NOT_TESTED_IN_CURRENT_EXACT_SCOPE",
            "wfa": "MISSING",
            "lockbox": "MISSING",
            "prospective": "MISSING",
            "cost_model": "REQUIRED",
            "selection_permission": "BLOCKED",
        })
    return {
        "state": "RESEARCH_ONLY",
        "winner": None,
        "selection_rule": "Choose only on repeated net-of-cost OOS evidence with frozen policy; simplicity wins ties.",
        "models": rows,
        "required_common_contract": [
            "identical point-in-time universe",
            "identical release vintages and execution lag",
            "identical costs and constraints",
            "repeated purged/embargoed walk-forward folds",
            "registered experiment budget and multiple-testing correction",
            "one-time untouched lockbox",
            "mature prospective outcomes",
        ],
    }


def attach_regime_tournament(desk: dict) -> dict:
    if isinstance(desk, dict):
        desk["regime_tournament"] = build_regime_tournament(desk)
    return desk
