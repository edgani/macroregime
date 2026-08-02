"""YAML-backed extensible registries."""
from pathlib import Path
from typing import TypeVar
import yaml
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class YamlRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self, model: type[T]) -> list[T]:
        payload = yaml.safe_load(self.path.read_text(encoding="utf-8")) or []
        if not isinstance(payload, list):
            raise ValueError(f"registry root must be a list: {self.path}")
        return [model.model_validate(item) for item in payload]
