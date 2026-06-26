"""Tests for equation input display blocks."""

from __future__ import annotations

from engine.state.state_manager import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import TaskStatus

from api.equation_inputs_display import (
    AWAITING_USER_INPUT,
    build_formula_inputs_input_table,
    build_formula_inputs_table_rows,
    build_substituted_formula_display,
    definitions_from_equation_variables,
    format_value_with_unit_for_display,
    primary_formula_inputs_complete,
)
from api.output_blocks import build_display_outputs

_ALL_AWAITING_ROWS = [
    {"symbol": "", "definition": "Design material", "value": AWAITING_USER_INPUT},
    {"symbol": "P", "definition": "Design pressure", "value": AWAITING_USER_INPUT},
    {"symbol": "T", "definition": "Design temperature", "value": AWAITING_USER_INPUT},
    {
        "symbol": "D",
        "definition": "Outside diameter",
        "value": AWAITING_USER_INPUT,
    },
    {"symbol": "S", "definition": "Allowable stress", "value": AWAITING_USER_INPUT},
    {"symbol": "E", "definition": "Joint efficiency", "value": AWAITING_USER_INPUT},
    {"symbol": "W", "definition": "Weld strength reduction", "value": AWAITING_USER_INPUT},
    {"symbol": "Y", "definition": "Temperature coefficient", "value": AWAITING_USER_INPUT},
]


def test_format_value_with_unit_for_display_converts_pascal_to_mpa() -> None:
    assert format_value_with_unit_for_display(193_000_000, "Pa") == "193 MPa"
    assert format_value_with_unit_for_display(8.0, "bar") == "8.0 bar"
    assert format_value_with_unit_for_display(200.0, "C") == "200.0 °C"


def test_build_formula_inputs_table_rows_from_task_inputs() -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-inputs-test01", status=TaskStatus.AWAITING_INPUT)
    task.inputs = {
        "material": EngineeringInput(
            input_id="material",
            value="A106 Gr A",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "design_pressure": EngineeringInput(
            input_id="design_pressure",
            value=3.0,
            unit="bar",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    }

    rows = build_formula_inputs_table_rows(task)
    assert rows[0] == {
        "symbol": "",
        "definition": "Design material",
        "value": "ASTM A106 Grade A",
    }
    assert rows[1] == {
        "symbol": "P",
        "definition": "Design pressure",
        "value": "3.0 bar",
    }
    assert rows[2]["value"] == AWAITING_USER_INPUT


def test_design_temperature_value_uses_degree_celsius_symbol() -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-inputs-test-temp", status=TaskStatus.AWAITING_INPUT)
    task.inputs = {
        "design_temperature": EngineeringInput(
            input_id="design_temperature",
            value=38.0,
            unit="c",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    }

    rows = build_formula_inputs_table_rows(task)
    assert rows[2] == {
        "symbol": "T",
        "definition": "Design temperature",
        "value": "38.0 °C",
    }


def test_outside_diameter_value_includes_nps_and_hides_nps_row() -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-inputs-test-nps-d", status=TaskStatus.AWAITING_INPUT)
    task.inputs = {
        "nominal_pipe_size": EngineeringInput(
            input_id="nominal_pipe_size",
            value="4",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
            original_value="4 inch",
        ),
        "d_input_mode": EngineeringInput(
            input_id="d_input_mode",
            value="nps_lookup",
            unit="dimensionless",
            source=InputSource.SYSTEM,
            status=InputStatus.CONFIRMED,
        ),
        "outside_diameter": EngineeringInput(
            input_id="outside_diameter",
            value=114.3,
            unit="mm",
            source=InputSource.TABLE,
            status=InputStatus.CONFIRMED,
        ),
    }
    task.outputs = {
        "outside_diameter_lookup": {
            "standard": "asme_b36.10",
            "nps": "4",
            "outside_diameter_mm": 114.3,
        },
    }

    rows = build_formula_inputs_table_rows(
        task,
        definition_overrides={"outside_diameter": "Outside diameter of pipe as measured"},
    )
    symbols = [row["symbol"] for row in rows]
    assert "NPS" not in symbols

    diameter_row = next(row for row in rows if row["symbol"] == "D")
    assert diameter_row == {
        "symbol": "D",
        "definition": "Outside diameter of pipe as measured",
        "value": "114.3 mm (NPS: 4 inch, ASME B36.10)",
    }


def test_nps_row_hidden_before_nominal_pipe_size_entered() -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-inputs-test-nps-await", status=TaskStatus.AWAITING_INPUT)
    task.inputs = {
        "material": EngineeringInput(
            input_id="material",
            value="A106 Gr A",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    }

    rows = build_formula_inputs_table_rows(
        task,
        definition_overrides={"outside_diameter": "Outside diameter of pipe as measured"},
    )
    symbols = [row["symbol"] for row in rows]
    assert "NPS" not in symbols

    diameter_row = next(row for row in rows if row["symbol"] == "D")
    assert diameter_row["definition"] == "Outside diameter of pipe as measured"
    assert "(NPS:" not in diameter_row["definition"]
    assert "NPS" not in diameter_row["value"]
    assert "B36" not in diameter_row["value"]
    assert diameter_row["value"] == AWAITING_USER_INPUT


def test_direct_outside_diameter_keeps_nps_row_hidden_without_nps_suffix() -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-inputs-test-direct-d", status=TaskStatus.AWAITING_INPUT)
    task.inputs = {
        "d_input_mode": EngineeringInput(
            input_id="d_input_mode",
            value="direct_od",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "outside_diameter": EngineeringInput(
            input_id="outside_diameter",
            value=114.3,
            unit="mm",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    }

    rows = build_formula_inputs_table_rows(
        task,
        definition_overrides={"outside_diameter": "Outside diameter of pipe as measured"},
    )
    symbols = [row["symbol"] for row in rows]
    assert "NPS" not in symbols

    diameter_row = next(row for row in rows if row["symbol"] == "D")
    assert diameter_row == {
        "symbol": "D",
        "definition": "Outside diameter of pipe as measured",
        "value": "114.3 mm",
    }


def test_weld_joint_efficiency_includes_joint_category_in_table() -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-inputs-test-e", status=TaskStatus.AWAITING_INPUT)
    task.inputs = {
        "joint_category": EngineeringInput(
            input_id="joint_category",
            value="seamless",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "weld_joint_efficiency": EngineeringInput(
            input_id="weld_joint_efficiency",
            value=1.0,
            unit="dimensionless",
            source=InputSource.TABLE,
            status=InputStatus.CONFIRMED,
        ),
    }

    rows = build_formula_inputs_table_rows(task)
    assert rows[5] == {
        "symbol": "E",
        "definition": "Joint efficiency",
        "value": "1.0 (ASME B31.3 Tables A-1A/A-1B, seamless)",
    }




def test_allowable_stress_value_includes_asme_b31_3_lookup_context() -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-inputs-test-s-lookup", status=TaskStatus.AWAITING_INPUT)
    task.inputs = {
        "material": EngineeringInput(
            input_id="material",
            value="SA-106B",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "design_temperature": EngineeringInput(
            input_id="design_temperature",
            value=400.0,
            unit="F",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    }
    task.outputs = {
        "allowable_stress": 193_000_000,
        "allowable_stress_unit": "Pa",
        "allowable_stress_lookup": {
            "standard": "asme_b31.3",
            "table_id": "asme_b31.3_A-1",
            "material": "SA-106B",
            "design_temperature_f": 400.0,
            "interpolated": False,
        },
    }

    rows = build_formula_inputs_table_rows(task)
    stress_row = next(row for row in rows if row["symbol"] == "S")
    assert stress_row["value"] == "193 MPa (ASME B31.3 Table A-1, ASTM A106 Grade B @ 400 °F)"


def test_build_formula_inputs_table_rows_include_coefficients() -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-inputs-test04", status=TaskStatus.AWAITING_INPUT)
    task.inputs = {
        "weld_joint_efficiency": EngineeringInput(
            input_id="weld_joint_efficiency",
            value=1.0,
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "weld_strength_reduction": EngineeringInput(
            input_id="weld_strength_reduction",
            value=1.0,
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "temperature_coefficient": EngineeringInput(
            input_id="temperature_coefficient",
            value=0.4,
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    }
    task.outputs = {"allowable_stress": 193_000_000, "allowable_stress_unit": "Pa"}

    rows = build_formula_inputs_table_rows(task)
    assert rows[4] == {
        "symbol": "S",
        "definition": "Allowable stress",
        "value": "193 MPa",
    }
    assert rows[5] == {
        "symbol": "E",
        "definition": "Joint efficiency",
        "value": "1.0",
    }
    assert rows[6] == {
        "symbol": "W",
        "definition": "Weld strength reduction",
        "value": "1.0",
    }
    assert rows[7] == {
        "symbol": "Y",
        "definition": "Temperature coefficient",
        "value": "0.4",
    }


def test_definitions_from_equation_variables() -> None:
    overrides = definitions_from_equation_variables(
        [
            {"symbol": "P", "name": "Internal design gage pressure"},
            {"symbol": "D", "name": "Outside diameter of pipe as measured"},
        ]
    )
    assert overrides["design_pressure"] == "Internal design gage pressure"
    assert overrides["outside_diameter"] == "Outside diameter of pipe as measured"


def test_build_formula_inputs_input_table_has_headers() -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-inputs-test05", status=TaskStatus.AWAITING_INPUT)

    table = build_formula_inputs_input_table(task)
    assert table["columns"] == [
        {"key": "symbol", "label": "Symbol", "sortable": False},
        {"key": "definition", "label": "Definition", "sortable": False},
        {"key": "value", "label": "Value", "sortable": False},
    ]
    assert table["rows"] == _ALL_AWAITING_ROWS


def test_primary_formula_inputs_complete(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-inputs-test02", status=TaskStatus.AWAITING_INPUT)
    task.inputs = {
        "material": EngineeringInput(
            input_id="material",
            value="A106 Gr A",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "design_pressure": EngineeringInput(
            input_id="design_pressure",
            value=3.0,
            unit="bar",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "design_temperature": EngineeringInput(
            input_id="design_temperature",
            value=85.0,
            unit="C",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    }
    planning = {"missing_inputs": ["nominal_pipe_size"]}

    assert primary_formula_inputs_complete(task, planning) is True


def test_path_preview_embeds_inputs_table_on_equation(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("eq-inputs-test03", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {
            "path_decision": {
                "pressure_loading": "internal_pressure",
                "selected_node": "B313-304.1.2",
            },
            "missing_inputs": ["design_temperature"],
            "current_phase": "formula_parameters",
        },
    }
    task.inputs = {
        "material": EngineeringInput(
            input_id="material",
            value="A106 Gr A",
            unit="dimensionless",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
        "design_pressure": EngineeringInput(
            input_id="design_pressure",
            value=3.0,
            unit="bar",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    }

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    ids = [block["id"] for block in blocks]
    assert not any(block_id.startswith("path-preview-inputs-table") for block_id in ids)

    equation = next(block for block in blocks if block["id"] == "path-preview-equation-B313-304.1.2")
    assert "variables" not in equation
    assert equation["input_table"]["columns"][0]["label"] == "Symbol"
    assert equation["input_table"]["columns"][1]["label"] == "Definition"
    assert equation["input_table"]["columns"][2]["label"] == "Value"
    assert equation["input_table"]["rows"][0] == {
        "symbol": "",
        "definition": "Design material",
        "value": "ASTM A106 Grade A",
    }
    pressure_row = equation["input_table"]["rows"][1]
    assert pressure_row["symbol"] == "P"
    assert pressure_row["value"] == "3.0 bar"
    assert "pressure" in pressure_row["definition"].lower()
    assert equation["input_table"]["rows"][2]["value"] == AWAITING_USER_INPUT


def test_allowable_stress_not_emitted_as_standalone_result_block(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test10", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "allowable_stress": 193_000_000,
        "allowable_stress_unit": "Pa",
        "planning_summary": {
            "goal": "pipe wall thickness design",
            "action": "request_input",
            "active_definition_node": "B313-304.1.1",
            "path_decision": {
                "pressure_loading": "internal_pressure",
                "selected_node": "B313-304.1.2",
            },
            "missing_inputs": ["design_pressure"],
            "current_phase": "formula_parameters",
        },
    }
    task.active_nodes = ["B313-304.1.1", "B313-304.1.2"]

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    assert not any(
        block["type"] == "result" and "allowable" in str(block.get("title", "")).lower()
        for block in blocks
    )

    equation = next(
        block
        for block in blocks
        if block["type"] == "equation" and block["id"].startswith("path-preview-equation-")
    )
    stress_row = next(row for row in equation["input_table"]["rows"] if row["symbol"] == "S")
    assert stress_row["value"] == "193 MPa"


def test_build_substituted_formula_display_replaces_symbols() -> None:
    from api.equation_inputs_display import build_wall_thickness_substituted_equation

    display, latex = build_wall_thickness_substituted_equation(
        result_value=2.252389391087652,
        result_unit="mm",
        variables_si={
            "P": 3_447_378.65,
            "D": 254.0,
            "S": 193_000_000.0,
            "E": 1.0,
            "W": 1.0,
            "Y": 0.4,
        },
    )

    assert display.startswith("t = ")
    assert display.endswith("= 2.252 mm")
    assert "PD" not in display
    assert "SEW" not in display
    assert "PY" not in display
    assert "(193000000)(1)(1)" in display
    assert "e+" not in display
    assert "e+" not in latex
    assert "\\frac" in latex
    assert "= 2.252\\ \\mathrm{mm}" in latex


def test_build_minimum_thickness_equation_pending_and_complete() -> None:
    from api.equation_inputs_display import build_minimum_thickness_equation

    pending_display, pending_latex = build_minimum_thickness_equation(t_value=0.25946870333750355)
    assert pending_display == "t_m = 0.259 + c"
    assert pending_latex == pending_display

    complete_display, complete_latex = build_minimum_thickness_equation(
        t_value=0.25946870333750355,
        c_value=0.1,
        t_m_value=0.35946870333750355,
        unit="mm",
    )
    assert complete_display == "t_m = 0.259 + 0.100 = 0.359 mm"
    assert "0.359\\ \\mathrm{mm}" in complete_latex
