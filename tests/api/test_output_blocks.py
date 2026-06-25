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

    assert not any(block_id.startswith("node-activation-") for block_id in ids)
    assert types.count("equation") == 3
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
    assert substituted.get("leading_result") == {"value": "2.252", "unit": "mm"}
    assert substituted["display"].startswith("2.252 mm  t = ")
    assert "input_table" not in substituted
    assert "SEW" not in substituted["display"]

    minimum = next(block for block in blocks if block["id"] == "minimum-thickness-equation")
    assert minimum["display"] == "t_m = 2.252 + 0.500 = 2.752 mm"

    summary = next(block for block in blocks if block["id"] == "required-thickness-summary")
    assert summary["content"] == "Required wall thickness: 2.252 mm."

    conclusion = next(block for block in blocks if block["id"] == "minimum-thickness-conclusion")
    assert "Minimum required pipe wall thickness is 2.752 mm." in conclusion["content"]


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


def test_post_calculation_outputs_before_corrosion_allowance(standards_reader, state_manager) -> None:
    from tests.acceptance.helpers import run_completed_workflow

    task_id = "pipe-wall-thickness-desi-test12"
    run_completed_workflow(state_manager, standards_reader, task_id)
    task = state_manager.get_task(task_id)
    task.inputs.pop("corrosion_allowance", None)
    task.outputs.pop("minimum_required_thickness", None)
    task.outputs.pop("t_m", None)
    task.status = TaskStatus.AWAITING_INPUT
    state_manager.replace_task(task_id, task)

    blocks = build_display_outputs(task)
    ids = [block["id"] for block in blocks]

    assert "path-preview-equation-B313-304.1.2" in ids
    assert "path-calculation-substituted-equation" in ids
    assert "minimum-thickness-equation" in ids
    assert "required-thickness-summary" in ids
    assert "minimum-thickness-conclusion" not in ids
    assert not any(block_id.startswith("node-activation-") for block_id in ids)

    minimum = next(block for block in blocks if block["id"] == "minimum-thickness-equation")
    assert minimum["display"].endswith("+ c")
    assert "2.252" in minimum["display"]


def test_execution_trace_keeps_definition_node_outputs(standards_reader) -> None:
    from tests.acceptance.helpers import run_completed_workflow

    manager = TaskStateManager()
    task_id = "pipe-wall-thickness-desi-test11"
    run_completed_workflow(manager, standards_reader, task_id)
    task = manager.get_task(task_id)
    task.outputs.pop("required_thickness", None)
    task.outputs.pop("t", None)
    task.outputs.pop("minimum_required_thickness", None)
    task.outputs.pop("t_m", None)
    task.outputs.pop("_execution_trace", None)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    ids = [block["id"] for block in blocks]

    assert any(block_id.startswith("node-activation-equation-B313-304.1.1") for block_id in ids)
    assert "equation-B313-304.1.2" not in ids
