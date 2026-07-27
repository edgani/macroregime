# War Room OS V9.4 — Autonomous Public Data Plane

V9.4 corrects one responsibility problem in V9.3: public data discovery and collection should be automated by War Room rather than pushed back to the operator.

## What V9.4 does itself

- Defines executable public-source routes for all five markets.
- Downloads and hashes SEC/Nasdaq, EIA/CFTC, ALFRED/BIS, Binance/Deribit/Coin Metrics evidence when network access and required free API keys are available.
- Records IDX browser-session handoff when Cloudflare blocks non-browser collection; it never fabricates a successful fetch.
- Separates public acquisition from licensed imports, account fills, blind outcomes and prospective evidence.
- Bundles a genuine current Nasdaq symbol-directory snapshot as a real-data smoke test.

## Current status

- Source routes: 5/5
- Autonomous public collectors: 5/5
- Real bundled public snapshots: 1/5
- Point-in-time data admitted: 0/5
- Fully trading-ready: 0/5
- Technical predictors: 0
- Capital: BLOCKED

The package is not a trading-ready release. Successful downloads are evidence acquisition, not proof of return prediction.
