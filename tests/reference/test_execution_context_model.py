"""Tests for runtime ExecutionContext model per template."""

from __future__ import annotations

from engine.validation.execution_context_validator import (
    validate_execution_context,
    validate_execution_context_dict,
)
from models.execution_context import (
    ExecutionContextStatus,
    execution_context_for_task,
    execution_context_from_dict,
    execution_context_to_dict,
    new_decision_id,
    Decision,
)
from models.fact_store import FactStore
from models.goal_store import GoalStore
from models.task import TaskStatus


def test_execution_context_factory() -> None:
    ctx = execution_context_for_task(
        "TASK-test",
        workflow_id="WF-pipe-wall-thickness-design",
        status=TaskStatus.AWAITING_INPUT,
    )
    assert ctx.id.startswith("EXEC-")
    assert ctx.type == "execution_context"
    assert ctx.task_id == "TASK-test"
    assert ctx.status == ExecutionContextStatus.AWAITING_INPUT


def test_valid_execution_context_passes() -> None:
    ctx = execution_context_for_task(
        "TASK-test",
        workflow_id="WF-pipe-wall-thickness-design",
    )
    ctx.authority_context_id = "AUTHCTX-asme-b31.3"
    assert validate_execution_context(ctx) == []


def test_completed_with_blocked_goals_fails() -> None:
    ctx = execution_context_for_task("TASK-test", workflow_id="WF-test")
    ctx.authority_context_id = "AUTHCTX-test"
    ctx.status = ExecutionContextStatus.COMPLETED
    ctx.state.blocked_goals = ["GOAL-1"]
    issues = validate_execution_context(ctx)
    assert any("blocked goals" in issue for issue in issues)


def test_json_round_trip() -> None:
    ctx = execution_context_for_task(
        "TASK-test",
        workflow_id="WF-test",
        project_id="PROJECT-1",
    )
    ctx.authority_context_id = "AUTHCTX-test"
    ctx.decisions.append(
        Decision(
            id=new_decision_id(),
            parameter="PARAM-pressure-design-case",
            selected_value="internal_pressure",
            source="user_input",
            timestamp="2026-07-02T10:20:00Z",
        )
    )
    restored = execution_context_from_dict(execution_context_to_dict(ctx))
    assert restored.id == ctx.id
    assert restored.task_id == ctx.task_id
    assert len(restored.decisions) == 1


def test_validate_dict_round_trip() -> None:
    ctx = execution_context_for_task("TASK-test", workflow_id="WF-test")
    ctx.authority_context_id = "AUTHCTX-test"
    assert validate_execution_context_dict(execution_context_to_dict(ctx)) == []


def test_stores_embedded() -> None:
    ctx = execution_context_for_task("TASK-test")
    assert isinstance(ctx.fact_store, FactStore)
    assert isinstance(ctx.goal_store, GoalStore)
