"""Append-only transcript block tests."""

from __future__ import annotations

from pathlib import Path

from engine.presentation.response_composer import ResponseComposer
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.presentation import (
    PresentationBlock,
    append_transcript_blocks,
    rebuild_presentation_snapshot,
)
from models.task import TaskStatus
from storage.session_store import SessionStore


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def _equation_block() -> PresentationBlock:
    return PresentationBlock(
        block_id="eq-turn-1",
        kind="equation_asset",
        source="messaging",
        text="Governing equation layout from formula parameter prompt.",
        refs={"equation_id": "asme-b313-required-wall-thickness"},
    )


def _guidance_block() -> PresentationBlock:
    return PresentationBlock(
        block_id="guidance-turn-1",
        kind="guidance",
        source="guidance",
        text="The workflow is evaluating the active thickness paragraph.",
        refs={"node_id": "304.1.2-a"},
    )


def test_equation_block_remains_visible_after_next_input() -> None:
    transcript = append_transcript_blocks((), (_equation_block(),))
    next_prompt = PresentationBlock(
        block_id="prompt-turn-2",
        kind="prompt",
        source="messaging",
        text="Please provide design pressure.",
    )
    transcript_after = append_transcript_blocks(transcript, (next_prompt,))

    assert any(block.block_id == "eq-turn-1" for block in transcript_after)
    assert transcript_after[-1].block_id == "prompt-turn-2"


def test_explanation_block_remains_visible_after_next_input() -> None:
    transcript = append_transcript_blocks((), (_guidance_block(),))
    advanced = PresentationBlock(
        block_id="guidance-turn-2",
        kind="guidance",
        source="guidance",
        text="Parameter gathering phase is now active.",
    )
    transcript_after = append_transcript_blocks(transcript, (advanced,))

    assert any(block.block_id == "guidance-turn-1" for block in transcript_after)
    assert transcript_after[-1].block_id == "guidance-turn-2"


def test_current_presentation_snapshot_can_change_without_erasing_transcript() -> None:
    transcript = append_transcript_blocks((), (_guidance_block(), _equation_block(),))
    snapshot_phase_a = rebuild_presentation_snapshot(
        (
            PresentationBlock(
                block_id="snap-a",
                kind="parameter_request",
                source="presentation_engine",
                text="Phase A snapshot.",
            ),
        )
    )
    snapshot_phase_b = rebuild_presentation_snapshot(
        (
            PresentationBlock(
                block_id="snap-b",
                kind="parameter_request",
                source="presentation_engine",
                text="Phase B snapshot.",
            ),
        )
    )

    assert snapshot_phase_a[0].block_id == "snap-a"
    assert snapshot_phase_b[0].block_id == "snap-b"
    assert any(block.block_id == "guidance-turn-1" for block in transcript)
    assert any(block.block_id == "eq-turn-1" for block in transcript)


def test_session_store_append_message_persists_transcript_blocks(tmp_path) -> None:
    store = SessionStore(tmp_path / "sessions", session_id="guidance-transcript")
    blocks = [_guidance_block(), _equation_block()]
    store.append_message(
        "assistant",
        "legacy flat message",
        transcript_blocks=[block.to_dict() for block in blocks],
    )
    loaded = store.load_conversation()

    assert loaded[0].get("transcript_blocks")
    assert len(loaded[0]["transcript_blocks"]) == 2


def test_response_composer_compose_returns_presentation() -> None:
    composer = ResponseComposer()
    manager = TaskStateManager()
    task = manager.create_task("transcript-01", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {"workflow": "pipe_wall_thickness_design"}

    response = composer.compose(
        task=task,
        reader=_reader(),
        transcript_blocks=(_guidance_block(),),
        guidance_blocks=(),
    )

    assert response.presentation_blocks is not None
    assert response.transcript_blocks[0].block_id == "guidance-turn-1"
