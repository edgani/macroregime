# V9.0 Release Status

## Verdict

**ROOT CAUSE FOUND. METHODOLOGY REPAIRED. NOT YET TRADING READY.**

The former 0/5 result was caused first by missing collection outputs, not five failed market models. The audit also found a serious methodological flaw: outcomes and predictors shared one manifest and one global decision time, which was insufficient to prevent historical look-ahead.

V9.0 adds model-scoped core/add-on contracts, forecast-local as-of joins, outcome isolation, provider routes and automatic manifest generation.

## Current proof state

- Data collected in shipped package: 0/5 markets.
- Historical market models run under corrected V9.0 protocol: 0/5.
- Trading-ready markets: 0/5.
- Technical indicators used as predictors: 0.

## Next execution step

Acquire/collect the exact datasets in `V90_SOURCE_ROUTE_REGISTRY.json`, build predictor manifests, freeze models and run the sealed historical/prospective proof sequence. Full proof still requires licensed data for several roles and future prospective observations.

## Current measured state

The route audit records 0 data-admitted markets and 0 empirically failed market models. All five are currently classified as `COLLECTION_NOT_RUN`, because no signed market dataset manifest exists in the package. This distinction prevents a missing ETL run from being misreported as a failed trading model.
