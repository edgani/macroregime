# Data feeds wired from macroregime (the 1-by-1 audit)

Every external-data `.py` in macroregime, and what's now wired:

## Wired this build
| feed | source | market/use | key |
|---|---|---|---|
| **typef_idx** | idx.co.id | **IHSG/IDX prices + foreign buy/sell (bandarmologi)** — now PRIMARY for idx | none |
| **treasury_liquidity** | fiscaldata.treasury.gov + NY Fed | **TGA/RRP/SOFR → liquidity read** (fixes the "—") | none |
| data.loader | yfinance | US/crypto/commodity/fx prices | none |
| data.fred_loader | FRED (api + fredgraph) | WALCL/DGS10/T5YIE/HY-OAS/M2/RRP → quad+systemic | FRED_API_KEY |
| macro-proxy ETFs | yfinance | SPY/GLD/USO/UUP/XLI/XLY/TLT → GIP + multi-tf regime + cross-asset | none |

## Available in bundle, need keys you have (onchain expansion — not blocking)
cftc_cot_scraper (COT, free) · defillama_scraper (api.llama.fi, free) · onchain_engine ·
live_data_engine (yfinance options + DefiLlama + FINRA + COT). Your keys now read from env/secrets:
`FRED_API_KEY, TAOSTATS_KEY, ETHERSCAN_KEY, DUNE_SIM_KEY, GEMINI_API_KEY, GLASSNODE_KEY, CRYPTOQUANT_KEY`
— set them in Streamlit secrets to light up the onchain/options panels.

## Multi-timeframe regime (now renders in Mission Control)
`regime_multitf.py` + v40 `gip_engine.py`: Structural + Monthly (GIP) + Weekly + Daily (price-proxy) +
Posture (aggressive/defensive). Needs SPY/GLD/USO/UUP — now fetched as macro proxies, so it populates live.

## What still shows honest gaps live (not mock)
- Markets that fail to fetch → "NOT LOADED" (never stale prices).
- Setups that don't clear the conviction gate → "no name cleared the gate" (not fabricated).
- Onchain/options panels → light up when you add the keys above.

Set keys, `streamlit run app.py`, Live. IHSG pulls from idx.co.id, liquidity from Treasury/NY Fed,
regime shows all four timeframes.
