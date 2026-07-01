"""Workflow lifecycle emitter tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.execution.lifecycle_emitter import (
    WorkflowLifecycleEmitter,
    is_executable_node,
    parse_lifecycle_events,
)
from engine.reference.standards_reader import StandardsReader
from models.workflow_lifecycle import WorkflowLifecycleEventType


@pytest.fixture
def standards_reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_lifecycle_event_type_values() -> None:
    assert WorkflowLifecycleEventType.BEFORE_ENTER.value == "beforeEnter"
    assert WorkflowLifecycleEventType.ON_ENTER.value == "onEnter"
    assert WorkflowLifecycleEventType.ON_EXECUTE.value == "onExecute"
    assert WorkflowLifecycleEventType.ON_EXIT.value == "onExit"
    assert WorkflowLifecycleEventType.ON_ERROR.value == "onError"


def test_is_executable_node_for_equation_only() -> None:
    assert is_executable_node({"type": "equation"}, "equation")
    assert not is_executable_node({"type": "parameter"}, "parameter")
    assert not is_executable_node({"type": "workflow"}, "workflow")


def test_emit_before_enter_renders_template(standards_reader: StandardsReader) -> None:
    store = standards_reader.graph_store
    assert store.available
    emitter = WorkflowLifecycleEmitter(store)
    event = emitter.emit_before_enter(
        "B313-param-P",
        context={"P": 500, "design_pressure": 500},
    )
    assert event.event == WorkflowLifecycleEventType.BEFORE_ENTER
    assert "500" in event.message


def test_emit_on_exit_includes_after_exit_payload(standards_reader: StandardsReader) -> None:
    store = standards_reader.graph_store
    emitter = WorkflowLifecycleEmitter(store)
    emitter.emit_on_exit("B313-param-P", context={"P": 1})
    event = emitter.events[-1]
    assert event.event == WorkflowLifecycleEventType.ON_EXIT


def test_parse_lifecycle_events_round_trip(standards_reader: StandardsReader) -> None:
    store = standards_reader.graph_store
    emitter = WorkflowLifecycleEmitter(store)
    emitter.emit_on_enter("B313-eq-wall-thickness", context={})
    raw = emitter.to_dicts()
    parsed = parse_lifecycle_events(raw)
    assert len(parsed) == 1
    assert parsed[0].event == WorkflowLifecycleEventType.ON_ENTER
    assert parsed[0].node_id == "B313-eq-wall-thickness"
