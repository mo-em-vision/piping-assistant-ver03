"""Format captured ask/answer text for durable input archive transcript blocks."""

from __future__ import annotations

from typing import Any

from api.equation_inputs_display import format_value_with_unit_for_display
from models.fact import Fact, fact_scalar_value, fact_unit

_HIDDEN_UNITS = frozenset({"dimensionless", "1", ""})


def format_archive_ask_text(pre_submit_ask: dict[str, Any] | None) -> str | None:
    """Return composer-visible ask text from a captured pre-submit current_ask."""
    if not isinstance(pre_submit_ask, dict):
        return None

    short_prompt = pre_submit_ask.get("short_prompt")
    if isinstance(short_prompt, str) and short_prompt.strip():
        return short_prompt.strip()

    prompt = pre_submit_ask.get("prompt")
    if isinstance(prompt, str) and prompt.strip():
        return prompt.strip()

    return None


def format_archive_answer_text(
    fact: Fact,
    *,
    parameter_id: str,
) -> tuple[str, str | None]:
    """Return display text and optional unit for an archived answer block."""
    value = fact_scalar_value(fact)
    unit = fact_unit(fact)
    resolved_unit = None if unit in _HIDDEN_UNITS else unit

    from api.serializers import _categorical_selection_display

    display = _categorical_selection_display(parameter_id, value)
    if display:
        return display, resolved_unit

    if parameter_id == "straight_pipe_section" and isinstance(value, bool):
        return ("Yes" if value else "No"), resolved_unit

    display = format_value_with_unit_for_display(value, unit)
    if display:
        return display, resolved_unit
    if value is None:
        return "", resolved_unit
    return str(value), resolved_unit
