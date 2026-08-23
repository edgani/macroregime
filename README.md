# Macro Decision OS v3

This build implements the causal research/decision specification.

## Deployment
Upload the entire folder contents to the repo root and set Streamlit main file to `app.py`.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Key design constraints
- no RSI/MACD/EMA/Bollinger/candlestick/Fibonacci/chart-pattern alpha
- price is not a macro regime classifier; ATH lives only in Experiment Registry research
- no synthetic fallback
- no hard-coded regime→asset trade map
- no arbitrary confidence/probability scores
- scenario probability remains DATA_GATED unless calibrated evidence exists
- bottleneck evidence != LONG; pricing/catalyst/runway/risk are separate
- NO TRADE is a first-class output
- every failed experiment is retained in `research/failure_library.csv`

## Important data limitation
Public latest/revised macro history is not point-in-time vintage-safe. Final proof still requires ALFRED/equivalent, PIT analyst revisions, historical universes/delistings, and other asset-specific PIT datasets listed in Data Lineage.
