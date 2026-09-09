from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import zipfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build_release import build_release

output = ROOT / ".tmp" / "release_packaging_test.zip"
digest = build_release(ROOT, output)
recorded = output.with_suffix(".zip.sha256.txt").read_text(encoding="ascii").split()[0]
actual = hashlib.sha256(output.read_bytes()).hexdigest()
assert digest == recorded == actual
with zipfile.ZipFile(output) as archive:
    names = archive.namelist()
    assert {"app.py", "tests/browser_smoke.py", "tools/build_release.py"} <= set(names)
    assert len(names) == len(set(names))
    assert not any("__pycache__" in name or name.endswith((".pyc", ".sqlite", ".db")) for name in names)
print("PASS: release packaging is self-consistent and excludes runtime state")
