# Final true-root Q1 fix notes

## What was actually wrong
The structural quad engine was still dominated by level logic, not rate-of-change logic.

That mechanically biases the model toward:
- Q2 when growth proxies are positive and inflation proxies are slightly positive
- Q4 when growth proxies roll over and inflation proxies cool

That is not how a Hedgeye-style quad should work. The quad should care about growth and inflation accelerating or decelerating.

## What changed
1. Structural climate now uses rate-of-change first:
   - observed acceleration flags: `indpro_acc`, `payrolls_acc`, `lei_acc`, `cpi_acc`, `corepce_acc`
   - proxy fallback slope logic: 1M versus 3M/3 for equities, oil, gold, breakeven, dollar

2. Structural inflation no longer defaults to positive just because the level of CPI or oil is positive.

3. Structural penalty now uses a structural-specific proxy estimate:
   - `1 - structural_obs_reliability`

## Why this matters
If the real world is Quarterly Q1 / Monthly Q2, the model must allow:
- structural growth ROC positive
- structural inflation ROC negative
- monthly weather still tactical reflation

The old block could not do this cleanly because positive inflation levels kept shoving structural to Q2.
