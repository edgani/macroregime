# War Room OS — Full Live Intelligence Stack v2

This build connects every workspace to a declared data contract. It does **not** equate “connected” with “always available”: provider authentication, entitlement, exchange licensing and uptime remain external dependencies.

## Runtime design

- Core price/macro refresh: 60 seconds.
- Institutional event refresh: 10 seconds.
- Derivatives/options state refresh: 15 seconds.
- Slower fundamentals/physical/ownership hub: 120 seconds.
- Persistent Kafka/WebSocket connections run outside Streamlit and expose local snapshots.
- Independent provider calls run concurrently.
- No synthetic production fallback.
- Fresh cache and stale last-good cache are visibly distinct.

## Live/public sources

- Binance Futures: mark/index, funding, OI, global account ratio and taker ratio.
- Bybit: mark/index, funding, OI and account ratio.
- OKX: swap price, OI and funding.
- Deribit: BTC/ETH option summary, OI, volume, mark IV and option reference zones.
- SEC EDGAR: submissions/filings and XBRL company facts after setting a real User-Agent identity.
- CFTC Public Reporting Environment: weekly TFF and disaggregated COT through official JSON endpoints.
- DeFiLlama: chain TVL and historical TVL context.

## Licensed sources/adapters

- Unusual Whales REST and persistent stream bridge.
- Massive REST plus stock/options WebSocket bridge.
- ORTEX short-interest/borrow fields.
- Intrinio earnings, estimates, ownership, ETF NAV flow and settlement short interest.
- CoinGlass cross-exchange derivatives/liquidation analytics.
- Nansen Smart Money.
- Arkham labeled transfers.
- Databento futures/options statistics and trades bridge.
- Licensed IDX broker/foreign/order-book bridge.
- EIA API for physical energy series.

## Integrated derivatives interpretation

The options/derivatives workspace combines:

- price × OI quadrant;
- funding and crowding;
- taker imbalance;
- short interest, cost-to-borrow, days-to-cover and float;
- call/put OI and volume;
- streamed directional delta flow;
- streamed directional vega flow;
- net option premium;
- risk-reversal skew and IV term structure;
- GEX/gamma zones, zero-gamma when supplied;
- vanna/charm model context;
- expected-move bands and liquidation zones;
- observed persistence across five-minute buckets.

Outputs are context labels and pressure indices, not guaranteed direction or calibrated squeeze probabilities.

## Verification

- `validate_live_stack.py` validates offline parsers, semantics, failover, Python and dashboard JavaScript.
- `validate_redesign.py` validates all workspaces and no-credential behavior.
- `verify_live_connections.py --strict` validates the actual deployment's keys, bridges, endpoints and entitlements.

See `LIVE_DATA_ACTIVATION.md`, `.env.example`, `DATA_REQUIREMENTS_MATRIX.json`, and `stream_workers/README.md`.
