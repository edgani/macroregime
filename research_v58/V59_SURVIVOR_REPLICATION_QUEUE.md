# V59 Fresh Point-in-Time Replication Queue

Generated: 2026-07-25T03:06:15Z

## Gate from V58

- 868 mapped candidates.
- 795 registered empirical claims in the current data-ready batteries.
- Three candidates survive the conservative global 795-claim correction on gross maintained returns.
- Zero candidates survive the same global gate after a coarse 25 bps/month deduction.
- Therefore all three remain research candidates with zero live weight.

## 1. AnnouncementReturn — Earnings announcement return

**Role:** event_information_diffusion

**Exact definition:** Sum of market-adjusted returns from trading day -1 through +2 around the quarterly earnings announcement date; original OpenAP definition uses IBES fpi=6 announcement dates.

**Why advanced:** Survived gross one-sided Bonferroni lower bounds in both validation and lockbox after accounting for all 795 v58 claims.

**Why not proven:** No survivor remains after the coarse 25 bps/month global stress; maintained aggregate portfolios do not expose constituents, turnover, borrow, capacity or data-vintage errors.

**Required sources:**

- IBES historical announcement dates with publication timestamps
- CRSP daily returns, delisting returns and shares/prices
- contemporaneous market and risk-free return
- point-in-time security identifier link table

**Critical bias tests:**

- announcement timestamp before/after close
- earnings date revisions
- delisting return inclusion
- same-day multiple announcements
- microcap exclusion and capacity
- transaction cost and event turnover

**Promotion gate:**

- exact source lineage and stock-level reconstruction hash match
- validation and untouched lockbox lower bounds positive after the full updated global trial budget
- positive after measured turnover, spread, market impact, borrow and delisting costs
- incremental value over simple event/revision/dividend baselines
- stable across market-cap and liquidity buckets without microcap dependence
- no single calendar year contributes over 30 percent of total improvement
- signed prospective observations mature with zero live weight until approval

## 2. AnalystRevision — EPS forecast revision

**Role:** expectations_revision

**Exact definition:** For current-fiscal-year IBES estimates (fpi=1), keep the last observation each month and compute current mean estimate divided by prior-month mean estimate.

**Why advanced:** Survived gross one-sided Bonferroni lower bounds in both validation and lockbox after accounting for all 795 v58 claims.

**Why not proven:** No survivor remains after the coarse 25 bps/month global stress; maintained aggregate portfolios do not expose constituents, turnover, borrow, capacity or data-vintage errors.

**Required sources:**

- IBES Detail or Summary history with estimate timestamps and broker identifiers
- CRSP daily/monthly returns and delisting returns
- point-in-time identifier links
- actual earnings and guidance timestamps for contamination controls

**Critical bias tests:**

- stale-estimate removal
- broker duplication
- post-announcement contamination
- split adjustments
- coverage and microcap filters
- turnover and crowding

**Promotion gate:**

- exact source lineage and stock-level reconstruction hash match
- validation and untouched lockbox lower bounds positive after the full updated global trial budget
- positive after measured turnover, spread, market impact, borrow and delisting costs
- incremental value over simple event/revision/dividend baselines
- stable across market-cap and liquidity buckets without microcap dependence
- no single calendar year contributes over 30 percent of total improvement
- signed prospective observations mature with zero live weight until approval

## 3. DivYieldST — Predicted div yield next month

**Role:** distribution_seasonality

**Exact definition:** Use qualifying CRSP cash distributions and prior payment timing to predict next-month dividend seasonality; discretize expected yield into the frozen bins from SignalDoc.

**Why advanced:** Survived gross one-sided Bonferroni lower bounds in both validation and lockbox after accounting for all 795 v58 claims.

**Why not proven:** No survivor remains after the coarse 25 bps/month global stress; maintained aggregate portfolios do not expose constituents, turnover, borrow, capacity or data-vintage errors.

**Required sources:**

- CRSP distribution history including distcd and ex/pay dates
- CRSP prices, returns and delisting returns
- corporate-action adjustment history
- point-in-time identifier links

**Critical bias tests:**

- ex-date versus declaration-date availability
- special dividend contamination
- tax/clientele seasonality
- price drop around ex-date
- turnover/capacity
- subperiod stability after decimalization

**Promotion gate:**

- exact source lineage and stock-level reconstruction hash match
- validation and untouched lockbox lower bounds positive after the full updated global trial budget
- positive after measured turnover, spread, market impact, borrow and delisting costs
- incremental value over simple event/revision/dividend baselines
- stable across market-cap and liquidity buckets without microcap dependence
- no single calendar year contributes over 30 percent of total improvement
- signed prospective observations mature with zero live weight until approval

## Secondary challenger

ShortInterest stays in the ledger but is not advanced: its global 795-claim validation lower bound is negative.

## Capital boundary

Live decision weight: `0.0`  
Capital permission: `BLOCKED`
