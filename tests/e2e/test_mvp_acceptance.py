"""MVP acceptance criteria from docs/tests/2. acceptance_criteria.md."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.app import app
from cli.orchestrator import ChatOrchestrator
from engine.executor.executor import execute_workflow
from engine.graph.graph_engine import GraphEngine
from engine.planner.planner import Planner
from engine.reports.formatters import render_html, render_markdown
from engine.reports.report_data import build_report_from_task
from engine.reports.report_generator import ReportGenerator
from engine.state.state_manager import TaskStateManager
from models.agent import IntentResult
from models.execution import ExecutionStatus
from models.input import EngineeringInput, InputSource
from models.task import TaskStatus
from tests.agents.conftest import FakeLLMClient
from tests.e2e.scenario_loader import load_scenario
from tests.e2e.scenario_runner import ScenarioRunner


def _sample_inputs() -> dict[str, EngineeringInput]:
    return {
        "design_pressure": EngineeringInput(
            input_id="design_pressure",
            value=500,
            unit="psi",
            source=InputSource.USER,
        ),
        "outside_diameter": EngineeringInput(
            input_id="outside_diameter",
            value=10,
            unit="in",
            source=InputSource.USER,
        ),
        "material": EngineeringInput(
            input_id="material",
            value="SA-106B",
            unit="dimensionless",
            source=InputSource.USER,
        ),
        "design_temperature": EngineeringInput(
            input_id="design_temperature",
            value=200,
            unit="F",
            source=InputSource.USER,
        ),
    }


def test_user_request_reaches_planner(standards_reader, state_manager) -> None:
    task = state_manager.create_task("mvp-planner", status=TaskStatus.AWAITING_INPUT)
    planner = Planner(standards_reader, state=state_manager)
    intent = IntentResult(
        intent="pipe_wall_thickness_design",
        domain="piping",
        workflow="pipe_wall_thickness_design",
        confidence=0.95,
    )

    plan = planner.plan(intent, task, user_message="Calculate pipe thickness")

    assert plan.selected_root == "pipe_wall_thickness_design"
    assert plan.selected_nodes


def test_graph_finds_required_nodes(standards_reader) -> None:
    plan = GraphEngine().build_plan(
        task_id="mvp-graph",
        root_id="pipe_wall_thickness_design",
        inputs={},
        reader=standards_reader,
    )

    assert "B313-material-stress" in plan.nodes
    assert "B313-304.1.1" in plan.nodes
    assert plan.execution_order.index("B313-material-stress") < plan.execution_order.index(
        "B313-304.1.1"
    )


def test_execution_produces_deterministic_results(standards_reader, state_manager) -> None:
    task_id = "mvp-exec"
    state_manager.create_task(task_id)
    for engineering_input in _sample_inputs().values():
        state_manager.store_input(task_id, engineering_input)

    first = execute_workflow(task_id, "pipe_wall_thickness_design", state=state_manager, reader=standards_reader)
    outputs_first = dict(state_manager.get_task(task_id).outputs)

    state_manager.create_task("mvp-exec-2")
    for engineering_input in _sample_inputs().values():
        state_manager.store_input("mvp-exec-2", engineering_input)
    second = execute_workflow(
        "mvp-exec-2",
        "pipe_wall_thickness_design",
        state=state_manager,
        reader=standards_reader,
    )
    outputs_second = dict(state_manager.get_task("mvp-exec-2").outputs)

    assert first.status == ExecutionStatus.COMPLETED
    assert second.status == ExecutionStatus.COMPLETED
    assert outputs_first["required_thickness"] == outputs_second["required_thickness"]
    assert outputs_first["allowable_stress"] == outputs_second["allowable_stress"]


def test_trace_is_stored(standards_reader, state_manager) -> None:
    task_id = "mvp-trace"
    state_manager.create_task(task_id)
    for engineering_input in _sample_inputs().values():
        state_manager.store_input(task_id, engineering_input)

    execute_workflow(task_id, "pipe_wall_thickness_design", state=state_manager, reader=standards_reader)
    task = state_manager.get_task(task_id)

    assert isinstance(task.outputs.get("_execution_trace"), list)
    assert isinstance(task.outputs.get("_validation_trace"), list)
    assert len(task.outputs["_execution_trace"]) >= 1


def test_report_is_generated(standards_reader, state_manager, tmp_path) -> None:
    task_id = "pipe-wall-thickness-design-mvp-report"
    state_manager.create_task(task_id)
    for engineering_input in _sample_inputs().values():
        state_manager.store_input(task_id, engineering_input)

    execute_workflow(task_id, "pipe_wall_thickness_design", state=state_manager, reader=standards_reader)
    task = state_manager.get_task(task_id)
    report = build_report_from_task(task, standards_reader)

    generator = ReportGenerator(standards_reader.standards_root)
    storage = generator.generate(report, tmp_path, formats=("markdown", "html", "json", "pdf"))

    assert Path(storage.markdown_path).exists()
    assert Path(storage.html_path).exists()
    assert Path(storage.json_path).exists()
    md = Path(storage.markdown_path).read_text(encoding="utf-8")
    html = Path(storage.html_path).read_text(encoding="utf-8")
    assert "Executive Summary" in md
    assert "Pipe Wall Thickness" in html


def test_state_can_resume_tasks(standards_reader, state_manager) -> None:
    task_id = "mvp-resume"
    state_manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
    state_manager.store_input(
        task_id,
        EngineeringInput(
            input_id="design_pressure",
            value=500,
            unit="psi",
            source=InputSource.USER,
        ),
    )

    paused = execute_workflow(task_id, "pipe_wall_thickness_design", state=state_manager, reader=standards_reader)
    assert paused.status == ExecutionStatus.AWAITING_INPUT

    for key, engineering_input in _sample_inputs().items():
        state_manager.store_input(task_id, engineering_input)

    resumed = execute_workflow(task_id, "pipe_wall_thickness_design", state=state_manager, reader=standards_reader)
    assert resumed.status == ExecutionStatus.COMPLETED
    assert state_manager.get_task(task_id).status == TaskStatus.COMPLETED


def test_changed_inputs_create_conflicts(standards_reader, state_manager) -> None:
    task_id = "mvp-branch"
    state_manager.create_task(task_id)
    for engineering_input in _sample_inputs().values():
        state_manager.store_input(task_id, engineering_input)

    execute_workflow(task_id, "pipe_wall_thickness_design", state=state_manager, reader=standards_reader)

    state_manager.store_input(
        task_id,
        EngineeringInput(
            input_id="design_temperature",
            value=400,
            unit="F",
            source=InputSource.USER,
        ),
    )
    task = state_manager.get_task(task_id)
    assert any(conflict.input_id == "design_temperature" for conflict in task.conflicts)

    rerun = execute_workflow(task_id, "pipe_wall_thickness_design", state=state_manager, reader=standards_reader)
    assert rerun.status == ExecutionStatus.COMPLETED
    assert state_manager.get_task(task_id).outputs["allowable_stress"] == 179_000_000.0


def test_orchestrator_waiting_input_for_pipe_thickness() -> None:
    manager = TaskStateManager()
    orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))
    response, _ = orchestrator.handle_message("Calculate minimum wall thickness for refinery pipe")

    assert response.status == "waiting_input"
    assert response.task_id is not None


def test_cli_graph_and_report_commands() -> None:
    runner = CliRunner()
    graph = runner.invoke(app, ["graph", "show", "pipe_wall_thickness_design"])
    validate = runner.invoke(app, ["node", "validate", "B313-304.1.1"])

    assert graph.exit_code == 0
    assert "B313-304.1.1" in graph.stdout
    assert validate.exit_code == 0
    assert "PASS" in validate.stdout


def test_golden_report_structure(
    standards_reader,
    expected_dir: Path,
    scenario_runner: ScenarioRunner,
    tmp_path,
) -> None:
    scenario = load_scenario(
        Path(__file__).resolve().parents[1] / "data" / "scenarios" / "pipe_wall_thickness_basic.yaml"
    )
    result = scenario_runner.run(scenario)
    report = result.final.report_data
    assert report is not None

    md = render_markdown(report)
    html = render_html(report)
    golden = (expected_dir / "pipe_wall_thickness_report_structure.json").read_text(encoding="utf-8")
    import json

    structure = json.loads(golden)
    for section in structure["required_sections"]:
        assert section in md, f"Missing report section: {section}"
    for node in structure["required_nodes"]:
        assert node in md or node.replace("B313-", "") in md
    for field in structure["required_report_fields"]:
        assert getattr(report, field, None) is not None

    generator = ReportGenerator(standards_reader.standards_root)
    storage = generator.generate(report, tmp_path, formats=("markdown", "html"))
    assert Path(storage.markdown_path).exists()
    assert Path(storage.html_path).exists()
