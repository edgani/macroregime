# V9.2 — Route to 5/5 Without Fake Proof

## The key decision

Do not attempt to prove every instrument in every market at once. Freeze one executable sleeve per market, prove it, then expand. Five markets means five independent receipts—not one universal model.

## Fastest defensible data route

### 1. US stocks
Start with Sharadar SF1 + SEP + TICKERS and SEC EDGAR. This gives an attainable survivor-aware, point-in-time historical core. Add I/B/E/S PIT only as a separately registered expectations model. Use real broker exports for prospective fills.

### 2. IDX
There is no defensible free substitute for long historical IDX reference, corporate-action and trade/log data. Acquire IDX Data Reference plus Historical/EOD/Log. Use issuer filings and KSEI disclosures. Broker summary is an add-on and may not block the fundamental core.

### 3. Commodities
Freeze WTI, gold and copper on CME/NYMEX/COMEX. Combine official physical vintages and release-lagged CFTC with CME DataMine contract history. Do not transfer proof among contracts.

### 4. FX
Use CME currency futures rather than unobservable OTC execution. Combine ALFRED/BIS/central-bank data, CFTC TFF and CME DataMine. The proof applies only to the named futures contracts and roll method.

### 5. Crypto
Freeze BTC and ETH on named Binance and Deribit accounts. Public Binance archives and Deribit data can bootstrap market history; protocol economics and supply data remain separately sourced. Actual exchange exports are mandatory for real profit factor.

## What 5/5 means

1. **5/5 provider-ready** — files and hashes exist.
2. **5/5 data-admitted** — point-in-time and survivor/venue lifecycle checks pass.
3. **5/5 historical blind-proven** — sealed outcomes pass exact-scope benchmarks.
4. **5/5 limited-production-ready** — prospective shadow and small-capital execution pass.
5. **5/5 fully proven** — at least 200 closed prospective trades, 24 months and four regimes per sleeve, with real PF and drawdown gates.

These stages cannot be collapsed into one backtest without recreating the contamination and selection problem.

## Non-negotiable proof metrics

- No technical predictor.
- Immutable global trial ledger, including failed experiments and prompt/model retries.
- Predictor data available before each forecast.
- Separate outcome custodian.
- Real net PF >= 1.50; bootstrap 95% lower bound >= 1.20.
- Normal max drawdown <= 15%; stress max drawdown <= 20%.
- Price projection beats unchanged-price and simple fundamental baselines.
- Bottleneck activation beats bottleneck-only dormant controls.
- Extreme-winner/large-move recall passes market-specific tests.
- Costs, spread, impact, borrow, financing, taxes and capacity are explicit.

## What the user must supply or authorize

The application cannot purchase licensed datasets or access brokerage/exchange account fills by itself. To move from route-ready to proof-ready, provide local exports/API entitlements listed in `V92_PROVIDER_ONBOARDING.env.example`.
