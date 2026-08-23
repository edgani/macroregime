# Macro Decision Engine — fixed deploy build

## Why the previous build failed
`app.py` imported local modules such as:
- `config.metric_registry_v2`
- `data_layer_v2`
- `engines.scenario_matrix_v2`
- `engines.projection_engine_v2`
- `engines.bottleneck_engine_v2`
- `data.eia_physical`

Those files were missing from the deploy package.

## Streamlit Cloud
Upload the **entire contents of this folder** to the repo root, not only `app.py`.

Required repo structure:
```
app.py
requirements.txt
data_layer_v2.py
config/
engines/
data/
research/
.streamlit/
```

Set Main file path to:
`app.py`

Optional secrets/environment:
- `SEC_USER_AGENT`
- `EIA_API_KEY` (physical-energy layer remains fail-closed until exact EIA routes are mapped)

Data policy:
- no synthetic price fallback
- missing data => NO DATA / DATA_GATED
- discovery priors cannot score a ticker
- bottleneck verification != automatic LONG
