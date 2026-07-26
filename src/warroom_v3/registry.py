from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()

def load_registry(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("registry_hash") != canonical_hash(data.get("entries", [])):
        raise ValueError("formula registry hash mismatch")
    return data
