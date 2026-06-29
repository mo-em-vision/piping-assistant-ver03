"""Structured outputs produced by executable graph nodes (Phase 11)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NodeOutput:
    """One named value emitted by an executable node."""

    name: str
    label: str
    value: Any
    unit: str = "dimensionless"
    symbol: str | None = None
    param_node_id: str | None = None
