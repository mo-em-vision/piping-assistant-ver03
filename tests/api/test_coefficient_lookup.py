"""Tests for automatic E/W/Y coefficient table lookups."""

from __future__ import annotations

from pathlib import Path

from api.parameter_definitions import submit_task_input
from engine.executor.coefficient_lookup import apply_coefficient_lookups
from engine.state.state_manager import TaskStateManager
from models.fact import SourceType, ValidationStatus, fact_scalar_value
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus
from engine.state.goal_projection import planning_projection
from tests.helpers.facts import legacy_input, populate_task_facts, set_fact_from_input
from tests.helpers.goals import task_with_planning


def _pipe_wall_task(
    manager: TaskStateManager,
    task_id: str,
    *,
    inputs: dict[str, EngineeringInput],
    missing: list[str],
) -> None:
    task = manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
    populate_task_facts(task, inputs)
    planning = {
        "missing_inputs": [],
        "missing_assumptions": [],
        "missing_execution_assumptions": list(missing),
        "current_phase": "coefficient_resolution",
        "phase_missing": {"coefficient_resolution": list(missing)},
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)


def test_joint_category_submission_resolves_weld_joint_efficiency_from_table(
    project_root: Path,
) -> None:
    standards_root = project_root / "knowledge" / "standards"
    manager = TaskStateManager()
    _pipe_wall_task(
        manager,
        "coeff-submit-test01",
        inputs={
            "material": EngineeringInput(
                "material",
                "A106 Gr B",
                "dimensionless",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "design_temperature": EngineeringInput(
                "design_temperature",
                85.0,
                "C",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "weld_joint_efficiency": EngineeringInput(
                "weld_joint_efficiency",
                1.0,
                "dimensionless",
                InputSource.DEFAULT,
                status=InputStatus.PROPOSED_DEFAULT,
                default=1.0,
                requires_confirmation=True,
            ),
        },
        missing=["joint_category", "weld_joint_efficiency"],
    )

    submit_task_input(
        manager,
        "coeff-submit-test01",
        parameter="joint_category",
        value="seamless",
        unit=None,
        standards_root=standards_root,
    )

    task = manager.get_task("coeff-submit-test01")
    efficiency = task.fact_store.active_fact("weld_joint_efficiency")
    assert efficiency is not None
    assert efficiency.validation.status == ValidationStatus.CONFIRMED
    assert efficiency.source.source_type == SourceType.TABLE_LOOKUP
    assert fact_scalar_value(efficiency) == 1.0
    planning = planning_projection(task)
    assert "weld_joint_efficiency" not in (
        planning["phase_missing"].get("coefficient_resolution") or []
    )


def test_apply_coefficient_lookups_waits_for_confirmed_joint_category(
    project_root: Path,
) -> None:
    standards_root = project_root / "knowledge" / "standards"
    manager = TaskStateManager()
    task = manager.create_task("coeff-apply-test01", status=TaskStatus.AWAITING_INPUT)
    populate_task_facts(
        task,
        {
            "material": EngineeringInput(
                "material",
                "SA-106B",
                "dimensionless",
                InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "joint_category": EngineeringInput(
                "joint_category",
                "seamless",
                "dimensionless",
                InputSource.DEFAULT,
                status=InputStatus.PROPOSED_DEFAULT,
                default="seamless",
                requires_confirmation=True,
            ),
            "weld_joint_efficiency": EngineeringInput(
                "weld_joint_efficiency",
                1.0,
                "dimensionless",
                InputSource.DEFAULT,
                status=InputStatus.PROPOSED_DEFAULT,
                default=1.0,
                requires_confirmation=True,
            ),
        },
    )

    apply_coefficient_lookups(task, standards_root)

    efficiency = task.fact_store.active_fact("weld_joint_efficiency")
    assert efficiency is not None
    assert efficiency.validation.status == ValidationStatus.PENDING
    set_fact_from_input(
        task,
        legacy_input(
            "joint_category",
            "seamless",
            "dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    apply_coefficient_lookups(task, standards_root)
    efficiency = task.fact_store.active_fact("weld_joint_efficiency")
    assert efficiency is not None
    assert efficiency.validation.status == ValidationStatus.CONFIRMED
    assert efficiency.source.source_type == SourceType.TABLE_LOOKUP
