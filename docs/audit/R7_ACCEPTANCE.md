# R7 Acceptance — Market-Specific Alpha Engines (2026-07-29)

Checkpoint tag: PRE_R7_MARKET_SPECIFIC_ALPHA. Base: R6 8eabd20 (pushed, verified).

## Deliverables (master prompt R7)

| # | Deliverable | Status | Evidence |
|---|---|---|---|
| 1 | Five market-specific alpha contracts | DONE | engines/alpha_{us,ihsg,crypto,commodities,fx}.py + data/research/prereg_r7.json (frozen 2026-07-28): exact claim, universe, target, horizon, baseline, costs, trial budget, lockbox per market |
| 2 | Frozen candidate-family registry | DONE | prereg_r7.json — us 12, ihsg 13, crypto 11, commodities 11, fx 11 families; family sets provably different across markets |
| 3 | Immutable trial ledger | DONE | data/research/trial_ledger.jsonl — SHA-256 hash chain, verified; all trials incl. failures kept |
| 4 | Formula registry | DONE | prereg formula_family fields; fx carry formula documented in engines/alpha_fx.py |
| 5 | Baseline registry | DONE | prereg baselines per market (spy/jci/btc_eth_ew/bcom/usd_cash + random_same_turnover) |
| 6 | Preliminary results | DONE (REAL, HONEST) | FX carry tournament, 2 trials on real FRED rates + real spot: n=22 monthly, ann +2.52%, vol 8.0%, Sharpe 0.31, maxDD -11.5%, hit 59%, excess vs equal-weight baseline ≈ +0.1% → NO edge demonstrated; verdict PRELIMINARY_IN_SAMPLE_ONLY, weight 0 |
| 7 | Rejected candidate list | NONE YET | no family has exhausted its trial budget; 47 families are DATA_GATED (UNAVAILABLE, weight 0), not REJECTED |
| 8 | Market-specific proof matrix | DONE | data/alpha/alpha_center_r7.json |
| 9 | Alpha Center output | DONE | data/alpha/alpha_center_r7.json — all candidates NO_TRADE/RESEARCH_ONLY |
| 10 | Sample unified ticker packets | DONE | data/alpha/sample_packets_r7.json — 5 packets; missing numerics are null, never 0; missing feeds named |
| 11 | Coverage-gap report | DONE | gap registry (R5) + per-family reasons + per-packet missing_feeds |
| 12 | Tests | DONE | tests/test_r7_alpha_engines.py — 8 tests; suite 184 passed + 2 slow-boot |
| 13 | Commit/push/ZIP/clean tree | DONE | see git log |

## What R7 proves and does NOT prove

PROVES: five engines are genuinely separate (families, formulas, baselines, costs differ);
no universal score artifact; trial machinery works end-to-end on REAL data (FRED + spot);
gated families fail closed with weight 0; SNDK/PLTR never used for tuning.

DOES NOT PROVE: any alpha. The single tested family (FX carry) shows Sharpe 0.31
with excess ≈ 0 vs its baseline on 22 months — that is not an edge and is not
promoted. 47 of 48 families are DATA_GATED pending licensed PIT feeds
(EDGAR PIT, consensus, TrendForce, IDX broker flow, on-chain, CFTC, EIA/LME).
No component is PROVEN_FOR_EXACT_CLAIM yet. Nothing is tradable.

## R8 entry condition

Extreme-winner/false-lookalike tournament (SNDK, PLTR, SPXC, full cohorts from
data/cohorts/extreme_cohorts.json + matched controls) — evaluation-only cases,
never tuning inputs.
