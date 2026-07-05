"""API tests for task_state.current_ask."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from api.serializers import task_state
from config.loader import CLIConfig
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.api.conftest import api_session_id
from tests.helpers.goals import task_with_planning


def test_task_state_current_ask_from_goal_tree() -> None:
    manager = TaskStateManager()
    task = manager.create_task("current-ask-api-test01", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_assumptions": ["pressure_loading"],
        "current_phase": "path_decisions",
        "phase_missing": {"path_decisions": ["pressure_loading"]},
        "phase_questions": {
            "path_decisions": {
                "pressure_loading": "Is the pipe subjected to internal or external pressure?",
            }
        },
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    payload = task_state(manager.get_task(task.task_id), manager)
    current_ask = payload.get("current_ask")
    assert current_ask is not None
    assert current_ask["kind"] == "input"
    assert current_ask["parameter_id"] == "pressure_loading"
    assert "internal or external pressure" in str(current_ask["prompt"])


def test_create_task_current_ask_aligns_with_submittable_parameters(
    tmp_path: Path,
    project_root: Path,
) -> None:
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
    service = DesktopApiService(config=config, session_id="default")
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)

    submittable = state["progress"].get("submittable_parameters") or []
    if not submittable:
        pytest.skip("workflow has no submittable parameters at creation in this graph pack")

    current_ask = state.get("current_ask")
    assert current_ask is not None
    assert current_ask["kind"] == "input"
    assert current_ask["parameter_id"] == submittable[0]


def test_fresh_pipe_wall_task_prompts_for_pressure_loading_first(
    tmp_path: Path,
    project_root: Path,
) -> None:
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
    service = DesktopApiService(config=config, session_id="default")
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)

    current_ask = state.get("current_ask")
    assert current_ask is not None
    assert current_ask["kind"] == "input"
    assert current_ask["parameter_id"] == "pressure_loading"

    timeline = state["progress"]["timeline"]
    active_steps = [step for step in timeline if step.get("status") == "active"]
    assert active_steps
    assert active_steps[0]["id"] == "pressure_loading"
    assert not any(step.get("id") == "thickness" and step.get("status") == "active" for step in timeline)

    assert state["active_nodes"]
    assert state["active_nodes"][0] in {"304.1.1-a", "B313-304.1.1"}

    from engine.inspection.builder import build_inspection_payload

    store = service._store_for(session_id)
    manager = store.load_state_manager()
    task = manager.get_task(state["task_id"])
    inspection = build_inspection_payload(task, manager=manager, reader=service._reader())
    frame = inspection["replay_frames"][0]
    assert frame.get("active_node") is not None
