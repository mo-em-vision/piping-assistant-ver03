"""Chat orchestrator tests."""

from __future__ import annotations

from ai.agents.intent_agent import IntentAgent
from api.chat_orchestrator import ChatOrchestrator
from engine.state.state_manager import TaskStateManager
from models.fact import ValidationStatus
from tests.agents.conftest import FakeLLMClient
from tests.helpers.facts import fact_get_value


def test_orchestrator_returns_waiting_input_for_pipe_thickness() -> None:
    manager = TaskStateManager()
    orchestrator = ChatOrchestrator(
        manager,
        llm_client=FakeLLMClient({}),
    )
    response, _ = orchestrator.handle_message("Calculate minimum wall thickness for refinery pipe")

    assert response.status == "waiting_input"
    assert response.task_id is not None
    assert "straight_pipe_section" in (response.data.get("missing_inputs") or [])
    assert "straight pipe section" in response.message.lower()


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
    assert fact_get_value(task, "internal_design_gage_pressure") == 500.0
    assert fact_get_value(task, "material_grade") == "astm_a106_gr_b"
    assert fact_get_value(task, "design_temperature") == 85.0
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
    assert fact_get_value(task, "pressure_loading") == "internal_pressure"


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
    assert fact_get_value(task, "internal_design_gage_pressure") == 500.0
    assert fact_get_value(task, "nominal_pipe_size") == "10"
    pressure_fact = task.fact_store.active_fact("internal_design_gage_pressure")
    assert pressure_fact is not None
    assert pressure_fact.validation.status == ValidationStatus.CONFIRMED


def test_orchestrator_accepts_numbered_pressure_loading_choice() -> None:
    manager = TaskStateManager()
    orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))

    orchestrator.handle_message("Calculate minimum wall thickness for refinery pipe")
    orchestrator.handle_message("yes, straight section")
    response, _ = orchestrator.handle_message("2")

    assert response.status == "waiting_input"
    task_id = response.task_id
    assert task_id is not None
    task = manager.get_task(task_id)
    assert fact_get_value(task, "pressure_loading") == "external_pressure"


def test_orchestrator_shows_formula_prompt_after_internal_pressure() -> None:
    manager = TaskStateManager()
    orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))

    orchestrator.handle_message("Calculate minimum wall thickness for refinery pipe")
    orchestrator.handle_message("yes, straight section")
    response, _ = orchestrator.handle_message("internal pressure")

    assert response.status == "waiting_input"
    assert "Formula:" in response.message
    assert "Missing parameters:" in response.message
    assert "t = PD" in response.message


def test_orchestrator_shows_numbered_path_decision_before_formula() -> None:
    manager = TaskStateManager()
    orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))

    orchestrator.handle_message("Calculate minimum wall thickness for refinery pipe")
    orchestrator.handle_message("yes, straight section")
    response, _ = orchestrator.handle_message("still deciding")

    assert response.status == "waiting_input"
    assert "1." in response.message
    assert "2." in response.message
    assert "pressure_loading" in (response.data.get("missing_inputs") or [])
    assert "Formula:" not in response.message


def test_orchestrator_symbol_labeled_input_updates_known_parameters() -> None:
    manager = TaskStateManager()
    orchestrator = ChatOrchestrator(manager, llm_client=FakeLLMClient({}))

    orchestrator.handle_message("Calculate minimum wall thickness for refinery pipe")
    orchestrator.handle_message("yes, straight section")
    orchestrator.handle_message("internal pressure")
    response, _ = orchestrator.handle_message("P: 8 bar, D: 4 inch")

    assert response.status == "waiting_input"
    task_id = response.task_id
    assert task_id is not None
    task = manager.get_task(task_id)
    assert fact_get_value(task, "internal_design_gage_pressure") == 8.0
    assert fact_get_value(task, "outside_diameter") == 4.0
    assert "material_grade" in (response.data.get("missing_inputs") or [])
