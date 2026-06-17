"""Execution event and audit data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventType(str, Enum):
    NODE_DISCOVERED = "node_discovered"
    DEPENDENCY_RESOLVED = "dependency_resolved"
    INPUT_REQUESTED = "input_requested"
    INPUT_RECEIVED = "input_received"
    CONDITION_CHECKED = "condition_checked"
    DECISION_CREATED = "decision_created"
    CALCULATION_STARTED = "calculation_started"
    CALCULATION_COMPLETED = "calculation_completed"
    WARNING_CREATED = "warning_created"
    REPORT_GENERATED = "report_generated"


@dataclass
class Event:
    event: EventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    node: str | None = None
    condition: str | None = None
    result: Any | None = None
    decision: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
