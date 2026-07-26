# Signed proof receipts — v5.2

This directory is empty by design. Editable booleans are not proof.

A valid `warroom.proof_receipt.v2` must:

1. bind an exact `component`, `scope` and `claim_type`;
2. carry a unique receipt ID, key ID, issue time and expiry time;
3. be Ed25519-signed over canonical JSON excluding only the signature field;
4. use a key allowed for that component and exact scope;
5. pass a valid revocation registry and not be expired, future-dated or self-revoked;
6. set every required gate true: WFA, lockbox, prospective, cost model and multiple testing;
7. include 64-hex hashes for formula, code manifest, dataset manifest, frozen spec, trial ledger and prospective evidence;
8. bind every proof hash to an actual in-package artifact with the matching role and SHA-256;
9. include a matured prospective start/end window and at least 20 observations;
10. include explicit human approval for `CAPITAL_PERMISSION`.

## Trust-root pinning

Editing `proof/trusted_public_keys.json` is insufficient. Its SHA-256 must be pinned out-of-band in:

```text
WARROOM_TRUST_ROOT_SHA256=<64-hex hash>
```

The shipped trust store is empty. Validate the untouched package before installing keys. Store the expected hash in a separate secret/configuration channel, not beside the trust file.

## Fail-closed behavior

Missing/invalid trust root, missing/invalid revocation registry, unknown key, signature mismatch, component/scope mismatch, stale data, missing artifact, hash mismatch, immature prospective evidence or absent approval all result in `BLOCKED`.
