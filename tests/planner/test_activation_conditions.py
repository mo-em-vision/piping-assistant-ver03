"""Tests for requirement activation condition evaluation."""

from __future__ import annotations

from engine.planner.activation_conditions import evaluate_activation_condition
from engine.state.fact_migration import fact_from_engineering_input
from models.engineering_plan import ActivationCondition
from models.input import EngineeringInput, InputSource, InputStatus
from tests.acceptance.helpers import internal_pressure_assumption


def test_evaluate_activation_condition_pending_when_branch_unresolved() -> None:
    condition = ActivationCondition(
        field="pressure_loading",
        operator="equals",
        value="internal_pressure",
    )
    assert evaluate_activation_condition(condition, {}) is None


def test_evaluate_activation_condition_matches_internal_pressure() -> None:
    condition = ActivationCondition(
        field="pressure_loading",
        operator="equals",
        value="internal_pressure",
    )
    fact = fact_from_engineering_input(
        internal_pressure_assumption(),
        task_id="TASK-activation",
        workflow_id="pipe_wall_thickness_design",
    )
    assert evaluate_activation_condition(condition, {"pressure_loading": fact}) is True


def test_evaluate_activation_condition_rejects_external_pressure() -> None:
    condition = ActivationCondition(
        field="pressure_loading",
        operator="equals",
        value="internal_pressure",
    )
    fact = fact_from_engineering_input(
        EngineeringInput(
            "pressure_loading",
            "external_pressure",
            "dimensionless",
            InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        task_id="TASK-activation",
        workflow_id="pipe_wall_thickness_design",
    )
    assert evaluate_activation_condition(condition, {"pressure_loading": fact}) is False
