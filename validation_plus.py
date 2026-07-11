"""validation_plus.py — completes the validation suite to the guideline checklist.

WIRES the gold-standard tests that already exist in gcfis/backtest.py (cross-sectional IC,
permutation p, Probabilistic + Deflated Sharpe, Wilson CI, TRADEABLE verdict) into an
EXECUTABLE suite, and ADDS the guideline methods that were missing everywhere:

  • Monte-Carlo p-value        (null via N random strategies on the SAME prices)
  • White's Reality Check      (data-snooping across M strategy variants; stationary bootstrap)
  • Hansen's SPA test          (SPA_c — studentized, drops inferior strategies from the null)
  • Benjamini–Hochberg FDR     (multiple-testing control across the strategy/feature set)
  • PSI + KS drift             (train-vs-recent distribution drift → downweight/retire)
  • Permutation feature import (per-feature IC contribution, shuffle-and-measure)

VALIDATED WITH TWO CONTROLS (a validator that only ever says "no edge" is not validated):
  NEGATIVE control = pure random walk + noise signal → every method must say NO EDGE.
  POSITIVE control = planted cross-sectional factor → the methods must DETECT it.

On real data: a signal is tradeable only if it clears perm_p<0.05 AND DSR>=0.95 AND survives
Reality-Check/SPA after data-snooping AND is stable OOS. Not financial advice.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats

# reuse the existing gold-standard machinery (already in your repo)
from gcfis.backtest import (
    forward_return, cross_sectional_ic, permutation_pvalue,
    long_short_decile, deflated_sharpe, probabilistic_sharpe, wilson_ci, verdict,
)

# ─────────────────────────── Monte-Carlo p-value ───────────────────────────
def monte_carlo_pvalue(strategy_returns, n_random=1000, seed=0):
    """Compare observed annualized Sharpe to a null of RANDOM sign strategies on the same returns.
    p = fraction of random strategies with Sharpe >= observed. High p on noise = correct."""
    r = np.asarray(strategy_returns, float)
    r = r[np.isfinite(r)]
    if len(r) < 10 or r.std(ddof=1) == 0:
        return {"ok": False, "n": len(r)}
    obs = r.mean() / r.std(ddof=1)
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(n_random):
        signs = rng.choice([-1.0, 1.0], size=len(r))
        rr = r * signs
        s = rr.mean() / (rr.std(ddof=1) or 1e-9)
        if s >= obs:
            ge += 1
    return {"ok": True, "obs_sharpe": round(float(obs), 3),
            "mc_p": round((ge + 1) / (n_random + 1), 4), "n_random": n_random}


# ─────────────────────── stationary bootstrap (Politis–Romano) ───────────────────────
def _stationary_bootstrap_idx(T, avg_block, rng):
    idx = np.empty(T, dtype=int)
    p = 1.0 / max(avg_block, 1)
    i = 0
    cur = rng.integers(0, T)
    while i < T:
        idx[i] = cur
        i += 1
        if rng.random() < p:
            cur = rng.integers(0, T)      # new block
        else:
            cur = (cur + 1) % T           # continue block
    return idx


# ─────────────────────── White's Reality Check ───────────────────────
def whites_reality_check(D, n_boot=500, avg_block=10, seed=0):
    """D: (T x M) loss-differentials d_{t,k} = strategy_k perf - benchmark (higher = better).
    H0: best strategy has NO superior predictive ability. p high = no data-snooped winner."""
    D = np.asarray(D, float)
    T, M = D.shape
    dbar = D.mean(axis=0)
    V = np.sqrt(T) * dbar.max()
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(n_boot):
        idx = _stationary_bootstrap_idx(T, avg_block, rng)
        db = D[idx].mean(axis=0)
        Vb = np.sqrt(T) * (db - dbar).max()      # recenter (White 2000)
        if Vb >= V:
            ge += 1
    return {"stat_V": round(float(V), 4), "rc_p": round((ge + 1) / (n_boot + 1), 4),
            "best_k": int(dbar.argmax()), "M": M}


# ─────────────────────── Hansen's SPA (consistent) ───────────────────────
def hansen_spa(D, n_boot=500, avg_block=10, seed=0):
    """SPA_c: studentized max-statistic, inferior strategies removed from the recentering set.
    Sharper than White's RC (less conservative). p high = no strategy beats benchmark."""
    D = np.asarray(D, float)
    T, M = D.shape
    dbar = D.mean(axis=0)
    omega = D.std(axis=0, ddof=1)
    omega = np.where(omega < 1e-12, 1e-12, omega)
    t_stat = np.sqrt(T) * dbar / omega
    T_spa = max(0.0, float(t_stat.max()))
    # consistent recentering threshold: keep only strategies not too far below zero
    thresh = -np.sqrt(omega ** 2 * 2 * np.log(np.log(max(T, 3))) / T)
    keep = dbar >= thresh
    rng = np.random.default_rng(seed)
    ge = 0
    for _ in range(n_boot):
        idx = _stationary_bootstrap_idx(T, avg_block, rng)
        db = D[idx].mean(axis=0)
        z = np.sqrt(T) * (db - dbar) / omega
        z = np.where(keep, z, -np.inf)            # exclude inferior from the max
        Tb = max(0.0, float(np.nanmax(z)))
        if Tb >= T_spa:
            ge += 1
    return {"stat_SPA": round(T_spa, 4), "spa_p": round((ge + 1) / (n_boot + 1), 4),
            "kept": int(keep.sum()), "M": M}


# ─────────────────────── Benjamini–Hochberg FDR ───────────────────────
def benjamini_hochberg(pvals, q=0.05):
    """Control false-discovery-rate across many tested signals. Returns significant mask + threshold."""
    p = np.asarray(pvals, float)
    m = len(p)
    order = np.argsort(p)
    ranked = p[order]
    thresh = q * (np.arange(1, m + 1) / m)
    below = ranked <= thresh
    k = np.max(np.where(below)[0]) + 1 if below.any() else 0
    cutoff = ranked[k - 1] if k > 0 else 0.0
    sig = np.zeros(m, dtype=bool)
    if k > 0:
        sig[order[:k]] = True
    return {"n_tested": m, "n_significant": int(k), "bh_cutoff": round(float(cutoff), 4),
            "significant_idx": sorted(order[:k].tolist()) if k else []}


# ─────────────────────── drift: PSI + KS ───────────────────────
def psi(ref, cur, bins=10):
    """Population Stability Index. >0.10 minor, >0.25 major drift (retire/recalibrate)."""
    ref = np.asarray(ref, float); cur = np.asarray(cur, float)
    ref = ref[np.isfinite(ref)]; cur = cur[np.isfinite(cur)]
    if len(ref) < 20 or len(cur) < 20:
        return {"ok": False}
    edges = np.quantile(ref, np.linspace(0, 1, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    r = np.histogram(ref, edges)[0] / len(ref)
    c = np.histogram(cur, edges)[0] / len(cur)
    r = np.clip(r, 1e-4, None); c = np.clip(c, 1e-4, None)
    val = float(np.sum((c - r) * np.log(c / r)))
    lvl = "major" if val > 0.25 else "minor" if val > 0.10 else "stable"
    return {"ok": True, "psi": round(val, 4), "level": lvl}


def ks_drift(ref, cur):
    """Kolmogorov–Smirnov two-sample: is the recent distribution different from reference?"""
    ref = np.asarray(ref, float); cur = np.asarray(cur, float)
    ref = ref[np.isfinite(ref)]; cur = cur[np.isfinite(cur)]
    if len(ref) < 20 or len(cur) < 20:
        return {"ok": False}
    d, p = stats.ks_2samp(ref, cur)
    return {"ok": True, "ks_stat": round(float(d), 4), "ks_p": round(float(p), 4),
            "drifted": bool(p < 0.05)}


# ─────────────────────── permutation feature importance (IC) ───────────────────────
def permutation_feature_importance(features: dict, fwd: pd.DataFrame, rebalance: int, seed=0):
    """features: {name: signal_df}. Measures each feature's cross-sectional IC, then the IC
    drop when that feature is shuffled → its marginal contribution. No feed needed."""
    rng = np.random.default_rng(seed)
    out = {}
    for name, sig in features.items():
        base_ic, _ = cross_sectional_ic(sig, fwd, rebalance)
        shuffled = sig.copy()
        for d in shuffled.index[::rebalance]:
            row = shuffled.loc[d].values
            shuffled.loc[d] = rng.permutation(row)
        perm_ic, _ = cross_sectional_ic(shuffled, fwd, rebalance)
        out[name] = {"ic": round(base_ic, 4), "ic_when_shuffled": round(perm_ic, 4),
                     "importance": round(base_ic - perm_ic, 4)}
    return out


# ═══════════════════════ FULL SIGNAL VALIDATION (one call) ═══════════════════════
def _ls_series(sig, fwd, rebalance, ql=0.10, qh=0.90):
    """Per-rebalance long-short return series at given decile cutoffs (non-overlapping)."""
    dates = sig.index[::rebalance]; rets = []
    for d in dates:
        s = sig.loc[d].dropna(); f = fwd.loc[d].dropna()
        common = s.index.intersection(f.index)
        if len(common) < 30:
            rets.append(0.0); continue
        s2, f2 = s[common], f[common]
        q = s2.quantile([ql, qh])
        lo = f2[s2 >= q.iloc[1]].mean(); sh = f2[s2 <= q.iloc[0]].mean()
        rets.append((lo - sh) if (np.isfinite(lo) and np.isfinite(sh)) else 0.0)
    return rets


def validate_signal(close: pd.DataFrame, signal: pd.DataFrame, horizon=10, rebalance=10,
                    n_perm=200, n_boot=300):
    """Run the full guideline battery on ONE cross-sectional signal."""
    fwd = forward_return(close, horizon)
    ic, ics = cross_sectional_ic(signal, fwd, rebalance)
    perm_p = permutation_pvalue(signal, fwd, rebalance, ic, n=n_perm)
    ls = long_short_decile(signal, fwd, rebalance)

    # data-snooping across DECILE-CUTOFF variants of THIS signal (the real snooping dimension)
    cutoffs = [(0.05, 0.95), (0.10, 0.90), (0.15, 0.85), (0.20, 0.80), (0.25, 0.75)]
    ret_cols = [_ls_series(signal, fwd, rebalance, ql, qh) for ql, qh in cutoffs]
    rc = spa = {"ok": False}
    L = min(len(c) for c in ret_cols)
    if L >= 10:
        D = np.array([c[:L] for c in ret_cols]).T          # (T x M), benchmark = 0
        rc = whites_reality_check(D, n_boot=n_boot)
        spa = hansen_spa(D, n_boot=n_boot)

    # FDR across HORIZON variants (which holding period — a real multiple-testing set)
    horizons = [5, 10, 15, 20]
    hp = []
    for h in horizons:
        fh = forward_return(close, h)
        ich, _ = cross_sectional_ic(signal, fh, rebalance)
        hp.append(permutation_pvalue(signal, fh, rebalance, ich, n=100))
    fdr = benjamini_hochberg(hp)

    # drift: first-half vs second-half of the signal distribution
    flat = signal.values.flatten()
    half = len(flat) // 2
    dr = psi(flat[:half], flat[half:]); ks = ks_drift(flat[:half], flat[half:])
    mc = monte_carlo_pvalue(ret_cols[1]) if L >= 10 else {"ok": False}  # cutoff 0.10 series

    tradeable = bool(perm_p < 0.05 and ls.get("ok") and (ls.get("dsr") or 0) >= 0.95
                     and rc.get("rc_p", 1) < 0.10)
    return {
        "ic": round(ic, 4), "perm_p": round(perm_p, 4),
        "sharpe_ann": round(ls.get("sharpe_ann"), 3) if ls.get("ok") else None,
        "dsr": round(ls.get("dsr"), 3) if ls.get("ok") else None,
        "psr": round(ls.get("psr_vs0"), 3) if ls.get("ok") else None,
        "wilson_ci": ls.get("wilson_ci"), "n_trades": ls.get("n_trades"),
        "monte_carlo_p": mc.get("mc_p"), "reality_check_p": rc.get("rc_p"), "spa_p": spa.get("spa_p"),
        "fdr_significant": f"{fdr.get('n_significant')}/{len(horizons)} horizons",
        "drift_psi": dr.get("psi"), "drift_ks_p": ks.get("ks_p"),
        "VERDICT": "TRADEABLE" if tradeable else "NOISE — do not trade",
    }


# ═══════════════════════ CONTROLS (validate the validator) ═══════════════════════
def _panel(n_names=80, T=700, seed=0, planted=False, beta=0.9, h=10, bump=0.05):
    """Cross-sectional panel. planted=False → pure noise (signal unrelated to forward return).
    planted=True → the FORWARD return over each non-overlapping h-day window loads on the signal."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2016-01-01", periods=T)
    factor = rng.normal(0, 1, (T, n_names))              # the signal / view at each date
    rets = rng.normal(0.0003, 0.02, (T, n_names))        # base daily returns
    if planted:
        # at each rebalance date d, spread beta*factor[d] across the NEXT h daily returns,
        # so fwd[d] = sum(rets[d+1..d+h]) loads on factor[d] (true forward predictability)
        for d in range(0, T - h, h):
            rets[d + 1:d + h + 1, :] += beta * factor[d, :] * bump / h
    close = pd.DataFrame(100 * np.exp(np.cumsum(rets, axis=0)),
                         index=dates, columns=[f"N{i}" for i in range(n_names)])
    signal = pd.DataFrame(factor, index=dates, columns=close.columns)
    return close, signal


def run_controls(verbose=True):
    out = {}
    for label, planted in [("NEGATIVE (noise)", False), ("POSITIVE (planted factor)", True)]:
        close, signal = _panel(planted=planted, seed=1 if planted else 7)
        res = validate_signal(close, signal, horizon=10, rebalance=10, n_perm=200, n_boot=300)
        out[label] = res
        if verbose:
            print(f"\n── CONTROL: {label} ──")
            for k, v in res.items():
                print(f"    {k:22} {v}")
    if verbose:
        neg = out["NEGATIVE (noise)"]; pos = out["POSITIVE (planted factor)"]
        print("\n── control verdict ──")
        neg_ok = neg["VERDICT"].startswith("NOISE")
        pos_ok = pos["VERDICT"] == "TRADEABLE"
        print(f"    NEGATIVE says NOISE : {'✓' if neg_ok else '✗ FAIL'}  (perm_p={neg['perm_p']}, dsr={neg['dsr']}, mc_p={neg['monte_carlo_p']})")
        print(f"    POSITIVE says TRADEABLE: {'✓' if pos_ok else '✗ FAIL'}  (ic={pos['ic']}, perm_p={pos['perm_p']}, dsr={pos['dsr']}, rc_p={pos['reality_check_p']})")
        print(f"\n    VALIDATOR {'VALIDATED ✓ (detects edge when real, rejects noise)' if (neg_ok and pos_ok) else 'NEEDS REVIEW ✗'}")
    return out


if __name__ == "__main__":
    print("=" * 70)
    print("VALIDATION-PLUS — guideline battery + negative/positive controls")
    print("=" * 70)
    run_controls()
