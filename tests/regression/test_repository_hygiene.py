"""Repository hygiene contract for tracked production artifacts."""

import subprocess
from pathlib import Path


def test_repository_tracks_no_python_bytecode() -> None:
    root = Path(__file__).parents[2]
    result = subprocess.run(
        ["git", "ls-files", "*.pyc"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == ""
