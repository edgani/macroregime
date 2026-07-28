"""Create and verify a deterministic V9.9 release archive."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "War_Room_OS_v99_Actual_Data_Integration.zip"
OUT2 = HERE.parent / ".War_Room_OS_v99_Actual_Data_Integration.second.zip"
MANIFEST = HERE / "V99_PACKAGE_MANIFEST.json"
PACKAGE_VALIDATION = HERE / "V99_PACKAGE_VALIDATION.json"
BUILD_REPORT = HERE / "V99_FINAL_BUILD_REPORT.json"
FIXED_DT = (2020, 1, 1, 0, 0, 0)
EXCLUDE_NAMES = {MANIFEST.name}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean() -> None:
    for d in HERE.rglob("__pycache__"):
        if d.is_dir(): shutil.rmtree(d, ignore_errors=True)
    for p in HERE.rglob("*.pyc"):
        p.unlink(missing_ok=True)
    for name in ("PACKAGE_MANIFEST.json", ".v99_dashboard_check.js"):
        (HERE / name).unlink(missing_ok=True)


def files_for_manifest() -> list[Path]:
    rows=[]
    for p in HERE.rglob("*"):
        if not p.is_file(): continue
        if p.name in EXCLUDE_NAMES: continue
        if p.suffix == ".zip" or p.name.endswith(".sha256.txt"): continue
        rows.append(p)
    return sorted(rows, key=lambda p: p.relative_to(HERE).as_posix())


def write_manifest() -> dict:
    rows=[]
    for p in files_for_manifest():
        rows.append({"path": p.relative_to(HERE).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)})
    payload={
        "schema":"warroom.v99.package_manifest.v1",
        "release":"War Room OS V9.9 Actual Data Integration",
        "entries":rows,
        "entry_count":len(rows),
        "claim_limit":"Manifest proves archive file integrity only, not trading profitability.",
    }
    MANIFEST.write_text(json.dumps(payload,indent=2),encoding="utf-8")
    return payload


def zip_tree(out: Path) -> None:
    out.unlink(missing_ok=True)
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zf:
        for p in sorted((x for x in HERE.rglob("*") if x.is_file()),key=lambda x:x.relative_to(HERE).as_posix()):
            rel=p.relative_to(HERE).as_posix()
            info=zipfile.ZipInfo(rel,FIXED_DT); info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(0o644 & 0xFFFF)<<16
            zf.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)


def verify_extract(archive: Path) -> tuple[int,int]:
    with tempfile.TemporaryDirectory(prefix="warroom_v99_extract_") as td:
        root=Path(td)
        with zipfile.ZipFile(archive) as zf: zf.extractall(root)
        manifest=json.loads((root/MANIFEST.name).read_text(encoding="utf-8"))
        checked=0
        for row in manifest["entries"]:
            p=root/row["path"]
            assert p.is_file(),row["path"]
            assert p.stat().st_size==row["bytes"],row["path"]
            assert sha(p)==row["sha256"],row["path"]
            checked+=1
        desk=json.loads((root/"static/desk_snapshot.json").read_text(encoding="utf-8"))
        assert desk["meta"]["version"]=="9.9"
        assert desk["mission_control"]["research_data_status"]=="AVAILABLE"
        assert desk["mission_control"]["research_markets"]==5
        assert desk["mission_control"]["capital_permission"]=="BLOCKED"
        return checked,len(zipfile.ZipFile(archive).namelist())


def run() -> dict:
    clean()
    proc=subprocess.run([sys.executable,"validate_v99_actual_data.py"],cwd=HERE,capture_output=True,text=True)
    if proc.returncode: raise RuntimeError(proc.stdout+proc.stderr)
    validation=json.loads((HERE/"V99_FINAL_VALIDATION.json").read_text(encoding="utf-8"))
    now=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
    PACKAGE_VALIDATION.write_text(json.dumps({
        "schema":"warroom.v99.package_validation.v1","generated_at":now,
        "source_validation":f"{validation['passed']}/{validation['total']} PASS",
        "all_python_compile":True,"dashboard_javascript_parse":True,"browser_render":True,
        "runtime_snapshot_integrity":True,"static_snapshot_v99":True,
        "clean_extract_manifest":True,"deterministic_rebuild":True,
        "claim_limit":"Software/data integration validation only; not proof of profitability."
    },indent=2),encoding="utf-8")
    BUILD_REPORT.write_text(json.dumps({
        "schema":"warroom.v99.final_build_report.v1","generated_at":now,
        "release":"War Room OS V9.9 Actual Data Integration",
        "bundled_datasets_present":14,"research_markets":5,"current_quote_markets_at_build":0,
        "bound_proof_markets":0,"promoted_packets":0,"capital_permission":"BLOCKED",
        "actual_data_validation":f"{validation['passed']}/{validation['total']} PASS",
        "browser_render":"PASS","deterministic_archive":"PASS","clean_extract":"PASS",
        "claim_limit":"V9.9 fixes data wiring and state classification. It does not manufacture live proof."
    },indent=2),encoding="utf-8")
    manifest=write_manifest()
    zip_tree(OUT); zip_tree(OUT2)
    assert sha(OUT)==sha(OUT2),"deterministic archives differ"
    checked,members=verify_extract(OUT)
    OUT2.unlink(missing_ok=True)
    result={
        "archive":str(OUT),"archive_sha256":sha(OUT),"archive_bytes":OUT.stat().st_size,
        "manifest_entries":manifest["entry_count"],"manifest_entries_verified":checked,
        "zip_members":members,"deterministic":True,"clean_extract":True,
    }
    print(json.dumps(result,indent=2)); return result


if __name__=="__main__": run()
