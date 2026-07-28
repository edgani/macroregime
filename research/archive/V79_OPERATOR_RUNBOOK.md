# V7.9 Operator Runbook

## 1. One-time setup

Run `CHECK_FINAL_V79.bat`. Do not continue when validation fails.

Run `SETUP_FINAL_CORE.bat` and enter:

- `SPY`, `VOO`, or `IVV`;
- the fraction of the total account assigned to this isolated strategy sleeve;
- the sleeve's current equity weight: `0` for cash, `1` for equity, or blank when unknown;
- estimated one-way execution cost in basis points.

The sleeve remains disabled unless the exact phrase `AUTHORIZE V79` is entered.

## 2. Monthly operation

Run `RUN_FINAL_CORE.bat` only after the previous calendar month has completed. The system fetches two live data sources, removes the open month, checks the trailing ten months, verifies the frozen proof receipt, applies the cost and scope guards, and writes:

`runtime/v79_last_instruction.json`

There are only five valid operator outcomes:

| Status/action | Operator response |
|---|---|
| `BUY ... TO 100% OF THE AUTHORIZED SLEEVE` | Buy the configured ETF until the authorized sleeve is fully in equity. |
| `HOLD_EQUITY` | Do nothing. |
| `SELL ... AND MOVE THE AUTHORIZED SLEEVE TO CASH` | Sell the configured ETF and hold the sleeve in cash. |
| `HOLD_CASH` | Do nothing. |
| Any `NO_ORDER`, `BLOCKED`, or fail-closed status | Do not trade. |

Cash means cash or the broker's ordinary cash sweep. A bond or duration ETF is not a validated substitute.

## 3. Execution discipline

- Execute once during a regular US market session after month-end.
- Keep total one-way spread, fees, and slippage at or below 25 bps.
- Do not front-run the signal before the month closes.
- Do not reverse the order based on intramonth price, news, macro views, another dashboard tab, or discretion.
- Do not add leverage, shorts, options, individual stocks, or sector tilts.
- After execution, update `WARROOM_V79_CURRENT_EQUITY_WEIGHT` in `.env` to `1` or `0` so the next run emits HOLD rather than a duplicate rebalance.

## 4. Safety checks before every order

The receipt must show all of the following:

```text
mode = LIVE_PRODUCTION
feed.status = LIVE_DUAL_SOURCE_CONFIRMED
feed.consensus_status = PASS
instruction.status = READY_EXACT_SCOPE
instruction.ready_to_execute = true
instruction.input_sha256 = non-empty
```

Check that the instrument and sleeve fraction are the ones you authorized. Check that the estimated cost is realistic. A missing or surprising field means no trade.

## 5. Scope boundary

The final V7.9 trading system is only the broad-US-equity monthly long/cash sleeve. The rest of War Room is research-only. No ticker row, accumulation label, topping label, regime panel, crypto panel, commodity panel, FX panel, or IHSG panel may create an order.
