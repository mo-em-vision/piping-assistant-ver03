"""Flow Guidance Layer tests — ResponseComposer."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.messaging.formula_parameter_prompt import build_formula_parameter_prompt
from engine.messaging.step_prompt import build_step_prompt
from engine.presentation.response_composer import ResponseComposer
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.presentation import (
    GuidanceBlock,
    PresentationBlock,
    append_transcript_blocks,
    rebuild_presentation_snapshot,
)
from models.planning import NavigationPhase, NavigationPlan
from models.task import TaskStatus


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_response_composer_separates_presentation_blocks_from_transcript_blocks() -> None:
    prior_transcript = (
        PresentationBlock(
            block_id="hist-1",
            kind="guidance",
            source="guidance",
            text="Earlier traversal narration.",
        ),
    )
    composer = ResponseComposer()
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-compose-01", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {"workflow": "pipe_wall_thickness_design"}

    response = composer.compose(
        task=task,
        reader=_reader(),
        guidance_blocks=(
            GuidanceBlock(
                block_id="g-1",
                text="Current phase narration.",
                refs={"node_id": "304.1.2-a"},
            ),
        ),
        transcript_blocks=prior_transcript,
    )

    assert response.transcript_blocks[0].block_id == "hist-1"
    assert response.presentation_blocks
    assert response.presentation_blocks is not response.transcript_blocks


def test_transcript_helpers_preserve_append_only_semantics() -> None:
    prior = (
        PresentationBlock(
            block_id="eq-1",
            kind="equation_asset",
            source="messaging",
            text="Equation block from prior turn.",
        ),
    )
    appended = append_transcript_blocks(
        prior,
        (
            PresentationBlock(
                block_id="prompt-2",
                kind="prompt",
                source="messaging",
                text="Next deterministic prompt.",
            ),
        ),
    )
    snapshot = rebuild_presentation_snapshot(
        (
            PresentationBlock(
                block_id="snap-1",
                kind="parameter_request",
                source="presentation_engine",
                text="Current snapshot only.",
            ),
        )
    )

    assert appended[0].block_id == "eq-1"
    assert appended[-1].block_id == "prompt-2"
    assert snapshot[0].block_id == "snap-1"
    assert snapshot[0].block_id not in {block.block_id for block in appended}


def test_response_composer_combines_guidance_and_deterministic_prompt() -> None:
    composer = ResponseComposer()
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-compose-02", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "selected_root": "pipe_wall_thickness_design",
    }
    reader = _reader()
    navigation_plan = NavigationPlan(
        current_phase=NavigationPhase.EXPANSION_ASSUMPTIONS,
        phase_missing={"expansion_assumptions": ["straight_pipe_section"]},
    )
    step_prompt = build_step_prompt(
        reader=reader,
        task=task,
        navigation_plan=navigation_plan,
        missing_input_ids=["straight_pipe_section"],
    )
    assert step_prompt

    response = composer.compose(
        task=task,
        reader=reader,
        guidance_blocks=(
            GuidanceBlock(
                block_id="g-expansion",
                text="Confirming straight pipe applicability before expansion.",
            ),
        ),
        navigation_plan=navigation_plan,
        missing_input_ids=["straight_pipe_section"],
    )

    kinds = {block.kind for block in response.presentation_blocks}
    assert "guidance" in kinds
    assert "prompt" in kinds or response.active_prompt is not None


def test_response_composer_does_not_duplicate_parameter_prompt() -> None:
    composer = ResponseComposer()
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-compose-03", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "selected_root": "pipe_wall_thickness_design",
    }
    reader = _reader()
    formula_prompt = build_formula_parameter_prompt(
        reader=reader,
        task=task,
        navigation_plan=NavigationPlan(current_phase=NavigationPhase.PARAMETER_GATHERING),
        missing_input_ids=["design_pressure"],
    )

    response = composer.compose(
        task=task,
        reader=reader,
        guidance_blocks=(
            GuidanceBlock(
                block_id="g-params",
                text="Collecting design parameters for the active branch.",
            ),
        ),
        navigation_plan=NavigationPlan(current_phase=NavigationPhase.PARAMETER_GATHERING),
        missing_input_ids=["design_pressure"],
    )

    guidance_text = " ".join(
        block.text or ""
        for block in response.presentation_blocks
        if block.kind == "guidance"
    )
    if formula_prompt:
        assert formula_prompt.strip() not in guidance_text


def test_response_composer_output_is_ui_neutral() -> None:
    composer = ResponseComposer()
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-compose-04", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {"workflow": "pipe_wall_thickness_design"}

    response = composer.compose(task=task, reader=_reader())

    payload = response.to_dict()
    assert isinstance(payload["presentation_blocks"], list)
    assert isinstance(payload["transcript_blocks"], list)
    for block in payload["presentation_blocks"]:
        assert isinstance(block, dict)
        assert "block_id" in block
        assert "kind" in block
        assert "rich" not in str(block).lower()
