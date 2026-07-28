"""Dependency-light integrity validation for bundled datasets.

This validates container structure and hashes without pretending to reproduce Parquet semantics.
Semantic research recomputation still requires pyarrow and is reported separately.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHECKS = []


def check(name, passed, detail=""):
    CHECKS.append({"name": name, "passed": bool(passed), "detail": str(detail)[:4000]})
    print(("PASS" if passed else "FAIL"), name, detail)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parquet_container(path: Path) -> dict:
    size = path.stat().st_size
    if size < 12:
        return {"ok": False, "reason": "too small", "size": size}
    with path.open("rb") as f:
        head = f.read(4)
        f.seek(-8, 2)
        tail = f.read(8)
    footer_len = int.from_bytes(tail[:4], "little")
    ok = head == b"PAR1" and tail[4:] == b"PAR1" and 0 < footer_len <= size - 12
    return {"ok": ok, "size": size, "footer_length": footer_len, "sha256": sha(path)}


def main() -> int:
    asset_suffixes = {".json", ".csv", ".parquet", ".txt", ".yaml", ".yml"}
    files = sorted(
        p for p in ROOT.rglob("*")
        if p.is_file()
        and p.suffix.lower() in asset_suffixes
        and any(part in {"data", "research", "research_data", "datasets"} for part in p.relative_to(ROOT).parts)
        and "__pycache__" not in p.parts
    )
    parquets = [p for p in files if p.suffix.lower() == ".parquet"]
    nonempty = [p for p in files if p.stat().st_size > 0]
    check("bundled_data_files_present", bool(files), len(files))
    check("bundled_data_files_nonempty", len(nonempty) == len(files), f"{len(nonempty)}/{len(files)}")
    pq = {str(p.relative_to(ROOT)): parquet_container(p) for p in parquets}
    check("parquet_containers_structurally_valid", all(x["ok"] for x in pq.values()), pq)
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in files}
    report = {
        "schema": "warroom.bundled_data_integrity.v52",
        "status": "PASS" if all(x["passed"] for x in CHECKS) else "FAIL",
        "semantic_recomputation": "REQUIRES_PYARROW",
        "files": len(files), "parquet_files": len(parquets),
        "checks": CHECKS, "sha256": hashes, "parquet_metadata": pq,
    }
    (ROOT / "V52_BUNDLED_DATA_INTEGRITY_REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
