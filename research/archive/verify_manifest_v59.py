"""Strict deterministic package manifest verifier for War Room OS v5.9."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "PACKAGE_MANIFEST_V59.json"
IGNORE_DIRS = {
    ".git", ".venv", "__pycache__", ".cache", ".pytest_cache", "audit_logs", "runtime",
    "audit_state_v55", "audit_state_v56", "audit_state_v57", "audit_state_v58", "audit_state_v59"
}
IGNORE_EXACT = {
    "PACKAGE_MANIFEST_V59.json",
    "V59_USER_VALIDATION_REPORT.json", "V59_SOURCE_VALIDATION.json",
    "desk_data.json", "dashboard_live.html",
    "V42_DEEP_REAUDIT_PREVIEW.png", "V42_DEEP_REAUDIT_VALIDATION_REPORT.json",
    "runtime/desk_snapshot.json", "runtime/worker_status.json", "runtime/force_refresh.flag",
    "runtime/worker.instance.lock", "runtime/worker.pid", "runtime/worker_boot.log", "runtime/worker.log",
    "static/desk_snapshot.json", "static/worker_status.json",
    "V52_HARDENING_ADVERSARIAL_REPORT.json", "V52_BUNDLED_DATA_INTEGRITY_REPORT.json",
    "V55_PARQUET_COMPAT_VALIDATION.json", "V70_OPTIONS_GAMMA_VALIDATION.json",
    "V71_OPTIONS_PROSPECTIVE_VALIDATION.json", "V72_SIGNED_DEALER_VALIDATION.json",
    "V72_OUTCOME_EVALUATOR_VALIDATION.json", "V72_RELEASE_RUNNER_VALIDATION.json",
    "V72_MANIFEST_GENERATOR_VALIDATION.json"
}
IGNORE_SUFFIXES = {".pyc", ".tmp", ".log"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def ignored(rel: Path) -> bool:
    s = rel.as_posix()
    return (
        any(part in IGNORE_DIRS for part in rel.parts)
        or s in IGNORE_EXACT
        or rel.suffix.lower() in IGNORE_SUFFIXES
        or (s.startswith("proof/receipts/") and rel.name != "README.md")
        or (rel.name.startswith(".") and s not in {".env.example", ".streamlit/config.toml", "runtime/.gitkeep", "static/.gitkeep"})
    )


def release_files(root: Path = ROOT) -> dict[str, Path]:
    return {
        p.relative_to(root).as_posix(): p
        for p in sorted(root.rglob("*"))
        if p.is_file() and not ignored(p.relative_to(root))
    }


def verify(root: Path = ROOT, manifest_path: Path | None = None) -> dict:
    mp = manifest_path or root / MANIFEST.name
    result = {"status": "FAIL", "errors": [], "checked_files": 0, "manifest_files": 0}
    try:
        raw = json.loads(mp.read_text(encoding="utf-8"))
    except Exception as exc:
        result["errors"].append(f"manifest unreadable:{type(exc).__name__}:{exc}")
        return result
    if raw.get("schema") != "warroom.package_manifest.v59":
        result["errors"].append("manifest schema mismatch")
    rows = raw.get("files") or []
    expected: dict[str, dict] = {}
    for row in rows:
        rel = str(row.get("path") or "")
        path = Path(rel)
        if not rel or path.is_absolute() or ".." in path.parts or rel in expected:
            result["errors"].append(f"unsafe or duplicate path:{rel}")
        else:
            expected[rel] = row
    actual = release_files(root)
    result["manifest_files"] = len(expected)
    result["checked_files"] = len(actual)
    for rel in sorted(set(expected) - set(actual)):
        result["errors"].append(f"missing:{rel}")
    for rel in sorted(set(actual) - set(expected)):
        result["errors"].append(f"unexpected:{rel}")
    for rel in sorted(set(actual) & set(expected)):
        path = actual[rel]
        row = expected[rel]
        if path.stat().st_size != int(row.get("bytes", -1)):
            result["errors"].append(f"size:{rel}")
        elif sha256(path) != str(row.get("sha256") or ""):
            result["errors"].append(f"hash:{rel}")
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    if hashlib.sha256(canonical).hexdigest() != str(raw.get("files_digest_sha256") or ""):
        result["errors"].append("manifest files digest mismatch")
    result["status"] = "PASS" if not result["errors"] else "FAIL"
    return result


if __name__ == "__main__":
    import sys
    report = verify()
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)
