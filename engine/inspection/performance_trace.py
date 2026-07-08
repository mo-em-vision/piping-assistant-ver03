"""Dev-only performance tracing grouped by trace_id per user interaction."""

from __future__ import annotations

import re
import threading
import time
import uuid
from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any, Iterator, Mapping

from engine.inspection.dev_guard import inspection_enabled

MAX_RECENT_TRACES = 40
MAX_SPANS_PER_TRACE = 80
MAX_NOTE_LEN = 120

VALID_OP_TYPES = frozenset(
    {
        "api",
        "planner",
        "graph",
        "state",
        "validation",
        "equation",
        "lookup",
        "serializer",
        "llm",
        "frontend",
        "database",
        "execution",
    }
)

_TRACE_ID_HEADER = "X-Performance-Trace-Id"
_TRACE_ID_PATTERN = re.compile(r"^[0-9a-f]{16}$")

_current_trace: ContextVar["_ActiveTrace | None"] = ContextVar("_perf_current_trace", default=None)
_span_stack: ContextVar[list[str]] = ContextVar("_perf_span_stack", default=[])
_context_tokens: ContextVar[list[tuple[ContextVar[Any], Token[Any]]]] = ContextVar(
    "_perf_context_tokens",
    default=[],
)


@dataclass
class SpanRecord:
    span_id: str
    parent_span_id: str | None
    name: str
    op_type: str
    started_at: float
    duration_ms: float
    status: str
    llm: bool
    notes: str | None


@dataclass
class _OpenSpan:
    span_id: str
    parent_span_id: str | None
    name: str
    op_type: str
    started_at: float
    llm: bool
    notes: str | None


@dataclass
class _ActiveTrace:
    trace_id: str
    trigger: str
    task_id: str | None
    started_at: float
    spans: list[SpanRecord] = field(default_factory=list)
    open_spans: list[_OpenSpan] = field(default_factory=list)
    llm_call_occurred: bool = False
    spans_omitted: int = 0


@dataclass
class _FinishedTrace:
    trace_id: str
    trigger: str
    task_id: str | None
    total_duration_ms: float
    llm_call_occurred: bool
    status: str
    error: str | None
    spans: list[SpanRecord]
    spans_omitted: int = 0


class _TraceStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._recent: deque[_FinishedTrace] = deque(maxlen=MAX_RECENT_TRACES)

    def append(self, trace: _FinishedTrace) -> None:
        with self._lock:
            self._recent.appendleft(trace)

    def snapshot(self, *, limit: int = MAX_RECENT_TRACES) -> list[dict[str, Any]]:
        capped = max(1, min(int(limit), MAX_RECENT_TRACES))
        with self._lock:
            traces = list(self._recent)[:capped]
        return [_finished_trace_to_dict(item) for item in traces]


_store = _TraceStore()


def trace_header_name() -> str:
    return _TRACE_ID_HEADER


def normalize_trace_id(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip().lower()
    if _TRACE_ID_PATTERN.fullmatch(cleaned):
        return cleaned
    return None


def new_trace_id() -> str:
    return uuid.uuid4().hex[:16]


def resolve_trace_id(header_value: str | None) -> str:
    return normalize_trace_id(header_value) or new_trace_id()


def trigger_for_request(*, method: str, path: str) -> str:
    normalized = path.rstrip("/") or "/"
    if method.upper() == "GET":
        if normalized.endswith("/inspection"):
            return "inspection_poll"
    return f"{method.upper()} {normalized}"


def extract_task_id_from_path(path: str) -> str | None:
    prefix = "/api/v1/tasks/"
    normalized = path.rstrip("/") or "/"
    if not normalized.startswith(prefix):
        return None
    remainder = normalized.removeprefix(prefix)
    if not remainder:
        return None
    task_id = remainder.split("/", 1)[0].strip()
    return task_id or None


def _sanitize_notes(notes: str | None) -> str | None:
    if notes is None:
        return None
    text = " ".join(str(notes).split())
    if not text:
        return None
    if len(text) > MAX_NOTE_LEN:
        return text[: MAX_NOTE_LEN - 3] + "..."
    return text


def _normalize_op_type(op_type: str) -> str:
    cleaned = str(op_type or "api").strip().lower()
    if cleaned not in VALID_OP_TYPES:
        return "api"
    return cleaned


def current_trace_id() -> str | None:
    active = _current_trace.get()
    if active is None:
        return None
    return active.trace_id


def begin_interaction_trace(
    trigger: str,
    *,
    trace_id: str | None = None,
    task_id: str | None = None,
) -> str:
    if not inspection_enabled():
        return trace_id or new_trace_id()

    resolved_id = normalize_trace_id(trace_id) or new_trace_id()
    active = _ActiveTrace(
        trace_id=resolved_id,
        trigger=str(trigger),
        task_id=task_id,
        started_at=time.perf_counter(),
    )
    token = _current_trace.set(active)
    stack_token = _span_stack.set([])
    tokens = list(_context_tokens.get())
    tokens.extend([(_current_trace, token), (_span_stack, stack_token)])
    _context_tokens.set(tokens)
    return resolved_id


def finish_interaction_trace(*, status: str = "success", error: str | None = None) -> None:
    active = _current_trace.get()
    if active is None or not inspection_enabled():
        return

    if active.spans_omitted > 0:
        active.spans.append(
            SpanRecord(
                span_id=uuid.uuid4().hex[:12],
                parent_span_id=None,
                name="spans_truncated",
                op_type="api",
                started_at=time.perf_counter(),
                duration_ms=0.0,
                status="success",
                llm=False,
                notes=_sanitize_notes(f"omitted={active.spans_omitted}"),
            )
        )

    finished_at = time.perf_counter()
    finished = _FinishedTrace(
        trace_id=active.trace_id,
        trigger=active.trigger,
        task_id=active.task_id,
        total_duration_ms=round((finished_at - active.started_at) * 1000.0, 3),
        llm_call_occurred=active.llm_call_occurred,
        status=status,
        error=error,
        spans=list(active.spans),
        spans_omitted=active.spans_omitted,
    )
    _store.append(finished)


def reset_trace_context() -> None:
    tokens = list(_context_tokens.get())
    for var, token in reversed(tokens):
        try:
            var.reset(token)
        except (LookupError, ValueError):
            pass
    _context_tokens.set([])
    _current_trace.set(None)
    _span_stack.set([])


@contextmanager
def request_trace_context(
    *,
    method: str,
    path: str,
    headers: Mapping[str, str] | None = None,
) -> Iterator[str | None]:
    if not inspection_enabled():
        yield None
        return

    header_map = headers or {}
    header_value = None
    for key, value in header_map.items():
        if key.lower() == _TRACE_ID_HEADER.lower():
            header_value = value
            break

    trace_id = begin_interaction_trace(
        trigger_for_request(method=method, path=path),
        trace_id=resolve_trace_id(header_value),
        task_id=extract_task_id_from_path(path),
    )
    status = "success"
    error: str | None = None
    try:
        yield trace_id
    except Exception as exc:
        status = "error"
        error = str(exc)
        raise
    finally:
        try:
            finish_interaction_trace(status=status, error=error)
        finally:
            reset_trace_context()


def _current_parent_span_id() -> str | None:
    stack = _span_stack.get()
    if not stack:
        return None
    return stack[-1]


def _add_completed_span(
    active: _ActiveTrace,
    *,
    name: str,
    op_type: str,
    duration_ms: float,
    status: str,
    llm: bool,
    notes: str | None,
    parent_span_id: str | None,
) -> None:
    if len(active.spans) >= MAX_SPANS_PER_TRACE:
        active.spans_omitted += 1
        return
    if llm:
        active.llm_call_occurred = True
    active.spans.append(
        SpanRecord(
            span_id=uuid.uuid4().hex[:12],
            parent_span_id=parent_span_id,
            name=name,
            op_type=_normalize_op_type(op_type),
            started_at=time.perf_counter(),
            duration_ms=round(max(0.0, duration_ms), 3),
            status=status,
            llm=llm,
            notes=_sanitize_notes(notes),
        )
    )


def add_summary_span(
    name: str,
    op_type: str,
    duration_ms: float,
    *,
    status: str = "success",
    llm: bool = False,
    notes: str | None = None,
) -> None:
    active = _current_trace.get()
    if active is None or not inspection_enabled():
        return
    _add_completed_span(
        active,
        name=name,
        op_type=op_type,
        duration_ms=duration_ms,
        status=status,
        llm=llm,
        notes=notes,
        parent_span_id=_current_parent_span_id(),
    )


@contextmanager
def perf_span(
    name: str,
    op_type: str,
    *,
    status_on_exit: str = "success",
    notes: str | None = None,
    llm: bool = False,
    skipped: bool = False,
) -> Iterator[None]:
    active = _current_trace.get()
    if active is None or not inspection_enabled():
        yield
        return

    if len(active.spans) >= MAX_SPANS_PER_TRACE:
        active.spans_omitted += 1
        yield
        return

    span_id = uuid.uuid4().hex[:12]
    parent_id = _current_parent_span_id()
    started_at = time.perf_counter()
    stack = list(_span_stack.get())
    stack.append(span_id)
    stack_token = _span_stack.set(stack)
    tokens = list(_context_tokens.get())
    tokens.append((_span_stack, stack_token))
    _context_tokens.set(tokens)
    active.open_spans.append(
        _OpenSpan(
            span_id=span_id,
            parent_span_id=parent_id,
            name=name,
            op_type=_normalize_op_type(op_type),
            started_at=started_at,
            llm=llm,
            notes=_sanitize_notes(notes),
        )
    )
    if llm:
        active.llm_call_occurred = True

    final_status = "skipped" if skipped else status_on_exit
    error: str | None = None
    try:
        yield
    except Exception as exc:
        final_status = "error"
        error = str(exc)
        raise
    finally:
        duration_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
        note_text = notes
        if error is not None:
            note_text = f"{notes or ''} error={error}".strip()
        active.open_spans = [item for item in active.open_spans if item.span_id != span_id]
        _add_completed_span(
            active,
            name=name,
            op_type=op_type,
            duration_ms=duration_ms,
            status=final_status,
            llm=llm,
            notes=note_text,
            parent_span_id=parent_id,
        )
        current_stack = list(_span_stack.get())
        if current_stack and current_stack[-1] == span_id:
            current_stack.pop()
        _span_stack.set(current_stack)


def _span_to_dict(span: SpanRecord) -> dict[str, Any]:
    return {
        "span_id": span.span_id,
        "parent_span_id": span.parent_span_id,
        "name": span.name,
        "op_type": span.op_type,
        "duration_ms": span.duration_ms,
        "status": span.status,
        "llm": span.llm,
        "notes": span.notes,
    }


def _active_trace_snapshot(active: _ActiveTrace) -> dict[str, Any]:
    finished_at = time.perf_counter()
    span_rows = [_span_to_dict(span) for span in active.spans]
    for open_span in active.open_spans:
        span_rows.append(
            {
                "span_id": open_span.span_id,
                "parent_span_id": open_span.parent_span_id,
                "name": open_span.name,
                "op_type": open_span.op_type,
                "duration_ms": round((finished_at - open_span.started_at) * 1000.0, 3),
                "status": "running",
                "llm": open_span.llm,
                "notes": open_span.notes,
            }
        )
    return {
        "trace_id": active.trace_id,
        "trigger": active.trigger,
        "task_id": active.task_id,
        "total_duration_ms": round((finished_at - active.started_at) * 1000.0, 3),
        "llm_call_occurred": active.llm_call_occurred,
        "status": "running",
        "error": None,
        "spans_omitted": active.spans_omitted,
        "spans": span_rows,
    }


def _finished_trace_to_dict(trace: _FinishedTrace) -> dict[str, Any]:
    return {
        "trace_id": trace.trace_id,
        "trigger": trace.trigger,
        "task_id": trace.task_id,
        "total_duration_ms": trace.total_duration_ms,
        "llm_call_occurred": trace.llm_call_occurred,
        "status": trace.status,
        "error": trace.error,
        "spans_omitted": trace.spans_omitted,
        "spans": [_span_to_dict(span) for span in trace.spans],
    }


def current_trace_snapshot() -> dict[str, Any] | None:
    active = _current_trace.get()
    if active is None:
        return None
    return _active_trace_snapshot(active)


def recent_traces_snapshot(*, limit: int = MAX_RECENT_TRACES) -> dict[str, Any]:
    if not inspection_enabled():
        return {"traces": []}
    return {"traces": _store.snapshot(limit=limit)}


def attach_trace_to_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not inspection_enabled():
        return payload
    snapshot = current_trace_snapshot()
    if snapshot is None:
        return payload
    merged = dict(payload)
    merged["performance_trace"] = snapshot
    return merged
