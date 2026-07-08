"""Presentation engine tests (Phase 9)."""

from __future__ import annotations

import inspect
from pathlib import Path

from engine.executor.executor import execute_workflow
from engine.presentation.presentation_engine import build_presentation
from engine.reference.standards_reader import StandardsReader
from engine.state import TaskStateManager
from engine.state.workflow_state import build_workflow_state
from models.input import EngineeringInput, InputSource, InputStatus
from models.workflow_state import WorkflowParameter, WorkflowState
from tests.acceptance.helpers import sample_inputs
from tests.helpers.facts import fact_get_value
from models.fact import SourceType, ValidationStatus


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def _minimal_state(
    *,
    warnings: tuple[str, ...] = (),
    parameters: dict[str, WorkflowParameter] | None = None,
    lookup_results: dict | None = None,
) -> WorkflowState:
    return WorkflowState(
        task_id="presentation-test",
        workflow_id="pipe_wall_thickness_design",
        parameters=parameters or {},
        warnings=warnings,
        lookup_results=lookup_results or {},
    )


def test_build_presentation_does_not_accept_task() -> None:
    signature = inspect.signature(build_presentation)
    assert "task" not in signature.parameters
    assert "Task" not in str(signature)


def test_warnings_render_as_warning_blocks() -> None:
    reader = _reader()
    state = _minimal_state(warnings=("Review corrosion allowance.",))
    blocks = build_presentation(state, reader.graph_store)
    warning_blocks = [block for block in blocks if block["type"] == "warning"]
    assert warning_blocks
    assert warning_blocks[0]["text"] == "Review corrosion allowance."


def test_pending_parameter_renders_parameter_request_block() -> None:
    reader = _reader()
    param = WorkflowParameter(
        name="design_pressure",
        value=None,
        dimension="pressure",
        unit="psi",
        priority=10,
        source="user_input",
        status="pending",
        symbol="P",
        canonical_unit="UNIT-Pa",
        allowed_units=("UNIT-psi", "UNIT-Pa"),
        unit_id="UNIT-psi",
    )
    state = _minimal_state(parameters={"design_pressure": param})
    blocks = build_presentation(state, reader.graph_store)
    request_blocks = [block for block in blocks if block["type"] == "parameter_request"]
    assert len(request_blocks) == 1
    block = request_blocks[0]
    assert block["parameter_id"] == "design_pressure"
    assert block["symbol"] == "P"
    assert "UNIT-psi" in block["allowed_units"]
    assert block["canonical_unit"] == "UNIT-Pa"


def test_lookup_result_renders_lookup_block() -> None:
    reader = _reader()
    state = _minimal_state(
        lookup_results={
            "allowable_stress_lookup": {
                "table": "A-1",
                "value": 193_000_000.0,
                "unit": "Pa",
            }
        }
    )
    blocks = build_presentation(state, reader.graph_store)
    lookup_blocks = [block for block in blocks if block["type"] == "lookup_result"]
    assert len(lookup_blocks) == 1
    block = lookup_blocks[0]
    assert block["lookup_id"] == "allowable_stress_lookup"
    assert block["table"] == "A-1"
    assert block["value"] == 193_000_000.0
    assert block["unit"] == "Pa"


def test_execute_workflow_produces_graph_native_presentation_blocks() -> None:
    manager = TaskStateManager()
    reader = _reader()
    task_id = "presentation-pipe-wall"
    manager.create_task(task_id)
    for engineering_input in sample_inputs().values():
        manager.store_input(task_id, engineering_input)

    execute_workflow(
        task_id,
        "pipe_wall_thickness_design",
        state=manager,
        reader=reader,
    )

    workflow_state = manager.get_workflow_state(task_id, reader=reader)
    blocks = workflow_state.presentation_blocks
    assert blocks
    block_types = {block["type"] for block in blocks}
    assert block_types & {"paragraph", "symbol_table", "equation_result", "warning", "lookup_result"}


def test_presentation_equation_result_includes_render_steps() -> None:
    manager = TaskStateManager()
    reader = _reader()
    task_id = "presentation-equation-steps"
    manager.create_task(task_id)
    for engineering_input in sample_inputs().values():
        manager.store_input(task_id, engineering_input)

    execute_workflow(
        task_id,
        "pipe_wall_thickness_design",
        state=manager,
        reader=reader,
    )

    workflow_state = manager.get_workflow_state(task_id, reader=reader)
    equation_blocks = [
        block
        for block in workflow_state.presentation_blocks
        if block.get("type") == "equation_result"
    ]
    assert equation_blocks
    steps = equation_blocks[0].get("steps")
    assert isinstance(steps, dict)
    assert {"original", "substituted", "simplified", "evaluated"} <= set(steps.keys())
    assert steps["original"]
    assert steps["evaluated"]
    equation_display_trace = equation_blocks[0].get("equation_display_trace")
    if isinstance(equation_display_trace, dict):
        assert equation_display_trace.get("status") in {"evaluated", "blocked"}


def test_workflow_state_builder_attaches_presentation_blocks() -> None:
    manager = TaskStateManager()
    reader = _reader()
    task_id = "presentation-wf-builder"
    manager.create_task(task_id)
    manager.store_input(
        task_id,
        EngineeringInput(
            input_id="design_pressure",
            value=500,
            unit="psi",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
        ),
    )
    manager.store_output(task_id, "workflow", "pipe_wall_thickness_design")
    manager.add_warning(task_id, "Check design temperature.")
    task = manager.get_task(task_id)

    workflow_state = build_workflow_state(
        task,
        reader=reader,
        step_progress=manager.list_step_progress(task_id),
    )
    assert workflow_state.presentation_blocks
    assert workflow_state.version == "5"
    assert any(block["type"] == "warning" for block in workflow_state.presentation_blocks)
