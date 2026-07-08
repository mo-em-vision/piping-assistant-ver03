"""Tests for developer performance tracing."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from api.desktop_service import ApiError, DesktopApiService
from api.performance_trace import get_performance_traces_payload
from engine.inspection.performance_trace import (
    MAX_SPANS_PER_TRACE,
    begin_interaction_trace,
    current_trace_id,
    finish_interaction_trace,
    perf_span,
    recent_traces_snapshot,
    reset_trace_context,
    resolve_trace_id,
)
from tests.api.conftest import api_session_id


def _service(tmp_path: Path, project_root: Path) -> DesktopApiService:
    from config.loader import CLIConfig

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


def test_resolve_trace_id_accepts_client_value() -> None:
    client_id = "a" * 16
    assert resolve_trace_id(client_id) == client_id


def test_resolve_trace_id_generates_fallback() -> None:
    trace_id = resolve_trace_id(None)
    assert len(trace_id) == 16
    assert trace_id != resolve_trace_id(None)


def test_perf_span_records_nested_spans(inspection_env) -> None:
    begin_interaction_trace("test_trigger", trace_id="b" * 16)
    try:
        with perf_span("outer", "api"):
            with perf_span("inner", "planner", notes="step=1"):
                pass
        finish_interaction_trace(status="success")
    finally:
        reset_trace_context()

    traces = recent_traces_snapshot()["traces"]
    assert traces
    trace = traces[0]
    assert trace["trace_id"] == "b" * 16
    assert trace["trigger"] == "test_trigger"
    names = {span["name"] for span in trace["spans"]}
    assert "outer" in names
    assert "inner" in names
    op_types = {span["op_type"] for span in trace["spans"]}
    assert "api" in op_types
    assert "planner" in op_types


def test_context_reset_prevents_leakage(inspection_env) -> None:
    begin_interaction_trace("first", trace_id="c" * 16)
    finish_interaction_trace(status="success")
    reset_trace_context()
    assert current_trace_id() is None

    begin_interaction_trace("second", trace_id="d" * 16)
    finish_interaction_trace(status="success")
    reset_trace_context()

    traces = recent_traces_snapshot()["traces"]
    assert traces[0]["trace_id"] == "d" * 16
    assert traces[1]["trace_id"] == "c" * 16


def test_span_truncation_summarizes_excess(inspection_env) -> None:
    begin_interaction_trace("truncation_test", trace_id="e" * 16)
    try:
        for index in range(MAX_SPANS_PER_TRACE + 5):
            with perf_span(f"span_{index}", "api"):
                pass
        finish_interaction_trace(status="success")
    finally:
        reset_trace_context()

    trace = recent_traces_snapshot()["traces"][0]
    assert trace["spans_omitted"] > 0
    assert any(span["name"] == "spans_truncated" for span in trace["spans"])


def test_submit_input_returns_performance_trace(
    tmp_path: Path,
    project_root: Path,
    inspection_env,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    client_trace_id = "f" * 16
    begin_interaction_trace(
        "POST /api/v1/tasks/inputs",
        trace_id=client_trace_id,
        task_id=task_id,
    )
    try:
        state = service.submit_input(
            task_id,
            parameter="straight_pipe_section",
            value=True,
            unit="dimensionless",
            session_id=session_id,
        )
        finish_interaction_trace(status="success")
    finally:
        reset_trace_context()

    assert "performance_trace" in state
    trace = state["performance_trace"]
    assert trace["trace_id"] == client_trace_id
    span_names = {span["name"] for span in trace["spans"]}
    assert "submit_input" in span_names
    assert "task_state" in span_names
    op_types = {span["op_type"] for span in trace["spans"]}
    assert "api" in op_types
    assert "planner" in op_types
    assert "serializer" in op_types

    traces = recent_traces_snapshot()["traces"]
    assert traces[0]["trace_id"] == client_trace_id


def test_inspection_poll_separate_trace(
    tmp_path: Path,
    project_root: Path,
    inspection_env,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = created["task_id"]

    begin_interaction_trace("inspection_poll", trace_id="1" * 16, task_id=task_id)
    try:
        service.get_inspection(task_id, session_id)
        finish_interaction_trace(status="success")
    finally:
        reset_trace_context()

    trace = recent_traces_snapshot()["traces"][0]
    assert trace["trigger"] == "inspection_poll"
    span_names = {span["name"] for span in trace["spans"]}
    assert "build_inspection_payload" in span_names
    assert "get_inspection" in span_names


def test_performance_traces_api_disabled(tmp_path: Path, project_root: Path) -> None:
    os.environ.pop("DEV_INSPECTION_ENABLED", None)
    service = _service(tmp_path, project_root)
    assert service is not None
    with pytest.raises(ApiError) as exc:
        get_performance_traces_payload()
    assert exc.value.status == 404


def test_performance_traces_api_returns_recent(
    tmp_path: Path,
    project_root: Path,
    inspection_env,
) -> None:
    service = _service(tmp_path, project_root)
    session_id = api_session_id(service)
    created = service.create_task("pipe_wall_thickness_design", session_id)

    begin_interaction_trace("create_task", trace_id="2" * 16, task_id=created["task_id"])
    finish_interaction_trace(status="success")
    reset_trace_context()

    payload = get_performance_traces_payload(limit=5)
    assert "traces" in payload
    assert payload["traces"]
    assert payload["traces"][0]["trace_id"] == "2" * 16
