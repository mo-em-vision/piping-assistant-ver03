"""Per-span performance budgets for pipe wall interactive workflow (plan §9)."""

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
from tests.helpers.performance_metrics import (
    INSPECTION_BUILD_MIN_MS,
    assert_interactive_gate_submit_span_budgets,
    collect_full_projection_metrics,
    collect_inspection_metrics,
    collect_interactive_submit_metrics,
    record_performance_row,
)
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
    task = manager.create_task("perf-spans-pwt", status=TaskStatus.AWAITING_INPUT)
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


def _gate_submit_trace(
    service: DesktopApiService,
    session_id: str,
    task_id: str,
    *,
    trace_id: str,
) -> dict:
    begin_interaction_trace("POST /api/v1/tasks/inputs", trace_id=trace_id, task_id=task_id)
    try:
        state = service.submit_input(
            task_id,
            parameter="straight_pipe_section",
            value=True,
            session_id=session_id,
        )
        finish_interaction_trace(status="success")
        return state["performance_trace"]
    finally:
        reset_trace_context()


def test_measure_submit_input_total_time(
    tmp_path: Path,
    project_root: Path,
    inspection_env,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    trace = _gate_submit_trace(service, session_id, created["task_id"], trace_id="1" * 16)

    metrics = assert_interactive_gate_submit_span_budgets(trace, context="gate_submit")
    record_performance_row(
        behavior="Measure submit_input total time",
        test_name="test_measure_submit_input_total_time",
        metrics=metrics,
    )


def test_measure_graph_expansion_time(
    tmp_path: Path,
    project_root: Path,
    inspection_env,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    trace = _gate_submit_trace(service, session_id, created["task_id"], trace_id="2" * 16)

    metrics = assert_interactive_gate_submit_span_budgets(trace, context="graph_expansion")
    assert metrics["graph_preview_eval_ms"] > 0 or metrics["graph_build_plan_ms"] > 0
    record_performance_row(
        behavior="Measure graph expansion time",
        test_name="test_measure_graph_expansion_time",
        metrics={
            "graph_build_plan_ms": metrics["graph_build_plan_ms"],
            "graph_preview_eval_ms": metrics["graph_preview_eval_ms"],
        },
    )


def test_measure_planner_projection_time(
    tmp_path: Path,
    project_root: Path,
    inspection_env,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    trace = _gate_submit_trace(service, session_id, created["task_id"], trace_id="3" * 16)

    metrics = assert_interactive_gate_submit_span_budgets(trace, context="planner_projection")
    assert metrics["engineering_plan_projection_ms"] > 0
    record_performance_row(
        behavior="Measure planner projection time",
        test_name="test_measure_planner_projection_time",
        metrics={
            "engineering_plan_projection_ms": metrics["engineering_plan_projection_ms"],
            "goal_tree_refresh_ms": metrics["goal_tree_refresh_ms"],
        },
    )


def test_measure_task_state_serialization_time(
    tmp_path: Path,
    project_root: Path,
    inspection_env,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    trace = _gate_submit_trace(service, session_id, created["task_id"], trace_id="4" * 16)

    metrics = assert_interactive_gate_submit_span_budgets(trace, context="task_state_serialization")
    assert metrics["task_state_span_ms"] > 0
    record_performance_row(
        behavior="Measure task_state serialization time",
        test_name="test_measure_task_state_serialization_time",
        metrics={"task_state_span_ms": metrics["task_state_span_ms"]},
    )


def test_measure_display_output_build_time(
    tmp_path: Path,
    project_root: Path,
    inspection_env,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    trace = _gate_submit_trace(service, session_id, created["task_id"], trace_id="5" * 16)

    metrics = assert_interactive_gate_submit_span_budgets(trace, context="display_output_build")
    assert metrics["display_output_projection_ms"] > 0
    record_performance_row(
        behavior="Measure display output build time",
        test_name="test_measure_display_output_build_time",
        metrics={"display_output_projection_ms": metrics["display_output_projection_ms"]},
    )


def test_dev_mode_projections_do_not_contribute_on_interactive_submit(
    tmp_path: Path,
    project_root: Path,
    inspection_env,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    interactive_trace = _gate_submit_trace(service, session_id, task_id, trace_id="6" * 16)
    interactive_metrics = collect_interactive_submit_metrics(interactive_trace)
    assert_interactive_trace_projection_budget(interactive_trace, context="interactive_submit")

    manager, task, reader = _fresh_pipe_wall_task(project_root)
    begin_interaction_trace("task_state_full", trace_id="7" * 16, task_id=task.task_id)
    try:
        task_state(task, manager, reader=reader, projection_mode="full")
        finish_interaction_trace(status="success")
    finally:
        reset_trace_context()
    full_metrics = collect_full_projection_metrics(_latest_trace())
    assert SERIALIZER_DEBUG_PROJECTION_SPANS.issubset(span_names(_latest_trace()))

    begin_interaction_trace("inspection_poll", trace_id="8" * 16, task_id=task_id)
    try:
        service.get_inspection(task_id, session_id)
        finish_interaction_trace(status="success")
    finally:
        reset_trace_context()
    inspection_trace = _latest_trace()
    inspection_metrics = collect_inspection_metrics(inspection_trace)
    assert_trace_rebuilds_inspection_debug_projections(inspection_trace, context="inspection_poll")

    assert interactive_metrics["serializer_debug_projection_ms"] == 0.0
    assert interactive_metrics["build_inspection_payload_ms"] == 0.0
    assert full_metrics["serializer_debug_projection_ms"] >= 0.0
    assert inspection_metrics["build_inspection_payload_ms"] >= INSPECTION_BUILD_MIN_MS
    assert (
        inspection_metrics["build_inspection_payload_ms"]
        > interactive_metrics["serializer_debug_projection_ms"]
    )

    record_performance_row(
        behavior="Dev-mode projections latency A/B",
        test_name="test_dev_mode_projections_do_not_contribute_on_interactive_submit",
        metrics={
            "interactive_serializer_debug_ms": interactive_metrics["serializer_debug_projection_ms"],
            "interactive_inspection_build_ms": interactive_metrics["build_inspection_payload_ms"],
            "full_serializer_debug_ms": full_metrics["serializer_debug_projection_ms"],
            "inspection_build_ms": inspection_metrics["build_inspection_payload_ms"],
            "inspection_total_ms": inspection_metrics["inspection_total_ms"],
        },
    )
