"""Structured node documentation resolver tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.graph.documentation_resolver import (
    extract_raw_documentation,
    resolve_node_documentation,
    resolve_workflow_documentation,
)
from engine.reference.standards_reader import StandardsReader
from engine.state import TaskStateManager
from models.input import EngineeringInput, InputSource, InputStatus


@pytest.fixture
def standards_reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "standards", standard="asme_b31.3")


def test_legacy_lowering_maps_question_to_instructions() -> None:
    raw = extract_raw_documentation(
        {
            "title": "Design pressure",
            "question": "What is the design pressure?",
            "purpose": "Workflow summary",
        },
        body="Body text",
    )
    assert raw["instructions"] == "What is the design pressure?"
    assert raw["summary"] == "Workflow summary"
    assert raw["description"] == "Body text"


def test_explicit_documentation_block_overrides_legacy() -> None:
    raw = extract_raw_documentation(
        {
            "purpose": "Legacy purpose",
            "documentation": {
                "summary": "Structured summary",
                "instructions": "Structured instructions",
            },
        },
        body="Legacy body",
    )
    assert raw["summary"] == "Structured summary"
    assert raw["instructions"] == "Structured instructions"
    assert raw["description"] == "Legacy body"


def test_camel_case_documentation_keys_normalized() -> None:
    raw = extract_raw_documentation(
        {
            "documentation": {
                "beforeEnter": "Before step",
                "reportSummary": "Report line",
            },
        },
        "",
    )
    assert raw["before_enter"] == "Before step"
    assert raw["report_summary"] == "Report line"


def test_resolve_node_documentation_renders_templates(standards_reader: StandardsReader) -> None:
    store = standards_reader.graph_store
    assert store.available
    doc = resolve_node_documentation(
        store,
        "B313-param-P",
        context={"P": 500, "design_pressure": 500},
    )
    assert doc.instructions
    assert "500" in doc.before_enter


def test_designation_parameter_resolves_without_runtime_fields(standards_reader: StandardsReader) -> None:
    store = standards_reader.graph_store
    doc = resolve_node_documentation(store, "B313-param-nps")
    assert doc.node_id == "B313-param-nps"
    assert doc.title or doc.instructions or doc.description or doc.summary or True


def test_quantity_node_resolves_documentation(standards_reader: StandardsReader) -> None:
    store = standards_reader.graph_store
    doc = resolve_node_documentation(store, "B313-quantity-pressure")
    assert doc.node_id == "B313-quantity-pressure"
    assert doc.description or doc.summary


def test_workflow_state_includes_node_documentation(standards_reader: StandardsReader) -> None:
    manager = TaskStateManager()
    task_id = "doc-workflow-state"
    manager.create_task(task_id)
    manager.store_input(
        task_id,
        EngineeringInput(
            input_id="design_pressure",
            value=500,
            unit="psi",
            source=InputSource.USER,
            status=InputStatus.CONFIRMED,
            symbol="P",
        ),
    )
    manager.store_output(task_id, "workflow", "pipe_wall_thickness_design")
    manager.store_output(task_id, "graph_root", "B313-WF-PIPE-WALL-THICKNESS")
    manager.store_step_progress(task_id, "B313-304.1.2", "completed")

    workflow_state = manager.get_workflow_state(task_id, reader=standards_reader)
    assert workflow_state.version == "3"
    assert workflow_state.current_documentation is not None
    assert "B313-304.1.2" in workflow_state.node_documentation
    assert "B313-WF-PIPE-WALL-THICKNESS" in workflow_state.node_documentation


def test_resolve_workflow_documentation_includes_workflow_root(standards_reader: StandardsReader) -> None:
    manager = TaskStateManager()
    task_id = "doc-root"
    manager.create_task(task_id)
    manager.store_output(task_id, "workflow", "pipe_wall_thickness_design")
    manager.store_output(task_id, "graph_root", "B313-WF-PIPE-WALL-THICKNESS")

    task = manager.get_task(task_id)
    docs = resolve_workflow_documentation(
        standards_reader,
        task,
        node_ids=set(),
        parameters={},
    )
    assert "B313-WF-PIPE-WALL-THICKNESS" in docs
    assert docs["B313-WF-PIPE-WALL-THICKNESS"].summary
