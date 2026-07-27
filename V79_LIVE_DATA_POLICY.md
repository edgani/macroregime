# V7.9 Live Data Policy

## Production sources

An executable signal requires agreement between two independently distributed daily-close feeds:

- FRED series `SP500`, whose stated source is S&P Dow Jones Indices LLC.
- Yahoo-distributed daily history for `^GSPC`.

FRED is retained as the canonical series only after both sources agree over the final ten completed months.

## Consensus gate

The sources must have the same latest completed month and at least ten shared consecutive months. Each close must agree within the larger of:

- 1.0 index point; or
- 2 basis points of the FRED close.

A mismatch causes `UNAVAILABLE_FAIL_CLOSED`.

## Time gate

All observations in the still-open calendar month are removed. The final signal window must contain ten consecutive completed months. At the next monthly rebalance, a source that has not updated becomes stale and blocks the order.

## Forbidden production inputs

- Bundled research CSVs.
- Cached or manually edited current snapshots.
- User CSVs.
- The old V6.6/V7.8 2026 seed values.
- A single provider without confirmation.

User CSV mode exists only to audit the formula. It always has `verified_live_feed = false` and cannot create an executable instruction.

## Failure behavior

The system does not infer, fill forward, estimate, or substitute a value. Network failure, missing provider, stale data, disagreement, duplicate month, gap, future date, or invalid close returns no order.
