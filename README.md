# Opportunity Intelligence Engine v2.6 — IHSG Transaction Intelligence

This release keeps the v2.4 research and capital-safety logic but redesigns the daily Opportunities page for immediate comprehension.

## Daily hierarchy

1. **Today's posture** — one macro state plus one plain-language implication.
2. **At a glance** — ACT NOW / WATCH / AVOID-DOWNSIDE / NOT READY counts with ticker chips.
3. **Top opportunities now** — up to four cards showing the action, why it matters, confidence, evidence balance, and available expression.
4. **How it can be traded** — stock / leverage / options / spot readiness counts.
5. **Expression desk** — a simple ranked list. Advanced tables, model gates, and the evidence chart are collapsed by default.
6. **Selected opportunity** — entry logic and deeper research only after the user opens a ticker.

## Expression contract

- **US:** cash stock, leverage when earned, listed calls/puts when earned.
- **IHSG:** cash-only by design.
- **Crypto:** spot/value-capture research; leverage remains gated until crypto-specific causal/leverage data clears. BTC/ETH Deribit rows stay visible in Options.
- **FX:** leverage rows stay visible but remain WAIT until relative-macro / REER / BoP / positioning / policy data clears.
- **Commodity:** leverage rows stay visible but remain WAIT until physical balance / inventory / curve / spare-capacity evidence clears.

The system does **not** turn missing data into a momentum signal. Visibility is not permission to trade.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Windows: `run_windows.bat`  
Linux: `./run_linux.sh`

## Validation

```bash
python tests/run_all.py
```

See `VISUAL_CHANGELOG.md`, `TEST_MATRIX.md`, `VALIDATION_RESULTS.md`, `KNOWN_LIMITATIONS.md`, and `DEPLOY_FROM_ZERO.md`.


## IHSG Transaction Intelligence (v2.6)

IHSG now has an optional, fail-closed transaction evidence layer. It never turns a missing API response into a signal and it contributes at most **one** independent evidence-family vote to the stock decision engine.

### Data stack

- **Index Alpha**: EOD broker attribution, buy/sell value/volume/frequency/average price, Regular (RG) vs Negotiated (NG) market, and foreign flow. The engine requests single trading days for the persistence calculation because Index Alpha multi-day ranges are aggregated.
- **Invezgo**: live intraday summary and order-book depth. HAKA/HAKI-style aggressive-flow metrics are used only when the returned payload actually contains them; otherwise absorption remains gated.
- **IDX / KSEI**: primary-source ownership/corporate-action confirmation remains the slow confirmation layer.

### Important accounting guardrail

The sum of broker net buys across all brokers is approximately zero by market accounting. v2.6 therefore **does not** create a fake total-market "broker net buy." It measures:

- broker-level multi-day directional persistence;
- concentration asymmetry between accumulating and distributing brokers;
- execution-cost proxy for the top accumulating brokers;
- foreign group net flow;
- negotiated-market contamination / transfer risk;
- visible order-book balance with deliberately low weight;
- aggressive-flow vs price disagreement only when HAKA/HAKI-like fields exist.

The displayed `transaction_score` is a **research-state score, not a calibrated probability**.

### Configure API keys

Local:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Then edit the two values:

```toml
INDEX_ALPHA_API_KEY = "..."
INVEZGO_API_KEY = "..."
```

For Streamlit Cloud, add the same names in the app's Secrets settings. Environment variables with the same names also work.

Optional broker-history setting:

```bash
OIE_IHSG_BROKER_LOOKBACK=5
```

The broad scan intentionally does **not** poll queue-tracking for every stock. Queue data is exposed in `ihsg_transaction.py` for a future focused ticker microscope; this prevents quota waste and avoids claiming a replenishment signal before the queue schema is explicitly validated.
