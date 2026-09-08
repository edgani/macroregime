# Market Opportunity OS v3.2 — Longitudinal Discovery + Outcome Learning

Base: **v3.1 Story / Expectation Optionality**. This is an additive upgrade; the existing Macro Decision Engine, IHSG transaction intelligence, story/expectation optionality, causal graph, valuation logic and fail-closed decision gates remain intact.

## Added
- Immutable `OPPORTUNITY_EVENT` memory in `state/opportunity_memory.sqlite`.
- Automatic discovery from the existing cross-market scan; no ticker-by-ticker input required for the loaded universe.
- Explicit causal event fields: driver → first order → second order → bottleneck → beneficiary → revenue/margin capture → catalyst → invalidation.
- Multi-archetype classification and component scores instead of one opaque score.
- First-seen / first-unusual / first-high-conviction timestamps and prices.
- Persistent lifecycle states: DISCOVERED → EMERGING → PROVING → HIGH_CONVICTION → PRICING_IN → MATURE → CROWDED / INVALIDATED / RESOLVED.
- Forward outcome schema for 1D, 3D, 1W, 2W, 1M, 3M, 6M and 12M.
- Absolute return, benchmark alpha, sector alpha, MFE, MAE, time-to-MFE, time-to-MAE, peak return and max drawdown.
- Bounded cached outcome maturation using yfinance where a real symbol + benchmark are available.
- Explicit false-positive taxonomy and missed-runner audit store.
- Regime/market/sector/theme historical expectancy with sample-size confidence.
- Expanding chronological walk-forward calibration; no random shuffle.
- Baseline comparison surface that stays DATA GATED when PIT baseline features do not exist.
- Automatic daily / weekly learning reports under `state/learning_reports/`.
- HK / China / Europe / Taiwan equity architecture support when symbols/data are supplied.
- New dense dark-cyan Opportunity Tracker UI inspired by the supplied dashboard reference.
- Original v3.1 decision desk preserved as `DECISION DESK`.

## Guardrails
- No autotrading, broker credentials, private keys, leverage execution or automatic orders.
- No RSI / MACD / stochastic / generic MA-cross primary opportunity logic.
- Production weights do not self-modify from recent outcomes.
- First-detection snapshots are immutable; future data only enters outcome/lifecycle tables.
- No fake historical performance. Fresh installs correctly show insufficient-sample / no-mature-outcome states.
- Narrative exposure alone cannot create a longitudinal opportunity event.

## Validation
Run:

```bash
python tests/run_all.py
```

Current package result: **18 PASS / 0 NONPASS** plus **20/20 v3.2 structural acceptance checks**.
