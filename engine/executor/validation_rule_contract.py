"""Supported validation_rule node contract assessment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.reference.standards_reader import StandardsReader

SUPPORTED_CONDITION_GROUPS = frozenset({"all_of", "any_of"})


@dataclass(frozen=True)
class ValidationRuleSupport:
    """Whether a validation_rule node can run under the generic runner."""

    supported: bool
    reason: str = ""


def _requires_entries(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    requires = metadata.get("requires") or []
    if not isinstance(requires, list):
        return []
    return [item for item in requires if isinstance(item, dict)]


def _result_entry(metadata: dict[str, Any]) -> dict[str, Any] | None:
    result = metadata.get("result")
    if isinstance(result, dict):
        return result
    return None


def assess_validation_rule_support(
    metadata: dict[str, Any],
    *,
    reader: StandardsReader,
) -> ValidationRuleSupport:
    """Return whether metadata conforms to the supported validation-rule contract."""
    if str(metadata.get("type", "")) != "validation_rule":
        return ValidationRuleSupport(False, "not a validation_rule node")

    rule_class = str(metadata.get("rule_class") or "validation").strip()
    if rule_class and rule_class != "validation":
        return ValidationRuleSupport(False, f"unsupported rule_class: {rule_class}")

    result = _result_entry(metadata)
    if result is None:
        return ValidationRuleSupport(False, "missing result block")

    output_param_id = str(result.get("parameter") or "").strip()
    if not output_param_id.startswith("PARAM-"):
        return ValidationRuleSupport(False, "result.parameter must be PARAM-*")
    try:
        reader.load(output_param_id)
    except FileNotFoundError:
        return ValidationRuleSupport(False, f"result parameter not found: {output_param_id}")

    conditions = metadata.get("conditions")
    if not isinstance(conditions, dict) or not conditions:
        execution = metadata.get("execution") or {}
        if isinstance(execution, dict) and execution.get("steps"):
            return ValidationRuleSupport(
                False,
                "execution.steps without evaluable conditions",
            )
        return ValidationRuleSupport(False, "missing conditions block")

    active_groups = [
        key
        for key in SUPPORTED_CONDITION_GROUPS
        if isinstance(conditions.get(key), list) and conditions[key]
    ]
    if not active_groups:
        return ValidationRuleSupport(
            False,
            "missing evaluable conditions (all_of or any_of)",
        )

    unsupported = [
        key
        for key in conditions
        if key not in SUPPORTED_CONDITION_GROUPS and conditions[key]
    ]
    if unsupported:
        return ValidationRuleSupport(
            False,
            f"unsupported condition combinators: {', '.join(sorted(unsupported))}",
        )

    for item in _requires_entries(metadata):
        param_id = str(item.get("parameter") or "").strip()
        if not param_id.startswith("PARAM-"):
            symbol = str(item.get("symbol") or item.get("alias") or "?")
            return ValidationRuleSupport(
                False,
                f"requires entry {symbol!r} missing parameter: PARAM-* binding",
            )

    return ValidationRuleSupport(True)
