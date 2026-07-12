from __future__ import annotations
import hashlib, json
from pathlib import Path

def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build_release_manifest(root: Path, relative_paths: list[str]) -> dict:
    rows=[]
    for rel in sorted(relative_paths):
        p=root/rel
        rows.append({"path":rel,"sha256":file_hash(p)})
    release_hash=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",", ":")).encode()).hexdigest()
    return {"files":rows,"release_hash":release_hash}
