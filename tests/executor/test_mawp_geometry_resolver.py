"""Tests for MAWP geometry resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.mawp_geometry_resolver import apply_pipe_schedule_lookup
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_pipe_schedule_lookup_sets_od_and_thickness() -> None:
    manager = TaskStateManager()
    task = manager.create_task("mawp-geometry", status=TaskStatus.AWAITING_INPUT)
    task.inputs["geometry_input_mode"] = EngineeringInput(
        input_id="geometry_input_mode",
        value="nps_and_schedule",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
    task.inputs["nominal_pipe_size"] = EngineeringInput(
        input_id="nominal_pipe_size",
        value="2",
        unit="NPS",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )
    task.inputs["pipe_schedule"] = EngineeringInput(
        input_id="pipe_schedule",
        value="40",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,
    )

    apply_pipe_schedule_lookup(task, PROJECT_ROOT / "knowledge" / "standards")

    od = task.inputs["outside_diameter"]
    thickness = task.inputs["actual_wall_thickness"]
    assert od.value == pytest.approx(60.33, abs=0.01)
    assert thickness.value == pytest.approx(3.912, abs=0.01)
