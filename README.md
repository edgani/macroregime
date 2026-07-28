# War Room OS V10.1 — Carry-Aware Operational Research & Shadow Trading

V10.1 extends the unified ticker decision packet with a causal carry-trade engine:

`rate/funding differential → funding currency → target currency/asset → beneficiaries → crowding → unwind risk → current direction → invalidation`.

It supports EURUSD, GBPUSD, AUDUSD, USDCAD, USDJPY, USDCHF, USDIDR, AUDJPY, CADJPY, GBPJPY and EURJPY references. Current carry direction is a research output. Systematic capital remains exact-proof gated.

## Run

- Production dashboard: `streamlit run app.py`
- Background data worker: `python warroom_data_worker_v101.py [--once|--full]`
- V3 kernel workstation: `streamlit run streamlit_app.py` (offline, fail-closed)
- V3 CLI: `warroom` (package under `src/`, see `pyproject.toml`)
- Tests: `pytest tests/ -q` (124 kernel + 10 paper-trading tests)
- Paper trading: see `docs/audit/PAPER_TRADING.md`

## Audit documentation

Start with `docs/audit/WORK_STATUS.md`. Evidence labels and claim adjudication:
`docs/audit/CLAIM_EVIDENCE_AUDIT.md`. Operator guide: `V101_OPERATOR_GUIDE.md`.
Historical per-version docs live under `research/archive/`.
