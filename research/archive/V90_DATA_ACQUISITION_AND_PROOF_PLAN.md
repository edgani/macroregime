# V9.0 Data Acquisition and Proof Execution Plan

## Fastest honest route

### US stocks

**Bootstrap now:** SEC EDGAR filings/XBRL, FINRA short-sale/short-interest publications, current Nasdaq symbol data, and prospective snapshots.

**Required for institutional historical proof:** survivor-free security master/corporate actions/delisting returns; point-in-time analyst estimates; historical options surfaces and signed activity; securities lending/borrow; quote/trade execution data.

**Recommended stack:** CRSP (or equivalent) + LSEG I/B/E/S PIT + Cboe DataShop + S&P Global/S3 securities finance + TAQ/broker fills.

### IHSG

**Bootstrap now:** KSEI master securities and local/foreign holding composition, IDX issuer filings/corporate actions/stock summaries.

**Required for full proof:** licensed IDX historical/EOD/reference data, broker summary or trade log/done detail, suspension/delisting history and broker fills. Broker inventory is an optional add-on; the core long-only selector can be tested without it, but it cannot claim broker-accumulation edge.

### Commodities

Build separate archetypes: oil/gas, metals and agriculture cannot share one formula.

**Bootstrap now:** EIA/USDA/other official physical balances and release archives, CFTC COT/TFF with publication lag.

**Required for execution proof:** CME DataMine trades/top-of-book/depth/settlements and, where essential, licensed physical basis/freight data.

### FX

**Bootstrap now:** ALFRED vintages, BIS SDMX, central-bank releases, IMF balance-of-payments/reserves, CFTC TFF where futures representation exists.

**Execution scope must be explicit:** CME FX futures can be proven with CME data; OTC spot requires separate venue/broker quotes and fills. Never transfer futures proof to spot.

### Crypto

**Bootstrap now:** Binance public archives, Deribit API/prospective archive, DefiLlama/Coin Metrics Community and protocol disclosures.

**Required for full proof:** complete venue lifecycle, historical OI/funding/liquidations or institutional market data, entity-adjusted on-chain data where used, and actual account fills. Each venue is a separate execution scope.

## Overfitting and article-contamination controls

- Cases such as SNDK and PLTR are diagnostics opened only after model freeze.
- LLM never sees historical outcomes during feature extraction or ranking.
- Every prompt/model retry counts as a trial.
- Narrative features must be supported by timestamped source records and deterministic extraction receipts.
- Counterfactual tests perturb demand, capacity, price realization and dilution assumptions; a causal model must change its projection appropriately.
- Matched dormant-bottleneck controls test whether the activation clock adds information beyond merely identifying a bottleneck.
- Final selectors are compared with transparent baselines and negative controls.
- No universal cross-market score; each market/archetype has its own proof receipt.

## What can be completed immediately vs what requires time

**Immediate:** historical data acquisition, PIT reconstruction, frozen historical research tests, shadow forecast launch.

**Requires future observations:** prospective calibration, 200 closed trades, 24-month/four-regime evidence and real limited-production PF/drawdown. No software change can honestly manufacture those observations.
