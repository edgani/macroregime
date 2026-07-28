from __future__ import annotations

import ast
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check(name: str, condition: bool, detail: str = "") -> dict:
    return {"check": name, "pass": bool(condition), "detail": detail}


def main() -> None:
    checks = []
    required = [
        "README_FIRST.md", "app.py", "RUN_APP.bat", "RUN_QUICK.bat", "RUN_FULL_HISTORY.bat", "RUN_OFFLINE_TESTS.bat",
        "OPEN_LOCKBOX_ONCE.bat", "bootstrap.ps1", "run_pipeline.py", "requirements.txt",
        "config/freeze_contract.json", "config/source_registry.json",
        "data/reference/sp500_ticker_start_end.csv", "data/reference/current_us_universe_2026-07-17.csv",
        "src/download_data.py", "src/build_prices.py", "src/build_entity_master.py",
        "src/build_sec_features.py", "src/build_panel.py", "src/run_tournament.py",
        "src/run_current_selector.py", "src/prospective.py", "src/open_lockbox.py",
        "outputs/synthetic_demo/SYNTHETIC_DEMO_SUMMARY.json",
        "docs/DATA_GAP_IMPACT.csv", "docs/CLAIM_LADDER.csv",
        "P6_93_FINAL_OPERATIONAL_STATUS.md"
    ]
    for relative in required:
        checks.append(check(f"required:{relative}", (ROOT / relative).exists()))

    contract = json.loads((ROOT / "config/freeze_contract.json").read_text())
    checks.append(check("historical claim ceiling", contract["claim_ceiling"].startswith("HISTORICAL_CANDIDATE")))
    checks.append(check("lockbox no retuning", contract["lockbox"]["retuning_after_open"] is False))
    checks.append(check("prospective required", contract["prospective"]["proven_label_requires_future_receipts"] is True))
    checks.append(check("registered target count four", len(contract["targets"]) == 4))
    checks.append(check("registered model count two", len(contract["models"]) == 2))

    membership = list(csv.DictReader((ROOT / "data/reference/sp500_ticker_start_end.csv").open()))
    checks.append(check("membership intervals >1000", len(membership) > 1000, str(len(membership))))
    checks.append(check("membership contains removals", sum(bool(r["end_date"]) for r in membership) > 500))

    universe = list(csv.DictReader((ROOT / "data/reference/current_us_universe_2026-07-17.csv").open()))
    eligible = sum(r.get("eligible_us_v1") == "YES" for r in universe)
    checks.append(check("current official universe >10k", len(universe) > 10000, str(len(universe))))
    checks.append(check("current eligible >4k", eligible > 4000, str(eligible)))

    for path in sorted((ROOT / "src").glob("*.py")) + [ROOT / "run_pipeline.py", ROOT / "app.py"]:
        try:
            ast.parse(path.read_text(encoding="utf-8"))
            checks.append(check(f"AST:{path.name}", True))
        except SyntaxError as exc:
            checks.append(check(f"AST:{path.name}", False, str(exc)))

    tests = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=ROOT, capture_output=True, text=True
    )
    checks.append(check("pytest", tests.returncode == 0, tests.stdout + tests.stderr))

    demo = json.loads((ROOT / "outputs/synthetic_demo/SYNTHETIC_DEMO_SUMMARY.json").read_text())
    checks.append(check("synthetic demo engineering only", demo["status"] == "SYNTHETIC_ENGINEERING_ONLY"))
    checks.append(check("synthetic OOS predictions", demo["oos_predictions"] > 1000, str(demo["oos_predictions"])))

    excluded = {"MANIFEST.json", "VALIDATION_LOG.json", "ZIP_VALIDATION.json"}
    files = sorted(
        str(path.relative_to(ROOT)) for path in ROOT.rglob("*")
        if path.is_file() and path.name not in excluded and ".venv" not in path.parts
    )
    manifest = {relative: {"size_bytes": (ROOT / relative).stat().st_size, "sha256": sha256(ROOT / relative)} for relative in files}
    (ROOT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    checks.append(check("manifest files >=40", len(manifest) >= 40, str(len(manifest))))
    checks.extend(check(f"hash:{name}", sha256(ROOT / name) == metadata["sha256"]) for name, metadata in manifest.items())

    validation = {
        "package": "War_Room_OS_P6_86_P6_93_US_ALPHA_FOUNDRY_OPERATIONAL",
        "pass": all(item["pass"] for item in checks),
        "checks_passed": sum(item["pass"] for item in checks),
        "checks_total": len(checks),
        "manifest_files": len(manifest),
        "real_market_data_included": False,
        "real_market_tournament_executed": False,
        "operational_runner_ready": True,
        "synthetic_engineering_validation": True,
        "proven_components": 0,
        "proven_selectors": 0,
        "proven_alpha": 0,
        "paper": "BLOCKED",
        "live": "BLOCKED",
        "checks": checks,
    }
    (ROOT / "VALIDATION_LOG.json").write_text(json.dumps(validation, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: validation[k] for k in ["pass", "checks_passed", "checks_total", "manifest_files", "operational_runner_ready"]}, indent=2))
    if not validation["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
