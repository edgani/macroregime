# Structural swing audit

This hotfix addresses the instability that caused structural quad to swing from Q2 to Q4 under sparse FRED coverage.

## Actual mechanical problems fixed
1. Structural raw score was **not reliability-scaled**. A few observed negative quarterly fields could dominate the score even when structural observation coverage was low.
2. Structural growth/inflation momentum thresholds were **too tight**, so ordinary quarterly cooling could flip the structural sign too easily.
3. Structural inflation block excluded **core PCE**, making the inflation climate too dependent on CPI/core CPI plus breakeven.
4. Structural regime modifiers were too friendly to Q4/Q3 under weak growth momentum.
5. Structural confidence penalty used broad macro proxy share instead of a structural-specific proxy estimate.

## Key code changes
- Reweighted `STRUCT_W` to favor level over momentum.
- Softened `QUAD_MOD` so Q4 is not won too easily by a small negative growth momentum print.
- Added `corepce_qtr_yoy` and `corepce_qtr_delta` to structural inflation.
- Added `structural_level_scale` and `structural_mom_scale` tied to `structural_obs_reliability`.
- Structural score now uses `structural_proxy = 1 - structural_obs_reliability`.

## What this is meant to do
- Stop hard structural swings caused by sparse quarterly observations.
- Keep structural climate slower and more level-driven.
- Leave monthly/weather and scenario/front-run layers faster.
