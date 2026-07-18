# War Room OS v6 — Original UI, Rich Runtime Data Binding

This package preserves the original 14-tab War Room interface and reconnects it to runtime data and
engine outputs without restoring the old hard-coded current tickers, prices, probabilities, targets or
allocation values.

## Run

On Windows, extract the ZIP to a new folder and double-click:

```text
RUN_APP.bat
```

The root `RUN_WARROOM.bat` calls the same launcher.

## Runtime feed behavior

Daily-model inputs use a resilient provider cascade:

1. yfinance batch;
2. direct Yahoo chart endpoint;
3. Binance for supported crypto;
4. Stooq where supported;
5. persistent last-known-good cache.

Intraday quotes are attached only to surfaced research-watch tickers. They do not replace daily OHLCV
as the model input. Provider and ticker failures are isolated, so one failure does not blank every tab.
A first run with no network and no pre-existing cache cannot create real current data.

Use `CHECK_FEEDS.bat` to produce a feed-diagnostics report. Use `SEED_OR_REFRESH_FEEDS.bat` to seed or
refresh the persistent cache.

## Alpha behavior

The Alpha tab has two deliberately separate layers:

- **Current tactical discovery watch** — generated from currently valid runtime setups across markets;
  explicitly labelled `UNPROVEN_RESEARCH_WATCH`.
- **Frozen US Alpha Foundry selector** — populated only after the separate SEC/price research pipeline
  runs and produces a real shortlist.

The tactical watch prevents Alpha from becoming an empty UI regression, but it is not promoted as a
proven selector. Curated moonshot names and placeholder tickers are not emitted as current candidates.

Run the historical Free Alpha Foundry with:

```text
RUN_ALPHA_FOUNDRY_QUICK.bat
```

## Mission Control and all tabs

Mission Control again displays the complete read-only cockpit:

- feed health and freshness;
- systemic state;
- multi-timeframe regime;
- regional context;
- cross-market opportunity watch;
- early warning;
- flow/rotation observations;
- Alpha proof state;
- permissions and integrity.

Macro, Early Warning, Flow, Supply Chain, Company Intel, Knowledge Graph and Validation consume rich
runtime payloads instead of being replaced by registry-only screens. Reference chains are explicitly
labelled as reference material, not current signals.

## Claim ceiling

- No current values are hard-coded into dashboard JavaScript.
- Runtime tactical setups are research watches, not proven alpha.
- The Foundry remains historical-candidate maximum until lockbox and prospective evidence pass.
- PAPER and LIVE are blocked.
- `MQA_RISK_RANGE_PROXY` is a local proxy label, not a claim of exact proprietary Hedgeye levels.

## Validation

See:

- `V6_DEEP_RUNTIME_AUDIT.json`
- `RELEASE_VALIDATION_v6.json`
- `research_review/DEEP_REAUDIT_v6.md`
- `PATCHED_MANIFEST_SHA256.json`
