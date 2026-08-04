"""Deterministic decision-surface rules for the rebuilt Command Center."""

from __future__ import annotations

from packet_factory import meters_snapshot

from eros.app.command_center import _action_rows, _headline_action, _scenario_rows


def test_headline_trims_extreme_gold_when_gate_is_open() -> None:
    headline, reason = _headline_action(meters_snapshot(), qualified_count=0)

    assert "TRIM EMAS" in headline
    assert "0.96" in reason
    assert "CONVICTION PLAY" in headline


def test_headline_fails_closed_when_gate_is_red() -> None:
    meters = meters_snapshot(exposure=0.0)
    headline, reason = _headline_action(meters, qualified_count=0)

    assert "GATE MERAH" in headline
    assert "0%" in headline
    assert "R2" in reason


def test_headline_surfaces_fear_entry_when_active() -> None:
    meters = meters_snapshot(fear_entry=True)
    headline, _ = _headline_action(meters, qualified_count=0)

    assert "FEAR-ENTRY AKTIF" in headline


def test_headline_fails_closed_when_meter_engine_is_down() -> None:
    headline, reason = _headline_action(None, qualified_count=0)

    assert "TIDAK TERSEDIA" in headline
    assert "fail-closed" in reason


def test_scenario_rows_cover_three_horizons_and_barbell_year() -> None:
    rows = _scenario_rows(meters_snapshot())

    assert [row["Horizon"] for row in rows] == ["1 MINGGU", "1 BULAN", "1 TAHUN+"]
    assert "BARBELL" in rows[2]["Sikap"]
    assert "dry powder" in rows[2]["Sikap"]


def test_scenario_rows_fail_closed_without_meters() -> None:
    rows = _scenario_rows(None)

    assert all(row["Sikap"] == "TAHAN" for row in rows)
    assert all("fail-closed" in row["Dasar"] for row in rows)


def test_action_rows_follow_machine_state_and_execution_gate() -> None:
    rows = _action_rows(meters_snapshot(), qualified_count=0, execution_enabled=False)
    by_asset = {row["Aset"]: row for row in rows}

    assert by_asset["Emas (GLD)"]["Aksi"] == "TRIM"
    assert by_asset["Ekuitas (SPX)"]["Aksi"] == "HOLD"
    assert by_asset["Saham individual"]["Aksi"] == "WAIT"
    assert by_asset["Eksekusi"]["Aksi"] == "VETO"


def test_action_rows_veto_everything_when_meter_engine_is_down() -> None:
    rows = _action_rows(None, qualified_count=0, execution_enabled=True)

    assert rows == [
        {
            "Aset": "SEMUA",
            "Aksi": "VETO",
            "Alasan": "Meter engine NO_DATA — tidak ada aksi baru tanpa data.",
            "Bukti": "fail-closed",
        }
    ]


def test_headline_never_crashes_on_missing_gate_values() -> None:
    """Reviewer finding: None BCM/FRAGILITY must fail closed, not TypeError."""

    from eros.meters.engines import MeterReading
    from eros.meters.snapshot import MetersSnapshot

    base = meters_snapshot().model_dump()
    base["bcm"] = MeterReading(
        meter_id="BCM", label="BCM", value=None, status="NO_DATA", components={},
        missing=["FEDFUNDS"], as_of="NO_DATA", evidence="PROVEN_SCOPE_LIMITED", note="",
    )
    base["exposure"] = None
    meters = MetersSnapshot(**base)

    headline, reason = _headline_action(meters, qualified_count=0)
    assert "GATE TIDAK LENGKAP" in headline
    assert "fail-closed" in reason

    rows = _scenario_rows(meters)
    assert all(row["Sikap"] == "TAHAN" for row in rows)

    actions = _action_rows(meters, qualified_count=0, execution_enabled=True)
    by_asset = {row["Aset"]: row for row in actions}
    assert by_asset["Ekuitas (SPX)"]["Aksi"] == "VETO"


def test_headline_survives_missing_gold_with_open_gate() -> None:
    """Reviewer re-check: gold NO_DATA with gate open must not TypeError."""

    from eros.meters.engines import MeterReading
    from eros.meters.snapshot import MetersSnapshot

    base = meters_snapshot().model_dump()
    base["gold"] = MeterReading(
        meter_id="GOLD", label="Gold", value=None, status="NO_DATA", components={},
        missing=["DFII10"], as_of="NO_DATA", evidence="PROVEN", note="",
    )
    meters = MetersSnapshot(**base)

    _headline, reason = _headline_action(meters, qualified_count=0)
    assert "GOLD NO_DATA" in reason
