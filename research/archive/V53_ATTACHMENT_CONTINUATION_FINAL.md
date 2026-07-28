# War Room OS v5.3 — Attachment-Last-Section Continuation

## Correction to v5.2

v5.2 hardened the real v4.2 application but stopped too early. It did not import the research state
recorded at the end of `Pasted text(161).txt` and it incorrectly described the v5.1 artifacts as
absent from the broader File Library.

The recovered accounting says:

- the separate v5.1 continuation battery tested 18 claims and promoted 0;
- the global claim package retained four narrow historical supports;
- V61 EUR/USD–EVZ exact timing was completed and failed 0/1;
- V62 pooled five-market ETF/volatility generalization was frozen, then aborted before outcome
  analysis because its exact price sources could not be archived reproducibly;
- V63 SPX causal-direction ensemble failed;
- robust current direction, an exact signed point target, cross-market options generalization,
  current-regime stability and prospective profitability remain unproven.

These are not contradictions. The 0/18 continuation battery and the global accounting refer to
different registered studies. v5.3 preserves both rather than allowing the later battery to erase
older narrow results or allowing older results to rescue later failures.

## What v5.3 changes

1. Adds `research_evidence_registry_v53.json` to every desk snapshot.
2. Shows historical supported, failed and aborted studies in the Research Process ledger.
3. Forces every historical result to `live_decision_weight = 0`, `prospective_pass = false`, and
   `capital_permission = BLOCKED`.
4. Adds `recover_v62_exact.py`, which accepts only the exact global package SHA-256 and exact V62
   protocol/abort hashes. It rejects ZIP traversal, duplicates and source substitution.
5. Archives the official OVX CSV already acquired in this session, but explicitly refuses to assume
   that it is a frozen V62 input before the exact protocol is recovered.

## Why V62 is still blocked

The exact V62 protocol has registered hash
`34d6925eb5dec62cfa84fd9ea40a8bd9b7910904900fde368621bde3356174a3`, but the protocol body,
source list, original runner and exact global ZIP were not inside the supplied v4.2 or v5.2 ZIP.
Guessing the five markets or using newly downloaded proxies would create a new trial after seeing
prior outcomes. v5.3 therefore closes the omission in the software and recovery process without
fabricating the missing experiment.

## Verdict

- Application hardening: PASS inherited and revalidated.
- Attachment research-state integration: PASS.
- Claim accounting preservation: PASS.
- V61: NOT PROVEN.
- V62 outcome analysis: BLOCKED BEFORE OUTCOME.
- Predictive components promoted to live: 0.
- Capital permission: BLOCKED.

## Final validation after integration

- Fresh-copy compile: PASS
- Adversarial hardening: 39/39 PASS
- Attachment-continuation controls: 11/11 PASS
- GCFIS warnings-as-errors: PASS
- Deep UI and market-contract validation: PASS
- Bundled-data container integrity: PASS
- Synthetic desk/dashboard: PASS
- Statistical positive/negative controls: PASS
- Source mutation during validators: 0
- Streamlit health and Parquet semantic recomputation: BLOCKED_BY_ENVIRONMENT, not claimed as PASS

See `V53_RELEASE_CLEAN_EXTRACT_VALIDATION.json`, `V53_FINAL_STATUS.md`, and
`V53_ATTACHMENT_LAST_SECTION_MATRIX.md`.
