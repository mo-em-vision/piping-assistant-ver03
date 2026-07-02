"""Tests for authority context sync."""

from __future__ import annotations

from engine.state.authority_context_sync import build_authority_context, link_authority_context
from engine.state.execution_context_sync import refresh_execution_context_for_task
from models.task import TaskStatus, new_task


def test_build_authority_context_from_workflow() -> None:
    task = new_task(
        "TASK-auth",
        status=TaskStatus.ACTIVE,
        workflow_id="pipe_wall_thickness_design",
    )
    task.outputs["workflow"] = "pipe_wall_thickness_design"

    auth = build_authority_context(task, workflow_id="pipe_wall_thickness_design")

    assert auth.id.startswith("AUTHCTX-")
    assert task.execution_context.authority_context_id == auth.id
    assert auth.execution_context_id == task.execution_context.id
    assert len(auth.active_authorities) == 1
    assert auth.active_authorities[0].authority_id == "AUTH-ASME-B31.3"


def test_refresh_links_authority_context() -> None:
    task = new_task("TASK-refresh", workflow_id="pipe_wall_thickness_design")
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    refresh_execution_context_for_task(task, workflow_id="pipe_wall_thickness_design")

    assert task.authority_context is not None
    assert task.authority_context.id == task.execution_context.authority_context_id


def test_link_authority_context_syncs_ids() -> None:
    task = new_task("TASK-link")
    task.authority_context = build_authority_context(task, workflow_id="pipe_wall_thickness_design")
    task.execution_context.authority_context_id = None
    link_authority_context(task)
    assert task.execution_context.authority_context_id == task.authority_context.id
