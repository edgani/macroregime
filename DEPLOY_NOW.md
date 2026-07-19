# Deploy War Room OS v2.7 — Deterministic Hosted Startup

This release replaces the v2.6 startup model. The dashboard is no longer allowed to render a
permanent bootstrap `R1` while hoping a detached process eventually fills it.

## Full replacement required

1. Delete the old deployed repository contents. Do not copy only `app.py` over v2.6.
2. Upload the **contents** of this package to the repository root.
3. Confirm these paths exist at root:
   - `app.py`
   - `warroom_data_worker.py`
   - `runtime_store.py`
   - `dashboard.html`
   - `data/loader.py`
   - `.streamlit/config.toml`
4. Keep the application entrypoint as `app.py`.
5. Clear the hosting build cache and redeploy.

## What must happen now

Before the iframe is mounted, `app.py` runs one small, bounded market bootstrap. First paint is
therefore one of only two truthful states:

- **R2 with market observations**: US, IHSG, crypto, commodities, and FX have at least the symbols
  the public providers returned; or
- **R2 NO_DATA with an explicit error**: public egress/providers failed.

The browser must never remain indefinitely at `INITIALIZING · R1`.

After first paint, the embedded collector fills separate background planes:

1. macro, liquidity, regime, and cross-asset context;
2. options/derivatives and institutional events;
3. slower fundamentals, SEC, CFTC, EIA, on-chain, and licensed feeds;
4. expanded universes.

## Hosted settings

Do not set `WARROOM_WORKER_MODE=process` on a managed Streamlit host. The package defaults to:

```text
WARROOM_WORKER_MODE=embedded
WARROOM_PRICE_BACKEND=http
WARROOM_ENABLE_YFINANCE_FALLBACK=0
```

The public loader has bounded fallbacks: Yahoo chart hosts, Stooq, Binance, and OKX. Missing data
remains missing; no synthetic series is substituted.

## Credentials

Add secrets through the hosting platform, not by committing `.env`:

- `FRED_API_KEY` is strongly recommended for reliable macro data.
- `WARROOM_SEC_USER_AGENT` must contain a real application/contact identity.
- Unusual Whales, Massive, ORTEX/Intrinio, Nansen, Arkham, Databento, CoinGlass, EIA, and licensed
  IDX feeds require their own key or entitlement.

Those optional sources may show `NOT_ENTITLED` or `ACTION_REQUIRED`; they must not prevent market
prices from loading.

## Diagnostics

Run locally or inspect from the deployment file console:

```text
python diagnose_no_data.py
python validate_v27_startup.py
python validate_v27_full.py
```

Key files:

- `runtime/worker_status.json`
- `runtime/worker.log`
- `runtime/worker_boot.log`
- `runtime/NO_DATA_DIAGNOSTIC.json`

A valid failure is explicit `NO_DATA/DEGRADED` with an error. Permanent `INITIALIZING` is not valid.
