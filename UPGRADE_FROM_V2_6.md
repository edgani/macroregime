# Upgrade from v2.6

v3.0 is an additive upgrade. Existing IHSG logic is preserved.

New files:

- `opportunity_kernel.py` — shared baseline/change/sequence/readiness logic
- `market_memory.py` — timestamped SQLite Market Memory
- `defillama_adapter.py` — free DeFiLlama ecosystem adapter
- `verticals.py` — market-specific feature families/readiness
- `data/onchain_watchlist.csv` — chain watchlist
- `V3_ARCHITECTURE.md` — architecture contract

UI additions:

- `CONTROL ROOM`
- `VERTICALS` with separate On-chain / Crypto / US / IHSG / FX / Commodity views

No API key migration is required. Existing `INDEX_ALPHA_API_KEY` and `INVEZGO_API_KEY` configuration remains unchanged.
