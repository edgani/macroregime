"""Build the Phase 0 baseline inventory for the War Room final audit.

Stdlib only. Writes machine-readable and human-readable baseline artifacts
into docs/audit/baseline/. Safe to re-run; outputs are deterministic given
the same git state.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = REPO / "docs" / "audit" / "baseline"
OUT.mkdir(parents=True, exist_ok=True)

KEY_FILES = [
    "app.py", "run.py", "runtime_store.py", "data_layer.py",
    "data_layer_v100.py", "data_layer_v101.py",
    "warroom_data_worker.py", "warroom_data_worker_v100.py", "warroom_data_worker_v101.py",
    "decision_packet_v98.py", "decision_packet_v99.py", "decision_packet_v100.py", "decision_packet_v101.py",
    "current_context_v100.py", "current_context_v101.py",
    "carry_trade_engine_v101.py", "action_engine_v101.py", "anti_overfit_gate_v96.py",
    "component_registry_v99.json", "pyproject.toml", "requirements.txt",
    "requirements-dev.txt", "requirements-streaming.txt", "Dockerfile", "docker-compose.yml",
]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(path: str) -> str:
    name = os.path.basename(path)
    lower = name.lower()
    if lower.endswith((".png", ".jpg", ".jpeg", ".gif")):
        return "image_artifact"
    if lower.startswith(("package_manifest", "v")) and lower.endswith((".json", ".md", ".txt", ".csv")):
        return "versioned_report_artifact"
    if lower.endswith(".bak"):
        return "backup_file"
    if lower.endswith((".bat", ".ps1")):
        return "shell_launcher"
    if lower.endswith(".py"):
        return "python_source"
    if lower.endswith((".html", ".js", ".css")):
        return "web_asset"
    if lower.endswith((".json", ".csv", ".parquet", ".db", ".sqlite")):
        return "data_or_config"
    if lower.endswith(".md"):
        return "documentation"
    return "other"


def main() -> int:
    files = git("ls-files").splitlines()
    rows = []
    for f in files:
        p = REPO / f
        size = p.stat().st_size if p.exists() else -1
        rows.append({"path": f, "size_bytes": size, "category": classify(f)})

    (OUT / "file_tree.txt").write_text(
        "\n".join(f"{r['size_bytes']:>12}  {r['path']}" for r in rows) + "\n", encoding="utf-8"
    )

    cat = Counter(r["category"] for r in rows)
    cat_bytes: Counter[str] = Counter()
    for r in rows:
        cat_bytes[r["category"]] += max(r["size_bytes"], 0)

    hashes = {}
    for rel in KEY_FILES:
        p = REPO / rel
        if p.exists():
            hashes[rel] = {"sha256": sha256(p), "size_bytes": p.stat().st_size}

    top_large = sorted(rows, key=lambda r: -r["size_bytes"])[:40]

    manifest = {
        "schema": "warroom.audit.baseline.v1",
        "branch": git("branch", "--show-current").strip(),
        "head_commit": git("rev-parse", "HEAD").strip(),
        "main_commit_at_branch_point": git("rev-parse", "main").strip(),
        "remotes": [line for line in git("remote", "-v").splitlines()],
        "tracked_file_count": len(rows),
        "tracked_bytes_total": sum(max(r["size_bytes"], 0) for r in rows),
        "category_counts": dict(cat),
        "category_bytes": dict(cat_bytes),
        "key_file_hashes": hashes,
        "largest_tracked_files": top_large,
        "untracked_present": bool(git("status", "--porcelain").strip()),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    deps = {
        "python_files": cat.get("python_source", 0),
        "requirements_txt": (REPO / "requirements.txt").read_text(encoding="utf-8"),
        "requirements_dev_txt": (REPO / "requirements-dev.txt").read_text(encoding="utf-8")
        if (REPO / "requirements-dev.txt").exists() else None,
        "requirements_streaming_txt": (REPO / "requirements-streaming.txt").read_text(encoding="utf-8")
        if (REPO / "requirements-streaming.txt").exists() else None,
        "pyproject_dependencies": (REPO / "pyproject.toml").read_text(encoding="utf-8"),
    }
    (OUT / "dependencies.json").write_text(json.dumps(deps, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "tracked_files": len(rows),
        "tracked_mb": round(manifest["tracked_bytes_total"] / 1e6, 1),
        "categories": dict(cat),
        "key_hashes": len(hashes),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
