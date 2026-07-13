"""Performance-related submit_input behavior tests."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile

from api.desktop_service import DesktopApiService
from config.loader import CLIConfig
from engine.inspection.performance_trace import (
    begin_interaction_trace,
    finish_interaction_trace,
    reset_trace_context,
)
from tests.helpers.performance_metrics import (
    assert_interactive_gate_submit_span_budgets,
    record_performance_row,
)
from tests.helpers.projection_performance_contract import assert_interactive_trace_projection_budget


def _pipe_wall_service() -> tuple[DesktopApiService, str]:
    os.environ["DEV_INSPECTION_ENABLED"] = "1"
    project_root = Path(__file__).resolve().parents[2]
    tmpdir = tempfile.mkdtemp()
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=Path(tmpdir),
        standards_root=project_root / "knowledge" / "standards",
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    service = DesktopApiService(config=config, session_id="default")
    project = service.create_project("Submit Input Perf Test")
    session_id = service.activate_project(project["id"])["session_id"]
    return service, session_id


def test_active_task_parameter_submit_does_not_call_llm() -> None:
    service, session_id = _pipe_wall_service()
    state = service.create_task("pipe_wall_thickness_design", session_id=session_id)
    task_id = state["task_id"]

    begin_interaction_trace("POST /api/v1/tasks/inputs", trace_id="9" * 16, task_id=task_id)
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

    trace = state.get("performance_trace") or {}
    assert trace.get("llm_call_occurred", False) is False
    assert "engineering_plan" not in state
    assert isinstance(state.get("display_outputs"), list)

    metrics = assert_interactive_gate_submit_span_budgets(trace, context="submit_input_no_llm")
    assert_interactive_trace_projection_budget(trace, context="submit_input_no_llm")
    record_performance_row(
        behavior="submit_input no LLM + span budgets",
        test_name="test_active_task_parameter_submit_does_not_call_llm",
        metrics=metrics,
    )
