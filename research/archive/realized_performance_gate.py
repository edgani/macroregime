"""Realized fills, profit factor, drawdown, stress and capacity gates for V8.5."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

TRADE_REQUIRED = [
    "trade_id", "strategy_id", "market", "security_id", "direction", "entry_fill_at",
    "exit_fill_at", "quantity", "entry_price", "exit_price", "commission", "fees",
    "spread_cost", "slippage_cost", "impact_cost", "borrow_cost", "financing_cost",
    "taxes", "regime", "adv_notional", "borrow_available", "source_snapshot_hash",
]
EQUITY_REQUIRED = ["timestamp", "net_liquidation_value", "stress_net_liquidation_value"]


def _timestamps(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce")


def _max_drawdown(values: pd.Series) -> float:
    s = pd.to_numeric(values, errors="coerce").dropna()
    if s.empty or (s <= 0).any():
        return math.inf
    peak = s.cummax()
    return float((1.0 - s / peak).max())


def _cluster_bootstrap_pf(frame: pd.DataFrame, *, repetitions: int = 10000, seed: int = 8501) -> dict[str, float]:
    months = sorted(frame["exit_month"].unique())
    if not months:
        return {"lower_95": float("nan"), "median": float("nan"), "valid_repetitions": 0}
    grouped = {month: frame.loc[frame["exit_month"] == month, "net_pnl"].to_numpy(dtype=float) for month in months}
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(repetitions):
        sample_months = rng.choice(months, size=len(months), replace=True)
        pnl = np.concatenate([grouped[month] for month in sample_months])
        profits = pnl[pnl > 0].sum()
        losses = -pnl[pnl < 0].sum()
        if losses > 0:
            values.append(float(profits / losses))
    if not values:
        return {"lower_95": float("nan"), "median": float("nan"), "valid_repetitions": 0}
    arr = np.asarray(values)
    return {"lower_95": float(np.quantile(arr, 0.05)), "median": float(np.median(arr)), "valid_repetitions": len(values)}


def validate_trade_ledger(frame: pd.DataFrame) -> dict[str, Any]:
    errors = []
    missing = [column for column in TRADE_REQUIRED if column not in frame.columns]
    if missing:
        return {"valid": False, "errors": [f"missing columns: {', '.join(missing)}"], "trades": len(frame)}
    work = frame.copy()
    if work["trade_id"].astype(str).duplicated().any():
        errors.append("duplicate trade_id")
    for column in ("entry_fill_at", "exit_fill_at"):
        work[column] = _timestamps(work[column])
        if work[column].isna().any():
            errors.append(f"invalid {column}")
    if not errors and (work["exit_fill_at"] <= work["entry_fill_at"]).any():
        errors.append("exit_fill_at must be after entry_fill_at")
    direction = work["direction"].astype(str).str.upper()
    if not direction.isin(["LONG", "SHORT"]).all():
        errors.append("direction must be LONG or SHORT")
    numeric_columns = [
        "quantity", "entry_price", "exit_price", "commission", "fees", "spread_cost",
        "slippage_cost", "impact_cost", "borrow_cost", "financing_cost", "taxes", "adv_notional",
    ]
    for column in numeric_columns:
        work[column] = pd.to_numeric(work[column], errors="coerce")
        if work[column].isna().any():
            errors.append(f"non-numeric {column}")
    for column in ("quantity", "entry_price", "exit_price", "adv_notional"):
        if (work[column] <= 0).any():
            errors.append(f"{column} must be positive")
    cost_columns = ["commission", "fees", "spread_cost", "slippage_cost", "impact_cost", "borrow_cost", "financing_cost", "taxes"]
    if (work[cost_columns] < 0).any().any():
        errors.append("cost fields must be nonnegative")
    if work["source_snapshot_hash"].astype(str).str.fullmatch(r"[0-9a-f]{64}").fillna(False).eq(False).any():
        errors.append("invalid source_snapshot_hash")
    if errors:
        return {"valid": False, "errors": sorted(set(errors)), "trades": len(work)}
    sign = np.where(direction.eq("LONG"), 1.0, -1.0)
    work["gross_pnl"] = sign * work["quantity"] * (work["exit_price"] - work["entry_price"])
    work["total_cost"] = work[cost_columns].sum(axis=1)
    work["net_pnl"] = work["gross_pnl"] - work["total_cost"]
    work["entry_notional"] = work["quantity"] * work["entry_price"]
    work["participation_rate"] = work["entry_notional"] / work["adv_notional"]
    work["exit_month"] = work["exit_fill_at"].dt.strftime("%Y-%m")
    profits = float(work.loc[work["net_pnl"] > 0, "net_pnl"].sum())
    losses = float(-work.loc[work["net_pnl"] < 0, "net_pnl"].sum())
    pf = profits / losses if losses > 0 else math.inf
    bootstrap = _cluster_bootstrap_pf(work)
    months = int(work["exit_month"].nunique())
    regimes = int(work["regime"].astype(str).nunique())
    borrow_ok = bool(work.loc[direction.eq("SHORT"), "borrow_available"].astype(bool).all()) if direction.eq("SHORT").any() else True
    capacity_ok = bool((work["participation_rate"] <= 0.10).all())
    result = {
        "valid": True,
        "errors": [],
        "trades": len(work),
        "months": months,
        "regimes": regimes,
        "gross_profit": profits,
        "gross_loss": losses,
        "real_net_profit_factor": float(pf),
        "profit_factor_bootstrap": bootstrap,
        "total_net_pnl": float(work["net_pnl"].sum()),
        "total_explicit_cost": float(work["total_cost"].sum()),
        "borrow_availability_pass": borrow_ok,
        "capacity_participation_pass": capacity_ok,
        "max_participation_rate": float(work["participation_rate"].max()),
    }
    result["gates"] = {
        "minimum_200_closed_trades": len(work) >= 200,
        "minimum_24_months": months >= 24,
        "minimum_4_regimes": regimes >= 4,
        "profit_factor_at_least_1_50": pf >= 1.50,
        "profit_factor_bootstrap_lower_at_least_1_20": bootstrap["lower_95"] >= 1.20,
        "borrow_available": borrow_ok,
        "capacity_participation": capacity_ok,
    }
    result["all_trade_gates_pass"] = all(result["gates"].values())
    return result


def validate_equity_ledger(frame: pd.DataFrame) -> dict[str, Any]:
    missing = [column for column in EQUITY_REQUIRED if column not in frame.columns]
    if missing:
        return {"valid": False, "errors": [f"missing columns: {', '.join(missing)}"]}
    work = frame.copy()
    work["timestamp"] = _timestamps(work["timestamp"])
    if work["timestamp"].isna().any() or work["timestamp"].duplicated().any():
        return {"valid": False, "errors": ["invalid or duplicate timestamp"]}
    work = work.sort_values("timestamp")
    for column in ("net_liquidation_value", "stress_net_liquidation_value"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
        if work[column].isna().any() or (work[column] <= 0).any():
            return {"valid": False, "errors": [f"invalid {column}"]}
    normal_dd = _max_drawdown(work["net_liquidation_value"])
    stress_dd = _max_drawdown(work["stress_net_liquidation_value"])
    return {
        "valid": True,
        "errors": [],
        "observations": len(work),
        "normal_max_drawdown": normal_dd,
        "stress_max_drawdown": stress_dd,
        "gates": {
            "normal_max_drawdown_at_most_15pct": normal_dd <= 0.15,
            "stress_max_drawdown_at_most_20pct": stress_dd <= 0.20,
        },
        "all_equity_gates_pass": normal_dd <= 0.15 and stress_dd <= 0.20,
    }


def evaluate(trades: pd.DataFrame, equity: pd.DataFrame) -> dict[str, Any]:
    trade_result = validate_trade_ledger(trades)
    equity_result = validate_equity_ledger(equity)
    all_pass = bool(trade_result.get("all_trade_gates_pass") and equity_result.get("all_equity_gates_pass"))
    return {"trade_ledger": trade_result, "equity_ledger": equity_result, "all_risk_profit_gates_pass": all_pass}
