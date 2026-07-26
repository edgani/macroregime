# War Room OS V6.6 — Scoped Usable Risk Control

## Verdict

V6.6 is final and usable **only for one exact decision scope**:

`US_SMA10_MONTHLY_RISK_CAP`

It may reduce or cap an independently chosen broad-US-equity exposure at a completed monthly rebalance. It may not create exposure, select tickers, authorize long/short positions, set targets, predict crashes, use leverage, or generalize to another market.

Directional and ticker capital remains blocked.

## Confirmed evidence

The rule was selected from a frozen four-rule screen and confirmed on the previously untouched January 1920–December 1959 period while retaining cumulative 17-trial correction.

- Confirmatory observations: 480 months
- Benchmark maximum drawdown: -81.76%
- Risk-cap maximum drawdown: -46.48%
- Drawdown improvement: +35.28 percentage points
- Benchmark worst-5% expected shortfall: -12.77% per month
- Risk-cap worst-5% expected shortfall: -7.38% per month
- Expected-shortfall improvement: +5.39 percentage points per month
- Annual arithmetic return difference: +0.17 percentage points
- Downside capture: 40.59%
- Upside capture: 66.08%
- Average exposure: 62.92%
- 25-basis-point one-way stress: PASS
- Moving-block bootstrap ES lower bound: +0.79 percentage points
- Bootstrap drawdown-improvement probability: 95.67%
- Rolling 20-year windows: 84
- Rolling windows with improved drawdown: 100%
- Rolling windows with improved expected shortfall: 100%
- Reverse-rule control: FAIL as required

The rolling median annual return difference was -1.14 percentage points. Therefore this is a risk-reduction control, not an alpha claim.

## Current bundled state

Using the completed June 2026 monthly observation:

- S&P 500 monthly value: 7,450.03
- Trailing 10-month SMA: 6,921.057
- State: `BASELINE_CAP_ALLOWED`
- Maximum multiplier imposed by this control: 1.0

This means the control does not force a broad-equity reduction for the July 2026 rebalance. It is not a buy recommendation. The monthly data must be refreshed before the next rebalance.

## Prospective evidence

V6.6 adds an append-only SHA-256 hash-chained shadow ledger. Every future ticker, direction, target, timing, OI/liquidation, options, broker-flow, and causal-driver model must record a zero-capital forecast before its outcome matures. Backfilled or modified forecasts fail validation.

## Still blocked

- US stock ticker selection
- IHSG ticker selection
- Commodity, FX, and crypto direction
- SNDK-like early-winner selection
- Price target and exact timing
- Shorting and leverage
- Archive-supported option modules as live selectors
- Cross-market use of SMA10
- Prospective profitability

## Release status

- Decision-active scoped risk controls: 1
- Decision-active ticker/directional alpha components: 0
- Evidence-active archive modules: 3
- Active operational controls: 6
- Directional/ticker capital permission: BLOCKED
- Scoped risk-cap permission: CONDITIONAL_RISK_CAP_ONLY
