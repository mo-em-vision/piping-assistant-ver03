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
    assert "304.1.2" not in str(current_ask["prompt"])


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


def test_fresh_pipe_wall_task_prompts_for_straight_pipe_first(
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
    assert current_ask["parameter_id"] == "straight_pipe_section"

    timeline = state["progress"]["timeline"]
    active_steps = [step for step in timeline if step.get("status") == "active"]
    assert active_steps
    assert active_steps[0]["id"] == "straight_pipe_section"
    assert not any(step.get("id") == "thickness" and step.get("status") == "active" for step in timeline)

    prompt = str(current_ask.get("prompt") or "")
    assert "straight section" in prompt.lower()

    assert state["active_nodes"]
    assert state["active_nodes"][0] in {"304.1.1-a", "B313-304.1.1"}

    from engine.inspection.builder import build_inspection_payload

    store = service._store_for(session_id)
    manager = store.load_state_manager()
    task = manager.get_task(state["task_id"])
    inspection = build_inspection_payload(task, manager=manager, reader=service._reader())
    frame = inspection["replay_frames"][0]
    assert frame.get("active_node") is not None


def _advance_pipe_wall_to_nominal_pipe_size(
    service: DesktopApiService,
    session_id: str,
) -> dict:
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]
    values: dict[str, tuple[object, str | None]] = {
        "straight_pipe_section": (True, None),
        "pressure_loading": ("internal_pressure", None),
        "internal_design_gage_pressure": (8.0, "bar"),
    }
    for _ in range(8):
        submittable = state["progress"].get("submittable_parameters") or []
        ask = (state.get("current_ask") or {}).get("parameter_id")
        param = ask if ask in submittable else (submittable[0] if submittable else None)
        if param == "nominal_pipe_size":
            break
        if param is None:
            break
        if param not in values:
            pytest.skip(f"unexpected parameter before nominal_pipe_size: {param}")
        value, unit = values[param]
        state = service.submit_input(
            task_id,
            parameter=param,
            value=value,
            unit=unit,
            session_id=session_id,
        )
    return state


def test_timeline_active_step_follows_current_ask_after_internal_design_gage_pressure(
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
    state = _advance_pipe_wall_to_nominal_pipe_size(service, session_id)

    current_ask = state.get("current_ask")
    assert current_ask is not None
    assert current_ask["kind"] == "input"
    assert current_ask["parameter_id"] == "nominal_pipe_size"

    submittable = state["progress"].get("submittable_parameters") or []
    assert submittable[0] == "nominal_pipe_size"
    assert state["progress"]["current_step_id"] == "nominal_pipe_size"

    timeline = {step["id"]: step["status"] for step in state["progress"]["timeline"]}
    assert timeline["nominal_pipe_size"] == "active"
    assert timeline["design_temperature"] == "pending"


def test_timeline_active_step_follows_material_grade_ask(
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
    state = _advance_pipe_wall_to_nominal_pipe_size(service, session_id)
    task_id = state["task_id"]
    state = service.submit_input(
        task_id,
        parameter="nominal_pipe_size",
        value=2,
        unit=None,
        session_id=session_id,
    )

    current_ask = state.get("current_ask")
    assert current_ask is not None
    assert current_ask["parameter_id"] == "material_grade"

    submittable = state["progress"].get("submittable_parameters") or []
    assert submittable[0] == "material_grade"
    assert state["progress"]["current_step_id"] == "material_grade"

    timeline = {step["id"]: step["status"] for step in state["progress"]["timeline"]}
    assert "nominal_pipe_size" in timeline
    assert "outside_diameter" in timeline
    assert timeline["nominal_pipe_size"] == "done"
    assert timeline["outside_diameter"] in {"done", "pending"}
    assert timeline["material_grade"] == "active"
    assert timeline["design_temperature"] == "pending"


def test_timeline_active_step_follows_current_ask_when_submittable_order_differs() -> None:
    """Timeline active row must match current_ask, not submittable_parameters[0]."""
    from engine.state.state_manager import TaskStateManager
    from models.input import InputSource, InputStatus
    from tests.helpers.facts import legacy_input, set_fact_from_input

    manager = TaskStateManager()
    task = manager.create_task("current-ask-timeline-sync", status=TaskStatus.AWAITING_INPUT)
    set_fact_from_input(
        task,
        legacy_input(
            input_id="internal_design_gage_pressure",
            value=8.0,
            unit="bar",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    planning = {
        "current_phase": "parameter_gathering",
        "phase_missing": {
            "parameter_gathering": [
                "nominal_pipe_size",
                "material_grade",
                "design_temperature",
            ],
        },
        "collection_field_order": [
            "straight_pipe_section",
            "pressure_loading",
            "internal_design_gage_pressure",
            "nominal_pipe_size",
            "material_grade",
            "design_temperature",
        ],
        "graph_input_order": [
            "internal_design_gage_pressure",
            "nominal_pipe_size",
            "material_grade",
            "design_temperature",
        ],
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    state = task_state(task, manager)
    current_ask = state.get("current_ask") or {}
    assert current_ask.get("kind") == "input"
    ask_id = current_ask.get("parameter_id")
    assert ask_id in {"material_grade", "material", "nominal_pipe_size"}

    submittable = state["progress"].get("submittable_parameters") or []
    if ask_id == "material_grade" and "nominal_pipe_size" in submittable:
        assert submittable.index("nominal_pipe_size") < submittable.index("material_grade")

    assert state["progress"]["current_step_id"] == ask_id or (
        ask_id == "material_grade"
        and state["progress"]["current_step_id"] == "material_grade"
    )

    timeline = {step["id"]: step["status"] for step in state["progress"]["timeline"]}
    active_ids = [step_id for step_id, status in timeline.items() if status == "active"]
    assert len(active_ids) == 1
    assert active_ids[0] == state["progress"]["current_step_id"]
    assert timeline.get("nominal_pipe_size") != "active" or ask_id == "nominal_pipe_size"


def test_timeline_shows_nps_and_od_before_material_at_internal_design_gage_pressure_ask(
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
    task_id = state["task_id"]
    for param, val, unit in (
        ("straight_pipe_section", True, None),
        ("pressure_loading", "internal_pressure", None),
        ("internal_design_gage_pressure", 8.0, "bar"),
    ):
        state = service.submit_input(
            task_id,
            parameter=param,
            value=val,
            unit=unit,
            session_id=session_id,
        )

    current_ask = state.get("current_ask") or {}
    assert current_ask.get("parameter_id") == "nominal_pipe_size"

    timeline = {
        step["id"]: step["status"]
        for step in state["progress"]["timeline"]
        if step["id"] not in {"thickness", "report"}
    }
    assert timeline["nominal_pipe_size"] == "active"
    assert timeline["outside_diameter"] == "pending"
    assert timeline.get("material_grade") == "pending"


def test_timeline_input_order_matches_parameter_ask_order(
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
    state = _advance_pipe_wall_to_nominal_pipe_size(service, session_id)

    input_ids = [
        step["id"]
        for step in state["progress"]["timeline"]
        if step["id"] not in {"thickness", "report"}
    ]
    assert input_ids.index("internal_design_gage_pressure") < input_ids.index("nominal_pipe_size")
    assert input_ids.index("nominal_pipe_size") < input_ids.index("design_temperature")
