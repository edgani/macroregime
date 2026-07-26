"""Load the tamper-evident live-feed snapshot built by build_feeds.py."""
from __future__ import annotations
from pathlib import Path

from safe_snapshot import read_safe_snapshot

SNAP = Path(__file__).resolve().parents[1] / "data" / "feeds_snapshot.json.gz"


def load_feeds():
    try:
        d = read_safe_snapshot(SNAP, expected_schema="warroom.feeds_snapshot.v1")
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def status(feeds):
    keys = ["fred", "fx_carry", "typef", "onchain", "cot", "gex", "finra"]
    return {k: (feeds.get(k) is not None) for k in keys}
