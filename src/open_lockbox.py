from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .common import OUTPUTS, PROCESSED, ROOT, package_version_hash, sha256_file, utc_now, write_json
from .run_tournament import run

SENTINEL = OUTPUTS / "lockbox" / "LOCKBOX_OPENED.json"
PANEL = PROCESSED / "us_monthly_research_panel.parquet"


def open_once() -> None:
    if SENTINEL.exists():
        previous = json.loads(SENTINEL.read_text(encoding="utf-8"))
        raise RuntimeError(f"Lockbox already opened at {previous['opened_at_utc']}; rerun prohibited.")
    if not PANEL.exists():
        raise FileNotFoundError(PANEL)
    sentinel = {
        "opened_at_utc": utc_now(),
        "contract_sha256": package_version_hash(),
        "panel_sha256": sha256_file(PANEL),
        "retuning_after_open": False,
        "status": "OPENED_ONCE",
        "claim_ceiling": "LOCKBOX_VALIDATED_CANDIDATE_MAX_NOT_PROVEN_WITHOUT_PROSPECTIVE",
    }
    write_json(SENTINEL, sentinel)
    # The historical lockbox is still known history; this controls computational reuse but does not erase LLM-memory contamination.
    run("lockbox")
    print(json.dumps(sentinel, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    open_once()


if __name__ == "__main__":
    main()
