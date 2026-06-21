"""Chat orchestrator tests."""

from __future__ import annotations

from ai.agents.intent_agent import IntentAgent
from cli.orchestrator import ChatOrchestrator
from engine.state.state_manager import TaskStateManager
from models.input import InputStatus
from tests.agents.conftest import FakeLLMClient


def test_orchestrator_returns_waiting_input_for_pipe_thickness() -> None:
    manager = TaskStateManager()
    orchestrator = ChatOrchestrator(
        manager,
        llm_client=FakeLLMClient({}),
    )
    response, _ = orchestrator.handle_message("Calculate minimum wall thickness for refinery pipe")

    assert response.status == "waiting_input"
    assert response.task_id is not None
    assert "pressure_loading" in (response.data.get("missing_inputs") or [])


def test_orchestrator_extracts_partial_inputs_on_follow_up() -> None:
    manager = TaskStateManager()
    orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))

    first, _ = orchestrator.handle_message("Calculate minimum wall thickness for refinery pipe")
    task_id = first.task_id
    assert task_id is not None

    orchestrator.handle_message("yes, straight section")
    orchestrator.handle_message("internal pressure")

    second, _ = orchestrator.handle_message(
        "design pressure 500 psi, material ASTM A106, temperature 85 C",
    )
    assert second.status == "waiting_input"
    assert second.task_id == task_id

    task = manager.get_task(task_id)
    assert task.inputs["design_pressure"].value == 500.0
    assert task.inputs["material"].value == "SA-106B"
    assert task.inputs["design_temperature"].value == 85.0
    assert "pressure_loading" not in (second.data.get("missing_inputs") or [])


def test_orchestrator_advances_after_internal_pressure_reply() -> None:
    manager = TaskStateManager()
    orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))

    first, _ = orchestrator.handle_message("Calculate minimum wall thickness for refinery pipe")
    task_id = first.task_id
    assert task_id is not None

    orchestrator.handle_message("yes, straight section")
    second, _ = orchestrator.handle_message("internal pressure")
    assert second.status == "waiting_input"
    assert second.task_id == task_id
    assert "pressure_loading" not in (second.data.get("missing_inputs") or [])

    task = manager.get_task(task_id)
    assert task.inputs["pressure_loading"].value == "internal_pressure"


def test_orchestrator_confirms_proposed_default() -> None:
    manager = TaskStateManager()
    orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))

    orchestrator.handle_message("Calculate minimum wall thickness for refinery pipe")
    orchestrator.handle_message("yes, straight section")
    orchestrator.handle_message("internal pressure")
    orchestrator.handle_message(
        "design pressure 500 psi, NPS 10, material SA-106B, temp 200 F"
    )
    orchestrator.handle_message("confirm")
    response, _ = orchestrator.handle_message("confirm")
    task_id = response.task_id
    assert task_id is not None

    task = manager.get_task(task_id)
    assert task.inputs["weld_joint_efficiency"].status == InputStatus.CONFIRMED
