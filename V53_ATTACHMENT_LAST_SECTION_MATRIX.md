# v5.3 — Attachment Last-Section Completion Matrix

This matrix is the authoritative reconciliation of the final section of `Pasted text(161).txt`.
It separates work that was already completed in v5.1, work that was omitted from v5.2, and work that
cannot be validly reconstructed without the exact registered artifact.

| Final-section item | Reconciled status | v5.3 action | Live permission |
|---|---|---|---|
| Oil/OVX exact first-passage timing | Narrow historical support exists in global accounting; the separate later continuation battery did not promote its retest | Both records retained; neither is allowed to overwrite the other | 0 weight / BLOCKED |
| SPX/VIX exact timing | Point estimate did not clear the global confidence gate | Failure retained | 0 weight / BLOCKED |
| FX/EVZ exact timing | V61 completed and failed 0/1 | Result state and registered result hash integrated into every desk snapshot | 0 weight / BLOCKED |
| Nasdaq/VXN continuation | No completed standalone registered result is present in the recovered accounting metadata | Not guessed or silently reconstructed | BLOCKED |
| Pooled five-market options/volatility generalization | V62 protocol frozen, then aborted before outcome analysis because exact price sources could not be archived reproducibly | Exact-package recovery gate added; protocol, abort and package hashes pinned | BLOCKED |
| Directional portfolio evidence | V60 pre-1987 three-asset result is historically supported but fragile and not current-regime proof | Preserved as evidence-only; cannot authorize an instrument direction | 0 weight / BLOCKED |
| Continuation audit battery | 18 claims tested, 0 promoted | Full failure count and selected metrics retained | 0 weight / BLOCKED |
| v5.2 application integration | Missing | Closed in v5.3: research registry attached to runtime snapshot and rendered in Research Process ledger | Still BLOCKED |
| Prospective profitability | Not matured | No historical retuning accepted as a substitute | BLOCKED |

## Exact V62 recovery identifiers

```text
Global claim package SHA-256:
4f97add774a50690baf88e642e807be68eac3399b66628a2be2d61d9b116df99

Frozen V62 protocol SHA-256:
34d6925eb5dec62cfa84fd9ea40a8bd9b7910904900fde368621bde3356174a3

V62 acquisition-abort SHA-256:
78c1d9e2c64f9cfa372900ee4b49927c2efd4ed5b5c07bac8bc8851c58db0bbf
```

`recover_v62_exact.py` rejects any package whose digest differs, rejects duplicate or unsafe ZIP
members, and refuses outcome analysis until both exact registered V62 artifacts are recovered.

## Completion ruling

The omission in v5.2 is closed. The final-section research state is now integrated and fail-closed.
V62 itself is not falsely marked complete: its outcome analysis remains blocked because the exact
registered package/protocol binary is not mounted. Creating a substitute after prior outcomes are
known would be a new trial and would invalidate the original V62 claim.
