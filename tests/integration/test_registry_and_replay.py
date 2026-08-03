from datetime import UTC, datetime
from pathlib import Path

import pytest

from eros.audit.replay import DecisionSnapshot, SnapshotRepository
from eros.data.adapters.base import AdapterMetadata, SourceAdapter
from eros.data.adapters.fixture import FixtureAdapter
from eros.data.ingestion.pipeline import ingest_raw


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


class _StaticAdapter(SourceAdapter):
    metadata = AdapterMetadata(
        source_id="STATIC",
        source_name="Static test adapter",
        license="test-only",
        availability="bundled",
        redistribution_allowed=False,
    )

    def fetch(self, dataset_id: str) -> bytes:
        return f"payload:{dataset_id}".encode()


def test_snapshot_repository_rejects_path_traversal_identifier(tmp_path: Path) -> None:
    repository = SnapshotRepository(tmp_path / "snapshots")
    snapshot = DecisionSnapshot(
        decision_id="../outside",
        created_at=datetime(2026, 8, 3, tzinfo=UTC),
        inputs={},
        outputs={},
        versions={},
    )

    with pytest.raises(ValueError, match="decision_id"):
        repository.store(snapshot)

    assert not (tmp_path / "outside.json").exists()


def test_fixture_adapter_rejects_path_traversal_dataset_id(tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixtures"
    fixture_root.mkdir()
    (tmp_path / "secret.csv").write_text("private", encoding="utf-8")

    with pytest.raises(ValueError, match="dataset_id"):
        FixtureAdapter(fixture_root).fetch("../secret")


def test_raw_ingestion_rejects_path_traversal_dataset_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="dataset_id"):
        ingest_raw(_StaticAdapter(), "../escape", tmp_path / "raw")

    assert not (tmp_path / "escape").exists()
