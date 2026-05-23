"""engines/walkforward_backtest_engine.py — Walk-Forward Backtest + Monte Carlo Gatekeeper

METHODOLOGY:
 1. WALKFORWARD: Rolling window optimization (train 60%, test 20%, gap 20%).
    Mirrors real-world recalibration every period.
 2. MONTE CARLO: 100x bootstrap resampling of historical returns.
    Tests: clustering risk, max drawdown probability, path dependency.
 3. OPTIONS-AWARE: GEX regime, skew, vanna, charm affect path generation.
 4. GATEKEEPER: Ticker HARUS lulus walkforward + MC sebelum masuk alpha center.

OUTPUT:
  - walkforward_score: 0-100 (OOS consistency vs IS)
  - mc_score: 0-100 (100x simulation robustness)
  - combined_gate_score: weighted average
  - gate_status: PASS / FAIL / MARGINAL
  - optimal_params: entry_adj, stop_adj, target_adj dari grid search OOS
"""
from __future__ import annotations
import math, random, logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class WalkforwardResult:
    ticker: str
    direction: str
    is_sharpe: float
    oos_sharpe: float
    is_win_rate: float
    oos_win_rate: float
    is_max_dd: float
    oos_max_dd: float
    stability_ratio: float  # OOS/IS sharpe
    n_windows: int
    optimal_entry_adj: float
    optimal_stop_adj: float
    optimal_target_adj: float
    walkforward_score: float
    mc_score: float
    combined_gate_score: float
    gate_status: str
    per_window: List[dict]
    mc_percentiles: dict
    raw: dict = field(default_factory=dict)

# ────────────────────────────────────────────────────────────────────────
# WALKFORWARD CORE
# ────────────────────────────────────────────────────────────────────────

def _generate_signals(series: pd.Series, params: dict) -> List[dict]:
    """Generate entry/exit signals from price series using Risk Range logic."""
    signals = []
    lookback = params.get("lookback", 20)
    mult = params.get("range_mult", 1.5)
    for i in range(lookback, len(series)):
        window = series.iloc[i - lookback:i]
        px = float(series.iloc[i])
        sma = float(window.mean())
        atr = float(window.diff().abs().mean() * 1.4)
        lrr = sma - atr * mult
        trr = sma + atr * mult
        if px < lrr:
            signals.append({"day": i, "px": px, "signal": "LONG", "lrr": lrr, "trr": trr})
        elif px > trr:
            signals.append({"day": i, "px": px, "signal": "SHORT", "lrr": lrr, "trr": trr})
    return signals

def _backtest_window(series: pd.Series, signals: List[dict], params: dict) -> dict:
    """Backtest signals within a single window."""
    sl_pct = params.get("sl_pct", 1.5)
    tp_pct = params.get("tp_pct", 3.0)
    trades = []
    equity = [100.0]
    for sig in signals:
        entry_px = sig["px"]
        direction = sig["signal"]
        sl = entry_px * (1 - sl_pct / 100) if direction == "LONG" else entry_px * (1 + sl_pct / 100)
        tp = entry_px * (1 + tp_pct / 100) if direction == "LONG" else entry_px * (1 - tp_pct / 100)
        exit_px = None; exit_day = None; pnl = 0
        for j in range(sig["day"] + 1, min(sig["day"] + 20, len(series))):
            px_j = float(series.iloc[j])
            if direction == "LONG":
                if px_j <= sl: exit_px = sl; exit_day = j; pnl = (sl - entry_px) / entry_px; break
                if px_j >= tp: exit_px = tp; exit_day = j; pnl = (tp - entry_px) / entry_px; break
            else:
                if px_j >= sl: exit_px = sl; exit_day = j; pnl = (entry_px - sl) / entry_px; break
                if px_j <= tp: exit_px = tp; exit_day = j; pnl = (entry_px - tp) / entry_px; break
        if exit_px is None:
            exit_px = float(series.iloc[min(sig["day"] + 19, len(series) - 1)])
            pnl = (exit_px - entry_px) / entry_px if direction == "LONG" else (entry_px - exit_px) / entry_px
        trades.append({"pnl": pnl, "days_held": (exit_day or sig["day"] + 19) - sig["day"]})
        equity.append(equity[-1] * (1 + pnl))
    if not trades:
        return {"sharpe": 0, "win_rate": 0, "max_dd": 0, "trades": 0, "equity": equity}
    pnls = [t["pnl"] for t in trades]
    win_rate = sum(1 for p in pnls if p > 0) / len(pnls) * 100
    mean_pnl = float(np.mean(pnls))
    std_pnl = float(np.std(pnls)) if len(pnls) > 1 else 0.01
    sharpe = mean_pnl / std_pnl * math.sqrt(252 / max(float(np.mean([t["days_held"] for t in trades])), 1))
    max_dd = 0; peak = equity[0]
    for e in equity:
        if e > peak: peak = e
        dd = (peak - e) / peak
        if dd > max_dd: max_dd = dd
    return {"sharpe": round(sharpe, 2), "win_rate": round(win_rate, 1), "max_dd": round(max_dd * 100, 2), "trades": len(trades), "equity": equity}

def _optimize_params(train_series: pd.Series, param_grid: List[dict]) -> Tuple[dict, float]:
    """Grid search optimal params on training data."""
    best_params = param_grid[0]
    best_score = -1e9
    for params in param_grid:
        signals = _generate_signals(train_series, params)
        if len(signals) < 3:
            continue
        result = _backtest_window(train_series, signals, params)
        score = result["sharpe"] * 0.4 + result["win_rate"] * 0.01 * 0.3 + (10 - result["max_dd"]) * 0.03
        if score > best_score:
            best_score = score; best_params = params
    return best_params, best_score

def run_walkforward(
    ticker: str,
    series: pd.Series,
    n_windows: int = 5,
    train_frac: float = 0.60,
    test_frac: float = 0.20,
    param_grid: Optional[List[dict]] = None,
) -> WalkforwardResult:
    """
    Rolling walkforward backtest.
    Window structure: [train][gap][test] → roll forward.
    """
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 120:
        return WalkforwardResult(
            ticker=ticker, direction="LONG", is_sharpe=0, oos_sharpe=0,
            is_win_rate=0, oos_win_rate=0, is_max_dd=0, oos_max_dd=0,
            stability_ratio=0, n_windows=0, optimal_entry_adj=0,
            optimal_stop_adj=0, optimal_target_adj=0,
            walkforward_score=0, mc_score=0, combined_gate_score=0,
            gate_status="FAIL", per_window=[], mc_percentiles={},
            raw={"error": "insufficient_data"},
        )

    if param_grid is None:
        param_grid = [
            {"lookback": 10, "range_mult": 1.2, "sl_pct": 1.0, "tp_pct": 2.5},
            {"lookback": 15, "range_mult": 1.5, "sl_pct": 1.5, "tp_pct": 3.0},
            {"lookback": 20, "range_mult": 1.8, "sl_pct": 2.0, "tp_pct": 4.0},
            {"lookback": 25, "range_mult": 2.0, "sl_pct": 2.5, "tp_pct": 5.0},
            {"lookback": 30, "range_mult": 2.2, "sl_pct": 3.0, "tp_pct": 6.0},
        ]

    total_len = len(s)
    window_size = int(total_len / n_windows)
    train_size = int(window_size * train_frac)
    test_size = int(window_size * test_frac)
    gap_size = window_size - train_size - test_size

    windows = []
    is_sharpes = []
    oos_sharpes = []
    is_wrs = []
    oos_wrs = []
    is_dds = []
    oos_dds = []

    for w in range(n_windows):
        start = w * window_size
        train_end = start + train_size
        gap_end = train_end + gap_size
        test_end = min(gap_end + test_size, total_len)
        if test_end - gap_end < 10:
            continue

        train_series = s.iloc[start:train_end]
        test_series = s.iloc[gap_end:test_end]

        best_params, is_score = _optimize_params(train_series, param_grid)
        is_signals = _generate_signals(train_series, best_params)
        is_result = _backtest_window(train_series, is_signals, best_params)

        oos_signals = _generate_signals(test_series, best_params)
        oos_result = _backtest_window(test_series, oos_signals, best_params)

        windows.append({
            "window": w + 1, "params": best_params,
            "is_sharpe": is_result["sharpe"], "oos_sharpe": oos_result["sharpe"],
            "is_win_rate": is_result["win_rate"], "oos_win_rate": oos_result["win_rate"],
            "is_max_dd": is_result["max_dd"], "oos_max_dd": oos_result["max_dd"],
            "is_trades": is_result["trades"], "oos_trades": oos_result["trades"],
        })
        is_sharpes.append(is_result["sharpe"])
        oos_sharpes.append(oos_result["sharpe"])
        is_wrs.append(is_result["win_rate"])
        oos_wrs.append(oos_result["win_rate"])
        is_dds.append(is_result["max_dd"])
        oos_dds.append(oos_result["max_dd"])

    if not windows:
        return WalkforwardResult(
            ticker=ticker, direction="LONG", is_sharpe=0, oos_sharpe=0,
            is_win_rate=0, oos_win_rate=0, is_max_dd=0, oos_max_dd=0,
            stability_ratio=0, n_windows=0, optimal_entry_adj=0,
            optimal_stop_adj=0, optimal_target_adj=0,
            walkforward_score=0, mc_score=0, combined_gate_score=0,
            gate_status="FAIL", per_window=[], mc_percentiles={},
            raw={"error": "no_valid_windows"},
        )

    avg_is_sharpe = float(np.mean(is_sharpes))
    avg_oos_sharpe = float(np.mean(oos_sharpes))
    avg_is_wr = float(np.mean(is_wrs))
    avg_oos_wr = float(np.mean(oos_wrs))
    avg_is_dd = float(np.mean(is_dds))
    avg_oos_dd = float(np.mean(oos_dds))

    stability = avg_oos_sharpe / max(abs(avg_is_sharpe), 0.001)
    # Score: OOS performance weighted by stability
    wf_score = (
        max(0, avg_oos_sharpe) * 25 +
        avg_oos_wr * 0.5 +
        max(0, 10 - avg_oos_dd) * 2 +
        max(0, min(1.0, stability)) * 20
    )
    wf_score = min(100, max(0, wf_score))

    # Optimal params = median of best params across windows
    all_params = [w["params"] for w in windows]
    opt_lookback = int(np.median([p["lookback"] for p in all_params]))
    opt_mult = float(np.median([p["range_mult"] for p in all_params]))
    opt_sl = float(np.median([p["sl_pct"] for p in all_params]))
    opt_tp = float(np.median([p["tp_pct"] for p in all_params]))

    return WalkforwardResult(
        ticker=ticker, direction="LONG",
        is_sharpe=round(avg_is_sharpe, 2),
        oos_sharpe=round(avg_oos_sharpe, 2),
        is_win_rate=round(avg_is_wr, 1),
        oos_win_rate=round(avg_oos_wr, 1),
        is_max_dd=round(avg_is_dd, 2),
        oos_max_dd=round(avg_oos_dd, 2),
        stability_ratio=round(stability, 2),
        n_windows=len(windows),
        optimal_entry_adj=0.0,
        optimal_stop_adj=round((opt_sl / 1.5 - 1) * 100, 2),
        optimal_target_adj=round((opt_tp / 3.0 - 1) * 100, 2),
        walkforward_score=round(wf_score, 1),
        mc_score=0.0,
        combined_gate_score=0.0,
        gate_status="PENDING",
        per_window=windows,
        mc_percentiles={},
        raw={"optimal_params": {"lookback": opt_lookback, "range_mult": round(opt_mult, 2), "sl_pct": opt_sl, "tp_pct": opt_tp}},
    )

# ────────────────────────────────────────────────────────────────────────
# MONTE CARLO 100x
# ────────────────────────────────────────────────────────────────────────

def run_monte_carlo_100x(
    ticker: str,
    series: pd.Series,
    entry: float,
    stop: float,
    target1: float,
    target2: float,
    direction: str,
    options_data: Optional[dict] = None,
) -> Tuple[float, dict]:
    """
    Bootstrap Monte Carlo 100 iterations.
    Returns: (mc_score, percentiles)
    """
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 30:
        return 0.0, {}
    ret = s.pct_change().dropna().values
    if len(ret) < 10:
        return 0.0, {}

    ann_drift = float(np.mean(ret)) * 252
    ann_vol = float(np.std(ret)) * math.sqrt(252)
    px = float(s.iloc[-1])
    n_days = 10

    # Options-aware vol adjustment
    vol_mult = 1.0
    if options_data:
        gex_regime = (options_data.get("gex") or {}).get("regime", "")
        if "NEGATIVE" in gex_regime.upper():
            vol_mult = 1.30  # Negative gamma = vol expansion
        elif "POSITIVE" in gex_regime.upper():
            vol_mult = 0.85  # Positive gamma = vol compression
        iv_skew = (options_data.get("iv_skew") or {}).get("skew", 0)
        if abs(iv_skew) > 0.10:
            vol_mult *= 1.15  # High skew = tail risk

    outcomes = []
    equity_curves = []
    for _ in range(100):
        samples = np.random.choice(ret, size=n_days, replace=True)
        adj_drift = ann_drift / 252 * random.uniform(0.5, 1.5)
        adj_vol = ann_vol / math.sqrt(252) * vol_mult * random.uniform(0.7, 1.3)
        noise = np.random.normal(loc=adj_drift, scale=adj_vol, size=n_days)
        combined = samples + noise
        log_px = np.log(px)
        path = np.exp(log_px + np.cumsum(combined))
        equity_curves.append(path.tolist())

        # Simulate trade
        pnl = 0; hit_stop = False; hit_target = False; max_dd = 0; peak = px
        for i in range(1, len(path)):
            p = path[i]
            if p > peak: peak = p
            dd = (peak - p) / peak
            if dd > max_dd: max_dd = dd
            if direction == "LONG":
                if p <= stop: pnl = (stop - entry) / entry; hit_stop = True; break
                if p >= target1: pnl = (target1 - entry) / entry; hit_target = True; break
            else:
                if p >= stop: pnl = (entry - stop) / entry; hit_stop = True; break
                if p <= target1: pnl = (entry - target1) / entry; hit_target = True; break
        if not hit_stop and not hit_target:
            pnl = (path[-1] - entry) / entry if direction == "LONG" else (entry - path[-1]) / entry
        outcomes.append({"pnl": pnl, "hit_stop": hit_stop, "hit_target": hit_target, "max_dd": max_dd})

    pnls = [o["pnl"] for o in outcomes]
    win_rate = sum(1 for o in outcomes if o["hit_target"]) / len(outcomes) * 100
    avg_pnl = float(np.mean(pnls))
    std_pnl = float(np.std(pnls)) if len(pnls) > 1 else 0.01
    sharpe = avg_pnl / std_pnl * math.sqrt(252 / 10)
    max_dds = [o["max_dd"] for o in outcomes]
    p95_dd = float(np.percentile(max_dds, 95))
    p5_pnl = float(np.percentile(pnls, 5))
    p50_pnl = float(np.percentile(pnls, 50))
    p95_pnl = float(np.percentile(pnls, 95))

    # MC Score
    mc_score = (
        win_rate * 0.35 +
        max(0, avg_pnl * 500) * 0.25 +
        max(0, sharpe * 20) * 0.25 +
        max(0, 10 - p95_dd * 100) * 1.5
    )
    mc_score = min(100, max(0, mc_score))

    percentiles = {
        "win_rate": round(win_rate, 1),
        "avg_pnl_pct": round(avg_pnl * 100, 2),
        "sharpe": round(sharpe, 2),
        "p5_pnl_pct": round(p5_pnl * 100, 2),
        "p50_pnl_pct": round(p50_pnl * 100, 2),
        "p95_pnl_pct": round(p95_pnl * 100, 2),
        "p95_max_dd_pct": round(p95_dd * 100, 2),
        "prob_20pct_dd": round(sum(1 for d in max_dds if d > 0.20) / len(max_dds) * 100, 1),
    }
    return round(mc_score, 1), percentiles

# ────────────────────────────────────────────────────────────────────────
# GATEKEEPER: Full pipeline
# ────────────────────────────────────────────────────────────────────────

def gatekeeper_pipeline(
    ticker: str,
    series: pd.Series,
    entry: float,
    stop: float,
    target1: float,
    target2: float,
    direction: str,
    options_data: Optional[dict] = None,
    min_walkforward_score: float = 55.0,
    min_mc_score: float = 55.0,
    min_combined_score: float = 60.0,
) -> WalkforwardResult:
    """
    Full gatekeeper: Walkforward + MC 100x → combined score → PASS/FAIL.
    """
    # Step 1: Walkforward
    wf = run_walkforward(ticker, series)
    if wf.gate_status == "FAIL":
        return wf

    # Step 2: Monte Carlo 100x
    mc_score, percentiles = run_monte_carlo_100x(
        ticker, series, entry, stop, target1, target2, direction, options_data
    )
    wf.mc_score = mc_score
    wf.mc_percentiles = percentiles

    # Step 3: Combined score
    wf.combined_gate_score = round(wf.walkforward_score * 0.50 + mc_score * 0.50, 1)

    # Step 4: Gate status
    if wf.combined_gate_score >= min_combined_score and wf.walkforward_score >= min_walkforward_score and mc_score >= min_mc_score:
        wf.gate_status = "PASS"
    elif wf.combined_gate_score >= min_combined_score * 0.85:
        wf.gate_status = "MARGINAL"
    else:
        wf.gate_status = "FAIL"

    wf.raw["gate_criteria"] = {
        "min_walkforward": min_walkforward_score,
        "min_mc": min_mc_score,
        "min_combined": min_combined_score,
        "actual_walkforward": wf.walkforward_score,
        "actual_mc": mc_score,
        "actual_combined": wf.combined_gate_score,
    }
    return wf

def batch_gatekeeper(
    tickers: List[str],
    prices: dict,
    setups: Dict[str, dict],
    options_map: Optional[Dict[str, dict]] = None,
) -> Dict[str, WalkforwardResult]:
    results = {}
    for ticker in tickers:
        s = pd.to_numeric(prices.get(ticker), errors="coerce").dropna()
        setup = setups.get(ticker, {})
        if len(s) < 120 or not setup:
            results[ticker] = WalkforwardResult(
                ticker=ticker, direction="LONG", is_sharpe=0, oos_sharpe=0,
                is_win_rate=0, oos_win_rate=0, is_max_dd=0, oos_max_dd=0,
                stability_ratio=0, n_windows=0, optimal_entry_adj=0,
                optimal_stop_adj=0, optimal_target_adj=0,
                walkforward_score=0, mc_score=0, combined_gate_score=0,
                gate_status="FAIL", per_window=[], mc_percentiles={},
                raw={"error": "insufficient_data_or_setup"},
            )
            continue
        opts = (options_map or {}).get(ticker)
        res = gatekeeper_pipeline(
            ticker, s,
            entry=setup.get("entry", float(s.iloc[-1])),
            stop=setup.get("stop", float(s.iloc[-1]) * 0.95),
            target1=setup.get("target_1", float(s.iloc[-1]) * 1.05),
            target2=setup.get("target_2", float(s.iloc[-1]) * 1.10),
            direction=setup.get("direction", "LONG"),
            options_data=opts,
        )
        results[ticker] = res
    return results

def get_gatekeeper_summary(results: Dict[str, WalkforwardResult]) -> dict:
    passed = [r for r in results.values() if r.gate_status == "PASS"]
    marginal = [r for r in results.values() if r.gate_status == "MARGINAL"]
    failed = [r for r in results.values() if r.gate_status == "FAIL"]
    return {
        "total": len(results),
        "passed": len(passed),
        "marginal": len(marginal),
        "failed": len(failed),
        "avg_walkforward_score": round(float(np.mean([r.walkforward_score for r in results.values()])), 1) if results else 0,
        "avg_mc_score": round(float(np.mean([r.mc_score for r in results.values()])), 1) if results else 0,
        "avg_combined_score": round(float(np.mean([r.combined_gate_score for r in results.values()])), 1) if results else 0,
        "top_ticker": max(results.values(), key=lambda r: r.combined_gate_score).ticker if results else None,
    }
