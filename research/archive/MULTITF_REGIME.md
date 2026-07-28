# Multi-timeframe regime + Live-only (this build)

## Multi-timeframe regime (your "monthly/weekly/daily + aggressive/defensive" ask)
`regime_multitf.py` + v40's `engines/gip_engine.py` (extracted, with config/). Mission Control now shows:
- **Structural** + **Monthly** quad — from GIPEngine (Hedgeye GIP; monthly = 80% price / 20% structural)
- **Weekly** + **Daily** quad — short-window growth/inflation momentum from price proxies
- **Posture** — AGGRESSIVE / DEFENSIVE / MIXED from how the timeframes align

Real-data example: structural+monthly+weekly **Q3 Stagflation**, daily **Q2 Reflation** →
**DEFENSIVE-tilt (rallies are tactical)**. That's your flexibility: lean defensive on the structural
anchor, play tactical longs when the short tape turns risk-on. HONEST: monthly weights in gip_engine
are hand-tuned (overfit flag in config) — structural is the anchor, short-tf is coincident tape.

Also extracted: `scenario_discovery_engine.py`, `quad_explainer.py` (why-this-quad / what-changes-it),
`regime_transition_engine.py` — available for the next wire-up.

## Live-only (removed historical + demo)
`app.py` now fetches live via v40's loaders and injects — no 2013-18 or demo modes.

## Dashboard fixes for the bugs you flagged
- **"needs FRED" now clears when live** (badge() gates it on `window.__LIVE`) — it was hardcoded.
- **"synthetic in mock" → "● live"** when real data present.
- **Markets not fetched this run show "NOT LOADED"** instead of stale mock prices (fixes IHSG BBCA 10,150
  showing when idx wasn't in the live run).

## Still to verify on YOUR machine (I can't fetch live here)
- Liquidity "—": v40's fred_loader fetches WALCL+RRP but not WTREGEN(TGA); liquidity computes from
  WALCL−RRP. If it still shows "—" live, paste the console — likely a live FRED key-name check.
- Cross-asset "—": needs the commodity/bond tickers in the live universe (they're in the markets list now).
- Per-market setups (IHSG/commodity/FX): need those markets to actually fetch + clear the conviction gate
  live; if 0, they now honestly show "no name cleared the gate" instead of mock.
