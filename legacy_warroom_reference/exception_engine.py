"""exception_engine.py — the Reality-Divergence / Root-Cause engine, built REAL on data.

Edward's ask (the thing to figure out): when a thesis says "regime R -> asset A moves direction D"
but reality does the OPPOSITE, the system must find WHY, by data, and rank the causes with evidence
strength — never stay silent, never fabricate a story. This is the "Exception Engine" the audits
kept naming but never built.

WORKED EXAMPLE = Edward's own case: "Quad 3 -> long gold, but gold fell — why?"
The causal chain behind the law: growth-down + inflation-up  ==>  real yields fall  ==>  gold rises.
So the testable law on data is: GOLD RISES WHEN REAL YIELDS FALL.

Four steps (this structure generalizes to crash meter, tickers, bottleneck — each needs its own data):
  1. FALSIFY   — does the law even hold on data? (IC, win-rate, walk-forward). No hardcoded verdict.
  2. ISOLATE   — find the exceptions: months where the law's precondition held but the asset moved against it.
  3. ATTRIBUTE — for those exceptions, decompose the move onto the drivers we HAVE, ranked, with evidence strength.
  4. COVERAGE  — state honestly which candidate causes are NOT in the data (so the attribution is known-partial).

Run offline (no live feeds): python exception_engine.py
"""
from __future__ import annotations
import os, warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
try:
    from scipy import stats
    _SP = True
except Exception:
    _SP = False

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "research")


def _spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    if m.sum() < 10:
        return float("nan"), float("nan")
    if _SP:
        r, p = stats.spearmanr(x[m], y[m]); return float(r), float(p)
    xr = pd.Series(x[m]).rank(); yr = pd.Series(y[m]).rank()
    return float(np.corrcoef(xr, yr)[0, 1]), float("nan")


def load():
    mp = pd.read_parquet(os.path.join(RES, "macro_panel.parquet"))
    # DATA-INTEGRITY FIX: gold was PEGGED (~$35) until the gold window closed Aug-1971. Pre-1971 gold
    # returns are ~0 by construction and would dilute every statistic. Restrict to the floating era.
    mp = mp[mp.index >= "1971-09-01"]
    d = pd.DataFrame(index=mp.index)
    d["gold_ret"] = mp["gold"].pct_change()
    d["real_yield"] = mp["rate10"] - mp["cpi_yoy"]          # EX-POST real yield proxy (nominal 10y - trailing CPI)
    d["d_real_yield"] = d["real_yield"].diff()
    d["d_dollar"] = mp["dxy"].pct_change()
    d["d_cpi"] = mp["cpi_yoy"].diff()
    d["oil_ret"] = mp["oil"].pct_change()
    return d


def step1_falsify(d):
    print("═══ STEP 1 — FALSIFY THE LAW: 'gold rises when real yields fall' ═══")
    sub = d.dropna(subset=["gold_ret", "d_real_yield"])
    ic, p = _spearman(sub["d_real_yield"], sub["gold_ret"])          # expect NEGATIVE (yield down -> gold up)
    falling = sub[sub["d_real_yield"] < 0]; rising = sub[sub["d_real_yield"] > 0]
    wr_fall = float((falling["gold_ret"] > 0).mean())
    med_fall = float(falling["gold_ret"].median()); med_rise = float(rising["gold_ret"].median())
    mid = len(sub) // 2
    ic_e, _ = _spearman(sub["d_real_yield"].iloc[:mid], sub["gold_ret"].iloc[:mid])
    ic_l, _ = _spearman(sub["d_real_yield"].iloc[mid:], sub["gold_ret"].iloc[mid:])
    print(f"  sample: {len(sub)} months ({sub.index.min():%Y-%m} → {sub.index.max():%Y-%m})")
    print(f"  IC(Δreal_yield → gold) = {ic:+.3f}  (p={p:.4f})   [law predicts NEGATIVE]")
    print(f"  walk-forward IC: early {ic_e:+.3f} | late {ic_l:+.3f}   (sign stable? {'yes' if ic_e*ic_l>0 else 'NO — fragile'})")
    print(f"  gold win-rate when real yield FELL: {wr_fall:.0%}   (median gold {med_fall:+.2%} vs {med_rise:+.2%} when yield rose)")
    holds = ic < -0.03 and ic_e * ic_l > 0
    print(f"  VERDICT: the law {'HOLDS (directionally, on data)' if holds else 'is WEAK/CONDITIONAL — do not treat as deterministic'}.")
    print(f"  → gold rising when real yields fall is a {wr_fall:.0%} tendency, NOT a certainty. The other {1-wr_fall:.0%} is what Step 2/3 explains.\n")
    return sub


def step2_isolate(sub):
    print("═══ STEP 2 — ISOLATE THE EXCEPTIONS (the 'Quad 3 but gold fell' months) ═══")
    precond = sub[sub["d_real_yield"] < 0]                            # law says: gold should be UP
    exceptions = precond[precond["gold_ret"] < 0]                    # reality: gold fell
    frac = len(exceptions) / max(len(precond), 1)
    print(f"  law precondition met (real yield fell): {len(precond)} months")
    print(f"  EXCEPTIONS (gold fell anyway): {len(exceptions)} months  = {frac:.0%} of the time the law failed")
    print(f"  → the system must NOT say 'gold up' with confidence in these; it must ask WHY. That is Step 3.\n")
    return exceptions


def step3_attribute(d, exceptions):
    print("═══ STEP 3 — ROOT-CAUSE ATTRIBUTION (why gold fell, by data, RANKED) ═══")
    drivers = ["d_real_yield", "d_dollar", "d_cpi", "oil_ret"]
    fit = d.dropna(subset=["gold_ret"] + drivers)                    # attribution period = where ALL drivers exist (DXY ~1971+)
    if len(fit) < 40:
        print("  insufficient overlapping driver history for attribution."); return
    Z = (fit[drivers] - fit[drivers].mean()) / fit[drivers].std()    # standardize so contributions are comparable
    y = (fit["gold_ret"] - fit["gold_ret"].mean()) / fit["gold_ret"].std()
    X = np.column_stack([np.ones(len(Z)), Z.values])
    beta, *_ = np.linalg.lstsq(X, y.values, rcond=None)              # standardized betas
    b = dict(zip(drivers, beta[1:]))
    print(f"  standardized betas (gold return sensitivity), fit on {len(fit)} months ({fit.index.min():%Y-%m}→{fit.index.max():%Y-%m}):")
    label = {"d_real_yield": "real-yield rise", "d_dollar": "dollar rise", "d_cpi": "inflation rise", "oil_ret": "oil rise"}
    for k in drivers:
        print(f"    {label[k]:18s} β={b[k]:+.3f}  ({'headwind' if b[k]<0 else 'tailwind'} for gold)")
    exc = exceptions.dropna(subset=drivers)
    if len(exc) < 5:
        print("\n  (too few exception months with full driver data for a stable attribution — need the missing feeds below.)\n"); return
    Ze = (exc[drivers] - fit[drivers].mean()) / fit[drivers].std()
    contrib = Ze.values * beta[1:]                                    # per-month, per-driver contribution to gold's move
    signed = contrib.mean(axis=0)                                     # avg signed contribution across exceptions
    print(f"\n  across {len(exc)} exception months (gold fell despite falling real yields), avg contribution per driver:")
    order = np.argsort(signed)                                        # most-negative (biggest drag) first
    for i in order:
        consistency = float((contrib[:, i] < 0).mean())
        role = "DRAG (pulled gold down)" if signed[i] < 0 else "tailwind (was pushing gold UP, but got overwhelmed)"
        grade = "STRONG" if consistency > 0.66 else "MODERATE" if consistency > 0.5 else "WEAK"
        gtag = f" → evidence {grade}" if signed[i] < 0 else ""
        print(f"    • {label[drivers[i]]:18s} {signed[i]:+.3f}  {role}{gtag}")
    top = label[drivers[order[0]]]
    print(f"\n  ANSWER (by data): when the gold↔real-yield law failed, the dominant cause was «{top}» —")
    print(f"  the real-yield tailwind was real but the {top} overwhelmed it. That is the 'why', ranked, not 'model failed'.\n")


def step4_coverage():
    print("═══ STEP 4 — COVERAGE (what's NOT in the data — attribution is known-partial) ═══")
    have = ["real yield (ex-post proxy: 10y − trailing CPI)", "dollar (DXY)", "inflation (CPI YoY)", "oil"]
    missing = ["China / EM central-bank reserve SALES (your exact example)", "GLD / gold-ETF fund flows",
               "COT net speculative positioning", "forced-liquidation / margin-call events", "TIPS real yield (vs the ex-post proxy)"]
    print("  IN the data (attributed above):"); [print(f"    ✓ {h}") for h in have]
    print("  NOT in the data (would sharpen/complete the attribution — wire these to close the gap):")
    [print(f"    ✗ {m}") for m in missing]
    print("\n  So the engine ALREADY answers 'why' with the drivers it has, and is HONEST that China-reserve-sales")
    print("  and ETF-flow legs are unmeasured here — exactly the seam to feed, not fake.\n")


if __name__ == "__main__":
    d = load()
    sub = step1_falsify(d)
    exc = step2_isolate(sub)
    step3_attribute(d, exc)
    step4_coverage()
    print("This is the Exception-Engine kernel, real & reproducible: python exception_engine.py")
    print("Same 4 steps apply to any thesis (crash>80 → crash? ticker BUY → up?) — each needs its own data + the")
    print("multiple-testing discipline in research_harness.py so scaling it doesn't become an overfitting factory.")
