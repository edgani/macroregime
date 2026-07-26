# War Room OS V6.0 — Deep Early-Move Driver Research

## Bottom line

Open interest and long/short liquidation improve **attribution**, but do not by themselves solve early discovery. Total OI is symmetric; realized liquidation is usually a transmission event after the move begins. The research architecture is therefore frozen as:

`origin → vulnerability → trigger → transmission/amplification → exhaustion`

## Empirical work completed

- Total empirical claim records accounted: **215,788**.
- Price/volume extreme-move claims: **125,529**, production survivors: **0**.
- Historical maintained factor-pair claims: **89,464**.
- Historical full-gate factor pairs: **572**.
- Strict post-discovery robustness survivors: **61**.
- Fresh point-in-time stock-level production drivers: **0**.

The 61 factor-pair robustness survivors are an acquisition priority, not a live signal. Frequent families include net payout/external financing, volatility/ownership interactions and a small cluster involving institutional ownership conditional on extreme short interest.

## What changed after adding OI and liquidation logic

1. `price up + OI up` is no longer labeled long accumulation. It is ambiguous new risk until signed flow or participant books resolve the side.
2. New long building, new short building, short covering and long liquidation are separate states.
3. Side-specific liquidations are normalized to depth/ADV and classified as move-underway amplification.
4. Early cascade risk uses OI/leverage relative to depth, funding, basis, crowding and liquidation distance **before** forced orders print.
5. Fundamental/physical/expectation/broker/on-chain origin layers remain separate so the system can answer what actually started the move.

## Negative result that matters

Brute-forcing more public OHLCV formulas is not the path to SNDK-like early discovery. Across 125,529 massive-move price/volume claims, nothing passed the production gates. This falsifies the current data-ready implementations; it does not prove that every technical feature in existence is useless.

## Highest-value next evidence panels

- **US stocks:** point-in-time analyst revisions, filings/guidance, customer qualification, industry pricing/capacity, borrow fee/utilization, signed options/equity flow.
- **IHSG:** historical ticker-broker inventory, crossings, foreign flow, free float/controller and done detail.
- **Commodities:** COT/TFF plus inventory surprises, curve, physical basis, freight/storage and signed hedging flow.
- **FX:** rate-path surprise, TFF, funding basis, options risk reversal and intervention/reserve state.
- **Crypto:** multi-venue OI, funding, basis, taker flow, depth, liquidation distance/prints, spot/on-chain/stablecoin origin.

## Harness status

The derivatives test harness passes planted-signal, null and timing controls. It detects a planted origin/vulnerability signal, produces zero null survivors and does not promote realized liquidation as an early driver. This validates the harness, **not** a market edge.

## Governance

- Live predictive weight: `0.0`.
- Capital permission: `BLOCKED`.
- No ticker is relabeled proven.
- Every missing licensed/point-in-time panel fails closed.
- No unrestricted formula mining after outcomes.
