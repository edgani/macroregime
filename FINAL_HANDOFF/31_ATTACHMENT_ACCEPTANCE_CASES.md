# Attachment-Driven Scenario Acceptance Cases

The user-supplied screenshots/video were treated as **scenario hypotheses to verify and structure**, not as authoritative facts or direct trade signals.

## Case 1 — Weak housing/labor vs hawkish policy
Screenshot claim: weak housing plus CPI/PPI/NFP/retail should perhaps remove hawkishness.

Required EROS behavior: do **not** apply a one-variable textbook map. Reconcile weak real activity with still-elevated inflation, supply shocks, policy communications and long-end/fiscal conditions. Output a **conflicted reaction-function scenario**, not “hawkish dead” or “hawkish guaranteed.”

Acceptance: PASS (`SCN_POLICY_CONFLICTED_REACTION_FUNCTION`).

## Case 2 — OpenAI / Anthropic mega IPO and “need to support the index”
Screenshot hypothesis: mega IPO valuation creates an incentive/“obligation” to keep indices strong.

Required EROS behavior: identify observable capital-formation/index-mechanics channels — offering size, valuation, free float, index eligibility, passive flows, rebalance demand, liquidity diversion — while rejecting an unverified motive claim that anyone is *obligated* to prop up the index.

Acceptance: PASS (`SCN_MEGA_IPO_CAPITAL_SUPPLY_INDEX_REFLEXIVITY`).

## Case 3 — Data-center securitization and “2008 in the making”
Screenshot hypothesis: easier data-center securitization could recreate 2008.

Required EROS behavior: identify structural similarities (leverage, opacity, SPVs/securitization, maturity mismatch, refinancing dependence, correlated collateral/cash-flow assumptions) but require actual underwriting deterioration, losses and forced balance-sheet transmission before escalating to a crisis scenario.

Acceptance: PASS as `2008_ANALOGUE_CANDIDATE_NOT_EQUIVALENCE` (`SCN_AI_DATACENTER_LEVERAGE_FRAGILITY`).

## Case 4 — QQQ GEX / options-flow video
The 53-second video visibly uses QQQ gamma-exposure, put/call gamma and VIX/flow context to infer short-horizon resistance/support and dealer behavior.

Required EROS behavior: GEX may only be a `MARKET_STRUCTURE_TIMING_MODIFIER`, `FRAGILITY_MODIFIER`, or `EXECUTION_CONTEXT` unless independent PIT/OOS history validates more. It may **not** become standalone macro directional alpha.

Acceptance: PASS (`SCN_DEALER_GAMMA_VOLATILITY_REGIME`).

## Guard
All four scenarios currently have numeric probability = `null`, timing/duration = `UNKNOWN_UNCALIBRATED`, and no forced production trade.
