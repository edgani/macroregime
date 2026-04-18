# Final Structural Parity Audit Notes

This patch targets the specific failure mode where the app could still print a structural Q2 even when the truth layer was weak or contaminated by monthly/tactical proxies.

## Root causes fixed

1. **Quarterly climate was not truly quarterly**
   - The old structural block used last-print / mixed monthly inputs and even 3M price proxies.
   - That let a single monthly CPI/oil move leak into the structural climate call.

2. **Structural inflation was over-pulled by oil/gold/USD proxy features**
   - Oil 3M / Gold 3M / UUP 3M lived inside the structural inflation block.
   - That mechanically biased structural toward Q2/Q3 whenever commodity shock tape was hot.

3. **Structural growth was over-pulled by SPY/XLI/XLY/IWM tape proxies**
   - That let risk-on tape masquerade as quarterly growth truth.

4. **FRED fetch failure could collapse the truth layer into all-proxy mode**
   - Empty series were returned directly.
   - No disk fallback existed.

## What changed

### A. Quarterly-smoothed observed climate features were added
New observed features now include:
- `indpro_qtr_yoy`, `retail_qtr_yoy`, `payrolls_qtr_yoy`, `housing_qtr_yoy`
- `cpi_qtr_yoy`, `core_cpi_qtr_yoy`, `corepce_qtr_yoy`
- `breakeven_qtr_avg`
- matching quarterly deltas vs prior 3M block

These are built from:
- trailing 3-month average of YoY series
- delta of the current 3M block vs prior 3M block

This makes structural climate slower and much closer to the intended quarterly interpretation.

### B. Structural block is now observed-first
Structural growth and inflation now primarily use quarterly-smoothed observed FRED features.

The old tape-heavy proxy features remain, but only in the mixed/monthly weather layer.

### C. Structural shock and slowdown flags were separated
New fields:
- `structural_slowdown_flags`
- `structural_inf_shock`

`build_quad()` now uses those for the structural block instead of reusing the monthly/tactical flags.

### D. FRED fetch got local disk fallback
- Successful FRED series are now saved under `.cache/fred_series/`
- If live fetch fails later, the app can reuse the last good local copy
- Fetch retries were added
- FRED TTL reduced to 600s

## Intended effect

- Monthly shock should no longer force structural Q2/Q3 as easily
- Structural should be harder to contaminate with oil/gold/USD/tape noise
- If FRED works, the climate layer should be materially closer to Hedgeye-style quarterly behavior
- If FRED is temporarily down after at least one good run, the app should degrade much better

## Still not fully solved

- If there is **never** a successful FRED pull and no local cache exists, the app still cannot manufacture true quarterly macro truth out of thin air
- Full date-by-date Hedgeye parity still requires explicit parity harness / calibration against public timestamps
- This patch fixes a major architecture/formula issue, but does not claim exact 100% Hedgeye replication yet
