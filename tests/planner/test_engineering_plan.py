"""Tests for normalized engineering plan output (pipe wall thickness)."""

from __future__ import annotations

from pathlib import Path

from api.serializers import task_state
from engine.planner.engineering_plan_builder import build_pipe_wall_engineering_plan
from engine.planner.goal_builder import build_goal_tree
from engine.planner.plan_inspector import build_engineering_plan_view, build_planner_inspector_summary
from engine.planner.plan_validation import validate_engineering_plan
from engine.planner.tools import GraphTools
from engine.reference.standards_reader import StandardsReader
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus
from tests.acceptance.helpers import (
    internal_pressure_assumption,
    straight_section_assumption,
)


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def _task_with_gates_satisfied(state: TaskStateManager) -> tuple:
    task = state.create_task("eng-plan-pwt", status=TaskStatus.AWAITING_INPUT)
    for inp in (straight_section_assumption(), internal_pressure_assumption()):
        state.store_fact(
            task.task_id,
            fact_from_engineering_input(
                inp,
                task_id=task.task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
        )
    task = state.get_task(task.task_id)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return state, task


def _fresh_pipe_wall_task(state: TaskStateManager | None = None):
    manager = state or TaskStateManager()
    task = manager.create_task("eng-plan-fresh-pwt", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return manager, task


def _phase_statuses(plan) -> dict[str, str]:
    return {phase.id: phase.status for phase in plan.phases}


def test_fresh_pipe_wall_phase_statuses_single_active_phase() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_pipe_wall_engineering_plan(task)
    validation = validate_engineering_plan(plan)

    assert validation.valid, validation.errors
    statuses = _phase_statuses(plan)
    assert statuses["expansion_assumptions"] == "active"
    assert statuses["path_decisions"] == "pending"
    assert statuses["parameter_gathering"] == "pending"
    assert statuses["coefficient_resolution"] == "blocked"
    assert statuses["equation_execution"] == "blocked"
    assert statuses["validation"] == "blocked"
    assert statuses["reporting"] == "blocked"
    assert sum(1 for status in statuses.values() if status == "active") == 1


def test_straight_pipe_resolved_only_path_decisions_active() -> None:
    state, task = _fresh_pipe_wall_task()
    state.store_fact(
        task.task_id,
        fact_from_engineering_input(
            straight_section_assumption(),
            task_id=task.task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    task = state.get_task(task.task_id)
    plan = build_pipe_wall_engineering_plan(task, existing_inputs=dict(task.fact_store.active_facts()))
    validation = validate_engineering_plan(plan)

    assert validation.valid, validation.errors
    statuses = _phase_statuses(plan)
    assert statuses["expansion_assumptions"] == "complete"
    assert statuses["path_decisions"] == "active"
    assert statuses["parameter_gathering"] == "pending"
    assert statuses["coefficient_resolution"] == "blocked"
    assert sum(1 for status in statuses.values() if status == "active") == 1


def test_gates_resolved_parameter_gathering_becomes_active() -> None:
    state, task = _task_with_gates_satisfied(TaskStateManager())
    plan = build_pipe_wall_engineering_plan(task, existing_inputs=dict(task.fact_store.active_facts()))
    validation = validate_engineering_plan(plan)

    assert validation.valid, validation.errors
    statuses = _phase_statuses(plan)
    assert statuses["expansion_assumptions"] == "complete"
    assert statuses["path_decisions"] == "complete"
    assert statuses["parameter_gathering"] == "active"
    assert statuses["coefficient_resolution"] == "blocked"
    assert sum(1 for status in statuses.values() if status == "active") == 1


def test_fresh_pipe_wall_internal_pressure_requirements_are_conditional() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_pipe_wall_engineering_plan(task)

    internal_pressure = plan.requirements["REQ-internal_design_gage_pressure"]
    assert internal_pressure.activation_status == "conditional"
    assert internal_pressure.activation_condition is not None
    assert internal_pressure.activation_condition.field == "pressure_loading"
    assert internal_pressure.activation_condition.value == "internal_pressure"

    lookup = plan.requirements["REQ-allowable_stress_lookup"]
    assert lookup.activation_status == "conditional"

    assert plan.root_goal.blocked_by == ["REQ-straight_pipe_section", "REQ-pressure_loading"]
    assert "REQ-internal_design_gage_pressure" in plan.root_goal.provisional_blocked_by
    assert "REQ-diameter_resolution" in plan.root_goal.provisional_blocked_by
    assert plan.input_strategy is not None
    assert "internal_design_gage_pressure" not in plan.input_strategy.next_fields


def test_internal_pressure_branch_activates_downstream_requirements() -> None:
    state, task = _task_with_gates_satisfied(TaskStateManager())
    plan = build_pipe_wall_engineering_plan(task, existing_inputs=dict(task.fact_store.active_facts()))

    internal_pressure = plan.requirements["REQ-internal_design_gage_pressure"]
    assert internal_pressure.activation_status == "active"
    assert internal_pressure.status == "missing"
    assert "REQ-internal_design_gage_pressure" in plan.root_goal.blocked_by
    assert plan.input_strategy is not None
    assert plan.input_strategy.next_fields == ["internal_design_gage_pressure"]


def test_external_pressure_branch_marks_internal_requirements_not_applicable() -> None:
    state, task = _fresh_pipe_wall_task()
    state.store_fact(
        task.task_id,
        fact_from_engineering_input(
            straight_section_assumption(),
            task_id=task.task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    state.store_fact(
        task.task_id,
        fact_from_engineering_input(
            EngineeringInput(
                "pressure_loading",
                "external_pressure",
                "dimensionless",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            task_id=task.task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    task = state.get_task(task.task_id)
    plan = build_pipe_wall_engineering_plan(task, existing_inputs=dict(task.fact_store.active_facts()))

    internal_pressure = plan.requirements["REQ-internal_design_gage_pressure"]
    assert internal_pressure.activation_status == "not_applicable"
    assert internal_pressure.status == "not_applicable"
    assert plan.requirements["REQ-required_wall_thickness"].activation_status == "not_applicable"
    assert "REQ-internal_design_gage_pressure" not in plan.root_goal.blocked_by
    assert "REQ-internal_design_gage_pressure" not in plan.root_goal.provisional_blocked_by


def test_planner_graph_summary_derived_from_engineering_plan() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_pipe_wall_engineering_plan(task)
    summary = build_planner_inspector_summary(plan)
    graph_summary = summary["planner_graph_summary"]

    assert graph_summary["selected_subgraph_count"] == len(plan.graph.selected_subgraph_node_ids)
    assert graph_summary["expanded_node_count"] == len(plan.graph.expanded_node_ids)
    assert graph_summary["dependency_edge_count"] == len(plan.dependencies)
    assert graph_summary["branch_decision_count"] == len(plan.graph.selected_branch_decisions)
    assert graph_summary["dependency_edge_count"] > 0


def test_temperature_coefficient_lookup_summary_includes_metallurgical_group() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_pipe_wall_engineering_plan(task)
    summary = build_planner_inspector_summary(plan)

    y_lookup = plan.requirements["REQ-temperature_coefficient_Y_lookup"]
    assert y_lookup.depends_on == ["REQ-metallurgical_group_lookup", "REQ-design_temperature"]

    derived = summary["derived_or_lookup_values"]
    y_entry = next(item for item in derived if item["field"] == "temperature_coefficient_Y")
    assert y_entry["method"] == "lookup"
    assert y_entry["depends_on"] == ["metallurgical_group", "design_temperature"]
    assert y_entry["status"] == y_lookup.status

    metallurgical_entry = next(item for item in derived if item["field"] == "metallurgical_group")
    assert metallurgical_entry["depends_on"] == ["material_grade"]


def test_fresh_pipe_wall_planner_inspector_summary_single_next_input() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_pipe_wall_engineering_plan(task)
    summary = build_planner_inspector_summary(plan)

    assert summary["next_input"] is not None
    assert summary["next_input"]["field"] == "straight_pipe_section"
    assert summary["next_input"]["phase"] == "expansion_assumptions"
    assert "next_required_inputs" not in summary

    outstanding = summary["outstanding_required_inputs"]
    outstanding_fields = [item["field"] for item in outstanding]
    assert outstanding_fields[0] == "straight_pipe_section"
    assert "pressure_loading" in outstanding_fields
    assert "internal_design_gage_pressure" in outstanding_fields

    internal_pressure_entry = next(
        item for item in outstanding if item["field"] == "internal_design_gage_pressure"
    )
    assert internal_pressure_entry["activation_status"] == "conditional"
    assert internal_pressure_entry["phase"] == "parameter_gathering"


def test_fresh_pipe_wall_input_strategy_asks_expansion_assumption_first() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_pipe_wall_engineering_plan(task)
    validation = validate_engineering_plan(plan)

    assert validation.valid, validation.errors
    assert plan.input_strategy is not None
    assert plan.input_strategy.current_phase == "expansion_assumptions"
    assert plan.input_strategy.next_fields == ["straight_pipe_section"]
    assert "pressure_loading" not in plan.input_strategy.next_fields


def test_straight_pipe_resolved_advances_to_path_decisions() -> None:
    state, task = _fresh_pipe_wall_task()
    state.store_fact(
        task.task_id,
        fact_from_engineering_input(
            straight_section_assumption(),
            task_id=task.task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    task = state.get_task(task.task_id)
    plan = build_pipe_wall_engineering_plan(task, existing_inputs=dict(task.fact_store.active_facts()))
    validation = validate_engineering_plan(plan)

    assert validation.valid, validation.errors
    assert plan.input_strategy is not None
    assert plan.input_strategy.current_phase == "path_decisions"
    assert plan.input_strategy.next_fields == ["pressure_loading"]


def test_pipe_wall_diameter_resolution_dependency_edges() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_pipe_wall_engineering_plan(task)
    validation = validate_engineering_plan(plan)

    assert validation.valid, validation.errors
    edges = {(edge.from_id, edge.to_id, edge.type) for edge in plan.dependencies}
    assert ("REQ-nominal_pipe_size", "REQ-outside_diameter_lookup", "lookup_input") in edges
    assert ("REQ-outside_diameter_lookup", "REQ-diameter_resolution", "resolves") in edges
    assert ("ALT-nps-lookup", "REQ-nominal_pipe_size", "activates") in edges
    assert ("ALT-nps-lookup", "REQ-outside_diameter_lookup", "activates") in edges
    assert ("REQ-diameter_resolution", "REQ-outside_diameter_lookup", "lookup_input") not in edges

    diameter = plan.requirements["REQ-diameter_resolution"]
    alt_ids = {alt.id for alt in diameter.alternatives or []}
    assert "ALT-direct-outside-diameter" in alt_ids
    assert "ALT-nps-lookup" in alt_ids


def test_pipe_wall_initial_engineering_plan() -> None:
    state, task = _task_with_gates_satisfied(TaskStateManager())
    reader = _reader()
    graph = GraphTools(reader)
    preview = graph.preview_plan(
        task_id=task.task_id,
        root_id="pipe_wall_thickness_design",
        inputs=dict(task.fact_store.active_facts()),
    )

    plan = build_pipe_wall_engineering_plan(task, preview=preview)
    validation = validate_engineering_plan(plan)

    assert validation.valid, validation.errors
    assert plan.root_goal.key == "calculate-minimum-required-thickness"
    assert plan.root_goal.target_parameter == "PARAM-minimum-required-thickness"

    blocked = set(plan.root_goal.blocked_by)
    assert "REQ-internal_design_gage_pressure" in blocked
    assert "REQ-diameter_resolution" in blocked
    assert "REQ-material_grade" in blocked
    assert "REQ-design_temperature" in blocked
    assert "REQ-pipe_construction_type" in blocked
    assert "REQ-corrosion_allowance" in blocked
    assert "REQ-outside_diameter" not in blocked
    assert "REQ-nominal_pipe_size" not in blocked

    diameter = plan.requirements["REQ-diameter_resolution"]
    assert diameter.alternatives
    alt_ids = {alt.id for alt in diameter.alternatives}
    assert "ALT-direct-outside-diameter" in alt_ids
    assert "ALT-nps-lookup" in alt_ids

    assert plan.graph.selected_subgraph_node_ids is not None
    assert len(plan.dependencies) > 0

    for req in plan.requirements.values():
        if req.question_spec:
            assert req.question_spec.field
            assert req.question_spec.label
            assert req.question_spec.expected_value_class
            assert req.question_spec.ask_policy
            assert "To continue the calculation" not in req.question_spec.label

    summary = build_planner_inspector_summary(plan)
    assert summary["root_goal"]["title"] == "Calculate minimum required pipe wall thickness"
    assert summary["root_goal"]["target_field"] == "minimum_required_thickness"
    assert summary["next_input"] is not None
    assert summary["next_input"]["field"] == "internal_design_gage_pressure"
    outstanding_fields = [item["field"] for item in summary["outstanding_required_inputs"]]
    assert "internal_design_gage_pressure" in outstanding_fields
    assert "diameter_input_mode" in outstanding_fields
    assert summary["alternatives"]
    assert summary["planner_graph_summary"]["dependency_edge_count"] > 0

    view = build_engineering_plan_view(plan)
    assert view["overview"]["goal"] == "Calculate minimum required pipe wall thickness"
    assert view["phases"]
    first_phase = view["phases"][0]
    assert "requirements" in first_phase
    assert first_phase["requirements"][0]["label"]
    assert "REQ-" not in first_phase["requirements"][0]["label"]
    assert view["overview"]["next_input"]
    assert "field" in view["overview"]["next_input"]


def test_goal_tree_from_engineering_plan_no_selected_nodes_on_root() -> None:
    state, task = _task_with_gates_satisfied(TaskStateManager())
    reader = _reader()
    build_goal_tree(task, reader)

    roots = task.goal_store.roots()
    assert roots
    root = roots[0]
    assert root.key == "calculate-minimum-required-thickness"
    assert "selected_nodes" not in root.metadata
    assert "To continue the calculation" not in root.name

    view = task.outputs.get("engineering_plan_view")
    assert isinstance(view, dict)
    assert view.get("overview", {}).get("goal")

    plan = task.outputs.get("engineering_plan")
    assert isinstance(plan, dict)
    assert plan.get("graph", {}).get("selected_subgraph_node_ids") is not None

    child_names = [g.name for g in task.goal_store.children(root.id)]
    assert not any("To continue the calculation" in name for name in child_names)


def test_coefficients_are_lookup_not_user_input() -> None:
    state, task = _task_with_gates_satisfied(TaskStateManager())
    reader = _reader()
    plan = build_pipe_wall_engineering_plan(task)

    for field in (
        "allowable_stress",
        "weld_joint_efficiency",
        "temperature_coefficient_Y",
        "weld_strength_reduction_factor_W",
    ):
        lookup_reqs = [
            req
            for req in plan.requirements.values()
            if req.field == field or field in req.id
        ]
        assert lookup_reqs
        assert all(req.requirement_class != "user_input" for req in lookup_reqs)


def test_nps_path_activates_lookup_requirement() -> None:
    state, task = _task_with_gates_satisfied(TaskStateManager())
    state.store_fact(
        task.task_id,
        fact_from_engineering_input(
            EngineeringInput(
                "d_input_mode",
                "nps_lookup",
                "dimensionless",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            task_id=task.task_id,
            workflow_id="pipe_wall_thickness_design",
        ),
    )
    task = state.get_task(task.task_id)
    plan = build_pipe_wall_engineering_plan(task, existing_inputs=dict(task.fact_store.active_facts()))

    nps = plan.requirements["REQ-nominal_pipe_size"]
    od_lookup = plan.requirements["REQ-outside_diameter_lookup"]
    assert nps.status == "missing"
    assert od_lookup.status in {"blocked", "ready"}
    assert od_lookup.requirement_class == "table_lookup"


def test_task_state_exposes_readable_engineering_plan() -> None:
    state, task = _task_with_gates_satisfied(TaskStateManager())
    reader = _reader()
    build_goal_tree(task, reader)
    state.replace_task(task.task_id, task)

    payload = task_state(task, state, reader=reader)
    plan = payload.get("engineering_plan")
    assert isinstance(plan, dict)
    assert "overview" in plan
    assert "phases" in plan
    assert "requirements" not in plan  # raw keyed dict
    assert "REQ-" not in str(plan)
    assert "engineering_plan" not in payload.get("outputs", {})
