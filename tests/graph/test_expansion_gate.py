"""Tests for expansion gate fields sourced from workflow navigation metadata."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_engine import GraphEngine
from engine.graph.lazy_expander import _collect_expansion_assumptions, expansion_gate_ready
from engine.reference.standards_reader import StandardsReader
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from engine.state.task_facts import active_facts, store_proposed_default


def test_expansion_gate_requires_pressure_loading_on_fresh_task(project_root: Path) -> None:
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    assert micro is not None
    resolved = engine._resolve_micro_root("pipe_wall_thickness_design", reader)

    manager = TaskStateManager()
    task = manager.create_task("expansion-gate-test", status=TaskStatus.AWAITING_INPUT)
    store_proposed_default(task, "straight_pipe_section", True, unit="dimensionless")
    inputs = dict(active_facts(task))

    gate_fields = _collect_expansion_assumptions(micro.store, resolved)
    assert "straight_pipe_section" in gate_fields
    assert "pressure_loading" in gate_fields
    assert expansion_gate_ready(micro.store, resolved, inputs) is False


def test_expansion_gate_requires_straight_pipe_before_anchor_expands(project_root: Path) -> None:
    from engine.graph.lazy_expander import expand_workflow

    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    assert micro is not None
    resolved = engine._resolve_micro_root("pipe_wall_thickness_design", reader)

    lazy_state = expand_workflow(micro.store, resolved, {}, lazy=True)
    assert "304.1.1-a" in lazy_state.active_nodes
    assert "304.1.2-a" not in lazy_state.active_nodes
    assert "straight_pipe_section" in lazy_state.pending_fields

    from tests.acceptance.helpers import straight_section_assumption
    from engine.state.fact_migration import fact_from_engineering_input

    inputs = {
        "straight_pipe_section": fact_from_engineering_input(
            straight_section_assumption(),
            task_id="expansion-gate-test",
            workflow_id="pipe_wall_thickness_design",
        )
    }
    lazy_with_straight = expand_workflow(micro.store, resolved, inputs, lazy=True)
    assert "304.1.1-a" in lazy_with_straight.active_nodes
    assert "straight_pipe_section" not in lazy_with_straight.pending_fields
    assert "pressure_loading" in lazy_with_straight.pending_fields
