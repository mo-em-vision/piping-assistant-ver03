"""Tests for graph-derived workflow path decisions."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_engine import GraphEngine
from engine.graph.path_decision import resolve_path_decision
from engine.reference.standards_reader import StandardsReader
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.helpers.facts import facts_from_inputs, legacy_input
from models.input import InputSource, InputStatus


def _store(project_root: Path):
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    assert micro is not None
    resolved = engine._resolve_micro_root("pipe_wall_thickness_design", reader)
    return micro.store, reader, resolved


def test_resolve_path_decision_internal_pressure(project_root: Path) -> None:
    store, reader, root = _store(project_root)
    inputs = facts_from_inputs(
        {
            "straight_pipe_section": straight_section_assumption(),
            "pressure_loading": internal_pressure_assumption(),
        },
        task_id="path-test",
    )
    plan = GraphEngine().build_plan(
        task_id="path-test",
        root_id="pipe_wall_thickness_design",
        inputs=inputs,
        reader=reader,
    )
    decision = resolve_path_decision(store, list(plan.execution_order), inputs)
    assert decision is not None
    assert decision["field"] == "pressure_loading"
    assert decision["value"] == "internal_pressure"
    assert decision["selected_node"] == "304.1.2-a"


def test_resolve_path_decision_external_pressure(project_root: Path) -> None:
    store, reader, root = _store(project_root)
    inputs = facts_from_inputs(
        {
            "straight_pipe_section": straight_section_assumption(),
            "pressure_loading": legacy_input(
                "pressure_loading",
                "external_pressure",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
        task_id="path-test",
    )
    plan = GraphEngine().build_plan(
        task_id="path-test",
        root_id="pipe_wall_thickness_design",
        inputs=inputs,
        reader=reader,
    )
    decision = resolve_path_decision(store, list(plan.execution_order), inputs)
    assert decision is not None
    assert decision["selected_node"] == "304.1.3"
