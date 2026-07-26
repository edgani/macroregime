# Deploy War Room OS v5.2

Deploy only by clean replacement.

1. Extract the release into a new folder.
2. Run `CHECK_EVERYTHING.bat` before adding old caches, proof keys, receipts or secrets.
3. Require `V52_USER_VALIDATION_REPORT.json` to show no failures and no environment blockers.
4. Configure live-data credentials outside source control.
5. Keep all execution/capital integration disabled; the default proof state promotes zero components.
6. After any source change, dependency change, trusted-key change or proof-receipt change, rerun validation and retain the new report.

Missing or unavailable feeds must remain `NO_DATA`, `NOT_CONFIGURED`, `NOT_ENTITLED`, `STALE` or `ACTION_REQUIRED`. They may not be silently imputed into a predictive claim.

A source-page change or current-development item is a review event only. It does not create direction.

Required deployment state:

```text
software_permission: READY_FOR_RESEARCH_REVIEW
predictive_components_promoted: 0
capital_permission: BLOCKED
```
