# War Room OS v2.3 — NO_DATA Root-Cause Audit

## What was actually wrong

1. **FX provider symbols were wrong**
   - `USDJPY=X` and `USDIDR=X` were queried even though Yahoo's canonical tickers are `JPY=X` and `IDR=X`.
   - v2.3 keeps aliases for backward compatibility and uses canonical provider symbols.

2. **Streamlit performed network work before rendering**
   - Core, institutional, derivatives and specialist collectors ran synchronously on every cached rerun.
   - One slow provider delayed the entire page. v2.3 moves network collection to `warroom_data_worker.py` and Streamlit reads `runtime/desk_snapshot.json` only.

3. **Yahoo retries were effectively unbounded for large universes**
   - A 200-name universe could generate about 50 serial retries after a partial batch failure.
   - Retries are now bounded by `WARROOM_YF_RETRY_CAP`; provider calls also have explicit timeouts and the entire core collector has a hard process timeout.

4. **No candidate was mislabeled as no data**
   - Alpha Center returned an empty `NO_DATA` model whenever no candidate cleared all gates.
   - It now reports `NO_SIGNAL`, keeps rejected candidates visible for audit, and issues `NO ACTION`.

5. **Company Intel depended on an aligned Alpha candidate**
   - The tab stayed empty even when price data existed.
   - It can now open any loaded setup or price-context ticker. Fundamentals and institutional enrichment have their own independent statuses.

6. **Optional paid enrichment contaminated tab-level status**
   - A missing dark-pool/borrow/Smart Money subscription could make a healthy market tab look like `NO_DATA`.
   - Core datasets and optional enrichments are now evaluated separately. Missing optional providers produce `PARTIAL` or `NOT_ENTITLED`, not false core-data failure.

7. **US options watchlist could contain only illiquid candidates**
   - Five setup tickers could consume all option-chain slots.
   - SPY, QQQ, IWM, SMH, NVDA and AMD are now reserved as liquid anchors before candidate-specific names.

8. **CFTC had only one public transport path**
   - The official Socrata JSON endpoint could fail and leave commodities/FX derivatives blank.
   - An official Socrata CSV fallback and persistent last-good cache were added. COT remains weekly, not intraday.

9. **Liquidity requests were sequential and all-or-nothing**
   - Treasury TGA, NY Fed RRP and SOFR were requested serially.
   - They now run concurrently, cache last-good values and can use loaded FRED WALCL/RRP/WTREGEN observations as a fallback. Missing data is never converted to neutral.

10. **Synthetic status was falsely triggered by the phrase “synthetic disabled”**
    - The source classifier searched for the word `synthetic` and could report `SYNTHETIC_TEST` even when synthetic generation was disabled.
    - Detection now requires an explicit test-only source.

## Status meanings in v2.3

- `LIVE`: core dataset is currently usable.
- `STALE`: last-good dataset is available but older than its freshness contract.
- `PARTIAL`: core data is usable, but one or more enrichment layers are absent/stale.
- `NO_SIGNAL`: data loaded; no candidate or event passed the current gate.
- `ACTION_REQUIRED`: a public source needs a local configuration item, e.g. SEC user-agent/contact.
- `NOT_ENTITLED`: the source requires a subscription/API entitlement that is not present.
- `NO_DATA`: the core provider returned no usable records and there is no last-good cache.
- `ERROR`: adapter/parser/provider call failed and no usable fallback exists.

## What cannot be made live without credentials or licensing

- Trade-level US options flow and normalized Greek flow.
- True TRF/off-exchange prints with institutional-size filtering.
- Borrow utilization, estimated live short interest and cost-to-borrow.
- Nansen Smart Money and Arkham entity attribution.
- Licensed IDX broker summary, foreign flow and order-book data.
- Intraday exchange futures open interest through Databento/CME entitlement.

The UI must show these as enrichment gaps. It must not replace them with fabricated data, FINRA short-volume inference, or static narrative.

## Start command

Use `RUN_FAST_WARROOM.bat`. It starts the data worker separately, then opens Streamlit immediately. The first screen can show `INITIALIZING`; it updates from the atomic local snapshot without blocking tab navigation.
