"""Tests for normalized engineering plan output (pipe wall thickness)."""

from __future__ import annotations

from pathlib import Path

from api.serializers import task_state
from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.goal_builder import build_goal_tree
from engine.planner.plan_inspector import build_engineering_plan_view, build_planner_inspector_summary
from engine.planner.plan_validation import validate_engineering_plan
from engine.planner.tools import GraphTools
from engine.reference.parameter_keys import param_node_id_for_input
from engine.reference.standards_reader import StandardsReader
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus
from tests.acceptance.helpers import (
    internal_pressure_assumption,
    straight_section_assumption,
)
from tests.planner.plan_contract import (
    REQ_MINIMUM_REQUIRED_THICKNESS_EQ,
    REQ_REQUIRED_WALL_THICKNESS,
    WELD_W_FIELD,
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


def _active_phases(plan) -> list:
    return [phase for phase in plan.phases if phase.status == "active"]


def test_fresh_pipe_wall_no_facts_input_strategy_and_phase_contract() -> None:
    """Fresh plan with no facts: input strategy and phase progression contract."""
    _, task = _fresh_pipe_wall_task()
    plan = build_engineering_plan(task, _reader())
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors

    strategy = plan.input_strategy
    assert strategy is not None
    assert strategy.mode == "single_next_question"
    assert strategy.current_phase == "expansion_assumptions"
    assert strategy.next_fields == ["straight_pipe_section"]
    assert "pressure_design_case" not in strategy.next_fields
    assert "pressure_design_case" in strategy.blocked_fields

    active_phases = _active_phases(plan)
    assert len(active_phases) == 1
    assert active_phases[0].id == "expansion_assumptions"

    assert _phase_statuses(plan) == {
        "expansion_assumptions": "active",
        "path_decisions": "pending",
        "equation_execution": "blocked",
        "reporting": "blocked",
    }


def test_fresh_pipe_wall_phase_statuses_single_active_phase() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_engineering_plan(task, _reader())
    validation = validate_engineering_plan(plan)

    assert validation.valid, validation.errors
    statuses = _phase_statuses(plan)
    assert statuses["expansion_assumptions"] == "active"
    assert statuses["path_decisions"] == "pending"
    assert "parameter_gathering" not in statuses
    assert "validation" not in statuses
    assert sum(1 for status in statuses.values() if status == "active") == 1
    active_phases = _active_phases(plan)
    assert len(active_phases) == 1
    assert active_phases[0].id == "expansion_assumptions"


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
    plan = build_engineering_plan(task, _reader(), existing_inputs=dict(task.fact_store.active_facts()))
    validation = validate_engineering_plan(plan)

    assert validation.valid, validation.errors
    statuses = _phase_statuses(plan)
    assert statuses["expansion_assumptions"] == "complete"
    assert statuses["path_decisions"] == "active"
    assert "parameter_gathering" not in statuses
    assert sum(1 for status in statuses.values() if status == "active") == 1


def test_gates_resolved_parameter_gathering_becomes_active() -> None:
    state, task = _task_with_gates_satisfied(TaskStateManager())
    plan = build_engineering_plan(task, _reader(), existing_inputs=dict(task.fact_store.active_facts()))
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
    plan = build_engineering_plan(task, _reader())

    assert "REQ-internal_design_gage_pressure" not in plan.requirements
    assert "REQ-allowable_stress_lookup" not in plan.requirements

    assert "REQ-straight_pipe_section" in plan.root_goal.blocked_by
    assert "REQ-pressure_design_case" in plan.root_goal.blocked_by
    assert "REQ-internal_design_gage_pressure" not in plan.root_goal.provisional_blocked_by
    assert plan.input_strategy is not None
    assert "internal_design_gage_pressure" not in plan.input_strategy.next_fields


def test_internal_pressure_branch_activates_downstream_requirements() -> None:
    state, task = _task_with_gates_satisfied(TaskStateManager())
    plan = build_engineering_plan(task, _reader(), existing_inputs=dict(task.fact_store.active_facts()))

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
                "pressure_design_case",
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
    plan = build_engineering_plan(task, _reader(), existing_inputs=dict(task.fact_store.active_facts()))

    assert "REQ-internal_design_gage_pressure" not in plan.requirements
    assert plan.input_strategy is not None
    assert "internal_design_gage_pressure" not in plan.input_strategy.next_fields
    assert "REQ-internal_design_gage_pressure" not in plan.root_goal.blocked_by
    assert "REQ-internal_design_gage_pressure" not in plan.root_goal.provisional_blocked_by


def test_planner_graph_summary_derived_from_engineering_plan() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_engineering_plan(task, _reader())
    summary = build_planner_inspector_summary(plan)
    graph_summary = summary["planner_graph_summary"]

    assert graph_summary["selected_subgraph_count"] == len(plan.graph.selected_subgraph_node_ids)
    assert graph_summary["expanded_node_count"] == len(plan.graph.expanded_node_ids)
    assert graph_summary["dependency_edge_count"] == len(plan.dependencies)
    assert graph_summary["branch_decision_count"] == len(plan.graph.selected_branch_decisions)
    assert graph_summary["dependency_edge_count"] > 0


def test_temperature_coefficient_lookup_summary_includes_metallurgical_group() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_engineering_plan(task, _reader())
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
    plan = build_engineering_plan(task, _reader())
    summary = build_planner_inspector_summary(plan)

    assert plan.input_strategy is not None
    assert plan.input_strategy.mode == "single_next_question"
    assert summary["current_phase"] == "expansion_assumptions"
    assert summary["next_input"] is not None
    assert summary["next_input"]["field"] == "straight_pipe_section"
    assert summary["next_input"]["phase"] == "expansion_assumptions"
    assert "next_required_inputs" not in summary

    traversal_summary = summary["traversal_summary"]
    assert traversal_summary is not None
    assert traversal_summary["current_active_node_id"] == param_node_id_for_input("straight_pipe_section")
    assert traversal_summary["pending_expansion_count"] > 0

    graph_summary = summary["planner_graph_summary"]
    assert graph_summary["dependency_edge_count"] > 0

    outstanding = summary["outstanding_required_inputs"]
    outstanding_fields = [item["field"] for item in outstanding]
    assert outstanding_fields[0] == "straight_pipe_section"
    assert "pressure_design_case" in outstanding_fields
    assert "internal_design_gage_pressure" not in outstanding_fields
    assert "material_grade" not in outstanding_fields

    conditional_fields = {item["field"] for item in summary["conditional_requirements"]}
    assert "internal_design_gage_pressure" not in conditional_fields

    assert summary["calculations"]
    calc_fields = {item["field"] for item in summary["calculations"]}
    assert "minimum_required_thickness" in calc_fields


def test_planner_inspector_summary_rebuilt_from_engineering_plan_dict() -> None:
    from engine.planner.plan_inspector import (
        build_planner_inspector_summary_from_dict,
        planner_inspector_summary_for_task,
    )
    from engine.planner.legacy_goal_adapter import store_engineering_plan_on_task

    _, task = _fresh_pipe_wall_task()
    plan = build_engineering_plan(task, _reader())
    store_engineering_plan_on_task(task, plan)
    task.outputs.pop("planner_inspector_summary", None)
    task.outputs["legacy_goal_map"] = {
        "GOAL-calculate-minimum-required-thickness": {
            "next_input": {"field": "internal_design_gage_pressure"},
        }
    }

    summary = planner_inspector_summary_for_task(task)
    assert summary is not None
    assert summary["next_input"]["field"] == "straight_pipe_section"
    straight_param = param_node_id_for_input("straight_pipe_section")
    assert summary["traversal_summary"]["current_active_node_id"] == straight_param
    assert summary["traversal_summary"]["pending_expansion_count"] > 0

    rebuilt = build_planner_inspector_summary_from_dict(task.outputs["engineering_plan"])
    assert rebuilt is not None
    assert rebuilt["current_phase"] == summary["current_phase"]
    assert rebuilt["next_input"] == summary["next_input"]
    assert rebuilt["traversal_summary"] == summary["traversal_summary"]


def test_fresh_pipe_wall_input_strategy_asks_expansion_assumption_first() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_engineering_plan(task, _reader())
    validation = validate_engineering_plan(plan)

    assert validation.valid, validation.errors
    assert plan.input_strategy is not None
    assert plan.input_strategy.mode == "single_next_question"
    assert plan.input_strategy.current_phase == "expansion_assumptions"
    assert plan.input_strategy.next_fields == ["straight_pipe_section"]
    assert "pressure_design_case" not in plan.input_strategy.next_fields
    assert "pressure_design_case" in plan.input_strategy.blocked_fields


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
    plan = build_engineering_plan(task, _reader(), existing_inputs=dict(task.fact_store.active_facts()))
    validation = validate_engineering_plan(plan)

    assert validation.valid, validation.errors
    assert plan.input_strategy is not None
    assert plan.input_strategy.current_phase == "path_decisions"
    assert plan.input_strategy.next_fields == ["pressure_design_case"]


def test_pipe_wall_diameter_resolution_dependency_edges() -> None:
    _, task = _fresh_pipe_wall_task()
    plan = build_engineering_plan(task, _reader())
    validation = validate_engineering_plan(plan)

    assert validation.valid, validation.errors
    edges = {(edge.from_id, edge.to_id, edge.type) for edge in plan.dependencies}
    assert ("REQ-nominal_pipe_size", "REQ-outside_diameter_lookup", "lookup_input") in edges
    assert ("REQ-outside_diameter_lookup", "REQ-diameter_resolution", "resolves") in edges
    assert ("ALT-nps-lookup", "REQ-nominal_pipe_size", "activates") in edges
    assert ("ALT-nps-lookup", "REQ-outside_diameter_lookup", "activates") not in edges
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

    plan = build_engineering_plan(task, _reader(), preview=preview)
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
    assert "REQ-outside_diameter_lookup" not in blocked
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
    assert summary["root_goal"]["title"] == "Pipe Wall Thickness Design"
    assert summary["root_goal"]["target_field"] == "minimum_required_thickness"
    assert summary["next_input"] is not None
    assert summary["next_input"]["field"] == "internal_design_gage_pressure"
    outstanding_fields = [item["field"] for item in summary["outstanding_required_inputs"]]
    assert "internal_design_gage_pressure" in outstanding_fields
    assert "diameter_input_mode" in outstanding_fields
    assert summary["alternatives"]
    assert summary["planner_graph_summary"]["dependency_edge_count"] > 0

    view = build_engineering_plan_view(plan)
    assert view["overview"]["goal"] == "Pipe Wall Thickness Design"
    assert view["phases"]
    first_phase = view["phases"][0]
    assert "requirements" in first_phase
    assert first_phase["requirements"][0]["label"]
    assert "REQ-" not in first_phase["requirements"][0]["label"]
    assert view["overview"]["next_input"]
    assert "field" in view["overview"]["next_input"]


def test_goal_store_root_blocked_by_respects_conditional_activation() -> None:
    from engine.planner.goal_builder import build_goal_tree

    manager = TaskStateManager()
    task = manager.create_task("goal-store-activation", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    reader = _reader()
    build_goal_tree(task, reader)
    manager.replace_task(task.task_id, task)

    root = task.goal_store.roots()[0]
    assert root.state.blocked_by == [
        "input-straight_pipe_section",
        "select-pressure_design_case",
    ]
    assert "input-internal_design_gage_pressure" not in root.state.blocked_by
    provisional = root.metadata.get("provisional_blocked_by") or []
    assert "input-internal_design_gage_pressure" in provisional
    assert "lookup-allowable_stress" in provisional


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

    from engine.planner.plan_inspector import engineering_plan_view_for_task

    view = engineering_plan_view_for_task(task)
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
    plan = build_engineering_plan(task, _reader())

    for field in (
        "allowable_stress",
        "weld_joint_efficiency",
        "temperature_coefficient_Y",
        WELD_W_FIELD,
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
    plan = build_engineering_plan(task, _reader(), existing_inputs=dict(task.fact_store.active_facts()))

    nps = plan.requirements["REQ-nominal_pipe_size"]
    od_lookup = plan.requirements["REQ-outside_diameter_lookup"]
    assert nps.status == "missing"
    assert od_lookup.status in {"blocked", "ready"}
    assert od_lookup.requirement_class == "table_lookup"


def test_task_state_exposes_canonical_engineering_plan() -> None:
    state, task = _task_with_gates_satisfied(TaskStateManager())
    reader = _reader()
    build_goal_tree(task, reader)
    state.replace_task(task.task_id, task)

    payload = task_state(task, state, reader=reader, projection_mode="full")
    plan = payload.get("engineering_plan")
    assert isinstance(plan, dict)
    assert "plan_id" in plan
    assert "requirements" in plan
    assert "root_goal" in plan
    assert "REQ-straight_pipe_section" in plan["requirements"]

    view = payload.get("engineering_plan_view")
    assert isinstance(view, dict)
    assert "overview" in view
    assert "phases" in view

    legacy = payload.get("legacy_goal_map")
    assert isinstance(legacy, dict)
    assert "GOAL-calculate-minimum-required-thickness" in legacy
    assert payload.get("goals") is None
    assert "engineering_plan" not in payload.get("outputs", {})
