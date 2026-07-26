# P6.91 — Operational Current Shadow Selector

The current selector trains only on rows whose target outcomes are already unlocked before the latest
decision date. It writes a Top-20 shortlist with:

- score and rank;
- fundamental and market evidence;
- filing accession and filing date;
- model, contract, input and output hashes;
- explicit `SHADOW_RESEARCH_ONLY` permission.
