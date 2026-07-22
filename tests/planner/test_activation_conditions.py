"""Requirement activation status resolution."""

from __future__ import annotations

from engine.planner.activation_conditions import resolve_activation_status
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from models.engineering_plan import ActivationCondition, PlanRequirement
from models.task import TaskStatus
from tests.acceptance.helpers import (
    external_pressure_assumption,
    internal_pressure_assumption,
    straight_section_assumption,
)


def _pressure_branch_requirement() -> PlanRequirement:
    return PlanRequirement(
        id="REQ-internal_design_gage_pressure",
        field="internal_design_gage_pressure",
        parameter_node_id="PARAM-internal-design-gage-pressure",
        requirement_class="user_input",
        status="missing",
        phase="parameter_gathering",
        required_by=["GOAL-calculate-minimum-required-thickness"],
        depends_on=[],
        activation_condition=ActivationCondition(
            field="pressure_design_case",
            operator="equals",
            value="internal_pressure",
        ),
    )


def _facts_for(*assumptions):
    manager = TaskStateManager()
    task = manager.create_task("activation-facts", status=TaskStatus.AWAITING_INPUT)
    return {
        fact.key: fact
        for assumption in assumptions
        for fact in (
            fact_from_engineering_input(
                assumption,
                task_id=task.task_id,
                workflow_id="pipe_wall_thickness_design",
            ),
        )
    }


def test_resolve_activation_status_conditional_before_branch() -> None:
    req = _pressure_branch_requirement()
    assert resolve_activation_status(req, {}) == "conditional"


def test_resolve_activation_status_active_for_internal_pressure() -> None:
    req = _pressure_branch_requirement()
    facts = _facts_for(straight_section_assumption(), internal_pressure_assumption())
    assert resolve_activation_status(req, facts) == "active"


def test_resolve_activation_status_not_applicable_for_external_pressure() -> None:
    req = _pressure_branch_requirement()
    facts = _facts_for(straight_section_assumption(), external_pressure_assumption())
    assert resolve_activation_status(req, facts) == "not_applicable"
