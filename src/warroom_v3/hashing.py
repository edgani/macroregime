from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_hash(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def combined_file_hash(paths: list[str | Path], *, root: str | Path | None = None) -> str:
    base = Path(root).resolve() if root else None
    records = []
    for raw in sorted(Path(p).resolve() for p in paths):
        name = raw.relative_to(base).as_posix() if base and raw.is_relative_to(base) else raw.name
        records.append({"path": name, "sha256": file_hash(raw)})
    return canonical_hash(records)
