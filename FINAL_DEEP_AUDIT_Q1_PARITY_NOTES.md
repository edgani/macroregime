# Deep audit: structural parity mismatch vs Hedgeye Q1

## Concrete bugs found in live code
1. Structural climate was **not actually using** the quarterly observed block that had been computed.
   - The app computed `indpro_qtr_yoy`, `retail_qtr_yoy`, `payrolls_qtr_yoy`, `cpi_qtr_yoy`, etc.
   - But the live structural score still used `g_level/g_mom/i_level/i_mom`, which are proxy-heavy monthly style features.
   - Result: structural could still print Q2 under proxy-heavy conditions.

2. Structural confidence penalty still used **broad macro proxy share** instead of a structural-specific proxy estimate.
   - In `build_quad()`, structural scoring passed `proxy` rather than `1 - structural_obs_reliability`.

3. Structural slowdown and inflation-shock modifiers were still inherited from **monthly-style flags**.
   - `struct_sf` and `struct_shock` were derived from monthly `slowdown_flags` / `inf_shock`.
   - This contaminated quarterly climate with weather/tactical shock logic.

4. Structural observation reliability did not include **core PCE quarterly** in the inflation observation set.

5. `fetch_fred()` had no local last-good fallback.
   - A transient fetch failure could zero out the FRED layer and push the app into proxy-heavy mode.

## What was changed
- Structural score now uses quarterly observed features directly:
  - growth: `*_qtr_yoy`, `*_qtr_delta`, `ism_qtr_avg`, `unrate_qtr_delta`, `claims_13w_avg_delta`
  - inflation: `cpi_qtr_yoy`, `core_cpi_qtr_yoy`, `corepce_qtr_yoy`, `breakeven_qtr_avg`
- Added structural-specific:
  - `structural_level_scale`
  - `structural_mom_scale`
  - `structural_slowdown_flags`
  - `structural_inf_shock`
- Structural score now uses `structural_proxy = 1 - structural_obs_reliability`
- `fetch_fred()` now retries and falls back to `.cache/fred_series/<SID>.csv` if live fetch fails.

## Why this matters
The prior live code was still effectively doing:
proxy-heavy monthly-style block -> damp it a bit -> call it structural

That is the main reason the structural result could stay far from Hedgeye's climate call.
