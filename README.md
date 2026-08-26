# Opportunity Intelligence Engine v2.3 — Validated Release

Beginner-first Streamlit decision system for US stocks, IHSG, FX, commodities and crypto.

## Daily workflow

`MACRO GATE → OPPORTUNITY DISCOVERY → ENTRY → EXPRESSION → SCENARIO/FALSIFIER`

The scanner runs automatically on first load and after the configured cache interval. `Refresh now` is optional.

### Entry is separate from detection

Lifecycle:

`DISCOVER → STARTER → CORE → ADD/HOLD → NO CHASE → TRIM/EXIT`

Early detection is never treated as a full-size entry. The entry layer uses causal/fundamental evidence, valuation/asymmetry, data quality, fair-value revision versus price revision, and the macro/crash gate. Options and leverage are selected only after entry is earned.

### Expression policy

- US stocks: cash ownership, leveraged long/short when earned, listed call/put candidates.
- IHSG: cash stock only. No short/leverage/options.
- Crypto: spot; leverage only when the crypto causal/economics model is ready; BTC/ETH listed crypto-option adapter.
- FX: visible in radar/spot context; leverage remains fail-closed until relative macro, REER/BoP, positioning and intervention/policy evidence are wired for that observation.
- Commodities: visible in radar/spot context; leverage remains fail-closed until physical balance, inventory, curve and spare-capacity evidence are wired.

## Macro Control Room

The macro page is intentionally compact:

1. Action now
2. Economy
3. Crash setup
4. Credit
5. Event override
6. Top three things that matter
7. NOW / +1Q / +2Q / +4Q projection grid
8. Top supported scenarios and explicit invalidation conditions

If fewer than 55% of critical macro families are available, the engine switches to `HOLD / MACRO GATED`; leverage upgrades are disabled instead of filling missing data with neutral assumptions.

## Point-in-time safeguards

- SEC CompanyFacts PIT parser filters facts by filing availability date.
- IDX company/financial-report discovery adapters are included.
- ALFRED/FRED vintage CSV adapter is included.
- Historical replay fixtures include known after-close publication timing and earliest regular-session execution dates.
- Same-sector valuation fails closed when peer evidence is insufficient.
- Tie-neutral percentile ranking maps identical peers to the 50th percentile instead of falsely ranking all as 100th percentile.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

Windows: `run_windows.bat`

Linux: `bash run_linux.sh`

## Validation

Run from the extracted package:

```bash
python tests/run_all.py
```

The release was frozen only after a clean-extract rerun of the bundled suite. See `VALIDATION_RESULTS.md`, `TEST_MATRIX.md`, `FINAL_AUDIT.md`, and `KNOWN_LIMITATIONS.md`.

## Important scope statement

This release is software/logic validated, not a claim of production-proven alpha. Real survivorship-safe full-universe PIT/OOS performance, complete historical options surfaces, global macro vintages, and several asset-class-specific historical feeds require data that is not bundled. Those components remain visibly gated rather than generating fake conviction.
