"""Reconstruct runtime facts from workflow parameters only."""

from __future__ import annotations

from models.fact import (
    Fact,
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
from models.workflow_state import WorkflowParameter

_SOURCE_TO_FACT_CLASS: dict[str, FactClass] = {
    "user_input": FactClass.USER_SUPPLIED,
    "lookup": FactClass.LOOKED_UP,
    "default": FactClass.DEFAULT_CONFIRMED,
    "equation": FactClass.CALCULATED,
    "derived": FactClass.DERIVED,
}

_SOURCE_TO_SOURCE_TYPE: dict[str, SourceType] = {
    "user_input": SourceType.USER_INPUT,
    "lookup": SourceType.TABLE_LOOKUP,
    "default": SourceType.DEFAULT_CONFIRMED,
    "equation": SourceType.EQUATION,
    "derived": SourceType.SYSTEM,
}

_STATUS_TO_VALIDATION: dict[str, ValidationStatus] = {
    "pending": ValidationStatus.PENDING,
    "confirmed": ValidationStatus.CONFIRMED,
    "proposed_default": ValidationStatus.PENDING,
}


def _fact_from_parameter(name: str, param: WorkflowParameter) -> Fact:
    fact_class = _SOURCE_TO_FACT_CLASS.get(param.source, FactClass.SYSTEM_GENERATED)
    source_type = _SOURCE_TO_SOURCE_TYPE.get(param.source, SourceType.SYSTEM)
    validation_status = _STATUS_TO_VALIDATION.get(param.status, ValidationStatus.PENDING)
    requires_confirmation = param.status == "proposed_default"
    provenance = FactProvenance(created_by=param.source)
    source = FactSource(source_type=source_type, source_id=param.source)
    common = dict(
        key=name,
        parameter=name,
        fact_class=fact_class,
        source=source,
        provenance=provenance,
        fact_id=new_fact_id(),
        validation_status=validation_status,
        symbol=param.symbol,
        requires_confirmation=requires_confirmation,
    )
    value = param.value
    if value is None:
        from models.fact import FactValidation, FactSupersession

        return Fact(
            id=common["fact_id"],
            parameter=name,
            key=name,
            fact_class=fact_class,
            value=None,
            source=source,
            provenance=provenance,
            validation=FactValidation(status=validation_status),
            supersession=FactSupersession(active=True),
            symbol=param.symbol,
            requires_confirmation=requires_confirmation,
        )
    if isinstance(value, bool):
        return build_boolean_fact(value=value, **common)
    if isinstance(value, (int, float)):
        return build_numeric_fact(amount=value, unit=param.unit, **common)
    return build_categorical_fact(
        label=str(value),
        normalized_key=str(value).strip().lower().replace(" ", "_"),
        **common,
    )


def facts_from_parameters(
    parameters: dict[str, WorkflowParameter],
) -> dict[str, Fact]:
    """Build fact map for graph display emitters."""
    return {name: _fact_from_parameter(name, param) for name, param in parameters.items()}


def engineering_inputs_from_parameters(
    parameters: dict[str, WorkflowParameter],
) -> dict[str, Fact]:
    """Legacy alias for :func:`facts_from_parameters`."""
    return facts_from_parameters(parameters)
