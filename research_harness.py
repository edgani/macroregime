"""
research_harness.py — the DISCIPLINED hidden-metric search.

Built in direct response to "LLMs that remember too much" (lookahead-via-memorization) and the
p-hacking trap. Instead of scanning thousands of random combinations, we test a MODEST set of
factor hypotheses that each carry a stated economic MECHANISM, and we apply three defenses:

  1. ANONYMIZATION — every factor is computed cross-sectionally as a within-date rank. The ticker
     identity never enters the signal, so "memory that AAPL ripped in 2020" cannot leak in.
  2. MULTIPLE-TESTING CORRECTION — because we test N factors, a raw p<0.05 is not enough. We apply
     Benjamini-Hochberg FDR AND White's Reality Check (bootstrap the best factor against the null of
     no predictability across the whole set).
  3. OUT-OF-SAMPLE — IC is measured only on the held-out tail.

Honest ceiling: this data (S&P 2013-18) is inside the model's training window, so even a "pass" here
is not memorization-proof. The ONLY clean test is post-training-cutoff (post-Jan-2026) data — every
result is therefore flagged pending a forward/post-cutoff confirmation.

Run:  python research_harness.py   → prints the card + writes research_results.json
"""
from __future__ import annotations
import json, os, numpy as np, pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "research")
FWD = 21            # forward horizon (trading days)
OOS_FRAC = 0.5      # hold out the second half
BOOT = 2000         # reality-check bootstraps


# Each factor: (name, mechanism, builder). Builder takes close & volume panels (dates × tickers)
# and returns a factor panel where HIGHER = predicted higher forward return.
def _factors(close: pd.DataFrame, vol: pd.DataFrame):
    ret = np.log(close).diff()
    rv60 = ret.rolling(60).std()
    F = {}
    F["mom_252_21"]   = ("underreaction to slow-diffusing news (12-1 momentum)",
                          close.shift(21) / close.shift(252) - 1.0)
    F["mom_126"]      = ("intermediate momentum / trend persistence",
                          close.pct_change(126))
    F["rev_5"]        = ("short-term overreaction & liquidity provision (1wk reversal)",
                          -close.pct_change(5))
    F["rev_21"]       = ("1-month mean reversion",
                          -close.pct_change(21))
    F["lowvol_60"]    = ("betting-against-beta: leverage-constrained buyers overpay for high-vol (Frazzini-Pedersen)",
                          -rv60)
    F["lowvol_120"]   = ("low-volatility anomaly, slower window",
                          -ret.rolling(120).std())
    F["vov_60"]       = ("vol-of-vol: unstable-regime names underperform (less-discussed)",
                          -rv60.rolling(60).std())
    F["accel"]        = ("momentum term-structure: accelerating trend (21d mom minus 63d mom)",
                          close.pct_change(21) - close.pct_change(63))
    F["range_loc"]    = ("effort/absorption: closing high-in-range = accumulation footprint (bandar mechanism, less-discussed)",
                          ((close - close.rolling(20).min()) / (close.rolling(20).max() - close.rolling(20).min())).rolling(10).mean())
    F["vol_trend_div"]= ("effort-result divergence: price up on FALLING volume = distribution, fade it (bandar mechanism)",
                          -(close.pct_change(20) * (vol.rolling(20).mean() / vol.rolling(60).mean() - 1.0)))
    F["maxret_21"]    = ("lottery / MAX effect: high max-daily-return names overpriced (Bali-Cakici-Whitelaw)",
                          -ret.rolling(21).max())
    F["illiq"]        = ("Amihud illiquidity premium: |ret|/dollar-vol",
                          (ret.abs() / (close * vol).replace(0, np.nan)).rolling(21).mean())
    F["skew_60"]      = ("idiosyncratic skewness preference: high positive skew overpriced (less-discussed)",
                          -ret.rolling(60).skew())
    F["dd_recover"]   = ("drawdown-recovery asymmetry: distance below 120d high, mean-reverting",
                          (close / close.rolling(120).max() - 1.0))
    return F


def _run():
    sp = pd.read_parquet(os.path.join(RES, "sp500_panel.parquet")).copy()
    sp["date"] = pd.to_datetime(sp["date"])
    close = sp.pivot_table(index="date", columns="Name", values="close").sort_index()
    vol = sp.pivot_table(index="date", columns="Name", values="volume").sort_index()
    keep = close.columns[close.notna().mean() > 0.9]
    close, vol = close[keep], vol[keep]
    fwd = np.log(close.shift(-FWD) / close)

    facs = _factors(close, vol)
    dates = close.index[260:-FWD - 1]
    split = dates[int(len(dates) * (1 - OOS_FRAC))]

    # per-factor OOS daily IC series (ANONYMIZED: cross-sectional ranks only)
    ic_series = {}
    for name, (_mech, panel) in facs.items():
        series = []
        idx = []
        for d in dates:
            if d < split:
                continue
            x = panel.loc[d].dropna(); y = fwd.loc[d].dropna()
            j = x.index.intersection(y.index)
            if len(j) > 30:
                r, _ = stats.spearmanr(x[j].rank(), y[j])   # rank both → identity-free
                series.append(r); idx.append(d)
        if series:
            ic_series[name] = pd.Series(series, index=idx)

    # per-factor stats
    rows = {}
    for name, s in ic_series.items():
        t, p = stats.ttest_1samp(s, 0.0)
        rows[name] = {"mech": facs[name][0], "mean_ic": float(s.mean()),
                      "t": float(t), "p_raw": float(p), "n_days": int(len(s))}

    # ── Benjamini-Hochberg FDR across the set ──
    names = list(rows.keys())
    ps = np.array([rows[n]["p_raw"] for n in names])
    order = np.argsort(ps); m = len(ps)
    bh_thresh = np.zeros(m)
    for rank, i in enumerate(order, start=1):
        bh_thresh[i] = ps[i] * m / rank
    # enforce monotonicity of BH-adjusted p
    adj = np.minimum.accumulate(bh_thresh[order][::-1])[::-1]
    for k, i in enumerate(order):
        rows[names[i]]["p_fdr"] = float(min(adj[k], 1.0))

    # ── White's Reality Check: is the BEST |mean IC| beyond the null of no predictability? ──
    # stack aligned OOS IC series, demean each (impose null), bootstrap the max mean.
    aligned = pd.DataFrame(ic_series).dropna()
    obs_best = aligned.mean().abs().max()
    demeaned = aligned - aligned.mean()
    rng = np.random.default_rng(0)
    n = len(demeaned); boot_max = np.empty(BOOT)
    vals = demeaned.values
    for b in range(BOOT):
        samp = vals[rng.integers(0, n, n)]
        boot_max[b] = np.abs(samp.mean(axis=0)).max()
    rc_p = float((np.sum(boot_max >= obs_best) + 1) / (BOOT + 1))

    return rows, rc_p, obs_best, str(split.date())


if __name__ == "__main__":
    rows, rc_p, obs_best, split = _run()
    ranked = sorted(rows.items(), key=lambda kv: kv[1]["mean_ic"], reverse=True)
    print("═════ DISCIPLINED FACTOR RESEARCH (anonymized, OOS, multiple-testing corrected) ═════")
    print(f"OOS from {split} · forward {FWD}d · {len(rows)} mechanism-tagged factors\n")
    print(f"{'factor':16s} {'OOS IC':>8s} {'t':>6s} {'p_raw':>8s} {'p_FDR':>8s}  verdict")
    for name, r in ranked:
        surv = "✅ survives FDR" if r["p_fdr"] < 0.05 and r["mean_ic"] > 0 else \
               ("· sig raw, dies on correction" if r["p_raw"] < 0.05 else "✗ noise")
        print(f"{name:16s} {r['mean_ic']:+8.4f} {r['t']:6.2f} {r['p_raw']:8.4f} {r['p_fdr']:8.4f}  {surv}")
    print(f"\nWhite's Reality Check: best |OOS IC| = {obs_best:.4f}, bootstrap p = {rc_p:.4f} "
          f"→ {'the best factor beats the multiple-testing null ✅' if rc_p < 0.05 else 'best factor is within multiple-testing noise ✗'}")
    n_surv = sum(1 for _, r in rows.items() if r["p_fdr"] < 0.05 and r["mean_ic"] > 0)
    print(f"\n{n_surv}/{len(rows)} factors survive FDR. Every survivor is still flagged PENDING a post-Jan-2026")
    print("forward confirmation — that is the only test memorization cannot fake.")
    out = {"split": split, "reality_check_p": rc_p, "best_abs_ic": obs_best,
           "factors": {n: r for n, r in rows.items()}}
    with open(os.path.join(HERE, "research_results.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("\nwrote research_results.json")
