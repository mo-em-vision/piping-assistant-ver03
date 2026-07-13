"""Tests for dynamic pipe-wall workflow timeline helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.desktop_service import DesktopApiService
from config.loader import CLIConfig
from engine.state.goal_projection import planning_projection
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus

from api.workflow_timeline import revealed_pipe_wall_input_ids, submittable_parameter_ids
from tests.api.conftest import api_session_id
from tests.helpers.facts import fact_get_value, legacy_input, set_fact_from_input
from tests.helpers.goals import task_with_planning
from models.fact import SourceType, ValidationStatus

_PIPE_WALL_PHASE_ORDER: tuple[str, ...] = (
    "expansion_assumptions",
    "path_decisions",
    "parameter_gathering",
    "coefficient_resolution",
    "definition_equation_completion",
    "ready",
    "equation_execution",
    "reporting",
)

_NEVER_USER_SUBMITTABLE: frozenset[str] = frozenset(
    {
        "allowable_stress",
        "weld_joint_efficiency",
        "weld_joint_strength_reduction_factor_W",
        "temperature_coefficient_Y",
        "metallurgical_group",
        "outside_diameter",
        "minimum_required_thickness",
        "required_thickness",
        "t",
        "t_m",
    }
)

_PIPE_WALL_INTERNAL_PRESSURE_SUBMISSIONS: dict[str, tuple[object, str | None]] = {
    "straight_pipe_section": (True, None),
    "pressure_loading": ("internal_pressure", None),
    "internal_design_gage_pressure": (8.0, "bar"),
    "nominal_pipe_size": ("6", None),
    "material_grade": ("SA-106B", None),
    "design_temperature": (38.0, "C"),
    "pipe_construction_type": ("Seamless pipe", None),
    "corrosion_allowance": (0.5, "mm"),
}


def _desktop_service(tmp_path: Path, project_root: Path) -> DesktopApiService:
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


def _api_current_phase(state: dict) -> str:
    execution_context = state.get("execution_context") or {}
    nested = execution_context.get("state") or {}
    return str(nested.get("current_phase") or "")


def _current_phase_allowed_fields(planning: dict) -> set[str]:
    current_phase = str(planning.get("current_phase") or "")
    if not current_phase:
        return set()
    allowed: set[str] = set()
    phase_missing = planning.get("phase_missing") or {}
    phase_allowed = planning.get("phase_allowed_fields") or {}
    if isinstance(phase_missing, dict):
        allowed.update(str(item) for item in (phase_missing.get(current_phase) or []))
    if isinstance(phase_allowed, dict):
        allowed.update(str(item) for item in (phase_allowed.get(current_phase) or []))
    return allowed


def _future_phase_fields(planning: dict) -> set[str]:
    current_phase = str(planning.get("current_phase") or "")
    phase_missing = planning.get("phase_missing") or {}
    phase_allowed = planning.get("phase_allowed_fields") or {}
    if not current_phase:
        return set()
    try:
        current_index = _PIPE_WALL_PHASE_ORDER.index(current_phase)
    except ValueError:
        return set()
    future: set[str] = set()
    for phase_id in _PIPE_WALL_PHASE_ORDER[current_index + 1 :]:
        if isinstance(phase_missing, dict):
            future.update(str(item) for item in (phase_missing.get(phase_id) or []))
        if isinstance(phase_allowed, dict):
            future.update(str(item) for item in (phase_allowed.get(phase_id) or []))
    return future


def _assert_live_submittable_phase_contract(state: dict, planning: dict) -> None:
    current_phase = _api_current_phase(state)
    assert current_phase == str(planning.get("current_phase") or "")

    submittable = list(state.get("progress", {}).get("submittable_parameters") or [])
    current_allowed = _current_phase_allowed_fields(planning)
    exclusive_future_fields = _future_phase_fields(planning) - current_allowed

    assert not (set(submittable) & exclusive_future_fields), (
        f"future-phase-only parameters exposed during {current_phase}: "
        f"{sorted(set(submittable) & exclusive_future_fields)}"
    )
    assert not (set(submittable) & _NEVER_USER_SUBMITTABLE), (
        f"lookup/output parameters must not be submittable during {current_phase}: {submittable}"
    )
    if submittable and current_allowed:
        assert set(submittable).issubset(current_allowed), (
            f"submittable {submittable} must stay within {current_phase} "
            f"phase_missing {sorted(current_allowed)}"
        )

    current_ask = state.get("current_ask") or {}
    if current_ask.get("kind") == "input" and submittable:
        ask_id = current_ask.get("parameter_id")
        assert ask_id in submittable, (
            f"current_ask {ask_id!r} must be one of submittable_parameters {submittable}"
        )


def _planning_for_task(
    service: DesktopApiService,
    session_id: str,
    task_id: str,
) -> dict:
    manager = service._store_for(session_id).load_state_manager()
    task = manager.get_task(task_id)
    return planning_projection(task)


def _submit_pipe_wall_parameters(
    service: DesktopApiService,
    session_id: str,
    task_id: str,
    parameter_ids: list[str],
) -> dict:
    state = service.get_task(task_id, session_id)
    for parameter_id in parameter_ids:
        value, unit = _PIPE_WALL_INTERNAL_PRESSURE_SUBMISSIONS[parameter_id]
        state = service.submit_input(
            task_id,
            parameter=parameter_id,
            value=value,
            unit=unit,
            session_id=session_id,
        )
    return state


def _coefficient_phase_missing(planning: dict) -> list[str]:
    phase_missing = planning.get("phase_missing") or {}
    if not isinstance(phase_missing, dict):
        return []
    return [str(item) for item in (phase_missing.get("coefficient_resolution") or [])]


def test_coefficient_phase_current_ask_matches_phase_missing_only(
    tmp_path: Path,
    project_root: Path,
) -> None:
    """At coefficient_resolution, current_ask and submittable_parameters stay in that phase bucket."""
    service = _desktop_service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    state = _submit_pipe_wall_parameters(
        service,
        session_id,
        task_id,
        [
            "straight_pipe_section",
            "pressure_loading",
            "internal_design_gage_pressure",
            "nominal_pipe_size",
            "material_grade",
            "design_temperature",
            "pipe_construction_type",
        ],
    )

    assert _api_current_phase(state) == "coefficient_resolution"

    planning = _planning_for_task(service, session_id, task_id)
    assert planning.get("current_phase") == "coefficient_resolution"

    coeff_missing = _coefficient_phase_missing(planning)
    assert coeff_missing, "coefficient_resolution must expose pending fields"

    phase_missing = planning.get("phase_missing") or {}
    other_phase_fields = {
        str(field)
        for phase_id, fields in phase_missing.items()
        if phase_id != "coefficient_resolution" and isinstance(fields, list)
        for field in fields
    }

    current_ask = state.get("current_ask") or {}
    assert current_ask.get("kind") == "input"
    ask_id = current_ask.get("parameter_id")
    assert isinstance(ask_id, str) and ask_id
    assert ask_id in coeff_missing
    assert ask_id not in other_phase_fields
    assert ask_id not in _NEVER_USER_SUBMITTABLE

    submittable = list(state.get("progress", {}).get("submittable_parameters") or [])
    assert submittable
    assert set(submittable).issubset(set(coeff_missing))
    assert not (set(submittable) & other_phase_fields)
    assert not (set(submittable) & _NEVER_USER_SUBMITTABLE)
    assert ask_id in submittable


def test_live_submit_submittable_parameters_remain_phase_scoped(
    tmp_path: Path,
    project_root: Path,
) -> None:
    """Sequential API submits: submittable_parameters and current_ask stay within the active phase."""
    service = _desktop_service(tmp_path, project_root)
    session_id = api_session_id(service)
    state = service.create_task("pipe_wall_thickness_design", session_id)
    task_id = state["task_id"]

    planning = _planning_for_task(service, session_id, task_id)
    _assert_live_submittable_phase_contract(state, planning)
    assert _api_current_phase(state) == "expansion_assumptions"
    assert state["progress"]["submittable_parameters"] == ["straight_pipe_section"]

    phase_after_submit: dict[str, str] = {
        "straight_pipe_section": "path_decisions",
        "pressure_loading": "parameter_gathering",
        "pipe_construction_type": "coefficient_resolution",
    }

    for _ in range(len(_PIPE_WALL_INTERNAL_PRESSURE_SUBMISSIONS) + 2):
        if state.get("status") == "completed":
            break

        planning = _planning_for_task(service, session_id, task_id)
        _assert_live_submittable_phase_contract(state, planning)

        submittable = state.get("progress", {}).get("submittable_parameters") or []
        if not submittable:
            break

        current_ask = state.get("current_ask") or {}
        parameter_id = current_ask.get("parameter_id")
        if parameter_id not in submittable:
            parameter_id = submittable[0]

        if parameter_id not in _PIPE_WALL_INTERNAL_PRESSURE_SUBMISSIONS:
            pytest.fail(f"unexpected submittable parameter before journey complete: {parameter_id}")

        value, unit = _PIPE_WALL_INTERNAL_PRESSURE_SUBMISSIONS[parameter_id]
        state = service.submit_input(
            task_id,
            parameter=parameter_id,
            value=value,
            unit=unit,
            session_id=session_id,
        )

        expected_phase = phase_after_submit.get(parameter_id)
        if expected_phase is not None:
            assert _api_current_phase(state) == expected_phase

    planning = _planning_for_task(service, session_id, task_id)
    _assert_live_submittable_phase_contract(state, planning)
    assert state.get("status") == "completed"
    assert _api_current_phase(state) == "ready"
    assert state["progress"]["submittable_parameters"] == []


def test_revealed_inputs_include_current_and_completed_phases() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-timeline01", status=TaskStatus.AWAITING_INPUT)
    set_fact_from_input(task, legacy_input(input_id="material_grade",
        value="SA-106B",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    set_fact_from_input(task, legacy_input(input_id="internal_design_gage_pressure",
        value=8.0,
        unit="bar",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    planning = {
        "current_phase": "parameter_gathering",
        "phase_missing": {
            "parameter_gathering": ["nominal_pipe_size"],
            "coefficient_resolution": [
                "pipe_construction_type",
            ],
        },
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

    revealed = revealed_pipe_wall_input_ids(task, planning_projection(task))
    assert revealed == [
        "internal_design_gage_pressure",
        "nominal_pipe_size",
        "material_grade",
        "outside_diameter",
    ]


def test_revealed_inputs_expand_into_coefficient_phase() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-timeline02", status=TaskStatus.AWAITING_INPUT)
    for input_id, value in (
        ("material_grade", "SA-106B"),
        ("internal_design_gage_pressure", 8.0),
        ("design_temperature", 200.0),
        ("nominal_pipe_size", "10"),
    ):
        set_fact_from_input(
            task,
            legacy_input(
                input_id=input_id,
                value=value,
                unit="dimensionless"
                if input_id in {"material_grade", "nominal_pipe_size"}
                else ("bar" if input_id == "internal_design_gage_pressure" else "C"),
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        )
    planning = {
        "current_phase": "coefficient_resolution",
        "phase_missing": {
            "coefficient_resolution": [
                "pipe_construction_type",
            ],
        },
    }
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "allowable_stress": 193.0,
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    revealed = revealed_pipe_wall_input_ids(task, planning_projection(task))
    assert "allowable_stress" in revealed
    assert "pipe_construction_type" in revealed or "joint_category" in revealed
    assert "weld_joint_efficiency" not in revealed
    assert "weld_joint_strength_reduction_factor_W" not in revealed
    assert "temperature_coefficient_Y" not in revealed


def test_submittable_parameters_remain_phase_scoped() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-timeline03", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "current_phase": "coefficient_resolution",
        "phase_missing": {
            "coefficient_resolution": ["pipe_construction_type"],
        },
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    submittable = submittable_parameter_ids(task, planning_projection(task))
    assert submittable == ["pipe_construction_type"]


def test_timeline_input_order_appends_newly_revealed_parameters() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-timeline05", status=TaskStatus.AWAITING_INPUT)
    set_fact_from_input(task, legacy_input(input_id="straight_pipe_section",
        value=True,
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    set_fact_from_input(task, legacy_input(input_id="pressure_loading",
        value="internal_pressure",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    set_fact_from_input(task, legacy_input(input_id="internal_design_gage_pressure",
        value=8.0,
        unit="bar",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    planning_early = {
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": ["nominal_pipe_size"]},
        "graph_input_order": [
            "straight_pipe_section",
            "pressure_loading",
            "internal_design_gage_pressure",
            "nominal_pipe_size",
            "material_grade",
        ],
        "collection_field_order": [
            "straight_pipe_section",
            "pressure_loading",
            "internal_design_gage_pressure",
            "nominal_pipe_size",
            "outside_diameter",
            "material_grade",
        ],
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning_early, workflow_id="pipe_wall_thickness_design")
    early = revealed_pipe_wall_input_ids(task, planning_projection(task))
    task.outputs["timeline_input_order"] = early

    set_fact_from_input(task, legacy_input(input_id="material_grade",
        value="SA-106B",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    set_fact_from_input(task, legacy_input(input_id="nominal_pipe_size",
        value="10",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    planning_late = {
        "current_phase": "coefficient_resolution",
        "phase_missing": {
            "coefficient_resolution": [
                "pipe_construction_type",
            ],
        },
        "graph_input_order": planning_early["graph_input_order"],
        "collection_field_order": [
            *planning_early["collection_field_order"],
            "pipe_construction_type",
        ],
    }
    task_with_planning(task, planning_late, workflow_id="pipe_wall_thickness_design")

    revealed = revealed_pipe_wall_input_ids(task, planning_projection(task))
    assert revealed[:4] == [
        "straight_pipe_section",
        "pressure_loading",
        "internal_design_gage_pressure",
        "nominal_pipe_size",
    ]
    assert revealed.index("material_grade") > revealed.index("nominal_pipe_size")
    assert revealed[-1:] == ["pipe_construction_type"]


def test_submittable_includes_unconfirmed_proposed_defaults_in_current_phase() -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-timeline04", status=TaskStatus.AWAITING_INPUT)
    set_fact_from_input(task, legacy_input(input_id="joint_category",
        value="seamless",
        unit="dimensionless",
        source=InputSource.DEFAULT,
        status=InputStatus.PROPOSED_DEFAULT,
        default="seamless",
        requires_confirmation=True,))
    planning = {
        "current_phase": "coefficient_resolution",
        "phase_missing": {
            "coefficient_resolution": ["pipe_construction_type"],
        },
        "graph_input_order": [
            "pipe_construction_type",
        ],
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    submittable = submittable_parameter_ids(task, planning_projection(task))
    assert submittable == ["pipe_construction_type"]


def test_submittable_includes_corrosion_after_calc_via_planner_queue(project_root) -> None:
    from api.workflow_bootstrap import refresh_task_planning
    from engine.planner.goal_navigation import build_current_ask
    from engine.reference.standards_reader import StandardsReader

    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    manager = TaskStateManager()
    task = manager.create_task("post-calc-corrosion-planner", status=TaskStatus.AWAITING_INPUT)
    inputs = [
        ("straight_pipe_section", True, None),
        ("pressure_loading", "internal_pressure", None),
        ("internal_design_gage_pressure", 8.0, "bar"),
        ("nominal_pipe_size", 6, None),
        ("outside_diameter", 168.28, "mm"),
        ("material_grade", "SA-106 B", None),
        ("design_temperature", 38.0, "C"),
        ("pipe_construction_type", "seamless", None),
        ("weld_joint_efficiency", 1.0, None),
        ("weld_joint_strength_reduction_factor_W", 1.0, None),
        ("temperature_coefficient_Y", 0.4, None),
    ]
    for iid, val, unit in inputs:
        set_fact_from_input(
            task,
            legacy_input(
                input_id=iid,
                value=val,
                unit=unit or "dimensionless",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        )
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "selected_root": "pipe_wall_thickness_design",
        "required_thickness": 3.5,
        "t": 3.5,
        "_execution_trace": [{"node_id": "304.1.2-a", "trace": {"calculation": {"steps": []}}}],
    }
    manager.replace_task(task.task_id, task)

    refresh_task_planning(task, reader, propose_defaults=False)
    manager.replace_task(task.task_id, task)
    task = manager.get_task(task.task_id)

    planning = planning_projection(task)
    submittable = submittable_parameter_ids(task, planning)
    assert submittable == ["corrosion_allowance"]
    assert planning.get("current_phase") == "coefficient_resolution"

    ask = build_current_ask(task, planning, reader=reader)
    assert ask is not None
    assert ask["kind"] == "input"
    assert ask["parameter_id"] == "corrosion_allowance"
