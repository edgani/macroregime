> **SUPERSEDED BY v2.4 AUDIT:** This historical report contains earlier validation language that is no longer used for production status. `metric_grades.json` and `DEEP_REAUDIT_V24.md` are authoritative. No metric is a proven autonomous trade signal without the remaining point-in-time, global multiple-testing, and prospective gates.

# War Room OS — validation & research, how to run it yourself

Everything that produces a number is reproducible. Nothing is taken on faith.

## Two harnesses (run offline, no feeds/keys needed — they use bundled real data)

**1. Metric grades** — `python walkforward_validate.py`
Walk-forward (fit early / test late) + permutation on every OS metric. Writes `metric_grades.json`.
The app reads this: VALIDATED → emits a live number; PARTIAL → banded; REJECTED/FEED-GATED → "—".
Result: factor_momentum & dollar_hub VALIDATED clean; crash_pressure VALIDATED but banded (fixed
weights only — fitting overfits and dies OOS); panic_bottom PARTIAL; rotation/lead-lag/price-alpha
REJECTED; bandarmetrics/accumulation FEED-GATED.

**2. Disciplined factor research** — `python research_harness.py`
Anti-memorization hidden-metric search: anonymized (cross-sectional ranks, no ticker identity),
FDR + White's Reality Check, out-of-sample. Writes `research_results.json`.
Result: survivors = short-horizon microstructure (skew, 1wk/1mo reversal, illiquidity). Momentum
died; low-vol reversed sign in the 2016-18 regime. Reality-check p=0.0005 (real, not fluke).

## Why post-cutoff data is the only clean test
Both harnesses run on data inside my training window, so a "pass" cannot fully rule out memorization
(skill and memory are observationally equivalent on seen data). The only memorization-proof
validation is forward / post-Jan-2026 data. Every grade is flagged pending that. This is the rigorous
version of "forward testing."

## In the app
- Header flips green **v0.3 · LIVE** when real data loads (stays MOCK if the run failed).
- **Validation tab** shows the LIVE grade card recomputed from `walkforward_validate.py` — it overrides
  any stale hardcoded claim.
- Every metric elsewhere is grade-gated: no ungraded number renders.

## Design
Unchanged from warroom_os_COMPLETE — same layout, same tabs, same badge system. Only the honesty of
what each panel emits changed.
