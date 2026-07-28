"""Static import-reachability graph for the repository (Phase 1/2 audit).

Parses every tracked .py file with AST, resolves intra-repo imports
(root flat modules, warroom/, engines/, config/, src/ packages), then walks
from runtime entry points to compute the reachable set. Unreachable files
are dead-code CANDIDATES only - dynamic loading is checked separately.
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = REPO / "docs" / "audit"

ENTRY_POINTS = [
    "app.py",
    "run.py",
    "warroom_data_worker.py",
    "warroom_data_worker_v100.py",
    "warroom_data_worker_v101.py",
    "shadow_runner_v101.py",
    "validate_all.py",
    "validate.py",
]

RUNTIME_DIRS = ["", "warroom", "engines", "config", "src"]


def tracked_py() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


def module_name(rel: str) -> str:
    parts = rel[:-3].replace("\\", "/").split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    # src-layout packages import as their inner path
    if parts and parts[0] == "src":
        parts = parts[1:]
    return ".".join(parts)


def imports_of(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return set()
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                mods.add(node.module)
            elif node.level > 0:
                # relative import inside a package: resolve approximately
                for a in node.names:
                    if node.module:
                        mods.add(node.module)
                    mods.add(a.name)
    return mods


def main() -> int:
    files = tracked_py()
    mod_to_file: dict[str, str] = {}
    for rel in files:
        mod_to_file.setdefault(module_name(rel), rel)
    # bare-stem index for flat-root imports: top-level files win over nested ones
    for rel in sorted(files, key=lambda r: ("/" in r, r)):
        mod_to_file.setdefault(Path(rel).stem, rel)

    edges: dict[str, set[str]] = {}
    for rel in files:
        deps = set()
        for mod in imports_of(REPO / rel):
            cand = mod
            while cand:
                if cand in mod_to_file and mod_to_file[cand] != rel:
                    deps.add(mod_to_file[cand])
                    break
                cand = cand.rpartition(".")[0]
            else:
                # try package-qualified forms
                for prefix in ("warroom.", "engines.", "config."):
                    hit = mod_to_file.get(prefix + mod)
                    if hit and hit != rel:
                        deps.add(hit)
        edges[rel] = deps

    seeds = [e for e in ENTRY_POINTS if (REPO / e).exists()]
    # tests import the package under test; treat them as seeds too
    seeds += [f for f in files if f.startswith(("tests/", "hardening_tests/")) and f.endswith(".py")]
    seeds += [f for f in files if f.startswith("src/")]

    reachable: set[str] = set()
    stack = list(seeds)
    while stack:
        cur = stack.pop()
        if cur in reachable:
            continue
        reachable.add(cur)
        stack.extend(edges.get(cur, ()) - reachable)

    unreachable = sorted(set(files) - reachable)
    report = {
        "schema": "warroom.audit.import_graph.v1",
        "tracked_py_files": len(files),
        "seed_count": len(seeds),
        "reachable_count": len(reachable),
        "unreachable_count": len(unreachable),
        "unreachable_files": unreachable,
        "edges": {k: sorted(v) for k, v in sorted(edges.items())},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "import_graph.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("tracked_py_files", "seed_count", "reachable_count", "unreachable_count")}, indent=2))
    print("--- first 40 unreachable ---")
    for f in unreachable[:40]:
        print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
