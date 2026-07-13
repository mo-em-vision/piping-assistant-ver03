"""Presentation / Flow Guidance must not mutate engineering truth."""

from __future__ import annotations

from pathlib import Path

from api.flow_guidance import build_flow_guidance_payload
from engine.presentation.guidance_resolver import validate_guidance_text
from engine.presentation.response_composer import ResponseComposer
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.planning import NavigationPhase, NavigationPlan
from models.presentation import GuidanceBlock
from models.task import TaskStatus
from tests.api.test_equation_display_trace import _apply_simulated_completed_state
from tests.helpers.engineering_snapshot import engineering_truth_snapshot


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_flow_guidance_does_not_mutate_engineering_truth() -> None:
    standards_reader = _reader()
    manager = TaskStateManager()
    task = manager.create_task("presentation-immutability", status=TaskStatus.AWAITING_INPUT)
    _apply_simulated_completed_state(task, standards_reader)
    task.warnings.append("Corrosion allowance exceeds typical project default.")

    before = engineering_truth_snapshot(task, standards_reader)
    payload = build_flow_guidance_payload(task, standards_reader)
    after = engineering_truth_snapshot(task, standards_reader)

    assert before == after
    assert payload.get("presentation_blocks") is not None

    warning_texts = [
        str(block.get("text") or "")
        for block in payload.get("presentation_blocks") or []
        if block.get("kind") == "warning"
    ]
    assert warning_texts == list(task.warnings)

    for block in payload.get("presentation_blocks") or []:
        if block.get("kind") != "guidance":
            continue
        validate_guidance_text(
            str(block.get("text") or ""),
            refs=block.get("refs") or {},
        )
        text = str(block.get("text") or "")
        assert "999.888" not in text
        assert r"\frac" not in text


def test_response_composer_preserves_warnings_and_engineering_outputs() -> None:
    standards_reader = _reader()
    manager = TaskStateManager()
    task = manager.create_task("composer-immutability", status=TaskStatus.AWAITING_INPUT)
    _apply_simulated_completed_state(task, standards_reader)
    task.warnings.extend(
        [
            "Review weld joint efficiency selection.",
            "Design temperature is near material limit.",
        ]
    )

    before = engineering_truth_snapshot(task, standards_reader)
    composer = ResponseComposer()
    response = composer.compose(
        task=task,
        reader=standards_reader,
        guidance_blocks=(
            GuidanceBlock(
                block_id="guidance-immutability",
                text="The workflow is advancing through the governing thickness path.",
                refs={"node_id": "304.1.2-a"},
            ),
        ),
        navigation_plan=NavigationPlan(current_phase=NavigationPhase.READY),
        validation_warnings=tuple(task.warnings),
    )
    after = engineering_truth_snapshot(task, standards_reader)

    assert before == after
    warning_texts = [
        block.text for block in response.presentation_blocks if block.kind == "warning"
    ]
    assert warning_texts == list(task.warnings)
    assert all("2.252" not in (block.text or "") for block in response.presentation_blocks)
