# app.py Flow Review Patch

This patch replaces the repo `app.py` only.

What it does:
- keeps the current modular repo and snapshot pipeline
- preserves existing engines/features/orchestration
- restructures the app into:
  - Dashboard
  - US Stocks
  - IHSG
  - Forex
  - Commodities
  - Crypto
  - Risk
  - Diagnostics
- uses a connected workflow / control-tower dashboard
- uses ticker-first market pages
- keeps IHSG buy-only and non-IHSG long/short surface
- reuses existing detailed pages inside expandable sections

How to use:
1. backup current `app.py`
2. replace repo `app.py` with the file in this patch
3. run:
   `streamlit run app.py`