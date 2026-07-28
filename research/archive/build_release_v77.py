"""Build deterministic War Room OS V7.7 Human-Readable Final ZIP."""
from __future__ import annotations

import hashlib
import json
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = Path(os.environ.get("WARROOM_V77_OUTPUT", ROOT / "War_Room_OS_v77_Human_Readable_Final.zip")).resolve()
MANIFEST = ROOT / "PACKAGE_MANIFEST_V77.json"
SHA_FILE = ROOT / "War_Room_OS_v77_Human_Readable_Final.sha256.txt"
FIXED_DT = (2026, 7, 26, 0, 0, 0)

EXCLUDED_PARTS = {".git", ".pytest_cache", "__pycache__", ".venv", "venv"}
EXCLUDED_PREFIXES = {"runtime/worker_", "runtime/dashboard_runtime.html", "static/desk_snapshot.json", "static/worker_status.json"}
EXCLUDED_NAMES = {OUT.name, MANIFEST.name, SHA_FILE.name}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def should_include(path: Path) -> bool:
    rel_path = path.relative_to(ROOT)
    rel = rel_path.as_posix()
    if any(part in EXCLUDED_PARTS for part in rel_path.parts):
        return False
    if path.name in EXCLUDED_NAMES:
        return False
    if any(rel.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return False
    return path.is_file()


def collect() -> list[Path]:
    return sorted((p for p in ROOT.rglob("*") if should_include(p)), key=lambda p: p.relative_to(ROOT).as_posix())


def main() -> None:
    validation = json.loads((ROOT / "V77_FINAL_VALIDATION.json").read_text(encoding="utf-8"))
    if validation.get("status") != "PASS":
        raise SystemExit("V77_FINAL_VALIDATION.json is not PASS")

    files = collect()
    entries = []
    for path in files:
        data = path.read_bytes()
        entries.append({"path": path.relative_to(ROOT).as_posix(), "size": len(data), "sha256": sha256_bytes(data)})
    digest = sha256_bytes(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    manifest = {
        "schema": "warroom.package_manifest.v77",
        "release": "War_Room_OS_v77_Human_Readable_Final",
        "release_date": "2026-07-26",
        "files": entries,
        "files_digest_sha256": digest,
        "inherited_decision_active_scoped_risk_controls": 1,
        "new_predictive_components": 0,
        "decision_active_ticker_or_directional_components": 0,
        "ticker_capital_permission": "BLOCKED",
        "claim_boundary": "Human-readable and semantic-state successor to V7.6; predictive proof boundary unchanged.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    zip_files = sorted(set(collect() + [MANIFEST]), key=lambda p: p.relative_to(ROOT).as_posix())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in zip_files:
            info = zipfile.ZipInfo(path.relative_to(ROOT).as_posix(), FIXED_DT)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())
    digest_zip = hashlib.sha256(OUT.read_bytes()).hexdigest()
    SHA_FILE.write_text(f"{digest_zip}  {OUT.name}\n", encoding="utf-8")
    print(json.dumps({"zip": str(OUT), "sha256": digest_zip, "members": len(zip_files), "manifest_entries": len(entries)}, indent=2))


if __name__ == "__main__":
    main()
