"""Generic center panel display sequence tests."""

from __future__ import annotations

import inspect

from api.display_block_metadata import equation_display_block_id
from api.equation_evaluation_display import build_equation_evaluation_block
from api.output_blocks import build_display_outputs
from api.result_summary_display import build_result_summary_display_block
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.api.test_equation_display_trace import (
    EQ_2_ID,
    EQ_3A_ID,
    _apply_simulated_completed_state,
)
from tests.helpers.goals import task_with_planning


def test_stable_equation_block_id_matches_equation_node(standards_reader) -> None:
    assert equation_display_block_id(EQ_3A_ID) == f"equation-{EQ_3A_ID}"


def test_build_equation_evaluation_block_uses_stable_id(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("stable-eq-id", status=TaskStatus.AWAITING_INPUT)
    planning = {"path_decision": {"selected_node": "304.1.2-a"}}
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")

    block = build_equation_evaluation_block(task, standards_reader, "304.1.2-a")
    assert block is not None
    assert block["id"] == equation_display_block_id(EQ_3A_ID)
    assert block.get("lifecycle") == "durable"


def test_paragraph_context_emitted_for_focus(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("paragraph-focus", status=TaskStatus.AWAITING_INPUT)
    planning = {
        "path_decision": {"selected_node": "304.1.2-a"},
        "current_phase": "formula_parameters",
    }
    task_with_planning(task, planning, workflow_id="pipe_wall_thickness_design")

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    paragraph_ids = [block["id"] for block in blocks if block["id"].startswith("paragraph-")]
    assert "paragraph-304.1.2-a" in paragraph_ids


def test_result_summary_structured_payload(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("result-summary", status=TaskStatus.COMPLETED)
    _apply_simulated_completed_state(task, standards_reader)

    block = build_result_summary_display_block(task, standards_reader)
    assert block is not None
    payload = block.get("payload") or {}
    assert payload.get("primary_result", {}).get("value")
    assert isinstance(payload.get("assumptions"), list)
    assert isinstance(payload.get("warnings"), list)


def test_no_pipe_wall_literals_in_generic_display_modules() -> None:
    from api import equation_evaluation_display, output_blocks, paragraph_display, result_summary_display

    for module in (
        equation_evaluation_display,
        output_blocks,
        paragraph_display,
        result_summary_display,
    ):
        source = inspect.getsource(module)
        assert "pipe_wall_thickness_design" not in source
        assert "304.1.2-a" not in source


def test_post_eval_emits_both_equations_with_stable_ids(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("both-equations", status=TaskStatus.AWAITING_INPUT)
    _apply_simulated_completed_state(task, standards_reader)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    equation_ids = {
        block["id"]
        for block in blocks
        if block.get("type") == "equation"
    }
    assert equation_display_block_id(EQ_2_ID) in equation_ids
    assert equation_display_block_id(EQ_3A_ID) in equation_ids
    assert not any(block_id.startswith("path-preview-equation-") for block_id in equation_ids)
    assert not any(block_id.startswith("equation-trace-") for block_id in equation_ids)
