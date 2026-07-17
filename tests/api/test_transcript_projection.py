"""Tests for read-time transcript projection (immutable stored history)."""

from __future__ import annotations

from api.transcript_projection import project_transcript_blocks_for_display


def test_project_legacy_title_and_description_to_workflow_intro() -> None:
    transcript = [
        {
            "block_id": "workflow-title-pipe_wall_thickness_design",
            "kind": "text",
            "source": "workflow_node",
            "text": "Pipe Wall Thickness Design",
            "payload": {"display_role": "title"},
        },
        {
            "block_id": "workflow-description-pipe_wall_thickness_design",
            "kind": "text",
            "source": "workflow_node",
            "text": "Determine minimum required pipe wall thickness.",
            "payload": {"display_role": "workflow_description"},
        },
    ]

    projected = project_transcript_blocks_for_display(transcript)

    assert len(projected) == 1
    assert projected[0]["block_id"] == "workflow-intro-pipe_wall_thickness_design"
    assert projected[0]["payload"]["display_role"] == "workflow_intro"
    assert projected[0]["payload"]["title"] == "Pipe Wall Thickness Design"
    assert "Pipe Wall Thickness Design" in projected[0]["text"]
    assert "Determine minimum required pipe wall thickness." in projected[0]["text"]


def test_project_prefers_native_workflow_intro_and_hides_legacy_pair() -> None:
    transcript = [
        {
            "block_id": "workflow-title-pipe_wall_thickness_design",
            "kind": "text",
            "source": "workflow_node",
            "text": "Legacy title",
            "payload": {"display_role": "title"},
        },
        {
            "block_id": "workflow-intro-pipe_wall_thickness_design",
            "kind": "text",
            "source": "workflow_node",
            "text": "Native intro.",
            "payload": {"display_role": "workflow_intro", "title": "Native title"},
        },
        {
            "block_id": "workflow-description-pipe_wall_thickness_design",
            "kind": "text",
            "source": "workflow_node",
            "text": "Legacy description",
            "payload": {"display_role": "workflow_description"},
        },
    ]

    projected = project_transcript_blocks_for_display(transcript)

    assert len(projected) == 1
    assert projected[0]["block_id"] == "workflow-intro-pipe_wall_thickness_design"
    assert projected[0]["text"] == "Native intro."


def test_project_does_not_mutate_input_transcript() -> None:
    transcript = [
        {
            "block_id": "workflow-title-pipe_wall_thickness_design",
            "kind": "text",
            "source": "workflow_node",
            "text": "Pipe Wall Thickness Design",
            "payload": {"display_role": "title"},
        },
        {
            "block_id": "workflow-description-pipe_wall_thickness_design",
            "kind": "text",
            "source": "workflow_node",
            "text": "Description text.",
            "payload": {"display_role": "workflow_description"},
        },
    ]
    original_ids = [block["block_id"] for block in transcript]

    project_transcript_blocks_for_display(transcript)

    assert [block["block_id"] for block in transcript] == original_ids
