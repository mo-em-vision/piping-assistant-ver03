"""Graph dependency and versioning data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EdgeType(str, Enum):
    DEPENDENCY = "dependency"
    REFERENCE = "reference"
    CONDITIONAL = "conditional"
    INFORMATIONAL = "informational"
    VALIDATION = "validation"


@dataclass(frozen=True)
class GraphEdge:
    from_node: str
    to_node: str
    type: EdgeType
    reason: str | None = None


@dataclass
class GraphVersion:
    graph_id: str
    created: datetime
    standard_versions: dict[str, str]
    nodes: tuple[str, ...]
    edges: tuple[GraphEdge, ...] = ()
