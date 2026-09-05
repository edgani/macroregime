# Market Opportunity OS v3.0

v3.0 upgrades v2.6 rather than replacing it. The invariant is: one shared intelligence kernel, market-specific data/causal adapters, and fail-closed decisions.

## Shared kernel

1. data validation
2. point-in-time normalization
3. baseline
4. change: level / velocity / acceleration / breadth / persistence / novelty
5. sequence memory
6. cross-confirmation
7. quality / anti-manipulation
8. state / regime
9. earliness / crowding
10. payoff / risk
11. decision
12. execution (separate)
13. outcome
14. Market Memory + OOS validation

There is no universal "Alpha Score" that allows one strong family to hide a fatal gate.

## Vertical engines

### On-chain
Core: wallet activity, liquidity, usage, ecosystem, quality, memory. v3 adds a free DeFiLlama chain radar using TVL, chain stablecoins, DEX activity, fees and revenue as separate confirmations. Wallet/social/narrative data remain independent adapters and are not inferred from TVL.

### Liquid crypto
Core target: spot flow, open interest, funding, liquidations, liquidity, memory. v3 retains value-capture economics but keeps leverage gated until the positioning adapters are complete.

### US stocks
Core target: fundamentals, estimate revisions, capital flow, causal chain, valuation, memory. Existing fundamentals and causal opportunity logic remain; full PIT revision/flow coverage remains a production gate.

### IHSG
Core target: fundamentals, broker flow, foreign flow, corporate actions, valuation, memory. The v2.6 broker accounting guardrails are unchanged: broker transaction evidence contributes at most one independent family.

### FX
Core target: relative rates, macro surprise, central bank policy, positioning, valuation, memory. Price-only data do not become directional alpha.

### Commodities
Core target: physical supply/demand, inventory, curve, positioning, memory. Price-only data do not become directional alpha.

## Market Memory

`state/market_memory.sqlite` is append-only for observations. Current observations are scored against prior stored snapshots before being appended, preventing the current observation from leaking into its own baseline. Sequence signatures compress repeated states while preserving event order.

## DeFiLlama

Free API only by default. No API key is required. The adapter intentionally separates TVL from stablecoins, DEX volume, fees and revenue because TVL can move mechanically with token prices.

## Remaining research gates

- social/X/Discord breadth and bot/co-ordination filtering
- generalized wallet-specialty/convergence data across chains
- liquid-crypto OI/funding/liquidation adapter
- US PIT estimate-revision and institutional-flow history
- IHSG corporate-action/ownership PIT enrichment beyond current transaction layer
- FX relative-rate/positioning/REER/BoP production adapter
- commodity physical inventory/curve/supply-demand production adapter
- calibrated outcome/backfill and multiple-hypothesis-controlled OOS model selection
