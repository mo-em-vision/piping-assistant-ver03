"""Tests for desktop display output blocks."""

from __future__ import annotations

from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus

from api.output_blocks import build_display_outputs
from api.serializers import task_state
from tests.acceptance.helpers import run_completed_workflow


def test_preview_outputs_for_awaiting_input_task(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test06", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {
            "goal": "pipe wall thickness design",
            "action": "request_input",
            "active_definition_node": "B313-304.1.1",
            "missing_inputs": ["material", "design_pressure"],
            "missing_assumptions": ["straight_pipe_section"],
            "current_phase": "expansion_assumptions",
            "phase_missing": {"expansion_assumptions": ["straight_pipe_section"]},
        },
    }
    task.active_nodes = ["B313-304.1.1"]
    manager.replace_task(task.task_id, task)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    types = {block["type"] for block in blocks}

    assert "equation" in types
    assert "table" not in types
    assert any(block["id"].startswith("node-activation-") for block in blocks)


def test_completed_workflow_outputs_include_results_and_equation(
    standards_reader,
    state_manager,
) -> None:
    task_id = "pipe-wall-thickness-desi-test07"
    run_completed_workflow(state_manager, standards_reader, task_id)
    task = state_manager.get_task(task_id)

    blocks = build_display_outputs(task)
    types = [block["type"] for block in blocks]
    ids = [block["id"] for block in blocks]

    assert types.count("equation") == 2
    assert "path-preview-equation-B313-304.1.2" in ids
    assert "path-calculation-substituted-equation" in ids
    assert "result" not in types
    assert "table" not in types
    assert "graph" not in types
    assert "reference" not in types
    assert "planning-status" not in ids

    preview = next(block for block in blocks if block["id"] == "path-preview-equation-B313-304.1.2")
    assert "input_table" in preview
    assert preview["input_table"]["rows"]

    substituted = next(
        block for block in blocks if block["id"] == "path-calculation-substituted-equation"
    )
    assert "leading_result" not in substituted
    assert substituted["display"].startswith("t = ")
    assert " = " in substituted["display"]
    assert substituted["display"].rstrip().endswith("mm")
    assert "input_table" not in substituted
    assert "SEW" not in substituted["display"]
    assert "(1)(1)" in substituted["display"] or "(1.0)(1)" in substituted["display"]
    assert "e+" not in substituted["content"]


def test_task_state_includes_display_outputs(
    standards_reader,
    state_manager,
) -> None:
    task_id = "pipe-wall-thickness-desi-test08"
    run_completed_workflow(state_manager, standards_reader, task_id)
    task = state_manager.get_task(task_id)

    state = task_state(task, state_manager)
    assert isinstance(state["display_outputs"], list)
    assert len(state["display_outputs"]) > 0


def test_path_preview_equation_resolves_variable_descriptions(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-desi-test09", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {
            "goal": "pipe wall thickness design",
            "action": "request_input",
            "active_definition_node": "B313-304.1.1",
            "path_decision": {
                "pressure_loading": "internal_pressure",
                "selected_node": "B313-304.1.2",
            },
            "missing_inputs": ["material", "design_pressure"],
            "current_phase": "formula_parameters",
        },
    }
    task.active_nodes = ["B313-304.1.1", "B313-304.1.2"]

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    equation_blocks = [
        block
        for block in blocks
        if block["type"] == "equation" and block["id"].startswith("path-preview-equation-")
    ]
    assert len(equation_blocks) == 1

    intro_blocks = [block for block in blocks if block["id"] == "path-preview-intro-B313-304.1.2"]
    assert len(intro_blocks) == 1
    intro = intro_blocks[0]
    assert intro["type"] == "text"
    assert "minimum required wall thickness" in intro["content"].lower()
    assert intro["content_suffix"] == " with the following equation:"
    assert intro["reference_links"][0]["node_id"] == "B313-304.1.2"
    assert intro["reference_links"][0]["label"] == "§304.1.2"
    assert not any(block["type"] == "reference" for block in blocks if block["id"].startswith("path-preview-"))

    equation = equation_blocks[0]
    assert equation.get("title") is None
    assert "variables" not in equation
    assert "input_table" in equation
    pressure_row = next(row for row in equation["input_table"]["rows"] if row["symbol"] == "P")
    assert pressure_row["definition"] == "Internal design gage pressure"
    assert pressure_row["value"] == "Awaiting user input"

    nomenclature_reference = equation.get("nomenclature_reference")
    assert nomenclature_reference is not None
    assert nomenclature_reference["node_id"] == "B313-304.1.1"
    assert nomenclature_reference["label"] == "§304.1.1(b)"
