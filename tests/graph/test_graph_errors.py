"""Graph Engine resilience tests (cycles, missing dependencies)."""

from __future__ import annotations

import pytest

from engine.graph.conditions import GraphCycleError
from engine.graph.graph_engine import GraphEngine
from engine.graph.lazy_expander import expand_workflow
from engine.graph.micro_graph_engine import MicroGraphEngine
from engine.graph.traversal import dfs_collect
from tests.graph.helpers import build_cycle_pack, build_missing_dependency_pack


def test_cycle_detection_raises_graph_cycle_error(tmp_path) -> None:
    store = build_cycle_pack(tmp_path)
    with pytest.raises(GraphCycleError):
        dfs_collect(store, "node-a", inputs={})


def test_build_plan_cycle_raises_graph_cycle_error(tmp_path) -> None:
    store = build_cycle_pack(tmp_path)
    engine = MicroGraphEngine(store)
    with pytest.raises(GraphCycleError):
        engine.build_plan(task_id="cycle", root_id="node-a", inputs={})


def test_missing_dependency_does_not_crash_expansion(tmp_path) -> None:
    store = build_missing_dependency_pack(tmp_path)
    expansion = expand_workflow(store, "node-root", {}, lazy=False)
    assert "node-root" in expansion.active_nodes
    assert store.get_node("node-missing") is None
    if "node-missing" in expansion.active_nodes:
        assert store.get_node("node-missing") is None
