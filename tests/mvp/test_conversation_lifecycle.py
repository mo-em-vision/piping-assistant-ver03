"""MVP strategy §16 — conversation lifecycle testing."""

from __future__ import annotations

from cli.orchestrator import ChatOrchestrator
from engine.reports.report_data import build_report_from_task
from engine.reports.report_generator import ReportGenerator
from engine.state.state_manager import TaskStateManager
from tests.acceptance.helpers import run_completed_workflow, sample_inputs
from tests.agents.conftest import FakeLLMClient


class TestConversationLifecycle:
    """§16 Conversation Testing — request → question → answer → calculation → report."""

    def test_chat_request_then_follow_up_preserves_task_context(self) -> None:
        manager = TaskStateManager()
        orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))

        first, _ = orchestrator.handle_message("Calculate pipe wall thickness for refinery piping")
        assert first.status == "waiting_input"
        assert first.task_id is not None
        task_id = first.task_id

        for engineering_input in sample_inputs().values():
            manager.store_input(task_id, engineering_input)

        second, _ = orchestrator.handle_message(
            "Calculate pipe wall thickness with the provided design conditions",
        )
        assert second.task_id == task_id
        assert second.status == "ready"
        assert manager.get_active_task() is not None

    def test_full_lifecycle_through_execution_and_report(
        self,
        standards_reader,
        tmp_path,
    ) -> None:
        manager = TaskStateManager()
        orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))

        response, _ = orchestrator.handle_message("Verify minimum wall thickness for process pipe")
        task_id = response.task_id
        assert task_id is not None

        for engineering_input in sample_inputs().values():
            manager.store_input(task_id, engineering_input)

        follow_up, _ = orchestrator.handle_message("Calculate pipe wall thickness with all inputs ready")
        assert follow_up.status == "ready"

        run_completed_workflow(manager, standards_reader, task_id)
        report = build_report_from_task(manager.get_task(task_id), standards_reader)
        storage = ReportGenerator(standards_reader.standards_root).generate(
            report,
            tmp_path,
            formats=("markdown", "html"),
        )

        assert report.status in {"PASS", "COMPLETED"}
        assert storage.markdown_path
        assert manager.get_task(task_id).outputs.get("required_thickness") is not None

    def test_follow_up_still_identifies_missing_inputs_when_partial(self) -> None:
        manager = TaskStateManager()
        orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))

        first, _ = orchestrator.handle_message("Calculate pipe wall thickness")
        task_id = first.task_id
        manager.store_input(task_id, sample_inputs()["design_pressure"])

        second, _ = orchestrator.handle_message(
            "Calculate pipe wall thickness — design pressure is 500 psi",
        )
        assert second.status == "waiting_input"
        assert second.task_id == task_id
        assert "pressure_loading" in (second.data.get("missing_inputs") or [])

    def test_follow_up_extracts_natural_language_inputs_without_manual_store(self) -> None:
        manager = TaskStateManager()
        orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))

        first, _ = orchestrator.handle_message("Calculate pipe wall thickness for refinery piping")
        assert first.status == "waiting_input"
        task_id = first.task_id
        assert task_id is not None

        orchestrator.handle_message("yes, straight section")
        orchestrator.handle_message("internal pressure")

        second, _ = orchestrator.handle_message(
            "material ASTM A106, Temperature: 85 Celcius, Pressure: 4 inch",
        )
        assert second.status == "waiting_input"
        assert second.task_id == task_id
        assert second.status != "clarify"

        task = manager.get_task(task_id)
        assert "material" in task.inputs
        assert "design_temperature" in task.inputs
        assert task.inputs["design_temperature"].value == 85.0
        assert "design_pressure" not in task.inputs

        missing = second.data.get("missing_inputs") or []
        assert "pressure_loading" not in missing
        assert "inch is a length unit" in (second.message or "").lower()
