"""Developer inspection API helpers."""

from __future__ import annotations

from typing import Any

from api.desktop_service import ApiError
from engine.inspection.builder import build_inspection_payload
from engine.inspection.dev_guard import inspection_enabled
from engine.inspection.integrity import run_integrity_checks
from engine.inspection.replay import build_replay_snapshot
from engine.inspection.trace import build_execution_trace
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.task import Task


def require_inspection_enabled() -> None:
    if not inspection_enabled():
        raise ApiError("not_found", "Developer inspection is not enabled", status=404)


def get_inspection_payload(
    manager: TaskStateManager,
    task_id: str,
    *,
    reader: StandardsReader | None,
) -> dict[str, Any]:
    require_inspection_enabled()
    task = manager.get_task(task_id)
    return build_inspection_payload(task, manager=manager, reader=reader)


def set_breakpoint(
    manager: TaskStateManager,
    task_id: str,
    *,
    paused: bool,
    step: bool = False,
) -> dict[str, Any]:
    require_inspection_enabled()
    task = manager.get_task(task_id)
    current = task.outputs.get("_inspection_breakpoint")
    if not isinstance(current, dict):
        current = {}
    payload = {
        "paused": paused,
        "step_once": step,
        "resume": not paused and not step,
    }
    manager.store_output(task_id, "_inspection_breakpoint", {**current, **payload})
    return payload


def run_integrity(
    reader: StandardsReader | None,
) -> dict[str, Any]:
    require_inspection_enabled()
    checks = run_integrity_checks(reader)
    return {"checks": [check.to_dict() for check in checks]}


def persist_replay_snapshot(task: Task, manager: TaskStateManager, reader: StandardsReader | None) -> None:
    if not inspection_enabled():
        return
    from engine.inspection.replay import build_replay_frames
    from engine.inspection.trace import build_execution_trace
    from engine.state.workflow_state import build_workflow_state
    from engine.inspection.planner_decisions import planner_decisions_from_task_outputs

    trace = build_execution_trace(dict(task.outputs), reader=reader)
    workflow_state = build_workflow_state(
        task,
        step_progress=manager.list_step_progress(task.task_id),
        reader=reader,
    )
    frames = build_replay_frames(
        trace,
        workflow_state,
        dict(task.outputs),
        planner_decisions=planner_decisions_from_task_outputs(task.outputs),
    )
    manager.store_output(task.task_id, "_replay_snapshot", build_replay_snapshot(frames))
