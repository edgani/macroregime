"""Registry schemas shared across storage and UI."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class RegistryStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DATA_DEBT = "DATA_DEBT"
    DISABLED = "DISABLED"


class RecordMetadata(BaseModel):
    created_at: datetime
    effective_at: datetime
    available_at: datetime
    version: str
    source_id: str
    code_hash: str
    lineage_id: str

    @model_validator(mode="after")
    def validate_lineage(self) -> "RecordMetadata":
        timestamps = (self.created_at, self.effective_at, self.available_at)
        if any(value.tzinfo is None or value.utcoffset() is None for value in timestamps):
            raise ValueError("registry timestamps must be timezone-aware")
        if self.created_at > self.effective_at or self.effective_at > self.available_at:
            raise ValueError("registry chronology must be created <= effective <= available")
        if any(
            not value.strip()
            for value in (self.version, self.source_id, self.code_hash, self.lineage_id)
        ):
            raise ValueError("registry lineage fields must be nonblank")
        return self


class DatasetRecord(BaseModel):
    dataset_id: str
    name: str
    source: str
    license: str
    frequency: str
    coverage: str
    release_lag: str
    revision_policy: str
    vintage_available: bool
    reliability_grade: str
    missingness: str
    survivorship_risk: str
    proxy_for: list[str] = Field(default_factory=list)
    owner: str
    update_sla: str
    status: RegistryStatus
