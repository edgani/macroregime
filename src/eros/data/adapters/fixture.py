"""Frozen fixture adapter for deterministic tests and demo mode."""
from pathlib import Path
from eros.data.adapters.base import AdapterMetadata, SourceAdapter


class FixtureAdapter(SourceAdapter):
    metadata = AdapterMetadata(source_id="FIXTURE", source_name="Frozen synthetic fixtures", license="Internal test fixture", availability="bundled", redistribution_allowed=True)

    def __init__(self, root: Path) -> None:
        self.root = root

    def fetch(self, dataset_id: str) -> bytes:
        path = self.root / f"{dataset_id}.csv"
        if not path.is_file():
            raise FileNotFoundError(dataset_id)
        return path.read_bytes()
