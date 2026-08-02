from datetime import UTC, datetime
from pathlib import Path

from eros.audit.replay import DecisionSnapshot, SnapshotRepository


def test_snapshot_is_immutable_and_replayable(tmp_path: Path) -> None:
    repository = SnapshotRepository(tmp_path)
    snapshot = DecisionSnapshot(
        decision_id="DEC-1",
        created_at=datetime(2026, 8, 2, tzinfo=UTC),
        inputs={"thesis_id": "TH-1", "available_value": 2.7},
        outputs={"action": "WAIT"},
        versions={"world_model": "0.1.0", "portfolio_policy": "0.1.0"},
    )
    stored = repository.store(snapshot)
    assert repository.replay("DEC-1") == snapshot
    assert repository.verify("DEC-1", stored.checksum)
