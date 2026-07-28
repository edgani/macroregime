# War Room OS v3 — Streamlit Trading Workstation Status

## Operational status

- Streamlit Market Desk: READY
- BTCUSDT / ETHUSDT data controls: READY
- 15m / 1h / 4h / 1d monitoring: READY
- MQA descriptive range: READY
- Momentum axes: READY
- MTF context: READY
- Manual execution planner: READY
- Risk-based sizing with costs and leverage cap: READY
- Append-only paper trade journal: READY
- Prospective evidence collection: READY
- Autonomous signal generation: BLOCKED
- Broker/exchange order placement: NOT INCLUDED

## Trading contract

The operator selects direction and owns the decision. The system provides descriptive state, arithmetic level templates, risk sizing, paper journaling, and evidence monitoring. No probability or predictive edge is claimed until version-bound prospective gates pass.

## Streamlit pages

1. Market Desk
2. Execution Planner
3. Paper Journal
4. Operations & Evidence
5. System Contract

## Local launch

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install .
warroom bootstrap-all
warroom streamlit
```

Open `http://127.0.0.1:8501`.

## Oracle VPS

```bash
sudo bash ops/install_oracle_ubuntu.sh
ssh -L 8501:127.0.0.1:8501 ubuntu@SERVER_IP
```

Then open `http://127.0.0.1:8501` locally.
