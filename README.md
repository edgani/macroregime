# War Room OS v3 — Streamlit Trading Workstation

War Room OS v3 is an installable Streamlit workstation for **live market monitoring, discretionary trade planning, risk sizing, paper-trade journaling, and prospective evidence collection**.

It is designed to stay useful without turning unvalidated research into fake certainty.

## What is ready

- Streamlit Market Desk.
- BTCUSDT and ETHUSDT finalized-bar bootstrap and collection from Binance public market data.
- 15m, 1h, 4h, and 1d views.
- Canonical point-in-time CSV import for SPY, QQQ, futures, FX, commodities, IHSG, and other frozen-matrix assets.
- Candlestick chart with fixed ATR and past-only conformal boundaries.
- MQA volatility/range state.
- Separate Momentum axes rather than one opaque composite score.
- Four-role MTF context: Structural, Trend, Tactical, Execution.
- Manual direction selection and structural execution template.
- Position sizing with account equity, risk percentage, estimated costs, and leverage cap.
- Downloadable operator ticket.
- Append-only paper-trade journal with tamper-evident global and per-trade chains.
- Paper P&L, R multiple, win rate, and equity curve.
- Immutable prospective observations and matured outcomes.
- Evidence evaluation, incidents, runtime journals, Docker, systemd, and Oracle VPS installer.

## What is intentionally not included

- Broker or exchange order placement.
- Autonomous BUY/SELL.
- Uncalibrated probability.
- Automatic promotion to PAPER or LIVE evidence.
- Claims that the structural template has predictive edge.

The operator chooses direction and remains responsible for execution. The app supplies context, arithmetic, risk controls, and records.

# Quick start

## Windows

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install .
python scripts\validate_all.py
warroom bootstrap-all
warroom streamlit
```

Open:

```text
http://127.0.0.1:8501
```

## Linux / macOS

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install .
python scripts/validate_all.py
warroom bootstrap-all
warroom streamlit
```

Open `http://127.0.0.1:8501`.

# Streamlit workflow

## 1. Market Desk

Choose an asset and timeframe. The page shows:

- finalized-bar chart;
- ATR and conformal boundaries;
- range location and volatility state;
- trend context, acceleration, release, persistence, efficiency, noise, and exhaustion;
- MTF alignment and conflict codes;
- watchlist for the selected timeframe.

`BULLISH CONTEXT`, `BEARISH CONTEXT`, and conflict labels are descriptive. They are not calibrated trade probabilities.

## 2. Execution Planner

1. Review MTF context.
2. Select LONG or SHORT yourself.
3. Generate an unvalidated structural template.
4. Edit entry zone, invalidation, and targets.
5. Enter account equity, risk budget, estimated round-trip costs, and leverage ceiling.
6. Calculate the operator plan.
7. Download the JSON ticket or open it as a paper trade.

The quantity is capped by both cash-risk budget and maximum leverage.

## 3. Paper Journal

- Review open, closed, and cancelled paper trades.
- Close using the current market price or a manual price.
- Record the close reason.
- Track realized P&L, R multiple, win rate, and cumulative P&L.
- Validate journal integrity before reading results.

## 4. Operations & Evidence

- Bootstrap or collect selected Binance scopes.
- Bootstrap or collect all approved online scopes.
- Import canonical PIT CSV data.
- Inspect evidence evaluation and immutable journals.
- Review operational incidents.

# Canonical CSV format

Required columns:

```text
asset,timeframe,observed_at,available_at,open,high,low,close,volume,source_record_id
```

Optional:

```text
revision_id
```

Timestamps must be timezone-aware. `available_at` cannot precede `observed_at`.

CLI import:

```bash
warroom import-csv /path/to/file.csv --tier bootstrap
```

Prospective import additionally requires every observation to be strictly after the armed seal start.

# Oracle Ubuntu VPS

```bash
unzip WarRoom_OS_v3_Streamlit_Trading_2026-07-13.zip
cd warroom_os_v3_streamlit
sudo bash ops/install_oracle_ubuntu.sh
```

The service binds to localhost. From your computer:

```bash
ssh -L 8501:127.0.0.1:8501 ubuntu@SERVER_IP
```

Open `http://127.0.0.1:8501`.

Optional operator PIN:

```bash
sudo systemctl edit warroom-streamlit.service
```

Add:

```ini
[Service]
Environment=WARROOM_OPERATOR_PIN=replace-with-a-long-secret
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart warroom-streamlit.service
```

# Daily commands

```bash
warroom status
warroom bootstrap-all
warroom collect-all
warroom evaluate
warroom snapshot BTCUSDT
warroom streamlit
```

# Runtime directories

- `runtime/bootstrap/` — historical context, not prospective evidence.
- `runtime/prospective/` — sealed forward market batches.
- `runtime/observations/` — immutable descriptive tickets.
- `runtime/outcomes/` — realized forward outcomes.
- `runtime/trading/plans/` — immutable manual paper plans.
- `runtime/trading/paper_events.jsonl` — append-only paper lifecycle events.
- `runtime/evaluation/latest.json` — current evidence report.
- `runtime/incidents/` — immutable operational failures.
- `runtime/uploads/` — canonical CSV uploads named by content hash.

# Validation

```bash
python scripts/validate_all.py
```

The release validates code, formula registry, market matrix, applicability, collection plan, provider registry, release manifest, prospective seal, trial ledger, runtime stores, and the paper journal.

# Trust boundary

The original ZIP is retained as migration and audit evidence only. Active production code under `src/warroom_v3` cannot import the rejected legacy `gcfis`, `warroom`, or old entry/risk-range stack.
