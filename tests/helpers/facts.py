"""Test helpers for creating runtime facts on tasks."""

from __future__ import annotations

from typing import Any

from engine.state.fact_migration import fact_from_engineering_input, facts_from_legacy_inputs
from engine.state.task_facts import store_fact, store_user_fact
from models.fact import Fact, ValidationStatus, fact_scalar_value, fact_unit
from models.input import EngineeringInput, InputSource, InputStatus
from models.task import Task


def set_fact(
    task: Task,
    key: str,
    value: Any,
    *,
    unit: str = "dimensionless",
    status: ValidationStatus = ValidationStatus.CONFIRMED,
) -> Fact:
    fact = store_user_fact(task, key, value, unit=unit)
    active = task.fact_store.active_fact(key)
    assert active is not None
    if status != ValidationStatus.CONFIRMED:
        active.validation.status = status
    return active


def set_fact_from_input(task: Task, inp: EngineeringInput) -> Fact:
    fact = fact_from_engineering_input(
        inp,
        task_id=task.task_id,
        workflow_id=str(task.outputs.get("workflow") or ""),
    )
    store_fact(task, fact)
    return fact


def legacy_input(
    input_id: str,
    value: Any,
    unit: str = "dimensionless",
    *,
    source: InputSource = InputSource.USER,
    status: InputStatus = InputStatus.CONFIRMED,
    **kwargs: Any,
) -> EngineeringInput:
    """Build EngineeringInput for migration helper only."""
    return EngineeringInput(
        input_id=input_id,
        value=value,
        unit=unit,
        source=source,
        status=status,
        **kwargs,
    )


def populate_task_facts(task: Task, inputs: dict[str, EngineeringInput]) -> None:
    for inp in inputs.values():
        set_fact_from_input(task, inp)


def facts_from_inputs(
    inputs: dict[str, EngineeringInput],
    *,
    task_id: str = "test",
    workflow_id: str | None = None,
) -> dict[str, Fact]:
    """Convert legacy EngineeringInput dict to active facts for graph/validation APIs."""
    store = facts_from_legacy_inputs(inputs, task_id=task_id, workflow_id=workflow_id)
    return store.active_facts()


def fact_get_value(task: Task, key: str) -> Any:
    fact = task.fact_store.active_fact(key)
    if fact is None:
        raise KeyError(key)
    return fact_scalar_value(fact)


def fact_get_unit(task: Task, key: str) -> str:
    fact = task.fact_store.active_fact(key)
    if fact is None:
        raise KeyError(key)
    return fact_unit(fact)
