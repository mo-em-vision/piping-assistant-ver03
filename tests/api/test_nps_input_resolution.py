"""Tests for NPS submission resolving outside diameter from B36.10 tables."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.parameter_definitions import submit_task_input
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.helpers.goals import task_with_planning


@pytest.fixture(scope="module")
def standards_root() -> Path:
    return Path(__file__).resolve().parents[2] / "knowledge" / "standards"


def test_submit_nominal_pipe_size_resolves_outside_diameter(standards_root: Path) -> None:
    manager = TaskStateManager()
    task = manager.create_task("nps-submit-test01", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_inputs": ["nominal_pipe_size"],
        "missing_assumptions": [],
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": ["nominal_pipe_size"]},
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    updated = submit_task_input(
        manager,
        task.task_id,
        parameter="nominal_pipe_size",
        value="4 inch",
        unit=None,
        standards_root=standards_root,
    )

    assert updated.inputs["nominal_pipe_size"].value == "4"
    od = updated.inputs["outside_diameter"]
    assert od.value == pytest.approx(114.3)
    assert od.unit == "mm"
    assert updated.inputs["d_input_mode"].value == "nps_lookup"
    lookup = updated.outputs["outside_diameter_lookup"]
    assert lookup["nps"] == "4"
    assert lookup["outside_diameter_in"] == pytest.approx(4.5)


def test_submit_nominal_pipe_size_with_dn_unit_resolves_outside_diameter(standards_root: Path) -> None:
    manager = TaskStateManager()
    task = manager.create_task("nps-submit-test03", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_inputs": ["nominal_pipe_size"],
        "missing_assumptions": [],
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": ["nominal_pipe_size"]},
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    updated = submit_task_input(
        manager,
        task.task_id,
        parameter="nominal_pipe_size",
        value="100",
        unit="DN",
        standards_root=standards_root,
    )

    assert updated.inputs["nominal_pipe_size"].value == "4"
    od = updated.inputs["outside_diameter"]
    assert od.value == pytest.approx(114.3)
    assert od.unit == "mm"


def test_submit_unknown_nominal_pipe_size_raises(standards_root: Path) -> None:
    manager = TaskStateManager()
    task = manager.create_task("nps-submit-test02", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_inputs": ["nominal_pipe_size"],
        "missing_assumptions": [],
        "phase_missing": {"parameter_gathering": ["nominal_pipe_size"]},
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    with pytest.raises(ValueError, match="not found"):
        submit_task_input(
            manager,
            task.task_id,
            parameter="nominal_pipe_size",
            value="99",
            unit=None,
            standards_root=standards_root,
        )
