# Opportunity Intelligence Engine v1.5 — Auto Decision View

## What changed
- No scan button required. First load automatically scans every asset in the selected markets.
- Market-selection changes automatically trigger a new scan.
- Cached public data is reused for ~30 minutes; an optional manual refresh remains available.
- Macro gate, market scan, and near-term scenario discovery run together.
- Daily workflow is one `OPPORTUNITIES` workspace with expression sub-views:
  - `BUY & HOLD · STOCKS`
  - `SPOT / CASH`
  - `LEVERAGED LONG / SHORT`
  - `OPTIONS · CALL / PUT`
  - `EARLY RADAR`
- Causal chains and scenario branches only appear inside the selected opportunity when they materially affect the decision.
- Options are only surfaced after a directional thesis gate; the selected US option candidate additionally checks live expiry, ATM IV, bid/ask spread, OI, and implied move. This is still research-gated, not a production option-pricing alpha model.
- No classic technical indicators are used.

## Data behavior
- US/IHSG equities: Yahoo market + public quarterly company financial metadata.
- Crypto: CoinGecko market/supply first; DeFiLlama used for available protocol revenue economics.
- FX/commodities: lightweight market-price/history adapter so startup does not waste company-financial calls.
- Macro: embedded Macro + Action engine.
- Scenario evidence: cached public news discovery.

Current-at-fetch is not the same as production-complete PIT coverage. Missing critical data lowers the action state rather than being filled with fake precision.

## Run
Windows:
`run_windows.bat`

Linux:
`./run_linux.sh`

Or:
`python -m streamlit run app.py`
