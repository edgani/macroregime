"""Legal-source adapter interface."""

from abc import ABC, abstractmethod

from pydantic import BaseModel


class AdapterMetadata(BaseModel):
    source_id: str
    source_name: str
    license: str
    availability: str
    redistribution_allowed: bool


class SourceAdapter(ABC):
    metadata: AdapterMetadata

    @abstractmethod
    def fetch(self, dataset_id: str) -> bytes:
        """Return source bytes without transforming them."""
