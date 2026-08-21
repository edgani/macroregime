# Production Safety / Legacy Quarantine Verification

The supplied legacy Warroom code compiles and its legacy functional suite passes, but that is **software evidence only**. The legacy repository still contains synthetic fallbacks, price-momentum/technical paths and hardcoded narrative probabilities. See `LEGACY_QUARANTINE.md`.

The self-run production-facing entrypoint is `final_core/production_entry.py`. It imports only the new `final_core` scenario logic and does not import legacy Warroom modules. Uncalibrated scenarios are forced to `WAIT`; no numeric scenario probability is available; GEX remains research-only; no current ticker/trade is emitted.
