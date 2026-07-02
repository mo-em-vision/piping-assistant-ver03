"""Deterministic documentation template rendering."""

from __future__ import annotations

import re
from typing import Any

from models.fact import Fact, fact_scalar_value
from models.task import Task
from models.workflow_state import WorkflowParameter

_TEMPLATE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def render_doc_template(text: str, context: dict[str, Any]) -> str:
    """Replace ``{{key}}`` tokens with stringified context values."""
    if not text or not context:
        return text

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in context:
            return match.group(0)
        value = context[key]
        if value is None:
            return ""
        return str(value)

    return _TEMPLATE_PATTERN.sub(_replace, text)


def build_doc_context(
    task: Task | None = None,
    *,
    parameters: dict[str, WorkflowParameter] | None = None,
    inputs: dict[str, Fact] | None = None,
) -> dict[str, Any]:
    """Build template context from task state and structured parameters."""
    context: dict[str, Any] = {}

    if task is not None:
        for key, value in task.outputs.items():
            if not key.endswith("_unit") and not key.endswith("_lookup"):
                context[key] = value
        for key, fact in task.fact_store.active_facts().items():
            context[key] = fact_scalar_value(fact)
            if fact.symbol:
                context[fact.symbol] = fact_scalar_value(fact)

    if inputs:
        for key, fact in inputs.items():
            context.setdefault(key, fact_scalar_value(fact))
            if fact.symbol:
                context.setdefault(fact.symbol, fact_scalar_value(fact))

    if parameters:
        for name, param in parameters.items():
            context.setdefault(name, param.value)
            if param.symbol:
                context.setdefault(param.symbol, param.value)

    return context
