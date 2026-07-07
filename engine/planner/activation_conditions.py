"""Evaluate requirement activation conditions against task inputs."""

from __future__ import annotations

from typing import Literal

from engine.graph.assumption_checker import field_value
from models.engineering_plan import ActivationCondition, PlanRequirement
from models.fact import Fact

ActivationStatus = Literal["active", "conditional", "not_applicable"]


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


def resolve_activation_status(
    requirement: PlanRequirement,
    known_facts: dict[str, Fact],
) -> ActivationStatus:
    """Resolve whether a requirement is active, conditional, or not applicable."""
    condition = requirement.activation_condition
    if condition is None:
        return "active"

    outcome = evaluate_activation_condition(condition, known_facts)
    if outcome is None:
        return "conditional"
    if outcome:
        return "active"
    return "not_applicable"
