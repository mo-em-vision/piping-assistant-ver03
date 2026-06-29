"""MVP strategy §7 — component testing strategy."""

from __future__ import annotations

import pytest

from engine.graph.graph_engine import GraphEngine
from engine.planner.planner import Planner
from engine.reports.formatters import render_markdown
from engine.validation.validation_engine import ValidationEngine
from models.execution import ExecutionStatus
from models.task import TaskStatus
from tests.acceptance.helpers import (
    MATERIAL_STRESS_NODE,
    PIPE_WALL_THICKNESS_ROOT,
    WALL_THICKNESS_NODE,
    pipe_thickness_intent,
    run_completed_workflow,
    sample_inputs,
)


class TestGraphEngineStrategy:
    """§7 Graph Engine — discovery, traversal, order, trace."""

    def test_node_discovery_and_execution_order(self, standards_reader) -> None:
        plan = GraphEngine().build_plan(
            task_id="mvp-component-graph",
            root_id=PIPE_WALL_THICKNESS_ROOT,
            inputs=sample_inputs(),
            reader=standards_reader,
        )
        assert WALL_THICKNESS_NODE in plan.execution_order
        assert "B313-param-P" in plan.execution_order
        assert "B313-param-S" in plan.execution_order


class TestValidationLayerStrategy:
    """§7 Validation Layer — input, unit, engineering limits, overrides."""

    def test_validation_blocks_invalid_pressure(self, standards_reader, state_manager) -> None:
        task_id = "mvp-component-validation"
        inputs = sample_inputs(pressure="abc")
        result = run_completed_workflow(state_manager, standards_reader, task_id, inputs=inputs)
        assert result.status != ExecutionStatus.COMPLETED


class TestExecutionLayerStrategy:
    """§7 Execution Layer — formulas, intermediates, deterministic results."""

    def test_execution_produces_required_thickness(self, standards_reader, state_manager) -> None:
        task_id = "pipe-wall-thickness-design-mvp-exec"
        result = run_completed_workflow(state_manager, standards_reader, task_id)
        assert result.status.value == "completed"
        assert state_manager.get_task(task_id).outputs.get("required_thickness") is not None


class TestPlannerStrategy:
    """§7 Planner — intent routing, planning, missing data."""

    def test_planner_identifies_missing_data(self, standards_reader, state_manager) -> None:
        task = state_manager.create_task("mvp-component-planner", status=TaskStatus.AWAITING_INPUT)
        plan = Planner(standards_reader, state=state_manager).plan(
            pipe_thickness_intent(),
            task,
            user_message="Calculate pipe thickness",
        )
        assert plan.missing_assumptions or plan.missing_inputs
        assert plan.selected_root == PIPE_WALL_THICKNESS_ROOT


class TestReportGeneratorStrategy:
    """§7 Report Generator — trace rendering and completeness."""

    def test_report_renders_trace_sections(self, standards_reader, state_manager) -> None:
        from tests.acceptance.helpers import rebuild_report_from_task

        task_id = "pipe-wall-thickness-design-mvp-report"
        run_completed_workflow(state_manager, standards_reader, task_id)
        report = rebuild_report_from_task(state_manager.get_task(task_id), standards_reader)
        markdown = render_markdown(report)

        assert report.traversal
        assert report.traceability
        assert "Workflow Traversal Record" in markdown


class TestAiInteractionStrategy:
    """§7 AI Interaction — questions without engineering decisions."""

    def test_input_agent_requests_without_calculating(self) -> None:
        from ai.agents.input_agent import InputAgent
        from models.task import Task

        agent = InputAgent(client=None)
        task = Task(task_id="mvp-ai", status=TaskStatus.AWAITING_INPUT)
        result = agent.analyze(task, workflow=PIPE_WALL_THICKNESS_ROOT)

        assert result.missing_inputs
        assert result.requests
        assert all(request.reason for request in result.requests)


COMPONENT_LAYERS = [
    "tests/graph",
    "tests/planner",
    "tests/validation",
    "tests/executor",
    "tests/calculation",
    "tests/reports",
    "tests/agents",
    "tests/e2e",
    "tests/acceptance",
    "tests/mvp",
]


@pytest.mark.parametrize("layer_path", COMPONENT_LAYERS)
def test_component_test_layers_exist(project_root, layer_path: str) -> None:
    """§3 Test distribution — integration/e2e, component, and unit layers are present."""
    assert (project_root / layer_path).is_dir(), f"Missing test layer: {layer_path}"
