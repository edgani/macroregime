"""Immutable RAW-to-decision pipeline contracts."""

import hashlib
from pathlib import Path

from pydantic import BaseModel

from eros.data.adapters.base import SourceAdapter
from eros.data.identifiers import validate_storage_identifier


class RawReceipt(BaseModel):
    dataset_id: str
    path: Path
    sha256: str
    source_id: str


def ingest_raw(adapter: SourceAdapter, dataset_id: str, raw_root: Path) -> RawReceipt:
    safe_id = validate_storage_identifier(dataset_id, "dataset_id")
    payload = adapter.fetch(safe_id)
    checksum = hashlib.sha256(payload).hexdigest()
    destination = raw_root / safe_id / f"{checksum}.bin"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        destination.write_bytes(payload)
    return RawReceipt(
        dataset_id=safe_id,
        path=destination,
        sha256=checksum,
        source_id=adapter.metadata.source_id,
    )
