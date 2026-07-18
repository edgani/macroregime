# Live Data Activation — War Room OS

## What this build guarantees

The code path is fail-closed:

- no synthetic production values;
- missing data is never converted into neutral or zero;
- each provider is isolated;
- fresh cache and stale last-good cache are labeled separately;
- network/provider errors render `ERROR`, `OFFLINE`, `NOT_CONFIGURED`, `EMPTY`, or `STALE` without taking down the dashboard;
- every event retains provider, dataset, timestamp, record count and semantic caveat.

This cannot guarantee third-party uptime, entitlement, exchange licensing, or an unchanged vendor schema. Run `verify_live_connections.py --strict` on the deployment machine after adding credentials.

## Data planes

### Event plane

- Unusual Whales: option trades/alerts, Greek flow, GEX, IV, sector/industry option flow.
- Massive: raw stock/options trades and true TRF/off-exchange prints when exchange/TRF fields identify them.
- SEC EDGAR: Form 4, 8-K, 13D/G, 13F, 10-Q/K, S-1 and offering filings.
- Nansen: provider-classified Smart Money holdings/net flow.
- Arkham: labeled entity/address transfers.
- Licensed IDX bridge: broker, foreign flow and order-book events.

### State plane

- Binance, Bybit, OKX: perpetual price, OI, funding and available crowding/taker fields.
- Deribit: BTC/ETH option book summary, IV and OI.
- Massive: US option-chain OI, volume, IV, quotes, trades and Greeks.
- ORTEX: estimated/live short interest, cost-to-borrow, days-to-cover and free float.
- Intrinio: settlement short interest, earnings, ownership, estimates and ETF NAV flow.
- CoinGlass: normalized cross-exchange OI/funding/liquidations and heatmap/map.
- Databento bridge: exchange futures/options statistics, trades and instrument records.
- EIA: physical petroleum and natural-gas data.
- CFTC PRE: weekly TFF and disaggregated COT datasets.
- SEC XBRL: filed company fundamentals.

## Direction, squeeze, target and duration semantics

War Room does not output a fake certainty score.

### Direction context

Direction is built from evidence layers:

1. price × OI state;
2. funding and account/taker imbalance;
3. option directional delta flow and premium balance;
4. volatility demand/supply from directional vega;
5. IV skew and term structure;
6. gamma/GEX context;
7. short interest, borrow cost and days-to-cover;
8. price acceptance/rejection and liquidity/reference zones.

The result is `UPSIDE_PRESSURE_CONTEXT`, `DOWNSIDE_PRESSURE_CONTEXT`, or `BALANCED_CONTEXT`, never a calibrated probability unless a separate frozen OOS model proves calibration.

### Short/long squeeze

A squeeze context requires crowding plus a forcing mechanism plus price confirmation. Open interest alone cannot determine direction. The dashboard exposes every driver and labels the output as a pressure index.

### Targets

Displayed “targets” are reference zones:

- expiry-implied expected move;
- call/put wall;
- positive/negative GEX concentration;
- zero-gamma/gamma-flip level when supplied;
- modeled liquidation clusters;
- price/risk-range levels from the core engine.

They are not guaranteed destinations.

### Duration

Duration context is anchored to observable horizons:

- option expiry/DTE;
- 5-minute flow persistence buckets;
- funding interval;
- intraday OI history;
- reporting cadence for SEC/CFTC/short interest;
- current regime persistence.

It does not predict an exact completion date.

## Activation order

1. Copy `.env.example` to `.env`.
2. Set `WARROOM_SEC_USER_AGENT` to a real application/contact identity.
3. Add paid provider keys only for subscriptions you own.
4. Install normal and streaming dependencies.
5. Start persistent workers for UW, Massive and Databento when entitled.
6. Check every worker `/health` endpoint.
7. Run `python verify_live_connections.py --strict --write-report`.
8. Run `streamlit run app.py`.

## Required commands

```bash
pip install -r requirements.txt
pip install -r requirements-streaming.txt
python validate_live_stack.py
python verify_live_connections.py --write-report
streamlit run app.py
```

## Provider activation caveats

- Unusual Whales Kafka messages are protobuf. Set `UW_KAFKA_DECODER_MODULE` to the decoder generated or supplied for the entitled schemas.
- Massive options and stock WebSockets require explicit subscriptions permitted by the account.
- Databento uses one dataset per live session; run another bridge process for another dataset.
- IDX broker/foreign/order-book data requires a legitimate licensed source and the schema contract documented in `.env.example`.
- Form 13F and official short interest are delayed by their reporting schedules and must not be treated as intraday signals.
