"""Build the reviewable release ZIP and its matching SHA-256 sidecar."""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "release" / "market_opportunity_os_v3_3_codex_verified.zip"
TOP_LEVEL_SUFFIXES = {".py", ".md", ".txt", ".bat", ".sh"}
INCLUDED_DIRS = (".streamlit", "data", "tests", "tools")
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", "artifacts", "release", "validation_state"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".sqlite", ".db"}

def release_files(root: Path) -> list[Path]:
    files = [p for p in root.iterdir() if p.is_file() and p.suffix.lower() in TOP_LEVEL_SUFFIXES]
    for dirname in INCLUDED_DIRS:
        base = root / dirname
        if base.exists():
            files.extend(p for p in base.rglob("*") if p.is_file())
    return sorted((p for p in files if not (set(p.relative_to(root).parts) & EXCLUDED_PARTS)
                   and p.suffix.lower() not in EXCLUDED_SUFFIXES),
                  key=lambda p: p.relative_to(root).as_posix())

def build_release(root: Path, output: Path) -> str:
    root, output = root.resolve(), output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=output.name + ".", suffix=".tmp", dir=output.parent)
    os.close(fd)
    temporary = Path(name)
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for source in release_files(root):
                archive.write(source, source.relative_to(root).as_posix())
        digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
        temporary.replace(output)
        sidecar = output.with_suffix(output.suffix + ".sha256.txt")
        sidecar_tmp = sidecar.with_suffix(sidecar.suffix + ".tmp")
        sidecar_tmp.write_text(f"{digest}  {output.name}\n", encoding="ascii")
        sidecar_tmp.replace(sidecar)
        return digest
    finally:
        temporary.unlink(missing_ok=True)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    digest = build_release(args.root, args.output)
    print(f"RELEASE_BUILT {args.output.resolve()} SHA256={digest.upper()}")

if __name__ == "__main__":
    main()
