"""Tests for compact node provenance payloads."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.node_provenance import (
    enrich_display_blocks_provenance,
    provenance_for_node,
    step_provenance,
)
from api.output_blocks import build_display_outputs
from api.serializers import task_state
from api.workflow_bootstrap import bootstrap_new_task
from config.loader import CLIConfig
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus


@pytest.fixture
def standards_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def test_provenance_for_node_shape(standards_reader: StandardsReader) -> None:
    provenance = provenance_for_node(standards_reader, "B313-304.1.1")

    assert provenance is not None
    assert provenance["node_id"] == "B313-304.1.1"
    assert provenance["paragraph"] == "304.1.1"
    assert provenance["hover_excerpt"]
    assert provenance["standard"] == "ASME B31.3"


def test_provenance_for_node_includes_source_field(standards_reader: StandardsReader) -> None:
    provenance = provenance_for_node(standards_reader, "B313-304.1.1", source_field="purpose")

    assert provenance is not None
    assert provenance["source_field"] == "purpose"


def test_enrich_display_blocks_provenance_from_source_node(standards_reader: StandardsReader) -> None:
    blocks = [
        {
            "id": "reference-B313-304.1.2",
            "type": "reference",
            "source_node": "B313-304.1.2",
            "excerpt": "Example excerpt",
        }
    ]
    enrich_display_blocks_provenance(blocks, standards_reader)

    assert blocks[0]["provenance"]["node_id"] == "B313-304.1.2"
    assert blocks[0]["provenance"]["hover_excerpt"]
    assert blocks[0]["provenance"]["source_field"] == "purpose"


def test_display_outputs_include_provenance(standards_reader: StandardsReader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-prov-01", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {
            "goal": "pipe wall thickness design",
            "action": "request_input",
            "active_definition_node": "B313-304.1.1",
            "missing_inputs": ["material"],
            "current_phase": "parameter_gathering",
        },
    }
    task.active_nodes = ["B313-304.1.1"]
    manager.replace_task(task.task_id, task)

    blocks = build_display_outputs(task, standards_root=standards_reader.standards_root)
    with_provenance = [block for block in blocks if block.get("provenance")]

    assert with_provenance
    assert all(block["provenance"]["node_id"] for block in with_provenance)
    assert all(block["provenance"]["hover_excerpt"] for block in with_provenance)


def test_task_state_timeline_and_parameters_include_provenance(
    standards_reader: StandardsReader,
) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-prov-02", status=TaskStatus.AWAITING_INPUT)
    config = CLIConfig(
        report_format="html",
        language="english",
        default_standard="ASME_B31.3",
        sessions_dir=Path("sessions"),
        standards_root=standards_reader.standards_root,
        openai_api_key=None,
        openai_model="gpt-4o-mini",
        openai_base_url=None,
    )
    bootstrap_new_task(task, "pipe_wall_thickness_design", config)
    manager.replace_task(task.task_id, task)

    state = task_state(task, manager, standards_root=standards_reader.standards_root)
    timeline_with_provenance = [step for step in state["progress"]["timeline"] if step.get("provenance")]
    parameters_with_provenance = [item for item in state["parameters"] if item.get("provenance")]

    assert timeline_with_provenance
    assert parameters_with_provenance
    assert timeline_with_provenance[0]["provenance"]["node_id"]
    assert any(step["provenance"].get("hover_excerpt") for step in timeline_with_provenance)
    assert any(item["provenance"].get("hover_excerpt") for item in parameters_with_provenance)
    assert any(item["provenance"].get("source_field") for item in parameters_with_provenance)


def test_step_provenance_for_calculation_step(standards_reader: StandardsReader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("pipe-wall-thickness-prov-03", status=TaskStatus.AWAITING_INPUT)
    task.outputs = {
        "workflow": "pipe_wall_thickness_design",
        "planning_summary": {"active_definition_node": "B313-304.1.1"},
    }
    task.active_nodes = ["B313-304.1.1"]
    manager.replace_task(task.task_id, task)

    provenance = step_provenance(standards_reader, task, "thickness", task.outputs["planning_summary"])

    assert provenance is not None
    assert provenance["node_id"] == "B313-304.1.1"
    assert provenance["source_field"] == "purpose"
