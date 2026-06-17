"""AI agent context data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    intent: str | None = None
    available_nodes: list[str] = field(default_factory=list)
    missing_inputs: list[str] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
