"""Tests for canonical six-column equation input table projection."""

from __future__ import annotations

from engine.equation.input_table import (
    INPUT_TABLE_COLUMNS,
    build_base_input_row,
    equation_parameter_description,
    equation_parameter_name,
    finalize_equation_input_table_row,
    format_value_for_table,
    source_column_text,
)
from engine.reference.parameter_keys import parameter_display_label
from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus

from api.equation_evaluation_display import build_equation_evaluation_block
from tests.helpers.facts import populate_task_facts
from tests.helpers.goals import task_with_planning

EXPECTED_COLUMN_KEYS = ("symbol", "parameter", "description", "value", "unit", "source")


def test_input_table_columns_schema() -> None:
    keys = tuple(column["key"] for column in INPUT_TABLE_COLUMNS)
    assert keys == EXPECTED_COLUMN_KEYS


def test_format_value_for_table_splits_unit() -> None:
    value, unit = format_value_for_table(8.0, "bar")
    assert value == "8"
    assert unit == "bar"


def test_build_base_input_row_uses_param_metadata(standards_reader) -> None:
    row = build_base_input_row(
        reader=standards_reader,
        symbol="P",
        param_id="PARAM-internal-design-gage-pressure",
    )
    assert row["symbol"] == "P"
    assert row["parameter"] == parameter_display_label(
        "PARAM-internal-design-gage-pressure",
        reader=standards_reader,
    )
    assert row["description"] == equation_parameter_description(
        standards_reader,
        "PARAM-internal-design-gage-pressure",
    )
    assert row["symbol"] != row["parameter"]


def test_source_column_text_for_resolved_user_input() -> None:
    row = finalize_equation_input_table_row(
        {
            "value_provenance": {
                "source_type": "user_input",
                "status": "resolved",
                "label": "User supplied",
            }
        }
    )
    assert row["source"] == "User input"


def test_build_equation_block_has_six_column_table(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-input-table", status=TaskStatus.AWAITING_INPUT)
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
    column_keys = [column["key"] for column in block["input_table"]["columns"]]
    assert column_keys == list(EXPECTED_COLUMN_KEYS)

    pressure_row = next(row for row in block["input_table"]["rows"] if row["symbol"] == "P")
    assert pressure_row["parameter"] == equation_parameter_name(
        standards_reader,
        "PARAM-internal-design-gage-pressure",
    )
    assert pressure_row["value"] == "8"
    assert pressure_row["unit"] == "bar"
    assert pressure_row["source"] == "User input"
