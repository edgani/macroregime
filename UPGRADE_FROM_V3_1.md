# Upgrade from v3.1

v3.2 is deliberately additive.

## Preserved without replacement
- Macro Decision Engine and crash/risk governor.
- Existing v3.1 Story / Expectation Optionality module.
- IHSG Index Alpha / Invezgo transaction intelligence.
- Existing causal graph and scenario discovery.
- Existing valuation / expression / entry decision logic.
- Existing `state/market_memory.sqlite` snapshot memory.

## New longitudinal layer
`state/opportunity_memory.sqlite` stores immutable first-detection events separately from existing Market Memory.

This prevents a future outcome, revised fundamental, later analyst estimate, or later lifecycle state from overwriting what was actually known when the opportunity first appeared.

The new `OPPORTUNITIES` page is the longitudinal tracker. The original v3.1 daily UI remains under `DECISION DESK` for direct comparison and regression checking.
