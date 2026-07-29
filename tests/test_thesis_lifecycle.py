"""Thesis lifecycle (lampu merah) + thesis frame tests (R11.2)."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from action_engine_v101 import (  # noqa: E402
    shadow_first_forecast_dates,
    thesis_frame,
    thesis_lifecycle,
)

TODAY = dt.date(2026, 7, 29)


def _lc(shadow="NOT_ELIGIBLE", proj=True, quote=True, tracked=None):
    return thesis_lifecycle(shadow_permission=shadow, projection_valid=proj,
                            quote_usable=quote, tracked_since=tracked, today=TODAY)


def test_not_ready_when_projection_invalid():
    r = _lc(proj=False)
    assert r["state"] == "NOT_READY"
    assert r["lamp"] == "RED"
    assert r["label_id"] == "BELUM SIAP"
    assert "VALUE_BRIDGE_PROJECTION_INVALID_OR_MISSING" in r["advance_blockers"]


def test_not_ready_when_quote_unusable():
    r = _lc(quote=False)
    assert r["state"] == "NOT_READY"
    assert "NO_USABLE_CURRENT_QUOTE" in r["advance_blockers"]


def test_preparing_when_valid_but_below_shadow_eligibility():
    r = _lc()
    assert r["state"] == "PREPARING"
    assert r["lamp"] == "YELLOW"
    assert r["label_id"] == "SIAP-SIAP"


def test_live_when_shadow_eligible_and_old_tracking():
    r = _lc(shadow="ELIGIBLE", tracked="2026-01-01")
    assert r["state"] == "LIVE"
    assert r["lamp"] == "GREEN"


def test_live_just_started_when_tracking_recent():
    r = _lc(shadow="ELIGIBLE", tracked="2026-07-25")
    assert r["state"] == "LIVE_JUST_STARTED"
    assert r["lamp"] == "BLUE"
    assert r["label_id"] == "BARU JALAN"
    assert r["tracked_since"] == "2026-07-25"


def test_live_when_eligible_but_no_ledger_history():
    r = _lc(shadow="ELIGIBLE", tracked=None)
    assert r["state"] == "LIVE"


def test_shadow_first_forecast_dates_reads_ledger(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    rows = [
        {"record_type": "FORECAST", "security_id": "MU", "recorded_at": "2026-07-29T01:55:16Z"},
        {"record_type": "ORDER_INTENT", "security_id": "MU", "recorded_at": "2026-07-29T01:55:16Z"},
        {"record_type": "FORECAST", "security_id": "MU", "recorded_at": "2026-07-30T01:55:16Z"},
        {"record_type": "FORECAST", "security_id": "COHR", "recorded_at": "2026-07-28T09:00:00Z"},
        {"garbage": True},
    ]
    ledger.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    first = shadow_first_forecast_dates(ledger)
    assert first == {"MU": "2026-07-29", "COHR": "2026-07-28"}


def test_shadow_first_forecast_dates_missing_file(tmp_path):
    assert shadow_first_forecast_dates(tmp_path / "nope.jsonl") == {}


def test_thesis_frame_uses_engine_numbers_only():
    proj = {"valid": True, "state": "CURRENT_PEER_VALUE_BRIDGE",
            "expected_target_price": 187.155, "target_low": 145.565, "target_high": 249.54}
    risk = {"stop": 78.19, "invalidation": "Re-evaluate when assumptions break."}
    f = thesis_frame(projection=proj, risk_plan=risk, horizon_days=180)
    assert f["projection_price"] == 187.155
    assert f["projection_range"] == [145.565, 249.54]
    assert f["invalidation_price"] == 78.19
    assert f["invalidation_price_basis"] == "HARD_LOSS_CONTROL_REFERENCE"
    assert f["horizon_days"] == 180


def test_thesis_frame_invalid_projection_is_honest():
    f = thesis_frame(projection={"valid": False}, risk_plan={}, horizon_days=None)
    assert f["projection_price"] is None
    assert f["projection_range"] is None
    assert f["invalidation_price"] is None
    assert f["invalidation_price_basis"] == "NOT_COMPUTED"
