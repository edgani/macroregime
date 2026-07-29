"""Regression test for the 2026-07-29 re-audit root cause: the packet quote
gate must accept BOTH quote-producer vocabularies (v99 execution collector:
VALID_EXECUTION_REFERENCE; v101 current-context collector:
VALID_CURRENT_REFERENCE). Before the fix, all 258 live quotes were discarded
and packets silently fell back to 2018 research-panel prices."""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from decision_packet_v99 import _quote_status  # noqa: E402

NOW = dt.datetime.now(dt.timezone.utc)


def _record(validation: str, age_seconds: float = 300) -> dict:
    ts = (NOW - dt.timedelta(seconds=age_seconds)).isoformat()
    return {"price": 123.45, "validation": validation, "received_at": ts, "provider_timestamp": ts}


def test_v101_current_reference_is_reference_available_and_fresh():
    st = _quote_status(_record("VALID_CURRENT_REFERENCE"), "us")
    assert st["reference_available"] is True
    assert st["execution_fresh"] is True
    assert st["state"] == "EXECUTION_FRESH"


def test_v99_execution_reference_still_accepted():
    st = _quote_status(_record("VALID_EXECUTION_REFERENCE"), "us")
    assert st["reference_available"] is True
    assert st["execution_fresh"] is True


def test_stale_last_known_reference_usable_but_not_fresh():
    st = _quote_status(_record("STALE_LAST_KNOWN_REFERENCE", age_seconds=48 * 3600), "us")
    assert st["reference_available"] is True
    assert st["execution_fresh"] is False
    assert st["state"] == "CURRENT_REFERENCE_STALE"


def test_unknown_validation_rejected():
    st = _quote_status(_record("SOME_FUTURE_LABEL"), "us")
    assert st["reference_available"] is False
    assert st["execution_fresh"] is False


def test_missing_record_is_honest_no_quote():
    st = _quote_status(None, "us")
    assert st["state"] == "NO_CURRENT_QUOTE"
    assert st["reference_available"] is False


def test_freshness_respects_age_limits_for_us_equities():
    # provider age beyond the 36h limit -> usable reference but not execution-fresh
    st = _quote_status(_record("VALID_CURRENT_REFERENCE", age_seconds=40 * 3600), "us")
    assert st["reference_available"] is True
    assert st["execution_fresh"] is False
