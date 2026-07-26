from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from .contracts import ComponentKey, EvidenceStatus
from .hashing import canonical_hash

@dataclass(frozen=True)
class ApplicabilityEntry:
    key: ComponentKey
    status: EvidenceStatus
    artifact_hash: str | None = None
    reason: str = "NOT_EVALUATED"

    def record(self) -> dict:
        d=asdict(self); d["status"]=self.status.value; return d

class ApplicabilityRegistry:
    def __init__(self, entries: list[ApplicabilityEntry]):
        records=[e.record() for e in entries]
        if len({canonical_hash(r["key"]) for r in records}) != len(records): raise ValueError("duplicate applicability scope")
        self.entries=tuple(entries); self.registry_hash=canonical_hash(records)
    def lookup(self,key:ComponentKey)->EvidenceStatus:
        for e in self.entries:
            if e.key==key: return e.status
        return EvidenceStatus.NOT_EVALUATED
    def dump(self,path:str|Path)->None:
        records=[e.record() for e in self.entries]
        Path(path).write_text(json.dumps({"entries":records,"registry_hash":canonical_hash(records)},indent=2,sort_keys=True),encoding="utf-8")
