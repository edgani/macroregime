"""Strict realized-performance gate for War Room OS V9.5.

Unlike the legacy gate, this module rejects direct paper/synthetic ledgers, parses booleans
strictly, binds trades to one account and real execution source, rejects future/backfilled-looking
fills, requires an elapsed 24-month window, and reconciles trade P&L to the account equity ledger.
"""
from __future__ import annotations

import datetime as dt
import math
import re
from typing import Any

import numpy as np
import pandas as pd

HEX64 = re.compile(r"^[0-9a-f]{64}$")
LIVE_SOURCES = {"BROKER_EXPORT", "EXCHANGE_EXPORT", "BROKER_API", "EXCHANGE_API"}
TRADE_REQUIRED = [
    "trade_id", "forecast_id", "strategy_id", "market", "security_id", "direction",
    "entry_fill_at", "exit_fill_at", "quantity", "entry_price", "exit_price",
    "commission", "fees", "spread_cost", "slippage_cost", "impact_cost",
    "borrow_cost", "financing_cost", "taxes", "regime", "regime_definition_hash",
    "adv_notional", "borrow_available", "source_snapshot_hash", "execution_source",
    "is_live", "paper", "synthetic", "account_id_hash", "entry_order_id_hash",
    "exit_order_id_hash",
]
EQUITY_REQUIRED = [
    "timestamp", "net_liquidation_value", "stress_net_liquidation_value",
    "external_cash_flow", "account_id_hash", "source_snapshot_hash", "execution_source",
    "is_live", "paper", "synthetic", "stress_model_hash",
]


def _strict_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "yes"}:
            return True
        if text in {"false", "0", "no"}:
            return False
    raise ValueError(f"not a strict boolean: {value!r}")


def _strict_bool_series(series: pd.Series, name: str, errors: list[str]) -> pd.Series:
    out: list[bool] = []
    for index, value in series.items():
        try:
            out.append(_strict_bool(value))
        except ValueError:
            errors.append(f"invalid boolean {name} at row {index}")
            out.append(False)
    return pd.Series(out, index=series.index, dtype=bool)


def _timestamps(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce")


def _max_drawdown(values: pd.Series) -> float:
    s = pd.to_numeric(values, errors="coerce").dropna()
    if s.empty or (s <= 0).any():
        return math.inf
    peak = s.cummax()
    return float((1.0 - s / peak).max())


def _cluster_bootstrap_pf(frame: pd.DataFrame, *, repetitions: int = 10000, seed: int = 9501) -> dict[str, float | int]:
    months = sorted(frame["exit_month"].unique())
    if not months:
        return {"lower_95": float("nan"), "median": float("nan"), "valid_repetitions": 0}
    grouped = {m: frame.loc[frame["exit_month"] == m, "net_pnl"].to_numpy(dtype=float) for m in months}
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(repetitions):
        sample = rng.choice(months, size=len(months), replace=True)
        pnl = np.concatenate([grouped[m] for m in sample])
        profits = pnl[pnl > 0].sum()
        losses = -pnl[pnl < 0].sum()
        if losses > 0:
            values.append(float(profits / losses))
    if not values:
        return {"lower_95": float("nan"), "median": float("nan"), "valid_repetitions": 0}
    arr = np.asarray(values)
    return {
        "lower_95": float(np.quantile(arr, 0.05)),
        "median": float(np.median(arr)),
        "valid_repetitions": len(values),
    }


def _valid_hex_series(series: pd.Series) -> bool:
    return bool(series.astype(str).str.lower().str.fullmatch(HEX64.pattern).fillna(False).all())


def validate_trade_ledger(frame: pd.DataFrame, *, now: dt.datetime | None = None) -> dict[str, Any]:
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    missing = [c for c in TRADE_REQUIRED if c not in frame.columns]
    if missing:
        return {"valid": False, "errors": ["missing columns: " + ", ".join(missing)], "trades": len(frame)}
    errors: list[str] = []
    work = frame.copy()
    if work.empty:
        errors.append("trade ledger is empty")
    if work["trade_id"].astype(str).duplicated().any():
        errors.append("duplicate trade_id")
    if work["entry_order_id_hash"].astype(str).duplicated().any():
        errors.append("duplicate entry_order_id_hash")
    if work["exit_order_id_hash"].astype(str).duplicated().any():
        errors.append("duplicate exit_order_id_hash")

    for column in ("entry_fill_at", "exit_fill_at"):
        work[column] = _timestamps(work[column])
        if work[column].isna().any():
            errors.append(f"invalid {column}")
    if not work[["entry_fill_at", "exit_fill_at"]].isna().any().any():
        if (work["exit_fill_at"] <= work["entry_fill_at"]).any():
            errors.append("exit_fill_at must be after entry_fill_at")
        if (work["exit_fill_at"] > pd.Timestamp(now)).any():
            errors.append("future exit fills rejected")

    direction = work["direction"].astype(str).str.upper().str.strip()
    if not direction.isin(["LONG", "SHORT"]).all():
        errors.append("direction must be LONG or SHORT")
    source = work["execution_source"].astype(str).str.upper().str.strip()
    if not source.isin(LIVE_SOURCES).all():
        errors.append("execution_source must be a recognized live broker/exchange source")

    live = _strict_bool_series(work["is_live"], "is_live", errors)
    paper = _strict_bool_series(work["paper"], "paper", errors)
    synthetic = _strict_bool_series(work["synthetic"], "synthetic", errors)
    borrow = _strict_bool_series(work["borrow_available"], "borrow_available", errors)
    if not live.all():
        errors.append("all fills must be marked live")
    if paper.any():
        errors.append("paper fills rejected")
    if synthetic.any():
        errors.append("synthetic fills rejected")

    hash_columns = [
        "regime_definition_hash", "source_snapshot_hash", "account_id_hash",
        "entry_order_id_hash", "exit_order_id_hash",
    ]
    for column in hash_columns:
        if not _valid_hex_series(work[column]):
            errors.append(f"invalid {column}")
        if work[column].astype(str).str.lower().eq("0" * 64).any():
            errors.append(f"zero {column} rejected")
    accounts = set(work["account_id_hash"].astype(str).str.lower())
    if len(accounts) != 1:
        errors.append("one exact sleeve must bind to one account_id_hash")
    markets = set(work["market"].astype(str).str.lower().str.strip())
    if len(markets) != 1:
        errors.append("one exact sleeve must contain one market")
    strategies = set(work["strategy_id"].astype(str).str.strip())
    if len(strategies) != 1 or not next(iter(strategies), ""):
        errors.append("one exact sleeve must contain one strategy_id")
    sources = set(source)
    if len(sources) != 1:
        errors.append("one exact sleeve must contain one execution_source")
    if set(work["entry_order_id_hash"].astype(str).str.lower()) & set(work["exit_order_id_hash"].astype(str).str.lower()):
        errors.append("entry and exit order hashes collide")

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
    costs = ["commission", "fees", "spread_cost", "slippage_cost", "impact_cost", "borrow_cost", "financing_cost", "taxes"]
    if (work[costs] < 0).any().any():
        errors.append("cost fields must be nonnegative")
    if direction.eq("SHORT").any() and not borrow[direction.eq("SHORT")].all():
        errors.append("short fill without borrow availability")

    if errors:
        return {"valid": False, "errors": sorted(set(errors)), "trades": len(work)}

    sign = np.where(direction.eq("LONG"), 1.0, -1.0)
    work["gross_pnl"] = sign * work["quantity"] * (work["exit_price"] - work["entry_price"])
    work["total_cost"] = work[costs].sum(axis=1)
    work["net_pnl"] = work["gross_pnl"] - work["total_cost"]
    work["entry_notional"] = work["quantity"] * work["entry_price"]
    work["participation_rate"] = work["entry_notional"] / work["adv_notional"]
    work["exit_month"] = work["exit_fill_at"].dt.strftime("%Y-%m")

    span_days = int((work["exit_fill_at"].max() - work["exit_fill_at"].min()).days) if len(work) > 1 else 0
    months = int(work["exit_month"].nunique())
    regime_counts = work["regime"].astype(str).value_counts()
    regimes = int(len(regime_counts))
    regimes_with_20 = int((regime_counts >= 20).sum())
    profits = float(work.loc[work["net_pnl"] > 0, "net_pnl"].sum())
    losses = float(-work.loc[work["net_pnl"] < 0, "net_pnl"].sum())
    pf = profits / losses if losses > 0 else math.inf
    bootstrap = _cluster_bootstrap_pf(work)
    capacity_ok = bool((work["participation_rate"] <= 0.10).all())
    gates = {
        "minimum_200_closed_trades": len(work) >= 200,
        "minimum_24_distinct_months": months >= 24,
        "minimum_730_elapsed_days": span_days >= 730,
        "minimum_4_regimes": regimes >= 4,
        "minimum_20_trades_in_each_of_4_regimes": regimes_with_20 >= 4,
        "profit_factor_at_least_1_50": pf >= 1.50,
        "profit_factor_bootstrap_lower_at_least_1_20": float(bootstrap["lower_95"]) >= 1.20,
        "borrow_available": True,
        "capacity_participation": capacity_ok,
    }
    return {
        "valid": True,
        "errors": [],
        "trades": len(work),
        "months": months,
        "elapsed_days": span_days,
        "regimes": regimes,
        "regimes_with_at_least_20_trades": regimes_with_20,
        "real_net_profit_factor": float(pf),
        "profit_factor_bootstrap": bootstrap,
        "total_net_pnl": float(work["net_pnl"].sum()),
        "total_explicit_cost": float(work["total_cost"].sum()),
        "max_participation_rate": float(work["participation_rate"].max()),
        "account_id_hash": next(iter(accounts)),
        "market": next(iter(markets)),
        "strategy_id": next(iter(strategies)),
        "execution_source": next(iter(sources)),
        "gates": gates,
        "all_trade_gates_pass": all(gates.values()),
    }


def validate_equity_ledger(frame: pd.DataFrame, *, expected_account_id_hash: str, expected_execution_source: str, max_exit_at: pd.Timestamp | None = None, now: dt.datetime | None = None) -> dict[str, Any]:
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    missing = [c for c in EQUITY_REQUIRED if c not in frame.columns]
    if missing:
        return {"valid": False, "errors": ["missing columns: " + ", ".join(missing)]}
    errors: list[str] = []
    work = frame.copy()
    work["timestamp"] = _timestamps(work["timestamp"])
    if work["timestamp"].isna().any() or work["timestamp"].duplicated().any():
        errors.append("invalid or duplicate timestamp")
    work = work.sort_values("timestamp")
    if not work["timestamp"].isna().any() and (work["timestamp"] > pd.Timestamp(now)).any():
        errors.append("future equity observations rejected")
    for column in ("net_liquidation_value", "stress_net_liquidation_value", "external_cash_flow"):
        work[column] = pd.to_numeric(work[column], errors="coerce")
        if work[column].isna().any():
            errors.append(f"invalid {column}")
    if (work["net_liquidation_value"] <= 0).any() or (work["stress_net_liquidation_value"] <= 0).any():
        errors.append("equity values must be positive")
    live = _strict_bool_series(work["is_live"], "is_live", errors)
    paper = _strict_bool_series(work["paper"], "paper", errors)
    synthetic = _strict_bool_series(work["synthetic"], "synthetic", errors)
    if not live.all() or paper.any() or synthetic.any():
        errors.append("equity ledger must be live and non-paper/non-synthetic")
    equity_sources = set(work["execution_source"].astype(str).str.upper().str.strip())
    if not equity_sources or not equity_sources.issubset(LIVE_SOURCES):
        errors.append("invalid equity execution_source")
    if equity_sources != {expected_execution_source.upper()}:
        errors.append("equity execution_source does not match trade ledger")
    for column in ("account_id_hash", "source_snapshot_hash", "stress_model_hash"):
        if not _valid_hex_series(work[column]) or work[column].astype(str).str.lower().eq("0" * 64).any():
            errors.append(f"invalid {column}")
    accounts = set(work["account_id_hash"].astype(str).str.lower())
    if accounts != {expected_account_id_hash.lower()}:
        errors.append("equity account does not match trade account")
    if max_exit_at is not None and not work.empty and work["timestamp"].max() < max_exit_at:
        errors.append("equity ledger ends before final trade exit")
    span_days = int((work["timestamp"].max() - work["timestamp"].min()).days) if len(work) > 1 else 0
    if span_days < 730:
        errors.append("equity ledger spans fewer than 730 days")
    if errors:
        return {"valid": False, "errors": sorted(set(errors)), "observations": len(work)}
    normal_dd = _max_drawdown(work["net_liquidation_value"])
    stress_dd = _max_drawdown(work["stress_net_liquidation_value"])
    gates = {
        "normal_max_drawdown_at_most_15pct": normal_dd <= 0.15,
        "stress_max_drawdown_at_most_20pct": stress_dd <= 0.20,
    }
    return {
        "valid": True,
        "errors": [],
        "observations": len(work),
        "elapsed_days": span_days,
        "normal_max_drawdown": normal_dd,
        "stress_max_drawdown": stress_dd,
        "external_cash_flow_total": float(work["external_cash_flow"].sum()),
        "start_nlv": float(work["net_liquidation_value"].iloc[0]),
        "end_nlv": float(work["net_liquidation_value"].iloc[-1]),
        "gates": gates,
        "all_equity_gates_pass": all(gates.values()),
    }


def evaluate(trades: pd.DataFrame, equity: pd.DataFrame, *, now: dt.datetime | None = None, expected_market: str | None = None) -> dict[str, Any]:
    trade_result = validate_trade_ledger(trades, now=now)
    if trade_result.get("valid") and expected_market is not None and str(trade_result.get("market")).lower() != str(expected_market).lower():
        trade_result = {**trade_result, "valid": False, "errors": ["trade market does not match predictor market"], "all_trade_gates_pass": False}
    if not trade_result.get("valid"):
        return {"trade_ledger": trade_result, "equity_ledger": {"valid": False, "errors": ["trade ledger invalid"]}, "all_risk_profit_gates_pass": False}
    exits = pd.to_datetime(trades["exit_fill_at"], utc=True, errors="coerce")
    equity_result = validate_equity_ledger(
        equity,
        expected_account_id_hash=str(trade_result["account_id_hash"]),
        expected_execution_source=str(trade_result["execution_source"]),
        max_exit_at=exits.max() if not exits.isna().all() else None,
        now=now,
    )
    reconciliation = {"pass": False, "difference": None, "tolerance": None}
    if equity_result.get("valid"):
        equity_pnl = equity_result["end_nlv"] - equity_result["start_nlv"] - equity_result["external_cash_flow_total"]
        trade_pnl = float(trade_result["total_net_pnl"])
        tolerance = max(1.0, abs(trade_pnl) * 0.01)
        difference = abs(equity_pnl - trade_pnl)
        reconciliation = {"pass": difference <= tolerance, "difference": difference, "tolerance": tolerance, "equity_adjusted_pnl": equity_pnl, "trade_net_pnl": trade_pnl}
    all_pass = bool(trade_result.get("all_trade_gates_pass") and equity_result.get("all_equity_gates_pass") and reconciliation["pass"])
    return {
        "schema": "warroom.v95.realized_performance.v1",
        "trade_ledger": trade_result,
        "equity_ledger": equity_result,
        "pnl_reconciliation": reconciliation,
        "all_risk_profit_gates_pass": all_pass,
    }
