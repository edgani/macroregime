"""Typed anti-contamination policy for quantitative research promotion."""

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from eros.data.identifiers import validate_storage_identifier

ControlStatus = Literal["ENFORCED", "PARTIAL", "NOT_IMPLEMENTED", "BLOCKED"]


class PolicySource(BaseModel):
    """Identity of the external failure-analysis source."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    url: HttpUrl
    accessed_at: date


class ContaminationControl(BaseModel):
    """One deterministic research-promotion control."""

    model_config = ConfigDict(extra="forbid")

    control_id: str
    failure_mode: str = Field(min_length=1)
    enforcement: str = Field(min_length=1)
    status: ControlStatus
    blocks_live_capital: Literal[True]

    @model_validator(mode="after")
    def validate_control(self) -> "ContaminationControl":
        """Reject unsafe IDs and whitespace-only descriptions."""

        validate_storage_identifier(self.control_id, "control_id")
        if not self.failure_mode.strip() or not self.enforcement.strip():
            raise ValueError("control descriptions must be nonblank")
        return self


class ContaminationPolicy(BaseModel):
    """Fail-closed policy derived from known LLM quant failure modes."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1)
    source: PolicySource
    principle: str = Field(min_length=1)
    controls: list[ContaminationControl] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_policy(self) -> "ContaminationPolicy":
        """Require unique controls and at least one live-capital blocker."""

        identifiers = [item.control_id for item in self.controls]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("contamination control IDs must be unique")
        if not self.principle.strip():
            raise ValueError("policy principle must be nonblank")
        return self

    @property
    def live_capital_ready(self) -> bool:
        """Allow promotion only when every blocking control is enforced."""

        return all(item.status == "ENFORCED" for item in self.controls)

    @property
    def unresolved_blockers(self) -> list[ContaminationControl]:
        """Return blocking controls that are not fully enforced."""

        return [
            item
            for item in self.controls
            if item.blocks_live_capital and item.status != "ENFORCED"
        ]


def load_contamination_policy(path: Path) -> ContaminationPolicy:
    """Parse a strict policy document from a repository-owned path."""

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError("contamination policy is not valid YAML") from exc
    if not isinstance(payload, dict):
        raise ValueError("contamination policy must be a mapping")
    return ContaminationPolicy.model_validate(payload)
