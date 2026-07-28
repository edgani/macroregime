# V6.5 Institutional Research Architecture

## Design objective

Build a decision system whose active surface is at least as disciplined as an institutional research stack, without pretending that public or incomplete data can guarantee superior hedge-fund returns.

The architecture separates eight causal functions:

1. **Structural state** — macro, leverage, liquidity and regime context.
2. **Origin** — earnings, pricing, capacity, inventory, policy or protocol changes.
3. **Expectations gap** — consensus, guidance, revisions and implied distribution.
4. **Economic transmission** — customer-supplier, production network and bottlenecks.
5. **Position vulnerability** — OI, borrow, funding, basis, options and crowding relative to depth.
6. **Trigger/amplification** — signed flow, dealer hedge, liquidation and forced deleveraging.
7. **Value capture** — the listed security that actually receives revenue, margin, fee or scarcity rent.
8. **Execution/risk** — entry state, liquidity, invalidation, sizing and capital gates.

## Market-specific engines

### US equities

Required production inputs:

- point-in-time SEC filings and corporate actions;
- point-in-time analyst estimates, guidance and revisions;
- stock-level option surfaces and signed open/close participant flow;
- borrow fee, utilization and lendable supply;
- ETF/index membership and passive flow;
- economic customer-supplier and product/capacity mapping.

### IHSG

Required production inputs:

- historical ticker-by-broker activity and inventory persistence;
- crossing and negotiated-market adjustment;
- foreign/local flow and done-detail distribution;
- free-float, controller, placement, rights, warrant and lock-up history;
- point-in-time company fundamentals and commodity/import exposure;
- issuer/customer/project and capacity mapping.

### Commodities

Required production inputs:

- release-time-adjusted COT/TFF and contract OI;
- complete futures curve and rolls;
- inventory vintages and surprises;
- physical basis, freight, storage and outages;
- option IV/Greeks and signed participant flow where available;
- producer/consumer hedging and capacity response.

### FX

Required production inputs:

- policy-path surprises and real-rate expectations;
- CFTC participant positioning with publication lag;
- cross-currency basis and dollar funding;
- options risk reversal, term structure and signed flow;
- external debt, reserves and intervention vintages;
- terms of trade and commodity transmission.

### Crypto

Required production inputs:

- venue-specific OI, basis and funding;
- aggressor trades and order-book depth;
- explicit long/short liquidation by venue;
- exchange and bridge flows;
- stablecoin liquidity, unlocks, treasury and protocol fee/value capture;
- fragmented-liquidity and collateral-regime normalization.

## Promotion ladder

No component may skip a stage:

1. Mapping complete.
2. Data lineage and availability verified.
3. Canonical replication.
4. Strong baseline comparison.
5. Frozen validation.
6. Untouched lockbox.
7. Global multiple-testing correction.
8. Stability and ablation.
9. Non-micro/capacity and actual cost reconstruction.
10. Cross-era/market no-retuning replication.
11. Prospective watch with frozen parameters.
12. Signed limited-production receipt.
13. Human-approved limited capital.

## Active-kernel rule

A component can be active only inside its proven scope. A descriptive component may describe. An archive-supported component may support research. Neither may become a ticker score, direction, target, sizing input or capital permission without the later gates.

This removes a common institutional failure mode: sophisticated-looking dashboards quietly combining unvalidated signals into one confident score.
