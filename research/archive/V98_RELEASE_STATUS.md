# War Room OS V9.8 — Unified Decision Packet

## What V9.8 repairs

V9.7 separated parts of one trading decision across unrelated tabs and left the dashboard mostly
`NO_DATA`. V9.8 reconnects official/public source receipts and current execution-reference quotes to
the runtime, then attaches the complete reasoning and execution chain to the selected ticker.

The eight primary tabs are now:

1. Mission Control
2. Macro & Risk
3. Alpha Center
4. US Stocks
5. IHSG
6. Crypto
7. Commodities
8. FX

The following are no longer separate primary tabs:

- Price Projection
- Flow & Positioning
- Causal Chain & Bottlenecks
- Execution Control
- Data Integrity & Reality
- Validation

For each selected ticker, the same packet now contains decision state, quote, causal chain,
market-specific flow/positioning, value-capture projection, entry/stop/target, sizing, execution state,
and proof/data lineage. Detailed source and proof diagnostics sit inside the collapsed **Data & Proof**
drawer.

## Important runtime repairs

- Quote collection now runs before the desk is built.
- Public acquisition receipts are hash-validated and read by the dashboard.
- One failed source cannot erase successful sources from other markets.
- A failed quote refresh keeps the last-known record visible as stale context instead of overwriting it
  with an empty file. A stale/context quote is never execution-fresh or predictor-eligible.
- A research projection is scoped to the exact ticker path and cannot promote capital by itself.
- HUMI is present in the IHSG execution-reference selector; inclusion is explicitly not a recommendation.
- Technical predictors remain zero.
- Auto-submit remains disabled.

## Validation

- Limited-production control-plane adversarial validation: **40/40 PASS**
- Unified architecture, packet, UI and quote-resilience validation: **33/33 PASS**
- Combined: **73/73 PASS**
- Current offline ticker packets built: **17** across **5/5 markets**
- Primary navigation: **8/8**

## Honest current status

The V9.8 architecture and control plane are ready. The bundled build contains a hash-valid current US
security-master snapshot, but the build container has no live execution quotes. Bound exact-market
proof remains **0/5**, fully proven live markets remain **0/5**, and capital remains **BLOCKED**.

This is intentional: context remains readable while a missing proof produces `NO_TRADE`, not a blank
dashboard and not a fabricated signal.
