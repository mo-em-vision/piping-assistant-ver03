"""build_plan contract tests for GraphEngine."""

from __future__ import annotations

import pytest

from engine.graph.graph_engine import GraphEngine, GraphTraversalError, normalize_root_id
from models.execution import ExecutionPlan
from tests.acceptance.helpers import MATERIAL_STRESS_NODE, WALL_THICKNESS_NODE
from tests.graph.conftest import PIPE_WALL_ROOT, assert_dependency_order, gate_open_inputs


def test_build_plan_returns_execution_plan(b313_reader, graph_engine) -> None:
    plan = graph_engine.build_plan(
        task_id="execution-plan-type",
        root_id=PIPE_WALL_ROOT,
        inputs=gate_open_inputs(task_id="execution-plan-type"),
        reader=b313_reader,
    )
    assert isinstance(plan, ExecutionPlan)


def test_build_plan_includes_nodes_edges_order_version(b313_reader, graph_engine) -> None:
    plan = graph_engine.build_plan(
        task_id="plan-shape",
        root_id=PIPE_WALL_ROOT,
        inputs=gate_open_inputs(task_id="plan-shape"),
        reader=b313_reader,
    )
    assert plan.task_id == "plan-shape"
    assert plan.root
    assert plan.nodes
    assert plan.execution_order
    assert len(plan.execution_order) == len(set(plan.execution_order))
    assert plan.dependencies
    assert plan.graph_version is not None
    assert plan.graph_version.nodes


def test_build_plan_internal_pressure_contains_expected_nodes(b313_reader, graph_engine) -> None:
    plan = graph_engine.build_plan(
        task_id="internal-nodes",
        root_id=PIPE_WALL_ROOT,
        inputs=gate_open_inputs(task_id="internal-nodes"),
        reader=b313_reader,
    )
    assert WALL_THICKNESS_NODE in plan.nodes
    assert "304.1.3" not in plan.nodes
    assert MATERIAL_STRESS_NODE in plan.nodes or "asme-b313-table-A-1" in plan.nodes


def test_execution_order_dependencies_before_dependents(b313_reader, graph_engine) -> None:
    plan = graph_engine.build_plan(
        task_id="topo-order",
        root_id=PIPE_WALL_ROOT,
        inputs=gate_open_inputs(task_id="topo-order"),
        reader=b313_reader,
    )
    assert_dependency_order(plan)
    if MATERIAL_STRESS_NODE in plan.execution_order and WALL_THICKNESS_NODE in plan.execution_order:
        assert plan.execution_order.index(MATERIAL_STRESS_NODE) < plan.execution_order.index(
            WALL_THICKNESS_NODE
        )


def test_graph_version_contains_node_identity(b313_reader, graph_engine) -> None:
    plan = graph_engine.build_plan(
        task_id="graph-version",
        root_id=PIPE_WALL_ROOT,
        inputs=gate_open_inputs(task_id="graph-version"),
        reader=b313_reader,
    )
    assert plan.graph_version is not None
    version_nodes = set(plan.graph_version.nodes)
    assert version_nodes.issuperset(set(plan.nodes))


def test_build_plan_is_deterministic(b313_reader, graph_engine) -> None:
    kwargs = {
        "task_id": "deterministic-plan",
        "root_id": PIPE_WALL_ROOT,
        "inputs": gate_open_inputs(task_id="deterministic-plan"),
        "reader": b313_reader,
    }
    first = graph_engine.build_plan(**kwargs)
    second = graph_engine.build_plan(**kwargs)
    assert first.nodes == second.nodes
    assert first.execution_order == second.execution_order
    assert first.dependencies == second.dependencies
    assert first.graph_version.nodes == second.graph_version.nodes


def test_discover_roots_unknown_workflow_safe_result(b313_reader, graph_engine) -> None:
    candidates = graph_engine.discover_roots(
        b313_reader,
        workflow="totally_unknown_workflow_slug",
    )
    assert candidates == []


def test_build_plan_unknown_workflow_raises(b313_reader, monkeypatch) -> None:
    monkeypatch.setenv("VER03_LEGACY_GRAPH_TRAVERSAL", "0")
    engine = GraphEngine()
    with pytest.raises(GraphTraversalError):
        engine.build_plan(
            task_id="unknown",
            root_id="totally_unknown_workflow_slug",
            inputs={},
            reader=b313_reader,
        )


def test_normalize_root_id_accepts_roots_path() -> None:
    assert normalize_root_id("roots/pipe_wall_thickness_design/root.md") == "pipe_wall_thickness_design"
