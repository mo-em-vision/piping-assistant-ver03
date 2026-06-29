"""Workflow execution lifecycle events (Phase 8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class WorkflowLifecycleEventType(str, Enum):
    BEFORE_ENTER = "beforeEnter"
    ON_ENTER = "onEnter"
    ON_EXECUTE = "onExecute"
    ON_EXIT = "onExit"
    ON_ERROR = "onError"


@dataclass(frozen=True)
class WorkflowLifecycleEvent:
    """Graph traversal lifecycle event for one node step."""

    event: WorkflowLifecycleEventType
    node_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
