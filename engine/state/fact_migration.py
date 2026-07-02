"""Migrate legacy EngineeringInput records to Facts."""

from __future__ import annotations

from typing import Any

from engine.reference.param_resolver import resolve_parameter_id
from models.fact_store import FactStore
from models.fact import (
    FactClass,
    FactProvenance,
    FactSource,
    SourceType,
    ValidationStatus,
    build_boolean_fact,
    build_categorical_fact,
    build_numeric_fact,
    new_fact_id,
)
from models.input import EngineeringInput, InputSource, InputStatus, ResolutionMethod


def _validation_status_from_input(status: InputStatus) -> ValidationStatus:
    mapping = {
        InputStatus.PENDING: ValidationStatus.PENDING,
        InputStatus.CONFIRMED: ValidationStatus.CONFIRMED,
        InputStatus.PROPOSED_DEFAULT: ValidationStatus.PENDING,
        InputStatus.USER_OVERRIDE: ValidationStatus.CONFIRMED,
    }
    return mapping.get(status, ValidationStatus.PENDING)


def _fact_class_from_input(inp: EngineeringInput) -> FactClass:
    if inp.resolution_method == ResolutionMethod.TABLE_LOOKUP:
        return FactClass.LOOKED_UP
    if inp.resolution_method == ResolutionMethod.EQUATION:
        return FactClass.CALCULATED
    if inp.resolution_method == ResolutionMethod.DEFAULT_CONFIRMED:
        return FactClass.DEFAULT_CONFIRMED
    if inp.source == InputSource.USER:
        return FactClass.USER_SUPPLIED
    if inp.source == InputSource.TABLE:
        return FactClass.LOOKED_UP
    if inp.source == InputSource.DEFAULT:
        return FactClass.DEFAULT_CONFIRMED
    if inp.source == InputSource.SYSTEM:
        return FactClass.SYSTEM_GENERATED
    return FactClass.USER_SUPPLIED


def _source_from_input(inp: EngineeringInput) -> FactSource:
    source_type = SourceType.USER_INPUT
    source_id = "USER"
    if inp.source == InputSource.TABLE:
        source_type = SourceType.TABLE_LOOKUP
        source_id = inp.resolution_ref.table if inp.resolution_ref and inp.resolution_ref.table else "TABLE"
    elif inp.source == InputSource.DEFAULT:
        source_type = SourceType.DEFAULT_CONFIRMED
        source_id = inp.introduced_at_node or "SYSTEM"
    elif inp.source == InputSource.SYSTEM:
        source_type = SourceType.SYSTEM
        source_id = "SYSTEM"
    lookup_node = None
    if inp.resolution_ref and inp.resolution_ref.node_id:
        lookup_node = inp.resolution_ref.node_id
    return FactSource(
        source_type=source_type,
        source_id=source_id,
        lookup_node=lookup_node,
        description=inp.description,
    )


def fact_from_engineering_input(
    inp: EngineeringInput,
    *,
    task_id: str,
    workflow_id: str | None = None,
) -> Any:
    from models.fact import Fact

    key = inp.input_id
    parameter = resolve_parameter_id(key)
    provenance = FactProvenance(
        task_id=task_id,
        workflow_id=workflow_id,
        collected_at_node=inp.introduced_at_node,
        produced_by_node=inp.resolved_at_node,
        created_by=inp.source.value,
        timestamp=None,
    )
    source = _source_from_input(inp)
    fact_class = _fact_class_from_input(inp)
    validation_status = _validation_status_from_input(inp.status)
    common = dict(
        key=key,
        parameter=parameter,
        fact_class=fact_class,
        source=source,
        provenance=provenance,
        fact_id=new_fact_id(),
        validation_status=validation_status,
        symbol=inp.symbol,
        description=inp.description,
    )
    if inp.value is None:
        from models.fact import Fact, FactValidation, FactSupersession

        return Fact(
            id=common["fact_id"],
            parameter=parameter,
            key=key,
            fact_class=fact_class,
            value=None,
            source=source,
            provenance=provenance,
            validation=FactValidation(status=validation_status),
            supersession=FactSupersession(active=True),
            symbol=inp.symbol,
            description=inp.description,
            default=inp.default,
            requires_confirmation=inp.requires_confirmation,
            default_condition=inp.default_condition,
            introduced_at_node=inp.introduced_at_node,
            resolved_at_node=inp.resolved_at_node,
            original_value=inp.original_value,
            original_unit=inp.original_unit,
            uncertainty=inp.uncertainty,
        )
    if isinstance(inp.value, bool):
        return build_boolean_fact(value=inp.value, **common)
    if isinstance(inp.value, (int, float)):
        return build_numeric_fact(
            amount=inp.value,
            unit=inp.unit,
            **common,
        )
    return build_categorical_fact(
        label=str(inp.value),
        normalized_key=str(inp.value).strip().lower().replace(" ", "_"),
        **common,
    )


def facts_from_legacy_inputs(
    inputs: dict[str, EngineeringInput],
    *,
    task_id: str,
    workflow_id: str | None = None,
) -> FactStore:
    store = FactStore()
    for inp in inputs.values():
        fact = fact_from_engineering_input(inp, task_id=task_id, workflow_id=workflow_id)
        store.append_fact(fact)
    return store
