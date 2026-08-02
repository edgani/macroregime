"""Immutable decision snapshot storage and replay."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel


class DecisionSnapshot(BaseModel):
    decision_id: str
    created_at: datetime
    inputs: dict[str, object]
    outputs: dict[str, object]
    versions: dict[str, str]


class StoredSnapshot(BaseModel):
    path: Path
    checksum: str


class SnapshotRepository:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, decision_id: str) -> Path:
        return self.root / f"{decision_id}.json"

    def store(self, snapshot: DecisionSnapshot) -> StoredSnapshot:
        path = self._path(snapshot.decision_id)
        if path.exists():
            raise FileExistsError(f"immutable snapshot already exists: {snapshot.decision_id}")
        payload = snapshot.model_dump_json(indent=2)
        path.write_text(payload, encoding="utf-8")
        return StoredSnapshot(path=path, checksum=hashlib.sha256(payload.encode()).hexdigest())

    def replay(self, decision_id: str) -> DecisionSnapshot:
        return DecisionSnapshot.model_validate_json(self._path(decision_id).read_text(encoding="utf-8"))

    def verify(self, decision_id: str, checksum: str) -> bool:
        payload = self._path(decision_id).read_text(encoding="utf-8")
        return hashlib.sha256(payload.encode()).hexdigest() == checksum
