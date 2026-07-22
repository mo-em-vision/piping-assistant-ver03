"""Tests for graph-driven requirement ordering."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_engineering_plan
from engine.planner.requirement_ordering import build_requirement_order_context
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.helpers.facts import set_fact_from_input
from tests.planner.helpers import _reader


def _gates_open_task():
    manager = TaskStateManager()
    task = manager.create_task("order-gates-open", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    for inp in (straight_section_assumption(), internal_pressure_assumption()):
        set_fact_from_input(task, inp)
    return task


def test_fresh_pipe_wall_next_field_follows_graph_order() -> None:
    task = _gates_open_task()
    reader = _reader()
    plan = build_engineering_plan(task, reader)
    assert plan is not None
    assert plan.input_strategy is not None
    assert plan.input_strategy.next_fields == ["design_temperature"]


def test_requirement_order_context_uses_expansion_before_dependencies() -> None:
    task = _gates_open_task()
    reader = _reader()
    plan = build_engineering_plan(task, reader)
    assert plan is not None
    execution_order = list(plan.graph.selected_subgraph_node_ids or ())
    context = build_requirement_order_context(
        plan.requirements,
        reader=reader,
        execution_order=execution_order,
    )
    assert "internal_design_gage_pressure" in context.field_index
    assert "design_temperature" in context.field_index
    assert (
        context.field_index["design_temperature"]
        < context.field_index["internal_design_gage_pressure"]
    )


def test_requirement_index_breaks_ties_when_dependency_depth_matches() -> None:
    """When depth and graph index tie, requirements dict emission order wins."""
    from engine.planner.requirement_ordering import requirement_sort_key
    from models.engineering_plan import PlanRequirement, QuestionSpec

    def _req(field: str) -> PlanRequirement:
        return PlanRequirement(
            id=f"REQ-{field}",
            field=field,
            parameter_node_id=None,
            phase="parameter_gathering",
            requirement_class="user_input",
            status="missing",
            activation_status="active",
            question_spec=QuestionSpec(
                field=field,
                label=field,
                expected_value_class="scalar",
                priority=100,
                ask_policy="ask_now",
            ),
        )

    requirements = {
        "REQ-alpha_input_x": _req("alpha_input_x"),
        "REQ-alpha_lookup_key": _req("alpha_lookup_key"),
    }
    context = build_requirement_order_context(
        requirements,
        execution_order=["PARAM-alpha_lookup_key", "PARAM-alpha_input_x"],
    )

    x_key = requirement_sort_key("REQ-alpha_input_x", requirements["REQ-alpha_input_x"], context)
    lookup_key = requirement_sort_key(
        "REQ-alpha_lookup_key", requirements["REQ-alpha_lookup_key"], context
    )
    assert x_key < lookup_key
