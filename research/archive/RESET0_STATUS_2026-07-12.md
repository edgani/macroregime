# War Room OS v3 — Reset Sprint 0 Status

## Source lock

- Source ZIP: `warroom_os_COMPLETE (6).zip`
- SHA-256: `92c670a92b3a594fb5775c45ce00c4fcaed4f9dcff14ac06e8c7acaf04886a9a`
- Compared with previous ZIP: 213/216 files identical; only three files changed.

## Locked scientific decisions

- New OHLC/risk-range patch: `REJECTED` as production default.
- Legacy MQA: `REJECTED` for entry/stop/target/probability.
- Factor momentum 126: `REJECTED` as validated numeric signal.
- Crash pressure: `RESEARCH_ONLY`, banded descriptive context.
- Panic bottom: `RESEARCH_ONLY`, descriptive fear context.
- Unknown or not-evaluated scope: `UNAVAILABLE`.

## Engineering delivered

- Research and decision contracts are separated.
- PAPER/LIVE contracts require complete execution and evidence.
- Actionability is fail-closed.
- Registry is bound to actual source implementation hashes.
- Legacy imports are prohibited in the clean `src` tree.
- Migration decisions are explicit.

## Validation

```text
18 tests discovered
18 tests passed
```

This validates Reset Sprint 0 engineering only. It does not validate trading edge.

## Next sprint

Build point-in-time data/provider contracts and MQA/Momentum benchmark sensors without importing the legacy decision stack.
