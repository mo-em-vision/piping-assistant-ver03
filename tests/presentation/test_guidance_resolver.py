"""Flow Guidance Layer tests — GuidanceResolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.presentation.guidance_resolver import (
    GuidanceResolver,
    GuidanceValidationError,
    validate_guidance_text,
)
from models.engineering_plan import PlannerTraversalState, TraversalActiveNode, TraversalEvent
from models.presentation import GuidanceContext

_GUIDANCE_YAML = Path(__file__).resolve().parents[2] / "presentation" / "guidance" / "workflows" / "pipe_wall_thickness_design.yaml"


def _pressure_design_case_context() -> GuidanceContext:
    return GuidanceContext(
        workflow_id="pipe_wall_thickness_design",
        current_phase="path_decisions",
        active_node_id="304.1.2-a",
        node_role="paragraph",
        traversal_event="branch_decision_required",
        edge_reason="pressure_design_case",
        task_facts={},
    )


def test_guidance_resolver_returns_traversal_narration_for_matching_context() -> None:
    resolver = GuidanceResolver()
    context = _pressure_design_case_context()

    blocks = resolver.resolve(context)

    assert blocks
    assert blocks[0].source == "guidance"
    assert blocks[0].kind == "guidance"
    assert "internal versus external" in blocks[0].text.lower()
    assert blocks[0].refs.get("node_id") == "304.1.2-a"


def test_guidance_yaml_does_not_duplicate_parameter_prompt_copy() -> None:
    forbidden = "Please provide: design pressure. Is the pipe subject to internal or external pressure?"

    with pytest.raises(GuidanceValidationError, match="parameter prompt"):
        validate_guidance_text(forbidden)


def test_guidance_block_may_reference_equation_but_not_duplicate_formula_text() -> None:
    validate_guidance_text(
        "The governing thickness equation on the active path will be used next.",
        refs={"equation_id": "asme-b313-304-1-2-eq-3a"},
    )

    with pytest.raises(GuidanceValidationError, match="formula"):
        validate_guidance_text(
            r"t = \frac{P D}{2 S E}",
            refs={"equation_id": "asme-b313-304-1-2-eq-3a"},
        )


def test_guidance_resolver_does_not_use_planner_message_as_guidance() -> None:
    traversal = PlannerTraversalState(
        traversal_id="trav-test",
        current_active_node_id="304.1.2-a",
        current_active_node=TraversalActiveNode(
            node_id="304.1.2-a",
            node_type="equation",
            reason="DEBUG ONLY: internal planner message must not appear in guidance",
        ),
        traversal_events=[
            TraversalEvent(
                order=1,
                event_type="node_selected",
                node_id="304.1.2-a",
                message="DEBUG ONLY: planner traversal event message",
            )
        ],
    )
    resolver = GuidanceResolver()
    context = GuidanceContext(
        workflow_id="pipe_wall_thickness_design",
        current_phase="parameter_gathering",
        active_node_id=traversal.current_active_node_id,
        node_role="equation",
        traversal_event="node_selected",
    )

    blocks = resolver.resolve(context)

    combined = " ".join(block.text for block in blocks)
    assert "DEBUG ONLY" not in combined
    assert "planner traversal event message" not in combined.lower()


def test_guidance_fixture_yaml_exists() -> None:
    assert _GUIDANCE_YAML.is_file()


def test_mawp_guidance_yaml_narration_without_formula() -> None:
    mawp_yaml = (
        Path(__file__).resolve().parents[2]
        / "presentation"
        / "guidance"
        / "workflows"
        / "mawp_design.yaml"
    )
    assert mawp_yaml.is_file()
    text = mawp_yaml.read_text(encoding="utf-8").lower()
    assert "mawp =" not in text
    assert "2sewt" not in text.replace(" ", "")

    resolver = GuidanceResolver()
    context = GuidanceContext(
        workflow_id="mawp_design",
        current_phase="path_decisions",
        active_node_id="304.1.2-a",
        node_role="paragraph",
        traversal_event="branch_decision_required",
        edge_reason="wall_thickness_basis",
        task_facts={},
    )
    blocks = resolver.resolve(context)
    assert blocks
    assert "thickness basis" in blocks[0].text.lower()
