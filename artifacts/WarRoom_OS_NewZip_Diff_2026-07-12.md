# War Room OS — New ZIP Diff Report

Source: `warroom_os_COMPLETE (6).zip`  
Compared with: `warroom_os_COMPLETE (20).zip`

## Exact archive comparison

- Both archives: 232 entries, 216 files.
- Identical files: 213.
- Added files: 0.
- Removed files: 0.
- Changed files: 3.

| Changed path | Old bytes | New bytes | New SHA-256 |
|---|---:|---:|---|
| `warroom_os/gcfis/engines/entry.py` | 5,441 | 9,061 | `c27f213f52662d96…` |
| `warroom_os/gcfis/orchestrator.py` | 17,222 | 17,330 | `84d38d49066434a0…` |
| `warroom_os/run.py` | 14,545 | 14,756 | `7be72e604375ef6d…` |

## Functional meaning of the patch

1. `run.py` now forwards a flattened OHLCV dictionary into `run_gcfis`.
2. `gcfis/orchestrator.py` forwards per-ticker OHLCV into the entry engine.
3. `gcfis/engines/entry.py` adds true ATR and activates `risk_range_hedgeye.py` when at least 60 OHLC rows exist.

## What the patch does not fix

- Fixed `{"chop": 1.0}` is still passed into the decision pipeline.
- MTF is still computed after the decision.
- The UI setup is recomputed through a different fallback path.
- EV still reads a nonexistent `sig.entry` field instead of `entry_px`.
- Global metric grades are still not enforced.
- `validate_all.py` still ignores child return codes.
- Pytest still collects zero tests from the legacy test file.
- `dashboard.html` is still absent.

## Diff verdict

This is an entry-path patch, not a complete architectural rebuild. Because the new branch promotes an empirically rejected range formula without evidence gating, the patch increases production risk despite adding useful OHLC plumbing and a true-ATR helper.
