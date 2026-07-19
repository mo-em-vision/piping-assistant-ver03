"""Render report_statement placeholders for engineering decision blocks."""

from __future__ import annotations

import re
from typing import Any

from engine.messaging.decision_interaction_resolver import DecisionInteractionView, selected_option_from_view
from engine.reference.paragraph_hierarchy import paragraph_reference
from engine.reference.standards_reader import StandardsReader

_ALLOWED_PLACEHOLDERS = frozenset({"selected_label", "requesting_reference", "activated_reference"})
_PLACEHOLDER_PATTERN = re.compile(r"\{([a-z_]+)\}")


def _reference_label_for_node(reader: StandardsReader, node_id: str) -> str:
    try:
        record = reader.load(node_id)
    except FileNotFoundError:
        return node_id
    metadata = record.metadata
    presentation = metadata.get("presentation") or {}
    if isinstance(presentation, dict):
        reference_label = str(presentation.get("reference_label") or "").strip()
        if reference_label:
            return reference_label
    paragraph = paragraph_reference(metadata)
    if paragraph:
        return paragraph
    title = str(metadata.get("title") or "").strip()
    return title or node_id


def _validate_template(report_statement: str) -> None:
    for match in _PLACEHOLDER_PATTERN.finditer(report_statement):
        name = match.group(1)
        if name not in _ALLOWED_PLACEHOLDERS:
            raise ValueError(f"Unsupported placeholder {{{name}}} in report_statement")


def render_decision_statement(
    reader: StandardsReader,
    *,
    view: DecisionInteractionView,
    selected_value: Any,
    activated_node_ids: list[str] | None = None,
) -> str:
    """Return report-ready text from authored report_statement and resolved references."""
    option = selected_option_from_view(view, selected_value)
    if option is None:
        raise ValueError(f"No report_statement for decision value {selected_value!r}")

    template = option.report_statement
    _validate_template(template)

    requesting_reference = _reference_label_for_node(reader, view.requesting_node_id)
    activated_ids = list(activated_node_ids or [])
    if activated_ids:
        activated_reference = _reference_label_for_node(reader, activated_ids[0])
    else:
        activated_reference = requesting_reference

    replacements = {
        "selected_label": option.label,
        "requesting_reference": requesting_reference,
        "activated_reference": activated_reference,
    }
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{key}}}", value)
    return " ".join(rendered.split())
