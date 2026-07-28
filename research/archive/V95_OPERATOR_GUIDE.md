# V9.5 operator guide — from zero to prospective shadow operation

## 1. Install

On Windows PowerShell, open the extracted folder and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python validate_v95_release.py
```

Expected result: every V9.5 software/adversarial test passes, `operational_permission` is `SHADOW_TRADING_READY`, and `capital_permission` remains `BLOCKED`.

## 2. Configure public sources

Copy `V95_PROVIDER_ONBOARDING.env.example` to `.env`, then fill only credentials you own.

- `WARROOM_SEC_USER_AGENT` must identify the application and include a contact email.
- `FRED_API_KEY` enables FRED/ALFRED observations.
- `CFTC_APP_TOKEN` is optional but useful for larger CFTC requests.

Run a bounded first collection:

```powershell
python autonomous_public_data_plane_v95.py --output runtime/v95_public_acquisition --max-cftc-rows 5000
```

A successful download proves source identity and payload integrity only. It does not grant trading permission.

## 3. Run the dashboard

```powershell
streamlit run app.py
```

Read the two permissions separately:

- **Shadow operation**: the pipeline may record new prospective decisions and simulated execution.
- **Live capital**: remains blocked until an exact V9.5 proof run passes.

## 4. Record a prospective forecast

Copy and edit `V95_SHADOW_FORECAST_TEMPLATE.json`. Generate fresh timestamps and real hashes from the frozen model, code, data snapshot, trial ledger and projection file. Then run:

```powershell
python shadow_execution_ledger_v95.py forecast --ledger runtime/v95_shadow/shadow_ledger.jsonl --input V95_SHADOW_FORECAST_TEMPLATE.json
```

The forecast must be written within five minutes of `generated_at`. Historical/backfilled forecasts are rejected.

## 5. Record the simulated order and fill

```powershell
python shadow_execution_ledger_v95.py order --ledger runtime/v95_shadow/shadow_ledger.jsonl --input V95_SHADOW_ORDER_TEMPLATE.json
python shadow_execution_ledger_v95.py fill --ledger runtime/v95_shadow/shadow_ledger.jsonl --input V95_SHADOW_FILL_TEMPLATE.json
python shadow_execution_ledger_v95.py verify --ledger runtime/v95_shadow/shadow_ledger.jsonl
```

Shadow fills are permanently marked paper/synthetic/non-live and therefore cannot enter the live performance gate.

## 6. Mature outcomes

After the frozen horizon has ended, append a genuine outcome with an immutable source hash. Outcomes entered before maturity are rejected.

## 7. Normalize actual account evidence

For an export that already contains closed round trips, copy `V95_CLOSED_TRADE_MAPPING_TEMPLATE.json`, map the real column names without inventing values, set a private `WARROOM_ID_HASH_SALT`, and run:

```powershell
$env:WARROOM_ID_HASH_SALT="your-private-random-salt"
python live_trade_normalizer_v95.py --input broker_closed_trades.csv --mapping my_trade_mapping.json --output runtime/market_evidence/us/live_trades.csv
python equity_ledger_normalizer_v95.py --input broker_equity.csv --mapping my_equity_mapping.json --output runtime/market_evidence/us/equity.csv
```

The normalizers pseudonymize account and order identifiers. They do not infer missing costs, pair raw fills into trades, or convert paper records into live evidence.

## 8. Live-proof route

Each market needs a separate predictor manifest, forecast seal, outcome manifest, projection file, actual live trade ledger, account equity ledger and trusted signed proof receipt. Run:

```powershell
python blind_proof_runner_v95.py `
  --predictor-manifest runtime/market_evidence/us/predictor_manifest.json `
  --outcome-manifest runtime/market_evidence/us/outcome_manifest.json `
  --projections runtime/market_evidence/us/projections.csv `
  --trades runtime/market_evidence/us/live_trades.csv `
  --equity runtime/market_evidence/us/equity.csv `
  --signed-receipt proof/receipts/us_v95.json `
  --forecast-seal runtime/market_evidence/us/forecast_seal.json `
  --out runtime/v95_proof_runs/us.json
```

The same lane must pass independently for `idx`, `commodity`, `fx` and `crypto`. Installing a proof-run path and exact hash in `component_registry_v95.json` still cannot activate it unless the proof run says `LIMITED_PRODUCTION_ELIGIBLE`, has no errors and contains a valid trusted signature.

## 9. Never do this

Do not rename paper fills as live fills, backfill forecasts, replace delisted securities with survivors, use revised data as though it were known earlier, type desirable metrics into receipts, or use a current symbol list as historical universe proof. V9.5 rejects many of these mechanically; anything not mechanically detectable remains prohibited evidence handling.
