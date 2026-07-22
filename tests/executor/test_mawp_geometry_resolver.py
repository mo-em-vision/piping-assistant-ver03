"""Tests for NPS/schedule geometry resolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.executor.nps_schedule_geometry_resolver import apply_pipe_schedule_lookup
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus
from tests.helpers.facts import fact_get_value, legacy_input, set_fact_from_input
from models.fact import SourceType, ValidationStatus, fact_scalar_value

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_pipe_schedule_lookup_sets_thickness_without_rederiving_od() -> None:
    from engine.executor.nps_input_resolver import apply_nominal_pipe_size_lookup

    manager = TaskStateManager()
    task = manager.create_task("mawp-geometry", status=TaskStatus.AWAITING_INPUT)
    set_fact_from_input(task, legacy_input(input_id="outside_diameter__resolution_branch",
        value="nps_lookup",
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

    apply_nominal_pipe_size_lookup(task, PROJECT_ROOT / "knowledge" / "standards")
    od_before = fact_scalar_value(task.fact_store.active_fact("outside_diameter"))

    apply_pipe_schedule_lookup(task, PROJECT_ROOT / "knowledge" / "standards")

    od = task.fact_store.active_fact("outside_diameter")
    thickness = task.fact_store.active_fact("actual_wall_thickness")
    assert fact_scalar_value(od) == pytest.approx(od_before, rel=1e-3)
    assert fact_scalar_value(thickness) == pytest.approx(3.912, abs=0.01)
    assert od.source.lookup_node == "asme-b3610-nps-outside-diameter-lookup"
    assert thickness.source.lookup_node == "asme-b3610-pipe-dimensions-lookup"
