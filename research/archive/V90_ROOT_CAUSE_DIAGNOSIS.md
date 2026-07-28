# War Room OS V9.0 — Root-Cause Diagnosis of the 0/5 Result

## Executive verdict

The V8.9 result **0/5 was not an empirical failure of five trading models**. It was an orchestration and data-contract failure: the shipped package contained no per-market `dataset_manifest.json`, no raw evidence files, and no completed collection run. Therefore every market failed at the first file-existence check.

That is only the surface problem. A deeper source/code audit found nine blockers.

## 1. No data was shipped or collected

`V89_CURRENT_REAL_DATA_AUDIT.json` reports the same error for every market: `dataset_manifest.json not found`. The package validates hypothetical fixtures but does not execute a production collection job.

**Fix:** V9.0 adds a provider registry, automatic manifest builder, collection-plan resolver, and data-directory diagnostics. A market can no longer be labelled empirically failed merely because collection never ran.

## 2. The collector coverage was far smaller than the contract

The V8.9 connector module covered SEC, FRED/ALFRED, EIA, CFTC, BLS and two current Deribit endpoints. It did not collect FINRA, Nasdaq lifecycle data, BIS, KSEI/IDX, Binance archives, DefiLlama/Coin Metrics, licensed estimates, borrow, option surfaces, or exchange execution data. It therefore could not create most required roles.

**Fix:** every role now has an explicit public, licensed and prospective route. Missing licensed inputs remain explicit; no proxy is silently relabelled.

## 3. All-or-nothing admission was too rigid

V8.9 required every possible role before any market model could be tested. That makes an optional options or broker-flow module block a valid fundamental-only core model.

**Fix:** admission is now exact-model scoped. Core roles are mandatory; optional modules enter as separately hashed add-on tests. A reduced model is not the same model and must be registered separately.

## 4. Outcome data was mixed into the predictor contract

`outcome_prices` was listed as a required admission role and was checked using one global `decision_time`. This is methodologically wrong. Outcomes must be hidden from discovery and opened only after forecasts are frozen.

**Fix:** outcome data is moved to a separate custodian manifest. Predictor admission cannot contain realized returns, future peaks or future drawdowns.

## 5. Point-in-time checking was global, not forecast-local

A single `available_at <= decision_time` test at the end of an eight-year history does not prevent historical look-ahead for earlier forecasts.

**Fix:** V9.0 requires one `decision_time` per forecast and performs an as-of join for every instrument/date. A forecast is rejected if any feature was not available at that exact time.

## 6. No complete universe/lifecycle reconstruction existed

US and IDX proof require inactive/delisted securities, historical identifiers, corporate actions, suspensions and listing windows. Current symbol directories cannot supply this alone.

**Fix:** institutional route uses CRSP or equivalent for US and IDX historical/reference products plus KSEI for Indonesia. Free routes are allowed only with an explicit evidence ceiling and survivorship sensitivity analysis.

## 7. No raw-to-causal feature factory existed

The package had narrative and projection schemas but no production pipeline converting filing, capacity, inventory, qualification, order, margin and value-capture facts into versioned causal objects.

**Fix:** raw evidence is extracted into deterministic, cited event objects: origin → transmission → bottleneck → beneficiary → expectation gap → monetization clock → invalidation. LLM extraction is never allowed to see outcomes and cannot directly produce a score.

## 8. Real profit factor and drawdown cannot come from public outcome bars alone

Real PF requires fills after commission, spread, slippage, impact, borrow, financing and tax. Public trades are not the user's fills.

**Fix:** historical research uses exchange quote/trade data; prospective proof uses the user's broker/exchange fill ledger. PF and drawdown promotion remain impossible until actual execution evidence exists.

## 9. Full proof cannot be compressed into one day

A 24-month prospective requirement and 200 closed trades are future observations. Generating them synthetically or backfilling them would be fraud, not acceleration.

**Fix:** separate historical research promotion, prospective shadow promotion and limited-production promotion. Historical success can authorize paper/shadow operation, not a false claim of completed live proof.

## Correct order of attack

1. Build one complete point-in-time data plane per market.
2. Freeze causal feature families and transparent baselines before outcomes are opened.
3. Run nested walk-forward and sealed lockbox with a global immutable trial ledger.
4. Run post-cutoff prospective forecasts.
5. Use actual fills for PF, drawdown, capacity and execution adjudication.
6. Promote only the exact market, direction, horizon and execution method that passes.

V9.0 fixes the proof machinery and identifies the actual data purchases/collections required. It does **not** claim that the five markets are already proven.
