# War Room OS v5 — Resilient Feed Contract

## What changed

The dashboard now uses a provider/cache cascade instead of a single yfinance call:

- Daily OHLCV: yfinance batch → direct Yahoo chart → Binance for crypto → Stooq where supported → last-known-good cache.
- Macro: FRED API → FRED CSV → DBnomics → FRED cache.
- IDX: resilient Yahoo base with optional IDX/typef enrichment.
- Intraday surfaced-ticker quotes: Binance or Yahoo/yfinance → quote cache.

## Failure behavior

A failure is local:

- one ticker fails: only that ticker is missing or cached;
- one market fails: other markets remain available;
- current providers fail: the last-known-good daily frames and last verified desk remain visible;
- malformed setup: the row is quarantined rather than globally blocking the desk.

No synthetic price may enter a decision-bearing UI.

## Data labels

- `INTRADAY_QUOTE_PLUS_DAILY_MODEL`: fresh/delayed intraday quote attached to daily-model levels;
- `RESILIENT_DAILY`: daily history refreshed or served from fresh cache;
- `RESILIENT_DAILY_LKG`: one or more markets are using older last-known-good data;
- `RESILIENT_DAILY_PARTIAL`: at least one market is available and another is missing;
- `RESILIENT_DESK_LKG`: the current build failed and the last verified desk was restored;
- `DATA_UNAVAILABLE`: first run, no provider and no cache.

## What cannot be guaranteed

No free internet feed can honestly guarantee 100% uptime or exchange-grade real-time delivery.
The system guarantees graceful degradation and persistent last-known-good display after at least one
successful fetch. Intraday Yahoo quotes may be delayed. PAPER/LIVE permission remains independent.
