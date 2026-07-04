"""Graph Engine tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.graph.graph_engine import GraphCycleError, GraphEngine, normalize_root_id
from engine.reference.standards_reader import StandardsReader
from models.fact import fact_scalar_value
from models.graph import EdgeType, GraphEdge
from models.input import InputSource, InputStatus
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.helpers.facts import facts_from_inputs, legacy_input


def _reader() -> StandardsReader:
    root = Path(__file__).resolve().parents[2]
    return StandardsReader(root / "knowledge" / "standards", standard="asme_b31.3")


def test_build_plan_execution_order_without_pressure_loading() -> None:
    reader = _reader()
    plan = GraphEngine().build_plan(
        task_id="pipe-wall-thickness-design-test",
        root_id="pipe_wall_thickness_design",
        inputs={},
        reader=reader,
    )

    assert "304.1.1-a" in plan.nodes
    assert "304.1.1-b" in plan.nodes
    assert "304.1.2-a" not in plan.nodes


def test_build_plan_internal_pressure_path() -> None:
    reader = _reader()
    plan = GraphEngine().build_plan(
        task_id="pipe-wall-thickness-design-test",
        root_id="pipe_wall_thickness_design",
        inputs=facts_from_inputs(
            {
                "straight_pipe_section": straight_section_assumption(),
                "pressure_loading": internal_pressure_assumption(),
            },
            task_id="pipe-wall-thickness-design-test",
        ),
        reader=reader,
    )

    assert "304.1.1-a" in plan.nodes
    assert "304.1.1-b" in plan.nodes
    assert "304.1.2-a" in plan.nodes
    assert "B313-304.1.3" not in plan.nodes


def test_build_plan_external_pressure_path() -> None:
    reader = _reader()
    plan = GraphEngine().build_plan(
        task_id="pipe-wall-thickness-design-test",
        root_id="pipe_wall_thickness_design",
        inputs=facts_from_inputs(
            {
                "straight_pipe_section": straight_section_assumption(),
                "pressure_loading": legacy_input(
                    "pressure_loading",
                    "external_pressure",
                    source=InputSource.USER,
                    status=InputStatus.CONFIRMED,
                ),
            },
            task_id="pipe-wall-thickness-design-test",
        ),
        reader=reader,
    )

    assert "304.1.3" in plan.nodes
    assert "304.1.1-a" in plan.nodes
    assert "304.1.1-b" in plan.nodes
    assert "304.1.2-a" not in plan.nodes


def test_build_plan_includes_dependencies() -> None:
    reader = _reader()
    plan = GraphEngine().build_plan(
        task_id="task-deps",
        root_id="pipe_wall_thickness_design",
        inputs=facts_from_inputs(
            {
                "straight_pipe_section": straight_section_assumption(),
                "pressure_loading": internal_pressure_assumption(),
                "design_pressure": legacy_input("design_pressure", 500, "psi"),
            },
            task_id="task-deps",
        ),
        reader=reader,
    )

    assert plan.task_id == "task-deps"
    assert fact_scalar_value(plan.inputs["design_pressure"]) == 500
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
    assert normalize_root_id("tasks/pipe_wall_thickness_design/root.md") == "pipe_wall_thickness_design"
    assert normalize_root_id("tasks/asme_b31.3/pipe_wall_thickness_design/root.md") == "pipe_wall_thickness_design"
    assert normalize_root_id("pipe_wall_thickness_design") == "pipe_wall_thickness_design"
    assert normalize_root_id("B313-WF-PIPE-WALL-THICKNESS") == "B313-WF-PIPE-WALL-THICKNESS"


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
    required = GraphEngine().required_user_inputs(
        "pipe_wall_thickness_design",
        reader,
        task_inputs=facts_from_inputs(
            {
                "straight_pipe_section": straight_section_assumption(),
                "pressure_loading": internal_pressure_assumption(),
            },
            task_id="required-inputs-test",
        ),
    )

    assert "design_pressure" in required
    assert "material" in required
    assert "design_temperature" in required


def test_lazy_resolve_next_step_fast() -> None:
    import time

    reader = _reader()
    engine = GraphEngine()
    start = time.perf_counter()
    for _ in range(20):
        step = engine.resolve_next_step(
            "pipe_wall_thickness_design",
            reader,
            {},
        )
        assert step is not None
    elapsed = time.perf_counter() - start
    assert elapsed < 4.0, f"20 lazy resolve_next_step calls took {elapsed:.3f}s"
