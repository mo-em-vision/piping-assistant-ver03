"""Acceptance criteria §3 and §21 — CLI interface and user visibility."""

from __future__ import annotations

from cli.app import app
from cli.orchestrator import ChatOrchestrator
from cli.session_store import SessionStore
from engine.state.state_manager import TaskStateManager
from models.task import TaskStatus
from tests.acceptance.helpers import PIPE_WALL_THICKNESS_ROOT, plan_pipe_thickness, sample_inputs
from tests.agents.conftest import FakeLLMClient
from typer.testing import CliRunner


class TestSupportedInterface:
    """§3 Supported Interface — CLI + chat interaction."""

    def test_cli_task_list_command(self) -> None:
        result = CliRunner().invoke(app, ["task", "list"])
        assert result.exit_code == 0

    def test_cli_graph_show_displays_execution_path(self) -> None:
        result = CliRunner().invoke(app, ["graph", "show", PIPE_WALL_THICKNESS_ROOT])
        assert result.exit_code == 0
        assert "B313-304.1.1" in result.stdout
        assert "B313-304.1.2" in result.stdout
        assert "B313-table-A-1" in result.stdout

    def test_cli_node_validate_command(self) -> None:
        result = CliRunner().invoke(app, ["node", "validate", "B313-304.1.1"])
        assert result.exit_code == 0
        assert "PASS" in result.stdout

    def test_chat_starts_task_and_requests_inputs(self) -> None:
        manager = TaskStateManager()
        orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))
        response, _ = orchestrator.handle_message("Calculate minimum wall thickness for refinery pipe")

        assert response.status == "waiting_input"
        assert response.task_id is not None
        assert response.question

    def test_cli_task_resume_restores_session_task(self, tmp_path, monkeypatch) -> None:
        sessions_dir = tmp_path / "sessions"
        store = SessionStore(sessions_dir, session_id="default")
        manager = TaskStateManager()
        task_id = "pipe-wall-thickness-design-resume-cli"
        manager.create_task(task_id, status=TaskStatus.AWAITING_INPUT)
        manager.store_input(task_id, sample_inputs()["design_pressure"])
        store.save_state_manager(manager)

        class _SessionStore(SessionStore):
            def __init__(self, _sessions_dir: Path, session_id: str | None = None) -> None:
                super().__init__(sessions_dir, session_id=session_id or "default")

        monkeypatch.setattr("cli.commands.tasks.SessionStore", _SessionStore)
        result = CliRunner().invoke(app, ["task", "resume", task_id])
        assert result.exit_code == 0
        assert task_id in result.stdout

    def test_cli_report_generate_command(self, tmp_path, monkeypatch) -> None:
        sessions_dir = tmp_path / "sessions"
        store = SessionStore(sessions_dir, session_id="default")
        manager = TaskStateManager()
        task_id = "pipe-wall-thickness-design-report-cli"
        manager.create_task(task_id, status=TaskStatus.COMPLETED)
        for engineering_input in sample_inputs().values():
            manager.store_input(task_id, engineering_input)
        manager.store_output(task_id, "required_thickness", 12.5)
        store.save_state_manager(manager)

        class _SessionStore(SessionStore):
            def __init__(self, _sessions_dir: Path, session_id: str | None = None) -> None:
                super().__init__(sessions_dir, session_id=session_id or "default")

        monkeypatch.setattr("cli.commands.reports.SessionStore", _SessionStore)
        result = CliRunner().invoke(app, ["report", "generate", task_id, "--format", "html"])
        assert result.exit_code == 0
        assert "Report generated" in result.stdout


class TestUserVisibility:
    """§21 User Visibility — selected nodes, dependencies, and execution path."""

    def test_graph_command_shows_dependencies_before_execution(self) -> None:
        result = CliRunner().invoke(app, ["graph", "show", "B313-304.1.2"])
        assert result.exit_code == 0
        assert "B313-table-A-1" in result.stdout
        assert "B313-304.1.1" in result.stdout

    def test_planner_exposes_selected_nodes_and_missing_inputs(
        self,
        standards_reader,
        state_manager,
    ) -> None:
        task = state_manager.create_task("acceptance-visibility", status=TaskStatus.AWAITING_INPUT)
        plan = plan_pipe_thickness(standards_reader, state_manager, task)

        assert plan.selected_nodes
        assert plan.missing_assumptions or plan.phase_missing.get("expansion_assumptions")
        assert plan.questions
        assert any(
            "straight" in question.lower()
            or "pressure" in question.lower()
            or "304.1.1" in question
            for question in plan.questions
        )
