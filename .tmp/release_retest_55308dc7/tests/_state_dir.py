from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def isolated_state_dir():
    """Use the harness-provisioned state directory, with a normal local fallback.

    The aggregate runner already gives every test process a unique directory via
    OIE_STATE_DIR.  Re-nesting TemporaryDirectory under it is unnecessary and is
    rejected by some managed Windows sandboxes.
    """
    provisioned = os.environ.get("OIE_STATE_DIR")
    if provisioned:
        path = Path(provisioned)
        path.mkdir(parents=True, exist_ok=True)
        yield path
        return
    with tempfile.TemporaryDirectory() as directory:
        yield Path(directory)
