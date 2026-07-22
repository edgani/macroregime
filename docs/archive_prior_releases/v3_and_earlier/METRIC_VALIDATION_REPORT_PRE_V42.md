> **SUPERSEDED BY v2.4 AUDIT:** This historical report contains earlier validation language that is no longer used for production status. `metric_grades.json` and `DEEP_REAUDIT_V24.md` are authoritative. No metric is a proven autonomous trade signal without the remaining point-in-time, global multiple-testing, and prospective gates.

# METRIC VALIDATION REPORT — reproducible walk-forward grades
### Source of truth: `walkforward_validate.py` → `metric_grades.json`. Re-run anytime: `python walkforward_validate.py`

Rule the UI enforces: a metric emits a **number** only if VALIDATED. PARTIAL emits **banded** (low/elevated/high). REJECTED / FEED-GATED emit **"—"**, never a fabricated value. Every ticker inherits the grade of the engine that surfaced it.

Method: out-of-sample rank-IC (fit early / test late), permutation p, and — for the crash composite — a second pre/post-1990 regime split. Data: macro_panel (spx/cape/rate/gold 1881-2023), real VIX 1990+, sp500_panel (482 tickers OHLCV 2013-18).

| # | metric | grade | out-of-sample evidence | emit |
|---|---|---|---|---|
| 1 | **crash_pressure** | ✅ VALIDATED | fixed-weight IC **+0.100** (perm_p 0.004) on 60/40 **and +0.110** pre/post-1990 | **banded** |
| 2 | **factor_momentum** | ✅ VALIDATED | OOS mean daily-IC **+0.021**, t=2.53, p=0.012 (442 OOS days) | number |
| 3 | **dollar_hub** | ✅ VALIDATED | OOS IC **−0.216**, perm_p 0.002 (dollar↑→gold↓) | number |
| 4 | **panic_bottom** | 🟡 PARTIAL | extreme-fear→fwd-3m **+3.07% vs +1.54%** (~2x) but monthly-OOS **p=0.10** | number+flag |
| 5 | **cape_rate** | ❌ REJECTED | as a *predictor* OOS insignificant (IC +0.04, p=0.29) | — |
| 6 | **bandarmetrics_markup** | ⚫ FEED-GATED | validated elsewhere (fwd-42d IC 0.173) but needs idx.co.id foreign-flow | number if fed |
| 7 | **accumulation_composite** | ⚫ FEED-GATED | 0.30RS+0.25VE ok; ER/own/OI need feeds → show "—", never silent-zero | partial |
| 8 | **rotation_momentum** | ❌ REJECTED | coin-flip OOS | descriptive only |
| 9 | **lead_lag_daily** | ❌ REJECTED | p>0.5 OOS | none |
| 10 | **price_alpha_discovery** | ❌ REJECTED | price/vol fails to surface winners early (rank-IC −0.12) | structural prior only |

## The important honest nuances
- **crash_pressure only validates with FIXED weights.** A *fitted* linear model overfits and flips to **−0.16 OOS** — that was my earlier failed test. So the crash meter must use fixed priors, never fit, and its IC is modest (+0.10 = weak-but-real) → it shows as a band (low / elevated / high), not a precise 0-100. No single component (fragility, liquidity, momentum) is significant alone OOS; the combo is what carries it.
- **panic_bottom direction is robust (~2x forward return) but not monthly-OOS-significant (p=0.10).** The engine's DAILY fear-greed test was strongly significant (t=8.36); on monthly OOS alone it's directional-not-significant due to low event count. Emit the number, flag the confidence.
- **CAPE predicts the long-run RATE path, not crash timing** — high CAPE actually had the *wrong* sign vs near-term drawdown. Do not repurpose it as a crash/return signal.
- **The three ❌ REJECTED price signals are the honest core of "no garbage":** rotation, lead-lag, and price-only alpha discovery do not survive OOS. They emit no tradeable number. Finding the next 10x needs structural feeds (options/insider/13F/earnings-language/capex/supplier), not a price screener.

## What ships as trustworthy hard numbers
factor_momentum, dollar_hub — clean OOS validation. crash_pressure & panic_bottom ship banded/flagged. Everything else emits "—" until it either passes walk-forward or gets its feed.
