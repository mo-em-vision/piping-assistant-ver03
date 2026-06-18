"""Graph Engine tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.graph.graph_engine import GraphCycleError, GraphEngine, normalize_root_id
from engine.reference.standards_reader import StandardsReader
from models.graph import EdgeType, GraphEdge
from models.input import EngineeringInput, InputSource


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "standards", standard="asme_b31.3")


def test_build_plan_execution_order() -> None:
    reader = _reader()
    plan = GraphEngine().build_plan(
        task_id="pipe-wall-thickness-design-test",
        root_id="pipe_wall_thickness_design",
        inputs={},
        reader=reader,
    )

    assert "B313-material-stress" in plan.nodes
    assert "B313-304.1.1" in plan.nodes
    assert plan.execution_order.index("B313-material-stress") < plan.execution_order.index(
        "B313-304.1.1"
    )


def test_build_plan_includes_dependencies() -> None:
    reader = _reader()
    plan = GraphEngine().build_plan(
        task_id="task-deps",
        root_id="pipe_wall_thickness_design",
        inputs={
            "design_pressure": EngineeringInput(
                input_id="design_pressure",
                value=500,
                unit="psi",
                source=InputSource.USER,
            )
        },
        reader=reader,
    )

    assert plan.task_id == "task-deps"
    assert plan.inputs["design_pressure"].value == 500
    assert len(plan.dependencies) >= 2
    assert plan.graph_version is not None


def test_topological_sort_cycle_raises() -> None:
    with pytest.raises(GraphCycleError):
        GraphEngine._topological_sort(
            {"A", "B"},
            [
                GraphEdge(from_node="A", to_node="B", type=EdgeType.DEPENDENCY),
                GraphEdge(from_node="B", to_node="A", type=EdgeType.DEPENDENCY),
            ],
        )


def test_normalize_root_id() -> None:
    assert normalize_root_id("roots/pipe_wall_thickness_design/root.md") == "pipe_wall_thickness_design"
    assert normalize_root_id("pipe_wall_thickness_design") == "pipe_wall_thickness_design"


def test_discover_roots_wall_thickness() -> None:
    reader = _reader()
    candidates = GraphEngine().discover_roots(
        reader,
        workflow="pipe_wall_thickness_design",
    )

    assert candidates
    assert candidates[0].root_id == "pipe_wall_thickness_design"
    assert candidates[0].confidence >= 0.85


def test_required_user_inputs() -> None:
    reader = _reader()
    required = GraphEngine().required_user_inputs("pipe_wall_thickness_design", reader)

    assert "design_pressure" in required
    assert "outside_diameter" in required
    assert "material" in required
    assert "design_temperature" in required
    assert "allowable_stress" not in required
