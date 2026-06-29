"""Background prefetch cache for upcoming graph steps."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from engine.graph.graph_store import GraphStore
from engine.graph.lazy_expander import ExpansionState, expand_workflow, next_pending_parameter
from models.input import EngineeringInput


@dataclass
class PrefetchCache:
    """Thread-safe cache of prefetched expansion contexts keyed by task id."""

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _entries: dict[str, dict[str, Any]] = field(default_factory=dict, repr=False)

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._entries.get(task_id)

    def put(self, task_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            self._entries[task_id] = payload

    def invalidate(self, task_id: str) -> None:
        with self._lock:
            self._entries.pop(task_id, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


_GLOBAL_PREFETCH = PrefetchCache()


def prefetch_cache() -> PrefetchCache:
    return _GLOBAL_PREFETCH


def prefetch_next(
    store: GraphStore,
    *,
    task_id: str,
    root_id: str,
    inputs: dict[str, EngineeringInput],
    horizon: int = 1,
) -> dict[str, Any]:
    """Prefetch expansion state and upcoming parameter metadata."""
    expansion = expand_workflow(store, root_id, inputs, lazy=False)
    current = next_pending_parameter(store, expansion, inputs)
    upcoming: list[str] = []
    if current:
        seen_current = False
        for node_id in expansion.active_nodes:
            node = store.get_node(node_id)
            if node is None or node.node_type != "parameter":
                continue
            input_id = str(node.metadata.get("input_id", ""))
            if not input_id:
                continue
            if input_id == current:
                seen_current = True
                continue
            if seen_current and input_id not in inputs:
                upcoming.append(input_id)
                if len(upcoming) >= horizon:
                    break

    payload = {
        "root_id": root_id,
        "active_nodes": list(expansion.active_nodes),
        "current_parameter": current,
        "upcoming_parameters": upcoming,
    }
    prefetch_cache().put(task_id, payload)
    return payload


def prefetch_async(
    store: GraphStore,
    *,
    task_id: str,
    root_id: str,
    inputs: dict[str, EngineeringInput],
    horizon: int = 1,
) -> None:
    """Fire-and-forget prefetch in a background thread."""

    def _run() -> None:
        try:
            prefetch_next(
                store,
                task_id=task_id,
                root_id=root_id,
                inputs=inputs,
                horizon=horizon,
            )
        except Exception:
            pass

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
