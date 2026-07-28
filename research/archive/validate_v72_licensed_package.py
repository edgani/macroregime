"""CLI preflight for a local licensed V72 source archive."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from v72_release_runners import V72RunnerError, validate_licensed_source_package, write_json_atomic


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--licensed-root", required=True, type=Path)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ns = ap.parse_args()
    try:
        receipt = validate_licensed_source_package(ns.manifest, ns.licensed_root)
        write_json_atomic(ns.out, receipt)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0
    except (V72RunnerError, OSError, ValueError) as exc:
        print(json.dumps({"schema":"warroom.v72_source_validation_failure","status":"FAIL","error":f"{type(exc).__name__}: {exc}","capital_permission":"BLOCKED"}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
