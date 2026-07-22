# Deploy War Room OS v4.2

Deploy by clean replacement. Never overlay v4.2 on an older folder because stale snapshots, static HTML, locks or legacy reports can preserve prior semantics.

## Required procedure

1. Extract to a new directory.
2. Configure secrets outside the package.
3. Run `CHECK_EVERYTHING.bat` on the target machine.
4. Deploy `app.py` only after `V42_USER_VALIDATION_REPORT.json` is `PASS`.
5. Keep capital integration disabled; the default proof registry promotes zero predictive components.

## Data behavior

Missing credentials must remain `NO_DATA`, `NOT_CONFIGURED`, `NOT_ENTITLED` or `ACTION_REQUIRED`. Optional source failures may not block independent domains, but they may not be silently imputed into claims.

## Official-source radar

A source-page hash change is a review alert only. A dated development remains `REVIEW_REQUIRED` until a human verifies the source, interpretation, beneficiary mapping and claim boundary. It never creates long/short direction by itself.

## Required deployment result

```text
software_permission: READY_FOR_USER_REVIEW
predictive_components_promoted: 0
capital_permission: BLOCKED
```
