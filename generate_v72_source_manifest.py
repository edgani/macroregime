"""Generate the deterministic V72 licensed-source manifest; no outcomes are opened."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from v72_release_runners import V72RunnerError, generate_source_manifest, write_json_atomic


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--licensed-root", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--include-grk", action="store_true")
    group.add_argument("--exclude-grk", action="store_true")
    ns = ap.parse_args()
    include = True if ns.include_grk else False if ns.exclude_grk else None
    try:
        payload = generate_source_manifest(ns.licensed_root, include_grk=include)
        write_json_atomic(ns.out, payload)
        print(json.dumps({"schema": payload["schema"], "status": "PASS_MANIFEST_GENERATED_UNEVALUATED", "files": len(payload["files"]), "capital_permission": "BLOCKED"}, indent=2))
        return 0
    except (V72RunnerError, OSError, ValueError) as exc:
        print(json.dumps({"schema":"warroom.v72_source_manifest_generation_failure","status":"FAIL","error":f"{type(exc).__name__}: {exc}","capital_permission":"BLOCKED"}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
