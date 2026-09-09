# Test Matrix

`python tests/run_all.py` executes 28 isolated suites covering:

- package, static, and final contracts;
- decision core, adapters, macro snapshots, IHSG transactions, and DeFiLlama behavior;
- opportunity scoring, story optionality, negative controls, and fuzz cases;
- immutable lifecycle episodes, point-in-time timestamps, horizon selection, and forward outcomes;
- chronological walk-forward behavior, prospective baselines, universe snapshots, and runner cohorts;
- readiness, economic-capture, valuation, evidence-quality, and market-specific gates;
- unified UI, visual/static contracts, navigation interaction, and query-parameter deep links;
- release packaging and extraction exclusions.

Browser automation is separate: `tests/browser_smoke.py` runs against a live Streamlit server when the host permits Chromium.

The authoritative latest result belongs in `LOGIC_AUDIT.md`; generated logs and screenshots are not maintained in Git.
