"""Executor-level lookup execution and fact storage."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.executor.lookup_engine import LookupEngine
from engine.state.task_facts import store_lookup_categorical_fact, store_lookup_numeric_fact
from models.task import Task


@dataclass
class LookupExecutionResult:
    outputs: dict[str, float] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


def execute_lookup_rule(
    *,
    pack_root: Path,
    table_ref: str,
    rule: str,
    inputs: dict[str, Any],
    returns: list[dict[str, Any]] | None = None,
) -> LookupExecutionResult:
    """Execute a v2 table rule lookup without graph-layer orchestration."""
    engine = LookupEngine(pack_root)
    result = engine.execute_rule_lookup(
        table_ref=table_ref,
        rule=rule,
        inputs=inputs,
        returns=returns,
    )
    return LookupExecutionResult(outputs=dict(result.outputs), meta=dict(result.meta))


def store_numeric_lookup_result(
    task: Task,
    *,
    key: str,
    amount: float,
    unit: str,
    table_ref: str,
    symbol: str | None = None,
    description: str | None = None,
    lookup_node: str | None = None,
    lookup_rule: str | None = None,
    input_facts: list[str] | None = None,
    lookup_row_identity: str | None = None,
    authority_id: str | None = None,
    produced_by_node: str | None = None,
) -> None:
    """Store a table-lookup numeric fact with lookup provenance."""
    store_lookup_numeric_fact(
        task,
        key=key,
        amount=amount,
        unit=unit,
        table_ref=table_ref,
        symbol=symbol,
        description=description,
        lookup_node=lookup_node,
        lookup_rule=lookup_rule,
        input_facts=input_facts,
        lookup_row_identity=lookup_row_identity,
        authority_id=authority_id,
        produced_by_node=produced_by_node,
    )


def store_categorical_lookup_result(
    task: Task,
    *,
    key: str,
    label: str,
    table_ref: str | None = None,
    symbol: str | None = None,
    description: str | None = None,
    original_value: Any | None = None,
    lookup_node: str | None = None,
    lookup_rule: str | None = None,
    input_facts: list[str] | None = None,
    lookup_row_identity: str | None = None,
    authority_id: str | None = None,
    produced_by_node: str | None = None,
) -> None:
    """Store a table-lookup categorical fact with lookup provenance."""
    store_lookup_categorical_fact(
        task,
        key=key,
        label=label,
        table_ref=table_ref,
        symbol=symbol,
        description=description,
        original_value=original_value,
        lookup_node=lookup_node,
        lookup_rule=lookup_rule,
        input_facts=input_facts,
        lookup_row_identity=lookup_row_identity,
        authority_id=authority_id,
        produced_by_node=produced_by_node,
    )
