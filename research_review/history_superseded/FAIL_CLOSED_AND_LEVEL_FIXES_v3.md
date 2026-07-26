# War Room OS Patched Review v3 — Fail-Closed and Level Fixes

## Root cause of the CONSISTENCY_BLOCKED screen

The v2 guard treated any malformed setup row as a desk-wide critical error. Low-priced crypto rows were
particularly exposed because the fallback setup path used close-only data and rounded all prices to two
decimals. The entry engine also used absolute reward/risk distances, allowing directionally inverted levels
to retain a positive R/R before the downstream invariant check blocked the entire dashboard.

## v3 changes

- `price_setups.py` passes full OHLCV and ticker identity into `run_entry`.
- `entry.py` enforces `stop < entry < target` for longs and `target < entry < stop` for shorts before a
  setup can be valid.
- Breakout/continuation targets are extended beyond the current executable entry when price has already
  moved beyond the frozen risk range.
- Adaptive price precision preserves level separation for sub-$1 instruments.
- `consistency_guard.py` quarantines only malformed rows and preserves unrelated valid outputs.
- Unconfirmed Mission Control rotation names are withheld locally rather than blocking the desk.
- `app.py` distinguishes data unavailability, row quarantine and genuine critical consistency failure.
- `dashboard.html` shows LIVE only when `meta.source == LIVE`; BLOCKED/NO DATA can no longer appear as LIVE.

## Permission

These changes repair runtime correctness. They do not promote any setup, component or selector to proven
alpha. PAPER and LIVE permissions remain blocked by the existing validation gates.
