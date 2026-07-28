# Build Notes — Full Live Intelligence v2

## Added

- Full tab-level data coverage registry.
- Public crypto perpetual OI/funding/crowding adapters.
- Deribit option state.
- Massive US option-chain/Greeks/OI adapter.
- Unusual Whales REST plus protobuf Kafka/JSON WebSocket bridge architecture.
- Integrated delta/vega/premium/skew/GEX context with five-minute persistence.
- ORTEX and Intrinio short-interest/borrow context.
- CoinGlass liquidation and cross-exchange derivatives context.
- Databento live futures/options statistics bridge.
- SEC filings and XBRL fundamentals.
- Intrinio earnings, estimates, ownership and ETF flow.
- Official CFTC Public Reporting Environment JSON adapters.
- EIA physical energy adapter.
- Nansen, Arkham and DeFiLlama context.
- Licensed IDX bridge contract.
- Deployment connection verifier.
- Provider-level cache, stale failover, network-offline mode and failure isolation.

## Interpretation controls

- Open interest does not reveal trade direction by itself.
- Directional Greek flow can represent hedges, rolls, spreads or closing trades.
- Signed-OI gamma is labeled a proxy unless actual position-side data is supplied.
- Squeeze pressure is not a calibrated probability.
- Expected move, walls, GEX and liquidation concentrations are reference zones, not guaranteed targets.
- Expiry/DTE and flow persistence are context horizons, not exact duration forecasts.

## Verified in this build

- Python compilation.
- Dashboard JavaScript syntax.
- All workspace rendering/no-credential behavior.
- Option-chain analytics fixtures.
- Streamed Greek-flow and sector-rotation fixtures.
- Crypto squeeze-context fixtures.
- Provider parser fixtures.
- Liquidation-zone fixtures.
- Fresh/stale cache failover.
- Full tab-coverage registry.

## Not verifiable in the build environment

- User-specific API authentication.
- Paid entitlements and exchange licenses.
- Live provider schema variants tied to an account.
- Public endpoint reachability from the final deployment network.
- Third-party uptime after validation.

Use `verify_live_connections.py --strict` on the deployment machine.
