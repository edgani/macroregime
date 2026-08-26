# Opportunity Intelligence Engine v2.4 — Visual Decision System

This release fixes the two biggest daily-use problems in v2.3:

1. **FX / commodities / crypto were easy to mistake as “missing”** because fail-closed leverage/options tables only returned qualified trades. v2.4 keeps those markets visible and labels non-qualified rows `WAIT / GATED` instead of deleting them from the surface.
2. **The page was too text-heavy.** v2.4 makes the daily screen visual-first and collapses deep research prose.

## Daily visual hierarchy

- 5 compact top metrics
- Opportunity map: evidence × unpriced asymmetry
- Expression coverage heatmap: US / IHSG / Crypto / FX / Commodity × cash / spot / leverage / options
- Expression-specific evidence/asymmetry chart
- Compact action table (`● ACTION` vs `○ WAIT`)
- Selected-opportunity decision stack
- Deep thesis / valuation / causal chain / sources hidden under one expander
- Macro NOW→+4Q heatmap + top pressure bars + max 3 paths

## Expression contract

- **US:** cash stock, leverage when earned, listed calls/puts when earned.
- **IHSG:** cash-only by design.
- **Crypto:** spot/value-capture research; leverage remains gated until the crypto-specific causal/leverage data clears. BTC/ETH Deribit rows are visible in Options even when the thesis is not yet qualified.
- **FX:** leverage surface is visible. A row remains WAIT until the dedicated relative-macro / REER / BoP / positioning / policy model clears.
- **Commodity:** leverage surface is visible. A row remains WAIT until physical balance / inventory / curve / spare-capacity evidence clears.

The system does **not** turn missing data into a price-momentum signal. Visibility is not permission to trade.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Windows: `run_windows.bat`  
Linux: `./run_linux.sh`

## Validation

Run:

```bash
python tests/run_all.py
```

v2.4 adds `test_visual_contract.py`, which checks that the visual functions exist and that FX/commodity/crypto no longer disappear from the leverage/options presentation contract.

See:
- `VISUAL_CHANGELOG.md`
- `TEST_MATRIX.md`
- `VALIDATION_RESULTS.md`
- `KNOWN_LIMITATIONS.md`
- `DEPLOY_FROM_ZERO.md`
