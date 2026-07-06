"""Dev-only tracker for in-flight and recently completed backend operations."""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

from engine.inspection.dev_guard import inspection_enabled

_MAX_RECENT = 80


@dataclass
class OperationRecord:
    id: str
    name: str
    category: str
    started_at: float
    started_at_epoch_ms: int
    metadata: dict[str, Any] = field(default_factory=dict)
    parent_id: str | None = None
    status: str = "running"
    finished_at: float | None = None
    duration_ms: float | None = None
    error: str | None = None

    def elapsed_ms(self, *, now: float | None = None) -> float:
        if self.duration_ms is not None:
            return self.duration_ms
        end = now if now is not None else time.perf_counter()
        return round((end - self.started_at) * 1000.0, 3)

    def to_running_dict(self, *, now: float | None = None) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "elapsed_ms": self.elapsed_ms(now=now),
            "started_at": self.started_at,
            "started_at_epoch_ms": self.started_at_epoch_ms,
            "parent_id": self.parent_id,
            "metadata": dict(self.metadata),
        }

    def to_recent_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "parent_id": self.parent_id,
            "error": self.error,
            "metadata": dict(self.metadata),
        }


class OperationTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running: dict[str, OperationRecord] = {}
        self._recent: deque[OperationRecord] = deque(maxlen=_MAX_RECENT)
        self._stack = threading.local()

    def _current_parent_id(self) -> str | None:
        stack = getattr(self._stack, "ids", None)
        if not stack:
            return None
        return stack[-1]

    def start(self, name: str, *, category: str = "general", **metadata: Any) -> str:
        op_id = uuid.uuid4().hex[:12]
        record = OperationRecord(
            id=op_id,
            name=name,
            category=category,
            started_at=time.perf_counter(),
            started_at_epoch_ms=int(time.time() * 1000),
            metadata=metadata,
            parent_id=self._current_parent_id(),
        )
        with self._lock:
            self._running[op_id] = record
        stack = getattr(self._stack, "ids", None)
        if stack is None:
            stack = []
            self._stack.ids = stack
        stack.append(op_id)
        return op_id

    def complete(self, op_id: str, *, status: str = "completed", error: str | None = None) -> None:
        finished_at = time.perf_counter()
        with self._lock:
            record = self._running.pop(op_id, None)
            if record is None:
                return
            record.status = status
            record.finished_at = finished_at
            record.duration_ms = round((finished_at - record.started_at) * 1000.0, 3)
            record.error = error
            self._recent.appendleft(record)
        stack = getattr(self._stack, "ids", None)
        if stack and stack[-1] == op_id:
            stack.pop()

    def snapshot(self) -> dict[str, Any]:
        now = time.perf_counter()
        with self._lock:
            running = [record.to_running_dict(now=now) for record in self._running.values()]
            recent = [record.to_recent_dict() for record in self._recent]
        running.sort(key=lambda item: item["started_at"])
        return {"running": running, "recent": recent}


_tracker = OperationTracker()


def operations_snapshot() -> dict[str, Any]:
    if not inspection_enabled():
        return {"running": [], "recent": []}
    return _tracker.snapshot()


@contextmanager
def track_operation(name: str, *, category: str = "general", **metadata: Any) -> Iterator[None]:
    if not inspection_enabled():
        yield
        return

    op_id = _tracker.start(name, category=category, **metadata)
    try:
        yield
    except Exception as exc:
        _tracker.complete(op_id, status="failed", error=str(exc))
        raise
    else:
        _tracker.complete(op_id, status="completed")
