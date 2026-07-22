"""Tests for MAWP workflow graph expansion."""

from __future__ import annotations

from pathlib import Path

from engine.graph.graph_engine import GraphEngine
from engine.graph.lazy_expander import expand_workflow
from engine.reference.standards_reader import StandardsReader
from tests.graph.conftest import MAWP_ROOT, mawp_gate_open_inputs


def _mawp_store(project_root: Path):
    reader = StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")
    engine = GraphEngine()
    micro = engine._micro_engine(reader)
    assert micro is not None
    resolved = engine._resolve_micro_root(MAWP_ROOT, reader)
    return micro.store, resolved


def test_mawp_expansion_includes_mawp_equation_chain(project_root: Path) -> None:
    store, root_id = _mawp_store(project_root)
    inputs = mawp_gate_open_inputs()
    expansion = expand_workflow(store, root_id, inputs, lazy=False)
    active = set(expansion.active_nodes)

    assert "asme-b313-pressure-design-thickness" in active
    assert "asme-b313-mawp-pressure" in active
    assert "PARAM-maximum-allowable-working-pressure" in active

    # Thickness design equations (eq 3a/3b) must not appear on MAWP path.
    assert "asme-b313-304-1-2-eq-3a" not in active
    assert "asme-b313-304-1-2-eq-3b" not in active


def test_mawp_expansion_includes_b3610_lookup_in_nps_mode(project_root: Path) -> None:
    store, root_id = _mawp_store(project_root)
    inputs = mawp_gate_open_inputs()
    expansion = expand_workflow(store, root_id, inputs, lazy=False)
    active = set(expansion.active_nodes)

    assert "asme-b3610-nps-outside-diameter-lookup" in active
    assert "PARAM-nominal-pipe-size" in active
    assert "asme-b313-table-A-3" in active


def test_mawp_expansion_includes_lookup_producers(project_root: Path) -> None:
    store, root_id = _mawp_store(project_root)
    inputs = mawp_gate_open_inputs()
    expansion = expand_workflow(store, root_id, inputs, lazy=False)
    active = set(expansion.active_nodes)

    assert "asme-b313-table-A-1" in active or "PARAM-allowable-stress" in active


def test_mawp_expansion_excludes_pipe_wall_workflow_node(project_root: Path) -> None:
    store, root_id = _mawp_store(project_root)
    inputs = mawp_gate_open_inputs()
    expansion = expand_workflow(store, root_id, inputs, lazy=False)

    assert "WF-PIPE-WALL-THICKNESS" not in expansion.active_nodes
