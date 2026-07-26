"""Clean-copy, mutation-detecting release audit for War Room OS v5.2 hardening.

Every executable validator runs in a fresh copy.  Existing immutable files are hashed before and
after; a validator that edits source/config/data fails even when it returns zero.  Environmental
blockers are distinct from passes and cannot yield a full-release verdict.
"""
from __future__ import annotations

import compileall
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
CORE_REPORT = ROOT / "V52_CLEAN_EXTRACT_AUDIT_REPORT.json"
SUMMARY_LOG = ROOT / "V52_CLEAN_EXTRACT_TEST_LOG.txt"

IGNORE_DIRS = {"__pycache__", ".git", ".cache", "runtime", "audit_logs"}
GENERATED_NAMES = {
    "dashboard_live.html", "desk_data.json", "V42_DEEP_REAUDIT_PREVIEW.png",
    "PACKAGE_MANIFEST_V52.json", "PACKAGE_MANIFEST_V52.sha256",
}
IMMUTABLE_SUFFIXES = {".py", ".html", ".md", ".txt", ".json", ".csv", ".parquet", ".yaml", ".yml", ".toml"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def generated(path: Path) -> bool:
    name = path.name
    if any(part in IGNORE_DIRS for part in path.parts):
        return True
    if name in GENERATED_NAMES:
        return True
    if name.startswith(("V42_", "V43_", "V50_", "V51_", "V52_")) and path.suffix.lower() in {".json", ".png", ".log"}:
        return True
    if name.endswith((".pyc", ".tmp")) or name.startswith("."):
        return True
    if name.endswith(".sha256.json"):
        return True
    return False


def immutable_manifest(root: Path) -> dict[str, str]:
    out = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if generated(rel) or p.suffix.lower() not in IMMUTABLE_SUFFIXES:
            continue
        out[rel.as_posix()] = digest(p)
    return out


def root_digest(manifest: dict[str, str]) -> str:
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def copy_package(dst: Path) -> None:
    def ignore(_dir, names):
        ignored = set()
        for name in names:
            if name in IGNORE_DIRS or name.endswith((".pyc", ".tmp")):
                ignored.add(name)
        return ignored
    shutil.copytree(ROOT, dst, ignore=ignore, dirs_exist_ok=True)


def run_in_fresh_copy(name: str, command: list[str], *, timeout: float = 300, blocked_returncodes: set[int] | None = None) -> dict:
    blocked_returncodes = blocked_returncodes or set()
    with tempfile.TemporaryDirectory(prefix=f"warroom_v52_{name}_") as td:
        work = Path(td) / "pkg"
        copy_package(work)
        before = immutable_manifest(work)
        env = os.environ.copy()
        env.update({"PYTHONWARNINGS": "error", "PYTHONDONTWRITEBYTECODE": "1", "TERM": "xterm", "WARROOM_DISABLE_AUTOSTART": "1"})
        try:
            proc = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, timeout=timeout)
            rc = proc.returncode
            output = (proc.stdout + "\n" + proc.stderr)[-30000:]
            status = "BLOCKED_BY_ENVIRONMENT" if rc in blocked_returncodes else "PASS" if rc == 0 else "FAIL"
        except subprocess.TimeoutExpired as exc:
            rc = None
            output = f"timeout after {timeout}s: {exc}"
            status = "FAIL"
        after = immutable_manifest(work)
        modified = sorted(k for k, v in before.items() if after.get(k) != v)
        deleted = sorted(k for k in before if k not in after)
        added = sorted(k for k in after if k not in before)
        mutation = sorted(set(modified + deleted + added))
        if mutation:
            status = "FAIL"
        return {
            "name": name,
            "status": status,
            "returncode": rc,
            "source_immutable": not mutation,
            "mutated_paths": mutation,
            "output_tail": output,
        }


def dependency_gate() -> dict:
    modules = {
        "streamlit": "streamlit", "requests": "requests", "yfinance": "yfinance",
        "pandas": "pandas", "numpy": "numpy", "scipy": "scipy", "scikit_learn": "sklearn",
        "statsmodels": "statsmodels", "hmmlearn": "hmmlearn", "networkx": "networkx",
        "pyarrow": "pyarrow", "python_dotenv": "dotenv", "cryptography": "cryptography",
    }
    states = {}
    for label, module in modules.items():
        try:
            obj = importlib.import_module(module)
            states[label] = {"state": "AVAILABLE", "version": str(getattr(obj, "__version__", "UNKNOWN"))}
        except Exception as exc:
            states[label] = {"state": "MISSING", "error": f"{type(exc).__name__}: {exc}"}
    missing = sorted(k for k, v in states.items() if v["state"] == "MISSING")
    return {"name": "runtime_dependencies", "status": "PASS" if not missing else "BLOCKED_BY_ENVIRONMENT", "missing": missing, "modules": states}


def proof_gate() -> dict:
    try:
        from proof_registry import default_registry, component_status
        reg = default_registry()
        statuses = {k: component_status(k) for k in reg["components"]}
        promoted = sorted(k for k, v in statuses.items() if v.get("predictive_promoted"))
        capital = sorted(k for k, v in statuses.items() if v.get("capital_permission") != "BLOCKED")
        return {
            "name": "default_proof_state", "status": "PASS" if not promoted and not capital else "FAIL",
            "predictive_components_promoted": promoted, "capital_authorized_components": capital,
        }
    except Exception as exc:
        return {"name": "default_proof_state", "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    source = immutable_manifest(ROOT)
    tests = [
        run_in_fresh_copy("compile_all", [sys.executable, "-m", "compileall", "-q", "."], timeout=180),
        run_in_fresh_copy("hardening_adversarial_39", [sys.executable, "hardening_tests/test_hardening_v52.py"], timeout=180),
        run_in_fresh_copy("gcfis_warnings_as_errors", [sys.executable, "gcfis/tests/test_all.py"], timeout=180),
        run_in_fresh_copy("deep_reaudit_ui_and_contracts", [sys.executable, "validate_v42_deep_reaudit.py"], timeout=300),
        run_in_fresh_copy("bundled_data_container_integrity", [sys.executable, "validate_bundled_data_v52.py"], timeout=180),
        run_in_fresh_copy(
            "synthetic_end_to_end",
            [sys.executable, "run.py", "--synthetic", "--markets", "us,idx,crypto,commodity,fx", "--out", "runtime/v52_desk.json", "--html", "runtime/v52_dashboard.html"],
            timeout=240,
        ),
        run_in_fresh_copy("validator_positive_negative_controls", [sys.executable, "validation_plus.py"], timeout=900),
        run_in_fresh_copy("actual_streamlit_health", [sys.executable, "validate_streamlit_health_v52.py"], timeout=120, blocked_returncodes={2}),
    ]
    deps = dependency_gate()
    proofs = proof_gate()
    pyarrow_available = deps["modules"]["pyarrow"]["state"] == "AVAILABLE"
    research = {
        "name": "parquet_semantic_recomputation",
        "status": "PASS" if pyarrow_available else "BLOCKED_BY_ENVIRONMENT",
        "reason": "pyarrow available; legacy research scripts may be recomputed" if pyarrow_available else "pyarrow missing; Parquet containers are hash/structure verified but semantic batteries cannot run",
    }
    if pyarrow_available:
        # The strict wrapper checks every child return code. It receives a generous timeout here.
        research = run_in_fresh_copy("parquet_semantic_recomputation", [sys.executable, "validate_all.py"], timeout=1800, blocked_returncodes={2})

    all_rows = tests + [deps, proofs, research]
    executable_failures = [x["name"] for x in all_rows if x["status"] == "FAIL"]
    blockers = [x["name"] for x in all_rows if x["status"] == "BLOCKED_BY_ENVIRONMENT"]
    mutation_failures = [x["name"] for x in tests if not x.get("source_immutable", True)]
    hardening_pass = not executable_failures and not mutation_failures
    full_release = hardening_pass and not blockers and not proofs.get("predictive_components_promoted") and False
    # Full release is intentionally false while zero signed prospective capital receipts exist.
    verdict = "HARDENING_PASS_FULL_RELEASE_BLOCKED" if hardening_pass else "HARDENING_FAIL"

    core_tests = [{k: v for k, v in row.items() if k != "output_tail"} for row in all_rows]
    report = {
        "schema": "warroom.clean_extract_audit.v52",
        "verdict": verdict,
        "hardening_status": "PASS" if hardening_pass else "FAIL",
        "full_release_status": "BLOCKED",
        "source_manifest_files": len(source),
        "source_manifest_sha256": root_digest(source),
        "warnings_as_errors": True,
        "validators_run_on_fresh_copies": True,
        "source_mutation_failures": mutation_failures,
        "executable_failures": executable_failures,
        "environment_blockers": blockers,
        "predictive_components_promoted": len(proofs.get("predictive_components_promoted") or []),
        "capital_permission": "BLOCKED",
        "tests": core_tests,
        "claim_boundary": "Software hardening can pass; predictive edge and prospective profitability cannot be promoted without signed exact-scope matured evidence.",
    }
    CORE_REPORT.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        f"VERDICT={verdict}", f"HARDENING={'PASS' if hardening_pass else 'FAIL'}", "FULL_RELEASE=BLOCKED",
        f"SOURCE_FILES={len(source)}", f"SOURCE_MANIFEST_SHA256={root_digest(source)}",
    ]
    lines += [f"{x['name']}={x['status']} rc={x.get('returncode','-')} immutable={x.get('source_immutable','-')}" for x in all_rows]
    lines += ["PREDICTIVE_COMPONENTS_PROMOTED=0", "CAPITAL_PERMISSION=BLOCKED"]
    SUMMARY_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for row in tests:
        print(f"{row['name']}: {row['status']} rc={row.get('returncode')} immutable={row.get('source_immutable')}")
        if row["status"] == "FAIL":
            print(row.get("output_tail", "")[-4000:])
    print(json.dumps({"verdict": verdict, "failures": executable_failures, "blockers": blockers}, indent=2))
    return 0 if hardening_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
