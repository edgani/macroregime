# ChatGPT/Qwen AUDIT — VERIFIED AGAINST REAL CODE, THEN FIXED
Every claim checked against the actual source (not accepted on faith). Reproducible smoke tests pass; full pipeline runs end-to-end after all fixes.

## Context you should keep in mind
In your own transcript, ChatGPT admitted its quantitative numbers ("Sharpe −65%", "IC 0.02", "SHAP 80%", "Monte Carlo 18%") were **hallucinated** — it had no notebook, no dataset, no seed. So the *bug claims* (which are about your code and are checkable) are worth taking seriously; the *performance numbers* that motivated the EVOS redesign were confabulated. I verified the code claims; I did not import any of the fabricated metrics.

## Verified verdicts + fixes applied

| # | Claim | Verdict | Fix |
|---|---|---|---|
| 1 | **EV-negative trap** (`final_desk.py`) | ✅ REAL — no `ev>0` gate; tanh let conviction/surge drag a −EV trade to +desk_score | Added hard gate: `ev ≤ 0 → reject ("losing expectation — never emit")`. Verified: EV=−15 now rejected, EV=+5 still valid |
| 2 | **Squeeze blindspot** (`decision_stack.py`) | ✅ REAL — short returned `DISTRIBUTION_SHORT` before the squeeze check | Added squeeze override FIRST: short into SQUEEZE/short-covering → `REDUCE_AVOID`. Verified: short-in-squeeze → REDUCE_AVOID |
| 3 | **Q3 Gold blindspot** (`regime_meta.py`) | ✅ REAL — equity risk-off `W["long"]=0.20` crushed commodity/gold like tech | Decoupled real assets: commodity long-tilt floored when its own bottleneck/reflexivity is strong, not zeroed by the equity cycle. ⚠ floor is a labeled PRIOR pending regime-replay validation |
| 4 | **Hallucinated evidence strings** (`decision_stack.py`) | 🟡 PARTIAL — one was already filtered, two weren't | Removed both default strings → empty evidence now fails the ≥2-reason gate → correctly WATCH, never fabricated |
| 5 | **Crash-bottom ignores credit** (`crash_bottom.py`) | 🟡 MOSTLY FALSE — credit IS in pressure via fragility (0.22×), but durable-bottom classification didn't hard-gate it | Added `credit_not_frozen` gate: `fragility ≥ 55 → downgrade DURABLE_BOTTOM to LOCAL_BOUNCE_RISK` (VIX can calm while credit stays frozen in a margin cascade) |
| 6 | **tanh moonshot compression** (`final_desk.py`) | 🟡 REAL math, design tradeoff | NOT silently changed — swapping the transform changes every rank without validation. Proper fix = separate alpha/tactical lanes (bigger, needs validation). Flagged, not forced |
| 7 | **Whipsaw / change-centric z** (`market_drivers.py`) | ✅ REAL structurally — but my earlier stability test showed aggregate posture stable under ±10% | NOT silently changed — smoothing/level is a weight change that needs validation per your own standard. Flagged for the validation harness |
| 8 | **Single-catalyst rejection** (`final_desk.py`) | 🟡 REAL behavior, defensible — ≥2-reason gate cuts false positives | Left as-is; loosening is a tradeoff, not clearly correct |

## The honest split
Fixes 1–5 are either unambiguous safety/correctness bugs or economically-defensible structural decoupling — implemented and tested. Items 6–8 are **weight/behavior changes**, and changing weights without validation is exactly the failure mode your own framework (and your ChatGPT reviewer) warned against — so I flagged them for the validation harness instead of silently altering numbers. That distinction is the whole point: correctness bugs get fixed; unvalidated weight changes do not get smuggled in as "fixes."
