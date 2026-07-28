"""Seal deterministic V72 derived claim tables before the one-time lockbox opening."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from v72_release_runners import V72RunnerError, generate_derived_manifest, write_json_atomic


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--derived-root", required=True, type=Path)
    ap.add_argument("--source-receipt", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--c1", default="c1.csv")
    ap.add_argument("--c2", default="c2.csv")
    ap.add_argument("--c3", default="c3.csv")
    ns = ap.parse_args()
    names = {
        "V72_C1_VERIFIED_GAMMA_RESPONSE": ns.c1,
        "V72_C2_INCREMENTAL_PIN_BREAK": ns.c2,
        "V72_C3_NET_GAMMA_SCALP": ns.c3,
    }
    try:
        payload = generate_derived_manifest(ns.derived_root, ns.source_receipt, filenames=names)
        write_json_atomic(ns.out, payload)
        print(json.dumps({"schema": payload["schema"], "status": "PASS_DERIVED_TABLES_SEALED_UNOPENED", "tables": len(payload["files"]), "capital_permission": "BLOCKED"}, indent=2))
        return 0
    except (V72RunnerError, OSError, ValueError) as exc:
        print(json.dumps({"schema":"warroom.v72_derived_manifest_generation_failure","status":"FAIL","error":f"{type(exc).__name__}: {exc}","capital_permission":"BLOCKED"}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
