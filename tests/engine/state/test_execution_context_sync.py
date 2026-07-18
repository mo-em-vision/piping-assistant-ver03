"""Tests for execution context sync."""

from __future__ import annotations

from engine.state.execution_context_sync import refresh_execution_context_for_task
from engine.state.task_facts import store_user_fact
from models.task import TaskStatus, new_task
from tests.helpers.goals import task_with_planning


def test_refresh_builds_facts_index_and_state() -> None:
    task = new_task("TASK-sync", status=TaskStatus.AWAITING_INPUT, workflow_id="pipe_wall_thickness_design")
    store_user_fact(task, "material", "SA-106B")
    task_with_planning(
        task,
        {
            "current_phase": "parameter_gathering",
            "phase_missing": {"parameter_gathering": ["design_pressure"]},
        },
        workflow_id="pipe_wall_thickness_design",
    )
    refresh_execution_context_for_task(task, workflow_id="pipe_wall_thickness_design")

    ctx = task.execution_context
    assert ctx.id.startswith("EXEC-")
    assert len(ctx.facts_index.active) >= 1
    assert ctx.state.current_phase == "parameter_gathering"
    assert ctx.authority_context_id == "AUTHCTX-asme-b31.3"
    assert task.authority_context is not None
    assert task.authority_context.id == ctx.authority_context_id
    assert task.authority_context.active_authorities[0].authority_id == "AUTH-ASME-B31.3"


def test_decision_recorded_on_selection_fact() -> None:
    task = new_task("TASK-decision", status=TaskStatus.AWAITING_INPUT)
    store_user_fact(task, "pressure_design_case", "internal_pressure")
    refresh_execution_context_for_task(task)
    assert len(task.execution_context.decisions) >= 1
