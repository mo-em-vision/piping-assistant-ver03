"""Tests for completion summary collectors and result summary display."""

from __future__ import annotations

from api.completion_summary_collectors import (
    APPLIED_STANDARD_HEADER,
    ASSUMPTIONS_INTRO,
    collect_applied_paragraphs,
    collect_completion_assumptions,
)
from api.result_summary_display import build_result_summary_display_block
from engine.state.state_manager import TaskStateManager
from engine.state.task_facts import store_user_fact
from models.task import TaskStatus
from tests.api.test_equation_display_trace import _apply_simulated_completed_state
from tests.helpers.goals import task_with_planning


def _store_confirmed_fact(task, field: str, value) -> None:
    store_user_fact(task, field, value)


def test_collect_applied_paragraphs_from_equation_trace(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("applied-paragraphs", status=TaskStatus.COMPLETED)
    _apply_simulated_completed_state(task, standards_reader)

    header, paragraphs = collect_applied_paragraphs(task, standards_reader)
    assert header == APPLIED_STANDARD_HEADER
    labels = [item.label for item in paragraphs]
    assert "ASME B31.3 §304.1.2" in labels
    assert "ASME B31.3 §304.1.1" in labels


def test_collect_completion_assumptions_from_graph_metadata(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("completion-assumptions", status=TaskStatus.COMPLETED)
    _apply_simulated_completed_state(task, standards_reader)
    task_with_planning(
        task,
        {"path_decision": {"selected_node": "304.1.2-a"}},
        workflow_id="pipe_wall_thickness_design",
    )
    task.active_nodes = ["304.1.1-a", "304.1.2-a"]
    _store_confirmed_fact(task, "straight_pipe_section", True)
    _store_confirmed_fact(task, "pressure_design_case", "internal_pressure")

    assumptions = collect_completion_assumptions(task, standards_reader)
    phrases = [item.phrase for item in assumptions]
    assert any("straight section" in phrase.lower() for phrase in phrases)
    assert any("t < d/6" in phrase.lower() for phrase in phrases)
    assert any("internal pressure" in phrase.lower() for phrase in phrases)
    assert all(item.reference_label.startswith("ASME B31.3") for item in assumptions)


def test_result_summary_uses_documentation_summary_and_assumptions(standards_reader) -> None:
    manager = TaskStateManager()
    task = manager.create_task("result-summary-enhanced", status=TaskStatus.COMPLETED)
    _apply_simulated_completed_state(task, standards_reader)
    task_with_planning(
        task,
        {"path_decision": {"selected_node": "304.1.2-a"}},
        workflow_id="pipe_wall_thickness_design",
    )
    task.active_nodes = ["304.1.1-a", "304.1.2-a"]
    _store_confirmed_fact(task, "straight_pipe_section", True)
    _store_confirmed_fact(task, "pressure_design_case", "internal_pressure")

    block = build_result_summary_display_block(task, standards_reader)
    assert block is not None

    content = block["content"]
    assert "t_m = 2.252" in content
    assert "selected branch" in content
    assert APPLIED_STANDARD_HEADER in content
    assert "ASME B31.3 §304.1.1" in content
    assert "ASME B31.3 §304.1.2" in content
    assert ASSUMPTIONS_INTRO in content
    assert "Applied conditions:" not in content

    payload = block["payload"]
    assert payload.get("documentation_summary")
    assert isinstance(payload.get("applied_paragraphs"), list)
    assert isinstance(payload.get("assumptions"), list)
    assert "applied_conditions" not in payload
