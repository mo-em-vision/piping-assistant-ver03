"""Graph dependency and versioning data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class EdgeType(str, Enum):
    # Legacy depends_on types
    DEPENDENCY = "dependency"
    REFERENCE = "reference"
    CONDITIONAL = "conditional"
    INFORMATIONAL = "informational"
    VALIDATION = "validation"
    # Semantic micro-graph edges
    REQUIRES = "requires"
    CALCULATES = "calculates"
    DEFINES = "defines"
    EXPLAINS = "explains"
    OUTPUTS = "outputs"
    CONTAINS = "contains"
    ANCHORS_TO = "anchors_to"
    USES_TABLE = "uses_table"
    NEXT_STEP = "next_step"
    VALIDATES = "validates"
    LOCATED_IN = "located_in"
    DEFINED_BY = "defined_by"
    RELATED_TO = "related_to"
    UPDATES = "updates"
    SUPERSEDES = "supersedes"
    DERIVED_FROM = "derived_from"
    CONFLICTS_WITH = "conflicts_with"
    USES = "uses"
    ACCEPTS = "accepts"


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
