"""Workflow execution lifecycle event emission."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from engine.graph.doc_templates import build_doc_context
from engine.graph.documentation_resolver import resolve_node_documentation
from engine.graph.graph_store import GraphStore
from engine.graph.node_behaviors import is_executable_equation
from engine.reference.node_types import canonical_type
from models.input import EngineeringInput
from models.node_documentation import NodeDocumentation
from models.task import Task
from models.workflow_lifecycle import WorkflowLifecycleEvent, WorkflowLifecycleEventType


def is_executable_node(metadata: dict[str, Any], node_type: str | None = None) -> bool:
    """True when the node runs calculations or lookups (not reference-only)."""
    return is_executable_equation(metadata, node_type)


def _should_emit_lifecycle(metadata: dict[str, Any], node_type: str | None) -> bool:
    raw = node_type if node_type is not None else str(metadata.get("type", ""))
    ctype = canonical_type(metadata, raw)
    return ctype not in {"root", "definition"}


class WorkflowLifecycleEmitter:
    """Emit spec lifecycle events during plan execution."""

    def __init__(self, store: GraphStore) -> None:
        self._store = store
        self._events: list[WorkflowLifecycleEvent] = []

    def _resolve_doc(self, node_id: str, *, context: dict[str, Any]) -> NodeDocumentation:
        return resolve_node_documentation(self._store, node_id, context=context)

    def _append(
        self,
        event_type: WorkflowLifecycleEventType,
        node_id: str,
        *,
        message: str = "",
        payload: dict[str, Any] | None = None,
    ) -> WorkflowLifecycleEvent:
        event = WorkflowLifecycleEvent(
            event=event_type,
            node_id=node_id,
            message=message,
            payload=dict(payload or {}),
        )
        self._events.append(event)
        return event

    def emit_before_enter(self, node_id: str, *, context: dict[str, Any]) -> WorkflowLifecycleEvent:
        doc = self._resolve_doc(node_id, context=context)
        return self._append(
            WorkflowLifecycleEventType.BEFORE_ENTER,
            node_id,
            message=doc.before_enter,
        )

    def emit_on_enter(self, node_id: str, *, context: dict[str, Any]) -> WorkflowLifecycleEvent:
        doc = self._resolve_doc(node_id, context=context)
        message = doc.summary or doc.title
        return self._append(
            WorkflowLifecycleEventType.ON_ENTER,
            node_id,
            message=message,
        )

    def emit_on_execute(self, node_id: str, *, context: dict[str, Any]) -> WorkflowLifecycleEvent:
        doc = self._resolve_doc(node_id, context=context)
        message = doc.instructions or doc.description
        return self._append(
            WorkflowLifecycleEventType.ON_EXECUTE,
            node_id,
            message=message,
        )

    def emit_on_exit(self, node_id: str, *, context: dict[str, Any]) -> WorkflowLifecycleEvent:
        doc = self._resolve_doc(node_id, context=context)
        return self._append(
            WorkflowLifecycleEventType.ON_EXIT,
            node_id,
            message=doc.after_exit,
            payload={"after_exit": doc.after_exit} if doc.after_exit else {},
        )

    def emit_on_error(
        self,
        node_id: str,
        error_message: str,
        *,
        context: dict[str, Any],
    ) -> WorkflowLifecycleEvent:
        return self._append(
            WorkflowLifecycleEventType.ON_ERROR,
            node_id,
            message=error_message,
            payload={"errors": [error_message] if error_message else []},
        )

    @property
    def events(self) -> list[WorkflowLifecycleEvent]:
        return list(self._events)

    def to_dicts(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for event in self._events:
            data = asdict(event)
            data["event"] = event.event.value
            rows.append(data)
        return rows

    @staticmethod
    def build_context(
        task: Task,
        *,
        inputs: dict[str, EngineeringInput] | None = None,
    ) -> dict[str, Any]:
        return build_doc_context(task, inputs=inputs)


def parse_lifecycle_events(raw: Any) -> tuple[WorkflowLifecycleEvent, ...]:
    """Parse persisted lifecycle events from task outputs."""
    if not isinstance(raw, list):
        return ()

    events: list[WorkflowLifecycleEvent] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        event_name = item.get("event")
        node_id = item.get("node_id")
        if not event_name or not node_id:
            continue
        try:
            event_type = WorkflowLifecycleEventType(str(event_name))
        except ValueError:
            continue
        timestamp = item.get("timestamp")
        if isinstance(timestamp, str):
            from datetime import datetime

            parsed_ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            from datetime import datetime, timezone

            parsed_ts = datetime.now(timezone.utc)
        payload = item.get("payload")
        events.append(
            WorkflowLifecycleEvent(
                event=event_type,
                node_id=str(node_id),
                timestamp=parsed_ts,
                message=str(item.get("message", "")),
                payload=dict(payload) if isinstance(payload, dict) else {},
            )
        )
    return tuple(events)
