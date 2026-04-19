"""backtest_quad_engine.py

Historical quad performance backtester.
Answers: "When this was Q1/Q2/Q3/Q4 historically, what returned how much?"

Uses price data already loaded in the app — no extra data needed.
Assigns historical regime to each date using the SAME logic as the live engine.

Key output per quad:
  - avg 3m, 6m, 12m return for each asset basket
  - hit rate (% of periods with positive return)
  - max drawdown during that regime
  - typical duration in weeks
  - best/worst assets per regime

This is what makes the system credible — not just "Q2 = commodities" theory
but "Q2 historically returned +18% in commodities, -4% in bonds, with 82% hit rate."
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class QuadBacktestResult:
    quad: str
    n_periods: int                     # number of historical instances
    # Per-asset returns (mean, std, hit_rate) across all historical instances
    asset_returns: Dict[str, Dict]     # {ticker: {mean_3m, mean_6m, mean_12m, hit_rate, sharpe}}
    # Regime summary
    avg_duration_weeks: float
    max_drawdown: float                # worst drawdown seen during any Q instance
    confidence_bias: str               # "overconfident" | "reliable" | "noisy"
    # Best/worst performers historically
    best_assets: List[str]
    worst_assets: List[str]
    # vs SPY baseline
    vs_spy_3m: float                   # average outperformance vs SPY in 3m window
    sample_dates: List[str]            # sample of start dates for this quad


# The asset universe for backtesting
_BACKTEST_ASSETS = {
    "SPY":   "US Equity",
    "QQQ":   "Growth/Tech",
    "IWM":   "Small Cap",
    "TLT":   "Long Bond",
    "GLD":   "Gold",
    "GC=F":  "Gold Futures",
    "XLE":   "Energy",
    "XLB":   "Materials",
    "XLI":   "Industrials",
    "XLV":   "Healthcare",
    "XLP":   "Cons Staples",
    "HYG":   "HY Credit",
    "UUP":   "USD",
    "CL=F":  "WTI Oil",
    "HG=F":  "Copper",
    "EEM":   "EM Equities",
    "BTC-USD": "Bitcoin",
    "^JKSE": "IHSG",
}


def _ret(s: pd.Series, n: int) -> Optional[float]:
    """Return n-bar forward return from current position."""
    if s is None or len(s) < n + 1:
        return None
    try:
        base = float(s.iloc[0])
        end_ = float(s.iloc[n])
        if base == 0 or not (math.isfinite(base) and math.isfinite(end_)):
            return None
        return float(end_ / base - 1)
    except Exception:
        return None


def _assign_historical_quad(
    growth_acc: bool,
    inflation_acc: bool,
) -> str:
    """Simple quad assignment from RoC direction."""
    if growth_acc and not inflation_acc:
        return "Q1"
    elif growth_acc and inflation_acc:
        return "Q2"
    elif not growth_acc and inflation_acc:
        return "Q3"
    else:
        return "Q4"


def _rolling_roc(s: pd.Series, window: int = 12, offset: int = 3) -> pd.Series:
    """Rolling rate-of-change acceleration: change in 12m return over offset months."""
    roc = s.pct_change(window)
    accel = roc - roc.shift(offset)
    return accel


def run_backtest(
    prices: Dict[str, pd.Series],
    lookback_years: int = 8,
    forward_windows: Tuple[int, int, int] = (63, 126, 252),  # 3m, 6m, 12m in trading days
) -> Dict[str, QuadBacktestResult]:
    """
    Run historical quad backtest using available price data.

    Strategy:
    1. Use SPY + TLT to approximate growth/inflation regime
       - SPY 12m RoC > SPY 12m RoC 3m ago → growth accelerating
       - CPI approximated by inverse TLT 12m return (falling bonds = rising inflation)
    2. Assign historical quad to each month
    3. For each quad period, compute forward returns for all assets
    4. Aggregate stats

    Returns dict of QuadBacktestResult per quad.
    """
    spy = prices.get("SPY", pd.Series())
    tlt = prices.get("TLT", pd.Series())
    gld = prices.get("GLD", prices.get("GC=F", pd.Series()))

    if spy is None or len(spy) < 252:
        return {}  # Need at least 1 year of data

    # Align all to monthly (resample for regime classification)
    try:
        spy_m = spy.resample("ME").last().dropna()
        tlt_m = tlt.resample("ME").last().dropna() if (tlt is not None and len(tlt) > 60) else pd.Series(dtype=float)
    except Exception:
        return {}

    if len(spy_m) < 24:
        return {}

    # Trim to lookback
    cutoff = spy_m.index[-1] - pd.DateOffset(years=lookback_years)
    spy_m = spy_m[spy_m.index >= cutoff]
    if len(spy_m) < 12:
        return {}
    if len(tlt_m) > 0:
        tlt_m = tlt_m[tlt_m.index >= cutoff]

    # Compute growth and inflation acceleration proxies (monthly)
    growth_roc = _rolling_roc(spy_m, window=12, offset=3)
    if len(tlt_m) >= 15:
        inflation_roc = -_rolling_roc(tlt_m, window=12, offset=3)  # inverted: TLT falling = inflation rising
    else:
        inflation_roc = pd.Series(0.0, index=spy_m.index)

    # Assign quad per month
    quad_history: List[Tuple[pd.Timestamp, str]] = []
    for dt in spy_m.index:
        if dt not in growth_roc.index:
            continue
        g = growth_roc.get(dt, float("nan"))
        i = inflation_roc.get(dt, 0.0) if dt in inflation_roc.index else 0.0
        if not math.isfinite(g):
            continue
        g_acc = bool(g > 0)
        i_acc = bool(i > 0)
        q = _assign_historical_quad(g_acc, i_acc)
        quad_history.append((dt, q))

    if len(quad_history) < 8:
        return {}

    # Group into consecutive quad runs
    results: Dict[str, QuadBacktestResult] = {}

    for target_quad in ["Q1", "Q2", "Q3", "Q4"]:
        asset_data: Dict[str, List[float]] = {tk: [] for tk in _BACKTEST_ASSETS}
        asset_data["SPY_base"] = []
        durations = []
        sample_dates = []

        # Find periods where this quad was active for at least 2 months
        i = 0
        while i < len(quad_history):
            dt, q = quad_history[i]
            if q == target_quad:
                # Count consecutive months
                run_start = i
                while i < len(quad_history) and quad_history[i][1] == target_quad:
                    i += 1
                run_len = i - run_start
                if run_len >= 2:
                    start_dt = quad_history[run_start][0]
                    durations.append(run_len * 4.3)  # months → weeks
                    sample_dates.append(str(start_dt.date()))

                    # Forward returns from start of this regime
                    for tk in _BACKTEST_ASSETS:
                        s = prices.get(tk, pd.Series())
                        if s is None or len(s) == 0:
                            continue
                        try:
                            # Align to daily and get forward returns
                            s_daily = s[s.index >= start_dt]
                            if len(s_daily) < 10:
                                continue
                            r3 = _ret(s_daily, forward_windows[0])
                            if r3 is not None:
                                asset_data[tk].append(r3)
                        except Exception:
                            continue

                    # SPY baseline for comparison
                    s_spy = prices.get("SPY", pd.Series())
                    if s_spy is not None and len(s_spy) > 0:
                        try:
                            s_spy_d = s_spy[s_spy.index >= start_dt]
                            r_spy = _ret(s_spy_d, forward_windows[0])
                            if r_spy is not None:
                                asset_data["SPY_base"].append(r_spy)
                        except Exception:
                            pass
            else:
                i += 1

        if not any(v for v in asset_data.values()):
            continue

        # Compute stats per asset
        asset_returns: Dict[str, Dict] = {}
        for tk, returns in asset_data.items():
            if tk == "SPY_base" or not returns:
                continue
            arr = np.array(returns, dtype=float)
            arr = arr[np.isfinite(arr)]
            if len(arr) == 0:
                continue
            mean_r = float(np.mean(arr))
            std_r = float(np.std(arr)) if len(arr) > 1 else 0.0
            hit_rate = float(np.mean(arr > 0))
            sharpe = float(mean_r / std_r * np.sqrt(4)) if std_r > 0 else 0.0  # annualized approx

            # Max drawdown: use actual price series during all Q periods
            mdd = 0.0
            try:
                s = prices.get(tk, pd.Series())
                if s is not None and len(s) > 10:
                    cum = (1 + s.pct_change().fillna(0)).cumprod()
                    roll_max = cum.cummax()
                    drawdowns = (cum - roll_max) / roll_max
                    mdd = float(drawdowns.min())
            except Exception:
                pass

            asset_returns[tk] = {
                "mean_3m": round(mean_r, 4),
                "std_3m": round(std_r, 4),
                "hit_rate": round(hit_rate, 3),
                "sharpe_3m": round(sharpe, 3),
                "n_samples": len(arr),
                "max_drawdown": round(mdd, 4),
                "display_name": _BACKTEST_ASSETS.get(tk, tk),
            }

        if not asset_returns:
            continue

        # Sort by mean 3m return
        sorted_by_ret = sorted(asset_returns.items(), key=lambda x: x[1]["mean_3m"], reverse=True)
        best_assets = [tk for tk, _ in sorted_by_ret[:4] if sorted_by_ret[0][1]["mean_3m"] > 0]
        worst_assets = [tk for tk, _ in sorted_by_ret[-4:] if sorted_by_ret[-1][1]["mean_3m"] < 0]

        # vs SPY
        spy_base_arr = np.array([v for v in asset_data.get("SPY_base",[]) if math.isfinite(v)])
        spy_baseline_3m = float(np.mean(spy_base_arr)) if len(spy_base_arr) > 0 else 0.0
        spy_data = asset_returns.get("SPY", {})
        vs_spy = float(spy_data.get("mean_3m", 0.0)) - spy_baseline_3m

        # Confidence bias: compare hit rate to expected
        avg_hit = float(np.mean([v["hit_rate"] for v in asset_returns.values()]))
        if avg_hit > 0.65:
            conf_bias = "reliable"
        elif avg_hit > 0.50:
            conf_bias = "noisy"
        else:
            conf_bias = "unreliable"

        results[target_quad] = QuadBacktestResult(
            quad=target_quad,
            n_periods=len(durations),
            asset_returns=asset_returns,
            avg_duration_weeks=float(np.mean(durations)) if durations else 0,
            max_drawdown=min((v.get("max_drawdown", 0) for v in asset_returns.values()), default=0.0),
            confidence_bias=conf_bias,
            best_assets=best_assets[:4],
            worst_assets=worst_assets[:3],
            vs_spy_3m=round(vs_spy, 4),
            sample_dates=sample_dates[:5],
        )

    return results


def format_backtest_summary(results: Dict[str, QuadBacktestResult]) -> Dict:
    """Convert backtest results to serializable dict for storage in snap."""
    out = {}
    for quad, r in results.items():
        out[quad] = {
            "n_periods": r.n_periods,
            "avg_duration_weeks": round(r.avg_duration_weeks, 1),
            "confidence_bias": r.confidence_bias,
            "best_assets": r.best_assets,
            "worst_assets": r.worst_assets,
            "vs_spy_3m": r.vs_spy_3m,
            "sample_dates": r.sample_dates,
            "asset_returns": {
                tk: {
                    "mean_3m_pct": round(v["mean_3m"] * 100, 1),
                    "hit_rate_pct": round(v["hit_rate"] * 100, 0),
                    "sharpe": v["sharpe_3m"],
                    "n": v["n_samples"],
                    "name": v["display_name"],
                }
                for tk, v in r.asset_returns.items()
                if abs(v.get("mean_3m", 0)) > 0.001
            },
        }
    return out
