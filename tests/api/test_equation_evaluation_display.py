"""Tests for graph-driven equation evaluation display blocks."""

from __future__ import annotations

from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus

from api.equation_evaluation_display import (
    _definition_reference_for_parameter,
    build_equation_evaluation_block,
    resolve_equation_node_for_display,
)
from api.equation_inputs_display import AWAITING_USER_INPUT
from tests.helpers.facts import populate_task_facts
from tests.helpers.goals import task_with_planning


def test_resolve_equation_node_from_paragraph_references(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-eval-resolve", status=TaskStatus.AWAITING_INPUT)

    equation_id = resolve_equation_node_for_display(standards_reader, "304.1.2-a", task)
    assert equation_id == "asme-b313-304-1-2-eq-3a"


def test_build_equation_evaluation_block_includes_live_values(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-eval-block", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {"selected_node": "304.1.2-a"},
        "current_phase": "formula_parameters",
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    populate_task_facts(
        task,
        {
            "internal_design_gage_pressure": EngineeringInput(
                input_id="internal_design_gage_pressure",
                value=8.0,
                unit="bar",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
    )

    block = build_equation_evaluation_block(task, standards_reader, "304.1.2-a")
    assert block is not None
    assert block["display"] == "t = PD / 2(SEW + PY)"
    assert block["input_table"]["columns"][1]["label"] == "Parameter"
    assert block["input_table"]["columns"][2]["label"] == "Description"

    pressure_row = next(row for row in block["input_table"]["rows"] if row["symbol"] == "P")
    assert pressure_row["value"] == "8"
    assert pressure_row["unit"] == "bar"
    assert any(row["value"] == AWAITING_USER_INPUT for row in block["input_table"]["rows"])
    assert pressure_row.get("definition_reference") is not None


def test_build_equation_evaluation_block_derived_t_shows_value_reference(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-eval-304-1-1", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {
            "pressure_design_case": "internal_pressure",
            "selected_node": "304.1.1-a",
        },
        "current_phase": "formula_parameters",
    }
    task.outputs = {"workflow": "pipe_wall_thickness_design"}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    task.active_nodes = ["304.1.1-a", "304.1.2-a"]

    block = build_equation_evaluation_block(task, standards_reader, "304.1.1-a")
    assert block is not None
    assert block["display"] == "t_m = t + c"

    t_row = next(row for row in block["input_table"]["rows"] if row["symbol"] == "t")
    assert t_row.get("value_reference") is not None
    assert t_row["value_reference"]["node_id"] == "304.1.2-a"
    assert t_row["value_reference"]["label"] == "ASME B31.3 §304.1.2"
    assert t_row["value"] != AWAITING_USER_INPUT

    c_row = next(row for row in block["input_table"]["rows"] if row["symbol"] == "c")
    assert c_row.get("value_reference") is None
    assert c_row["value"] == AWAITING_USER_INPUT


def test_eq2_trace_updates_t_value_when_output_available(standards_reader) -> None:
    from api.equation_evaluation_display import build_equation_trace_block
    from api.equation_inputs_display import AWAITING_USER_INPUT

    manager = TaskStateManager()
    task = manager.create_task("eq-eval-trace-t", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {
            "pressure_design_case": "internal_pressure",
            "selected_node": "304.1.2-a",
        },
        "current_phase": "formula_parameters",
    }
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "t": 2.0,
        "required_thickness": 2.0,
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")
    task.active_nodes = ["304.1.1-a", "304.1.2-a"]

    trace = build_equation_trace_block(task, standards_reader, "304.1.1-a")
    assert trace is not None
    assert trace.get("display_role") == "equation"
    assert trace.get("display_state") == "evaluated"
    t_row = next(row for row in trace["input_table"]["rows"] if row["symbol"] == "t")
    assert t_row["value"] != AWAITING_USER_INPUT
    assert "2.000" in t_row["value"]
    assert t_row.get("value_reference") is not None
    assert t_row.get("value_status") == "equation_derived"


def test_definition_reference_strips_letter_suffix_from_label(standards_reader) -> None:
    reference = _definition_reference_for_parameter(standards_reader, "PARAM-allowable-stress")
    assert reference is not None
    assert reference["label"] == "§304.1.1"
    assert reference["node_id"]
