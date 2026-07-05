"""Tests for expansion gate fields sourced from workflow navigation metadata."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_engine import GraphEngine
from engine.graph.lazy_expander import _collect_expansion_assumptions, expansion_gate_ready
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from api.workflow_bootstrap import _apply_default_expansion_assumptions
from engine.state.task_facts import active_facts


def test_expansion_gate_requires_pressure_loading_on_fresh_task(project_root: Path) -> None:
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    assert micro is not None
    resolved = engine._resolve_micro_root("pipe_wall_thickness_design", reader)

    manager = TaskStateManager()
    task = manager.create_task("expansion-gate-test", status=TaskStatus.AWAITING_INPUT)
    _apply_default_expansion_assumptions(task)
    inputs = dict(active_facts(task))

    gate_fields = _collect_expansion_assumptions(micro.store, resolved)
    assert "pressure_loading" in gate_fields
    assert expansion_gate_ready(micro.store, resolved, inputs) is False
