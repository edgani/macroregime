"""Build byte-deterministic War Room OS V5.9 release from exact V5.8 ancestry."""
from __future__ import annotations
import hashlib, json, tempfile, zipfile
from pathlib import Path
from verify_manifest_v59 import ROOT, MANIFEST, release_files, verify

OUT = ROOT.parent / "War_Room_OS_v59_Position_Lifecycle_from_v58.zip"
CHECKSUM = ROOT.parent / "War_Room_OS_v59_Position_Lifecycle_from_v58.sha256.txt"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def manifest_payload() -> dict:
    rows = [
        {"path": rel, "bytes": path.stat().st_size, "sha256": sha256(path)}
        for rel, path in release_files(ROOT).items()
    ]
    rows.sort(key=lambda row: row["path"])
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return {
        "schema": "warroom.package_manifest.v59",
        "release": "War_Room_OS_v59_Position_Lifecycle_from_v58",
        "visual_application_version": "4.2",
        "direct_parent": "War_Room_OS_v58_Exhaustive_Reverse_Engineering",
        "direct_parent_sha256": "a3e24e9cc390bb572817aa260e1018bc50f6271b870431e81cca03cf87645601",
        "continuation": "V59_POSITION_LIFECYCLE_AND_REAL_WIRING_FIX",
        "files_digest_sha256": hashlib.sha256(canonical).hexdigest(),
        "files": rows,
        "live_predictive_components_promoted": 0,
        "capital_permission": "BLOCKED",
        "claim_boundary": "Lifecycle output is descriptive only. It does not prove informed accumulation, future surge/top probability, ticker alpha, target accuracy, timing or prospective profitability."
    }


def safe(name: str) -> bool:
    path = Path(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and not name.startswith(("/", "\\"))


def write_zip(path: Path) -> None:
    files = release_files(ROOT)
    files[MANIFEST.name] = MANIFEST
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9, strict_timestamps=True) as archive:
        for rel in sorted(files):
            info = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            info.create_system = 3
            archive.writestr(info, files[rel].read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def validate_zip(path: Path) -> dict:
    errors: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            errors.append("duplicate zip members")
        errors.extend(f"unsafe:{name}" for name in names if not safe(name))
        with tempfile.TemporaryDirectory(prefix="v59_zip_") as td:
            archive.extractall(td)
            report = verify(Path(td), Path(td) / MANIFEST.name)
            if report["status"] != "PASS":
                errors.extend(report["errors"][:200])
    return {"status": "PASS" if not errors else "FAIL", "errors": errors}


def main() -> int:
    payload = manifest_payload()
    MANIFEST.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = verify()
    if report["status"] != "PASS":
        print(json.dumps(report, indent=2))
        return 1
    with tempfile.TemporaryDirectory(prefix="v59_build_") as td:
        a = Path(td) / "a.zip"
        b = Path(td) / "b.zip"
        write_zip(a)
        write_zip(b)
        if a.read_bytes() != b.read_bytes():
            print("deterministic rebuild mismatch")
            return 1
        OUT.write_bytes(a.read_bytes())
    clean = validate_zip(OUT)
    if clean["status"] != "PASS":
        print(json.dumps(clean, indent=2))
        return 1
    digest = sha256(OUT)
    CHECKSUM.write_text(f"{digest}  {OUT.name}\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "zip": str(OUT),
        "sha256": digest,
        "bytes": OUT.stat().st_size,
        "manifest_files": len(payload["files"]),
        "deterministic_rebuild": True,
        "clean_extract_manifest": "PASS"
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
