"""engine_ic_test.py — REAL, no-lookahead cross-sectional IC test of each engine.

For each rebalance date d: slice every ticker to trailing history ≤ d (NO future data),
compute each engine's scalar score as-of d, then Spearman-rank-correlate the cross-section
of scores against the forward H-day return (d → d+H). Aggregate = mean IC, IC-IR (=mean/std),
t-stat, % positive — exactly alphalens' IC summary. Momentum is included as a harness sanity check
against the bundled factor_ic.parquet. Nothing fabricated; whatever the IC is, it prints.
"""
from __future__ import annotations
import sys, os, warnings, time
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from scipy.stats import spearmanr

H = 21           # forward horizon (trading days)
STEP = 21        # rebalance every ~month
TRAIL = 504      # trailing window fed to each engine (2y) — captures all ≤252 rolling, no future data
MIN_HIST = 260   # need this much history before scoring
MIN_XS = 40      # min tickers in a cross-section to compute IC


def load_panel():
    df = pd.read_parquet(os.path.join("research", "sp500_panel.parquet"))
    df["date"] = pd.to_datetime(df["date"])
    out = {}
    for tk, g in df.groupby("Name"):
        g = g.sort_values("date").set_index("date")
        g = g[["open", "high", "low", "close", "volume"]].astype(float)
        if len(g) > MIN_HIST + H + 5:
            out[tk] = g
    return out


# ── scorers: each takes a ticker's trailing OHLCV (≤ d) + optional bench, returns a scalar or None ──
def score_momentum(tk, df, bench):
    c = df["close"]
    return float(c.iloc[-1] / c.iloc[-127] - 1.0) if len(c) >= 127 else None

def score_markup(tk, df, bench):
    from engines import bandarmetrics_engine as BM
    try:
        d2 = df.rename(columns={"open": "Open", "high": "High", "low": "Low",
                                "close": "Close", "volume": "Volume"})
        r = BM.compute(d2)
        mr = r.get("markup_readiness") or {}
        v = mr.get("readiness")
        return float(v) if v is not None else None
    except Exception:
        return None

def score_accumulation(tk, df, bench):
    from gcfis.engines.accumulation import run_accumulation
    try:
        r = run_accumulation(tk, df["close"], bench, volume=df["volume"])
        v = r.get("accumulation")
        return float(v) if v is not None else None
    except Exception:
        return None

def score_flow(tk, df, bench):
    from gcfis.engines.flow_type import run_flow_type
    try:
        r = run_flow_type(df["close"], volume=df["volume"])
        v = r.get("flow01")
        return float(v) if v is not None else None
    except Exception:
        return None

def score_reflexivity(tk, df, bench):
    from gcfis.engines.reflexivity import run_reflexivity
    try:
        r = run_reflexivity(df["close"], volume=df["volume"])
        v = r.get("reflexivity")
        return float(v) if (r.get("ok") and v is not None) else None
    except Exception:
        return None

SCORERS = {
    "momentum_126 (baseline)": score_momentum,
    "bandarmetrics_markup": score_markup,
    "accumulation": score_accumulation,
    "flow_type_flow01": score_flow,
    "reflexivity": score_reflexivity,
}


def run(engines=None, max_tickers=None):
    panel = load_panel()
    tickers = list(panel.keys())
    if max_tickers:
        tickers = tickers[:max_tickers]
    panel = {t: panel[t] for t in tickers}
    # equal-weight benchmark from the panel itself (each ticker normalized to 1, averaged) — a real
    # market proxy; sliced to ≤ d per rebalance so it carries no future data either.
    norm = pd.DataFrame({t: df["close"] / df["close"].iloc[0] for t, df in panel.items()})
    BENCH = norm.mean(axis=1).dropna()
    # common calendar = union of dates
    all_dates = sorted(set().union(*[set(df.index) for df in panel.values()]))
    all_dates = pd.DatetimeIndex(all_dates)
    reb_idx = range(MIN_HIST, len(all_dates) - H - 1, STEP)
    reb_dates = [all_dates[i] for i in reb_idx]
    engines = engines or list(SCORERS.keys())
    print(f"panel: {len(panel)} tickers | dates {all_dates[0].date()}→{all_dates[-1].date()} | "
          f"{len(reb_dates)} rebalances | H={H}d, trail={TRAIL}d\n")

    results = {}
    for name in engines:
        scorer = SCORERS[name]
        t0 = time.time()
        ics = []
        for d in reb_dates:
            scores, fwd = {}, {}
            di = all_dates.get_loc(d)
            d_fwd = all_dates[di + H]
            bench_sub = BENCH.loc[:d].iloc[-TRAIL:]
            for tk, df in panel.items():
                sub = df.loc[:d]
                if len(sub) < MIN_HIST:
                    continue
                sub = sub.iloc[-TRAIL:]                      # trailing window, no future data
                s = scorer(tk, sub, bench_sub)
                if s is None or not np.isfinite(s):
                    continue
                # forward return d → d+H (clean, no overlap with score data)
                try:
                    p0 = df["close"].asof(d); p1 = df["close"].asof(d_fwd)
                    if p0 and p1 and np.isfinite(p0) and np.isfinite(p1) and p0 > 0:
                        scores[tk] = s; fwd[tk] = p1 / p0 - 1.0
                except Exception:
                    continue
            common = [t for t in scores if t in fwd]
            if len(common) >= MIN_XS:
                sv = [scores[t] for t in common]; fv = [fwd[t] for t in common]
                if len(set(sv)) > 3:                         # need score variation
                    ic, _ = spearmanr(sv, fv)
                    if np.isfinite(ic):
                        ics.append(ic)
        ics = np.array(ics)
        if len(ics) >= 5:
            mean_ic = ics.mean(); ic_std = ics.std(ddof=1)
            ic_ir = mean_ic / ic_std if ic_std > 0 else 0.0
            t_stat = ic_ir * np.sqrt(len(ics))
            pct_pos = float((ics > 0).mean())
            results[name] = dict(mean_ic=mean_ic, ic_ir=ic_ir, t_stat=t_stat,
                                 pct_pos=pct_pos, n=len(ics), secs=time.time() - t0)
        else:
            results[name] = dict(mean_ic=np.nan, n=len(ics), secs=time.time() - t0)
    return results


def report(results):
    print(f"{'engine':<26}{'mean IC':>9}{'IC-IR':>8}{'t-stat':>8}{'%pos':>7}{'n':>5}{'sec':>6}")
    print("-" * 69)
    for name, r in results.items():
        if np.isnan(r.get("mean_ic", np.nan)):
            print(f"{name:<26}{'—':>9}{'':>8}{'':>8}{'':>7}{r['n']:>5}{r['secs']:>6.0f}")
            continue
        flag = "✅" if (abs(r["t_stat"]) > 2 and abs(r["mean_ic"]) > 0.02) else ("🟡" if abs(r["t_stat"]) > 1.5 else "❌")
        print(f"{name:<26}{r['mean_ic']:>9.4f}{r['ic_ir']:>8.3f}{r['t_stat']:>8.2f}"
              f"{r['pct_pos']*100:>6.0f}%{r['n']:>5}{r['secs']:>6.0f}  {flag}")
    print("\n✅ IC≠0 & |t|>2   🟡 |t|>1.5 (weak)   ❌ indistinguishable from noise")
    print("Caveats: survivor-biased S&P panel, single regime ~2013–2018, long-only cross-section.")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--engines", nargs="*", default=None)
    ap.add_argument("--max_tickers", type=int, default=None)
    a = ap.parse_args()
    report(run(engines=a.engines, max_tickers=a.max_tickers))
