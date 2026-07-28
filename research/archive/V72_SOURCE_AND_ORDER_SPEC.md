# V72 SPX/SPXW signed-dealer research — exact data order and source contract

## Required Cboe products

1. **Enhanced US Options Trade-by-Trade Execution Detail (TBT), C1**
   - Date range: 2019-10-07 through at least 2025-06-30.
   - Underlyings/roots: SPX and SPXW only.
   - Session: retain RTH; keep GTH/Curb in the raw archive but exclude them from the primary study.
   - Delivery: daily zipped CSV, immutable raw archive.

2. **Option Quotes, `^SPX`, 1-minute, Include Calcs + Include Open Interest, per-day**
   - Same analysis dates as TBT.
   - Must include NBBO, open interest, active underlying price, implied volatility, delta, gamma, theta, vega, and rho for every active SPX/SPXW series at each interval.
   - This is mandatory because positions in contracts that do not trade in a minute still have gamma and must remain in aggregate exposure. Open interest is used only for the unsigned topology baseline and placebo; it can never supply dealer sign.

3. **US Options Trade-by-Trade Greeks (GRK), C1 — optional cross-check**
   - Same dates as TBT when purchased.
   - Official trade-time join: `trading_dt + formatted_symbol + price`, forward ASOF on transaction time, maximum five seconds.
   - GRK validates trade-time analytics but cannot replace the complete one-minute quote surface.

4. **SPX/ES one-minute underlying and liquidity data**
   - SPX or front ES price with a documented futures-roll rule.
   - ES traded notional and executable spread/depth proxy.
   - Complete regular-session calendar aligned to C1.

## Why Open-Close alone is not the primary source

Open-Close is useful for aggregated participant flow and a lower-cost challenger. It is not sufficient for the primary position-reconstruction claim because the primary study needs trade-level execution linkage, exact timestamps, complex/simple execution IDs, and trade-level Greeks.

## License boundary

Cboe marks TBT, GRK, and Open-Close as proprietary. Raw licensed records must remain outside the distributable War Room ZIP. Only schema definitions, hashes, code, validation reports, and license-permitted derived aggregates may enter a release.

## Raw archive layout expected by the runner

```text
licensed_data/
  tbt/C1_TBT_YYYY-MM-DD.zip
  quotes/OPTION_QUOTES_SPX_1MIN_YYYY-MM-DD.zip
  grk/C1_GRK_YYYY-MM-DD.zip  # optional cross-check
  underlier/SPX_ES_1MIN_YYYY-MM-DD.csv
  manifests/source_manifest.json
```

`source_manifest.json` must list every expected trading date, raw file path, bytes, SHA-256, source product, exchange, and license classification. A missing expected date fails the study; it cannot be silently skipped.

## Research boundary

Receiving the data does not promote a signal. It only changes V72 from `DATA_LICENSE_REQUIRED` to `READY_TO_EVALUATE`. Promotion still requires frozen validation, untouched lockbox, costs, placebos, multiple-testing correction, and signed prospective evidence.
