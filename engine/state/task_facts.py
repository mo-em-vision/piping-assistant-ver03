"""Task-level fact access helpers."""

from __future__ import annotations

from typing import Any

from models.fact import (
    Fact,
    FactClass,
    FactProvenance,
    FactSource,
    SourceType,
    ValidationStatus,
    build_categorical_fact,
    build_numeric_fact,
    fact_from_user_submission,
    fact_is_expansion_ready,
    fact_scalar_value,
    fact_unit,
    pending_parameter_fact,
    proposed_default_fact,
)
from models.fact_store import FactStore
from models.execution_context import InputConflict
from models.task import Task

from engine.reference.parameter_keys import active_material_grade_fact


def active_facts(task: Task) -> dict[str, Fact]:
    return task.fact_store.active_facts()


def active_fact(task: Task, key: str) -> Fact | None:
    return task.fact_store.active_fact(key)


def active_material_fact(task: Task) -> Fact | None:
    """Backward-compatible alias for ``active_material_grade_fact``."""
    return active_material_grade_fact(task)


def fact_value(task: Task, key: str, default: Any = None) -> Any:
    return task.fact_store.get_value(key, default)


def fact_unit_for_key(task: Task, key: str, default: str = "dimensionless") -> str:
    fact = task.fact_store.active_fact(key)
    if fact is None:
        return default
    return fact_unit(fact)


def store_fact(task: Task, fact: Fact) -> Task:
    ctx = task.execution_context
    if fact.provenance.execution_context_id is None:
        fact.provenance.execution_context_id = ctx.id
    existing = ctx.fact_store.active_fact(fact.key)
    if existing is not None and fact_scalar_value(existing) != fact_scalar_value(fact):
        if not (
            existing.validation.status == ValidationStatus.PENDING
            and existing.requires_confirmation
            and fact_is_expansion_ready(fact)
        ):
            task.conflicts.append(
                InputConflict(
                    previous_calculation_invalid=True,
                    reason="input changed",
                    input_id=fact.key,
                    previous_value=fact_scalar_value(existing),
                    new_value=fact_scalar_value(fact),
                )
            )
    ctx.fact_store.upsert_active(fact)
    from engine.state.assumption_recorder import record_assumption_from_fact
    from engine.state.decision_recorder import record_decision_from_fact
    from engine.state.execution_context_sync import refresh_execution_context_for_task

    value = fact_scalar_value(fact)
    if value is not None:
        record_decision_from_fact(task, fact.key, value)
        record_assumption_from_fact(task, fact.key, value)
    refresh_execution_context_for_task(task)
    return task


def store_user_fact(
    task: Task,
    key: str,
    value: Any,
    *,
    unit: str = "dimensionless",
    workflow_id: str | None = None,
    collected_at_node: str | None = None,
    collected_at_phase: str | None = None,
    symbol: str | None = None,
    description: str | None = None,
) -> Task:
    fact = fact_from_user_submission(
        key=key,
        value=value,
        unit=unit,
        task_id=task.task_id,
        workflow_id=workflow_id,
        collected_at_node=collected_at_node,
        collected_at_phase=collected_at_phase,
        symbol=symbol,
        description=description,
    )
    return store_fact(task, fact)


def store_proposed_default(
    task: Task,
    key: str,
    value: Any,
    *,
    unit: str = "dimensionless",
    **kwargs: Any,
) -> Task:
    fact = proposed_default_fact(key, value, task_id=task.task_id, unit=unit, **kwargs)
    return store_fact(task, fact)


def merge_fact_store(task: Task, facts: dict[str, Fact] | FactStore) -> None:
    if isinstance(facts, FactStore):
        for fact in facts.facts.values():
            if fact.supersession.active:
                task.fact_store.upsert_active(fact)
            else:
                task.fact_store.append_fact(fact)
        return
    for fact in facts.values():
        task.fact_store.upsert_active(fact)


def deactivate_fact(task: Task, key: str) -> None:
    """Remove the active fact for a parameter key without deleting history."""
    fact = task.fact_store.active_fact(key)
    if fact is None:
        return
    fact.supersession.active = False
    fact.validation.status = ValidationStatus.SUPERSEDED
    task.fact_store.active_by_key.pop(key, None)


def pending_parameter_fact_from_descriptor(
    descriptor: Any,
    *,
    task_id: str,
) -> Fact:
    """Build a pending fact placeholder from a parameter registry descriptor."""
    return pending_parameter_fact(
        descriptor.input_id,
        task_id=task_id,
        unit=descriptor.unit,
        parameter=descriptor.input_id,
        symbol=descriptor.symbol,
        description=descriptor.description,
        introduced_at_node=descriptor.introduced_at_node,
    )


def store_lookup_numeric_fact(
    task: Task,
    *,
    key: str,
    amount: float | int,
    unit: str,
    table_ref: str | None = None,
    symbol: str | None = None,
    description: str | None = None,
    original_value: Any | None = None,
    original_unit: str | None = None,
) -> Fact:
    """Store a table-lookup numeric fact on the task."""
    from engine.reference.param_resolver import resolve_parameter_id

    fact = build_numeric_fact(
        key=key,
        parameter=resolve_parameter_id(key),
        amount=amount,
        unit=unit,
        fact_class=FactClass.LOOKED_UP,
        source=FactSource(
            source_type=SourceType.TABLE_LOOKUP,
            source_id=table_ref or "TABLE",
            description=description,
        ),
        provenance=FactProvenance(task_id=task.task_id, created_by="lookup"),
        validation_status=ValidationStatus.CONFIRMED,
        symbol=symbol,
        description=description,
        original_value=original_value,
        original_unit=original_unit,
    )
    store_fact(task, fact)
    return fact


def store_lookup_categorical_fact(
    task: Task,
    *,
    key: str,
    label: str,
    table_ref: str | None = None,
    symbol: str | None = None,
    description: str | None = None,
    original_value: Any | None = None,
) -> Fact:
    """Store a table-lookup categorical fact on the task."""
    from engine.reference.param_resolver import resolve_parameter_id

    fact = build_categorical_fact(
        key=key,
        parameter=resolve_parameter_id(key),
        label=label,
        normalized_key=None,
        fact_class=FactClass.LOOKED_UP,
        source=FactSource(
            source_type=SourceType.TABLE_LOOKUP,
            source_id=table_ref or "TABLE",
            description=description,
        ),
        provenance=FactProvenance(task_id=task.task_id, created_by="lookup"),
        validation_status=ValidationStatus.CONFIRMED,
        symbol=symbol,
        description=description,
        original_value=original_value,
    )
    store_fact(task, fact)
    return fact


def store_system_categorical_fact(
    task: Task,
    *,
    key: str,
    label: str,
    symbol: str | None = None,
    description: str | None = None,
) -> Fact:
    """Store a confirmed system-generated categorical fact."""
    from engine.reference.param_resolver import resolve_parameter_id

    fact = build_categorical_fact(
        key=key,
        parameter=resolve_parameter_id(key),
        label=label,
        normalized_key=None,
        fact_class=FactClass.SYSTEM_GENERATED,
        source=FactSource(source_type=SourceType.SYSTEM, source_id="SYSTEM"),
        provenance=FactProvenance(task_id=task.task_id, created_by="system"),
        validation_status=ValidationStatus.CONFIRMED,
        symbol=symbol,
        description=description,
    )
    store_fact(task, fact)
    return fact
