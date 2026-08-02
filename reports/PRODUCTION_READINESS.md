# Production Readiness

Status: **NOT APPROVED FOR LIVE CAPITAL**

This report separates software readiness from evidence readiness. A runnable interface is not proof of investment value.

| Gate | Status | Evidence |
|---|---|---|
| Five-tab architecture | PASS | Streamlit AppTest and `MAIN_TABS` contract |
| Typed, reproducible fixture | PASS | Pydantic validation of `demo_dashboard.json` |
| Visible synthetic labelling | PASS | E2E banner assertion |
| Execution lock | PASS | State and E2E assertions |
| Registry-driven global baseline | PASS | Integration tests for universe and dataset registries |
| PIT availability behavior | PASS | Leakage tests |
| Feed-health fail-closed behavior | PASS | Unit tests |
| Public benchmark market adapters | PASS | Six market groups, provider isolation, freshness labels, and stale-cache regression tests |
| Narrative firewall | PASS | Unit tests |
| Competing hypotheses including null | PASS | Unit tests |
| Evidence-family de-duplication | PASS | Unit tests |
| Conservative EV including all costs | PASS | Unit tests |
| No technical indicators | PASS | Regression source scan |
| Global PIT macro evidence adapters | FAIL | Material data debt beyond public benchmark prices |
| Full license/entitlement enforcement | FAIL | Registry metadata only |
| Legacy formula replication | PARTIAL | Baseline unit tests; inherited result corpus not fully replicated |
| Historical multi-country frozen replay | FAIL | Holdout corpus absent |
| Prospective calibration | FAIL | No matured sealed forecast sample |
| Qualified opportunity | PASS-EMPTY | No opportunity is promoted |
| Portfolio decision readiness | FAIL | No private holdings, tax, access, or liquidity context |
| Live-capital permission | LOCKED | Correct by design |

## Reproduction

```bash
uv sync --extra dev
uv run ruff check src tests app.py
uv run mypy
uv run pytest -q
uv run streamlit run app.py
```

A production claim requires all failing evidence gates to pass without weakening the validation policy.
