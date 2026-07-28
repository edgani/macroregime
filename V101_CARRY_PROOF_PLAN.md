# V10.1 Carry Proof Plan

## What must be proven

The claim is not “rate differential exists.” The claim is that a frozen, executable carry-state rule improves net outcomes relative to no-position and simple-rate-differential baselines after publication lags, forward/basis costs, spreads, slippage and unwind losses.

## Frozen sequence

1. Freeze the causal map and candidate family before outcomes are inspected.
2. Build an official point-in-time panel with decision timestamp and `available_at` timestamp.
3. Include every candidate and failed trial in the family ledger.
4. Run purged expanding walk-forward tests with embargo.
5. Select before opening the untouched lockbox.
6. Apply PBO, Deflated Sharpe, familywise bootstrap/Holm, parameter-neighbourhood, regime, cost-stress and concentration gates.
7. Seal prospective forecasts before the outcome period.
8. Reconcile actual fills, costs, capacity and drawdowns.

## Required historical fields

Use `V101_CARRY_HISTORY_TEMPLATE.csv`. Each row needs:

- decision timestamp and actual data-availability timestamp;
- exact pair;
- base and quote policy/money-market rates;
- admitted stress state;
- pair spot return over the frozen horizon;
- carry accrual and execution cost;
- regime;
- `point_in_time=true`;
- `source_class=POINT_IN_TIME_OFFICIAL`.

Final revised data, reconstructed values without release timestamps, duplicate pair-date observations and data available after the decision time are rejected.

## Promotion standard

The packaged policy requires at least ten years, 200 closed trades, four regimes, PBO no greater than 20%, Deflated Sharpe probability at least 95%, multiple-testing correction, positive cost-stressed behavior and a separate prospective/actual-fill pass. Historical PASS alone cannot authorize capital.

## Current status

The engine, state machine, data admission and proof firewall are implemented. No point-in-time carry panel, untouched future outcomes or actual fills are fabricated. Therefore carry alpha remains `NOT_PROVEN` and systematic live remains `PROOF_GATED`.
