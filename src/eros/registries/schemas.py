"""Registry schemas shared across storage and UI."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


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
