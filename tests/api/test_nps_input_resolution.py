"""Tests for NPS submission resolving outside diameter from B36.10 tables."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.parameter_definitions import submit_task_input
from engine.state.state_manager import TaskStateManager
from models.fact import fact_scalar_value, fact_unit
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
        value="4",
        unit=None,
        standards_root=standards_root,
    )

    assert fact_scalar_value(updated.fact_store.active_fact("nominal_pipe_size")) == "4"
    od_fact = updated.fact_store.active_fact("outside_diameter")
    assert od_fact is not None
    assert fact_scalar_value(od_fact) == pytest.approx(114.3)
    assert fact_unit(od_fact) == "mm"
    d_mode = updated.fact_store.active_fact("d_input_mode")
    assert d_mode is not None
    assert fact_scalar_value(d_mode) == "nps_lookup"
    lookup = updated.outputs["outside_diameter_lookup"]
    assert lookup["nps"] == "4"
    assert lookup["outside_diameter_in"] == pytest.approx(4.5)


def test_submit_nominal_pipe_size_dropdown_without_unit(standards_root: Path) -> None:
    manager = TaskStateManager()
    task = manager.create_task("nps-submit-test04", status=TaskStatus.AWAITING_INPUT)
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
        value="6",
        unit=None,
        standards_root=standards_root,
    )

    assert fact_scalar_value(updated.fact_store.active_fact("nominal_pipe_size")) == "6"
    od_fact = updated.fact_store.active_fact("outside_diameter")
    assert od_fact is not None
    assert fact_scalar_value(od_fact) == pytest.approx(168.28, rel=1e-3)


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

    assert fact_scalar_value(updated.fact_store.active_fact("nominal_pipe_size")) == "4"
    od_fact = updated.fact_store.active_fact("outside_diameter")
    assert od_fact is not None
    assert fact_scalar_value(od_fact) == pytest.approx(114.3)
    assert fact_unit(od_fact) == "mm"


def test_submit_outside_diameter_from_nps_step(standards_root: Path) -> None:
    manager = TaskStateManager()
    task = manager.create_task("od-submit-from-nps", status=TaskStatus.AWAITING_INPUT)
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
        parameter="outside_diameter",
        value="114.3",
        unit="mm",
        standards_root=standards_root,
    )

    od_fact = updated.fact_store.active_fact("outside_diameter")
    assert od_fact is not None
    assert fact_scalar_value(od_fact) == pytest.approx(114.3)
    d_mode = updated.fact_store.active_fact("d_input_mode")
    assert d_mode is not None
    assert fact_scalar_value(d_mode) == "direct_od"


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

    with pytest.raises(ValueError, match="not allowed|not found"):
        submit_task_input(
            manager,
            task.task_id,
            parameter="nominal_pipe_size",
            value="99",
            unit=None,
            standards_root=standards_root,
        )
