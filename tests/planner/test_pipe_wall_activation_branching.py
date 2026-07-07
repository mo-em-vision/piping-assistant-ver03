"""Pipe wall activation and internal/external pressure branching contract tests."""

from __future__ import annotations

from engine.planner.engineering_plan_builder import build_pipe_wall_engineering_plan
from engine.planner.pipe_wall_plan import INTERNAL_PRESSURE_BRANCH_CONDITION
from engine.planner.plan_phases import _askable_fields_for_phase
from engine.planner.plan_validation import validate_engineering_plan
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.acceptance.helpers import (
    external_pressure_assumption,
    internal_pressure_assumption,
    straight_section_assumption,
)

_INTERNAL_PRESSURE_CONDITIONAL_REQUIREMENT_IDS = (
    "REQ-internal_design_gage_pressure",
    "REQ-diameter_resolution",
    "REQ-material_grade",
    "REQ-design_temperature",
    "REQ-corrosion_allowance",
    "REQ-pipe_construction_type",
    "REQ-required_wall_thickness",
    "REQ-minimum_required_thickness_eq",
)

_EXTERNAL_INTERNAL_EQUATION_REQUIREMENT_IDS = (
    "REQ-required_wall_thickness",
    "REQ-minimum_required_thickness_eq",
)


def _fresh_pipe_wall_task():
    manager = TaskStateManager()
    task = manager.create_task("activation-branch-pwt", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    return manager, task


def _build_plan(*inputs):
    manager, task = _fresh_pipe_wall_task()
    for inp in inputs:
        manager.store_fact(
            task.task_id,
            fact_from_engineering_input(
                inp,
                task_id=task.task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
        )
    task = manager.get_task(task.task_id)
    existing = dict(task.fact_store.active_facts())
    plan = build_pipe_wall_engineering_plan(task, existing_inputs=existing)
    return plan


def _assert_internal_pressure_branch_condition(req) -> None:
    assert req.activation_condition is not None
    assert req.activation_condition == INTERNAL_PRESSURE_BRANCH_CONDITION
    assert req.activation_condition.field == "pressure_loading"
    assert req.activation_condition.operator == "equals"
    assert req.activation_condition.value == "internal_pressure"


def _parameter_gathering_askable_fields(plan) -> list[str]:
    askable = _askable_fields_for_phase(plan.requirements, "parameter_gathering")
    return [field for _, field in askable]


def test_fresh_plan_internal_pressure_requirements_are_conditional_with_full_branch_condition() -> None:
    plan = _build_plan()

    for req_id in _INTERNAL_PRESSURE_CONDITIONAL_REQUIREMENT_IDS:
        req = plan.requirements[req_id]
        assert req.activation_status == "conditional", req_id
        _assert_internal_pressure_branch_condition(req)


def test_fresh_plan_internal_pressure_requirements_are_provisional_not_hard_blocked() -> None:
    plan = _build_plan()

    assert plan.root_goal.blocked_by == ["REQ-straight_pipe_section", "REQ-pressure_loading"]
    provisional = set(plan.root_goal.provisional_blocked_by)
    for req_id in _INTERNAL_PRESSURE_CONDITIONAL_REQUIREMENT_IDS:
        assert req_id in provisional, req_id
        assert req_id not in plan.root_goal.blocked_by, req_id


def test_internal_pressure_branch_activates_all_internal_pressure_requirements() -> None:
    plan = _build_plan(straight_section_assumption(), internal_pressure_assumption())
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors

    for req_id in _INTERNAL_PRESSURE_CONDITIONAL_REQUIREMENT_IDS:
        req = plan.requirements[req_id]
        assert req.activation_status == "active", req_id
        assert req.activation_status != "not_applicable", req_id

    assert plan.input_strategy is not None
    assert plan.input_strategy.current_phase == "parameter_gathering"
    assert any(phase.status == "active" and phase.id == "parameter_gathering" for phase in plan.phases)


def test_internal_pressure_branch_next_field_follows_parameter_gathering_priority() -> None:
    plan = _build_plan(straight_section_assumption(), internal_pressure_assumption())
    validation = validate_engineering_plan(plan)
    assert validation.valid, validation.errors

    strategy = plan.input_strategy
    assert strategy is not None
    assert strategy.current_phase == "parameter_gathering"
    assert len(strategy.next_fields) == 1

    askable_fields = _parameter_gathering_askable_fields(plan)
    assert askable_fields, "expected at least one askable parameter_gathering field"
    assert strategy.next_fields[0] in askable_fields
    assert strategy.next_fields[0] == askable_fields[0]


def test_external_pressure_branch_marks_internal_requirements_and_equations_not_applicable() -> None:
    plan = _build_plan(straight_section_assumption(), external_pressure_assumption())

    for req_id in _INTERNAL_PRESSURE_CONDITIONAL_REQUIREMENT_IDS:
        req = plan.requirements[req_id]
        assert req.activation_status == "not_applicable", req_id
        assert req.status == "not_applicable", req_id

    for req_id in _EXTERNAL_INTERNAL_EQUATION_REQUIREMENT_IDS:
        req = plan.requirements[req_id]
        assert req.activation_status == "not_applicable", req_id
        assert req.status == "not_applicable", req_id


def test_external_pressure_branch_does_not_ask_internal_design_gage_pressure() -> None:
    plan = _build_plan(straight_section_assumption(), external_pressure_assumption())

    assert plan.input_strategy is not None
    assert "internal_design_gage_pressure" not in plan.input_strategy.next_fields
    assert plan.input_strategy.next_fields == []

    assert "REQ-internal_design_gage_pressure" not in plan.root_goal.blocked_by
    assert "REQ-internal_design_gage_pressure" not in plan.root_goal.provisional_blocked_by
