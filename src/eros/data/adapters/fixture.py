"""Frozen fixture adapter for deterministic tests and demo mode."""

from pathlib import Path

from eros.data.adapters.base import AdapterMetadata, SourceAdapter
from eros.data.identifiers import validate_storage_identifier


class FixtureAdapter(SourceAdapter):
    metadata = AdapterMetadata(
        source_id="FIXTURE",
        source_name="Frozen synthetic fixtures",
        license="Internal test fixture",
        availability="bundled",
        redistribution_allowed=True,
    )

    def __init__(self, root: Path) -> None:
        self.root = root

    def fetch(self, dataset_id: str) -> bytes:
        safe_id = validate_storage_identifier(dataset_id, "dataset_id")
        path = self.root / f"{safe_id}.csv"
        if not path.is_file():
            raise FileNotFoundError(dataset_id)
        return path.read_bytes()
