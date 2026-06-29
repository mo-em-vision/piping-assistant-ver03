"""Node behavior registry — collapse scattered type/kind checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from engine.reference.node_types import (
    canonical_type,
    is_lookup_node,
    is_section_node,
    is_table_node,
    is_ui_parameter,
    node_kind,
)

BehaviorPredicate = Callable[[dict[str, Any], str | None], bool]


@dataclass(frozen=True)
class NodeBehavior:
    """Predicates for one canonical node type (optionally filtered by kind)."""

    node_type: str
    kind: str | None = None

    def matches(self, metadata: dict[str, Any], node_type: str | None = None) -> bool:
        raw = node_type if node_type is not None else str(metadata.get("type", ""))
        ctype = canonical_type(metadata, raw)
        if ctype != self.node_type:
            return False
        if self.kind is None:
            return True
        return node_kind(metadata) == self.kind


def is_executable_equation(metadata: dict[str, Any], node_type: str | None = None) -> bool:
    raw = node_type if node_type is not None else str(metadata.get("type", ""))
    return canonical_type(metadata, raw) == "equation"


def is_data_parameter(metadata: dict[str, Any], node_type: str | None = None) -> bool:
    raw = node_type if node_type is not None else str(metadata.get("type", ""))
    ctype = canonical_type(metadata, raw)
    if ctype != "parameter":
        return False
    return not is_ui_parameter(metadata, raw)


def is_reference_unit(metadata: dict[str, Any], node_type: str | None = None) -> bool:
    raw = node_type if node_type is not None else str(metadata.get("type", ""))
    return canonical_type(metadata, raw) == "unit"


def is_structural_text(metadata: dict[str, Any], node_type: str | None = None) -> bool:
    return is_section_node(metadata, node_type) or is_table_node(metadata, node_type)


__all__ = [
    "NodeBehavior",
    "is_data_parameter",
    "is_executable_equation",
    "is_lookup_node",
    "is_reference_unit",
    "is_section_node",
    "is_structural_text",
    "is_ui_parameter",
]
