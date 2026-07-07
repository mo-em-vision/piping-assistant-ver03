"""Structured chat response objects for the desktop API."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ChatResponse:
    status: str
    message: str | None = None
    question: str | None = None
    required_by: str | None = None
    task_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
