# War Room OS V7.9 — Final Proven Core

## Verdict

**FINAL, PROVEN, AND READY TO USE FOR ONE EXACT TRADING SCOPE:**

> A user-authorized, dedicated broad-US-equity strategy sleeve that moves monthly between **100% SPY/VOO/IVV** and **100% cash**, using the latest completed S&P 500 monthly close versus its trailing 10-month simple moving average.

This is now a complete trading system rather than a research dashboard because every component that can create an order is inside the confirmed scope. Everything else in War Room is hard-blocked as `NO_TRADE_RESEARCH_ONLY`.

“Proven” here means historically confirmed reduction of broad-US-equity drawdown and left-tail severity under the frozen rule and tested assumptions. It does not mean guaranteed future profit.

## Exact rule

- Observation: most recent **completed calendar month** only.
- Equity state: completed monthly S&P 500 close is at or above SMA10.
- Cash state: completed monthly S&P 500 close is below SMA10.
- Execution: one rebalance during the first regular US market session after month-end.
- Instruments: SPY, VOO, or IVV; defensive state is cash.
- Position: 100% or 0% of the user-authorized strategy sleeve.
- No shorting, leverage, individual ticker selection, intramonth override, target price, or stop price.
- No order when estimated one-way total execution cost exceeds 25 bps.

## Confirmatory evidence

Frozen untouched confirmation period: January 1920 through December 1959, 480 months.

| Metric | Buy and hold | Monthly SMA10 long/cash |
|---|---:|---:|
| Maximum drawdown | -81.76% | -46.48% |
| Worst-5% monthly expected shortfall | -12.77% | -7.38% |
| Annual arithmetic return, 10 bps switching cost | 11.89% | 12.06% |
| Downside capture | — | 40.59% |
| Upside capture | — | 66.08% |

Robustness:

- 25 bps one-way switching-cost stress: passed.
- 84 rolling 20-year windows.
- Drawdown improvement in 100% of rolling windows.
- Expected-shortfall improvement in 100% of rolling windows.
- Bootstrap probability of drawdown improvement: 95.67% at 10 bps and 95.33% at 25 bps.
- Reverse-rule negative control failed as required.

The median rolling annual-return difference was about -1.14 percentage points. The accepted claim is therefore **risk reduction**, not persistent excess return.

## Production data safety

A current order requires live agreement between:

1. FRED `SP500`, sourced from S&P Dow Jones Indices; and
2. Yahoo-distributed `^GSPC` daily history.

The trailing ten completed months must match within the frozen tolerance. Missing data, provider disagreement, stale data, duplicate months, gaps, future dates, non-positive closes, or an unfinished current month produces `NO ORDER`.

The inaccurate legacy 2026 bundled seed used by older releases is permanently excluded from current execution. Manual CSV input is audit-only and can never create an executable instruction.

## Activation

1. Extract the ZIP into a new folder.
2. Run `CHECK_FINAL_V79.bat`.
3. Run `SETUP_FINAL_CORE.bat` and choose the instrument and strategy-sleeve size.
4. Type exactly `AUTHORIZE V79` only after reviewing the scope.
5. Run `RUN_FINAL_CORE.bat` after month-end.
6. Read `runtime/v79_last_instruction.json` and execute only when:
   - `mode` is `LIVE_PRODUCTION`;
   - feed status is `LIVE_DUAL_SOURCE_CONFIRMED`;
   - instruction status is `READY_EXACT_SCOPE`; and
   - `ready_to_execute` is `true`.

Any other status means no trade.

## Explicitly not proven and not tradable

- Individual US ticker long/short selection.
- IHSG, FX, commodity, or crypto direction.
- Predictive accumulation, topping, squeeze, or crash-date detection.
- Entry targets, stop prices, options positioning, leverage, or shorting.

Those tabs remain available only as research context and have zero order permission.
