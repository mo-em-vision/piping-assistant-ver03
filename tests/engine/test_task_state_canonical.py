"""Canonical task-state layer tests for pipe wall thickness awaiting-input."""

from __future__ import annotations

from api.serializers import task_state
from api.workflow_bootstrap import refresh_task_planning
from api.workflow_timeline import submittable_parameter_ids
from engine.reference.standards_reader import StandardsReader
from engine.state.goal_projection import planning_projection
from engine.state.state_manager import TaskStateManager
from engine.state.task_state_canonical import (
    build_canonical_task_state,
    build_task_inspector_summary,
    validate_task_state_invariants,
)
from models.input import InputSource, InputStatus
from models.task import TaskStatus
from tests.helpers.facts import legacy_input, set_fact_from_input
from tests.helpers.goals import task_with_planning


def _pipe_wall_post_calc_task(manager: TaskStateManager, task_id: str, *, project_root):
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    task = manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
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
        "allowable_stress": 195_100_000.0,
        "allowable_stress_unit": "Pa",
        "S": 195_100_000.0,
        "selected_nodes": ["304.1.1-a", "304.1.2-a", "PARAM-corrosion-allowance"],
        "graph_input_order": ["internal_design_gage_pressure", "corrosion_allowance"],
        "path_decision": {
            "field": "pressure_loading",
            "value": "internal_pressure",
            "selected_node": "304.1.2-a",
        },
        "_execution_trace": [{"node_id": "304.1.2-a", "trace": {"calculation": {"steps": []}}}],
    }
    task.active_nodes = [
        "304.1.1-a",
        "304.1.2-a",
        "PARAM-weld-strength-reduction-factor-w",
        "PARAM-corrosion-allowance",
    ]
    manager.replace_task(task.task_id, task)
    refresh_task_planning(task, reader, propose_defaults=False)
    manager.replace_task(task.task_id, task)
    return manager.get_task(task.task_id), reader


def test_canonical_awaiting_corrosion_allowance(project_root) -> None:
    manager = TaskStateManager()
    task, reader = _pipe_wall_post_calc_task(manager, "canonical-corrosion-wait", project_root=project_root)
    planning = planning_projection(task)

    canonical = build_canonical_task_state(task, manager, planning=planning, reader=reader)
    violations = validate_task_state_invariants(canonical)

    assert canonical["task"]["status"] == "awaiting_input"
    blocker = canonical["execution"]["current_blocker"]
    assert blocker["type"] == "missing_input"
    assert blocker["field"] == "corrosion_allowance"
    assert blocker["parameter_node_id"] == "PARAM-corrosion-allowance"

    progress = canonical["progress"]
    assert "corrosion_allowance" in progress["missing_inputs"]
    assert "corrosion_allowance" in progress["submittable_parameters"]
    assert progress["current_step_id"] == "corrosion_allowance"

    graph = canonical["graph"]
    assert "PARAM-corrosion-allowance" in graph["active_node_ids"]
    assert graph["active_node_ids"] != graph["expanded_node_ids"]
    assert "PARAM-weld-strength-reduction-factor-w" not in graph["active_node_ids"]
    assert canonical["execution"]["current_execution_node_id"] == "PARAM-corrosion-allowance"

    values = canonical["values"]
    assert "S" not in values
    assert "allowable_stress_unit" not in values
    assert "selected_nodes" not in values
    assert "graph_input_order" not in values
    stress = values.get("allowable_stress")
    assert isinstance(stress, dict)
    assert stress.get("symbol") == "S"
    assert isinstance(stress.get("value"), (int, float))
    assert stress.get("unit") == "Pa"

    assert "timeline" not in progress
    assert violations == []


def test_task_state_api_includes_canonical_and_inspector_summary(project_root) -> None:
    manager = TaskStateManager()
    task, reader = _pipe_wall_post_calc_task(manager, "canonical-api-shape", project_root=project_root)

    state = task_state(task, manager, reader=reader, projection_mode="full")
    canonical = state["canonical"]
    summary = state["inspector_summary"]

    assert canonical["execution"]["current_blocker"]["field"] == "corrosion_allowance"
    assert "corrosion_allowance" in state["progress"]["missing_inputs"]
    assert "corrosion_allowance" in state["progress"]["submittable_parameters"]
    assert summary["missing_inputs"] == ["corrosion_allowance"]
    assert summary["current_blocker"]["parameter_node_id"] == "PARAM-corrosion-allowance"
    assert summary["execution_graph_summary"]["active_count"] == 1


def test_workflow_state_variable_values_exclude_graph_metadata(project_root) -> None:
    manager = TaskStateManager()
    task, reader = _pipe_wall_post_calc_task(
        manager,
        "canonical-workflow-state",
        project_root=project_root,
    )

    from api.json_encoding import json_safe

    workflow_state = json_safe(manager.get_workflow_state(task.task_id, reader=reader))
    variable_values = workflow_state["variable_values"]

    for key in (
        "selected_nodes",
        "graph_input_order",
        "graph_step_titles",
        "collection_field_order",
        "phase_allowed_fields",
        "path_decision",
        "timeline_input_order",
        "S",
        "allowable_stress_unit",
    ):
        assert key not in variable_values


def test_inspector_summary_resolved_inputs(project_root) -> None:
    manager = TaskStateManager()
    task, reader = _pipe_wall_post_calc_task(
        manager,
        "canonical-inspector-summary",
        project_root=project_root,
    )
    canonical = build_canonical_task_state(task, manager, reader=reader)
    summary = build_task_inspector_summary(canonical)

    fields = {item["field"] for item in summary["resolved_inputs"]}
    assert "internal_design_gage_pressure" in fields
    assert "allowable_stress" in fields
    stress = next(item for item in summary["resolved_inputs"] if item["field"] == "allowable_stress")
    assert stress["symbol"] == "S"
    assert summary["selected_branch_decisions"]
    assert summary["selected_branch_decisions"][0]["selected_node"] == "304.1.2-a"


def test_submittable_still_resolves_for_corrosion(project_root) -> None:
    manager = TaskStateManager()
    task, _reader = _pipe_wall_post_calc_task(
        manager,
        "canonical-submittable",
        project_root=project_root,
    )
    planning = planning_projection(task)
    assert submittable_parameter_ids(task, planning) == ["corrosion_allowance"]
