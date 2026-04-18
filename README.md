Review patch based on app(210).py baseline.

What changed:
- Keeps legacy UI feel/styles and all legacy functions in the file
- Replaces old nested main navigation with:
  Dashboard / US Stocks / IHSG / Forex / Commodities / Crypto / Risk / Diagnostics
- Adds a workflow-style dashboard with connected boxes and market branch cards
- Keeps legacy deep-dive sections inside dashboard tabs / market expanders
- Reworks market pages to action-first surface

Notes:
- This is a review patch for app.py only.
- It preserves the original single-file logic and rewires the flow on top.