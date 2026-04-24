# MacroRegime Pro v10
## Hedgeye GIP Framework — Full Clean Build

### Setup
```bash
pip install -r requirements.txt
```

### FRED API Key
Add to `.streamlit/secrets.toml`:
```toml
FRED_API_KEY = "your_key_here"
```

### Run
```bash
streamlit run app.py
```

### Architecture
- `engines/gip_engine.py` — TRUE Hedgeye GIP model (Growth·Inflation·Policy)
- `engines/hurst_rr_engine.py` — TRADE/TREND/TAIL Risk Ranges (Rescaled Range/Hurst)
- `engines/global_quad_engine.py` — 50+ country quad classification
- `engines/scenario_engine.py` — Adaptive scenario discovery
- `engines/bottleneck_engine.py` — Full bottleneck scanner with TP logic
- `config/settings.py` — ALL parameters (zero hardcoded thresholds in engines)
- `data/loader.py` — FRED + yfinance with smart snapshot caching
- `orchestrator.py` — Full snapshot builder
- `app.py` — Streamlit UI

### Pages
1. Dashboard — Quad trinity + alerts + base scenario
2. Regime (GIP) — 2D quad map + signal breakdown + data quality
3. Risk Ranges — TRADE/TREND/TAIL per asset + Hurst + alerts
4. Global Quad — 50 countries + USD bias + EM assessment
5. Bottleneck Scanner — Citrini + Hedgeye + TP levels per bottleneck type
6. Scenarios — Adaptive regime transition scenarios
7. IHSG — Indonesia-specific context
