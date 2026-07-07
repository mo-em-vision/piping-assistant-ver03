"""Evaluate requirement activation conditions against task inputs."""

from __future__ import annotations

from engine.graph.assumption_checker import field_value
from models.engineering_plan import ActivationCondition
from models.fact import Fact


def evaluate_activation_condition(
    condition: ActivationCondition,
    existing_inputs: dict[str, Fact],
) -> bool | None:
    """Return True/False when the branch field is resolved, or None when still pending."""
    branch_value = field_value(condition.field, existing_inputs)
    if branch_value is None:
        return None

    actual = str(branch_value)
    operator = condition.operator
    expected = condition.value

    if operator == "equals":
        return actual == str(expected)
    if operator == "not_equals":
        return actual != str(expected)
    if operator == "in":
        allowed = expected if isinstance(expected, list) else [expected]
        return actual in {str(item) for item in allowed}
    return None
