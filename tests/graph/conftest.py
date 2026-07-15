"""Shared fixtures and helpers for Graph Engine tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.graph.graph_engine import GraphEngine
from engine.reference.standards_reader import StandardsReader
from models.execution import ExecutionPlan
from models.fact import Fact
from tests.acceptance.helpers import internal_pressure_assumption, straight_section_assumption
from tests.helpers.facts import facts_from_inputs

PIPE_WALL_ROOT = "pipe_wall_thickness_design"
MAWP_ROOT = "mawp_design"


@pytest.fixture
def b313_reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


@pytest.fixture
def graph_engine() -> GraphEngine:
    return GraphEngine()


def gate_open_inputs(*, task_id: str = "graph-test") -> dict[str, Fact]:
    """Facts that satisfy expansion gate for pipe wall thickness."""
    return facts_from_inputs(
        {
            "straight_pipe_section": straight_section_assumption(),
            "pressure_loading": internal_pressure_assumption(),
        },
        task_id=task_id,
    )


def mawp_gate_open_inputs(*, task_id: str = "mawp-graph-test") -> dict[str, Fact]:
    """Facts that satisfy expansion gate for MAWP workflow."""
    from models.input import InputSource, InputStatus
    from tests.helpers.facts import legacy_input

    return facts_from_inputs(
        {
            "straight_pipe_section": straight_section_assumption(),
            "pressure_loading": internal_pressure_assumption(),
            "outside_diameter__resolution_branch": legacy_input(
                "outside_diameter__resolution_branch",
                "nps_lookup",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
            "wall_thickness_basis": legacy_input(
                "wall_thickness_basis",
                "nominal_schedule",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        },
        task_id=task_id,
    )


def assert_dependency_order(plan: ExecutionPlan) -> None:
    """Every dependency edge source must appear before its target in execution_order."""
    index = {node_id: position for position, node_id in enumerate(plan.execution_order)}
    for edge in plan.dependencies:
        if edge.from_node not in index or edge.to_node not in index:
            continue
        assert index[edge.from_node] < index[edge.to_node], (
            f"{edge.from_node} must precede {edge.to_node} in execution order"
        )
