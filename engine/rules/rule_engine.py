"""Minimal rule evaluation for conditions (not full Validation Layer)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.executor.expression_evaluator import UnsafeExpressionError, evaluate_expression


@dataclass
class ConditionResult:
    condition_id: str
    expression: str
    passed: bool
    message: str | None = None


class RuleEngine:
    """Evaluate node-defined conditions using safe expression evaluation."""

    def evaluate_condition(
        self,
        *,
        condition_id: str,
        expression: str,
        variables: dict[str, float],
    ) -> ConditionResult:
        normalized = expression.replace("<", " < ").replace(">", " > ")
        normalized = " ".join(normalized.split())

        try:
            if " < " in normalized:
                left, right = normalized.split(" < ", 1)
                passed = evaluate_expression(left, variables) < evaluate_expression(right, variables)
            elif " > " in normalized:
                left, right = normalized.split(" > ", 1)
                passed = evaluate_expression(left, variables) > evaluate_expression(right, variables)
            elif " <= " in normalized:
                left, right = normalized.split(" <= ", 1)
                passed = evaluate_expression(left, variables) <= evaluate_expression(right, variables)
            elif " >= " in normalized:
                left, right = normalized.split(" >= ", 1)
                passed = evaluate_expression(left, variables) >= evaluate_expression(right, variables)
            elif " == " in normalized:
                left, right = normalized.split(" == ", 1)
                passed = evaluate_expression(left, variables) == evaluate_expression(right, variables)
            else:
                passed = bool(evaluate_expression(normalized, variables))
        except (UnsafeExpressionError, ValueError, ZeroDivisionError) as exc:
            return ConditionResult(
                condition_id=condition_id,
                expression=expression,
                passed=False,
                message=str(exc),
            )

        return ConditionResult(
            condition_id=condition_id,
            expression=expression,
            passed=passed,
            message=None if passed else f"Condition failed: {expression}",
        )

    def validate_positive(self, name: str, value: Any) -> str | None:
        if isinstance(value, (int, float)) and value <= 0:
            return f"{name} must be positive"
        return None
