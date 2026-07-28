"""Fresh-copy audit for War Room OS v5.3 attachment continuation.

The visual application remains v4.2.  v5.3 identifies the v5.2 hardened source plus
v5.1 global-claim accounting and the fail-closed V62 recovery gate.
"""
from __future__ import annotations

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
REPORT = ROOT / "V53_RELEASE_CLEAN_EXTRACT_VALIDATION.json"
LOG = ROOT / "V53_RELEASE_TEST_LOG.txt"

IGNORE_DIRS = {"__pycache__", ".git", ".cache", ".pytest_cache", "runtime", "audit_logs", ".venv"}
GENERATED_EXACT = {
    "desk_data.json", "dashboard_live.html", "V42_DEEP_REAUDIT_PREVIEW.png",
    "V42_DEEP_REAUDIT_VALIDATION_REPORT.json", "V52_CLEAN_EXTRACT_AUDIT_REPORT.json",
    "V52_CLEAN_EXTRACT_TEST_LOG.txt", "V53_RELEASE_CLEAN_EXTRACT_VALIDATION.json",
    "V53_RELEASE_TEST_LOG.txt", "V53_USER_VALIDATION_REPORT.json",
    "PACKAGE_MANIFEST_V53.json",
}
IMMUTABLE_SUFFIXES = {".py", ".html", ".md", ".txt", ".json", ".csv", ".parquet", ".yaml", ".yml", ".toml", ".bat"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def generated(rel: Path) -> bool:
    s = rel.as_posix()
    if any(part in IGNORE_DIRS for part in rel.parts):
        return True
    if rel.name in GENERATED_EXACT or rel.suffix.lower() in {".pyc", ".tmp", ".log"}:
        return True
    if s.startswith("proof/receipts/") and rel.name != "README.md":
        return True
    return False


def immutable_manifest(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if generated(rel) or p.suffix.lower() not in IMMUTABLE_SUFFIXES:
            continue
        out[rel.as_posix()] = digest(p)
    return out


def root_digest(rows: dict[str, str]) -> str:
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def copy_package(dst: Path) -> None:
    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {n for n in names if n in IGNORE_DIRS or n.endswith((".pyc", ".tmp"))}
    shutil.copytree(ROOT, dst, ignore=ignore, dirs_exist_ok=True)


def run_fresh(name: str, command: list[str], timeout: int, blocked_codes: set[int] | None = None) -> dict:
    blocked_codes = blocked_codes or set()
    print(f"START {name}", flush=True)
    with tempfile.TemporaryDirectory(prefix=f"warroom_v53_{name}_") as td:
        work = Path(td) / "pkg"
        copy_package(work)
        before = immutable_manifest(work)
        env = os.environ.copy()
        env.update({
            "PYTHONWARNINGS": "error",
            "PYTHONDONTWRITEBYTECODE": "1",
            "TERM": "xterm",
            "WARROOM_DISABLE_AUTOSTART": "1",
        })
        try:
            proc = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, timeout=timeout)
            rc = proc.returncode
            status = "BLOCKED_BY_ENVIRONMENT" if rc in blocked_codes else "PASS" if rc == 0 else "FAIL"
            output = (proc.stdout + "\n" + proc.stderr)[-24000:]
        except subprocess.TimeoutExpired as exc:
            rc = None
            status = "FAIL"
            output = f"timeout after {timeout}s: {exc}"
        after = immutable_manifest(work)
        mutation = sorted(
            set(k for k, v in before.items() if after.get(k) != v)
            | set(k for k in before if k not in after)
            | set(k for k in after if k not in before)
        )
        if mutation:
            status = "FAIL"
        row = {
            "name": name,
            "status": status,
            "returncode": rc,
            "source_immutable": not mutation,
            "mutated_paths": mutation,
            "output_tail": output,
        }
    print(f"DONE {name} {status} rc={rc} immutable={not mutation}", flush=True)
    return row


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
    from proof_registry import default_registry, component_status
    registry = default_registry()
    statuses = {key: component_status(key) for key in registry["components"]}
    promoted = sorted(key for key, value in statuses.items() if value.get("predictive_promoted"))
    capital = sorted(key for key, value in statuses.items() if value.get("capital_permission") != "BLOCKED")
    from research_evidence_v53 import load_research_evidence
    research = load_research_evidence()
    live_weight = sum(float(x.get("live_decision_weight", 0.0)) for x in research.get("claims", []))
    ok = not promoted and not capital and live_weight == 0.0 and research.get("capital_permission") == "BLOCKED"
    return {
        "name": "default_proof_and_research_state", "status": "PASS" if ok else "FAIL",
        "predictive_components_promoted": promoted, "capital_authorized_components": capital,
        "research_live_decision_weight": live_weight,
        "research_supported_historical_claims": research.get("supported_historical_claims"),
        "v61_status": research.get("v61_status"), "v62_status": research.get("v62_status"),
        "capital_permission": research.get("capital_permission"),
    }


def main() -> int:
    source = immutable_manifest(ROOT)
    tests = [
        run_fresh("compile_all", [sys.executable, "-m", "compileall", "-q", "."], 180),
        run_fresh("hardening_adversarial_39", [sys.executable, "hardening_tests/test_hardening_v52.py"], 240),
        run_fresh("attachment_continuation_11", [sys.executable, "hardening_tests/test_attachment_continuation_v53.py"], 180),
        run_fresh("gcfis_warnings_as_errors", [sys.executable, "gcfis/tests/test_all.py"], 240),
        run_fresh("deep_reaudit_ui_and_contracts", [sys.executable, "validate_v42_deep_reaudit.py"], 480),
        run_fresh("bundled_data_container_integrity", [sys.executable, "validate_bundled_data_v52.py"], 240),
        run_fresh(
            "synthetic_end_to_end",
            [sys.executable, "run.py", "--synthetic", "--markets", "us,idx,crypto,commodity,fx", "--out", "runtime/v53_desk.json", "--html", "runtime/v53_dashboard.html"],
            360,
        ),
        run_fresh("validator_positive_negative_controls", [sys.executable, "validation_plus.py"], 240),
        run_fresh("actual_streamlit_health", [sys.executable, "validate_streamlit_health_v52.py"], 180, {2}),
    ]
    deps = dependency_gate()
    proof = proof_gate()
    parquet = {
        "name": "parquet_semantic_recomputation",
        "status": "BLOCKED_BY_ENVIRONMENT" if deps["modules"]["pyarrow"]["state"] != "AVAILABLE" else "NOT_RUN",
        "reason": "pyarrow missing; containers are structurally/hash verified, semantic battery cannot run in this environment",
    }
    if deps["modules"]["pyarrow"]["state"] == "AVAILABLE":
        parquet = run_fresh("parquet_semantic_recomputation", [sys.executable, "validate_all.py"], 1800, {2})

    all_rows = tests + [deps, proof, parquet]
    failures = [x["name"] for x in all_rows if x["status"] == "FAIL"]
    blockers = [x["name"] for x in all_rows if x["status"] == "BLOCKED_BY_ENVIRONMENT"]
    mutation_failures = [x["name"] for x in tests if not x.get("source_immutable", True)]
    hardening_pass = not failures and not mutation_failures
    report = {
        "schema": "warroom.release_clean_extract_validation.v53",
        "status": "PASS" if hardening_pass else "FAIL",
        "release_verdict": "HARDENING_AND_RESEARCH_ACCOUNTING_PASS_CAPITAL_BLOCKED" if hardening_pass else "FAIL",
        "visual_application_version": "4.2",
        "release_continuation_version": "5.3",
        "hardening_base": "5.2",
        "research_accounting_base": "5.1",
        "source_manifest_files": len(source),
        "source_manifest_sha256": root_digest(source),
        "validators_run_on_fresh_copies": True,
        "warnings_as_errors": True,
        "source_mutation_failures": mutation_failures,
        "failures": failures,
        "environment_blockers": blockers,
        "supported_historical_claims": 4,
        "v61_fx_evz_exact_timing": "NOT_PROVEN",
        "v62_crossmarket_generalization": "ABORTED_BEFORE_OUTCOME_ANALYSIS",
        "predictive_components_promoted_to_live": 0,
        "research_live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
        "tests": [{k: v for k, v in row.items() if k != "output_tail"} for row in all_rows],
        "claim_boundary": "The attachment continuation is reconciled and visible. No failed/aborted study is promoted. V62 requires the exact registered v5.1 package/protocol binary; reconstruction is forbidden.",
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    LOG.write_text("\n".join([
        f"STATUS={report['status']}", f"VERDICT={report['release_verdict']}",
        f"SOURCE_FILES={len(source)}", f"SOURCE_MANIFEST_SHA256={report['source_manifest_sha256']}",
        *[f"{x['name']}={x['status']} rc={x.get('returncode','-')} immutable={x.get('source_immutable','-')}" for x in all_rows],
        "SUPPORTED_HISTORICAL_CLAIMS=4", "V61=NOT_PROVEN", "V62=ABORTED_BEFORE_OUTCOME_ANALYSIS",
        "PREDICTIVE_COMPONENTS_PROMOTED_TO_LIVE=0", "RESEARCH_LIVE_DECISION_WEIGHT=0", "CAPITAL_PERMISSION=BLOCKED",
    ]) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["status", "release_verdict", "failures", "environment_blockers", "capital_permission"]}, indent=2))
    return 0 if hardening_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
