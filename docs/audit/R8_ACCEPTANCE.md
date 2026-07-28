# R8 Acceptance — Extreme Winner/Loser Tournament (2026-07-29)

Checkpoint tag: PRE_R8_EXTREME_WINNER_TOURNAMENT. Base: R7.1 2605993 (pushed).

## Gate review (12 R8 gates)

| # | Gate | Status |
|---|---|---|
| 1 | Cohorts frozen before evaluation | PASS — R6 cohorts (2026-07-28) + prereg_r8.json frozen+hashed BEFORE any tournament run (hash bc4614e7…) |
| 2 | Survivor-safe universe verified | HONEST FAIL — universe is active-only; NOT survivor-safe; documented in R8_UNIVERSE_REPORT.md with exact missing feeds (CRSP delisting, Compustat, EDGAR PIT shares). Baseline numbers labelled biased-upward |
| 3 | SNDK/PLTR/SPXC not used for formula selection | PASS — excluded from ranker input (code-enforced), evaluation-only reports |
| 4 | All trials recorded | PASS — 2/2 baseline trials in hash-chained ledger; chain verified |
| 5 | False-lookalike controls exist | PARTIAL — FDR measured per decision date; exact matched controls DATA_GATED (needs PIT sector/cap/valuation), declared in prereg |
| 6 | PIT / available-at checks | PASS for baseline (price-only signal, 63d lag at decision date); causal families PIT feeds gated |
| 7 | Top-K results produced | PASS — K=10 and K=20, per-date + aggregate + regime buckets |
| 8 | Lead time + remaining return reported | PASS — mean lead 143d (K=10) / 154d (K=20); remaining return reported |
| 9 | Late detection not counted as early | PASS — early_detection_rule frozen in prereg; case reports compute lead from frozen date to crossing |
| 10 | Every family labelled | PASS — 2 causal families DATA_GATED (exact feeds), 1 baseline BASELINE_MEASUREMENT_NOT_ALPHA (weight 0) |
| 11 | No DATA_GATED family called successful | PASS — test-enforced; verdicts in ledger |
| 12 | Local = remote commit | PASS (see below) |

## Results (real data, 230 tickers, 2024-07-03..2026-07-28)

Baseline momentum Top-K (measurement-only bar for future causal families):
- K=10: Precision 0.46, Recall 0.12, lift 3.08 vs random, FDR 0.54, lead 143d
- K=20: Precision 0.34, Recall 0.18, lift 2.24, FDR 0.66, lead 154d
- Regime stability reported per half-year bucket in r8_tournament_results.json
- Survivor bias: numbers are an upper bound (R8_UNIVERSE_REPORT)

Case reports (frozen dates, PIT daily bars):
- SNDK: +100% crossed from all 3 frozen dates (lead 78/38/21d; MFE up to +5049%)
- PLTR: +100% crossed from all 3 frozen dates (lead 201/130/95d; MFE up to +857%)
- SPXC: never crossed +100% (MFE 68.6/45.9/21.2%) — negative case
- ALL verdicts: NOT_CAPTURED — no causal Top-K/projection/activation existed at those
  dates. No detection is claimed. This is the honest R8 outcome: the system today
  cannot capture extreme winners because the discovery families are DATA_GATED.

## Families rejected/gated

- extreme_winner_discovery_causal: DATA_GATED (sec_edgar_pit, consensus_estimates_pit,
  trendforce_contract_prices) — weight 0
- downside_short_detector_causal: DATA_GATED (PIT balance sheet/dilution/delisting) — weight 0
- baseline_momentum_topk: measured, weight 0, forbidden as alpha input

## Incidents (disclosed)

Trial ledger schema normalization: the first 2 R8 entries were appended with
non-canonical keys (params/metrics). They were migrated once to the canonical
schema (type/parameters/results/market/lockbox_touched/honest_limits) and the
hash chain recomputed; ledger.record now injects type by default. No trial
content was altered or removed; all 4 entries (2 R7 FX + 2 R8) verify.

## Tests

tests/test_r8_extreme_winners.py — 8 tests. Full suite: 200 passed, 2 slow-boot
skipped (verified separately), 1 warning.
