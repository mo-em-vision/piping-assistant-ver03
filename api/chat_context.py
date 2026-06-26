"""Chat context helpers for conversational task assistance."""

from __future__ import annotations

from typing import Any


def trim_conversation_history(
    messages: list[dict[str, str]],
    *,
    max_turns: int = 20,
) -> list[dict[str, str]]:
    if max_turns <= 0:
        return []
    if len(messages) <= max_turns:
        return messages
    return messages[-max_turns:]


def prior_turns_for_llm(
    messages: list[dict[str, Any]],
    *,
    task_id: str | None = None,
) -> list[dict[str, str]]:
    filtered = messages
    if task_id:
        filtered = [message for message in messages if message.get("task_id") == task_id]

    turns: list[dict[str, str]] = []
    for message in filtered[:-1]:
        role = str(message.get("role") or "").strip()
        content = str(message.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            turns.append({"role": role, "content": content})
    return trim_conversation_history(turns)


def build_task_context_brief(
    task_state_payload: dict[str, Any] | None,
    *,
    project_name: str | None = None,
) -> str:
    if not task_state_payload:
        return "No task state is available."

    lines: list[str] = []
    if project_name:
        lines.append(f"Project: {project_name}")

    name = str(task_state_payload.get("name") or "").strip()
    discipline = str(task_state_payload.get("discipline") or "").strip()
    if name:
        lines.append(f"Task: {name} ({discipline})" if discipline else f"Task: {name}")

    description = str(task_state_payload.get("description") or "").strip()
    if description:
        lines.append(f"Description: {description}")

    workflow_id = str(task_state_payload.get("workflow_id") or "").strip()
    if workflow_id:
        lines.append(f"Workflow: {workflow_id}")

    status = str(task_state_payload.get("status") or "").strip()
    if status:
        lines.append(f"Status: {status.replace('_', ' ')}")

    active_node = task_state_payload.get("active_node_context") or {}
    heading = str(active_node.get("display_heading") or "").strip()
    if heading:
        lines.append(f"Current topic: {heading}")

    progress = task_state_payload.get("progress") or {}
    timeline = progress.get("timeline") or progress.get("steps") or []
    current_step_id = progress.get("current_step_id")
    current_step = None
    if isinstance(timeline, list):
        for step in timeline:
            if not isinstance(step, dict):
                continue
            if current_step_id and step.get("id") == current_step_id:
                current_step = step
                break
        if current_step is None:
            for step in timeline:
                if isinstance(step, dict) and step.get("status") == "active":
                    current_step = step
                    break

    if isinstance(current_step, dict):
        title = str(current_step.get("title") or "").strip()
        hint = str(current_step.get("hint") or "").strip()
        if title:
            lines.append(
                f"Current step: {title} — {hint}" if hint else f"Current step: {title}"
            )

    if isinstance(timeline, list):
        completed = [
            step
            for step in timeline
            if isinstance(step, dict)
            and step.get("status") == "done"
            and (step.get("display_value") is not None or step.get("value") is not None)
        ]
        if completed:
            lines.append("Inputs already provided:")
            for step in completed:
                title = str(step.get("title") or step.get("id") or "Input")
                display_value = step.get("display_value")
                value = step.get("value")
                unit = str(step.get("unit") or "")
                if display_value is not None:
                    rendered = str(display_value)
                elif value is not None and unit and unit != "dimensionless":
                    rendered = f"{value} {unit}"
                elif value is not None:
                    rendered = str(value)
                else:
                    rendered = ""
                lines.append(f"- {title}: {rendered}")

    missing_inputs = progress.get("missing_inputs") or []
    if isinstance(missing_inputs, list) and missing_inputs:
        lines.append(f"Still needed: {', '.join(str(item) for item in missing_inputs)}")

    display_outputs = task_state_payload.get("display_outputs") or []
    if isinstance(display_outputs, list):
        output_labels = [
            str(block.get("title") or "").strip()
            for block in display_outputs
            if isinstance(block, dict) and str(block.get("title") or "").strip()
        ]
        if output_labels:
            lines.append(f"Visible workspace content: {'; '.join(output_labels)}")

    return "\n".join(lines) if lines else "No task state is available."
