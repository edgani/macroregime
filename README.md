# Opportunity Intelligence Engine v2.5 — Simple Decision Board

This release keeps the v2.4 research and capital-safety logic but redesigns the daily Opportunities page for immediate comprehension.

## Daily hierarchy

1. **Today's posture** — one macro state plus one plain-language implication.
2. **At a glance** — ACT NOW / WATCH / AVOID-DOWNSIDE / NOT READY counts with ticker chips.
3. **Top opportunities now** — up to four cards showing the action, why it matters, confidence, evidence balance, and available expression.
4. **How it can be traded** — stock / leverage / options / spot readiness counts.
5. **Expression desk** — a simple ranked list. Advanced tables, model gates, and the evidence chart are collapsed by default.
6. **Selected opportunity** — entry logic and deeper research only after the user opens a ticker.

## Expression contract

- **US:** cash stock, leverage when earned, listed calls/puts when earned.
- **IHSG:** cash-only by design.
- **Crypto:** spot/value-capture research; leverage remains gated until crypto-specific causal/leverage data clears. BTC/ETH Deribit rows stay visible in Options.
- **FX:** leverage rows stay visible but remain WAIT until relative-macro / REER / BoP / positioning / policy data clears.
- **Commodity:** leverage rows stay visible but remain WAIT until physical balance / inventory / curve / spare-capacity evidence clears.

The system does **not** turn missing data into a momentum signal. Visibility is not permission to trade.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Windows: `run_windows.bat`  
Linux: `./run_linux.sh`

## Validation

```bash
python tests/run_all.py
```

See `VISUAL_CHANGELOG.md`, `TEST_MATRIX.md`, `VALIDATION_RESULTS.md`, `KNOWN_LIMITATIONS.md`, and `DEPLOY_FROM_ZERO.md`.
