"""Typed, source-preserving records for both modalities."""
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class Observation:
    timestamp: float
    modality: str   # network | physical
    entity: str
    kind: str
    value: float
    source_id: str
    attrs: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Node:
    id: str
    modality: str
    entity: str
    description: str
    source_ids: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return asdict(self)
