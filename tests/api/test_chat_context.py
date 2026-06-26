"""Tests for chat context helpers."""

from __future__ import annotations

from api.chat_context import build_task_context_brief, prior_turns_for_llm, trim_conversation_history


def test_trim_conversation_history_keeps_latest_turns() -> None:
    messages = [{"role": "user", "content": f"message {index}"} for index in range(25)]

    trimmed = trim_conversation_history(messages, max_turns=5)

    assert len(trimmed) == 5
    assert trimmed[0]["content"] == "message 20"
    assert trimmed[-1]["content"] == "message 24"


def test_prior_turns_for_llm_excludes_latest_message_and_filters_task() -> None:
    messages = [
        {"role": "user", "content": "other task", "task_id": "task-b"},
        {"role": "user", "content": "first", "task_id": "task-a"},
        {"role": "assistant", "content": "answer", "task_id": "task-a"},
        {"role": "user", "content": "follow up", "task_id": "task-a"},
    ]

    turns = prior_turns_for_llm(messages, task_id="task-a")

    assert turns == [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "answer"},
    ]


def test_build_task_context_brief_includes_task_and_progress_fields() -> None:
    brief = build_task_context_brief(
        {
            "name": "Pipe Thickness Calculation",
            "discipline": "Piping",
            "workflow_id": "B313-PIPE-WALL-THICKNESS-DESIGN",
            "status": "in_progress",
            "active_node_context": {"display_heading": "§304.1.2"},
            "progress": {
                "current_step_id": "design_pressure",
                "missing_inputs": ["material"],
                "timeline": [
                    {
                        "id": "design_pressure",
                        "title": "Design pressure",
                        "status": "done",
                        "value": 8,
                        "unit": "bar",
                        "display_value": "8 bar",
                    }
                ],
            },
            "display_outputs": [{"title": "Wall thickness result"}],
        },
        project_name="Refinery Expansion",
    )

    assert "Project: Refinery Expansion" in brief
    assert "Task: Pipe Thickness Calculation" in brief
    assert "Current topic: §304.1.2" in brief
    assert "Still needed: material" in brief
    assert "Visible workspace content: Wall thickness result" in brief
