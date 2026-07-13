"""Performance gating: dev/debug projections must stay off the interactive workflow path."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from api.serializers import task_state
from config.loader import CLIConfig
from engine.inspection.performance_trace import (
    begin_interaction_trace,
    finish_interaction_trace,
    recent_traces_snapshot,
    reset_trace_context,
)
from engine.planner.goal_builder import build_goal_tree
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.api.conftest import api_session_id
from tests.api.test_parameter_key_contract import _INTERNAL_PRESSURE_SUBMISSIONS
from tests.helpers.projection_performance_contract import (
    SERIALIZER_DEBUG_PROJECTION_SPANS,
    assert_interactive_trace_projection_budget,
    assert_trace_rebuilds_inspection_debug_projections,
    span_names,
)


def _service(tmp_path: Path, project_root: Path) -> DesktopApiService:
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=tmp_path / "sessions",
        standards_root=project_root / "knowledge" / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    return DesktopApiService(config=config, session_id="default")


def _reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def _fresh_pipe_wall_task(project_root: Path):
    manager = TaskStateManager()
    task = manager.create_task("projection-perf-pwt", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    reader = _reader(project_root)
    build_goal_tree(task, reader)
    manager.replace_task(task.task_id, task)
    return manager, task, reader


@pytest.fixture
def inspection_env():
    previous = os.environ.get("DEV_INSPECTION_ENABLED")
    os.environ["DEV_INSPECTION_ENABLED"] = "1"
    yield
    if previous is None:
        os.environ.pop("DEV_INSPECTION_ENABLED", None)
    else:
        os.environ["DEV_INSPECTION_ENABLED"] = previous
    reset_trace_context()


def _latest_trace() -> dict:
    traces = recent_traces_snapshot()["traces"]
    assert traces, "expected a finished performance trace"
    return traces[0]


def test_submit_input_skips_debug_projection_rebuild(
    tmp_path: Path,
    project_root: Path,
    inspection_env,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    begin_interaction_trace("POST /api/v1/tasks/inputs", trace_id="a" * 16, task_id=task_id)
    try:
        state = service.submit_input(
            task_id,
            parameter="straight_pipe_section",
            value=True,
            session_id=session_id,
        )
        finish_interaction_trace(status="success")
    finally:
        reset_trace_context()

    assert "engineering_plan" not in state
    assert "planner_debug_projection" not in state
    trace = _latest_trace()
    assert_interactive_trace_projection_budget(trace, context="submit_input")
    assert "build_inspection_payload" not in span_names(trace)


def test_get_task_skips_debug_projection_rebuild(
    tmp_path: Path,
    project_root: Path,
    inspection_env,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    begin_interaction_trace("GET /api/v1/tasks/{id}", trace_id="b" * 16, task_id=task_id)
    try:
        state = service.get_task(task_id, session_id)
        finish_interaction_trace(status="success")
    finally:
        reset_trace_context()

    assert "engineering_plan" not in state
    trace = _latest_trace()
    assert_interactive_trace_projection_budget(trace, context="get_task")


def test_internal_pressure_journey_each_submit_skips_debug_projection_rebuild(
    tmp_path: Path,
    project_root: Path,
    inspection_env,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    for step_index in range(len(_INTERNAL_PRESSURE_SUBMISSIONS) + 4):
        if state.get("status") == "completed":
            break

        submittable = list(state.get("progress", {}).get("submittable_parameters") or [])
        if not submittable:
            break

        current_ask = state.get("current_ask") or {}
        parameter_id = current_ask.get("parameter_id")
        if parameter_id not in submittable:
            parameter_id = submittable[0]

        if parameter_id not in _INTERNAL_PRESSURE_SUBMISSIONS:
            pytest.fail(f"unexpected parameter prompt at step {step_index}: {parameter_id!r}")

        value, unit = _INTERNAL_PRESSURE_SUBMISSIONS[parameter_id]
        trace_id = f"{step_index:02x}" * 8

        begin_interaction_trace(
            "POST /api/v1/tasks/inputs",
            trace_id=trace_id,
            task_id=task_id,
        )
        try:
            state = service.submit_input(
                task_id,
                parameter=parameter_id,
                value=value,
                unit=unit,
                session_id=session_id,
            )
            finish_interaction_trace(status="success")
        finally:
            reset_trace_context()

        trace = _latest_trace()
        assert trace["trace_id"] == trace_id
        assert_interactive_trace_projection_budget(
            trace,
            context=f"submit_input:{parameter_id}",
        )


def test_full_projection_mode_rebuilds_serializer_debug_spans(
    project_root: Path,
    inspection_env,
) -> None:
    manager, task, reader = _fresh_pipe_wall_task(project_root)

    begin_interaction_trace("task_state_full", trace_id="c" * 16, task_id=task.task_id)
    try:
        payload = task_state(task, manager, reader=reader, projection_mode="full")
        finish_interaction_trace(status="success")
    finally:
        reset_trace_context()

    assert isinstance(payload.get("engineering_plan"), dict)
    names = span_names(_latest_trace())
    assert SERIALIZER_DEBUG_PROJECTION_SPANS.issubset(names)


def test_inspection_request_rebuilds_debug_projections(
    tmp_path: Path,
    project_root: Path,
    inspection_env,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    begin_interaction_trace("inspection_poll", trace_id="d" * 16, task_id=task_id)
    try:
        payload = service.get_inspection(task_id, session_id)
        finish_interaction_trace(status="success")
    finally:
        reset_trace_context()

    assert isinstance(payload.get("planner_debug_projection"), dict)
    assert isinstance(payload.get("task_state_views"), dict)
    assert isinstance(payload.get("engineering_plan"), dict)
    trace = _latest_trace()
    assert_trace_rebuilds_inspection_debug_projections(trace, context="get_inspection")
