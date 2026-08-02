# EROS v3 Requirements Traceability

Source: `EROS_v3_FINAL_MASTER_PROMPT.pdf`, sealed 2026-08-02.

This matrix is intentionally honest: `Implemented` means exercised by code and tests in this repository. `Data debt` means the architecture and fail-closed state exist, but the required verified source coverage or matured evidence does not.

| Requirement family | Implementation target | Verification | Current classification |
|---|---|---|---|
| Five-tab decision UI | `src/eros/app/`, `app.py` | Streamlit AppTest | Implemented |
| Visible synthetic mode and execution lock | `src/eros/app/state.py`, dashboard fixture | E2E product contract | Implemented |
| Global, registry-driven universe | `config/universe.yaml`, registries | Registry tests | Implemented baseline; coverage data debt |
| RAW to decision provenance | `src/eros/data/`, audit replay | Integration and checksum tests | Implemented baseline |
| Point-in-time availability | `src/eros/data/pit/` | Leakage tests | Implemented baseline |
| Feed health fails closed | `src/eros/data/quality/` | Unit tests | Implemented baseline |
| Narrative-to-evidence firewall | `src/eros/thesis/narrative_firewall.py` | Unit tests | Implemented baseline |
| Competing hypotheses and null thesis | `src/eros/thesis/discovery.py` | Unit tests | Implemented baseline |
| Bayesian evidence-family de-duplication | `src/eros/thesis/bayes.py` | Unit tests | Implemented baseline |
| Mechanism-first graph | `src/eros/mechanisms/`, `src/eros/ontology/` | Unit tests | Implemented baseline; validation data debt |
| Conservative net EV and all costs | `src/eros/opportunity/` | Unit tests | Implemented baseline |
| Value of waiting and conflict downgrade | `src/eros/allocation/` | Unit tests | Implemented baseline |
| Portfolio exposure and scenarios | `src/eros/portfolio/` | Unit tests | Implemented baseline; no personal portfolio loaded |
| No technical indicators | Source and registry policy | Regression scan | Implemented |
| Trial/failure preservation | Research and failure registries | Registry tests | Baseline implementation; evidence population data debt |
| Prospective prediction journal | Decision/research stores | Acceptance status | Data debt; no matured forecasts |
| Live-capital approval | Execution policy | E2E lock assertion | Intentionally blocked |
| Global live adapters and licensing | Adapter interfaces and dataset registry | Adapter integration tests | Material data debt |
| Replicated out-of-sample proof | Experiment registry and reports | Acceptance battery | Not proven |

## Non-negotiable product behavior

- Mechanisms precede tickers.
- Missing or stale data produces `UNKNOWN`, `STALE`, or `NO_DATA`; never a neutral fabricated score.
- Narratives can create research tickets but cannot change allocation directly.
- Every actionable path remains human-approved and evidence-gated.
- No standalone price-derived alpha or technical indicator is permitted.
- The interface shows evidence status, uncertainty, lineage, blind spots, and research debt.
