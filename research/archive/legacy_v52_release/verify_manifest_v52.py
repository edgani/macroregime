"""Strict manifest verifier for War Room OS v5.2 hardened release."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "PACKAGE_MANIFEST_V52.json"

IGNORE_DIRS = {".git", ".venv", "__pycache__", ".cache", ".pytest_cache", "audit_logs"}
IGNORE_EXACT = {
    "PACKAGE_MANIFEST_V52.json", "PACKAGE_MANIFEST_V52.sha256",
    "V52_USER_VALIDATION_REPORT.json", "desk_data.json", "dashboard_live.html",
    "runtime/desk_snapshot.json", "runtime/worker_status.json", "runtime/force_refresh.flag",
    "runtime/worker.instance.lock", "runtime/worker.pid", "runtime/worker_boot.log", "runtime/worker.log",
    "static/desk_snapshot.json", "static/worker_status.json",
}
IGNORE_SUFFIXES = {".pyc", ".tmp", ".log"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ignored(rel: Path) -> bool:
    posix = rel.as_posix()
    if any(part in IGNORE_DIRS for part in rel.parts):
        return True
    if posix in IGNORE_EXACT or rel.suffix.lower() in IGNORE_SUFFIXES:
        return True
    if posix.startswith("proof/receipts/") and rel.name != "README.md":
        return True
    if rel.name.startswith(".") and posix not in {".env.example", ".streamlit/config.toml", "runtime/.gitkeep", "static/.gitkeep"}:
        return True
    return False


def release_files(root: Path = ROOT) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root)
            if not ignored(rel):
                out[rel.as_posix()] = path
    return out


def verify(root: Path = ROOT, manifest_path: Path | None = None) -> dict:
    manifest_path = manifest_path or (root / MANIFEST.name)
    result = {"status": "FAIL", "errors": [], "checked_files": 0, "manifest_files": 0}
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        result["errors"].append(f"manifest unreadable: {type(exc).__name__}: {exc}")
        return result
    if raw.get("schema") != "warroom.package_manifest.v52":
        result["errors"].append("manifest schema mismatch")
    rows = raw.get("files") or []
    expected: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            result["errors"].append("invalid manifest row")
            continue
        rel = str(row.get("path") or "")
        p = Path(rel)
        if not rel or p.is_absolute() or ".." in p.parts or rel in expected:
            result["errors"].append(f"unsafe or duplicate path: {rel}")
            continue
        expected[rel] = row
    actual = release_files(root)
    result["manifest_files"] = len(expected)
    result["checked_files"] = len(actual)
    for rel in sorted(set(expected) - set(actual)):
        result["errors"].append(f"missing:{rel}")
    for rel in sorted(set(actual) - set(expected)):
        result["errors"].append(f"unexpected:{rel}")
    for rel in sorted(set(actual) & set(expected)):
        path = actual[rel]; row = expected[rel]
        if path.stat().st_size != int(row.get("bytes", -1)):
            result["errors"].append(f"size:{rel}")
        elif sha256(path) != str(row.get("sha256") or ""):
            result["errors"].append(f"hash:{rel}")
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if hashlib.sha256(canonical).hexdigest() != str(raw.get("files_digest_sha256") or ""):
        result["errors"].append("manifest files digest mismatch")
    result["status"] = "PASS" if not result["errors"] else "FAIL"
    return result


def main() -> int:
    result = verify()
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
