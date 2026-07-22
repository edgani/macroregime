# Evidence mount point

This directory is intentionally empty in the verification build. Place real, signed artifacts here:

- `data_lineage.json`
- `component_registry.json`
- `wfa_results.json`
- `portfolio_cost_model.json`
- `lockbox_seal.json`
- `prospective_results.json`

The doctor reports `BLOCKED / NOT RUN` until these artifacts exist and satisfy their contracts.
Template files live in `../evidence_templates/`; templates never count as evidence.
