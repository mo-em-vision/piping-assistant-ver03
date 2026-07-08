"""Tests for dynamic pipe-wall workflow timeline helpers."""

from __future__ import annotations

from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus

from api.workflow_timeline import revealed_pipe_wall_input_ids, submittable_parameter_ids
from engine.state.goal_projection import planning_projection
from tests.helpers.facts import fact_get_value, legacy_input, set_fact_from_input
from tests.helpers.goals import task_with_planning
from models.fact import SourceType, ValidationStatus


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
    assert planning.get("current_phase") == "definition_equation_completion"

    ask = build_current_ask(task, planning, reader=reader)
    assert ask is not None
    assert ask["kind"] == "input"
    assert ask["parameter_id"] == "corrosion_allowance"


def test_ready_phase_allows_execution_with_empty_goal_children(project_root) -> None:
    """After pre-execution inputs, READY phase must run thickness calc even when child goals are cleared."""
    from api.workflow_bootstrap import refresh_task_planning, task_ready_for_execution
    from engine.reference.standards_reader import StandardsReader

    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    manager = TaskStateManager()
    task = manager.create_task("ready-empty-children", status=TaskStatus.AWAITING_INPUT)
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
        ("corrosion_allowance", 0.5, "mm"),
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
    task.outputs = {"workflow": "pipe_wall_thickness_design", "selected_root": "pipe_wall_thickness_design"}
    refresh_task_planning(task, reader, propose_defaults=False)

    planning = planning_projection(task)
    assert planning.get("current_phase") == "ready"
    roots = task.goal_store.roots()
    assert roots
    assert not task.goal_store.children(roots[0].id)

    assert task_ready_for_execution(task) is True
