"""Tests for pipe wall thickness workflow expansion projection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from config.loader import CLIConfig
from dev.graph_explorer.adapter import GraphExplorerAdapter
from dev.graph_explorer.server import create_app
from dev.graph_explorer.workflow_expansion import build_workflow_expansion_view
from engine.planner.planner import Planner
from engine.reference.standards_reader import StandardsReader
from engine.state.fact_migration import fact_from_engineering_input
from engine.state.state_manager import TaskStateManager
from engine.state.task_facts import store_user_fact
from models.agent import IntentResult
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import Task, TaskStatus, new_task
from tests.acceptance.helpers import (
    internal_pressure_assumption,
    straight_section_assumption,
)
from tests.helpers.facts import legacy_input


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def config(project_root: Path) -> CLIConfig:
    return CLIConfig.load(project_root=project_root)


@pytest.fixture
def adapter(config: CLIConfig) -> GraphExplorerAdapter:
    return GraphExplorerAdapter(config, session_id="default")


def _reader(project_root: Path) -> StandardsReader:
    return StandardsReader(project_root / "knowledge" / "standards", standard="asme_b31.3")


def _store_input(state: TaskStateManager, task_id: str, inp: EngineeringInput) -> None:
    state.store_fact(
        task_id,
        fact_from_engineering_input(inp, task_id=task_id, workflow_id="pipe_wall_thickness_design"),
    )


def _build_task(
    task_id: str,
    *,
    outputs: dict[str, Any] | None = None,
    facts: list[EngineeringInput] | None = None,
    plan: bool = False,
    project_root: Path | None = None,
) -> Task:
    state = TaskStateManager()
    task = state.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    task.outputs["selected_root"] = "pipe_wall_thickness_design"
    if outputs:
        task.outputs.update(outputs)
    for fact in facts or []:
        _store_input(state, task_id, fact)
    task = state.get_task(task_id)
    if plan and project_root is not None:
        planner = Planner(_reader(project_root), state=state)
        intent = IntentResult(
            intent="pipe_wall_thickness_design",
            domain="piping",
            workflow="pipe_wall_thickness_design",
            confidence=0.95,
        )
        planner.plan(intent, task)
        task = state.get_task(task_id)
    return task


def _node(view: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for node in view.get("nodes") or []:
        if node.get("id") == node_id:
            return node
    return None


def _visible_ids(view: dict[str, Any]) -> set[str]:
    return {node["id"] for node in view.get("nodes") or [] if node.get("visible")}


def test_initial_task_expansion_assumptions(config: CLIConfig, adapter: GraphExplorerAdapter) -> None:
    task = _build_task("pw-exp-initial")
    view = build_workflow_expansion_view(task.task_id, "default", adapter)
    # Build directly from task object for session-less tests
    from dev.graph_explorer.projectors.pipe_wall_thickness import PipeWallThicknessExpansionProjector

    view = PipeWallThicknessExpansionProjector(adapter).project(task)

    assert view["current_phase"] == "expansion_assumptions"
    definition = _node(view, "304.1.1-a")
    assert definition is not None
    assert definition["visible"] is True
    assert definition["status"] == "awaiting_expansion_assumption"
    assert not any(
        node.get("status") == "awaiting_input" and node.get("type") == "parameter"
        for node in view["nodes"]
    )


def test_path_decisions_missing_pressure(config: CLIConfig, adapter: GraphExplorerAdapter) -> None:
    task = _build_task(
        "pw-exp-path",
        facts=[straight_section_assumption()],
    )
    from dev.graph_explorer.projectors.pipe_wall_thickness import PipeWallThicknessExpansionProjector

    view = PipeWallThicknessExpansionProjector(adapter).project(task)

    assert view["current_phase"] == "path_decisions"
    timeline = view["timeline"]
    path_phase = next(item for item in timeline if item["phase"] == "path_decisions")
    pressure_item = next(item for item in path_phase["items"] if item["id"] == "pressure_loading")
    assert pressure_item["status"] in {"missing", "current"}
    calc = _node(view, "304.1.2-a")
    if calc is not None:
        assert calc["status"] in {"pending_condition", "preview", "skipped"}


def test_internal_pressure_branch(config: CLIConfig, adapter: GraphExplorerAdapter) -> None:
    task = _build_task(
        "pw-exp-internal",
        facts=[straight_section_assumption(), internal_pressure_assumption()],
        plan=True,
        project_root=Path(__file__).resolve().parents[2],
    )
    from dev.graph_explorer.projectors.pipe_wall_thickness import PipeWallThicknessExpansionProjector

    view = PipeWallThicknessExpansionProjector(adapter).project(task)

    internal = _node(view, "304.1.2-a")
    external = _node(view, "304.1.3")
    assert internal is not None
    assert internal["visible"] is True
    assert internal["status"] in {"active", "awaiting_input", "ready", "expanded"}
    assert external is not None
    assert external["status"] == "skipped"

    edges = view.get("edges") or []
    to_external = [edge for edge in edges if edge.get("target") == "304.1.3"]
    if to_external:
        assert any(edge.get("skipped") or edge.get("type") == "skipped" for edge in to_external)


def test_external_pressure_branch(config: CLIConfig, adapter: GraphExplorerAdapter) -> None:
    task = _build_task(
        "pw-exp-external",
        facts=[
            straight_section_assumption(),
            legacy_input(
                "pressure_loading",
                "external_pressure",
                "dimensionless",
                source=InputSource.USER,
                status=InputStatus.CONFIRMED,
            ),
        ],
        plan=True,
        project_root=Path(__file__).resolve().parents[2],
    )
    from dev.graph_explorer.projectors.pipe_wall_thickness import PipeWallThicknessExpansionProjector

    view = PipeWallThicknessExpansionProjector(adapter).project(task)

    internal = _node(view, "304.1.2-a")
    external = _node(view, "304.1.3")
    assert external is not None
    assert external["status"] in {"active", "awaiting_input", "ready"}
    if internal is not None:
        assert internal["status"] == "skipped"


def test_parameter_gathering_blockers_only_current_phase(
    config: CLIConfig,
    adapter: GraphExplorerAdapter,
    project_root: Path,
) -> None:
    task = _build_task(
        "pw-exp-params",
        facts=[straight_section_assumption(), internal_pressure_assumption()],
        plan=True,
        project_root=project_root,
    )
    from dev.graph_explorer.projectors.pipe_wall_thickness import PipeWallThicknessExpansionProjector

    view = PipeWallThicknessExpansionProjector(adapter).project(task)

    assert view["current_phase"] in {"parameter_gathering", "path_decisions", "coefficient_resolution"}
    timeline = view["timeline"]
    coeff_phase = next(item for item in timeline if item["phase"] == "coefficient_resolution")
    for item in coeff_phase["items"]:
        if view["current_phase"] == "parameter_gathering":
            assert item["status"] in {"not_reached", "missing"}


def test_execution_trace_marks_executed(config: CLIConfig, adapter: GraphExplorerAdapter) -> None:
    task = _build_task(
        "pw-exp-trace",
        outputs={
            "_execution_trace": [
                {
                    "node_id": "304.1.2-a",
                    "status": "completed",
                    "inputs": {"design_pressure": 100},
                    "outputs": {"required_thickness": 0.1},
                    "warnings": [],
                    "errors": [],
                }
            ]
        },
        facts=[straight_section_assumption(), internal_pressure_assumption()],
    )
    from dev.graph_explorer.projectors.pipe_wall_thickness import PipeWallThicknessExpansionProjector

    view = PipeWallThicknessExpansionProjector(adapter).project(task)

    calc = _node(view, "304.1.2-a")
    assert calc is not None
    assert calc["status"] == "executed"
    assert calc["details"].get("execution", {}).get("outputs") == {"required_thickness": 0.1}


def test_missing_compiled_graph_returns_warning(config: CLIConfig) -> None:
    adapter = GraphExplorerAdapter(config, session_id="default")
    adapter._stores.clear()  # noqa: SLF001
    adapter._node_pack.clear()  # noqa: SLF001
    task = new_task("pw-exp-no-graph", status=TaskStatus.AWAITING_INPUT)
    task.outputs["workflow"] = "pipe_wall_thickness_design"
    view = build_workflow_expansion_view(task.task_id, "default", adapter)
    from dev.graph_explorer.projectors.pipe_wall_thickness import PipeWallThicknessExpansionProjector

    view = PipeWallThicknessExpansionProjector(adapter).project(task)
    assert view["warnings"]
    assert view["debug"]["has_compiled_graph"] is False


def test_workflow_expansion_route(project_root: Path) -> None:
    app = create_app(project_root)
    client = TestClient(app)
    response = client.get("/api/workflow-expansion", params={"task": "missing-task"})
    assert response.status_code == 200
    payload = response.json()
    assert "warnings" in payload
    assert payload["debug"]["has_task"] is False
