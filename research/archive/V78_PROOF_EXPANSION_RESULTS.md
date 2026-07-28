# War Room OS V7.8 — Proof Expansion Results

## Verdict

V7.8 is not a final proven trading system. It is a proof-expansion checkpoint that ran three bounded confirmatory families, promoted none of them, and hardened the exact data and prospective-evidence path required for a real ticker-level proof.

No gate was relaxed after results were opened. Every failed component remains at live decision weight `0.0`.

## 1. Cross-market time-series momentum

Five maintained aggregate series were tested: total TSMOM plus commodity, equity, fixed-income and FX sleeves. The post-publication validation period was 2013–2018 and the untouched lockbox was 2019–May 2026, with HAC/Newey–West inference, familywise correction, a 10 bps monthly hurdle, stability checks and reverse-sign controls.

Result: **0 of 5 promoted**.

The broad TSMOM series earned about **+0.3542% per month** in the lockbox, but its simultaneous lower bound after the 10 bps hurdle was **−0.6953% per month**. The aggregate point estimate therefore did not survive the frozen uncertainty gate. The other sleeves also failed the same exact promotion rule.

## 2. Cross-market SMA10 risk cap

The already-proven broad-US-equity monthly SMA10 risk-control claim was not copied blindly to other markets. Gold, oil and DXY were tested separately under one frozen protocol.

Result: **0 of 3 promoted**.

- **Gold:** lockbox drawdown and expected-shortfall improved, but the moving-block probability that both improved was **90.13%**, below the frozen 95% gate.
- **Oil:** lockbox drawdown improved by **29.44 percentage points** and expected shortfall improved materially, but annual return lagged the baseline by **4.70 percentage points**, beyond the allowed loss.
- **DXY:** the lockbox bootstrap probability was only **67.87%** and rolling drawdown robustness failed.

This is direct evidence that a rule proven for broad US equities cannot be generalized across markets merely because the formula is simple.

## 3. US 12% volatility-target exposure cap

A single fixed 12% annualized-volatility target was frozen before output. It used a 12-month realized-volatility estimate, monthly rebalance, one-month lag, no leverage and no shorting.

Result: **NOT PROMOTED**.

- Validation drawdown improvement: **4.20 percentage points**; bootstrap probability: **81.48%**.
- Lockbox drawdown improvement: **8.00 percentage points**; bootstrap probability: **92.14%**.
- Lockbox annual return difference: **−1.52 percentage points**.

It improved some risk metrics but failed the pre-registered minimum drawdown improvement and 95% bootstrap gates. It was not re-tuned after failure.

## What V7.8 added instead of faking a pass

1. A strict US point-in-time data contract requiring permanent security IDs, historical membership, corporate actions, explicit delisting status/returns, observation dates and availability timestamps.
2. A historical S&P 500 membership interval guard with a frozen source hash. It is explicitly a research cross-check, not official or sufficient proof.
3. A frozen three-candidate ticker protocol for the only modern archive-supported families: `SMILE_ONLY_PIT`, `SMILE_ANN_PIT`, and `SMILE_EXPECTATIONS_DIV_PIT`.
4. A new prospective forecast ledger that rejects stale/backfilled forecast creation **and** stale decision timestamps, plus a separate immutable outcome chain.
5. A no-auto-promotion rule: even 200 matured forecasts across four regimes only opens human proof review.

## Exact remaining blocker

A complete lawful survivor-bias-free ticker panel is not bundled. The final ticker proof requires permanent IDs, removed and delisted securities, corporate actions, historical membership, point-in-time option surfaces, estimates/revisions, borrow and actual execution costs. A current-constituent Yahoo-style panel cannot satisfy that requirement.

Until that panel passes the V7.8 data contract and the frozen ticker protocol is run, ticker, direction, accumulation, topping, entry, target, stop, timing and cross-market allocation remain zero-capital.
