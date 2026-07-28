# War Room OS v2.2 — Arrow lineage, missing-market and load-time fixes

## Arrow audit verdict

The previous arrows were not trustworthy enough for decision use.

### Root causes removed

1. **Mission Control assigned candidates by display index/modulo.**
   This could visually connect IHSG to `SI=F`, Crypto to a US equity, or FX to a ticker even when FX had no data.
2. **Several workspaces used Cartesian `connectAll`.**
   Every source node was connected to every output node even when no actual data lineage existed.
3. **No-data nodes could still appear to transmit a causal signal.**
4. **Arrowheads were always blue even when the line was green, magenta, yellow or structural purple.**
5. **Long setups could be promoted under a `LEAN_SHORT` market state.**

### New arrow contract

Every edge now has:

- explicit `from` and `to` entity;
- relation type;
- evidence class (`OBSERVED`, `INFERRED`, `STRUCTURAL`);
- state;
- optional active-flow flag;
- source/target data gate.

Mission Control now shows at most one aligned candidate per market and positions it directly below its parent market. A market with `NO_DATA` cannot emit a candidate arrow.

## Data/load fixes

- Yahoo market downloads are batched and reused for both Close and OHLCV.
- The previous loader downloaded each ticker twice and sequentially; that path was removed.
- Every missing market now receives its own fallback attempt even when another market loaded successfully. This specifically fixes the case where US loaded but FX stayed permanently empty.
- A delayed/free yfinance option-chain fallback is available when Massive is not configured. It supplies OI, volume, IV, quotes and estimated Black-Scholes delta/gamma. It is explicitly **not live options flow**.
- Alpha Center OBSERVED mode now displays only live-gated, direction-aligned candidates instead of always showing `NO_DATA`.
- Company Intel remembers the ticker selected from any queue/node.
- Commodity and FX derivative context can consume Databento/CFTC records. IHSG is explicitly labeled cash long-only rather than pretending an equity-derivatives feed exists.

## Still requires configuration

The following cannot become live without the relevant credential/entitlement or bridge:

- Unusual Whales live options/Greek flow;
- Massive TRF and live options data;
- ORTEX/Intrinio short-interest data;
- Nansen/Arkham institutional crypto intelligence;
- licensed IDX broker/foreign/order-book feed;
- Databento live futures statistics.

Missing providers remain `NOT_CONFIGURED`, `NO_DATA`, `STALE` or `ERROR`; no mock record is inserted.
