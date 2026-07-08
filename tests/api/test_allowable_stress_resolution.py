"""Tests for material + temperature submission resolving allowable stress S."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.parameter_definitions import submit_task_input
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.helpers.facts import fact_get_value, legacy_input, populate_task_facts, set_fact_from_input
from tests.helpers.goals import task_with_planning
from models.fact import SourceType, ValidationStatus


@pytest.fixture(scope="module")
def standards_root() -> Path:
    return Path(__file__).resolve().parents[2] / "knowledge" / "standards"


def _pipe_wall_task(manager: TaskStateManager, task_id: str, *, missing: list[str]) -> None:
    task = manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_inputs": list(missing),
        "missing_assumptions": [],
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": list(missing)},
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)


def test_submit_temperature_after_material_resolves_allowable_stress(standards_root: Path) -> None:
    manager = TaskStateManager()
    _pipe_wall_task(manager, "s-submit-test01", missing=["material_grade", "design_temperature"])

    submit_task_input(
        manager,
        "s-submit-test01",
        parameter="material_grade",
        value="A106 Gr B",
        unit=None,
        standards_root=standards_root,
    )
    after_material = manager.get_task("s-submit-test01")
    assert after_material.outputs.get("allowable_stress") is None

    updated = submit_task_input(
        manager,
        "s-submit-test01",
        parameter="design_temperature",
        value=200,
        unit="F",
        standards_root=standards_root,
    )

    stress = updated.outputs["allowable_stress"]
    assert stress == pytest.approx(193_000_000)
    assert updated.outputs["S"] == pytest.approx(193_000_000)
    lookup = updated.outputs["allowable_stress_lookup"]
    assert lookup["table_id"] == "asme_b31.3_A-1"
    assert lookup["standard"] == "asme_b31.3"
    assert lookup["design_temperature_f"] == pytest.approx(200)
    assert updated.outputs.get("allowable_stress_unit") == "Pa"


def test_submit_unknown_material_raises(standards_root: Path) -> None:
    manager = TaskStateManager()
    _pipe_wall_task(manager, "s-submit-test02", missing=["material_grade", "design_temperature"])

    with pytest.raises(ValueError, match="Select a material from the available options"):
        submit_task_input(
            manager,
            "s-submit-test02",
            parameter="material_grade",
            value="Unknown Alloy XYZ",
            unit=None,
            standards_root=standards_root,
        )


def test_allowable_stress_resolver_updates_on_temperature_change(standards_root: Path) -> None:
    from engine.executor.allowable_stress_resolver import apply_allowable_stress_lookup
    from models.input import EngineeringInput, InputSource, InputStatus

    manager = TaskStateManager()
    task = manager.create_task("s-resolver-test01", status=TaskStatus.AWAITING_INPUT)
    populate_task_facts(task, {
        "material_grade": EngineeringInput(
            input_id="material_grade",
            value="SA-106B",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "design_temperature": EngineeringInput(
            input_id="design_temperature",
            value=100,
            unit="F",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    })
    apply_allowable_stress_lookup(task, standards_root)
    assert task.outputs["allowable_stress"] == pytest.approx(207_000_000)

    set_fact_from_input(task, legacy_input(input_id="design_temperature",
        value=400,
        unit="F",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    apply_allowable_stress_lookup(task, standards_root)
    assert task.outputs["allowable_stress"] == pytest.approx(179_000_000)
