# War Room OS — Capital Intelligence Map

This package combines the existing GCFIS/War Room engines with a redesigned, data-driven interface modeled as a capital-intelligence map. The UI follows one decision path:

`World → Regime → Market → Theme/Bottleneck → Ticker/Token → Institutional Positioning → Execution → Validation`

## Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Read `START_HERE.md`, copy the relevant values from `.env.example`, and use `DATA_CONNECTORS.md` for provider setup and data semantics.

## Production rules

- Production mode never fabricates missing prices or events.
- Synthetic series exist only behind the explicit `python run.py --synthetic` test command.
- Missing feeds render `NO_DATA`, `NOT_CONFIGURED`, `STALE`, or `ERROR`.
- Options-chain OI is labeled as an OI-implied gamma proxy, not live flow or observed dealer inventory.
- FINRA short volume is descriptive aggregate data, not dark-pool prints, short interest, or institutional intent.
- Options alerts, TRF prints, SEC filings and whale transfers are evidence; none is automatically a directional position.
- Structural maps and live observations are visually and semantically separated.
- Default `OBSERVED` mode cannot promote structural Alpha hypotheses into Mission Control actions.
- IHSG remains long-only.

## Key files

```text
app.py                    Streamlit production app with split refresh cadences
dashboard.html            Capital Intelligence Map SPA
institutional_data.py     UW, Massive, SEC, Nansen and Arkham adapters
data_layer.py             Price/macro adapter; synthetic disabled by default
run.py                    Core engine orchestration and normalized desk object
validate_redesign.py      Fast UI/data-semantics integrity audit
DATA_CONNECTORS.md        Keys, cadence, semantics and failure behavior
REDESIGN_V1.md            Workspace and visual-system map
.env.example              Environment variable template
```

The original research, validation and engine directories remain in this package. Their historical reports should not be read as proof that every newly connected institutional dataset has forward edge. Options flow, TRF prints, SEC events and on-chain entity signals still require their own frozen event studies, walk-forward tests, costs, regime attribution and multiple-testing controls before any derived score is promoted to production.

## Run modes

```bash
streamlit run app.py
python run.py --institutional
python run.py --markets us,crypto --institutional
python run.py --synthetic          # explicit pipeline test only
python validate_redesign.py
python validate_all.py             # legacy/full validation stack
```

`dashboard.html` is a template and needs injected `window.DASHBOARD_DATA`. The included preview outside this folder is a clearly labeled UI fixture, not a production signal output.

## Current live-data boundary

The app uses near-real-time REST polling for configured institutional feeds and a slower cache for market/macro engines. It does not claim exchange-colocated tick latency. Provider credentials, entitlements and reporting lags still apply. A future WebSocket sidecar can replace the polling layer without changing the normalized event contract or UI.
