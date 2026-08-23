# Opportunity Intelligence Engine v1

A causal-first multi-market opportunity scanner for:

- US equities
- IHSG equities (BUY/BUILD/HOLD/TRIM/SELL/AVOID only)
- FX
- commodities
- crypto

It is designed around **high recall in discovery** and **high precision before action**. It does **not** use classic technical indicators.

## What is new

### 1. Full causal-chain expansion
The engine does not stop at the obvious asset. It maps:

root shock/change → direct beneficiaries → second/third/fourth-order beneficiaries → new bottlenecks → losers → normalization/capacity response.

The built-in graph includes AI/data-center compute, memory, networking, photonics/CPO, grid interconnection, transformers, switchgear, cables/copper, gas generation/turbines, nuclear/uranium, backup generation, cooling/liquid cooling, water, construction/EPC, powered land, war/oil/shipping/tankers/defense, CPO, crypto value capture, privacy/scarcity, FX intervention hazard, and ADES-style consumer/operating-leverage chains.

### 2. Automatic scenario discovery
The scanner runs broad news/theme queries rather than only named-ticker queries. It can:

- map a recurring theme to an existing causal root;
- generate a **NOVEL CLUSTER** when a recurring theme is not in the current library;
- persist first-seen / last-seen scenario memory;
- keep a novel scenario quarantined until a causal mechanism, confirmation and falsifier are established.

No numerical event probability is invented.

### 3. Projection + reverse valuation
For live equity rows with sufficient public data the deep dive shows:

- Bear / Base / Bull earnings-power projection;
- peer-multiple anchored research fair-value range;
- current price-implied EPS at the scanned peer median multiple;
- expectation gap;
- stage and research action state.

These are intentionally labelled research ranges until the PIT/OOS valuation model is validated.

### 4. Crypto economics
The deep dive can query CoinGecko supply/FDV context and DefiLlama revenue data. Revenue is **not** a hard buy rule. The research design requires:

usage → fees/revenue → tokenholder capture → dilution/unlocks → net accrual → price-in.

This lets VVV-style value capture and ZEC-style usage/scarcity be discovered by different causal families.

### 5. Historical acceptance tests
Frozen cases:

- SNDK — structural memory bottleneck
- PLTR — product/adoption + sales-cycle inflection
- VVV — revenue/value-capture inflection
- ZEC — usage/scarcity inflection
- USDJPY — policy intervention hazard
- ADES — fundamental/operating-leverage inflection

These cases are **tests only** and may never be used to tune thresholds. Negative controls and holdouts are mandatory before any production claim.

## Run

### Windows
Double click `run_windows.bat`.

Or:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

### Linux / WSL

```bash
./run_linux.sh
```

## Pages

The ZIP also contains `pages/2_Macro_Control_Room.py`, the latest Macro Control Room build, so Streamlit exposes it as a second page from the sidebar.

## Important limitations

This v1 is an inspectable working research product, not a claim that the full multi-market scanner is statistically proven. Production promotion still requires point-in-time data, negative controls, holdout winners, false-alarm accounting, lead-time analysis and purged/embargoed OOS validation.
