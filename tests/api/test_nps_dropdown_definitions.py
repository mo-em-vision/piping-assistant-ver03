"""Tests for NPS dropdown parameter definitions from ASME B36.10."""

from __future__ import annotations

from pathlib import Path

from api.parameter_definitions import build_parameter_definitions
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.helpers.goals import task_with_planning


def test_build_parameter_definitions_includes_nps_dropdown_options() -> None:
    standards_root = Path(__file__).resolve().parents[2] / "knowledge" / "standards"
    reader = StandardsReader(standards_root)

    manager = TaskStateManager()
    task = manager.create_task("nps-dropdown-defs", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_inputs": ["nominal_pipe_size"],
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": ["nominal_pipe_size"]},
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")

    definitions = build_parameter_definitions(task, reader=reader)
    nps = next(item for item in definitions if item["name"] == "nominal_pipe_size")

    assert nps["type"] == "dropdown"
    assert nps["default_unit"] == "NPS"
    assert nps["options"]
    assert any(option["value"] == "4" for option in nps["options"])
    assert all("OD" not in option["label"] for option in nps["options"])
    labels = [option["label"] for option in nps["options"]]
    assert labels.index("NPS 1") < labels.index("NPS 2-1/2")
    assert labels.index("NPS 2-1/2") < labels.index("NPS 3")


def test_build_parameter_definitions_includes_outside_diameter_resolution_branch() -> None:
    standards_root = Path(__file__).resolve().parents[2] / "knowledge" / "standards"
    reader = StandardsReader(standards_root)

    manager = TaskStateManager()
    task = manager.create_task("od-dropdown-defs", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "missing_inputs": ["outside_diameter"],
        "current_phase": "parameter_gathering",
        "phase_missing": {"parameter_gathering": ["outside_diameter"]},
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")

    definitions = build_parameter_definitions(task, reader=reader)
    od = next(item for item in definitions if item["name"] == "outside_diameter")

    assert od["type"] == "resolution_branch"
    ui = od["resolution_ui"]
    assert ui["branch_fact_key"] == "outside_diameter__resolution_branch"
    assert [branch["id"] for branch in ui["branches"]] == ["nps_lookup", "direct_od"]
    assert ui["default_value"] == "nps_lookup"
