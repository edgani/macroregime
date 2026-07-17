"""macro_ts_test.py — time-series signal test on 140y REAL macro data (non-overlapping annual).

Higher power + many regimes than the cross-sectional large-cap panel. CAPE is the known-good anchor:
high CAPE should predict LOW forward returns (Shiller) → significant NEGATIVE IC. If the harness
finds that, it proves the method discriminates real signal from noise. CSD = the Critical-Slowing-Down
fragility primitive from change_core, tested as a market-timing signal. Non-overlapping 12m steps
avoid overlap-induced fake significance. No-lookahead: signals use only data ≤ t.
"""
from __future__ import annotations
import sys, os, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from scipy.stats import spearmanr

df = pd.read_parquet(os.path.join("research", "macro_panel.parquet")).sort_index()
spx = df["spx"].astype(float)
ret = spx.pct_change()
H = 12  # forward months

from gcfis.core.change_core import csd, robust_z

def sig_cape(t_idx):      # valuation level (expect NEG corr with fwd return)
    v = df["cape"].iloc[:t_idx + 1].dropna()
    return float(v.iloc[-1]) if len(v) > 24 else None

def sig_mom12(t_idx):     # 12m price momentum
    s = spx.iloc[:t_idx + 1]
    return float(s.iloc[-1] / s.iloc[-13] - 1.0) if len(s) >= 13 else None

def sig_csd(t_idx):       # Critical Slowing Down (rising AR1+var before breaks) — fragility primitive
    r = ret.iloc[:t_idx + 1].dropna()
    if len(r) < 70:
        return None
    c = csd(r, window=36)
    return float(c.iloc[-1]) if len(c.dropna()) else None

SIGS = {"CAPE (anchor, expect −)": sig_cape, "momentum_12m": sig_mom12, "CSD_fragility": sig_csd}


def ts_ic(sig_fn, start=60):
    xs, ys = [], []
    i = start
    while i + H < len(spx):                        # non-overlapping annual steps
        s = sig_fn(i)
        f = spx.iloc[i + H] / spx.iloc[i] - 1.0 if spx.iloc[i] > 0 else np.nan
        if s is not None and np.isfinite(s) and np.isfinite(f):
            xs.append(s); ys.append(f)
        i += H
    if len(xs) < 10:
        return None
    ic, p = spearmanr(xs, ys)
    return dict(ic=ic, p=p, n=len(xs))


print(f"macro panel: {spx.index[0].date()}→{spx.index[-1].date()} | {len(spx)} months | "
      f"non-overlapping {H}m fwd\n")
print(f"{'signal':<26}{'IC':>9}{'p-value':>10}{'n':>6}")
print("-" * 51)
for name, fn in SIGS.items():
    r = ts_ic(fn)
    if r is None:
        print(f"{name:<26}{'—':>9}"); continue
    flag = "✅" if r["p"] < 0.05 else ("🟡" if r["p"] < 0.15 else "❌")
    print(f"{name:<26}{r['ic']:>9.4f}{r['p']:>10.4f}{r['n']:>6}  {flag}")
print("\n✅ p<0.05  🟡 p<0.15  ❌ not significant")
print("If CAPE is significant & negative, the method works — so ❌ elsewhere = weak signal, not broken test.")
