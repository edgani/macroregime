# MacroRegime Pro patch notes

## Objective
Keep the existing app baseline/UI, but harden the quad engine, front-run radar, and catalyst filter so the system is less prone to proxy-driven structural flips and less reliant on static watchlists.

## What changed
- Structural quad path is now slower than monthly weather:
  - structural level and momentum are damped when observed macro coverage is weak and proxy share is high
  - structural slowdown / shock modifiers are also damped before scoring
- `build_news_catalyst_overlay()` is now an event-lite catalyst filter:
  - still uses market-implied pressure
  - now also ranks the scheduled catalyst calendar by family relevance and proximity
  - output is explicitly catalyst/event-lite, not a literal news reader
- `build_forward_radar()` now derives the watchlist from near-ready opportunities plus route/catalyst state instead of a hardcoded static quad map
- Markets page no longer duplicates separate Opportunities / Signal Strength tabs:
  - both are still available in expanders above the market tabs
  - per-market tabs stay action-focused

## What was verified
- `app.py` compiles successfully with `python -m py_compile app.py`

## What is not verified yet
- Full live Streamlit runtime with external data providers
- Walk-forward / OOS validation of the updated structural damping
- Whether the output now matches Hedgeye more closely in all historical periods
- Whether the event-lite catalyst ranking is optimal across all regimes

## Remaining risk
This patch reduces obvious design problems, but it is not a claim of full Hedgeye parity or full production validation. It is a cleaner, more honest base for further GitHub iteration.
