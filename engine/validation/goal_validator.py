"""Validate runtime Goal nodes against the Goal Node template."""

from __future__ import annotations

from typing import Any

from models.goal import Goal, GoalClass

_FORBIDDEN_METADATA = frozenset(
    {
        "equation_formula",
        "standard_text",
        "workflow_definition",
        "calculation_result",
        "fact_value",
    }
)

_GOAL_CLASSES = frozenset(item.value for item in GoalClass)


def validate_goal(goal: Goal) -> list[str]:
    issues: list[str] = []
    if goal.type != "goal":
        issues.append("type must be 'goal'")
    if not goal.id:
        issues.append("missing id")
    if not goal.key:
        issues.append("missing key")
    if not goal.name:
        issues.append("missing name")
    if goal.goal_class.value not in _GOAL_CLASSES:
        issues.append(f"invalid goal_class: {goal.goal_class!r}")
    if not goal.target_parameter:
        issues.append("missing target_parameter")
    elif not str(goal.target_parameter).startswith("PARAM-"):
        issues.append(f"target_parameter must reference PARAM-*, got {goal.target_parameter!r}")
    if goal.provenance is None:
        issues.append("missing provenance")
    if goal.satisfaction is None:
        issues.append("missing satisfaction")
    elif goal.satisfaction.required_output is None:
        issues.append("missing satisfaction.required_output")

    for field in _FORBIDDEN_METADATA:
        if field in (goal.metadata or {}):
            issues.append(f"forbidden metadata field: {field}")

    if goal.goal_class == GoalClass.INPUT and goal.question is None:
        issues.append("input_goal requires question")

    return issues


def validate_goal_dict(data: dict[str, Any]) -> list[str]:
    from models.goal import goal_from_dict

    return validate_goal(goal_from_dict(data))
