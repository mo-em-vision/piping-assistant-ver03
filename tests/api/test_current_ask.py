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
        "missing_assumptions": ["pressure_design_case"],
        "current_phase": "path_decisions",
        "phase_missing": {"path_decisions": ["pressure_design_case"]},
        "phase_questions": {
            "path_decisions": {
                "pressure_design_case": "Is the pipe subjected to internal or external pressure?",
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
    assert current_ask["parameter_id"] == "pressure_design_case"
    assert "pressure" in str(current_ask["prompt"]).lower()
    assert "304.1.2" in str(current_ask["prompt"])


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
    assert current_ask["parameter_id"] in submittable
    engineering_plan = state.get("engineering_plan") or {}
    input_strategy = engineering_plan.get("input_strategy") or {}
    next_fields = input_strategy.get("next_fields") or []
    if next_fields:
        assert current_ask["parameter_id"] == next_fields[0]
    else:
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
    assert "straight pipe" in prompt.lower()

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
        "pressure_design_case": ("internal_pressure", None),
        "corrosion_allowance": (0.5, "mm"),
        "design_temperature": (200.0, "C"),
        "internal_design_gage_pressure": (8.0, "bar"),
    }
    for _ in range(12):
        submittable = state["progress"].get("submittable_parameters") or []
        ask = (state.get("current_ask") or {}).get("parameter_id")
        if ask == "nominal_pipe_size":
            break
        param = ask if ask in submittable else (submittable[0] if submittable else None)
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


def _advance_to_parameter(
    service: DesktopApiService,
    session_id: str,
    task_id: str,
    target: str,
    *,
    values: dict[str, tuple[object, str | None]] | None = None,
) -> dict:
    defaults: dict[str, tuple[object, str | None]] = {
        "straight_pipe_section": (True, None),
        "pressure_design_case": ("internal_pressure", None),
        "corrosion_allowance": (0.5, "mm"),
        "design_temperature": (200.0, "C"),
        "nominal_pipe_size": (2, None),
        "internal_design_gage_pressure": (8.0, "bar"),
        "material_grade": ("A106 B", None),
    }
    merged = {**defaults, **(values or {})}
    state = service.get_task(task_id, session_id)
    for _ in range(12):
        ask = state.get("current_ask") or {}
        parameter_id = ask.get("parameter_id")
        if parameter_id == target:
            return state
        if parameter_id not in merged:
            pytest.skip(f"unexpected parameter before {target}: {parameter_id}")
        value, unit = merged[parameter_id]
        state = service.submit_input(
            task_id,
            parameter=parameter_id,
            value=value,
            unit=unit,
            session_id=session_id,
        )
    pytest.fail(f"did not reach {target}")


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
    assert "nominal_pipe_size" in submittable
    assert state["progress"]["current_step_id"] == "nominal_pipe_size"

    timeline = {step["id"]: step["status"] for step in state["progress"]["timeline"]}
    assert timeline["nominal_pipe_size"] == "active"
    assert timeline.get("design_temperature") in {"done", "pending"}


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
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]
    state = _advance_to_parameter(service, session_id, task_id, "material_grade")

    current_ask = state.get("current_ask")
    assert current_ask is not None
    assert current_ask["parameter_id"] == "material_grade"

    submittable = state["progress"].get("submittable_parameters") or []
    assert "material_grade" in submittable
    assert state["progress"]["current_step_id"] == "material_grade"

    timeline = {step["id"]: step["status"] for step in state["progress"]["timeline"]}
    assert "nominal_pipe_size" in timeline
    assert "outside_diameter" in timeline
    assert timeline["nominal_pipe_size"] == "done"
    assert timeline["outside_diameter"] in {"done", "pending"}
    assert timeline["material_grade"] == "active"
    assert timeline.get("design_temperature") in {"done", "pending"}


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
            "pressure_design_case",
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
    state = _advance_to_parameter(
        service,
        session_id,
        task_id,
        "internal_design_gage_pressure",
    )

    current_ask = state.get("current_ask") or {}
    assert current_ask.get("parameter_id") == "internal_design_gage_pressure"

    timeline = {
        step["id"]: step["status"]
        for step in state["progress"]["timeline"]
        if step["id"] not in {"thickness", "report"}
    }
    assert timeline.get("internal_design_gage_pressure") == "active"
    assert timeline.get("nominal_pipe_size") == "pending"
    assert timeline.get("material_grade") == "pending"


def _timeline_input_ids(state: dict) -> list[str]:
    return [
        step["id"]
        for step in state["progress"]["timeline"]
        if step["id"] not in {"thickness", "report"}
    ]


def _assert_timeline_follows_collection_field_order(
    *,
    timeline_ids: list[str],
    collection_field_order: list[str],
) -> None:
    """Nav-listed fields keep presentation order; extras may append after."""
    nav_positions = {
        field: index for index, field in enumerate(collection_field_order)
    }
    nav_timeline = [step_id for step_id in timeline_ids if step_id in nav_positions]
    expected_nav = sorted(nav_timeline, key=lambda step_id: nav_positions[step_id])
    assert nav_timeline == expected_nav


def test_timeline_order_follows_collection_field_order_not_planner_ask_order(
    tmp_path: Path,
    project_root: Path,
) -> None:
    """Timeline row order follows collection_field_order; active row follows current_ask."""
    from engine.navigation import collection_step_order
    from engine.state.goal_projection import planning_projection

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

    current_ask = state.get("current_ask") or {}
    assert current_ask.get("kind") == "input"
    assert current_ask.get("parameter_id") == "nominal_pipe_size"

    timeline = state["progress"]["timeline"]
    active_steps = [
        step
        for step in timeline
        if step.get("status") == "active" and step["id"] not in {"thickness", "report"}
    ]
    assert active_steps
    assert active_steps[0]["id"] == "nominal_pipe_size"
    assert state["progress"]["current_step_id"] == "nominal_pipe_size"

    input_ids = _timeline_input_ids(state)
    store = service._store_for(session_id)
    manager = store.load_state_manager()
    task = manager.get_task(state["task_id"])
    reader = service._reader()
    planning = planning_projection(task)
    collection_field_order = list(
        task.outputs.get("collection_field_order")
        or collection_step_order(task, planning, reader=reader)
    )
    _assert_timeline_follows_collection_field_order(
        timeline_ids=input_ids,
        collection_field_order=collection_field_order,
    )

    assert "design_temperature" in input_ids
    assert "nominal_pipe_size" in input_ids
    assert input_ids.index("design_temperature") < input_ids.index("nominal_pipe_size")
    assert input_ids.index("outside_diameter") < input_ids.index("design_temperature")


_GENERIC_FALLBACK = "Complete the fields below to continue."


def _assert_active_input_prompt(state: dict) -> None:
    current_ask = state.get("current_ask") or {}
    assert current_ask.get("kind") == "input"
    parameter_id = current_ask.get("parameter_id")
    assert parameter_id
    prompt = str(current_ask.get("prompt") or "").strip()
    assert prompt
    assert _GENERIC_FALLBACK not in prompt


def test_fresh_pipe_wall_prompt_is_contextual_not_generic(
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

    _assert_active_input_prompt(state)
    assert state["current_ask"]["parameter_id"] == "straight_pipe_section"
    prompt = str(state["current_ask"]["prompt"])
    assert "straight pipe" in prompt.lower()
    assert "1." in prompt


def test_pressure_design_case_prompt_after_straight_pipe_is_numbered(
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
    state = service.submit_input(
        task_id,
        parameter="straight_pipe_section",
        value=True,
        unit=None,
        session_id=session_id,
    )

    _assert_active_input_prompt(state)
    assert state["current_ask"]["parameter_id"] == "pressure_design_case"
    prompt = str(state["current_ask"]["prompt"])
    assert "304.1.2" in prompt
    assert "304.1.3" in prompt
    assert "1." in prompt


def test_internal_pressure_prompt_includes_unit_examples(
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
    state = _advance_to_parameter(
        service,
        session_id,
        task_id,
        "internal_design_gage_pressure",
    )

    _assert_active_input_prompt(state)
    prompt = str(state["current_ask"]["prompt"]).lower()
    assert "pressure" in prompt
    assert "psi" in prompt or "bar" in prompt or "equation" in prompt


def test_material_grade_prompt_explains_allowable_stress_lookup(
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
    state = _advance_to_parameter(
        service,
        session_id,
        task_id,
        "material_grade",
    )

    _assert_active_input_prompt(state)
    assert state["current_ask"]["parameter_id"] == "material_grade"
    prompt = str(state["current_ask"]["prompt"]).lower()
    assert "allowable stress" in prompt or "material" in prompt
