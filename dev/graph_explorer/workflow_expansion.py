"""Orchestrator for workflow expansion visualization JSON."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from engine.router import PIPE_WALL_THICKNESS_DESIGN

from dev.graph_explorer.adapter import GraphExplorerAdapter
from dev.graph_explorer.expansion_types import PIPE_WALL_WORKFLOWS
from dev.graph_explorer.projectors.base import (
    GenericExpansionProjector,
    load_task_for_graph_explorer,
    resolve_workflow_id,
)
from dev.graph_explorer.projectors.pipe_wall_thickness import PipeWallThicknessExpansionProjector


def build_workflow_expansion_view(
    task_id: str | None,
    session_id: str | None,
    adapter: GraphExplorerAdapter,
) -> dict[str, Any]:
    """Build visualization-ready workflow expansion JSON for a task."""
    warnings: list[str] = []
    sid = session_id or adapter.session_id

    task = load_task_for_graph_explorer(adapter, task_id, session_id=sid)
    if task is None:
        message = f"Task not found in project session {sid}." if task_id else "No active task."
        return {
            "task_id": task_id,
            "workflow": "",
            "task_status": "unknown",
            "current_phase": "unknown",
            "phase_missing": {},
            "inputs": {},
            "expansion_state": {},
            "nodes": [],
            "edges": [],
            "timeline": [],
            "warnings": [message],
            "revision": _revision_for_empty(task_id, sid),
            "debug": {
                "has_task": False,
                "has_compiled_graph": bool(adapter._stores),  # noqa: SLF001
                "has_planning_summary": False,
                "has_execution_trace": False,
            },
        }

    workflow = resolve_workflow_id(task)
    if workflow in PIPE_WALL_WORKFLOWS or workflow == PIPE_WALL_THICKNESS_DESIGN:
        projector: GenericExpansionProjector | PipeWallThicknessExpansionProjector = (
            PipeWallThicknessExpansionProjector(adapter)
        )
    else:
        projector = GenericExpansionProjector(adapter)
        if workflow:
            warnings.append(f"No dedicated expansion projector for workflow '{workflow}'; using generic view.")

    try:
        view = projector.project(task, requested_task_id=task_id)
    except Exception as exc:  # noqa: BLE001 - return partial JSON for dev tooling
        warnings.append(f"Projection error: {exc}")
        fallback = GenericExpansionProjector(adapter)
        view = fallback.project(task, requested_task_id=task_id)

    view_warnings = list(view.get("warnings") or [])
    view_warnings.extend(warnings)
    view["warnings"] = view_warnings
    view["revision"] = compute_expansion_revision(task, adapter)
    return view


def compute_expansion_revision(task: Any, adapter: GraphExplorerAdapter) -> str:
    db_mtimes: list[float] = []
    for store in adapter._stores.values():  # noqa: SLF001
        path = store.db_path
        if path.is_file():
            db_mtimes.append(path.stat().st_mtime)

    from engine.state.task_facts import active_facts
    from models.fact import fact_scalar_value

    inputs = active_facts(task)
    payload = {
        "task_id": task.task_id,
        "active_nodes": sorted(task.active_nodes),
        "facts": {key: str(fact_scalar_value(inputs[key])) for key in sorted(inputs)},
        "outputs_keys": sorted(task.outputs.keys()),
        "trace_len": len(task.outputs.get("_execution_trace") or []),
        "goal_count": len(task.goal_store.goals),
        "db_mtimes": sorted(db_mtimes),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    return digest[:16]


def _revision_for_empty(task_id: str | None, session_id: str) -> str:
    payload = {"task_id": task_id, "session_id": session_id, "empty": True}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return digest[:16]
