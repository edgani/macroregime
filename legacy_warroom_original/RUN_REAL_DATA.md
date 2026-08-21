# Real data — corrected (you were right: v40 fetches live fine)

## What was actually wrong

My earlier guess ("Yahoo rate-limits cloud IPs") was wrong for your setup — **v40 fetches FRED + Yahoo
live without issue.** The real bug: my `data_layer` was calling `warroom.data.load` (a different loader)
instead of **v40's proven `data.loader.load_prices` + `data.fred_loader.load_fred_series`** — the exact
functions your working v40 uses. Fixed: `data_layer.load_all` now uses v40's loaders as the primary path
(byte-identical to your v40's), so it fetches live the same way v40 does.

## Chain now (Live mode)

```
app.py (Live) → data_layer.load_all(allow_live=True)
   → data.loader.load_prices(207-name universe)      # yfinance per-ticker (v40's working call)
   → data.loader.load_ohlcv(...)                     # for the price-signal path
   → data.fred_loader.load_fred_series()             # WALCL/DGS10/T5YIE/HY-OAS/M2/RRP … live
→ build_desk → macro_inputs.assemble → run_gcfis(liquidity/fragility/shock/forward_macro inputs)
→ inject into dashboard.html → header badge = LIVE, real tickers, Mission Control populated
```

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py      # pick "Live (your feeds)"
```
FRED liquidity uses fredgraph (no key); for reliability set `FRED_API_KEY` in Streamlit secrets.
The header flips **SYNTHETIC → LIVE**, NVDA shows today's price, fear-greed uses real VIX,
liquidity/fragility/shock fill from real FRED.

## In this sandbox it still shows synthetic — that's the sandbox, not the code

My environment blocks all outbound network (Yahoo/FRED → 403), so when *I* run it, v40's loaders return
nothing and it falls back to synthetic. That's why I validate on the bundled REAL historical data instead.
On your machine — where v40 already proves the network works — the same loaders return live data.

## Validation (no feeds needed, run anywhere)

```bash
python validate_all.py        # 7 suites on bundled REAL data → see TEST_REPORT.md
```
