# EROS v3.0

EROS is a global economic reasoning and capital-allocation decision-support system. It is not a charting terminal, indicator collection, or autonomous broker.

Current phase: **Phase 2 — Prove Everything**. The application deliberately fails closed, preserves `UNKNOWN`, and keeps execution locked until point-in-time, out-of-sample, replication, prospective, and human-approval gates pass.

## Product surface

The Streamlit application has exactly five main tabs:

1. **Command Center** — what changed, what matters, top theses, unknowns, and action gate.
2. **Global Explorer** — registry-driven countries, asset classes, mechanisms, and dossiers.
3. **Opportunity Engine** — conservative net-EV packets and rejected candidates.
4. **Portfolio** — hidden exposure, scenarios, liquidity, hedges, and decision journal.
5. **Research Lab** — evidence firewall, experiments, failures, data health, and proof gates.

The bundled state remains a visibly labelled synthetic fixture. At runtime, EROS overlays provider-labelled public benchmark observations for US equities, IHSG, crypto, FX, commodities, and rates/volatility. Provider failures are isolated and may fall back to explicitly `STALE` last-good data. These observations support monitoring only; they do not establish a causal regime or unlock execution.

## Quick start

Requirements: Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
uv run pytest -q
uv run streamlit run app.py
```

Open `http://localhost:8501`.

## Quality gates

```bash
uv run ruff check src tests app.py
uv run mypy
uv run pytest -q
```

## Architecture

```text
app.py
config/                       # runtime, universe, evidence, validation policy
registries/                   # datasets and economic mechanisms
data/snapshots/               # frozen synthetic decision snapshot
src/eros/
  app/                        # five-tab Streamlit decision interface
  data/                       # adapters, ingestion, PIT alignment, health
  ontology/ + mechanisms/     # mechanism-first economic graph
  thesis/                     # competing hypotheses, Bayesian update, firewall
  research/                   # experiments and inherited-formula replication
  opportunity/ + allocation/  # costs, conservative EV, waiting, conflicts
  portfolio/                  # hidden exposure and scenarios
  audit/ + registries/        # replay and registry contracts
tests/                        # unit, integration, leakage, regression, e2e
reports/                      # limitations and production-readiness evidence
```

## Hard rules

- Mechanism over correlation.
- Evidence over narrative.
- Three to seven competing hypotheses, including a null.
- No standalone price-derived alpha or technical indicators.
- Point-in-time availability and vintages are mandatory.
- All costs and losses enter net EV.
- Missing or stale data disables downstream decisions.
- No model approves itself.
- Human approval remains mandatory for execution.

## Read before using outputs

- `docs/REQUIREMENTS_TRACEABILITY.md`
- `reports/PRODUCTION_READINESS.md`
- `reports/LIMITATIONS.md`
- `reports/CLEANUP_MANIFEST.md`
