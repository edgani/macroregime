# Deploy War Room OS v2.9 — Decision-First

## Full replacement is required

Do not copy a few v2.9 files over an older deployment. Old runtime snapshots, static HTML and
worker locks can keep the previous interface alive.

1. Delete the old deployed repository contents.
2. Upload the **contents** of this package to the repository root.
3. Confirm these paths exist at root:
   - `app.py`
   - `warroom_data_worker.py`
   - `runtime_store.py`
   - `run.py`
   - `price_setups.py`
   - `dashboard.html`
   - `data/loader.py`
   - `.streamlit/config.toml`
4. Keep the application entrypoint as `app.py`.
5. Clear the hosting build cache and redeploy.

The header must read:

```text
v2.9 DECISION-FIRST
```

## First-paint behavior

Before the dashboard is mounted, `app.py` performs a small bounded market bootstrap. First paint is
therefore either:

- a committed snapshot with observed market histories; or
- explicit `NO_DATA/DEGRADED` with the actual startup error.

It must not remain indefinitely at bootstrap `R1`.

## Action vocabulary

- `BUILD LONG`: bullish setup is aligned with the market posture. Use the displayed trigger/stop;
  it does not mean market-buy immediately.
- `WATCH LONG`: bullish candidate, but alignment or trigger is missing. No position yet.
- `BUILD SHORT`: bearish setup is aligned in a two-sided market. Use the displayed trigger/stop.
- `WATCH SHORT`: bearish candidate, but alignment or trigger is missing. No position yet.
- `REDUCE / AVOID`: defensive response, especially for long-only IHSG. It never opens an IHSG short.
- `NO TRADE`: data can be live while no current setup is permitted.

## Alpha Center semantics

Alpha Center is no longer populated by a tactical price fallback. It loads the structural
asymmetry engine on first paint and separates:

1. extreme-upside/headroom discovery;
2. independent proof of value capture;
3. tactical timing/execution;
4. validation and capital permission.

`50–500x` is also shown as approximately `+4,900%–49,900%` scenario headroom. The higher the
headroom class, the lower the base rate. It is not a price target, expected return or probability.

## Data credentials

Add secrets through the hosting platform, not by committing `.env`:

- `FRED_API_KEY` for reliable macro history;
- `WARROOM_SEC_USER_AGENT` with a real application/contact identity;
- provider credentials/entitlements for Unusual Whales, Massive, ORTEX/Intrinio, Nansen, Arkham,
  Databento, CoinGlass, EIA and licensed IDX feeds.

A failed or unentitled endpoint is retained in the Evidence Ledger. The canvas displays a domain
summary such as `PARTIAL`, `NOT_ENTITLED` or `NO_SIGNAL`; one provider error must not blank the rest
of the workspace.

## Diagnostics

```text
python diagnose_no_data.py
python validate_v29_decision_first.py
```

Inspect:

- `runtime/worker_status.json`
- `runtime/worker.log`
- `runtime/worker_boot.log`
- `runtime/NO_DATA_DIAGNOSTIC.json`
