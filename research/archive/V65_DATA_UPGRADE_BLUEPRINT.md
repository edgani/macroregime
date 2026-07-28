# V6.5 Data Upgrade Blueprint

## Priority 1 — convert the V6.5 archive claims into a stock-level point-in-time test

### Required datasets

1. Standardized US equity option surfaces, including delta, tenor, IV, quote timestamp and quote-quality fields.
2. Trade-level or open/close options flow with participant classification where licensed.
3. CRSP-grade returns, delistings, shares, market capitalization and corporate actions.
4. Point-in-time analyst estimates and revisions.
5. Point-in-time earnings-announcement calendar and returns.
6. Stock-loan availability, borrow fee, utilization and lendable supply.

### Frozen output tests

- Monthly and weekly stock ranking.
- Equal-weighted and value-weighted constructions.
- NYSE/non-micro breakpoints.
- Price and liquidity filters.
- Turnover, spread, impact and borrow costs.
- Precision@K, Recall@K, remaining return, MAE/MFE and lead time.
- 2023–2026 untouched lockbox.

## Priority 2 — fundamental-origin engine

Use filing dissemination date rather than fiscal-period end.

Fields:

- revenue and segment acceleration;
- gross/operating margin changes;
- inventory versus revenue;
- capex and capacity response;
- shares, debt and financing;
- guidance versus consensus;
- customer qualification, backlog and pricing disclosures.

The test must compare:

- origin only;
- option/position vulnerability only;
- origin × vulnerability;
- origin × vulnerability × signed amplification.

## Priority 3 — true economic network

Replace correlation clusters with dated economic links:

- customer-supplier relationships;
- percent-of-revenue exposure;
- product/component mapping;
- qualification status;
- substitutability and lead time;
- capacity and inventory buffers.

The test must identify the real margin/fee recipient and prevent double-counting multiple securities exposed to the same underlying shock.

## Priority 4 — market-specific licensed layers

### US options

Cboe-style open/close participant data and trade-by-trade execution context.

### Futures, commodities and FX

CME option IV/Greeks and market-depth history; CFTC release-time-adjusted positioning; physical data.

### IHSG

IDX log/EOD/broker and corporate-action history plus point-in-time fundamentals and controller/free-float history.

### Crypto

Archived multi-venue trades, OI, funding, basis, liquidation and depth plus on-chain value-capture data.

## Acquisition rule

A missing paid dataset is not replaced with a convenient public proxy after outcomes are observed. The component stays blocked until the exact registered data contract is available or a substitute is registered and tested before outcome analysis.
