"""Strict importer for unmodified official IDX browser JSON exports."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

OFFICIAL_HOST = re.compile(r"(^|\.)idx\.co\.id$", re.I)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _find_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list) and all(isinstance(x, dict) for x in data):
        return data
    if isinstance(data, dict):
        for key in ("data", "Data", "results", "Results"):
            value = data.get(key)
            if isinstance(value, list) and all(isinstance(x, dict) for x in value):
                return value
    raise ValueError("IDX export has no recognizable row array")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--output", default="runtime/v95_idx_browser_import")
    args = parser.parse_args()
    from urllib.parse import urlparse
    host = urlparse(args.source_url).hostname or ""
    if not OFFICIAL_HOST.search(host):
        raise SystemExit("source-url must be an official idx.co.id URL")
    src = Path(args.input); raw = src.read_text(encoding="utf-8"); data = json.loads(raw); rows = _find_rows(data)
    if not rows:
        raise SystemExit("IDX export contains zero rows")
    keys = {str(k).lower() for row in rows[:100] for k in row}
    if not any(token in "|".join(keys) for token in ("code", "ticker", "symbol", "kode", "emiten")):
        raise SystemExit("IDX export schema lacks an issuer/security identifier")
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    dest = out / src.name; dest.write_text(raw, encoding="utf-8")
    receipt = {
        "schema": "warroom.v95.idx_browser_import.v1",
        "source": "IDX_OFFICIAL_BROWSER_EXPORT",
        "source_url": args.source_url,
        "imported_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "path": dest.name,
        "rows": len(rows),
        "sha256": sha(dest),
        "capital_permission": "BLOCKED",
        "claim_limit": "Current/public IDX export only; not survivor-free historical proof.",
    }
    receipt["receipt_hash"] = hashlib.sha256(json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (out / (src.stem + "_receipt.json")).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
