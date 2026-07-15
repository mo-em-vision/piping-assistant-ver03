"""Generic metadata-driven validation_rule execution."""

from __future__ import annotations

from typing import Any, Callable

from engine.executor.validation_rule_contract import (
    SUPPORTED_CONDITION_GROUPS,
    assess_validation_rule_support,
)
from engine.graph.assumption_checker import applicability_expansion_status
from engine.graph.relationship_resolver import resolve_requires_for_node
from engine.reference.standards_reader import NodeRecord, StandardsReader
from engine.rules.rule_engine import ConditionResult, RuleEngine
from engine.state.task_facts import store_validation_rule_categorical_fact
from models.execution import NodeExecutionResult, NodeExecutionStatus
from models.fact import Fact
from models.task import Task


def execute_validation_rule(
    record: NodeRecord,
    *,
    reader: StandardsReader,
    rule_engine: RuleEngine,
    task_inputs: dict[str, Fact],
    dependency_outputs: dict[str, Any],
    resolve_value: Callable[..., float | None],
    param_fact_key: Callable[[dict[str, Any]], str],
    output_alias_keys: Callable[[str, str], list[str]],
    task: Task | None = None,
) -> NodeExecutionResult:
    """Evaluate a validation_rule node from metadata contract, not node id."""
    metadata = record.metadata
    support = assess_validation_rule_support(metadata, reader=reader)
    if not support.supported:
        return NodeExecutionResult(
            node_id=record.node_id,
            status=NodeExecutionStatus.SKIPPED,
            trace={"reason": support.reason, "contract": "validation_rule"},
        )

    applicability = applicability_expansion_status(metadata, task_inputs)
    if applicability == "failed":
        return NodeExecutionResult(
            node_id=record.node_id,
            status=NodeExecutionStatus.SKIPPED,
            trace={"reason": "applicability not satisfied", "contract": "validation_rule"},
        )
    if applicability == "pending":
        return NodeExecutionResult(
            node_id=record.node_id,
            status=NodeExecutionStatus.AWAITING_INPUT,
            errors=["Validation rule applicability inputs are not yet decided"],
            trace={"reason": "applicability pending", "contract": "validation_rule"},
        )

    store = reader.graph_store
    bindings = resolve_requires_for_node(store, record.node_id, metadata)
    if not bindings:
        return NodeExecutionResult(
            node_id=record.node_id,
            status=NodeExecutionStatus.SKIPPED,
            trace={"reason": "no resolvable requires bindings", "contract": "validation_rule"},
        )

    symbol_values: dict[str, float] = {}
    missing: list[str] = []
    for binding in bindings:
        value = resolve_value(
            binding.param_id,
            task_inputs=task_inputs,
            dependency_outputs=dependency_outputs,
            sympy_symbol=binding.sympy_symbol,
        )
        if value is None:
            try:
                param = reader.load(binding.param_id)
                missing.append(
                    str(param.metadata.get("key") or binding.sympy_symbol),
                )
            except FileNotFoundError:
                missing.append(binding.sympy_symbol)
        else:
            symbol_values[binding.sympy_symbol] = value

    if missing:
        return NodeExecutionResult(
            node_id=record.node_id,
            status=NodeExecutionStatus.AWAITING_INPUT,
            errors=[f"Missing required inputs: {', '.join(missing)}"],
            trace={"missing_inputs": missing, "contract": "validation_rule"},
        )

    conditions = metadata.get("conditions") or {}
    condition_results: list[ConditionResult] = []
    group_outcomes: dict[str, bool] = {}

    for group_name in SUPPORTED_CONDITION_GROUPS:
        group = conditions.get(group_name)
        if not isinstance(group, list) or not group:
            continue
        results: list[ConditionResult] = []
        for index, item in enumerate(group):
            if not isinstance(item, dict):
                continue
            expression = str(item.get("expression") or "").strip()
            if not expression:
                continue
            cond_id = str(item.get("id") or f"{group_name}_{index}")
            result = rule_engine.evaluate_condition(
                condition_id=cond_id,
                expression=expression,
                variables=symbol_values,
            )
            results.append(result)
            condition_results.append(result)
        if not results:
            continue
        if group_name == "all_of":
            group_outcomes[group_name] = all(item.passed for item in results)
        else:
            group_outcomes[group_name] = any(item.passed for item in results)

    if not group_outcomes:
        return NodeExecutionResult(
            node_id=record.node_id,
            status=NodeExecutionStatus.SKIPPED,
            trace={"reason": "no evaluable condition expressions", "contract": "validation_rule"},
        )

    passed = all(group_outcomes.values())
    warnings: list[str] = []
    errors: list[str] = []
    on_fail = metadata.get("on_fail") or {}
    if not passed and isinstance(on_fail, dict):
        message = str(on_fail.get("message") or "").strip()
        severity = str(on_fail.get("severity") or "warning").strip().lower()
        blocks_goal = bool(on_fail.get("blocks_goal"))
        if message:
            if severity == "error" or blocks_goal:
                errors.append(message)
            else:
                warnings.append(message)
        elif blocks_goal:
            errors.append("Validation rule condition failed")

    status = NodeExecutionStatus.COMPLETED
    if errors:
        status = NodeExecutionStatus.ERROR

    result_entry = metadata.get("result") or {}
    output_param_id = str(result_entry.get("parameter") or "").strip()
    output_param = reader.load(output_param_id)
    output_key = param_fact_key(output_param.metadata)
    output_symbol = str(
        result_entry.get("symbol")
        or output_param.metadata.get("canonical_symbol")
        or ""
    ).strip()
    output_label = "true" if passed else "false"

    outputs: dict[str, Any] = {
        output_symbol: passed,
        output_key: output_label,
    }
    for alias in output_alias_keys(output_symbol, output_key):
        outputs[alias] = passed if alias == output_symbol else output_label

    if task is not None and output_key:
        store_validation_rule_categorical_fact(
            task,
            key=output_key,
            label=output_label,
            validation_rule_id=record.node_id,
            symbol=output_symbol or None,
            description=str(output_param.metadata.get("description") or "") or None,
        )

    trace = {
        "contract": "validation_rule",
        "condition_groups": group_outcomes,
        "conditions": [
            {
                "condition_id": item.condition_id,
                "expression": item.expression,
                "passed": item.passed,
                "message": item.message,
            }
            for item in condition_results
        ],
        "passed": passed,
        "result_parameter": output_param_id,
    }

    return NodeExecutionResult(
        node_id=record.node_id,
        status=status,
        inputs=symbol_values,
        outputs=outputs,
        warnings=warnings,
        errors=errors,
        trace=trace,
    )
