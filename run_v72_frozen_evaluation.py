"""One-time production CLI for the frozen V72 historical evaluator."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from v72_release_runners import V72RunnerError, open_and_evaluate_lockbox


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--derived-root", required=True, type=Path)
    ap.add_argument("--derived-manifest", required=True, type=Path)
    ap.add_argument("--source-receipt", required=True, type=Path)
    ap.add_argument("--derived-receipt", required=True, type=Path)
    ap.add_argument("--open-receipt", required=True, type=Path)
    ap.add_argument("--result", required=True, type=Path)
    ns = ap.parse_args()
    try:
        result = open_and_evaluate_lockbox(
            derived_manifest_path=ns.derived_manifest,
            derived_root=ns.derived_root,
            source_receipt_path=ns.source_receipt,
            derived_receipt_path=ns.derived_receipt,
            open_receipt_path=ns.open_receipt,
            result_path=ns.result,
        )
        print(json.dumps({"schema":result["schema"],"status":result["status"],"capital_permission":result["capital_permission"]}, indent=2))
        return 0
    except (V72RunnerError, OSError, ValueError) as exc:
        print(json.dumps({"schema":"warroom.v72_historical_evaluation_failure","status":"FAIL","error":f"{type(exc).__name__}: {exc}","capital_permission":"BLOCKED"}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
