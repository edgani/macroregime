# R8 Survivor-Safe Universe Report (2026-07-29)

## Verdict: NOT survivor-safe (honest)

| Requirement | Status | Gap |
|---|---|---|
| Active securities | PRESENT | cache/prices.parquet, 232 tickers (230 after case-ticker exclusion) |
| Delisted securities | ABSENT | no delisting feed; cache is active-only |
| Bankruptcies | ABSENT | requires CRSP delisting codes / Compustat |
| Failed narratives / dilution failures | PARTIAL | only if still listed and in cache universe |
| PIT membership | ABSENT | universe is a fixed list, not PIT-constituent |
| PIT market cap | ABSENT | requires shares-outstanding history (sec_edgar_pit or licensed) |
| Corporate actions | PARTIAL | yfinance Adj Close handles splits/dividends; delisting proceeds unknown |
| Matched controls (sector/cap/age/valuation/macro) | DATA_GATED_PARTIAL | sector/cap/valuation PIT feeds missing; liquidity-matched approximate controls possible |

Exact missing datasets: CRSP daily (or equivalent with delisting returns),
Compustat PIT fundamentals, SEC EDGAR PIT shares outstanding, licensed PIT
consensus estimates.

## Consequence for R8 metrics

- The measured +100% base rate and baseline Precision/Recall are BIASED UPWARD
  (failed names missing from denominator).
- Baseline numbers are therefore an upper bound for the live-tradable bar, not a
  fair historical estimate. Any future causal family evaluated on this universe
  inherits the same bias; family-vs-baseline comparison remains internally
  consistent on the SAME universe, which is noted in every trial record.
- Winner cohorts (R6 frozen) are "observed winners among active cache names",
  not "all winners in the historical universe".

This report is linked from prereg_r8.json and the trial ledger verdicts.
