# Final hardening notes

This bundle consolidates the highest-EV hardening changes into a single package:

- Fresh-first app open behavior with explicit modes: Smart fresh / Force rebuild / Snapshot only.
- Smart tail-refresh for history loading so stale or missing symbols refresh without forcing a full rebuild.
- Display/live quote layer separated from historical close, with fallback to last close and quote metadata propagated into tables.
- Non-crypto Yahoo history now uses `auto_adjust=False`.
- Shared-core duplicate validation/execution passes removed.
- Runtime universe selection can now return both selected universe and route metadata in one call via `build_runtime_plan(...)`.
- Basic smoke/regression guard added in `tests/` and `scripts/run_smoke_checks.py`.
- Stale bundled snapshot files removed from the package so first-open does not silently inherit old state.

## Validation performed

- `python scripts/run_smoke_checks.py`
- Includes compileall + unittest discovery (`tests/`)
- Offline smoke build forced with `MRP_LIVE_FETCH=0`

## Remaining limits

- Quote layer is still best-effort retail-grade, not exchange-grade real-time.
- Historical analytics still depend on the upstream coverage of Yahoo/CoinGecko/FRED and local history availability.
- A deeper next step would be per-market quote adapters (US / IHSG / FX / commodities / crypto) rather than a shared retail quote path.
