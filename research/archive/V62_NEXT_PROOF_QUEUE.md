# V6.2 Next Proof Queue

This queue is ordered by causal value and incremental data content, not by ease of producing attractive backtests.

## P1 — SEC filing-origin panel

**Claim:** A filing-time combination of revenue acceleration, margin inflection, inventory/capex state, share supply, and valuation/repricing gap improves extreme-winner recall over momentum and volatility.

Required:

- All listed and delisted U.S. issuers, 2009 onward.
- SEC filing/accession date as availability.
- Original versus amended filings separated.
- Corporate actions, ticker/CIK history, spinoffs and delistings.
- Quarterly flow normalization and taxonomy alias handling.
- Price/market-cap data aligned only after filing dissemination.

Frozen outcomes:

- +20%/21d, +30%/63d, +50%/126d, +100%/252d.
- Remaining return after selection.
- MFE, MAE, lead time, recall@K, precision@K.
- Baselines: momentum, ATR, size, simple earnings growth.

## P2 — Expectation-gap reconstruction

**Claim:** Point-in-time revenue/EPS revision velocity and guidance-versus-consensus gap identify winners before the majority of price repricing.

Required:

- Daily PIT analyst consensus and individual estimates.
- Number of analysts, stale-estimate controls, dispersion and revision direction.
- Company guidance with timestamp and comparable accounting basis.
- Estimate history that is not overwritten by later vendor revisions.

No price-derived proxy may inherit this claim.

## P3 — Economic production network

**Claim:** Dated demand/pricing/qualification shocks at customers or constrained upstream nodes predict value capture at linked suppliers.

Required:

- Customer-supplier links with effective dates and revenue concentration.
- Customer qualification/award language from filings and calls.
- Product-level substitutability, lead time and capacity.
- Actual input-output or product graph, not return-correlation clusters.

## P4 — Position scarcity and signed options

**Claim:** Fundamental origin plus borrow scarcity or signed option demand predicts acceleration and squeeze probability better than origin alone.

Required:

- Borrow fee, utilization, lendable supply, recalls and short demand.
- Option buy/sell, open/close, participant capacity, OI vintage, IV/Greeks and underlying depth.
- Ablation: origin only versus position only versus interaction.

Gross OI and headline short interest are not accepted substitutes.

## P5 — IHSG broker inventory

**Claim:** Crossing-adjusted broker inventory persistence plus free-float/controller structure and fundamental origin identifies accumulation before visible thematic surges.

Required:

- Full ticker-by-broker daily history.
- Negotiated/crossing adjustment.
- Foreign/domestic flow without assuming beneficial owner from broker code.
- Corporate-action and free-float vintage.
- Done-detail/lot-size data where legally available.

## P6 — Commodity physical origin

**Claim:** Inventory surprise, curve/basis tightening and capacity/logistics constraints identify physical surge before price acceleration; COT/OI determine whether positioning confirms, opposes or amplifies it.

Required:

- Release-vintage inventory and production data.
- Full futures curve and rolls.
- Physical basis, freight and storage.
- Participant positions, option skew and liquidity.

## P7 — Crypto leverage path

**Claim:** Origin demand/liquidity impulse plus OI/funding build and liquidation-distance-to-depth predicts cascade onset and exhaustion.

Required:

- Multi-venue archived trades, OI, funding, basis, depth and explicit liquidation flags.
- Exchange/on-chain flows, stablecoin issuance/redemptions, unlock and treasury selling.
- Venue outage and coverage controls.

## Promotion sequence

1. Frozen mapping and source lineage.
2. Canonical replication.
3. Point-in-time reconstruction audit.
4. Validation and untouched lockbox.
5. Global multiplicity correction.
6. Calibration, lead time, false alarms, MFE and MAE.
7. Ablation and no-retuning transportability.
8. Prospective signed evidence.
9. Only then non-zero live weight.
