"""Build a deterministic War Room OS v5.2 ZIP from the strict release file set."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from verify_manifest_v52 import ROOT, MANIFEST, release_files, verify

OUT = ROOT.parent / "War_Room_OS_v52_Real_Source_Hardened.zip"
CHECKSUM = ROOT.parent / "War_Room_OS_v52_Real_Source_Hardened.sha256.txt"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest() -> dict:
    rows = []
    for rel, path in release_files(ROOT).items():
        rows.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256(path)})
    rows.sort(key=lambda x: x["path"])
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "schema": "warroom.package_manifest.v52",
        "release": "War_Room_OS_v52_Real_Source_Hardened",
        "visual_application_version": "4.2",
        "hardening_release_version": "5.2",
        "files_digest_sha256": hashlib.sha256(canonical).hexdigest(),
        "files": rows,
        "mutable_exclusions": [
            "runtime/*", "static/desk_snapshot.json", "static/worker_status.json",
            "proof/receipts/* except README.md", ".venv/*", "V52_USER_VALIDATION_REPORT.json",
        ],
        "claim_boundary": "Package integrity and software hardening are not predictive proof; capital remains blocked.",
    }


def safe_member(name: str) -> bool:
    p = Path(name)
    return bool(name) and not p.is_absolute() and ".." not in p.parts and not name.startswith(("/", "\\"))


def write_zip(path: Path) -> None:
    files = release_files(ROOT)
    files[MANIFEST.name] = MANIFEST
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, strict_timestamps=True) as zf:
        for rel in sorted(files):
            data = files[rel].read_bytes()
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            info.create_system = 3
            zf.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def validate_zip(path: Path) -> dict:
    errors: list[str] = []
    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()
        if len(names) != len(set(names)):
            errors.append("duplicate zip members")
        errors += [f"unsafe zip path:{name}" for name in names if not safe_member(name)]
        with tempfile.TemporaryDirectory(prefix="warroom_v52_zip_") as td:
            dst = Path(td)
            zf.extractall(dst)
            check = verify(dst, dst / MANIFEST.name)
            if check["status"] != "PASS":
                errors.extend(check["errors"][:100])
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def main() -> int:
    payload = manifest()
    MANIFEST.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    local = verify()
    if local["status"] != "PASS":
        print(json.dumps(local, indent=2)); return 1
    with tempfile.TemporaryDirectory(prefix="warroom_v52_build_") as td:
        first = Path(td) / "a.zip"; second = Path(td) / "b.zip"
        write_zip(first); write_zip(second)
        h1 = sha256(first); h2 = sha256(second)
        if h1 != h2 or first.read_bytes() != second.read_bytes():
            print("deterministic rebuild mismatch"); return 1
        OUT.write_bytes(first.read_bytes())
    zip_check = validate_zip(OUT)
    if zip_check["status"] != "PASS":
        print(json.dumps(zip_check, indent=2)); return 1
    digest = sha256(OUT)
    CHECKSUM.write_text(f"{digest}  {OUT.name}\n", encoding="utf-8")
    result = {
        "status": "PASS", "zip": str(OUT), "sha256": digest,
        "bytes": OUT.stat().st_size, "manifest_files": len(payload["files"]),
        "manifest_files_digest_sha256": payload["files_digest_sha256"],
        "deterministic_rebuild": True, "zip_path_safety": True, "clean_extract_manifest": "PASS",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
