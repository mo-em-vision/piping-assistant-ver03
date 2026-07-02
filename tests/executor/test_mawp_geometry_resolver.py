"""Tests for MAWP geometry resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.mawp_geometry_resolver import apply_pipe_schedule_lookup
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus
from tests.helpers.facts import fact_get_value
from models.fact import SourceType, ValidationStatus, fact_scalar_value

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_pipe_schedule_lookup_sets_od_and_thickness() -> None:
    manager = TaskStateManager()
    task = manager.create_task("mawp-geometry", status=TaskStatus.AWAITING_INPUT)
    set_fact_from_input(task, legacy_input(input_id="geometry_input_mode",
        value="nps_and_schedule",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    set_fact_from_input(task, legacy_input(input_id="nominal_pipe_size",
        value="2",
        unit="NPS",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))
    set_fact_from_input(task, legacy_input(input_id="pipe_schedule",
        value="40",
        unit="dimensionless",
        source=InputSource.USER,
        status=InputStatus.CONFIRMED,))

    apply_pipe_schedule_lookup(task, PROJECT_ROOT / "knowledge" / "standards")

    od = task.fact_store.active_fact("outside_diameter")
    thickness = task.fact_store.active_fact("actual_wall_thickness")
    assert fact_scalar_value(od) == pytest.approx(60.33, abs=0.01)
    assert fact_scalar_value(thickness) == pytest.approx(3.912, abs=0.01)
