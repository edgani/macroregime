# Market Opportunity OS v3.1 — Story / Expectation Optionality

Base: v3.0 Market Opportunity OS, itself upgraded from Opportunity Intelligence Engine v2.6.

## Added
- IHSG Narrative/Story Optionality module.
- US Expectation Optionality module.
- Loss classification that explicitly separates turnaround/investment-led losses from structural bad losses.
- Cash-runway, debt/cash and share-count dilution-risk checks.
- R&D/revenue and capex/revenue investment-intensity context.
- US next-year EPS trend, 30-day EPS revision breadth, analyst count and next-year revenue-estimate growth via yfinance.
- Same-sector Price/Sales valuation fallback for loss-making US/IHSG stocks; minimum four valid peers and no whole-market fallback.
- Story/expectation fields added to US/IHSG vertical tables and Market Memory snapshots.
- One-click Windows launcher with isolated `.venv`.

## Guardrails
- `loss-making` alone contributes zero positive evidence.
- Story optionality can add at most one evidence family.
- US confirmation requires analyst revisions to agree with the fundamental inflection.
- Structural bad loss / high financing risk can add deterioration evidence.
- IHSG remains cash-only; no leverage/options behavior was enabled.
- Missing data remains gated.

## Validation
Run `python tests/run_all.py` for the full local contract suite.
