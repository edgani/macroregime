"""engines/simulation_engine.py — Monte Carlo Strategy Robustness Simulator v1.0
Run 100 simulated price paths per ticker to validate entry/stop/target setup.
Only tickers with robustness_score >= threshold survive to market tabs.
"""
from __future__ import annotations
import math
import random
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════
DEFAULT_N_SIMULATIONS: int = 100
DEFAULT_HOLDING_DAYS: int = 10          # Swing trade horizon
DEFAULT_THRESHOLD: float = 65.0          # Min robustness score to display
VOL_PERTURBATION: float = 0.30           # ±30% vol noise
DRIFT_PERTURBATION: float = 0.50         # ±50% drift noise
OPTIONS_PERTURBATION: float = 0.25       # ±25% greeks noise
REGIME_SHIFT_PROB: float = 0.10          # 10% chance regime flips in sim
MAX_DRAWDOWN_PENALTY: float = 2.0        # Penalty multiplier for deep DD


@dataclass
class SimResult:
    ticker: str
    win_rate: float
    loss_rate: float
    exp_return_pct: float
    avg_drawdown_pct: float
    sharpe_like: float
    robustness_score: float
    optimal_entry_adj_pct: float   # e.g. -2.0 = wait 2% pullback
    optimal_stop_adj_pct: float    # e.g. +1.5 = widen stop 1.5%
    optimal_target_adj_pct: float  # e.g. -1.0 = reduce target 1%
    time_to_win_days: float
    time_to_loss_days: float
    max_consecutive_losses: int
    passes_filter: bool
    raw_metrics: dict


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _safe_series(s) -> pd.Series:
    if s is None:
        return pd.Series(dtype=float)
    try:
        return pd.to_numeric(pd.Series(s), errors="coerce").dropna()
    except Exception:
        return pd.Series(dtype=float)


def _calc_historical_params(series: pd.Series) -> Tuple[float, float, float]:
    """Return (annual_drift, annual_vol, current_price) from historical close."""
    if len(series) < 30:
        return 0.0, 0.20, float(series.iloc[-1]) if len(series) > 0 else 100.0
    px = float(series.iloc[-1])
    ret = series.pct_change().dropna()
    if len(ret) < 5:
        return 0.0, 0.20, px
    daily_mean = float(ret.mean())
    daily_std = float(ret.std())
    ann_drift = daily_mean * 252
    ann_vol = daily_std * math.sqrt(252)
    if not math.isfinite(ann_drift):
        ann_drift = 0.0
    if not math.isfinite(ann_vol) or ann_vol <= 0:
        ann_vol = 0.20
    return ann_drift, ann_vol, px


def _bootstrap_path(
    current_price: float,
    historical_returns: np.ndarray,
    n_days: int,
    ann_drift: float,
    ann_vol: float,
    vol_perturb: float = VOL_PERTURBATION,
    drift_perturb: float = DRIFT_PERTURBATION,
) -> np.ndarray:
    """Generate one price path via historical bootstrap + GBM overlay."""
    if len(historical_returns) < 5:
        # Pure GBM fallback
        dt = 1 / 252
        adj_drift = ann_drift * random.uniform(1 - drift_perturb, 1 + drift_perturb)
        adj_vol = ann_vol * random.uniform(1 - vol_perturb, 1 + vol_perturb)
        shocks = np.random.normal(
            loc=adj_drift * dt,
            scale=adj_vol * math.sqrt(dt),
            size=n_days,
        )
        log_prices = np.log(current_price) + np.cumsum(shocks)
        return np.exp(log_prices)

    # Bootstrap base: resample historical returns
    samples = np.random.choice(historical_returns, size=n_days, replace=True)
    # Overlay GBM drift/vol adjustment
    adj_drift = ann_drift / 252 * random.uniform(1 - drift_perturb, 1 + drift_perturb)
    adj_vol = ann_vol / math.sqrt(252) * random.uniform(1 - vol_perturb, 1 + vol_perturb)
    noise = np.random.normal(loc=adj_drift, scale=adj_vol, size=n_days)
    combined = samples + noise
    log_px = np.log(current_price)
    log_path = log_px + np.cumsum(combined)
    path = np.exp(log_path)
    # Sanity check: prevent extreme blow-ups
    if path.max() > current_price * 5 or path.min() < current_price * 0.05:
        # Re-run with milder parameters
        return _bootstrap_path(
            current_price, historical_returns, n_days,
            ann_drift * 0.5, ann_vol * 0.8, vol_perturb * 0.5, drift_perturb * 0.5
        )
    return path


def _simulate_single_setup(
    path: np.ndarray,
    entry: float,
    stop: float,
    target1: float,
    target2: float,
    direction: str,
    options_data: Optional[dict] = None,
) -> dict:
    """Simulate one path. Returns outcome dict."""
    px_start = path[0]
    n = len(path)
    outcome = {
        "pnl_pct": 0.0,
        "hit_target": False,
        "hit_stop": False,
        "hit_target2": False,
        "max_dd_pct": 0.0,
        "exit_day": n,
        "exit_price": path[-1],
    }

    # Determine which level hit first
    for i in range(1, n):
        px = path[i]
        # Track drawdown from entry
        if direction == "LONG":
            dd = (px - px_start) / px_start if px < px_start else 0
        else:
            dd = (px_start - px) / px_start if px > px_start else 0
        if dd < outcome["max_dd_pct"]:
            outcome["max_dd_pct"] = dd

        if direction == "LONG":
            if px <= stop:
                outcome["hit_stop"] = True
                outcome["exit_day"] = i
                outcome["exit_price"] = px
                outcome["pnl_pct"] = (stop - entry) / entry * 100
                break
            if px >= target1 and not outcome["hit_target"]:
                outcome["hit_target"] = True
                outcome["exit_day"] = i
                outcome["exit_price"] = px
                outcome["pnl_pct"] = (target1 - entry) / entry * 100
                # Continue to see if target2 also hit
                if px >= target2:
                    outcome["hit_target2"] = True
                    outcome["pnl_pct"] = (target2 - entry) / entry * 100
                    break
        else:  # SHORT
            if px >= stop:
                outcome["hit_stop"] = True
                outcome["exit_day"] = i
                outcome["exit_price"] = px
                outcome["pnl_pct"] = (entry - stop) / entry * 100
                break
            if px <= target1 and not outcome["hit_target"]:
                outcome["hit_target"] = True
                outcome["exit_day"] = i
                outcome["exit_price"] = px
                outcome["pnl_pct"] = (entry - target1) / entry * 100
                if px <= target2:
                    outcome["hit_target2"] = True
                    outcome["pnl_pct"] = (entry - target2) / entry * 100
                    break

    # If no hit, mark-to-market at end
    if not outcome["hit_target"] and not outcome["hit_stop"]:
        if direction == "LONG":
            outcome["pnl_pct"] = (path[-1] - entry) / entry * 100
        else:
            outcome["pnl_pct"] = (entry - path[-1]) / entry * 100

    return outcome


def _score_simulations(
    outcomes: List[dict],
    direction: str,
    current_rr: float,
) -> Tuple[float, float, float, float, float, float, int, float, float]:
    """Aggregate 100 outcomes into metrics."""
    n = len(outcomes)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0.0, 0.0

    wins = [o for o in outcomes if o["hit_target"]]
    losses = [o for o in outcomes if o["hit_stop"]]

    win_rate = len(wins) / n * 100
    loss_rate = len(losses) / n * 100
    pnl_vals = [o["pnl_pct"] for o in outcomes]
    exp_ret = float(np.mean(pnl_vals)) if pnl_vals else 0.0
    dd_vals = [o["max_dd_pct"] for o in outcomes]
    avg_dd = float(np.mean(dd_vals)) if dd_vals else 0.0

    # Sharpe-like: expected return / std of returns (penalized by avg drawdown)
    ret_std = float(np.std(pnl_vals)) if len(pnl_vals) > 1 else 1.0
    if ret_std == 0:
        ret_std = 1.0
    sharpe = exp_ret / ret_std
    if avg_dd != 0:
        sharpe = sharpe / (1 + abs(avg_dd) * MAX_DRAWDOWN_PENALTY)

    # Robustness score (0-100)
    # Components: win_rate(35%) + exp_return_norm(25%) + sharpe(25%) + rr_bonus(15%)
    exp_ret_norm = max(0, min(100, exp_ret * 5))  # 20% exp ret = 100 points
    rr_bonus = min(15, current_rr * 5) if current_rr else 0  # RR 3.0 = 15 points
    score = (
        win_rate * 0.35
        + exp_ret_norm * 0.25
        + max(0, sharpe * 20) * 0.25  # Sharpe 5.0 = 100 points
        + rr_bonus
    )
    score = min(100.0, max(0.0, score))

    # Time stats
    ttw = float(np.mean([o["exit_day"] for o in wins])) if wins else 0.0
    ttl = float(np.mean([o["exit_day"] for o in losses])) if losses else 0.0

    # Consecutive losses streak
    max_streak = 0
    current_streak = 0
    for o in outcomes:
        if o["hit_stop"]:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    return win_rate, loss_rate, exp_ret, avg_dd, sharpe, score, max_streak, ttw, ttl


def _find_optimal_levels(
    series: pd.Series,
    current_price: float,
    direction: str,
    base_entry: float,
    base_stop: float,
    base_target1: float,
    base_target2: float,
    n_sims: int = 50,
) -> Tuple[float, float, float]:
    """Grid-search entry/stop/target adjustments for optimal expected return."""
    ann_drift, ann_vol, _ = _calc_historical_params(series)
    ret = series.pct_change().dropna().values
    if len(ret) < 5:
        return 0.0, 0.0, 0.0

    best_score = -1e9
    best_adj = (0.0, 0.0, 0.0)

    # Grid: entry ±3%, stop ±2%, target ±3%
    entry_grid = np.linspace(-3.0, 1.0, 9)   # Mostly wait for pullback
    stop_grid = np.linspace(-1.0, 2.0, 7)    # Tighter or wider
    target_grid = np.linspace(-2.0, 2.0, 9)

    for e_adj in entry_grid:
        for s_adj in stop_grid:
            for t_adj in target_grid:
                if direction == "LONG":
                    entry = base_entry * (1 + e_adj / 100)
                    stop = base_stop * (1 + s_adj / 100)
                    t1 = base_target1 * (1 + t_adj / 100)
                    t2 = base_target2 * (1 + t_adj / 100)
                    # Sanity: stop must be below entry, target above
                    if stop >= entry * 0.995 or t1 <= entry * 1.005:
                        continue
                else:
                    entry = base_entry * (1 - e_adj / 100)
                    stop = base_stop * (1 - s_adj / 100)
                    t1 = base_target1 * (1 - t_adj / 100)
                    t2 = base_target2 * (1 - t_adj / 100)
                    if stop <= entry * 1.005 or t1 >= entry * 0.995:
                        continue

                outcomes = []
                for _ in range(n_sims):
                    path = _bootstrap_path(
                        current_price, ret, DEFAULT_HOLDING_DAYS,
                        ann_drift, ann_vol,
                        vol_perturb=VOL_PERTURBATION * 0.7,
                        drift_perturb=DRIFT_PERTURBATION * 0.7,
                    )
                    o = _simulate_single_setup(path, entry, stop, t1, t2, direction)
                    outcomes.append(o)

                _, _, exp_ret, _, sharpe, score, _, _, _ = _score_simulations(
                    outcomes, direction, current_rr=abs(t1 - entry) / max(abs(entry - stop), 0.001)
                )
                if score > best_score:
                    best_score = score
                    best_adj = (e_adj, s_adj, t_adj)

    return best_adj


# ═══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════

def run_simulation(
    ticker: str,
    prices: dict,
    setup: dict,
    options_data: Optional[dict] = None,
    n_simulations: int = DEFAULT_N_SIMULATIONS,
    holding_days: int = DEFAULT_HOLDING_DAYS,
    threshold: float = DEFAULT_THRESHOLD,
) -> SimResult:
    """
    Run full Monte Carlo simulation for one ticker setup.

    setup dict must contain:
        direction: "LONG" | "SHORT"
        entry: float
        stop: float
        target_1: float
        target_2: float
        rr: float (optional)
    """
    series = _safe_series(prices.get(ticker))
    if len(series) < 30:
        return SimResult(
            ticker=ticker, win_rate=0, loss_rate=0, exp_return_pct=0,
            avg_drawdown_pct=0, sharpe_like=0, robustness_score=0,
            optimal_entry_adj_pct=0, optimal_stop_adj_pct=0,
            optimal_target_adj_pct=0, time_to_win_days=0,
            time_to_loss_days=0, max_consecutive_losses=0,
            passes_filter=False, raw_metrics={"error": "insufficient_data"}
        )

    direction = setup.get("direction", "LONG")
    entry = float(setup.get("entry", series.iloc[-1]))
    stop = float(setup.get("stop", entry * 0.95))
    target1 = float(setup.get("target_1", entry * 1.05))
    target2 = float(setup.get("target_2", target1))
    current_rr = float(setup.get("rr", 0)) or abs(target1 - entry) / max(abs(entry - stop), 0.001)

    ann_drift, ann_vol, px = _calc_historical_params(series)
    ret = series.pct_change().dropna().values

    # ── Main simulation ──
    outcomes = []
    for _ in range(n_simulations):
        # Regime shift perturbation
        if random.random() < REGIME_SHIFT_PROB:
            # Flip direction bias temporarily
            sim_direction = "SHORT" if direction == "LONG" else "LONG"
        else:
            sim_direction = direction

        path = _bootstrap_path(px, ret, holding_days, ann_drift, ann_vol)
        o = _simulate_single_setup(path, entry, stop, target1, target2, sim_direction, options_data)
        outcomes.append(o)

    win_rate, loss_rate, exp_ret, avg_dd, sharpe, score, max_streak, ttw, ttl = _score_simulations(
        outcomes, direction, current_rr
    )

    # ── Optimal level search (lighter: 50 sims × grid) ──
    try:
        opt_e, opt_s, opt_t = _find_optimal_levels(
            series, px, direction, entry, stop, target1, target2, n_sims=50
        )
    except Exception as e:
        logger.warning(f"Optimal level search failed for {ticker}: {e}")
        opt_e, opt_s, opt_t = 0.0, 0.0, 0.0

    passes = score >= threshold and win_rate >= 50 and exp_ret > 0

    return SimResult(
        ticker=ticker,
        win_rate=round(win_rate, 1),
        loss_rate=round(loss_rate, 1),
        exp_return_pct=round(exp_ret, 2),
        avg_drawdown_pct=round(avg_dd, 2),
        sharpe_like=round(sharpe, 2),
        robustness_score=round(score, 1),
        optimal_entry_adj_pct=round(opt_e, 2),
        optimal_stop_adj_pct=round(opt_s, 2),
        optimal_target_adj_pct=round(opt_t, 2),
        time_to_win_days=round(ttw, 1),
        time_to_loss_days=round(ttl, 1),
        max_consecutive_losses=max_streak,
        passes_filter=passes,
        raw_metrics={
            "n_simulations": n_simulations,
            "holding_days": holding_days,
            "ann_drift": round(ann_drift, 4),
            "ann_vol": round(ann_vol, 4),
            "current_rr": round(current_rr, 2),
            "outcome_distribution": {
                "wins": len([o for o in outcomes if o["hit_target"]]),
                "losses": len([o for o in outcomes if o["hit_stop"]]),
                "neutrals": len([o for o in outcomes if not o["hit_target"] and not o["hit_stop"]]),
            }
        }
    )


def run_simulation_batch(
    tickers: List[str],
    prices: dict,
    setups: Dict[str, dict],
    options_map: Optional[Dict[str, dict]] = None,
    n_simulations: int = DEFAULT_N_SIMULATIONS,
    threshold: float = DEFAULT_THRESHOLD,
) -> Dict[str, SimResult]:
    """Batch simulation for multiple tickers. Returns {ticker: SimResult}."""
    results = {}
    total = len(tickers)
    for i, ticker in enumerate(tickers):
        setup = setups.get(ticker, {})
        if not setup or not setup.get("entry"):
            continue
        opts = (options_map or {}).get(ticker)
        try:
            res = run_simulation(
                ticker, prices, setup,
                options_data=opts,
                n_simulations=n_simulations,
                threshold=threshold,
            )
            results[ticker] = res
        except Exception as e:
            logger.warning(f"Simulation failed for {ticker}: {e}")
            results[ticker] = SimResult(
                ticker=ticker, win_rate=0, loss_rate=0, exp_return_pct=0,
                avg_drawdown_pct=0, sharpe_like=0, robustness_score=0,
                optimal_entry_adj_pct=0, optimal_stop_adj_pct=0,
                optimal_target_adj_pct=0, time_to_win_days=0,
                time_to_loss_days=0, max_consecutive_losses=0,
                passes_filter=False, raw_metrics={"error": str(e)}
            )
        if (i + 1) % 10 == 0 or i == total - 1:
            logger.info(f"Simulation progress: {i+1}/{total}")
    return results


def filter_by_simulation(
    rows: List[dict],
    sim_results: Dict[str, SimResult],
    threshold: float = DEFAULT_THRESHOLD,
    require_pass: bool = True,
) -> List[dict]:
    """Attach simulation data to rows and optionally filter."""
    enriched = []
    for row in rows:
        ticker = row.get("ticker", "")
        sim = sim_results.get(ticker)
        if sim:
            row["simulation"] = {
                "win_rate": sim.win_rate,
                "exp_return_pct": sim.exp_return_pct,
                "avg_drawdown_pct": sim.avg_drawdown_pct,
                "sharpe_like": sim.sharpe_like,
                "robustness_score": sim.robustness_score,
                "optimal_entry_adj_pct": sim.optimal_entry_adj_pct,
                "optimal_stop_adj_pct": sim.optimal_stop_adj_pct,
                "optimal_target_adj_pct": sim.optimal_target_adj_pct,
                "time_to_win_days": sim.time_to_win_days,
                "time_to_loss_days": sim.time_to_loss_days,
                "max_consecutive_losses": sim.max_consecutive_losses,
                "passes_filter": sim.passes_filter,
            }
            # Apply optimal adjustments to the row
            if sim.optimal_entry_adj_pct != 0:
                if row.get("entry"):
                    row["entry"] = round(row["entry"] * (1 + sim.optimal_entry_adj_pct / 100), 4)
            if sim.optimal_stop_adj_pct != 0:
                if row.get("stop"):
                    row["stop"] = round(row["stop"] * (1 + sim.optimal_stop_adj_pct / 100), 4)
            if sim.optimal_target_adj_pct != 0:
                if row.get("target_1"):
                    row["target_1"] = round(row["target_1"] * (1 + sim.optimal_target_adj_pct / 100), 4)
                if row.get("target_2"):
                    row["target_2"] = round(row["target_2"] * (1 + sim.optimal_target_adj_pct / 100), 4)
            # Recalculate RR after adjustments
            if row.get("entry") and row.get("stop") and row.get("target_1"):
                risk = abs(row["entry"] - row["stop"])
                reward = abs(row["target_1"] - row["entry"])
                row["rr"] = round(reward / max(risk, 0.001), 2)
        else:
            row["simulation"] = None

        if require_pass and sim and not sim.passes_filter:
            continue
        enriched.append(row)
    return enriched


def get_simulation_summary(sim_results: Dict[str, SimResult]) -> dict:
    """Aggregate stats across all simulations."""
    passed = [s for s in sim_results.values() if s.passes_filter]
    failed = [s for s in sim_results.values() if not s.passes_filter]
    if not passed:
        return {"total": len(sim_results), "passed": 0, "failed": len(failed), "avg_score": 0}
    scores = [s.robustness_score for s in passed]
    return {
        "total": len(sim_results),
        "passed": len(passed),
        "failed": len(failed),
        "avg_score": round(float(np.mean(scores)), 1),
        "top_score": round(float(np.max(scores)), 1),
        "avg_win_rate": round(float(np.mean([s.win_rate for s in passed])), 1),
        "avg_exp_return": round(float(np.mean([s.exp_return_pct for s in passed])), 2),
    }
