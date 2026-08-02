"""Global ontology entity contracts."""

from enum import StrEnum

from pydantic import BaseModel, Field


class EntityType(StrEnum):
    ACTOR = "actor"
    GEOGRAPHY = "geography"
    MARKET = "market"
    ECONOMY = "economy"
    PHYSICAL_SYSTEM = "physical_system"
    CORPORATE_SYSTEM = "corporate_system"
    POLICY = "policy"
    EVENT = "event"
    THESIS = "thesis"
    MECHANISM = "mechanism"
    EVIDENCE = "evidence"
    EXPERIMENT = "experiment"
    OPPORTUNITY = "opportunity"
    DECISION = "decision"


class Entity(BaseModel):
    entity_id: str
    name: str
    entity_type: EntityType
    country_codes: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
