"""Tests for node calculation summaries in task state."""

from __future__ import annotations

from api.node_calculation_summaries import build_node_calculation_summaries
from api.serializers import task_state
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus

from tests.acceptance.helpers import (
    WALL_THICKNESS_EQUATION_NODE,
    confirmed_default_inputs,
    internal_pressure_assumption,
    straight_section_assumption,
)
from tests.helpers.facts import populate_task_facts
from tests.helpers.goals import task_with_planning

_THICKNESS_TRACE_ENTRY = {
    "node_id": WALL_THICKNESS_EQUATION_NODE,
    "outputs": {"required_thickness": 0.084, "required_thickness_unit": "mm"},
    "trace": {
        "calculation": {"steps": []},
        "variables_si": {
            "P": 800000.0,
            "D": 0.1683,
            "S": 138000000.0,
            "E": 1.0,
            "W": 1.0,
            "Y": 0.4,
        },
    },
}


def test_build_node_calculation_summaries_includes_thickness_result(
    standards_reader: StandardsReader,
) -> None:
    """Summaries read equation execution traces (paragraph id is not an equation node)."""
    manager = TaskStateManager()
    task = manager.create_task("node-calc-summary-test", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "required_thickness": 0.084,
        "_execution_trace": [_THICKNESS_TRACE_ENTRY],
    }
    task_with_planning(task, {}, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    summaries = build_node_calculation_summaries(task, standards_reader)
    thickness = next(item for item in summaries if item["node_id"] == WALL_THICKNESS_EQUATION_NODE)

    assert thickness.get("paragraph") in {None, "304.1.2", "304.1.1"} or thickness.get("title")
    assert thickness["primary_result"]["symbol"] == "t"
    assert thickness["primary_result"]["value"]
    assert any(row["symbol"] == "P" for row in thickness["inputs"])
    assert any(row["symbol"] == "D" for row in thickness["inputs"])


def test_task_state_includes_node_calculations(
    standards_reader: StandardsReader,
) -> None:
    manager = TaskStateManager()
    task = manager.create_task("node-calc-summary-test02", status=TaskStatus.AWAITING_INPUT)
    populate_task_facts(task, {
            "pressure_loading": internal_pressure_assumption(),
            "straight_pipe_section": straight_section_assumption(),
            **confirmed_default_inputs(),
            "material_grade": EngineeringInput(
                input_id="material_grade",
                value="SA-106B",
                unit="dimensionless",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "internal_design_gage_pressure": EngineeringInput(
                input_id="internal_design_gage_pressure",
                value=8.0,
                unit="bar",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "design_temperature": EngineeringInput(
                input_id="design_temperature",
                value=38.0,
                unit="C",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "nominal_pipe_size": EngineeringInput(
                input_id="nominal_pipe_size",
                value="6",
                unit="dimensionless",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "pipe_construction_type": EngineeringInput(
                input_id="pipe_construction_type",
                value="seamless",
                unit="dimensionless",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        })
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "required_thickness": 0.084,
        "_execution_trace": [_THICKNESS_TRACE_ENTRY],
    }
    task_with_planning(task, {}, workflow_id="pipe_wall_thickness_design")
    manager.replace_task(task.task_id, task)

    state = task_state(task, manager, reader=standards_reader)
    assert len(state["node_calculations"]) == 1
    assert state["node_calculations"][0]["primary_result"]["symbol"] == "t"
