"""systemic_ts_test.py — test the SYSTEMIC signal concepts on 140y real macro data, with per-era
regime breakdown (the audits' "edge persistence across regimes" priority). Non-overlapping at each
horizon for clean p-values; no-lookahead (expanding/trailing stats only). These are the concepts
underlying the systemic engines (valuation-room, panic-bottom, dollar-hub, real-rate, trend) tested
on the data actually available — not the full multi-feed engines. Whatever the IC is, it prints.
"""
from __future__ import annotations
import sys, os, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from scipy.stats import spearmanr

df = pd.read_parquet(os.path.join("research", "macro_panel.parquet")).sort_index()
spx = df["spx"].astype(float)

ERAS = [("1881-1949", "1881", "1949"), ("1950-1999", "1950", "1999"), ("2000-2023", "2000", "2023")]


def fwd_ret(series, i, H):
    if i + H < len(series) and series.iloc[i] and series.iloc[i] > 0:
        return series.iloc[i + H] / series.iloc[i] - 1.0
    return np.nan


def build(sig_fn, target, H, expect):
    """Return list of (date, signal, fwd_return) with no-lookahead, non-overlapping at horizon H."""
    rows, i = [], 24
    while i + H < len(df):
        s = sig_fn(i)
        f = fwd_ret(target, i, H)
        if s is not None and np.isfinite(s) and np.isfinite(f):
            rows.append((df.index[i], s, f))
        i += H
    return rows


def ic_of(rows):
    if len(rows) < 8:
        return None, None, len(rows)
    xs = [r[1] for r in rows]; ys = [r[2] for r in rows]
    ic, p = spearmanr(xs, ys)
    return ic, p, len(rows)


# ── signal definitions (no-lookahead: only data ≤ i) ──
def cape_pct(i):
    c = df["cape"].iloc[:i + 1].dropna()
    return float((c.rank(pct=True)).iloc[-1]) if len(c) > 60 else None   # expanding percentile

def drawdown(i):
    s = spx.iloc[:i + 1]
    peak = s.rolling(24, min_periods=12).max().iloc[-1]
    return float(s.iloc[-1] / peak - 1.0) if peak and peak > 0 else None  # 0=at high, −0.3=deep

def dxy_chg(i):
    d = df["dxy"].iloc[:i + 1].dropna()
    return float(d.iloc[-1] / d.iloc[-4] - 1.0) if len(d) >= 4 else None   # 3m dollar change

def real_rate(i):
    r10 = df["rate10"].iloc[:i + 1].dropna(); infl = df["cpi_yoy"].iloc[:i + 1].dropna()
    if len(r10) and len(infl):
        return float(r10.iloc[-1] - infl.iloc[-1])
    return None

def trend12(i):
    s = spx.iloc[:i + 1]
    return float(s.iloc[-1] / s.iloc[-13] - 1.0) if len(s) >= 13 else None


# name, signal_fn, target_series, horizon, economic expectation
TESTS = [
    ("valuation_room: CAPE%→SPX",   cape_pct,  spx,         36, "− (expensive→low fwd)"),
    ("panic_bottom: drawdown→SPX",  drawdown,  spx,          6, "− (deeper DD→higher fwd)"),
    ("dollar_hub: ΔDXY→gold",       dxy_chg,   df["gold"],   3, "− (USD up→gold down)"),
    ("dollar_hub: ΔDXY→oil",        dxy_chg,   df["oil"],    3, "− (USD up→oil down)"),
    ("real_rate→gold",              real_rate, df["gold"],  12, "− (high real rate→gold down)"),
    ("trend_persist: 12m→SPX",      trend12,   spx,          3, "+ (uptrend persists)"),
]

print(f"macro panel {spx.index[0].date()}→{spx.index[-1].date()} · non-overlapping, no-lookahead\n")
print(f"{'signal':<30}{'H':>4}{'IC(full)':>10}{'p':>8}{'n':>5}   {'per-era IC (81-49 / 50-99 / 00-23)':<34}{'expect':<22}")
print("-" * 132)
for name, fn, tgt, H, exp in TESTS:
    rows = build(fn, tgt, H, exp)
    ic, p, n = ic_of(rows)
    if ic is None:
        print(f"{name:<30}{H:>4}   insufficient data ({n})"); continue
    # per-era
    era_str = []
    for lbl, a, b in ERAS:
        er = [r for r in rows if str(a) <= str(r[0].year) <= str(b)]
        eic, _, en = ic_of(er)
        era_str.append(f"{eic:+.2f}({en})" if eic is not None else "  —  ")
    flag = "✅" if p < 0.05 else ("🟡" if p < 0.15 else "❌")
    consistent = "◆" if all(("+" in e if "+" in exp else "-" in e) for e in era_str if "—" not in e) else " "
    print(f"{name:<30}{H:>4}{ic:>10.3f}{p:>8.3f}{n:>5}   {' / '.join(era_str):<34}{exp:<22} {flag}{consistent}")

print("\n✅ p<0.05  🟡 p<0.15  ❌ n.s.   ◆ = sign consistent across all 3 eras (regime-robust)")
print("Testing signal CONCEPTS on available macro series, not the full multi-feed engines.")
