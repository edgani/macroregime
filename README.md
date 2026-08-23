
# Macro Decision OS v4

Causal macro/fundamental decision framework for US equities, IHSG, commodities, FX and crypto.

## Deploy
Upload **the entire folder contents** to the GitHub repo used by Streamlit, with `app.py` at repo root.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## What changed vs v3
- larger strict public macro/credit/funding panel (SOFR/IORB, IG/CCC credit, bank credit, ANFCI)
- official US Treasury/NY Fed plumbing adapter; components only, no net-liquidity trade rule
- DeFiLlama crypto-native live adapter (stablecoins/TVL/DEX) with no regime hardcode
- instrument-specific current options context (IV / expected range / skew / OI concentration); no deterministic GEX claim
- SEC filed-date Company Facts added to bottleneck monetization verification
- temporal walk-forward calibration harness for macro analog distributions; explicitly revision-unsafe until PIT vintages exist
- 36-scenario candidate registry separated from live Base/Competing/Tail/Null evidence
- governance overrides supersede contradictory legacy validation files from the older War Room
- data lineage includes staleness and revision-vintage flags

## Non-negotiable governance
- no RSI/MACD/EMA/Bollinger/candlestick/Fibonacci/chart-pattern alpha
- price is not a macro regime classifier
- ATH/price-state studies are research-only outcome-state experiments
- no synthetic fallback
- no hard-coded regime→asset mappings
- no arbitrary scenario probabilities or confidence scores
- bottleneck evidence is not a LONG signal
- remaining runway is a distribution and stays DATA_GATED until calibrated inputs exist
- `NO TRADE` is first-class

## Still data-gated
ALFRED/PIT macro vintages, pre-release consensus history, PIT analyst revisions, historical constituents/delistings, historical options/dealer inventory, cross-currency basis, broad physical commodity history, historical backlog/RPO/order database, crypto unlock/emission/exchange balances, IDX Type-F history.
